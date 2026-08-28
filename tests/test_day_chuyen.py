"""Dây chuyền ảnh → clip: bắn hết một lượt, xong cái nào đi tiếp cái ấy.

Đây là bài kiểm cho **một lỗi thời gian**, không phải cho một tính năng mới.

Đo trên máy chủ thật ngày 15/08/2026:

    một tấm ảnh              30,8 giây ở nhà máy
    ba mươi tấm bắn cùng lúc 38,2 giây cho cả ba mươi
    cổng cho                 979 job ảnh · 172–316 job clip cùng lúc

Tức nhà máy chạy song song thật: ba mươi tấm gần như không đắt hơn một tấm. Vậy
mà tool mất 5,9 phút cho 114 ảnh và 14,8 phút cho 114 clip — vì nó tự dựng ba
hàng rào nối đuôi nhau: thăm dò một tấm trước khi bung luồng, clip đợi **đủ**
114 ảnh, ảnh bìa đợi hết clip.

Không hàng rào nào trong đó là thật. Các bài dưới đây canh đúng bốn tính chất
mới, và canh cả những thứ **không được đổi** khi làm nhanh hơn: tệp đã có trên
đĩa thì không bắn lại, và bấm Dừng là dừng.

Máy chủ giả, không gọi mạng, không mất một đồng nào.
"""

from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager

import pytest

from core.auto import moi_luot
from core.auto_khau import (CHU_MOI_LUOT_DOC, BoiCanh, LoiKetJob, SoTheoDoi,
                            chia_doan_doc, dung_bo_viec)

# ── Máy chủ giả ──────────────────────────────────────────────────────────────


class _PhanHoi:
    """Một lượt tải tệp về."""

    def __init__(self, du_lieu: bytes) -> None:
        self._du_lieu = du_lieu
        self.status_code = 200
        self.headers = {"Content-Length": str(len(du_lieu))}

    def iter_bytes(self, _co=None):
        yield self._du_lieu

    def read(self):
        return self._du_lieu


class _Http:
    @staticmethod
    @contextmanager
    def stream(_cach, _dia_chi, headers=None):
        yield _PhanHoi(b"tep-gia-cua-may-chu-gia")


class _Cua:
    """Một cửa tạo job: `images`, `videos`, `tts`."""

    def __init__(self, may: "MayChuGia", loai: str) -> None:
        self._may = may
        self._loai = loai

    def create(self, **kw):
        return self._may.tao(self._loai, kw)


