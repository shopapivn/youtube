"""Nắn kịch bản về đúng độ dài — **không được tam sao thất bản**.

Chủ dự án, 17/08/2026: *"kịch bản đang không hay"*.

Nguyên nhân: bản trước đưa bản vừa viết lại vào viết lại tiếp, ba vòng liền.
Mỗi lần viết lại, AI làm mượt đi một chút, mất một chi tiết cụ thể, thay một
câu sắc bằng một câu tròn. Kịch bản **nhạt dần** mà không có dòng nhật ký nào
báo.

Tool gốc `D:\\CONTENT` ghi thẳng trong mã: *"Lượt 1-3: nén từ BẢN GỐC (đủ chất
liệu, tránh tam sao thất bản)."* Bài kiểm này chốt đúng điều đó.
"""

from __future__ import annotations

from core.auto_khau import CHENH_CHO_PHEP, VONG_NAN_TOI_DA, BoiCanh, _nan_do_dai


class _KenhGia:
    mo_hinh = "claude-sonnet-5"
    giong_van = ""
    ngon_ngu = ""
    style: dict = {}

    def __init__(self, muc_tieu=3400):
        self._mt = muc_tieu
        self.prompt = {"4-do-dai.md": "khuon <<DRAFT>> <<CHARS>>"}

    @property
    def ky_tu_muc_tieu(self):
        return self._mt


def _bc(goi_chat):
    return BoiCanh(goc=".", kenh=_KenhGia(), goi_chat=goi_chat,
                   on_log=lambda _d: None, ngu=lambda _g: None)


class _AiGia:
    """Ghi lại mọi bản chữ được đưa vào, và trả ra độ dài đặt trước."""

    def __init__(self, do_dai):
        self.nhan = []          # bản chữ AI nhận được mỗi lượt
        self._ra = list(do_dai)

    def __call__(self, loi_nhac, **_k):
        # Lời nhắc là "khuon <bản chữ> <số khai>" — bóc bản chữ ra.
        self.nhan.append(loi_nhac)
        n = self._ra[min(len(self.nhan) - 1, len(self._ra) - 1)]
        return "x" * n


GOC = "G" * 2000          # bản gốc, nhận ra được trong lời nhắc


class TestKhongTamSaoThatBan:
    def test_moi_vong_deu_nan_tu_BAN_GOC(self):
        """Cái chốt. Đưa bản đã sửa vào sửa tiếp là kịch bản nhạt dần."""
        ai = _AiGia([1500, 1600, 1700])       # đều ngoài ngưỡng ±25%
        _nan_do_dai(_bc(ai), _Luot(), _KenhGia(), {}, GOC)
        assert len(ai.nhan) == VONG_NAN_TOI_DA
        # Hai vòng đầu bắt buộc phải thấy bản gốc trong lời nhắc.
        for i in range(2):
            assert GOC in ai.nhan[i], (
                "vòng {0} nắn từ bản đã sửa chứ không từ bản gốc".format(i + 1))

    def test_khong_bao_gio_dua_ban_AI_vua_tra_ve_vao_lai(self):
        ai = _AiGia([1500, 1600, 1700])
        _nan_do_dai(_bc(ai), _Luot(), _KenhGia(), {}, GOC)
        for i, ln in enumerate(ai.nhan[:2]):
            assert "xxxx" not in ln, (
                "vòng {0} nhận lại chính bản AI vừa viết".format(i + 1))


class TestChinhConSoKhai:
    def test_ra_ngan_thi_lan_sau_khai_CAO_hon(self):
        """AI hụt số khai thì phải khai cao lên, không phải sửa bản chữ."""
        ai = _AiGia([1700, 1700, 1700])       # luôn ra một nửa mục tiêu
        _nan_do_dai(_bc(ai), _Luot(), _KenhGia(), {}, GOC)
        khai = [_so_khai(ln) for ln in ai.nhan]
        assert khai[1] > khai[0], khai

    def test_ra_dai_thi_lan_sau_khai_THAP_hon(self):
        ai = _AiGia([6800, 6800, 6800])       # luôn ra gấp đôi
        _nan_do_dai(_bc(ai), _Luot(), _KenhGia(), {}, GOC)
        khai = [_so_khai(ln) for ln in ai.nhan]
        assert khai[1] < khai[0], khai

    def test_co_giam_chan_khong_nhay_vot(self):
        """Chỉnh thẳng theo tỉ lệ thì số khai nhảy qua lại, không hội tụ."""
        ai = _AiGia([1700, 1700, 1700])
        _nan_do_dai(_bc(ai), _Luot(), _KenhGia(), {}, GOC)
        khai = [_so_khai(ln) for ln in ai.nhan]
        # Không giảm chấn thì lần hai khai gấp đôi (3400/1700 = 2).
        assert khai[1] < khai[0] * 2, "thiếu giảm chấn: {0}".format(khai)


