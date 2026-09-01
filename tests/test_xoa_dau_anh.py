"""Xoá dấu nhà cung cấp ở góc ảnh.

Chủ dự án, 15/08/2026: *"có 1 số ảnh bị dính logo Gemini… để trước khi đi tạo
video ảnh đã OK"*.

Chỗ này quan trọng hơn nó thoạt nghe: ảnh của cảnh nào là **khung đầu của clip
cảnh ấy**. Dấu còn trên ảnh thì nó nằm luôn trong clip. Phát hiện muộn là phải
làm lại từ khâu clip.

Không bài nào gọi mạng.
"""

from __future__ import annotations

import os

import pytest

np = pytest.importorskip("numpy")
PIL = pytest.importorskip("PIL")

from PIL import Image  # noqa: E402

from core.xoa_dau_anh import (  # noqa: E402
    NGUONG_CO_DAU, TEP_DAU, co_dung_duoc, xoa_dau, xoa_dau_tep,
)


def _anh(w=1376, h=768, mau=(120, 130, 140)):
    """Ảnh trơn, KHÔNG có dấu."""
    return Image.new("RGB", (w, h), mau)


def _vung_dau(W, H):
    d = np.load(TEP_DAU)
    s = d["hinh"].shape[0]
    x0 = W - int(d["le_phai"]) - int(d["canh"]) - int(d["bien"])
    y0 = H - int(d["le_duoi"]) - int(d["canh"]) - int(d["bien"])
    return x0, y0, s


def _dan_dau(im, alpha):
    """Dán một ngôi sao giả vào đúng chỗ, theo đúng phép trộn alpha."""
    d = np.load(TEP_DAU)
    hinh = d["hinh"].astype(np.float64)
    s = hinh.shape[0]
    A = np.asarray(im.convert("RGB"), dtype=np.float64)
    H, W = A.shape[:2]
    x0, y0, _ = _vung_dau(W, H)
    a = np.clip(hinh * alpha, 0.0, 0.93)[:, :, None]
    A[y0:y0 + s, x0:x0 + s, :] = (a * 255.0
                                  + (1 - a) * A[y0:y0 + s, x0:x0 + s, :])
    return Image.fromarray(A.astype(np.uint8)), (x0, y0, s)


def _nhieu(w=1376, h=768, hat=7):
    """Ảnh có vân — nền trơn quá thì bài kiểm dễ dãi hơn ảnh thật."""
    r = np.random.RandomState(hat)
    A = r.randint(60, 190, size=(h, w, 3)).astype(np.float64)
    for _ in range(3):  # làm mượt cho giống ảnh thật, đừng để nhiễu hạt tiêu
        A = (A + np.roll(A, 1, 0) + np.roll(A, 1, 1)) / 3.0
    return Image.fromarray(A.astype(np.uint8))


class TestChayDuoc:
    def test_du_lieu_dau_di_kem_ma(self):
        """Thiếu tệp này thì tính năng câm lặng không làm gì."""
        assert os.path.isfile(TEP_DAU), \
            "core/dau_chuan.npz phải đi kèm mã, đừng để nó ngoài bản phát hành"

    def test_may_nay_chay_duoc(self):
        assert co_dung_duoc()


class TestKhuonAnh:
    """Ảnh không đúng khuôn thì trả về NGUYÊN, đừng xử bừa."""

    def test_anh_qua_nho_thi_giu_nguyen(self):
        nho = _anh(80, 60)
        ra, am = xoa_dau(nho, tra_alpha=True)
        assert ra is nho, "ảnh nhỏ hơn vùng dấu thì không có gì để xoá"
        assert am == 0.0

    def test_anh_dung_khuon_co_dau_thi_co_sua(self):
        co_dau, _ = _dan_dau(_nhieu(), 0.32)
        ra, am = xoa_dau(co_dau, tra_alpha=True)
        assert ra is not co_dau
        assert am > 0.0

    def test_khong_sua_anh_dua_vao(self):
        """Chỉ đọc. Hàm này không được ghi đè ảnh gốc."""
        goc, _ = _dan_dau(_nhieu(), 0.32)
        # `tobytes` chứ không `getdata`: Pillow 14 bỏ `getdata`, và một bài
        # kiểm gãy vì thư viện đổi API thì lần sau không ai buồn sửa.
        truoc = goc.tobytes()
        xoa_dau(goc)
        assert goc.tobytes() == truoc


