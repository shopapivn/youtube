"""Dây chuyền **Prompt Visuals**: file giọng đọc → phụ đề → prompt từng cảnh → Excel.

═══ ĐÂY LÀ VIỆC NỐI DÂY, KHÔNG PHẢI VIỆC VIẾT MỚI ═══

Cả hai đầu việc đã nằm sẵn trong `tool-catalog/`, viết xong từ trước mà chưa có
màn hình nào gọi tới:

* `transcribe.local` — nghe file mp3/wav rồi ghi ra `.srt`. **Chạy trên máy
  khách bằng `faster-whisper`, không tiêu ví ShopAPI.**
* `prompt.workbook` — cắt phụ đề thành cảnh theo đúng trần độ dài của engine
  (Veo3 8 giây, Seedance 10 giây), nhờ AI viết `img_prompt`/`video_prompt` cho
  từng cảnh, rồi xuất `scene-prompts.xlsx`. **Bước này tiêu ví ShopAPI.**

Hai cổng khớp nhau sẵn: `transcribe.local` ra `subtitle/srt.v1`, `prompt.workbook`
vào cũng `subtitle/srt.v1`. Nên việc ở đây chỉ là dựng đúng tờ khai workflow rồi
đưa cho `core.builder_service.BuilderService` chạy.

Cột của workbook sinh ra **trùng tên với bảng của VE3_SUITE** (`scenes`,
`characters`, `director_plan`, `thumbnail`) — xem `tool-catalog/prompt.workbook/
run.py`. Nghĩa là file Excel lấy ở đây mở thẳng bằng VE3 được, không phải chép
cột sang.

Module gần như thuần tuý: không mạng, không Qt. Ngoại lệ duy nhất là
`liet_ke_phong_cach` — nó nhờ `core.khuon`/`core.kenh` đọc các bộ vẽ trong
khuôn kênh và `style.yaml` của kênh đã tạo, để tab này cho chọn ĐÚNG những
phong cách mà tab Tự động dùng. Phần dựng chỉ dẫn từ một bộ đã đọc
(`chi_dan_tu_bo`) vẫn thuần tuý, test bằng dict thường được.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

__all__ = [
    "ENGINE", "MO_HINH", "NGON_NGU", "MA_MODEL_NGHE", "MAU_HINH",
    "KHOA_CHI_DAN", "PhongCach", "chi_dan_tu_bo", "liet_ke_phong_cach",
    "LOI_NHAC_XAY_PHONG_CACH", "chi_dan_tu_tra_loi_ai",
    "CHE_DO_KE", "CHE_DO_CAN_ANH_NV",
    "dung_workflow", "dung_boi_canh", "cau_thieu_gi", "duong_workbook",
    "canh_de_xem", "dan_de_xem", "tom_tat_dan", "bia_de_xem", "nhac_de_xem",
    "boi_canh_de_xem", "man_de_xem", "ke_hoach_de_xem",
]

#: Engine dựng video, và trần độ dài clip của nó. Người dùng chọn engine nào thì
#: cảnh phải được cắt theo trần của engine ấy — cảnh 15 giây gửi cho Veo3 nghĩa
#: là 7 giây lời đọc không có hình.
ENGINE = (
    ("veo3", "Veo 3 — mỗi cảnh tối đa 8 giây"),
    ("seedance", "Seedance — mỗi cảnh tối đa 10 giây"),
)

#: Mô hình viết prompt. Đúng hai tên `prompt.workbook` nhận (xem `tool.json`).
MO_HINH = (
    ("claude-sonnet-5", "Sonnet 5 — nhanh, rẻ"),
    ("claude-opus-5", "Opus 5 — chậm hơn, prompt kỹ hơn"),
)

#: Tiếng của file giọng đọc. `auto` để máy tự đoán.
NGON_NGU = (
    ("vi", "Tiếng Việt"),
    ("en", "Tiếng Anh"),
    ("auto", "Tự đoán"),
)

#: **Phong cách hình ảnh** cho cả video — mượn ý "chọn template visual" ở bước 3
#: tab Tự động, nhưng không bắt khách dựng cả một kênh. Mỗi mẫu là một câu tiếng
#: Anh mô tả tông hình, đổ vào `context` của `prompt.workbook` (xem `dung_boi_canh`)
#: nên mọi cảnh giữ chung một look mà **không phải sửa tool** — `prompt.workbook`
#: đã nhận `context` sẵn. `auto` để AI tự chọn phong cách như trước.
MAU_HINH = (
    ("auto", "Tự động — để AI tự chọn phong cách", ""),
    ("dien_anh", "Điện ảnh — ánh sáng dịu, chiều sâu, màu ấm",
     "Cinematic live-action look: shallow depth of field, soft directional "
     "lighting, warm filmic colour grade, subtle film grain."),
    ("hoat_hinh_3d", "Hoạt hình 3D — kiểu Pixar, màu tươi",
     "Stylised 3D animation look (Pixar-like): clean rounded shapes, soft "
     "global illumination, vivid saturated palette, expressive characters."),
    ("hoat_hinh_2d", "Hoạt hình 2D — vẽ tay, nét mảnh",
     "Hand-drawn 2D animation look: clean line art, flat cel shading, gentle "
     "watercolour-style backgrounds."),
    ("tai_lieu", "Tài liệu — chân thực, ánh sáng tự nhiên",
     "Realistic documentary look: natural available light, true-to-life "
     "colours, handheld realism, minimal stylisation."),
    ("co_trang", "Cổ trang / lịch sử — hoài niệm, tông trầm",
     "Historical/period look: muted earthy palette, candle and daylight "
     "sources, textured period fabrics, nostalgic atmosphere."),
)

#: Các khoá của một bộ vẽ (`_KHUON/ve/*/ve.yaml`) hay `style.yaml` của kênh
#: được rút vào chỉ dẫn phong cách, kèm nhãn tiếng Anh đứng đầu dòng. Chỉ lấy
#: những khoá nói về HÌNH của cảnh; bỏ `thumb_*` (Prompt Visuals không làm ảnh
#: bìa) và `reference_lock` (nó trỏ vào ảnh `nv1.png` của kênh — tab này không
#: có kênh nên tấm ảnh đó không đi kèm, nhắc tới chỉ làm AI trỏ vào ảnh ma).
KHOA_CHI_DAN = (
    ("image_style", "Image style"),
    ("video_style", "Video/motion style"),
    ("palette", "Palette"),
    ("default_character_prompt", "Draw every recurring character in this "
                                 "design language"),
    ("negative_prompt", "Never show"),
    ("technical_suffix", "Append this style suffix to every image and video "
                         "prompt"),
)


@dataclass
class PhongCach:
    """Một lựa chọn trong ô “Phong cách hình ảnh” của tab Prompt Visuals.

    `chi_dan` là khối tiếng Anh đổ vào `context` cho `prompt.workbook`; rỗng
    nghĩa là “AI tự chọn” — không gửi gì cả.
    """

    ma: str
    ten: str
    mo_ta: str = ""
    chi_dan: str = ""


def chi_dan_tu_bo(du_lieu: Optional[Mapping[str, Any]]) -> str:
    """Rút 16 khoá hình của một bộ vẽ/`style.yaml` thành chỉ dẫn phong cách.

    Thuần tuý: nhận dict đã đọc sẵn, trả về khối chữ nhiều dòng theo thứ tự
    `KHOA_CHI_DAN`, bỏ khoá rỗng. Trả `""` khi không có gì dùng được — nơi gọi
    coi bộ đó như không tồn tại thay vì hiện một lựa chọn không làm gì.
    """
    dong: List[str] = []
    for khoa, nhan in KHOA_CHI_DAN:
        gia = str((du_lieu or {}).get(khoa) or "").strip()
        if gia:
            dong.append("{0}: {1}".format(nhan, gia))
    return "\n".join(dong)


def liet_ke_phong_cach(goc: str) -> List["PhongCach"]:
    """Mọi phong cách chọn được, đúng nguồn mà tab Tự động dùng khi dựng kênh.

    Thứ tự cố ý: “Tự động” trước, rồi các mẫu gọn (`MAU_HINH`), rồi **bộ vẽ
    trong khuôn kênh** (`CHANNEL/_KHUON/ve/` — thứ khách thấy khi tạo kênh ở
    tab Tự động), cuối cùng là **kênh đã tạo** (`style.yaml` của từng kênh) để
    video lẻ ăn khớp với kênh đang chạy.

    Bộ nào đọc hỏng hoặc không có khoá hình nào thì lặng lẽ bỏ qua — một tệp
    YAML viết sai không được làm mất các lựa chọn còn lại.
    """
    import os  # noqa: PLC0415

    from .kenh import (  # noqa: PLC0415
        TEP_KENH, TEP_STYLE, doc_yaml, duong_kenh, liet_ke_kenh,
    )
    from .khuon import liet_ke_ve  # noqa: PLC0415

    ra = [PhongCach(ma=ma, ten=ten, chi_dan=chi_dan)
          for ma, ten, chi_dan in MAU_HINH]
    for bo in liet_ke_ve(goc):
        chi_dan = chi_dan_tu_bo(bo.du_lieu)
        if chi_dan:
            ra.append(PhongCach(
                ma="ve:" + bo.ma, ten="Bộ vẽ: " + bo.nhan,
                mo_ta=bo.mo_ta or "Bộ vẽ trong khuôn kênh của tab Tự động.",
                chi_dan=chi_dan))
    for ma_kenh in liet_ke_kenh(goc):
        style = doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_STYLE))
        chi_dan = chi_dan_tu_bo(style)
        if not chi_dan:
            continue
        kenh = doc_yaml(os.path.join(duong_kenh(goc, ma_kenh), TEP_KENH))
        ten_kenh = str(kenh.get("ten") or "").strip()
        ra.append(PhongCach(
            ma="kenh:" + ma_kenh,
            ten="Kênh {0}{1}".format(ma_kenh,
                                     " — " + ten_kenh if ten_kenh else ""),
            mo_ta="Đúng phong cách kênh này đang dùng ở tab Tự động — video "
                  "lẻ sẽ ăn khớp với video của kênh.",
            chi_dan=chi_dan))
    return ra


#: Lời nhắc cho tab "AI xây phong cách từ ảnh của bạn" (Bước 2). Chủ dự án
#: 24/08/2026: *"cho khách tải vài ảnh và từ đó dùng API để xác định được phong
#: cách và về sau prompt sẽ là phong cách đó"*. AI nhìn ảnh, trả JSON đúng các
#: khoá của một bộ vẽ để `chi_dan_tu_bo` dựng chỉ dẫn như mọi phong cách khác.
LOI_NHAC_XAY_PHONG_CACH = (
    "Look at the attached reference image(s). They define the visual style "
    "the user wants for EVERY scene of a narrated video. Describe that style "
    "precisely enough that an image model can reproduce it on new subjects. "
    "Do not describe the specific subjects or scenes in the images — only the "
    "look: medium, line, shading, texture, lighting, colour, mood, framing.\n\n"
    "Return JSON only, no commentary:\n"
    '{"image_style": "<one dense English sentence: medium, technique, texture, '
    'lighting, level of detail>",\n'
    ' "video_style": "<how motion should look in this style, one sentence>",\n'
    ' "palette": "<the dominant colours, with hex codes if clear>",\n'
    ' "default_character_prompt": "<how people/characters are drawn in this '
    'style: proportions, faces, line, colour — no names>",\n'
    ' "negative_prompt": "<what must never appear for the look to hold, e.g. '
    'no photorealism, no 3D render, no text, no watermark>"}'
)


def chi_dan_tu_tra_loi_ai(tra_loi: str) -> str:
    """Câu trả lời của AI (JSON, có thể lẫn chữ thừa) → chỉ dẫn phong cách.

    Trả `""` nếu không rút được gì — nơi gọi nói với khách là chưa đọc được
    ảnh, không lặng lẽ dùng phong cách rỗng.
    """
    from .goi_van_ban import loc_json  # noqa: PLC0415

    try:
        du_lieu = loc_json(str(tra_loi or ""))
    except Exception:  # noqa: BLE001 — chữ rác thì coi như không có
        return ""
    if not isinstance(du_lieu, Mapping):
        return ""
    return chi_dan_tu_bo(du_lieu)


#: Model nghe mà `transcribe.local` khai trong `tool.json`. Nêu lại ở đây để
#: giao diện nói được **tên thật** của thứ còn thiếu thay vì câu chung chung.
MA_MODEL_NGHE = "faster-whisper-small"

#: Tên tệp `prompt.workbook` ghi ra trong workspace của nó.
TEN_WORKBOOK = "scene-prompts.xlsx"

NODE_NGHE = "nghe"
NODE_PROMPT = "prompt"


#: Ba cách kể chuyện — chủ dự án 24/08/2026, tham khảo VE3_SUITE. Mã đi thẳng
#: vào `config.che_do_ke` của `prompt.workbook` (xem `CHE_DO_*` ở `run.py`).
CHE_DO_KE = (
    ("tu_xay", "AI tự xây nhân vật & bối cảnh theo nội dung",
     "Không cần ảnh nhân vật. AI đọc lời đọc rồi dựng dàn nhân vật (nv1, nv2…) "
     "và các bối cảnh lặp lại (loc1, loc2…), mọi cảnh dùng chung."),
    ("mot_nhan_vat", "Một nhân vật cố định của kênh",
     "Bạn đưa MỘT ảnh nhân vật (nv1). Mọi cảnh xoay quanh nhân vật đó; không "
     "có nhân vật phụ hay bối cảnh tham chiếu — giống tab Tự động."),
    ("nhan_vat_va_boi_canh", "Nhân vật cố định + nhân vật & bối cảnh tham chiếu",
     "Bạn đưa ảnh nhân vật chính (nv1); AI dựng thêm nhân vật phụ (nv2…) và "
     "bối cảnh lặp lại (loc1…) theo nội dung để cả video nhất quán."),
)

#: Chế độ nào cần ảnh nhân vật chính do khách đưa.
CHE_DO_CAN_ANH_NV = ("mot_nhan_vat", "nhan_vat_va_boi_canh")


def dung_workflow(ma_artifact_audio: str, *, engine: str = "veo3",
                  mo_hinh: str = "claude-sonnet-5", ngon_ngu: str = "vi",
                  nhat_quan: bool = True, ma_artifact_context: str = "",
                  ma_chay: str = "prompt-visuals", che_do_ke: str = "tu_xay",
                  bia: bool = True, nhac: bool = True) -> Dict[str, Any]:
    """Dựng tờ khai workflow hai bước cho một file giọng đọc.

    `ma_artifact_audio` là mã artifact đã nạp vào kho của Studio — không phải
    đường dẫn file. Runner chỉ làm việc với mã artifact; đưa đường dẫn thẳng vào
    là nó không tìm ra và báo một câu lỗi chẳng ai hiểu.

    `nhat_quan` bật thì `prompt.workbook` chạy thêm **một lượt** đọc cả lời đọc
    để dựng dàn nhân vật cố định + một phong cách, rồi mọi cảnh dùng chung —
    y như tab Tự động. Tắt thì về hành vi cũ: mỗi cảnh tự do, sheet nhân vật rỗng.

    `ma_artifact_context` là mã artifact JSON (kịch bản + phong cách hình ảnh do
    `dung_boi_canh` gói lại) đưa vào cổng `context` của `prompt.workbook`. Bỏ
    trống thì workflow không có node `context` — đúng hành vi cũ. Có thì AI đọc
    thêm kịch bản (chính xác hơn chỉ nghe phụ đề) và giữ đúng phong cách đã chọn.

    `ma_chay` thành `workflow_id`, và `workflow_id` cũng là **tên tệp điểm
    dừng** (`workspace/builder/checkpoints/<id>.json`). Nên mỗi file giọng đọc
    phải có một mã riêng: dùng chung một mã thì chạy file thứ hai sẽ đè điểm
    dừng của file thứ nhất, và nút "chạy tiếp" khôi phục nhầm việc.
    """
    if not str(ma_artifact_audio or "").strip():
        raise ValueError("Chưa có file giọng đọc để chạy.")
    if engine not in dict(ENGINE):
        raise ValueError("Engine không hợp lệ: {0}".format(engine))
    if mo_hinh not in dict(MO_HINH):
        raise ValueError("Mô hình không hợp lệ: {0}".format(mo_hinh))
    if che_do_ke not in {ma for ma, _t, _m in CHE_DO_KE}:
        raise ValueError("Cách kể chuyện không hợp lệ: {0}".format(che_do_ke))

    cai_dat_nghe: Dict[str, Any] = {"model": "small", "device": "cpu",
                                    "compute_type": "int8"}
    # `language` bỏ trống nghĩa là để máy tự đoán — `run.py` của tool đọc
    # "auto"/"" thành `None` rồi mới đưa cho faster-whisper.
    cai_dat_nghe["language"] = "" if ngon_ngu == "auto" else ngon_ngu

    # Bước viết prompt nhận thêm cổng `context` (kịch bản + phong cách) khi có —
    # `prompt.workbook` khai `context` là tuỳ chọn, nên bỏ trống thì để `inputs`
    # rỗng như cũ, đừng nhét một khoá `context` rỗng vào cho runner khỏi đi tìm
    # một artifact không tồn tại.
    inputs_prompt: Dict[str, Any] = {}
    if str(ma_artifact_context or "").strip():
        inputs_prompt["context"] = ma_artifact_context

    return {
        "version": "1",
        "workflow_id": ma_chay,
        "name": "Prompt Visuals",
        "nodes": [
            # Khoá là `id`, KHÔNG phải `node_id` — `core.workflow.parse_workflow`
            # đọc `item["id"]`. Đặt nhầm thì lỗi báo ra là "Node thieu id", câu
            # đó không chỉ vào chỗ sai.
            {
                "id": NODE_NGHE,
                "tool_id": "transcribe.local",
                "inputs": {"audio": ma_artifact_audio},
                "config": cai_dat_nghe,
            },
            {
                "id": NODE_PROMPT,
                "tool_id": "prompt.workbook",
                "inputs": inputs_prompt,
                "config": {"engine": engine, "model": mo_hinh,
                           "nhat_quan_nhan_vat": bool(nhat_quan),
                           "che_do_ke": che_do_ke,
                           "thumbnail": bool(bia), "nhac": bool(nhac)},
            },
        ],
        "edges": [
            {
                "source_node": NODE_NGHE, "source_port": "subtitles",
                "target_node": NODE_PROMPT, "target_port": "subtitles",
            },
        ],
    }


def _mau_chi_dan(ma_mau: str) -> str:
    """Câu tiếng Anh mô tả tông hình của một mẫu `MAU_HINH`; `""` nếu là `auto`."""
    for ma, _ten, chi_dan in MAU_HINH:
        if ma == ma_mau:
            return chi_dan
    return ""


def dung_boi_canh(kich_ban: str = "", mau_hinh: str = "auto",
                  chi_dan: str = "", che_do_ke: str = "tu_xay",
                  nhan_vat_co_dinh: Optional[Mapping[str, Any]] = None
                  ) -> Dict[str, Any]:
    """Gói **kịch bản** (tuỳ chọn) + **phong cách hình ảnh** thành `context`.

    Cả hai đổ vào cùng cổng `context` mà `prompt.workbook` đã nhận sẵn — không
    phải sửa tool:

    * `script` — lời kịch bản khách dán vào. Chỉ nghe phụ đề thì AI dễ hiểu sai
      tên riêng, thuật ngữ; có kịch bản gốc thì prompt bám đúng nội dung hơn.
    * `visual_style_directive` — câu ép mọi cảnh giữ một tông hình.
      `prompt.workbook` đọc `context` cả ở lượt casting lẫn lượt chia cảnh, nên
      nó thấm vào `style.image_style`/`palette`/`motion`.

    Phong cách lấy từ một trong hai đường: `chi_dan` là khối chữ dựng sẵn (bộ
    vẽ trong khuôn, `style.yaml` của kênh — xem `liet_ke_phong_cach`), có nó
    thì dùng luôn; không có thì tra `mau_hinh` trong `MAU_HINH` như cũ.

    Trả `{}` khi không có gì để gửi — nơi gọi chỉ tạo artifact `context` khi dict
    khác rỗng, để workflow không mọc thêm một node thừa.
    """
    ra: Dict[str, Any] = {}
    kb = str(kich_ban or "").strip()
    if kb:
        ra["script"] = kb
    chi_dan = str(chi_dan or "").strip() or _mau_chi_dan(mau_hinh)
    if chi_dan:
        ra["visual_style_directive"] = (
            "Render EVERY scene in this fixed visual style, and set the video's "
            "style.image_style / palette / motion to match it: " + chi_dan)
    # Cách kể chuyện + nhân vật cố định (loại 1, 2): `prompt.workbook` đọc
    # `story_mode` và `fixed_character` từ context; loại 3 không ghi gì để
    # context rỗng vẫn rỗng (workflow không mọc node thừa).
    if che_do_ke in CHE_DO_CAN_ANH_NV:
        ra["story_mode"] = che_do_ke
        nv = dict(nhan_vat_co_dinh or {})
        nv.setdefault("id", "nv1")
        nv.setdefault("image_file", "nv1.png")
        ra["fixed_character"] = nv
    return ra


#: Đổi từng câu lỗi kỹ thuật của `BuilderService.readiness()` thành câu người
#: không biết lập trình đọc được, kèm **việc phải làm**. Câu gốc dạng
#: "transcribe.local: thieu model faster-whisper-small." thì đúng nhưng vô dụng:
#: người đọc không biết model là gì và không biết bấm vào đâu.
_DICH_THIEU = (
    ("thieu model", "Máy bạn chưa có bộ nghe tiếng ({0}). Chạy lại SETUP.bat "
                    "một lần khi có mạng — nó tải bộ nghe (khoảng 0,5 GB) về "
                    "thẳng thư mục tool, các lần sau dùng lại."),
    ("thieu thanh phan", "Máy bạn thiếu thư viện: {0}. Mở tab Agent, bấm "
                         "“Cài những thứ còn thiếu”."),
    ("thieu chuong trinh", "Máy bạn thiếu chương trình: {0}."),
    ("chua dang nhap", "Bạn chưa đăng nhập ShopAPI. Mở tab Tài khoản để đăng "
                       "nhập — bước viết prompt cần ví."),
)


def cau_thieu_gi(van_de) -> List[str]:
    """Dịch danh sách `Readiness.issues` sang tiếng người, bỏ trùng.

    Trả về danh sách rỗng khi chạy được — nơi gọi chỉ cần kiểm `if not`.
    """
    ra: List[str] = []
    for cau in van_de or ():
        chu = str(cau)
        # Câu gốc dạng "<tool_id>: <lý do> <tên thứ thiếu>."
        phan = chu.split(":", 1)
        con_lai = phan[1].strip() if len(phan) == 2 else chu
        dich = ""
        for dau_hieu, khuon in _DICH_THIEU:
            if dau_hieu in con_lai:
                ten = con_lai[len(dau_hieu):].strip(" .")
                dich = khuon.format(ten or MA_MODEL_NGHE)
                break
        muc = dich or chu
        if muc not in ra:
            ra.append(muc)
    return ra


def duong_workbook(trang_thai, goc_workspace) -> Optional[str]:
    """Tìm đường dẫn file Excel trong kết quả một lượt chạy, `None` nếu chưa có.

    Đi qua `RunState` thay vì đoán theo tên thư mục: runner đặt mỗi lượt chạy
    vào một `run_id` riêng, và đoán sai thì mở nhầm file của lượt trước — thứ
    người dùng không tài nào phát hiện, vì file trước cũng mở được.
    """
    nut = getattr(trang_thai, "nodes", {}) or {}
    buoc = nut.get(NODE_PROMPT)
    if buoc is None or getattr(buoc, "status", "") != "succeeded":
        return None
    ma = (getattr(buoc, "outputs", {}) or {}).get("workbook")
    if not ma:
        return None
    return str(ma)


def _mapping(gia_tri: Any) -> Mapping[str, Any]:
    return gia_tri if isinstance(gia_tri, Mapping) else {}


# ═══ ĐỌC LẠI WORKBOOK ĐỂ XEM TRƯỚC — thuần tuý, không đụng file ═══
#
# Tab Tự động cho khách **thấy từng cảnh** thay vì đoán mò (xem "dải phim" ở
# `ui_qt/trang_auto.py`). Prompt Visuals trước đây chỉ ném ra một file Excel rồi
# báo "xong": khách không biết prompt viết ra sao, cảnh có đúng thứ tự không,
# dàn nhân vật gồm những ai. Chủ dự án gọi đúng cái đó là *"logic hơi khó hiểu"*.
#
# Nên phần đọc lại — sắp cảnh theo số, đánh số, tóm tắt dàn nhân vật — nằm ở đây
# để test được mà không cần mở file thật: nơi gọi (giao diện) đọc các hàng của
# sheet bằng openpyxl rồi đưa vào đây, còn đây chỉ lo phần dễ sai là ghép và sắp.


def _lay(dong: Sequence[Any], vi_tri: Mapping[str, int], ten: str) -> str:
    """Lấy ô `ten` của một hàng theo bảng vị trí cột, trả chuỗi đã cắt trắng."""
    i = vi_tri.get(ten, -1)
    if i < 0 or i >= len(dong) or dong[i] is None:
        return ""
    return str(dong[i]).strip()


def _vi_tri_cot(hang: Sequence[Sequence[Any]]) -> Optional[Dict[str, int]]:
    """Hàng đầu là tiêu đề → bảng {tên cột: chỉ số}. `None` nếu chưa đủ hàng."""
    if len(hang) < 2:
        return None
    return {str(c or "").strip(): i for i, c in enumerate(hang[0])}


def canh_de_xem(hang: Sequence[Sequence[Any]]) -> List[Dict[str, Any]]:
    """Các hàng sheet `scenes` (hàng đầu là tiêu đề) → danh sách cảnh để xem.

    Sắp theo `scene_id` tăng dần: các cảnh được viết song song theo khúc nên thứ
    tự trong file chưa chắc đúng, mà khách cần đọc theo đúng mạch câu chuyện.
    Bỏ hàng không có số cảnh (dòng trống, dòng rác) thay vì để nó phá thứ tự.
    """
    hang = [list(d) for d in (hang or [])]
    vi_tri = _vi_tri_cot(hang)
    if vi_tri is None:
        return []
    ra: List[Dict[str, Any]] = []
    for dong in hang[1:]:
        so_txt = _lay(dong, vi_tri, "scene_id")
        try:
            so = int(float(so_txt))
        except (TypeError, ValueError):
            continue
        ra.append({
            "scene_id": so,
            "srt_start": _lay(dong, vi_tri, "srt_start"),
            "srt_end": _lay(dong, vi_tri, "srt_end"),
            "srt_text": _lay(dong, vi_tri, "srt_text"),
            "srt_text_vi": _lay(dong, vi_tri, "srt_text_vi"),
            "img_prompt": _lay(dong, vi_tri, "img_prompt"),
            "video_prompt": _lay(dong, vi_tri, "video_prompt"),
            "characters_used": _lay(dong, vi_tri, "characters_used"),
            "location_used": _lay(dong, vi_tri, "location_used"),
        })
    ra.sort(key=lambda c: c["scene_id"])
    return ra


def _bang_de_xem(hang: Sequence[Sequence[Any]], cot: Sequence[str],
                 khoa: str) -> List[Dict[str, str]]:
    """Các hàng một sheet (hàng đầu là tiêu đề) → dict theo `cot`, bỏ hàng thiếu `khoa`."""
    hang = [list(d) for d in (hang or [])]
    vi_tri = _vi_tri_cot(hang)
    if vi_tri is None:
        return []
    ra: List[Dict[str, str]] = []
    for dong in hang[1:]:
        if not _lay(dong, vi_tri, khoa):
            continue
        ra.append({c: _lay(dong, vi_tri, c) for c in cot})
    return ra


def bia_de_xem(hang: Sequence[Sequence[Any]]) -> List[Dict[str, str]]:
    """Sheet `thumbnail` → ba prompt ảnh bìa (kèm chữ hook + tiêu đề đề xuất)."""
    return _bang_de_xem(hang, ("thumb_id", "version_desc", "img_prompt",
                               "thumb_text", "title"), "thumb_id")


def nhac_de_xem(hang: Sequence[Sequence[Any]]) -> List[Dict[str, str]]:
    """Sheet `music` → các track Suno theo thứ tự thời gian."""
    ra = _bang_de_xem(hang, ("music_id", "start_time", "end_time",
                             "suno_prompt", "mood"), "music_id")
    ra.sort(key=lambda m: float(m["start_time"] or 0))
    return ra


def man_de_xem(hang: Sequence[Sequence[Any]]) -> List[Dict[str, str]]:
    """Sheet `story` → các màn (loại 2, 3) theo thứ tự."""
    ra = _bang_de_xem(hang, ("segment_id", "name", "message", "emotion", "motif",
                             "srt_from", "srt_to", "arc"), "segment_id")
    ra.sort(key=lambda m: float(m["segment_id"] or 0))
    return ra


def ke_hoach_de_xem(hang: Sequence[Sequence[Any]]) -> List[Dict[str, str]]:
    """Sheet `director_plan` → các beat theo màn rồi theo số beat."""
    ra = _bang_de_xem(hang, ("segment_id", "beat", "srt_from", "srt_to", "purpose",
                             "characters", "location", "shot_size", "camera",
                             "element_motion", "emotion"), "segment_id")
    ra.sort(key=lambda b: (float(b["segment_id"] or 0), float(b["beat"] or 0)))
    return ra


def boi_canh_de_xem(hang: Sequence[Sequence[Any]]) -> List[Dict[str, str]]:
    """Sheet `locations` → bối cảnh tham chiếu."""
    return _bang_de_xem(hang, ("id", "name", "english_prompt",
                               "lighting_default"), "id")


def dan_de_xem(hang: Sequence[Sequence[Any]]) -> List[Dict[str, str]]:
    """Các hàng sheet `characters` → dàn nhân vật cố định (bỏ hàng thiếu id)."""
    hang = [list(d) for d in (hang or [])]
    vi_tri = _vi_tri_cot(hang)
    if vi_tri is None:
        return []
    ra: List[Dict[str, str]] = []
    for dong in hang[1:]:
        cid = _lay(dong, vi_tri, "id")
        if not cid:
            continue
        ra.append({"id": cid, "role": _lay(dong, vi_tri, "role"),
                   "name": _lay(dong, vi_tri, "name"),
                   "english_prompt": _lay(dong, vi_tri, "english_prompt")})
    return ra


def tom_tat_dan(nhan_vat: Sequence[Mapping[str, Any]]) -> str:
    """Một dòng tiếng người tóm tắt dàn nhân vật giữ xuyên suốt cả video."""
    ds = list(nhan_vat or [])
    if not ds:
        return "Mỗi cảnh tự do — không khoá một nhân vật xuyên suốt."
    phan: List[str] = []
    for c in ds:
        ten = str(c.get("name") or "").strip()
        vai = str(c.get("role") or "").strip()
        nhan = " – ".join(x for x in (vai, ten) if x)
        cid = str(c.get("id") or "").strip() or "?"
        phan.append("{0}{1}".format(cid, " ({0})".format(nhan) if nhan else ""))
    return "Dàn nhân vật giữ xuyên suốt: " + ", ".join(phan)