class TestDungDungLuc:
    def test_dat_ngay_vong_dau_thi_khong_goi_them(self):
        ai = _AiGia([3400])
        ra = _nan_do_dai(_bc(ai), _Luot(), _KenhGia(), {}, GOC)
        assert len(ai.nhan) == 1 and len(ra) == 3400

    def test_ban_goc_da_dung_do_dai_thi_khong_goi_AI_lan_nao(self):
        ai = _AiGia([9999])
        goc = "G" * 3400
        ra = _nan_do_dai(_bc(ai), _Luot(), _KenhGia(), {}, goc)
        assert ai.nhan == [] and ra == goc

    def test_giu_ban_GAN_muc_tieu_nhat_khi_het_vong(self):
        """Hết vòng mà chưa đạt thì phải trả bản gần nhất, không phải bản cuối."""
        ai = _AiGia([2000, 1000, 900])        # vòng 1 gần nhất
        ra = _nan_do_dai(_bc(ai), _Luot(), _KenhGia(), {}, GOC)
        assert len(ra) == 2000, len(ra)

    def test_AI_hong_thi_giu_ban_dang_co(self):
        def no(*_a, **_k):
            raise RuntimeError("mang dut")

        ra = _nan_do_dai(_bc(no), _Luot(), _KenhGia(), {}, GOC)
        assert ra == GOC

    def test_khong_co_khuon_thi_tra_nguyen_ban_nhap(self):
        k = _KenhGia()
        k.prompt = {}
        ai = _AiGia([9999])
        assert _nan_do_dai(_bc(ai), _Luot(), k, {}, GOC) == GOC
        assert ai.nhan == []

    def test_nguong_dat_la_15_phan_tram(self):
        """Ngưỡng coi là "đạt" — siết 0,25 → 0,15 ngày 29/08/2026.

        Bản 2.13.1 nới 0,08 → 0,25 để "thôi gọi API nhiều vô ích". Ý định đúng,
        nhưng 0,25 biến mục tiêu 13 phút thành "10 tới 16 phút": lượt TL4-T7
        viết ra 3.026 ký tự (10,0 phút trên đích 13,0), tool in "độ dài đạt
        (lệch 23%)" rồi bỏ qua vòng nắn — con số mục tiêu mất hết nghĩa.

        0,15 vẫn rộng gần gấp đôi ý định gốc nên không kéo lại cảnh nắn ba
        vòng, mà đủ chặt để bản hụt hơn một phần bảy bị nắn. Lời nhắc nay đo
        bằng số câu nên bản viết đã sát đích hơn: phần lớn lượt tốn thêm đúng
        một vòng.
        """
        assert CHENH_CHO_PHEP == 0.15


# ── Tiện ích ────────────────────────────────────────────────────────────────


class _Luot:
    # `ma_kenh` phải có: khoá chống-trùng mang cả mã kênh từ 19/08/2026, vì hai
    # kênh cùng đánh số lượt từ 0001 thì đâm vào nhau. Bản giả thiếu trường mà
    # `LuotChay` thật có là bản giả nói dối — và nó đã làm sáu phép kiểm ở đây
    # đỏ lên đúng lúc thêm trường ấy.
    ma_kenh = "K99"
    ma_luot = "T99"
    thu_muc = "."


def _so_khai(loi_nhac: str) -> int:
    """Bóc con số khai ra khỏi lời nhắc `khuon <bản chữ> <số khai>`."""
    return int(loi_nhac.rsplit(" ", 1)[1])
