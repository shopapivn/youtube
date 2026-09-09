"""Hàng đợi NHIỀU lượt chạy của tab Tự động — chạy lần lượt hay vài lượt cùng lúc.

═══ VÌ SAO CÓ ═══

Chủ dự án, 09/09/2026: *"lúc trước để sản xuất thì mở nhiều tool, nhưng giờ
giới hạn không mở nhiều nên tao muốn có logic có thể sản xuất nhiều content —
chạy song song hoặc chạy lần lượt"*.

Từ 07/09/2026 tool chỉ cho mở MỘT bản (khoá `.dang-mo.lock`, xem
`shopapi_studio_qt.py`) vì hai bản cùng chiếm cổng nhận 8765 và máy ảo gọi về
nhầm bản. Cách cũ "mỗi video một cửa sổ tool" vì thế không còn. Tab Tự động thì
chỉ giữ đúng một lượt trong `_dang_chay` — có video thứ hai là phải ngồi đợi
video thứ nhất xong rồi mới dán link tiếp.

Mô-đun này là chỗ thay cho "mở nhiều tool": một danh sách lượt, mỗi lượt là một
thư mục `PROJECTS/AUTO/<kênh>/<lượt>/` đã có sẵn tệp trạng thái, và một con số
"chạy bao nhiêu cùng lúc". Số 1 là chạy lần lượt.

═══ KHÔNG BIẾT CHẠY MỘT LƯỢT NHƯ THẾ NÀO ═══

Cũng như `core/auto.py`, đây chỉ là thứ tự và trạng thái. Việc *khởi chạy một
lượt* được truyền vào (`khoi_chay`), và bên ấy phải gọi `bao_xong` khi lượt kết
thúc — xong, hỏng hay bị dừng. Nhờ vậy luật "hết chỗ thì chờ, trống chỗ thì
nạp tiếp, một lượt hỏng không chặn lượt sau" kiểm được bằng lượt giả, không
tốn tiền và không cần cửa sổ.

═══ HAI LƯỢT CÙNG LÚC THÌ GIẪM NHAU Ở ĐÂU ═══

Phần gọi máy chủ (viết chữ, giọng đọc, ảnh, clip) chạy song song được: cổng
tính trần theo tài khoản, hai lượt cùng bắn thì mỗi lượt chậm đi chứ không hỏng,
và van nhịp gọi (`core/su_co.NHIP`) là van toàn tiến trình nên hai lượt vẫn
chung một nhịp hỏi máy chủ.

Phần chạy TRÊN MÁY thì không:

* khâu phụ đề nạp mô hình Whisper vào RAM — hai bản cùng lúc trên máy 8 GB là
  hết bộ nhớ;
* khâu dựng mở FFmpeg ăn hết CPU — hai bản là cả hai cùng chậm gấp đôi, không
  nhanh hơn chạy nối tiếp một giây nào;
* đuôi CapCut của khâu dựng **bấm chuột thật** trên màn hình (`core/capcut.py`)
  — hai bản cùng bấm là bấm loạn vào cửa sổ của nhau.

Nên `khoa_khau_may` bọc các khâu ấy bằng MỘT khoá chung cho cả tiến trình: lượt
nào tới khâu đó trước thì làm, lượt sau đợi, và trong lúc đợi vẫn bấm Dừng
được. Máy chủ thì vẫn được cả hai lượt dùng song song.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .auto import Cancelled
from .ghi_dia import ghi_json

__all__ = [
    "CHO", "DANG", "XONG", "HONG", "DUNG", "CHU_TRANG_THAI",
    "SO_SONG_SONG_TOI_DA", "KHAU_TREN_MAY", "MucDoi", "HangDoiAuto",
    "khoa_khau_may", "duong_tep",
]

# ── Trạng thái một mục trong hàng đợi ────────────────────────────────────────
#
# Khác với trạng thái KHÂU trong `core/auto.py`: đây là trạng thái của cả lượt
# nhìn từ hàng đợi. Lượt "dừng" (`DUNG`) là lượt kết thúc mà chưa xong hết —
# người bấm Dừng, hoặc chạy tới chốt "dừng để xem". Nó không hỏng, và bấm
# "Chạy tiếp" là xếp lại vào hàng.

CHO = "cho"
DANG = "dang"
XONG = "xong"
HONG = "hong"
DUNG = "dung"

CHU_TRANG_THAI = {
    CHO: "chờ", DANG: "ĐANG CHẠY", XONG: "xong", HONG: "HỎNG", DUNG: "dừng",
}

#: Nhiều nhất bao nhiêu lượt cùng lúc. Ba là đủ: mỗi lượt đã tự bắn cả trăm
#: cảnh song song lên máy chủ, ba lượt là ba trăm việc đang bay — hơn nữa thì
#: chỉ xếp hàng ở cổng, không nhanh hơn.
SO_SONG_SONG_TOI_DA = 3

#: Tên tệp nhớ hàng đợi, nằm trong `workspace/` cùng chỗ với cài đặt. Không
#: đặt trong `PROJECTS/` — đó là chỗ của kết quả khách, không phải sổ sách tool.
TEN_TEP = "auto-hang-doi.json"

#: Các khâu chạy trên máy này, chỉ được MỘT lượt làm tại một thời điểm.
KHAU_TREN_MAY = ("phu-de", "dung")


def duong_tep(goc: str) -> str:
    return os.path.join(goc, "workspace", TEN_TEP)


@dataclass
class MucDoi:
    """Một lượt nằm trong hàng đợi."""

    #: Thư mục lượt — chính là `LuotChay.thu_muc`, và là khoá nhận dạng.
    thu_muc: str
    ma_kenh: str = ""
    ma_luot: str = ""
    #: Chạy tới hết khâu này rồi dừng (xem `core/auto.chay`). Rỗng = chạy hết.
    dung_sau: str = ""
    #: Ô "Xuất lại qua CapCut" lúc xếp vào hàng — mỗi lượt nhớ riêng, vì ô
    #: trên màn hình có thể đã đổi lúc lượt này tới lượt chạy.
    xuat_capcut: bool = False
    #: Một dòng cho người đọc: tiêu đề, hay link, hay "nội dung dán".
    mo_ta: str = ""
    trang_thai: str = CHO
    loi: str = ""
    #: Cờ dừng RIÊNG của lượt này — bấm Dừng một lượt không đụng lượt khác.
    huy: threading.Event = field(default_factory=threading.Event,
                                 repr=False, compare=False)

    @property
    def con_viec(self) -> bool:
        """Còn nằm trong hàng (chờ hoặc đang chạy)."""
        return self.trang_thai in (CHO, DANG)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thu_muc": self.thu_muc, "ma_kenh": self.ma_kenh,
            "ma_luot": self.ma_luot, "dung_sau": self.dung_sau,
            "xuat_capcut": bool(self.xuat_capcut), "mo_ta": self.mo_ta,
            "trang_thai": self.trang_thai, "loi": self.loi,
        }

    @classmethod
    def from_dict(cls, goi: Dict[str, Any]) -> "MucDoi":
        tt = str(goi.get("trang_thai") or CHO)
        # Mở lại tool mà còn mục "đang chạy" thì lần trước bị tắt giữa chừng.
        # Trả nó về "chờ": bấm "Chạy hàng đợi" là nhặt tiếp đúng khâu dở, vì
        # trạng thái thật của từng khâu nằm ở `trang-thai.json` của lượt.
        if tt == DANG or tt not in CHU_TRANG_THAI:
            tt = CHO
        return cls(
            thu_muc=str(goi.get("thu_muc") or ""),
            ma_kenh=str(goi.get("ma_kenh") or ""),
            ma_luot=str(goi.get("ma_luot") or ""),
            dung_sau=str(goi.get("dung_sau") or ""),
            xuat_capcut=bool(goi.get("xuat_capcut")),
            mo_ta=str(goi.get("mo_ta") or ""),
            trang_thai=tt,
            loi=str(goi.get("loi") or "") if tt != CHO else "",
        )


class HangDoiAuto:
    """Danh sách lượt + con số "bao nhiêu cùng lúc" + luật nạp tiếp.

    `khoi_chay(muc)` phải **trả về ngay** (chạy nền), và khi lượt kết thúc phải
    gọi `bao_xong(muc, ...)`. Mọi lời gọi ngược (`on_doi`, `on_het`) đều được
    phát **ngoài khoá**, nên bên nhận gọi lại vào hàng đợi cũng không kẹt.

    Hàng đợi có hai trạng thái: **mở** (trống chỗ là nạp mục chờ vào chạy) và
    **đóng** (mục chờ cứ nằm đó). Bấm "Chạy" là mở; bấm "Dừng tất cả" là đóng
    và gạt cờ dừng của mọi lượt đang chạy; hết việc thì tự đóng.
    """

    def __init__(self, khoi_chay: Callable[[MucDoi], None], *,
                 so_song_song: int = 1,
                 on_doi: Optional[Callable[[], None]] = None,
                 on_het: Optional[Callable[[List[MucDoi]], None]] = None) -> None:
        self._khoi_chay = khoi_chay
        self._ds: List[MucDoi] = []
        self._so = self._kep(so_song_song)
        self._mo = False
        self._khoa = threading.RLock()
        self._on_doi = on_doi
        self._on_het = on_het
        #: Những mục đã chạy trong ĐỢT này (từ lần mở gần nhất) — để lúc hết
        #: việc nói được "xong 3, hỏng 1" thay vì chỉ "xong".
        self._dot: List[MucDoi] = []

    # ── Đọc ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _kep(n: Any) -> int:
        try:
            n = int(n)
        except (TypeError, ValueError):
            n = 1
        return max(1, min(SO_SONG_SONG_TOI_DA, n))

    @property
    def ds(self) -> List[MucDoi]:
        with self._khoa:
            return list(self._ds)

    @property
    def so_song_song(self) -> int:
        return self._so

    @property
    def dang_mo(self) -> bool:
        return self._mo

    @property
    def so_dang(self) -> int:
        with self._khoa:
            return sum(1 for m in self._ds if m.trang_thai == DANG)

    @property
    def so_cho(self) -> int:
        with self._khoa:
            return sum(1 for m in self._ds if m.trang_thai == CHO)

    @property
    def co_viec_dang_chay(self) -> bool:
        return self.so_dang > 0

    def tim(self, thu_muc: str) -> Optional[MucDoi]:
        thu_muc = _chuan(thu_muc)
        with self._khoa:
            for m in self._ds:
                if _chuan(m.thu_muc) == thu_muc:
                    return m
        return None

    def dang_chay(self, thu_muc: str) -> bool:
        m = self.tim(thu_muc)
        return m is not None and m.trang_thai == DANG

    def con_viec(self, thu_muc: str) -> bool:
        """Lượt này còn nằm trong hàng (chờ hay đang chạy)?"""
        m = self.tim(thu_muc)
        return m is not None and m.con_viec

    def vi_tri_cho(self, thu_muc: str) -> int:
        """Đứng thứ mấy trong số mục CHỜ (1 = kế tiếp). 0 = không chờ."""
        thu_muc = _chuan(thu_muc)
        with self._khoa:
            i = 0
            for m in self._ds:
                if m.trang_thai != CHO:
                    continue
                i += 1
                if _chuan(m.thu_muc) == thu_muc:
                    return i
        return 0

    # ── Sửa ──────────────────────────────────────────────────────────────────

    def dat_so_song_song(self, n: int) -> int:
        """Đổi số chạy cùng lúc. Đang mở mà nới ra thì nạp thêm ngay; thu lại
        thì lượt đang chạy vẫn chạy hết, chỉ không nạp mới."""
        self._so = self._kep(n)
        self._nap_them()
        return self._so

    def them(self, muc: MucDoi, *, uu_tien: bool = False) -> MucDoi:
        """Xếp một lượt vào hàng. Trả về mục thật sự nằm trong hàng.

        Cùng thư mục mà đã có mục chờ/đang chạy thì **không thêm bản thứ hai**
        — chạy một lượt hai lần cùng lúc là hai luồng cùng ghi một
        `trang-thai.json`. Mục cũ đã xong/hỏng/dừng thì dùng lại chính nó: đặt
        về chờ, cập nhật chốt dừng và cờ CapCut theo lần xếp mới.

        `uu_tien=True` xếp lên **đầu** hàng chờ — cho "Chạy tiếp" và "Tạo lại
        cảnh": người vừa sửa xong đang đợi đúng lượt ấy, không phải đợi ba
        video khác chạy xong trước.
        """
        with self._khoa:
            cu = self.tim(muc.thu_muc)
            if cu is not None:
                if cu.con_viec:
                    return cu
                self._ds.remove(cu)
                cu.trang_thai = CHO
                cu.loi = ""
                cu.dung_sau = muc.dung_sau
                cu.xuat_capcut = muc.xuat_capcut
                if muc.mo_ta:
                    cu.mo_ta = muc.mo_ta
                cu.huy.clear()
                muc = cu
            muc.trang_thai = CHO
            muc.huy.clear()
            if uu_tien:
                # Lên trước mọi mục CHỜ, nhưng sau các mục đã xong/đang chạy
                # để bảng vẫn đọc theo thứ tự thời gian.
                vi_tri = len(self._ds)
                for i, m in enumerate(self._ds):
                    if m.trang_thai == CHO:
                        vi_tri = i
                        break
                self._ds.insert(vi_tri, muc)
            else:
                self._ds.append(muc)
        self._bao_doi()
        self._nap_them()
        return muc

    def bo(self, thu_muc: str) -> bool:
        """Bỏ một mục khỏi hàng. Mục đang chạy thì **không** — phải Dừng trước."""
        with self._khoa:
            m = self.tim(thu_muc)
            if m is None or m.trang_thai == DANG:
                return False
            self._ds.remove(m)
        self._bao_doi()
        return True

    def don_xong(self) -> int:
        """Bỏ mọi mục đã xong khỏi bảng. Trả về số mục đã bỏ."""
        with self._khoa:
            truoc = len(self._ds)
            self._ds = [m for m in self._ds if m.trang_thai != XONG]
            bo = truoc - len(self._ds)
        if bo:
            self._bao_doi()
        return bo

    def mo(self) -> None:
        """Mở hàng: trống chỗ là nạp mục chờ vào chạy."""
        with self._khoa:
            if not self._mo and self.so_dang == 0:
                self._dot = []
            self._mo = True
        self._nap_them()

    def dung_tat_ca(self) -> None:
        """Đóng hàng và gạt cờ dừng của mọi lượt đang chạy. Mục chờ nằm yên."""
        with self._khoa:
            self._mo = False
            dang = [m for m in self._ds if m.trang_thai == DANG]
        for m in dang:
            m.huy.set()
        self._bao_doi()

    def dung_mot(self, thu_muc: str) -> bool:
        """Gạt cờ dừng của đúng một lượt đang chạy. Hàng vẫn mở: lượt kế tiếp
        vẫn được nạp khi lượt này thoát."""
        m = self.tim(thu_muc)
        if m is None or m.trang_thai != DANG:
            return False
        m.huy.set()
        return True

    def bao_xong(self, muc: MucDoi, *, loi: str = "", dung: bool = False) -> None:
        """Bên chạy gọi khi lượt kết thúc. `dung=True` = còn dở nhưng không hỏng
        (người bấm Dừng, hoặc tới chốt "dừng để xem")."""
        with self._khoa:
            if muc.trang_thai != DANG:
                return
            if dung:
                muc.trang_thai = DUNG
            elif loi:
                muc.trang_thai = HONG
            else:
                muc.trang_thai = XONG
            muc.loi = str(loi or "")[:200]
        self._bao_doi()
        self._nap_them()

    # ── Luật nạp ─────────────────────────────────────────────────────────────

    def _nap_them(self) -> None:
        """Trống chỗ thì lấy mục chờ kế tiếp ra chạy. Hết việc thì tự đóng."""
        bat_dau: List[MucDoi] = []
        het = False
        with self._khoa:
            if not self._mo:
                return
            # Đánh dấu DANG ngay trong khoá — `so_dang` đếm được luôn — rồi
            # mới gọi `khoi_chay` ngoài khoá.
            while self.so_dang < self._so:
                ke = next((m for m in self._ds if m.trang_thai == CHO), None)
                if ke is None:
                    break
                ke.trang_thai = DANG
                ke.loi = ""
                ke.huy.clear()
                bat_dau.append(ke)
                self._dot.append(ke)
            if self.so_dang == 0:
                self._mo = False
                het = True
                dot = list(self._dot)
        for m in bat_dau:
            try:
                self._khoi_chay(m)
            except Exception as loi:  # noqa: BLE001 — một lượt không mở được
                # không được kẹt cả hàng: đánh dấu hỏng rồi nạp mục sau.
                with self._khoa:
                    m.trang_thai = HONG
                    m.loi = str(loi)[:200]
                self._bao_doi()
                self._nap_them()
                return
        if bat_dau:
            self._bao_doi()
        if het and self._on_het is not None:
            self._on_het(dot)

    def _bao_doi(self) -> None:
        if self._on_doi is not None:
            self._on_doi()

    # ── Nhớ qua lần tắt tool ─────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        with self._khoa:
            return {"so_song_song": self._so,
                    "muc": [m.to_dict() for m in self._ds]}

    def luu(self, goc: str) -> bool:
        """Ghi hàng đợi xuống đĩa (tệp tạm rồi đổi tên). Trả về ghi được không."""
        try:
            ghi_json(duong_tep(goc), self.to_dict())
            return True
        except OSError:
            return False

    def nap(self, goc: str) -> int:
        """Nạp lại hàng đợi lần trước. Trả về số mục nạp được.

        Chỉ nạp mục mà thư mục lượt **còn trên đĩa** — khách xoá thư mục thì
        mục ấy không còn gì để chạy. Không tự mở hàng: mở tool lên mà tự chạy
        tiếp ba video là tự tiêu tiền khi chưa ai bấm gì.
        """
        try:
            with open(duong_tep(goc), "r", encoding="utf-8") as tep:
                goi = json.load(tep)
        except (OSError, ValueError):
            return 0
        if not isinstance(goi, dict):
            return 0
        muc = []
        for g in goi.get("muc") or []:
            if not isinstance(g, dict):
                continue
            m = MucDoi.from_dict(g)
            if m.thu_muc and os.path.isdir(m.thu_muc):
                muc.append(m)
        with self._khoa:
            self._so = self._kep(goi.get("so_song_song", self._so))
            self._ds = muc
        return len(muc)


def _chuan(duong: str) -> str:
    return os.path.normcase(os.path.normpath(str(duong or "")))


# ── Khoá các khâu chạy trên máy ──────────────────────────────────────────────

_KHOA_MAY = threading.Lock()


def khoa_khau_may(viec: Dict[str, Callable[..., Any]], *,
                  cancel: Optional[threading.Event] = None,
                  ghi: Optional[Callable[[str], None]] = None,
                  khoa: Optional[threading.Lock] = None,
                  cac_khau=KHAU_TREN_MAY,
                  ngu_toi_da: float = 0.5) -> Dict[str, Callable[..., Any]]:
    """Bọc các khâu chạy trên máy (`KHAU_TREN_MAY`) bằng một khoá chung.

    Sửa **tại chỗ** bảng `viec` và trả lại chính nó. Hàm bọc giữ nguyên mọi
    thuộc tính của hàm gốc (`soi_lai`, `khong_tieu_vi`…) — `core/auto.chay`
    đọc chúng bằng `getattr`, mất là khâu đổi hành vi trong im lặng.

    Đợi khoá theo từng nhịp ngắn và ngó cờ dừng giữa các nhịp: lượt đứng chờ
    vẫn bấm Dừng được, không phải đợi lượt kia dựng xong.
    """
    khoa = khoa if khoa is not None else _KHOA_MAY

    def boc_mot(ma: str, lam):
        def boc(luot, tt):
            da_bao = False
            while not khoa.acquire(timeout=ngu_toi_da):
                if cancel is not None and cancel.is_set():
                    raise Cancelled()
                if not da_bao and ghi is not None:
                    da_bao = True
                    ghi("  chờ máy rảnh — một lượt khác đang dùng khâu này "
                        "trên máy, xong là tới lượt mình.")
            try:
                return lam(luot, tt)
            finally:
                khoa.release()

        boc.__name__ = getattr(lam, "__name__", "boc_" + ma)
        boc.__dict__.update(getattr(lam, "__dict__", {}) or {})
        return boc

    for ma in cac_khau:
        lam = viec.get(ma)
        if lam is not None:
            viec[ma] = boc_mot(ma, lam)
    return viec


def tom_tat(hd: HangDoiAuto) -> str:
    """Một câu về hàng đợi cho người đọc: "3 video · 1 đang chạy · 2 chờ"."""
    ds = hd.ds
    if not ds:
        return "Chưa có video nào trong hàng đợi."
    dem = {tt: sum(1 for m in ds if m.trang_thai == tt) for tt in CHU_TRANG_THAI}
    phan = ["{0} video".format(len(ds))]
    for tt, ten in ((DANG, "đang chạy"), (CHO, "chờ"), (XONG, "xong"),
                    (HONG, "hỏng"), (DUNG, "dừng")):
        if dem.get(tt):
            phan.append("{0} {1}".format(dem[tt], ten))
    cach = ("chạy lần lượt" if hd.so_song_song == 1
            else "chạy {0} cùng lúc".format(hd.so_song_song))
    return " · ".join(phan) + " — " + cach + (
        "" if hd.dang_mo or not dem.get(CHO) else
        " · bấm “Chạy hàng đợi” để chạy phần chờ")