class MayChuGia:
    """Nhà máy giả: nhận job, `tre` giây sau thì job ấy xong.

    Ghi lại **thời điểm** của từng lời gọi — đó mới là thứ các bài dưới đây đo:
    không phải "có gọi không" mà "gọi lúc nào so với cái khác".
    """

    def __init__(self, tre_anh: float = 0.15, tre_clip: float = 0.1,
                 cham: float = 0.0, anh_cham=(), clip_hong=()) -> None:
        self.tre = {"image": tre_anh, "video": tre_clip, "tts": tre_anh}
        self.cham = cham
        self.anh_cham = set(anh_cham)
        self.clip_hong = set(clip_hong)
        self.job = {}
        self.tao_luc = []          # (loại, lời nhắc, thời điểm)
        self.so_lan_retrieve = 0
        self.so_lan_list = 0
        self.cho_hoi_ca_luot = True
        self.khoa = threading.Lock()
        self.images = _Cua(self, "image")
        self.videos = _Cua(self, "video")
        self.tts = _Cua(self, "tts")
        self.jobs = self
        self.uploads = self
        self.base_url = "https://gia.shopapi.vn"
        self._http = _Http()

    # ── tạo job ──
    def tao(self, loai: str, kw):
        loi_nhac = str(kw.get("prompt") or kw.get("text") or "")
        with self.khoa:
            ma = "job_{0}_{1}".format(loai, len(self.job) + 1)
            tre = self.tre[loai]
            if any(m in loi_nhac for m in self.anh_cham):
                tre = self.cham
            self.job[ma] = {"id": ma, "loai": loai, "luc": time.time(),
                            "tre": tre,
                            "hong": any(m in loi_nhac
                                        for m in self.clip_hong)}
            self.tao_luc.append((loai, loi_nhac, time.time()))
            return {"id": ma, "status": "queued"}

    def _trang_thai(self, m):
        if time.time() - m["luc"] < m["tre"]:
            return "queued"
        return "failed" if m["hong"] else "succeeded"

    def _goi(self, m):
        goi = {"id": m["id"], "status": self._trang_thai(m)}
        if goi["status"] == "failed":
            goi["error"] = {"code": "engine_unavailable",
                            "message": "Trục trặc. Bạn không bị trừ tiền."}
        return goi

    # ── hỏi job ──
    def retrieve(self, ma):
        with self.khoa:
            self.so_lan_retrieve += 1
            m = self.job.get(ma)
        return self._goi(m) if m else {"id": ma, "status": "queued"}

    def list(self, *, status=None, limit=20, cursor=None, **_kw):
        if not self.cho_hoi_ca_luot:
            raise RuntimeError("cổng này chưa có GET /v1/jobs")
        with self.khoa:
            self.so_lan_list += 1
            ds = [self._goi(m) for m in self.job.values()]
        ds = [g for g in ds if g["status"] == status]
        ds.reverse()                       # mới nhất trước, như cổng thật
        dau = int(cursor or 0)
        khuc = ds[dau:dau + int(limit or 20)]
        con = dau + len(khuc)
        return {"object": "list", "data": khuc, "has_more": con < len(ds),
                "next_cursor": str(con) if con < len(ds) else None}

    # ── linh tinh ──
    def upload_file(self, duong):
        return "https://kho.gia/{0}?X-Amz-Expires=7200".format(
            os.path.basename(duong))

    def request(self, _cach, _duong, **_kw):
        return {"limits": {"requests_per_minute": 600000,
                           "concurrent_jobs": {"image": 979, "video": 200,
                                               "tts": 3},
                           "max_queued": 100000}}

    def _build_headers(self, accept=None):
        return {}


class KenhGia:
    ma = "TL1"
    anh_nv = []
    prompt = {}
    style = {}
    so_thumbnail = 3
    engine = "veo3"
    voice_id = "giong-1"
    mo_hinh = "mo-hinh-gia"


@pytest.fixture(autouse=True)
def khong_giu_nhip(monkeypatch):
    """Tắt van nhịp gọi và bộ nhớ hạn mức — bài kiểm không đo hai thứ đó."""
    from core import auto_khau
    from core import su_co

    monkeypatch.setattr(auto_khau, "xin_nhip", lambda *_a, **_k: None)
    # FFmpeg thật sẽ từ chối "tệp" giả của máy chủ giả — mà việc kiểm tệp đã có
    # bài riêng, ở đây nó chỉ làm nhiễu.
    monkeypatch.setattr(auto_khau, "_kiem_media", lambda *_a, **_k: None)
    auto_khau._HAN_MUC.clear()
    cu = su_co.NHIP.moi_phut
    yield
    auto_khau._HAN_MUC.clear()
    su_co.NHIP.moi_phut = cu


def _dung_luot(goc: str, canh, tieu_de: str = "Tiêu đề thử"):
    luot = moi_luot(goc, "TL1", "0001")
    os.makedirs(luot.thu_muc, exist_ok=True)
    with open(os.path.join(luot.thu_muc, "4-canh.json"), "w",
              encoding="utf-8") as t:
        json.dump(canh, t, ensure_ascii=False)
    with open(os.path.join(luot.thu_muc, "1-tieu-de.txt"), "w",
              encoding="utf-8") as t:
        t.write("TITLE: {0}\nTHUMB: chữ bìa\n".format(tieu_de))
    return luot


def _canh(n: int):
    return [{"scene_id": i, "img_prompt": "anh canh {0}".format(i),
             "video_prompt": "clip canh {0}".format(i),
             "srt_start": "00:00:00,000", "srt_end": "00:00:05,000"}
            for i in range(1, n + 1)]