class TestChiTruKhiCoDAU:
    """Ảnh vốn không có dấu thì đừng đụng vào.

    Ba đường dẫn tới đây, cả ba đều gặp thật:
      * ảnh nhà cung cấp trả về vốn đã sạch (1 trong 9 ảnh đo 15/08/2026);
      * khách bấm Skill "Xoá logo" hai lần trên cùng một thư mục;
      * tab Tự động chạy tiếp một lượt cũ đã có ảnh trên đĩa.
    Cứ trừ thì tấm ảnh mờ dần đi sau mỗi lần chạm vào.
    """

    def test_anh_sach_thi_giu_nguyen(self):
        sach = _nhieu()
        ra, am = xoa_dau(sach, tra_alpha=True)
        assert ra is sach, "không có dấu mà vẫn trừ là bôi bẩn ảnh vốn sạch"
        assert am == 0.0

    def test_anh_tron_khong_dau_cung_giu_nguyen(self):
        tron = _anh()
        ra, am = xoa_dau(tron, tra_alpha=True)
        assert ra is tron
        assert am == 0.0

    def test_xoa_hai_lan_khong_lam_anh_nhat_di(self):
        co_dau, (x0, y0, s) = _dan_dau(_nhieu(), 0.32)
        lan1 = xoa_dau(co_dau)
        lan2 = xoa_dau(lan1)
        assert lan2 is lan1, "lần hai phải nhận ra dấu đã sạch và bỏ qua"

    def test_bam_dung_8_trong_9_anh_that(self):
        """Con số này lấy từ đo thật, đừng nới ngưỡng cho tới khi đo lại."""
        cach = []
        for muc in (0.10, 0.20, 0.26, 0.32, 0.40):
            co_dau, _ = _dan_dau(_nhieu(), muc)
            _ra, am = xoa_dau(co_dau, tra_alpha=True)
            cach.append((muc, am))
        bo_sot = [m for m, am in cach if am == 0.0]
        assert not bo_sot, "bỏ sót dấu ở độ mờ {0}".format(bo_sot)

    def test_nguong_nam_giua_hai_khoang_do_duoc(self):
        """Ảnh có dấu khá hơn 10–66%, ảnh sạch thì mức nào cũng tệ hơn."""
        assert 0.0 < NGUONG_CO_DAU < 0.10, \
            "ngưỡng phải nằm dưới ca sát nhất (10,4%) và trên 0"


