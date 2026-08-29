"""Một khoá idempotency hỏng ở máy chủ không được kẹt cả lượt chạy.

═══ ĐO 28/08/2026, PHIM openstory/0010 ═══

Đoạn giọng đọc số 5 hỏng **mười hai lần liền** với `engine_unavailable`, trong
khi bốn đoạn trước làm được. Loại dần:

* **không phải nội dung** — 857 ký tự, dưới trần 1.000, chữ lành (cảnh cưới,
  nồi cơm thần, lời chúc ngủ ngon);
* **không phải nhà máy** — một câu 37 ký tự cùng lúc ấy xong trong 26 giây;
* **không phải độ dài** — gửi **đúng 857 ký tự ấy** qua đường trần trụi với
  khoá mới thì xong trong **62 giây**.

Cái khác duy nhất là **khoá**. Job hỏng ở máy chủ thì bản ghi của khoá ấy giữ
luôn cái hỏng; gọi lại bằng khoá cũ là nhận lại đúng cái xác ấy.

Tool vốn có một nấc thoát (đuôi `":k2"`) nhưng chỉ MỘT nấc, mà khâu ngoài thử
lại cả khâu ba lần và mỗi lần lại dựng đúng hai khoá cũ — nên sau lần đầu là cả
hai đều đã hỏng.
"""
from __future__ import annotations

import time

from core.auto_khau import khoa_thoat_ket


def test_moi_nac_mot_khoa_khac_nhau():
    a, b = khoa_thoat_ket(1), khoa_thoat_ket(2)
    assert a != b and a and b


def test_khong_bao_gio_tra_ve_duoi_RONG():
    """Đuôi rỗng là quay về đúng khoá đã hỏng — thứ hàm này sinh ra để tránh."""
    for lan in range(1, 5):
        assert khoa_thoat_ket(lan).strip(), lan


def test_doi_theo_THOI_GIAN_chu_khong_theo_bo_dem_trong_bo_nho(monkeypatch):
    """Chạy lại lượt sau khi tool tắt thì biến đếm về 0, khoá lại trùng cái cũ.

    Đây chính là chỗ lượt 0010 kẹt: mỗi lần chạy lại đều dựng đúng `""` và
    `":k2"`, cả hai đã hỏng từ lần chạy trước.
    """
    gia = {"t": 1_800_000_000.0}
    monkeypatch.setattr(time, "time", lambda: gia["t"])
    cu = khoa_thoat_ket(1)
    gia["t"] += 3600.0          # một giờ sau, tool khởi động lại
    assert khoa_thoat_ket(1) != cu


def test_cung_mot_phut_thi_khoa_on_dinh(monkeypatch):
    """Trong cùng một phút thì phải trùng.

    Nếu không thì hai lần thử lại sát nhau lại đặt hai job — tức trả tiền hai
    lần cho một việc, đúng thứ khoá idempotency sinh ra để chặn.
    """
    gia = {"t": 1_800_000_000.0}
    monkeypatch.setattr(time, "time", lambda: gia["t"])
    cu = khoa_thoat_ket(1)
    gia["t"] += 5.0
    assert khoa_thoat_ket(1) == cu


def test_khau_giong_doc_thu_DU_BA_KHOA_truoc_khi_bo_cuoc():
    """Nguồn phải cho thấy vòng ba nấc, không phải một nấc `:k2` như cũ."""
    import inspect

    import core.auto_khau as ak

    ma = inspect.getsource(ak._khau_giong_doc)
    assert "khoa_thoat_ket" in ma, "khâu giọng đọc vẫn dùng khoá chết"
    assert '":k2"' not in ma, "còn sót nấc thoát một-lần cũ"
    assert "for _lan in range(3)" in ma


def test_lan_goi_DAU_van_dung_khoa_on_dinh():
    """Lần đầu phải là khoá trần — đổi khoá ngay từ đầu là mất chống trả hai lần.

    Đọc nguồn vì hàm `doc()` nằm trong `mot_doan()`, không gọi thẳng từ ngoài.
    """
    import inspect

    import core.auto_khau as ak

    ma = inspect.getsource(ak._khau_giong_doc)
    assert 'doc("" if _lan == 0 else khoa_thoat_ket(_lan))' in ma


def test_khau_ANH_va_khau_CLIP_cung_thu_du_ba_khoa():
    """Cùng một bệnh, cùng một cách chữa — cả ba khâu tiêu tiền.

    Đo 28/08/2026, phim `openstory/0011` cảnh 40: nấc `":k2"` đặt lúc 17:44,
    tới 17:55 máy chủ vẫn "đang làm". Một nấc cố định thì chạy lại lượt là gặp
    đúng khoá đã hỏng.
    """
    import inspect

    import core.auto_khau as ak

    for ham, ten in ((ak._tao_anh, "khâu ảnh"), (ak._lam_clip, "khâu clip")):
        ma = inspect.getsource(ham)
        assert "khoa_thoat_ket" in ma, ten
        # Chỉ cấm dùng `:k2` làm ĐỐI SỐ; nhắc nó trong chú thích thì được,
        # đó là chỗ kể lại vì sao một nấc là không đủ.
        assert '(dang_dung, ":k2")' not in ma, ten
        assert '(url_anh, ":k2")' not in ma, ten
        assert "for _lan in range(1, 3)" in ma, ten
