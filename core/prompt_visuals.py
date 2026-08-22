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

Module thuần tuý: không mạng, không Qt, không đọc ghi file. Nhờ vậy phần dễ sai
nhất — tờ khai workflow — test được mà không cần tải model 0,5 GB về.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

__all__ = [
    "ENGINE", "MO_HINH", "NGON_NGU", "MA_MODEL_NGHE",
    "dung_workflow", "cau_thieu_gi", "duong_workbook",
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

#: Model nghe mà `transcribe.local` khai trong `tool.json`. Nêu lại ở đây để
#: giao diện nói được **tên thật** của thứ còn thiếu thay vì câu chung chung.
MA_MODEL_NGHE = "faster-whisper-small"

#: Tên tệp `prompt.workbook` ghi ra trong workspace của nó.
TEN_WORKBOOK = "scene-prompts.xlsx"

NODE_NGHE = "nghe"
NODE_PROMPT = "prompt"


def dung_workflow(ma_artifact_audio: str, *, engine: str = "veo3",
                  mo_hinh: str = "claude-sonnet-5", ngon_ngu: str = "vi",
                  nhat_quan: bool = True,
                  ma_chay: str = "prompt-visuals") -> Dict[str, Any]:
    """Dựng tờ khai workflow hai bước cho một file giọng đọc.

    `ma_artifact_audio` là mã artifact đã nạp vào kho của Studio — không phải
    đường dẫn file. Runner chỉ làm việc với mã artifact; đưa đường dẫn thẳng vào
    là nó không tìm ra và báo một câu lỗi chẳng ai hiểu.

    `nhat_quan` bật thì `prompt.workbook` chạy thêm **một lượt** đọc cả lời đọc
    để dựng dàn nhân vật cố định + một phong cách, rồi mọi cảnh dùng chung —
    y như tab Tự động. Tắt thì về hành vi cũ: mỗi cảnh tự do, sheet nhân vật rỗng.

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

    cai_dat_nghe: Dict[str, Any] = {"model": "small", "device": "cpu",
                                    "compute_type": "int8"}
    # `language` bỏ trống nghĩa là để máy tự đoán — `run.py` của tool đọc
    # "auto"/"" thành `None` rồi mới đưa cho faster-whisper.
    cai_dat_nghe["language"] = "" if ngon_ngu == "auto" else ngon_ngu

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
                "inputs": {},
                "config": {"engine": engine, "model": mo_hinh,
                           "nhat_quan_nhan_vat": bool(nhat_quan)},
            },
        ],
        "edges": [
            {
                "source_node": NODE_NGHE, "source_port": "subtitles",
                "target_node": NODE_PROMPT, "target_port": "subtitles",
            },
        ],
    }


#: Đổi từng câu lỗi kỹ thuật của `BuilderService.readiness()` thành câu người
#: không biết lập trình đọc được, kèm **việc phải làm**. Câu gốc dạng
#: "transcribe.local: thieu model faster-whisper-small." thì đúng nhưng vô dụng:
#: người đọc không biết model là gì và không biết bấm vào đâu.
_DICH_THIEU = (
    ("thieu model", "Máy bạn chưa có bộ nghe tiếng ({0}). Bấm “Tải bộ nghe” "
                    "ở trên — tải một lần khoảng 0,5 GB, các lần sau dùng lại."),
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
    import os  # noqa: PLC0415 — chỗ duy nhất trong module cần tới đường dẫn

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