class TestDoMoDoRIENGTungAnh:
    """Đừng bỏ đoạn tự dò — ảnh lệch bị trừ quá tay thành vết ĐEN."""

    def test_do_mo_thuong_gap_thi_xoa_gan_sach(self):
        goc = _nhieu()
        co_dau, (x0, y0, s) = _dan_dau(goc, 0.32)
        sach = xoa_dau(co_dau)
        a = np.asarray(sach.convert("RGB"), dtype=np.float64)
        b = np.asarray(goc.convert("RGB"), dtype=np.float64)
        lech = np.abs(a - b)[y0:y0 + s, x0:x0 + s].mean()
        assert lech < 6.0, "xoá xong phải gần bằng ảnh gốc, lệch {0:.1f}".format(lech)

    def test_do_mo_LECH_HAN_van_khong_thanh_vet_den(self):
        """Dùng cứng một độ mờ thì ảnh lệch bị trừ quá tay.

        Chỗ ngôi sao thành một vết đen — dễ thấy hơn hẳn cái dấu mờ ban đầu,
        tức là chữa xong còn xấu hơn lúc chưa chữa.
        """
        goc = _nhieu()
        co_dau, (x0, y0, s) = _dan_dau(goc, 0.12)
        sach = xoa_dau(co_dau)
        vung = np.asarray(sach.convert("RGB"), dtype=np.float64)[
            y0:y0 + s, x0:x0 + s].mean()
        nen = np.asarray(goc.convert("RGB"), dtype=np.float64)[
            y0:y0 + s, x0:x0 + s].mean()
        assert vung > nen - 12, \
            "vùng dấu tối hơn nền {0:.0f} mức — đó là vết đen".format(nen - vung)

    def test_do_mo_chon_bam_theo_do_mo_that(self):
        for that in (0.14, 0.24, 0.32):
            co_dau, _ = _dan_dau(_nhieu(), that)
            _ra, chon = xoa_dau(co_dau, tra_alpha=True)
            assert abs(chon - that) <= 0.06, \
                "dấu mờ {0} mà chọn {1}".format(that, chon)


class TestGhiDeTep:
    def _luu_co_dau(self, thu_muc, ten="a.png"):
        p = os.path.join(str(thu_muc), ten)
        _dan_dau(_nhieu(), 0.32)[0].save(p)
        return p

    def test_ghi_de_duoc_va_anh_van_mo_duoc(self, tmp_path):
        p = self._luu_co_dau(tmp_path)
        assert xoa_dau_tep(p) is True
        with Image.open(p) as im:
            assert im.size == (1376, 768)

    def test_chay_lan_hai_tra_False_va_khong_dung_vao_tep(self, tmp_path):
        """Khách bấm Skill hai lần trên cùng thư mục — chuyện thường."""
        p = self._luu_co_dau(tmp_path)
        assert xoa_dau_tep(p) is True
        with Image.open(p) as im:
            im.load()
            sau_lan_1 = im.tobytes()
        assert xoa_dau_tep(p) is False
        with Image.open(p) as im:
            im.load()
            assert im.tobytes() == sau_lan_1, "lần hai đã sửa thêm vào ảnh"

    def test_anh_khong_dung_khuon_thi_khong_dung_vao_tep(self, tmp_path):
        p = str(tmp_path / "nho.png")
        _anh(80, 60).save(p)
        truoc = os.path.getmtime(p), os.path.getsize(p)
        assert xoa_dau_tep(p) is False
        assert (os.path.getmtime(p), os.path.getsize(p)) == truoc

    def test_tep_khong_co_thi_tra_False_chu_khong_no(self, tmp_path):
        assert xoa_dau_tep(str(tmp_path / "khong-co.png")) is False

    def test_khong_de_lai_tep_tam(self, tmp_path):
        p = self._luu_co_dau(tmp_path)
        xoa_dau_tep(p)
        assert not os.path.exists(p + ".tam")


def test_khau_anh_co_goi_xoa_dau():
    """Gỡ lời gọi này ra là dấu đi thẳng vào clip — xem ghi chú ở `_xoa_dau`."""
    from pathlib import Path

    chu = (Path(__file__).resolve().parent.parent / "core" / "auto_khau.py"
           ).read_text(encoding="utf-8")
    assert chu.count("_xoa_dau(bc, tep)") >= 3, (
        "phải qua bước xoá dấu ở cả ba chỗ: ảnh cảnh mới tải, ảnh bìa, và ảnh "
        "có sẵn trên đĩa khi chạy tiếp lượt cũ")


def test_skill_xoa_logo_co_trong_danh_sach():
    from core.skills import MA_XOA_LOGO, SKILL

    ma = [s.ma for s in SKILL]
    assert MA_XOA_LOGO in ma
    s = [x for x in SKILL if x.ma == MA_XOA_LOGO][0]
    assert s.loai == "may", "chạy trên máy khách, không gọi mô hình"


