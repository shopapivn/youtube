"""Sổ đăng ký **kênh** — thứ mà luồng AUTO đọc để biết phải làm ra cái gì.

═══ MỘT KÊNH LÀ MỘT THƯ MỤC ═══

Toàn bộ "tính cách" của một kênh nằm trong `CHANNEL/<mã kênh>/`, không nằm rải
rác trong mã nguồn:

    CHANNEL/TL1-T1/
      kenh.yaml        ai xem, tiếng gì, dài bao nhiêu, giọng nào, engine nào
      style.yaml       nhìn như thế nào — màu, nét vẽ, đạo cụ, bối cảnh văn hoá
      nv/nv1.png       nhân vật tham chiếu; mọi ảnh sinh ra phải giống người này
      prompt/          chuỗi lời nhắc 1→7, chạy lần lượt để ra kịch bản và cảnh

Người dùng thêm kênh mới bằng cách **chép một thư mục rồi sửa chữ trong đó** —
không phải sửa code, không phải nhờ ai. Đó là điều kiện để luồng AUTO thật sự
tự chạy được với 10 kênh chứ không phải một kênh.

═══ TUYỆT ĐỐI KHÔNG CÓ KHOÁ TRONG THƯ MỤC KÊNH ═══

Mấy tool cũ để khoá sống ngay trong tệp cấu hình của từng dự án — khoá router,
khoá tài khoản đọc giọng, cả kho tài khoản. Chép nguyên nết ấy sang đây là một
ngày nào đó người dùng gửi thư mục kênh cho người khác dùng chung và cho luôn
cái ví.

Nên `kiem_kenh()` **quét và từ chối** mọi tệp cấu hình kênh có mùi khoá. Tiền
trong luồng AUTO đi qua đúng một cửa: ví ShopAPI mà tool đã đăng nhập sẵn.

Module thuần tuý: không mạng, không giao diện. Chỉ đọc và kiểm thư mục.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = [
    "THU_MUC_KENH", "TEP_KENH", "TEP_STYLE", "BUOC_PROMPT",
    "Kenh", "duong_kenh", "liet_ke_kenh", "doc_kenh", "kiem_kenh",
    "doc_yaml", "co_mui_khoa",
]

#: Thư mục chứa mọi kênh, nằm cạnh `shopapi_studio_qt.py`.
THU_MUC_KENH = "CHANNEL"

TEP_KENH = "kenh.yaml"
TEP_STYLE = "style.yaml"
THU_MUC_NV = "nv"
THU_MUC_PROMPT = "prompt"

#: Chuỗi bước làm kịch bản, chạy **đúng thứ tự này**. Tên tệp bắt đầu bằng số vì
#: người dùng phải nhìn thư mục là biết cái nào chạy trước — họ sẽ sửa mấy tệp
#: này thường xuyên hơn sửa bất cứ thứ gì khác trong tool.
#:
#: Bảy bước chép theo dây chuyền đã chạy thật ở `D:\\CONTENT` (title_thumb →
#: write_oneshot → check_fix → adapt → review → seo), cộng thêm bước 7 mà tool
#: cũ để ở nơi khác: viết lời nhắc tạo ảnh/clip cho từng cảnh.
BUOC_PROMPT = (
    ("1-tieu-de.md", "Đặt tiêu đề và chữ trên ảnh bìa"),
    ("2-viet.md", "Viết kịch bản lời đọc"),
    ("3-sua.md", "Đối chiếu và sửa chỗ hụt"),
    ("4-do-dai.md", "Nắn cho đúng độ dài"),
    ("5-hoan-thien.md", "Đọc lại lần cuối cho mượt"),
    ("6-seo.md", "Mô tả, hashtag, từ khoá"),
    ("7-canh.md", "Chia cảnh theo nghĩa, viết lời nhắc ảnh và clip"),
    ("8-thumbnail.md", "Viết lời nhắc ba ảnh bìa"),
    ("9-nhac.md", "Viết lời nhắc nhạc nền"),
)

#: Bước bắt buộc phải có thì luồng AUTO mới chạy nổi. Bước 6 (SEO) thiếu thì vẫn
#: ra được video, chỉ là không có sẵn phần mô tả để dán lên YouTube.
BUOC_BAT_BUOC = ("2-viet.md", "7-canh.md")


@dataclass
class Kenh:
    """Một kênh đã đọc xong từ đĩa."""

    ma: str = ""
    ten: str = ""
    #: Mã ngôn ngữ ISO ngắn: `es`, `vi`, `en`…
    ngon_ngu: str = ""
    #: Tên ngôn ngữ viết cho AI đọc: "Spanish — natural, second person (tú)".
    giong_van: str = ""
    #: Độ dài video nhắm tới, tính bằng phút.
    phut_muc_tieu: float = 10.0
    #: Số ký tự đọc được trong một phút của tiếng này. Dùng để quy phút → ký tự
    #: cho bước nắn độ dài. Đo từ giọng thật, không đoán.
    ky_tu_moi_phut: int = 900
    #: Mã giọng đọc trên cổng ShopAPI.
    voice_id: str = ""
    #: Engine dựng clip — quyết định trần độ dài mỗi cảnh (veo3 8s, seedance 10s).
    engine: str = "veo3"
    #: Mô hình AI viết kịch bản và lời nhắc.
    mo_hinh: str = "claude-sonnet-5"
    #: Chữ hoa cho chữ trên ảnh bìa hay không. Tiếng Nhật/Hàn không có chữ hoa
    #: nên kênh tiếng ấy phải để `false`, viết hoa là ra chữ hỏng.
    chu_bia_hoa: bool = True
    #: Số ảnh bìa sinh ra để người dùng chọn. Tool cũ làm 3 bản khác kiểu nhau
    #: (chân dung, cảnh kịch tính…) rồi người chọn tay — giữ nguyên nết đó.
    so_thumbnail: int = 3

    # ── Cách dựng video, cài một lần cho cả kênh ─────────────────────────────
    #
    # Chủ dự án, 14/08/2026: *"các vấn đề về edit có thể có template"*.
    #
    # Đây là những thứ mọi video của một kênh làm giống hệt nhau, nên hỏi từng
    # lượt là hỏi thừa. Cài ở kênh một lần rồi thôi.

    #: Đốt phụ đề thẳng vào hình hay không.
    #:
    #: `True` hợp với kênh đăng lên Facebook/TikTok — chỗ người xem tắt tiếng
    #: và phụ đề rời không hiện. `False` hợp với kênh chỉ đăng YouTube: tải tệp
    #: `.srt` lên riêng thì người xem bật/tắt được, đổi cỡ chữ được, và YouTube
    #: đọc được nội dung để đề xuất video — chữ đốt vào hình thì nó mù.
    dot_phu_de: bool = True

    #: Tệp nhạc nền, đường dẫn tính từ thư mục kênh (ví dụ `nhac/nen.mp3`).
    #:
    #: Rỗng = không có nhạc. Cổng ShopAPI **không bán nhạc**, nên đây phải là
    #: tệp khách tự có — mua, tải từ kho miễn phí bản quyền, hoặc tự làm. Tool
    #: không đi tải nhạc ở đâu về hộ: nhạc dính bản quyền là kênh ăn gậy, và
    #: đó là thứ tool không được phép quyết thay người.
    nhac_nen: str = ""

    #: Nhạc nhỏ hơn giọng đọc bao nhiêu lần. 0.12 = nhạc còn 12% độ to.
    #:
    #: Nghe thì thấy nhỏ quá, nhưng đây là mức người dựng phim hay dùng cho
    #: video có người nói suốt: nhạc để **lấp khoảng lặng**, không để nghe. To
    #: hơn 0.2 là người xem bắt đầu phải căng tai nghe lời.
    am_luong_nhac: float = 0.12

    #: Toàn bộ `style.yaml`, giữ nguyên để đưa thẳng cho bước viết lời nhắc.
    style: Dict[str, Any] = field(default_factory=dict)
    #: Đường dẫn ảnh nhân vật tham chiếu (thường là `nv/nv1.png`).
    anh_nv: List[str] = field(default_factory=list)
    #: Nội dung từng bước lời nhắc, khoá là tên tệp.
    prompt: Dict[str, str] = field(default_factory=dict)

    duong: str = ""

    @property
    def ky_tu_muc_tieu(self) -> int:
        """Số ký tự kịch bản cần có để đọc ra đúng `phut_muc_tieu`."""
        return int(round(self.phut_muc_tieu * max(1, self.ky_tu_moi_phut)))

    @property
    def ten_hien(self) -> str:
        return self.ten or self.ma


def duong_kenh(goc: str, ma: str = "") -> str:
    thu_muc = os.path.join(goc, THU_MUC_KENH)
    return os.path.join(thu_muc, ma) if ma else thu_muc


def liet_ke_kenh(goc: str) -> List[str]:
    """Tên các kênh đang có, xếp theo bảng chữ cái.

    Thư mục bắt đầu bằng `_` hoặc `.` bị bỏ qua — chỗ để người dùng cất bản
    nháp và bản mẫu mà không hiện ra trên giao diện.
    """
    thu_muc = duong_kenh(goc)
    try:
        muc = os.listdir(thu_muc)
    except OSError:
        return []
    ra = [t for t in muc
          if not t.startswith((".", "_"))
          and os.path.isfile(os.path.join(thu_muc, t, TEP_KENH))]
    return sorted(ra)


# ── Đọc YAML mà không bắt khách cài thêm gì ──────────────────────────────────


def doc_yaml(duong: str) -> Dict[str, Any]:
    """Đọc một tệp YAML đơn giản. Không có tệp thì trả về `{}`.

    Dùng `PyYAML` nếu máy có; không có thì rơi về bộ đọc tối giản ở dưới. Lý do
    không bắt buộc `PyYAML`: `requirements.txt` của tool là thứ khách chạy một
    lần lúc cài, và mỗi dòng thêm vào đó là một cửa nữa để hỏng trên máy lạ.
    Tệp cấu hình kênh chỉ dùng `khoá: giá trị` và danh sách gạch đầu dòng — bộ
    đọc tối giản đủ dùng, còn ai đã có `PyYAML` thì được bản đầy đủ.
    """
    try:
        with open(duong, "r", encoding="utf-8") as tep:
            tho = tep.read()
    except OSError:
        return {}
    try:
        import yaml  # noqa: PLC0415

        gia_tri = yaml.safe_load(tho)
        return gia_tri if isinstance(gia_tri, dict) else {}
    except ImportError:
        return _yaml_toi_gian(tho)
    except Exception:  # noqa: BLE001 — YAML hỏng thì thử bộ đọc thô
        return _yaml_toi_gian(tho)


def _yaml_toi_gian(tho: str) -> Dict[str, Any]:
    """Bộ đọc YAML đủ cho `kenh.yaml`: `khoá: giá trị` và danh sách `- mục`."""
    ra: Dict[str, Any] = {}
    khoa_hien: Optional[str] = None
    for dong in tho.splitlines():
        if not dong.strip() or dong.lstrip().startswith("#"):
            continue
        if dong.startswith((" ", "\t")) and dong.strip().startswith("- "):
            if khoa_hien:
                ra.setdefault(khoa_hien, [])
                if isinstance(ra[khoa_hien], list):
                    ra[khoa_hien].append(_go_nhay(dong.strip()[2:]))
            continue
        if dong.strip().startswith("- "):
            continue
        if ":" not in dong:
            continue
        khoa, _, gia_tri = dong.partition(":")
        khoa = khoa.strip()
        gia_tri = gia_tri.strip()
        khoa_hien = khoa
        ra[khoa] = _go_nhay(gia_tri) if gia_tri else ""
    return ra


def _go_nhay(chu: str) -> Any:
    chu = chu.strip()
    if len(chu) >= 2 and chu[0] == chu[-1] and chu[0] in "'\"":
        return chu[1:-1]
    thap = chu.lower()
    if thap in ("true", "yes"):
        return True
    if thap in ("false", "no"):
        return False
    try:
        return int(chu)
    except ValueError:
        pass
    try:
        return float(chu)
    except ValueError:
        return chu


# ── Đọc một kênh ─────────────────────────────────────────────────────────────


def doc_kenh(goc: str, ma: str) -> Kenh:
    """Đọc trọn một kênh từ đĩa. Không ném lỗi — thiếu gì thì `kiem_kenh` nói.

    Cố ý **không** ném khi thiếu tệp: giao diện cần dựng được danh sách kênh kể
    cả khi một kênh làm dở, để nói cho người dùng biết kênh nào thiếu gì. Ném ở
    đây thì cả tab trắng vì một thư mục hỏng.
    """
    thu_muc = duong_kenh(goc, ma)
    cai = doc_yaml(os.path.join(thu_muc, TEP_KENH))
    kenh = Kenh(
        ma=str(cai.get("ma") or ma),
        ten=str(cai.get("ten") or ""),
        ngon_ngu=str(cai.get("ngon_ngu") or ""),
        giong_van=str(cai.get("giong_van") or ""),
        phut_muc_tieu=_so(cai.get("phut_muc_tieu"), 10.0),
        ky_tu_moi_phut=int(_so(cai.get("ky_tu_moi_phut"), 900)),
        voice_id=str(cai.get("voice_id") or ""),
        engine=str(cai.get("engine") or "veo3"),
        mo_hinh=str(cai.get("mo_hinh") or "claude-sonnet-5"),
        chu_bia_hoa=bool(cai.get("chu_bia_hoa", True)),
        so_thumbnail=max(1, int(_so(cai.get("so_thumbnail"), 3))),
        dot_phu_de=bool(cai.get("dot_phu_de", True)),
        nhac_nen=str(cai.get("nhac_nen") or ""),
        # Kẹp trong 0..1. Số âm làm FFmpeg đảo pha, số lớn hơn 1 làm nhạc át
        # hẳn giọng đọc — cả hai đều là gõ nhầm chứ không ai cố ý.
        am_luong_nhac=min(1.0, max(0.0, _so(cai.get("am_luong_nhac"), 0.12))),
        style=doc_yaml(os.path.join(thu_muc, TEP_STYLE)),
        duong=thu_muc,
    )
    kenh.anh_nv = _anh_trong(os.path.join(thu_muc, THU_MUC_NV))
    kenh.prompt = _doc_prompt(os.path.join(thu_muc, THU_MUC_PROMPT))
    return kenh


def _so(gia_tri, mac_dinh: float) -> float:
    try:
        return float(gia_tri)
    except (TypeError, ValueError):
        return mac_dinh


def _anh_trong(thu_muc: str) -> List[str]:
    try:
        muc = sorted(os.listdir(thu_muc))
    except OSError:
        return []
    duoi = (".png", ".jpg", ".jpeg", ".webp")
    return [os.path.join(thu_muc, t) for t in muc if t.lower().endswith(duoi)]


def _doc_prompt(thu_muc: str) -> Dict[str, str]:
    ra: Dict[str, str] = {}
    for ten, _mo_ta in BUOC_PROMPT:
        try:
            with open(os.path.join(thu_muc, ten), "r", encoding="utf-8") as tep:
                ra[ten] = tep.read()
        except OSError:
            continue
    return ra


# ── Kiểm kênh, và chặn khoá lọt vào ──────────────────────────────────────────

#: Dấu vết khoá thật. Bắt theo **hình dạng khoá**, không bắt theo tên khoá: đặt
#: tên là `abc` mà giá trị là `sk-...` thì vẫn là khoá.
_DAU_VET_KHOA = re.compile(
    r"(sk-[A-Za-z0-9_\-]{16,}"
    r"|sk_[A-Za-z0-9]{16,}"
    r"|wk_[A-Za-z0-9]{16,}"
    r"|AIza[A-Za-z0-9_\-]{20,}"
    r"|ya29\.[A-Za-z0-9_\-]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)


def co_mui_khoa(chu: str) -> str:
    """Trả về đoạn khớp đầu tiên nếu chuỗi có vẻ chứa khoá, rỗng nếu sạch."""
    khop = _DAU_VET_KHOA.search(chu or "")
    return khop.group(0)[:12] + "…" if khop else ""


def kiem_kenh(kenh: Kenh) -> List[str]:
    """Kênh này còn thiếu gì. Rỗng nghĩa là chạy được.

    Mỗi câu phải nói **thiếu gì và sửa ở đâu** — người đọc nó là người không
    biết lập trình, đang nhìn một thư mục họ tự chép ra.
    """
    thieu: List[str] = []
    if not kenh.ma:
        thieu.append("Thiếu mã kênh — thêm dòng `ma:` vào {0}.".format(TEP_KENH))
    if not kenh.ngon_ngu:
        thieu.append("Chưa biết kênh nói tiếng gì — thêm `ngon_ngu:` vào {0} "
                     "(ví dụ `es`, `vi`, `en`).".format(TEP_KENH))
    if not kenh.voice_id:
        thieu.append("Chưa chọn giọng đọc — thêm `voice_id:` vào {0}. Mã giọng "
                     "lấy ở tab Voice.".format(TEP_KENH))
    if not kenh.anh_nv:
        thieu.append("Chưa có ảnh nhân vật tham chiếu — bỏ một tệp .png vào "
                     "thư mục `{0}/`. Thiếu nó thì mỗi cảnh ra một nhân vật "
                     "khác nhau.".format(THU_MUC_NV))
    if not kenh.style.get("image_style"):
        thieu.append("Chưa tả kênh nhìn như thế nào — thêm `image_style:` vào "
                     "{0}.".format(TEP_STYLE))
    for ten in BUOC_BAT_BUOC:
        if not (kenh.prompt.get(ten) or "").strip():
            mo_ta = dict(BUOC_PROMPT).get(ten, ten)
            thieu.append("Thiếu bước “{0}” — tạo tệp `{1}/{2}`.".format(
                mo_ta, THU_MUC_PROMPT, ten))

    # ═══ CHẶN KHOÁ ═══
    #
    # Quét cả cấu hình lẫn lời nhắc: người dùng chép thư mục kênh từ tool cũ
    # sang thì rất dễ mang theo cả dòng khoá router nằm trong đó.
    for ten, noi_dung in [(TEP_KENH, _tho(kenh.duong, TEP_KENH)),
                          (TEP_STYLE, _tho(kenh.duong, TEP_STYLE))] \
            + [("{0}/{1}".format(THU_MUC_PROMPT, k), v)
               for k, v in sorted(kenh.prompt.items())]:
        dau = co_mui_khoa(noi_dung)
        if dau:
            thieu.append(
                "Tệp `{0}` có vẻ chứa một khoá API ({1}). Xoá dòng đó đi — "
                "luồng AUTO dùng ví ShopAPI của tool, kênh không cần khoá "
                "riêng, và để khoá ở đây là ai cầm thư mục kênh cũng tiêu được "
                "tiền của bạn.".format(ten, dau))
    return thieu


def _tho(thu_muc: str, ten: str) -> str:
    try:
        with open(os.path.join(thu_muc, ten), "r", encoding="utf-8") as tep:
            return tep.read()
    except OSError:
        return ""
