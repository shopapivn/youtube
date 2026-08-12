"""Phiên viết: đúng thói quen viết kịch bản trên trình duyệt Claude, đem vào tool.

═══ VẤN ĐỀ THẬT ═══

Tab "Viết kịch bản" chạy theo **chuỗi bước đã chốt**: khách nạp template, bấm
chạy, nhận kịch bản. Nó nhanh khi đã biết mình muốn gì. Nhưng lúc còn đang mò —
"viết thử đoạn mở đầu", "đoạn này nhạt quá, kể lại theo hướng khác", "giữ đoạn
hai, viết tiếp phần ba" — thì chuỗi bước cứng không đỡ được: mỗi lần đổi ý là
chạy lại từ đầu, mất luôn thứ vừa nhận.

Đó chính là lối làm việc khách đang có sẵn trên trình duyệt Claude, và họ giữ nó
vì nó hợp: gõ, đọc trả lời, **gõ tiếp dựa trên trả lời đó**, vài vòng thì ra
kịch bản. Module này lo phần lõi của lối đó — nhớ hội thoại, nhớ tệp đính kèm,
lưu ra đĩa, dựng gói tin gửi lên mô hình.

Không Qt, không mạng: mọi luật ở đây (cắt tư liệu, đặt tên file, ghép lịch sử)
đều là chỗ mất dữ liệu hoặc mất tiền của khách nếu sai, nên phải test được thuần.

═══ VÌ SAO LƯU RA ĐĨA ═══

Một phiên viết là **công sức nhiều lượt**: khách chỉnh đi chỉnh lại nửa tiếng mới
ra giọng kể ưng ý. Đóng tool mà mất là mất đúng phần đắt nhất — đắt hơn cả tiền
gọi mô hình, vì tiền thì nạp lại được. Nên phiên nằm ở `<base_dir>/phien-viet/`
dạng JSON: chép sang máy khác được, mở bằng Notepad đọc được.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .mau_kich_ban import ten_file_an_toan
from .xuong_template import TRAN_MOI_FILE, TRAN_TONG_TU_LIEU, cat_bot

__all__ = [
    "TepDinhKem", "TinNhan", "PhienViet", "TuLieuDaGom",
    "THU_MUC", "MA_HOA", "HE_THONG", "SO_TIN_NHO", "TRAN_LICH_SU_GUI",
    "thu_muc_phien", "doc_file_chu", "dinh_kem", "gom_tu_lieu", "ten_tu_cau",
    "dung_tin_gui", "phien_moi", "liet_ke", "luu", "xoa", "so_gon",
]

#: Thư mục chứa phiên, nằm cạnh `config.json` — cùng lối với `mau-kich-ban`.
THU_MUC = "phien-viet"

#: Thứ tự thử khi đọc file .txt, y hệt `ui_qt/trang_voice.py`. File xuất từ Word
#: hay Google Docs trên máy Việt Nam hay là cp1258 hoặc utf-8 có BOM; chết ở khâu
#: đọc là khách đính kèm thấy "0 ký tự" mà không hiểu vì sao.
MA_HOA = ("utf-8-sig", "utf-8", "cp1258", "latin-1")

#: Số tin nhắn một phiên còn nhớ. Tin ở đây dài gấp bội tin của tab Agent (một
#: tin có thể là nguyên bản kịch bản 10 phút), nên nhớ ít lượt hơn mà vẫn nặng
#: ngang. Cắt ở đây chỉ để file phiên không phình vô hạn; phần thật sự quyết định
#: tiền là `TRAN_LICH_SU_GUI` bên dưới.
SO_TIN_NHO = 60

#: Trần ký tự lịch sử được **gửi đi** mỗi lượt.
#:
#: Chat là gửi lại toàn bộ hội thoại mỗi lượt, nên chi phí một phiên dài tăng
#: theo bình phương số lượt. Sau mười lượt qua lại quanh một kịch bản 20.000 ký
#: tự, gửi hết là mỗi câu "sửa giúp câu này" cũng đội lên vài trăm nghìn ký tự.
#: Lấy từ cuối lên vì lượt gần nhất mới là thứ khách đang bàn.
TRAN_LICH_SU_GUI = 60_000

#: Lời hệ thống. Nói rõ đây là bạn viết cùng, KHÔNG phải máy trả bài: chỗ này
#: khách hỏi lại, đổi ý, xin viết lại đoạn ba — trả lời kèm lời dẫn kiểu "Dưới
#: đây là kịch bản của bạn:" mỗi lượt thì lúc bấm "Gửi sang Voice" là máy đọc
#: luôn cả câu dẫn đó.
HE_THONG = (
    "Bạn là người viết kịch bản YouTube, làm việc cùng chủ kênh qua nhiều lượt "
    "trao đổi. Trả lời bằng tiếng Việt.\n"
    "- Bám vào những gì đã nói ở các lượt trước; khách sửa ý nào thì giữ nguyên "
    "phần còn lại, đừng viết lại từ đầu.\n"
    "- Khi được yêu cầu viết kịch bản hoặc một đoạn kịch bản, hãy trả về **đúng "
    "lời đọc**: không tiêu đề mục, không ghi chú quay phim, không markdown, "
    "không câu dẫn kiểu “Dưới đây là…”.\n"
    "- Khi được hỏi ý kiến hay xin gợi ý, cứ trả lời ngắn gọn như người thật."
)


# ── Tệp đính kèm ─────────────────────────────────────────────────────────────


@dataclass
class TepDinhKem:
    """Một file .txt khách đính vào phiên.

    `noi_dung` là phần đã cắt cho vừa trần; `so_chu_goc` giữ độ dài thật để giao
    diện nói được "đã cắt" thay vì âm thầm hiện con số nhỏ hơn khách biết.
    """

    ten: str
    noi_dung: str
    so_chu_goc: int = 0

    def __post_init__(self) -> None:
        if not self.so_chu_goc:
            self.so_chu_goc = len(self.noi_dung)

    @property
    def so_chu(self) -> int:
        return len(self.noi_dung)

    @property
    def da_cat(self) -> bool:
        return self.so_chu_goc > self.so_chu


@dataclass
class TuLieuDaGom:
    """Kết quả gom tư liệu: khối chữ để gửi, và những gì phải nói lại với khách."""

    chu: str = ""
    #: Câu báo cho từng file bị cắt hoặc bị bỏ — giao diện hiện nguyên văn.
    loi_bao: List[str] = field(default_factory=list)


def so_gon(so: int) -> str:
    """Số ký tự viết kiểu Việt Nam: `24.000`, không phải `24,000`.

    >>> so_gon(24000)
    '24.000'
    """
    return "{0:,}".format(int(so)).replace(",", ".")


def doc_file_chu(duong_dan: str) -> str:
    """Đọc file văn bản, thử lần lượt các bảng mã. Không đọc được thì trả rỗng."""
    for ma in MA_HOA:
        try:
            with open(duong_dan, "r", encoding=ma) as tep:
                return tep.read()
        except (UnicodeDecodeError, OSError):
            continue
    return ""


def dinh_kem(duong_dan: str) -> Optional[TepDinhKem]:
    """Đọc một file thành tệp đính kèm. File rỗng hoặc đọc không được thì bỏ.

    **Cắt ngay lúc đính**, không đợi tới lúc gửi: phần vượt trần không bao giờ
    được gửi đi, nên giữ nó trong bộ nhớ và trong file phiên chỉ tổ làm phiên
    của khách nặng lên vô ích.
    """
    chu = doc_file_chu(duong_dan)
    if not chu.strip():
        return None
    return TepDinhKem(ten=os.path.basename(duong_dan) or "tu-lieu.txt",
                      noi_dung=cat_bot(chu, TRAN_MOI_FILE), so_chu_goc=len(chu))


def gom_tu_lieu(tep: Sequence[TepDinhKem]) -> TuLieuDaGom:
    """Gộp tệp đính kèm thành một khối chữ có nhãn, trong trần tổng.

    Có nhãn từng file vì mô hình cần biết đâu là tư liệu tham khảo và đâu là lời
    khách; trộn lẫn là nó viết lại bài của người khác thay vì viết cho khách.

    Cắt thì **phải báo**: khách dán transcript 40 phút vào rồi hỏi "sao nó bỏ
    mất đoạn cuối" — không có dòng báo này thì không ai đoán ra.
    """
    ket = TuLieuDaGom()
    phan: List[str] = []
    con_lai = TRAN_TONG_TU_LIEU
    for mot in tep:
        noi_dung = (mot.noi_dung or "").strip()
        if not noi_dung:
            continue
        if con_lai <= 0:
            ket.loi_bao.append(
                "“{0}” chưa được gửi — đã đầy chỗ tư liệu của lượt này.".format(mot.ten))
            continue
        goc = mot.so_chu_goc or len(noi_dung)
        if len(noi_dung) > con_lai:
            noi_dung = cat_bot(noi_dung, con_lai)
        con_lai -= len(noi_dung)
        if len(noi_dung) < goc:
            ket.loi_bao.append("“{0}”: gửi {1} trong {2} ký tự (phần sau lược bớt).".format(
                mot.ten, so_gon(len(noi_dung)), so_gon(goc)))
        phan.append("TƯ LIỆU THAM KHẢO — {0}:\n{1}".format(mot.ten, noi_dung))
    ket.chu = "\n\n".join(phan)
    return ket


# ── Phiên ────────────────────────────────────────────────────────────────────


@dataclass
class TinNhan:
    vai: str          # "user" hoặc "assistant"
    noi_dung: str


def ten_tu_cau(cau: str, tran: int = 48) -> str:
    """Đặt tên phiên theo câu đầu khách gõ.

    Bắt khách nghĩ tên cho một cuộc trò chuyện *trước khi* trò chuyện là bắt họ
    trả lời một câu hỏi chưa có đáp án. Câu đầu tiên họ gõ đã nói đúng phiên này
    về cái gì rồi.
    """
    gon = " ".join(str(cau or "").split())
    if not gon:
        return "Phiên mới"
    return gon if len(gon) <= tran else gon[:tran].rstrip() + "…"


@dataclass
class PhienViet:
    """Một cuộc viết: tên, hội thoại, tệp đính kèm, và chỗ nằm trên đĩa."""

    ten: str = ""
    tin: List[TinNhan] = field(default_factory=list)
    tep: List[TepDinhKem] = field(default_factory=list)
    #: Mã nhận dạng, sinh một lần rồi theo phiên suốt đời — xem `_duong_dan_moi`.
    ma: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    sua_luc: float = field(default_factory=time.time)
    duong_dan: str = ""

    def them(self, vai: str, noi_dung: str) -> TinNhan:
        """Thêm một tin. Tin đầu của khách cũng là chỗ phiên tự có tên."""
        if vai not in ("user", "assistant"):
            raise ValueError("vai không hợp lệ: {0!r}".format(vai))
        tin = TinNhan(vai, str(noi_dung))
        self.tin.append(tin)
        del self.tin[:-SO_TIN_NHO]
        if not self.ten.strip() and vai == "user":
            self.ten = ten_tu_cau(noi_dung)
        self.sua_luc = time.time()
        return tin

    def bo_tep(self, chi_so: int) -> None:
        if 0 <= chi_so < len(self.tep):
            del self.tep[chi_so]

    @property
    def trong(self) -> bool:
        """Phiên chưa có lượt nào — chưa đáng chiếm một file trên đĩa."""
        return not self.tin

    @property
    def tra_loi_cuoi(self) -> str:
        """Câu trả lời gần nhất của trợ lý — thứ khách lưu .txt hoặc gửi sang Voice."""
        for tin in reversed(self.tin):
            if tin.vai == "assistant":
                return tin.noi_dung
        return ""


def phien_moi() -> PhienViet:
    return PhienViet()


def dung_tin_gui(phien: PhienViet) -> List[Dict[str, str]]:
    """Dựng gói `messages` gửi lên mô hình: hệ thống + tư liệu + cả hội thoại.

    **Gửi cả lịch sử** là toàn bộ điểm của chat — thiếu nó thì mỗi lượt là một
    lần hỏi từ đầu, khách gõ "đoạn hai kể chậm lại" mà mô hình không biết đoạn
    hai là gì.

    Tư liệu đính kèm bám vào **lượt sớm nhất còn được gửi**, không phải lượt mới
    nhất: đó là thứ nền của cả phiên, đọc trước rồi mới tới yêu cầu. Khi lịch sử
    dài quá trần và phần đầu bị cắt đi, tư liệu đi theo lượt sớm nhất còn lại —
    cắt tư liệu ra khỏi gói tin là mô hình quên mất bài của đối thủ ngay giữa
    chừng phiên viết.
    """
    tin = [{"role": "system", "content": HE_THONG}]
    khoi = gom_tu_lieu(phien.tep).chu
    chua_gan = bool(khoi)
    for mot in _lich_su_vua_tran(phien.tin):
        noi_dung = mot.noi_dung
        if chua_gan and mot.vai == "user":
            noi_dung = "{0}\n\n───────────────\n{1}".format(khoi, noi_dung)
            chua_gan = False
        tin.append({"role": mot.vai, "content": noi_dung})
    return tin


def _lich_su_vua_tran(tin: Sequence[TinNhan]) -> List[TinNhan]:
    """Lấy từ cuối lên cho tới khi chạm `TRAN_LICH_SU_GUI`.

    Luôn giữ ít nhất tin cuối cùng: một câu khách vừa gõ dài hơn cả trần vẫn phải
    được gửi, chứ không thể trả về gói tin rỗng rồi báo lỗi khó hiểu.
    """
    lay: List[TinNhan] = []
    con_lai = TRAN_LICH_SU_GUI
    for mot in reversed(tin):
        if lay and len(mot.noi_dung) > con_lai:
            break
        con_lai -= len(mot.noi_dung)
        lay.append(mot)
    lay.reverse()
    return lay


# ── Lưu ra đĩa ───────────────────────────────────────────────────────────────


def thu_muc_phien(base_dir: str) -> str:
    return os.path.join(base_dir, THU_MUC)


def _doc_mot(duong_dan: str) -> Optional[PhienViet]:
    """Đọc một file phiên. Hỏng thì trả None — hỏng một file không được giết cả
    danh sách, vì như thế là khách mất luôn quyền nhìn thấy các phiên còn tốt."""
    try:
        with open(duong_dan, "r", encoding="utf-8") as tep:
            du_lieu = json.load(tep)
    except (OSError, ValueError):
        return None
    if not isinstance(du_lieu, dict):
        return None
    tin = [TinNhan(str(m.get("vai")), str(m.get("noi_dung") or ""))
           for m in _danh_sach(du_lieu.get("tin"))
           if str(m.get("vai")) in ("user", "assistant")]
    if not tin:
        return None
    dinh = [TepDinhKem(str(m.get("ten") or "tu-lieu.txt"), str(m.get("noi_dung") or ""),
                       int(m.get("so_chu_goc") or 0))
            for m in _danh_sach(du_lieu.get("tep"))
            if str(m.get("noi_dung") or "").strip()]
    ten = str(du_lieu.get("ten") or "").strip() or ten_tu_cau(tin[0].noi_dung)
    ma = str(du_lieu.get("ma") or "").strip() or uuid.uuid4().hex[:12]
    try:
        sua_luc = float(du_lieu.get("sua_luc") or 0.0)
    except (TypeError, ValueError):
        sua_luc = 0.0
    return PhienViet(ten=ten, tin=tin[-SO_TIN_NHO:], tep=dinh, ma=ma,
                     sua_luc=sua_luc, duong_dan=duong_dan)


def _danh_sach(gia_tri: Any) -> Iterable[Dict[str, Any]]:
    if not isinstance(gia_tri, list):
        return []
    return [m for m in gia_tri if isinstance(m, dict)]


def liet_ke(base_dir: str) -> List[PhienViet]:
    """Mọi phiên đã lưu, **mới sửa gần nhất đứng đầu** — đó là phiên khách đang làm dở."""
    thu_muc = thu_muc_phien(base_dir)
    try:
        ten_file = sorted(os.listdir(thu_muc))
    except OSError:
        return []
    phien = [p for p in (_doc_mot(os.path.join(thu_muc, ten)) for ten in ten_file
                         if ten.lower().endswith(".json"))
             if p is not None]
    phien.sort(key=lambda p: (-p.sua_luc, p.ten.lower()))
    return phien


def _duong_dan_moi(thu_muc: str, phien: PhienViet) -> str:
    """Chỗ nằm của một phiên trên đĩa, tính từ tên nhưng nhận dạng bằng `ma`.

    Tên phiên do câu đầu của khách sinh ra, nên **hai phiên khác nhau trùng tên
    là chuyện thường**: hôm nay và tuần sau cùng gõ "viết kịch bản về ông Ba".
    Rút gọn xong thì hai cái ra chung một slug — ghi đè ở đây là xoá sổ nửa
    tiếng làm việc của khách mà không báo một tiếng.

    Nên slug chỉ là *chỗ ưu tiên*, còn quyền vào file thuộc về `ma`: slug đã có
    chủ khác thì tách sang `-2`, `-3`. Cùng `ma` mới được ghi đè, và đó đúng là
    thứ ta muốn — mỗi lượt chat là ghi đè chính phiên đó.
    """
    goc = ten_file_an_toan(phien.ten or "phien-viet")
    for lan in range(0, 100):
        ten_file = goc if lan == 0 else "{0}-{1}".format(goc, lan + 1)
        duong_dan = os.path.join(thu_muc, ten_file + ".json")
        if not os.path.exists(duong_dan):
            return duong_dan
        da_co = _doc_mot(duong_dan)
        if da_co is None or da_co.ma == phien.ma:
            return duong_dan
    return os.path.join(thu_muc, "{0}-{1}.json".format(goc, phien.ma))


def luu(base_dir: str, phien: PhienViet) -> str:
    """Ghi phiên ra đĩa, trả về đường dẫn. Đổi tên thì file cũ được dọn đi.

    Ghi qua file tạm rồi `os.replace`: mất điện hay tool bị tắt ngang giữa lúc
    ghi thì phiên cũ còn nguyên, thay vì thành một file JSON cụt đọc không ra.
    """
    thu_muc = thu_muc_phien(base_dir)
    os.makedirs(thu_muc, exist_ok=True)
    if not phien.ten.strip():
        phien.ten = ten_tu_cau(phien.tin[0].noi_dung if phien.tin else "")
    duong_dan = _duong_dan_moi(thu_muc, phien)
    du_lieu = {
        "version": 1, "ma": phien.ma, "ten": phien.ten, "sua_luc": phien.sua_luc,
        "tin": [{"vai": t.vai, "noi_dung": t.noi_dung} for t in phien.tin[-SO_TIN_NHO:]],
        "tep": [{"ten": t.ten, "noi_dung": t.noi_dung, "so_chu_goc": t.so_chu_goc}
                for t in phien.tep],
    }
    tam = duong_dan + ".tmp"
    with open(tam, "w", encoding="utf-8") as tep:
        json.dump(du_lieu, tep, ensure_ascii=False, indent=2)
        tep.write("\n")
    os.replace(tam, duong_dan)
    cu = phien.duong_dan
    phien.duong_dan = duong_dan
    if cu and cu != duong_dan:
        # Khách đổi tên phiên: để lại file cũ là danh sách có hai phiên y hệt
        # nhau, và lần mở sau không biết cái nào mới.
        try:
            os.remove(cu)
        except OSError:
            pass
    return duong_dan


def xoa(phien: PhienViet) -> bool:
    """Xoá phiên khỏi đĩa. Phiên chưa từng lưu thì coi như đã xong."""
    if not phien.duong_dan:
        return True
    try:
        os.remove(phien.duong_dan)
    except OSError:
        return False
    phien.duong_dan = ""
    return True
