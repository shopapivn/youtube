"""Job kẹt: máy chủ nhận việc rồi bỏ đó — bài kiểm cho sự cố 14/08/2026.

Chín clip cuối của một mẻ 112 cảnh kẹt ở trạng thái "đang xử lý". Sáu luồng
cùng ngồi đợi. Màn hình **không nhích một dòng nào suốt mười hai phút** — không
cách gì phân biệt "máy chủ đang làm" với "tool treo", kể cả người dựng tool
cũng chịu, và phải đi đọc mã mới biết là `_cho_job` đợi tới một tiếng trong im
lặng tuyệt đối.

Hai thứ được sửa, và cả hai đều phải được canh:

1. **Nói ra trong lúc đợi.** Im lặng là câu trả lời tệ nhất cho "nó còn chạy
   không".
2. **Đừng ôm một job kẹt cả tiếng.** Clip veo3 mất 1–3 phút; quá 12 phút là
   gần như chắc chắn khoá kẹt, và chỉ khoá mới mới thoát ra.

Máy chủ giả, không gọi mạng, không mất tiền.
"""

from __future__ import annotations

import pytest

from core.auto_khau import KHOANG_KE_CHO, LoiKetJob, _cho_job


class DongHoGia:
    """Đồng hồ tự tua tới mỗi lần có ai ngủ — để bài kiểm không đợi thật."""

    def __init__(self):
        self.bay_gio = 1_000_000.0

    def __call__(self) -> float:
        return self.bay_gio

    def ngu(self, giay: float) -> None:
        self.bay_gio += float(giay)


class MayChuGia:
    """Trả về `status` theo kịch bản, đếm số lần bị hỏi."""

    def __init__(self, cac_trang_thai):
        self.kich_ban = list(cac_trang_thai)
        self.so_lan_hoi = 0
        self.jobs = self

    def retrieve(self, _ma):
        self.so_lan_hoi += 1
        tt = (self.kich_ban.pop(0) if self.kich_ban
              else "processing")
        return {"id": "job_x", "status": tt}


class BoiCanhGia:
    def __init__(self, client, dong_ho):
        self.client = client
        self.dong_ho = dong_ho
        self.dong = []

    def kiem_dung(self):
        pass

    def ghi(self, dong):
        self.dong.append(dong)

    on_log = None

    def ngu(self, giay):
        self.dong_ho.ngu(giay)


@pytest.fixture
def gia(monkeypatch):
    dh = DongHoGia()
    monkeypatch.setattr("core.auto_khau.time.time", dh)
    # `_ngu_ngat` và `xin_nhip` đều ngủ thật — cho chúng tua đồng hồ thay vì đợi.
    monkeypatch.setattr("core.auto_khau._ngu_ngat",
                        lambda _bc, giay: dh.ngu(giay))
    monkeypatch.setattr("core.auto_khau.xin_nhip", lambda *_a, **_k: None)
    return dh


class TestJobXongBinhThuong:
    def test_xong_ngay_thi_khong_hoi_lan_nao(self, gia):
        bc = BoiCanhGia(MayChuGia([]), gia)
        goi = _cho_job(bc, {"id": "job_x", "status": "succeeded"})
        assert goi["status"] == "succeeded"
        assert bc.client.so_lan_hoi == 0, "đã xong rồi thì đừng hỏi lại"

    def test_xong_sau_vai_lan_hoi(self, gia):
        may = MayChuGia(["processing", "processing", "succeeded"])
        bc = BoiCanhGia(may, gia)
        assert _cho_job(bc, {"id": "job_x", "status": "queued"})["status"] == "succeeded"

    def test_may_chu_bao_hong_thi_nem_len_ngay(self, gia):
        bc = BoiCanhGia(MayChuGia(["failed"]), gia)
        with pytest.raises(RuntimeError, match="job hỏng"):
            _cho_job(bc, {"id": "job_x", "status": "queued"})


class TestNoiRaTrongLucDoi:
    """Im lặng là câu trả lời tệ nhất cho “nó còn chạy không”."""

    def test_doi_lau_thi_co_dong_nhac(self, gia):
        may = MayChuGia(["processing"] * 40 + ["succeeded"])
        bc = BoiCanhGia(may, gia)
        # 40 vòng, nhịp hỏi giãn tới 25 giây -> chừng 950 giây. Trần phải rộng
        # hơn thế, nếu không bài kiểm đo nhầm sang chuyện job kẹt.
        _cho_job(bc, {"id": "job_x", "status": "queued"}, tran=1800,
                 ten_viec="cảnh 66")
        assert bc.dong, "đợi mấy phút mà không nói gì là tool trông như treo"
        assert any("cảnh 66" in d for d in bc.dong), \
            "phải nói RÕ cái nào đang chậm, không phải “có cái gì đó chậm”"
        assert any("phút" in d for d in bc.dong)

    def test_job_nhanh_thi_khong_lam_rac_man_hinh(self, gia):
        may = MayChuGia(["processing", "succeeded"])
        bc = BoiCanhGia(may, gia)
        _cho_job(bc, {"id": "job_x", "status": "queued"}, ten_viec="cảnh 1")
        assert not bc.dong, "job xong nhanh thì không cần nhắc gì"

    def test_nhac_thua_dan_chu_khong_moi_vong_mot_dong(self, gia):
        may = MayChuGia(["processing"] * 60 + ["succeeded"])
        bc = BoiCanhGia(may, gia)
        _cho_job(bc, {"id": "job_x", "status": "queued"}, tran=1800)
        # Đợi tối đa 1800 giây, nhắc mỗi KHOANG_KE_CHO giây.
        assert len(bc.dong) <= int(1800 / KHOANG_KE_CHO) + 2


class TestKetThiChiuThua:
    def test_qua_tran_thi_nem_LoiKetJob(self, gia):
        """Loại lỗi riêng, vì nơi gọi xử khác hẳn: phải đặt job MỚI."""
        bc = BoiCanhGia(MayChuGia([]), gia)      # mãi mãi "processing"
        with pytest.raises(LoiKetJob):
            _cho_job(bc, {"id": "job_x", "status": "queued"}, tran=120)

    def test_khong_om_mot_job_ket_ca_tieng(self, gia):
        """Từng để 3600 giây — giữ chỗ một luồng suốt 60 phút cho một thứ
        không bao giờ tới."""
        bc = BoiCanhGia(MayChuGia([]), gia)
        dau = gia.bay_gio
        with pytest.raises(LoiKetJob):
            _cho_job(bc, {"id": "job_x", "status": "queued"})
        da_doi = gia.bay_gio - dau
        assert da_doi < 20 * 60, \
            "đợi {0:.0f} phút là quá lâu cho một clip 1–3 phút".format(da_doi / 60)
        assert da_doi > 5 * 60, \
            "đợi quá ít thì job chậm thật cũng bị bỏ, và tiền đã tiêu rồi"

    def test_cau_loi_noi_ro_da_doi_bao_lau(self, gia):
        bc = BoiCanhGia(MayChuGia([]), gia)
        with pytest.raises(LoiKetJob, match="phút"):
            _cho_job(bc, {"id": "job_x", "status": "queued"}, tran=120)


def test_tran_khong_the_dat_qua_thap(gia):
    """Trần 0 giây thì mọi job đều “kẹt” — chặn cái gõ nhầm đó ngay."""
    may = MayChuGia(["processing", "succeeded"])
    bc = BoiCanhGia(may, gia)
    assert _cho_job(bc, {"id": "job_x", "status": "queued"},
                    tran=0)["status"] == "succeeded"