def _boi_canh(goc: str, may: MayChuGia, cancel=None):
    # `nhip_hoi` nhỏ: máy chủ giả trả kết quả trong một phần mười giây, nhịp
    # hỏi thật 2 giây chỉ làm bài kiểm ngồi đợi chứ không đo thêm được gì.
    return BoiCanh(goc=goc, kenh=KenhGia(), goi_chat=lambda *a, **k: "",
                   client=may, cancel=cancel, on_log=lambda _d: None,
                   nhip_hoi=0.05)


# ── Cắt kịch bản thành đoạn đọc ─────────────────────────────────────────────


class TestChiaDoanDoc:
    """Mỗi đoạn là một lượt gọi riêng — mỗi chỗ nối là một chỗ đổi tông giọng.

    Nên luật ở đây là **ít đoạn nhất có thể**, không phải "cắt vụn cho ba suất
    song song có việc". Xem ghi chú dài ở `chia_doan_doc`.
    """

    KICH_BAN = ("Câu thứ nhất kể chuyện. " * 40 + "Câu cuối cùng. ") * 4

    def test_cat_it_doan_nhat_co_the(self):
        """Đúng con số chủ dự án chỉ ra 16/08/2026: 2.726 chữ phải ra 3 đoạn."""
        bai = "Một câu kể chuyện dài vừa phải. " * 87   # ~2.784 chữ
        doan = chia_doan_doc(bai)
        it_nhat = -(-len(bai.strip()) // CHU_MOI_LUOT_DOC)
        assert len(doan) == it_nhat == 3, (
            "chia {0} đoạn trong khi {1} là đủ — thừa {2} chỗ đổi tông "
            "giọng".format(len(doan), it_nhat, len(doan) - it_nhat))

    def test_cac_doan_deu_nhau(self):
        """Nhồi đầy thì đoạn cuối cụt lủn, tông giọng của nó lệch hẳn."""
        doan = chia_doan_doc("Một câu kể chuyện dài vừa phải. " * 87)
        ngan, dai = min(len(d) for d in doan), max(len(d) for d in doan)
        assert dai - ngan < 0.25 * dai, (
            "đoạn ngắn nhất {0} chữ, dài nhất {1} chữ".format(ngan, dai))

    def test_ghep_lai_khong_mat_mot_chu_nao(self):
        """Mất chữ ở đây là mất hẳn một khúc lời giữa video."""
        doan = chia_doan_doc(self.KICH_BAN)
        assert "".join(d.replace(" ", "") for d in doan) == \
            self.KICH_BAN.replace(" ", "").strip()

    def test_cat_o_ranh_gioi_cau(self):
        """Cắt giữa câu là chỗ nối nghe rõ một nhịp hụt."""
        for d in chia_doan_doc(self.KICH_BAN):
            assert d.rstrip()[-1] in ".!?…", (
                "đoạn kết thúc giữa câu: “…{0}”".format(d[-30:]))

    def test_uu_tien_cat_o_cho_xuong_dong(self):
        """Hết đoạn văn là chỗ người đọc nghỉ dài nhất — cắt ở đó lộ ít nhất."""
        bai = ("Câu mở đầu của đoạn văn này. " * 20).strip() + "\n\n" + \
              ("Câu mở đầu của đoạn văn kia. " * 20).strip()
        doan = chia_doan_doc(bai)
        assert len(doan) == 2
        assert doan[0].endswith("đoạn văn này.")

    def test_kich_ban_ngan_khong_bi_bam_vun(self):
        ngan = "Một câu ngắn thôi. Hai câu là hết bài."
        assert len(chia_doan_doc(ngan)) == 1

    def test_vua_dung_tran_thi_van_la_mot_doan(self):
        """Cắt đôi một bài đã vừa trần là thừa ra một chỗ đổi tông vô ích."""
        assert len(chia_doan_doc("a" * CHU_MOI_LUOT_DOC)) == 1

    def test_khong_bao_gio_vuot_tran_cua_cong(self):
        """Vượt trần là cổng từ chối — mất cả khâu, không phải chỉ xấu tiếng."""
        for d in chia_doan_doc("Câu dài dòng và lặp lại. " * 2000):
            assert len(d) <= CHU_MOI_LUOT_DOC

    def test_khuc_dai_khong_co_dau_cham_van_cat_duoc(self):
        """Không có nhánh cắt cứng thì hàm quay vòng vô tận ở đây."""
        doan = chia_doan_doc("a" * 3000)
        assert doan and all(len(d) <= CHU_MOI_LUOT_DOC for d in doan)

    def test_tran_dung_bang_tran_da_do_cua_cong(self):
        """Tool nội bộ đời trước đo được 1.000 — cùng một cổng giọng nói."""
        assert CHU_MOI_LUOT_DOC == 1000

    def test_hai_bat_bien_dung_voi_moi_kieu_kich_ban(self):
        """Ném đủ kiểu văn bản vào, hai điều sau không được sai lần nào.

        Kịch bản thật muôn hình vạn trạng: câu dài câu ngắn, xuống dòng loạn
        xạ, đoạn dài không có lấy một dấu chấm. Bài kiểm viết tay chỉ phủ được
        vài hình dạng mình nghĩ ra — mà bug nằm ở hình dạng mình không nghĩ ra.

        Hai điều phải luôn đúng:
          1. Không đoạn nào vượt trần (vượt là cổng từ chối, mất cả khâu).
          2. Ghép lại không mất một chữ nào (mất là mất hẳn một khúc lời).
        """
        import random

        ngau = random.Random(20260816)      # cố định hạt: đỏ là dựng lại được
        manh = ["Câu ngắn. ", "Một câu dài hơn hẳn để thử chỗ cắt. ",
                "\n", "\n\n", "Không-có-dấu-chấm-gì-cả-suốt-một-khúc-dài ",
                "Hỏi gì thế? ", "Trời ơi! ", "a", " ", "Ngừng một chút… "]
        for lan in range(300):
            bai = "".join(ngau.choice(manh)
                          for _ in range(ngau.randint(1, 400)))
            doan = chia_doan_doc(bai)
            for d in doan:
                assert len(d) <= CHU_MOI_LUOT_DOC, \
                    "lần {0}: đoạn {1} chữ, vượt trần".format(lan, len(d))
            goc = "".join(bai.split())
            assert "".join("".join(d.split()) for d in doan) == goc, \
                "lần {0}: ghép lại không khớp bản gốc".format(lan)

    def test_khong_quay_vong_vo_tan_voi_tran_be_xiu(self):
        """Trần nhỏ là chỗ mọi nhánh "cắt ở dấu" đều trượt xuống cắt cứng."""
        for tran in (1, 2, 3, 5):
            doan = chia_doan_doc("Một câu thử. Hai câu thử.", tran=tran)
            assert doan and all(len(d) <= tran for d in doan)


# ── Sổ theo dõi job ─────────────────────────────────────────────────────────


class TestSoTheoDoi:
    """Một lượt hỏi cho cả trăm job, thay vì mỗi job một luồng ngồi canh."""

    def _so(self, may, goc, nhip=0.05):
        return SoTheoDoi(_boi_canh(goc, may), nhip=nhip)

    def test_hoi_ca_luot_chu_khong_hoi_tung_cai(self, tmp_path):
        may = MayChuGia(tre_anh=0.2)
        so = self._so(may, str(tmp_path))
        ma = [may.tao("image", {"prompt": "x"})["id"] for _ in range(30)]
        try:
            for m in ma:
                assert so.cho(m, tran=60)["status"] == "succeeded"
        finally:
            so.dong()
        assert may.so_lan_retrieve == 0, (
            "hỏi riêng {0} lần cho 30 job — cả sổ chỉ cần một lượt hỏi".format(
                may.so_lan_retrieve))
        assert may.so_lan_list > 0

    def test_lat_trang_khi_job_nam_o_trang_hai(self, tmp_path):
        """114 job xong gần như cùng lúc, mà một trang chỉ chứa 100."""
        may = MayChuGia(tre_anh=0.05)
        so = self._so(may, str(tmp_path))
        ma = [may.tao("image", {"prompt": "x"})["id"] for _ in range(150)]
        try:
            # Job đầu tiên tạo ra nằm CUỐI danh sách (mới nhất trước) — tức
            # tận trang hai. Không lật trang thì nó chờ mãi.
            assert so.cho(ma[0], tran=60)["status"] == "succeeded"
        finally:
            so.dong()
        assert may.so_lan_retrieve == 0

    def test_cong_khong_cho_hoi_ca_luot_thi_quay_ve_hoi_tung_cai(self, tmp_path):
        """Lưới an toàn: cổng cũ chưa có `GET /v1/jobs` thì tool vẫn chạy."""
        may = MayChuGia(tre_anh=0.2)
        may.cho_hoi_ca_luot = False
        so = self._so(may, str(tmp_path))
        ma = may.tao("image", {"prompt": "x"})["id"]
        try:
            assert so.cho(ma, tran=60)["status"] == "succeeded"
        finally:
            so.dong()
        assert may.so_lan_retrieve > 0, "phải tự quay về lối hỏi từng cái"

    def test_job_hong_ma_may_chu_bao_chua_tru_tien_thi_dat_lai_duoc(self,
                                                                    tmp_path):
        may = MayChuGia(tre_anh=0.05, clip_hong=("hong",))
        so = self._so(may, str(tmp_path))
        ma = may.tao("image", {"prompt": "canh hong"})["id"]
        try:
            with pytest.raises(LoiKetJob):
                so.cho(ma, tran=60)
        finally:
            so.dong()

    def test_bam_dung_la_dung(self, tmp_path):
        dung = threading.Event()
        may = MayChuGia(tre_anh=30.0)
        bc = _boi_canh(str(tmp_path), may, cancel=dung)
        so = SoTheoDoi(bc, nhip=0.05)
        ma = may.tao("image", {"prompt": "x"})["id"]
        dung.set()
        try:
            from core.auto import Cancelled

            with pytest.raises(Cancelled):
                so.cho(ma, tran=600)
        finally:
            so.dong()


# ── Dây chuyền ảnh → clip ───────────────────────────────────────────────────


def _chay_khau_anh(goc, may, canh, cancel=None):
    luot = _dung_luot(goc, canh)
    bc = _boi_canh(goc, may, cancel=cancel)
    viec = dung_bo_viec(bc)
    return luot, viec["anh"](luot, luot.tt("anh"))


class TestDayChuyen:
    def test_ban_het_anh_mot_luot_roi_moi_co_clip_dau_tien(self, tmp_path):
        """Không còn thăm dò một tấm rồi mới bung — bắn hết, rồi mới có kết quả."""
        may = MayChuGia(tre_anh=0.6, tre_clip=0.05)
        _chay_khau_anh(str(tmp_path), may, _canh(20))

        anh = [t for loai, _n, t in may.tao_luc if loai == "image"]
        clip = [t for loai, _n, t in may.tao_luc if loai == "video"]
        assert len(anh) == 23, "20 ảnh cảnh + 3 ảnh bìa, cùng một mẻ"
        assert max(anh) < min(clip), (
            "tấm ảnh cuối cùng phải được bắn TRƯỚC khi clip đầu tiên ra đời — "
            "nếu không thì lại là chờ theo đợt")
        # ═══ NGƯỠNG PHẢI PHÂN BIỆT ĐƯỢC HAI TRẠNG THÁI, KHÔNG PHẢI ĐO TỐC ĐỘ MÁY ═══
        #
        # Bản trước chốt 0,5 giây. Nó **đỏ ngẫu nhiên 1/3 lần** trên máy đang
        # bận — mà một bài kiểm báo động giả thì tệ hơn không có: lần sau đỏ
        # thật cũng không ai tin.
        #
        # Con số này chỉ cần tách được hai trạng thái, và hai trạng thái ấy
        # cách nhau rất xa:
        #     bắn một lượt (đúng)  : dưới 0,2 giây
        #     chờ theo đợt (sai)   : 23 job / 3 suất × 0,6 giây ≈ 4,6 giây
        # Lấy 2,0 giây là dư mười lần biên về cả hai phía, mà vẫn bắt được
        # ngay nếu ai đó dựng lại hàng rào chờ theo đợt.
        assert max(anh) - min(anh) < 2.0, (
            "bắn 23 job mất {0:.1f} giây — chờ theo đợt chứ không bắn một "
            "lượt".format(max(anh) - min(anh)))

    def test_anh_xong_la_ban_clip_ngay_khong_doi_ca_me(self, tmp_path):
        """Hàng rào cũ: khâu clip đợi ĐỦ 114 ảnh. Một cảnh chậm là cả mẻ đứng."""
        may = MayChuGia(tre_anh=0.1, tre_clip=0.05, cham=3.0,
                        anh_cham=("anh canh 10",))
        goc = str(tmp_path)
        bat_dau = time.time()
        _chay_khau_anh(goc, may, _canh(12))

        clip = sorted(t for loai, _n, t in may.tao_luc if loai == "video")
        xong_anh_cham = bat_dau + 3.0
        assert clip and clip[0] < xong_anh_cham, (
            "clip đầu tiên phải ra đời trong lúc cảnh 10 còn đang vẽ, "
            "không phải sau khi cả mẻ ảnh xong")
        assert sum(1 for t in clip if t < xong_anh_cham) >= 10, (
            "gần hết clip phải bắn xong trước khi tấm ảnh chậm nhất về")

    def test_anh_bia_lam_cung_me_chu_khong_doi_het_clip(self, tmp_path):
        """3,3 phút cho đúng 3 tấm — vì chúng là một khâu riêng chạy sau cùng."""
        may = MayChuGia(tre_anh=0.1, tre_clip=0.5)
        goc = str(tmp_path)
        luot, ket = _chay_khau_anh(goc, may, _canh(6))

        bia = os.path.join(luot.thu_muc, "7-thumbnail")
        assert sorted(os.listdir(bia)) == ["thumb_001.png", "thumb_002.png",
                                           "thumb_003.png"]
        assert ket["so_thumbnail"] == 3
        clip = [t for loai, _n, t in may.tao_luc if loai == "video"]
        bia_luc = [t for loai, n, t in may.tao_luc
                   if loai == "image" and "canh" not in n]
        assert max(bia_luc) < max(clip), "ảnh bìa không được xếp sau clip"

    def test_ca_ba_khau_deu_ra_du_tep(self, tmp_path):
        may = MayChuGia()
        goc = str(tmp_path)
        luot, ket = _chay_khau_anh(goc, may, _canh(8))

        assert ket["so_anh"] == 8 and ket["so_clip"] == 8
        assert len(os.listdir(os.path.join(luot.thu_muc, "5-anh"))) == 8
        assert len(os.listdir(os.path.join(luot.thu_muc, "6-clip"))) == 8
        # Hai khâu sau nhìn đĩa thấy đủ thì phải đi qua mà KHÔNG gọi thêm gì.
        bc = _boi_canh(goc, may, cancel=None)
        viec = dung_bo_viec(bc)
        truoc = len(may.tao_luc)
        viec["clip"](luot, luot.tt("clip"))
        viec["thumbnail"](luot, luot.tt("thumbnail"))
        assert len(may.tao_luc) == truoc, (
            "khâu clip và khâu ảnh bìa vừa bắn lại thứ đã có — đó là trả tiền "
            "lần hai cho cùng một cảnh")

    def test_tep_da_co_tren_dia_thi_khong_ban_lai(self, tmp_path):
        """Luật không được phá: chạy tiếp phải nhặt đúng chỗ đứt."""
        goc = str(tmp_path)
        may = MayChuGia()
        luot, _ = _chay_khau_anh(goc, may, _canh(5))
        truoc = len(may.tao_luc)

        may_hai = MayChuGia()
        bc = _boi_canh(goc, may_hai)
        dung_bo_viec(bc)["anh"](luot, luot.tt("anh"))

        assert len([1 for loai, _n, _t in may.tao_luc
                    if loai == "image"]) == 8, "5 ảnh cảnh + 3 ảnh bìa"
        assert truoc == 13, "8 ảnh + 5 clip"
        assert may_hai.tao_luc == [], (
            "lượt hai bắn thêm {0} job cho những tệp đã nằm sẵn trên "
            "đĩa".format(len(may_hai.tao_luc)))

    def test_tien_do_dem_rieng_anh_va_clip(self, tmp_path):
        """Cột “Chi tiết” phải nói đúng khâu nào đang tới đâu."""
        goc = str(tmp_path)
        may = MayChuGia()
        luot, _ = _chay_khau_anh(goc, may, _canh(4))

        assert luot.tt("anh").ghi_chu["xong"] == 4
        assert luot.tt("anh").ghi_chu["viec"] == "ảnh"
        assert luot.tt("clip").ghi_chu == {"xong": 4, "tong": 4, "viec": "clip"}
        assert luot.tt("thumbnail").ghi_chu["viec"] == "ảnh bìa"

    def test_clip_hong_khong_lam_hong_khau_anh(self, tmp_path):
        """Clip ở đây là việc làm thêm cho sớm; nó hỏng thì ảnh vẫn phải xong."""
        goc = str(tmp_path)
        may = MayChuGia(clip_hong=("clip canh",))
        luot, ket = _chay_khau_anh(goc, may, _canh(4))

        assert ket["so_anh"] == 4, "ảnh vẫn phải đủ"
        assert ket["so_clip"] == 0
        assert len(os.listdir(os.path.join(luot.thu_muc, "5-anh"))) == 4

    def test_bam_dung_la_dung(self, tmp_path):
        from core.auto import Cancelled

        dung = threading.Event()
        may = MayChuGia(tre_anh=30.0)
        goc = str(tmp_path)

        def bam_sau_mot_nhip():
            time.sleep(0.3)
            dung.set()

        threading.Thread(target=bam_sau_mot_nhip, daemon=True).start()
        with pytest.raises(Cancelled):
            _chay_khau_anh(goc, may, _canh(6), cancel=dung)


# ── Giọng đọc: ba đoạn một lượt ─────────────────────────────────────────────


class TestDocSongSong:
    def _dung(self, goc, kich_ban):
        luot = moi_luot(goc, "TL1", "0001")
        os.makedirs(luot.thu_muc, exist_ok=True)
        with open(os.path.join(luot.thu_muc, "1-kich-ban.txt"), "w",
                  encoding="utf-8") as t:
            t.write(kich_ban)
        return luot

    def test_cac_doan_chay_cung_luc_chu_khong_noi_duoi(self, tmp_path,
                                                       monkeypatch):
        from core import auto_khau

        # Không có FFmpeg thật thì bước nối sẽ kêu — mà bài này đo lúc bắn.
        monkeypatch.setattr(auto_khau, "_noi_mp3", lambda *_a, **_k: None)
        goc = str(tmp_path)
        may = MayChuGia(tre_anh=0.4)
        luot = self._dung(goc, "Một câu kể chuyện dài dòng. " * 300)
        bc = _boi_canh(goc, may)

        bat_dau = time.time()
        ket = dung_bo_viec(bc)["giong-doc"](luot, luot.tt("giong-doc"))
        mat = time.time() - bat_dau

        assert ket["so_doan"] >= 8, "kịch bản dài phải được cắt nhỏ ra"
        assert mat < 0.4 * ket["so_doan"] * 0.75, (
            "mất {0:.1f} giây cho {1} đoạn — gần bằng chạy tuần tự, tức ba "
            "suất đọc của cổng đang bỏ không".format(mat, ket["so_doan"]))

    def test_thieu_mot_doan_la_hong_ca_khau(self, tmp_path, monkeypatch):
        """Thiếu một cảnh thì dựng vẫn được; thiếu một đoạn đọc thì không."""
        from core import auto_khau

        monkeypatch.setattr(auto_khau, "_noi_mp3", lambda *_a, **_k: None)
        goc = str(tmp_path)
        may = MayChuGia(tre_anh=0.05, clip_hong=("Câu hỏng",))
        luot = self._dung(goc, "Một câu kể chuyện dài dòng. " * 300 +
                          "Câu hỏng nằm cuối bài. ")
        bc = _boi_canh(goc, may)

        with pytest.raises(Exception) as e:
            dung_bo_viec(bc)["giong-doc"](luot, luot.tt("giong-doc"))
        assert "đã dừng" not in str(e.value)
