"""`core/auto_khau._hong_do_noi_dung` / `_ket_job` — gói G1, 28/09/2026.

Thiết kế: docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md, mục 1.3 và 1.5(#2).

Job hỏng đi qua `_ket_job`: nếu `_hong_do_noi_dung` nói ĐÚNG là lỗi nội dung,
`_ket_job` ném `RuntimeError` thường (khâu ngoài KHÔNG được đặt lại bằng khoá
mới). Nếu không, nó ném `LoiKetJob` (khâu ngoài ĐƯỢC đặt lại bằng khoá mới —
đúng cho trục trặc hạ tầng thoáng qua, vì job hỏng luôn được hoàn 100% tiền).

Trước bản vá 2.137.10: `reference_image_unreadable` và câu "hai lần liền
không dựng xong" (engine_unavailable đã bị máy chủ tự đếm đủ 2 lần) đều rơi
vào nhánh `LoiKetJob` — nên `_tao_anh`/`_lam_clip` (vòng gửi lại KHÔNG TRẦN SỐ
LẦN cho `LoiKetJob`) gửi lại vô hạn đúng nội dung đã hỏng.

Không gọi mạng, không Qt.
"""

from __future__ import annotations

import pytest

from core.auto_khau import LoiKetJob, _hong_do_noi_dung, _ket_job


# ── `_hong_do_noi_dung` trực tiếp ────────────────────────────────────────────


def test_reference_image_unreadable_la_noi_dung():
    assert _hong_do_noi_dung("failed", {"code": "reference_image_unreadable",
                                        "message": "không đọc được ảnh"}) is True


def test_engine_unavailable_hai_lan_lien_tiep_la_noi_dung_am_tham():
    loi_goi = {"code": "engine_unavailable",
               "message": ("Google đã nhận yêu cầu nhưng hai lần liền không "
                           "dựng xong clip cho cặp ảnh + mô tả này.")}
    assert _hong_do_noi_dung("failed", loi_goi) is True


def test_engine_unavailable_cau_tieng_anh_cung_nhan_ra():
    loi_goi = {"code": "engine_unavailable",
               "message": "twice failed to finish rendering this clip."}
    assert _hong_do_noi_dung("failed", loi_goi) is True


def test_mot_minh_engine_unavailable_van_la_ha_tang_khong_phai_noi_dung():
    """Mã một mình, không có câu "đã đếm đủ 2 lần" — vẫn phải là trục trặc
    tạm, để `_lam_clip` còn được đặt lại bằng khoá mới (test cũ
    `test_mot_lan_engine_unavailable_thi_van_thu_lai_binh_thuong`)."""
    loi_goi = {"code": "engine_unavailable", "message": "máy chủ trục trặc tạm"}
    assert _hong_do_noi_dung("failed", loi_goi) is False


def test_cau_dem_du_lan_khong_co_ma_thi_khong_tinh():
    """Câu chữ trùng lặp ở đâu đó nhưng mã KHÁC `engine_unavailable` — mã mới
    là thứ quyết định, không phải câu chữ đứng một mình."""
    loi_goi = {"code": "content_rejected",
               "message": "hai lần liền không dựng xong (câu không liên quan)"}
    # Vẫn là nội dung — nhưng vì mã content_rejected đã khớp thẳng, không phải
    # vì cửa "hai lần liền" bị lẫn.
    assert _hong_do_noi_dung("failed", loi_goi) is True


def test_hanh_vi_cu_khong_doi_content_rejected_va_cau_tieng_viet():
    assert _hong_do_noi_dung("failed", {"code": "content_rejected"}) is True
    assert _hong_do_noi_dung("failed", {"code": "", "message": "vi phạm quy định"}) is True
    assert _hong_do_noi_dung("rejected", {}) is True
    assert _hong_do_noi_dung("failed", {"code": "storage_full"}) is False


# ── Xuyên qua `_ket_job`: đúng loại lỗi được ném ─────────────────────────────


def _goi(status: str, error: dict) -> dict:
    return {"id": "job_x", "status": status, "error": error}


def test_ket_job_reference_image_unreadable_khong_thanh_loiketjob():
    """Đây chính là ca hỏng — trước bản vá nó ném `LoiKetJob` (được đặt lại
    bằng khoá mới), nên vòng gửi lại vô hạn ở nơi gọi cứ hỏi lại đúng tấm ảnh
    hỏng ấy mãi. Giờ phải ném lỗi thường, KHÔNG phải `LoiKetJob`."""
    goi = _goi("failed", {"code": "reference_image_unreadable",
                          "message": "ảnh tham chiếu hỏng"})
    with pytest.raises(RuntimeError) as kq:
        _ket_job(goi)
    assert not isinstance(kq.value, LoiKetJob)


def test_ket_job_engine_unavailable_hai_lan_khong_thanh_loiketjob():
    goi = _goi("failed", {"code": "engine_unavailable",
                          "message": ("Google đã nhận yêu cầu nhưng hai lần "
                                     "liền không dựng xong clip.")})
    with pytest.raises(RuntimeError) as kq:
        _ket_job(goi)
    assert not isinstance(kq.value, LoiKetJob)


def test_ket_job_engine_unavailable_don_le_van_la_loiketjob():
    """Hồi quy: trục trặc hạ tầng thật (không câu "đã đếm đủ 2 lần") vẫn phải
    được đặt lại bằng khoá mới như trước — không được xiết chặt quá tay."""
    goi = _goi("failed", {"code": "engine_unavailable", "message": "trục trặc tạm"})
    with pytest.raises(LoiKetJob) as kq:
        _ket_job(goi)
    assert kq.value.ma_loi == "engine_unavailable"


def test_ket_job_content_rejected_van_nhu_cu():
    goi = _goi("failed", {"code": "content_rejected", "message": "vi phạm quy định"})
    with pytest.raises(RuntimeError) as kq:
        _ket_job(goi)
    assert not isinstance(kq.value, LoiKetJob)


def test_ket_job_xong_thi_tra_ve_binh_thuong():
    goi = {"id": "job_x", "status": "succeeded"}
    assert _ket_job(goi) is goi


def test_ket_job_noi_dung_gan_code_de_tu_choi_noi_dung_nhan_ra(tmp_path):
    """Gói G3, 28/09/2026: nhánh content của `_ket_job` phải gắn `.code` lên
    lỗi ném ra — nếu không, cả `core.su_co.phan_loai` lẫn
    `core.tu_choi_noi_dung.nhan_dien` đều không nhận ra đây là nội dung (không
    có `.code`, và bảng `_BANG` không có mục NOI_DUNG chung chung nào), khiến
    job hỏng vì nội dung ở khâu clip lặng lẽ rơi xuống `chet` thay vì được cứu
    (bảng 1.4 tài liệu thiết kế)."""
    goi = _goi("failed", {"code": "content_rejected", "message": "vi phạm quy định"})
    with pytest.raises(RuntimeError) as kq:
        _ket_job(goi)
    assert getattr(kq.value, "code", "") == "content_rejected"