def _dan_dau_lech(im, alpha, cach_phai=120, cach_duoi=120, ti_le=1.0):
    """Dán sao ở VỊ TRÍ VÀ CỠ TUỲ Ý — mô phỏng dấu đặt theo khổ ảnh."""
    d = np.load(TEP_DAU)
    hinh = d["hinh"].astype(np.float64)
    s = hinh.shape[0]
    k = int(round(s * ti_le))
    if k != s:
        hinh = np.asarray(Image.fromarray((hinh * 255).astype(np.uint8))
                          .resize((k, k), Image.BILINEAR),
                          dtype=np.float64) / 255.0
    A = np.asarray(im.convert("RGB"), dtype=np.float64)
    H, W = A.shape[:2]
    x0 = W - cach_phai - k // 2
    y0 = H - cach_duoi - k // 2
    a = np.clip(hinh * alpha, 0.0, 0.93)[:, :, None]
    A[y0:y0 + k, x0:x0 + k, :] = (a * 255.0
                                  + (1 - a) * A[y0:y0 + k, x0:x0 + k, :])
    return Image.fromarray(A.astype(np.uint8)), (x0, y0, k)


class TestDuongDo:
    """Dấu KHÔNG nằm ở toạ độ đóng đinh — ảnh khách 01/09/2026: khổ 1376×768,
    tâm sao cách góc (120, 120) thay vì (97, 98), tool phán sạch và bỏ qua."""

    def test_dau_lech_cho_van_xoa_duoc(self):
        co_dau, (x0, y0, k) = _dan_dau_lech(_nhieu(), 0.34)
        ra, am = xoa_dau(co_dau, tra_alpha=True)
        assert am > 0, "phải DÒ ra dấu lệch chỗ, không phán sạch"
        goc = np.asarray(_nhieu().convert("RGB"), dtype=float)
        sach = np.asarray(ra.convert("RGB"), dtype=float)
        lech = np.abs(sach - goc)[y0:y0 + k, x0:x0 + k].mean()
        assert lech < 6, "vùng dấu phải về gần ảnh gốc (lệch TB {0:.1f})".format(lech)

    def test_dau_lech_ca_co_cung_xoa_duoc(self):
        co_dau, (x0, y0, k) = _dan_dau_lech(_nhieu(hat=11), 0.30,
                                            cach_phai=130, cach_duoi=110,
                                            ti_le=1.15)
        _ra, am = xoa_dau(co_dau, tra_alpha=True)
        assert am > 0, "dấu to hơn 15% vẫn phải dò ra"

    def test_anh_sach_khong_bi_duong_do_boi_ban(self):
        """Đường dò quét cả góc — ảnh sạch tuyệt đối không được bị trừ bừa."""
        for im in (_anh(), _nhieu(hat=3)):
            ra, am = xoa_dau(im, tra_alpha=True)
            assert am == 0.0 and ra is im

    def test_xoa_dau_lech_hai_lan_khong_nhat_di(self):
        co_dau, _ = _dan_dau_lech(_nhieu(hat=5), 0.34)
        lan1, am1 = xoa_dau(co_dau, tra_alpha=True)
        lan2, am2 = xoa_dau(lan1, tra_alpha=True)
        assert am1 > 0 and am2 == 0.0, \
            "xoá xong mà lần hai lại trừ tiếp là ảnh nhạt dần sau mỗi lần bấm"

    def test_anh_nho_hon_khuon_dong_dinh_van_do(self):
        """Ảnh 300×300 nằm ngoài toạ độ đóng đinh — trước đây bị bỏ qua thẳng."""
        nho = _nhieu(w=300, h=300, hat=9)
        co_dau, _ = _dan_dau_lech(nho, 0.34, cach_phai=90, cach_duoi=90)
        _ra, am = xoa_dau(co_dau, tra_alpha=True)
        assert am > 0
