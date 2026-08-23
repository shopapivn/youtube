"""Tìm ảnh + video mẫu của phong cách — chỉ đọc đĩa, KHÔNG gọi mạng.

Thư mục ảnh mẫu đã đổi bố cục hai lần: đầu tiên là tệp phẳng `<slug>.jpg`, rồi
`{i+1:03d}_*.png` do `core.batch.safe_filename` sinh ra khi chạy qua hàng đợi,
giờ là thư mục con `<slug>/01.jpg 02.jpg 03.jpg + video.mp4`. Máy khách đã tải
bản cũ vẫn còn ảnh theo bố cục cũ, nên `_anh_mau_cua` phải nhận cả ba — hỏng
đường lui là gallery của họ trắng trơn sau khi cập nhật tool.

Bài này dựng thư mục giả bằng `tmp_path` nên không phụ thuộc vào bộ ảnh thật đã
ship, và không tốn một lời gọi API nào.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


@pytest.fixture()
def mau(tmp_path, monkeypatch):
    """Trỏ `THU_MUC_MAU` sang thư mục rỗng tạm để tự dựng từng bố cục."""
    from ui_qt import kenh

    monkeypatch.setattr(kenh, "THU_MUC_MAU", str(tmp_path))
    return kenh, tmp_path


def _cham(p) -> None:
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    with open(str(p), "wb") as f:
        f.write(b"x")


def test_chua_co_gi_thi_khong_vo(mau):
    kenh, _tmp = mau
    assert kenh._anh_mau_cua(0, "pixar-3d") == []
    assert kenh._duong_anh_mau(0, "pixar-3d") == ""
    assert kenh._video_mau_cua("pixar-3d") == ""


def test_bo_cuc_moi_tra_ve_nhieu_anh_dung_thu_tu(mau):
    """Thư mục con nhiều ảnh: trả về đủ, sắp theo tên (01 trước 02 trước 03)."""
    kenh, tmp = mau
    for t in ("03.jpg", "01.jpg", "02.jpg"):
        _cham(tmp / "pixar-3d" / t)
    ra = kenh._anh_mau_cua(0, "pixar-3d")
    assert [os.path.basename(p) for p in ra] == ["01.jpg", "02.jpg", "03.jpg"]
    # Ảnh trên thẻ là ảnh đầu tiên.
    assert os.path.basename(kenh._duong_anh_mau(0, "pixar-3d")) == "01.jpg"


def test_video_trong_thu_muc_con_duoc_nhan_ra(mau):
    kenh, tmp = mau
    _cham(tmp / "pixar-3d" / "01.jpg")
    _cham(tmp / "pixar-3d" / "video.mp4")
    assert os.path.basename(kenh._video_mau_cua("pixar-3d")) == "video.mp4"
    # Video KHÔNG được lẫn vào danh sách ảnh, không thì thẻ đếm sai số ảnh.
    assert [os.path.basename(p) for p in kenh._anh_mau_cua(0, "pixar-3d")] \
        == ["01.jpg"]


def test_nhieu_video_tra_ve_du_va_dung_thu_tu(mau):
    kenh, tmp = mau
    for t in ("03.mp4", "01.mp4", "02.mp4"):
        _cham(tmp / "pixar-3d" / t)
    ra = kenh._video_mau_cua_nhieu("pixar-3d")
    assert [os.path.basename(p) for p in ra] == ["01.mp4", "02.mp4", "03.mp4"]
    assert os.path.basename(kenh._video_mau_cua("pixar-3d")) == "01.mp4"


def test_bo_dat_ten_cap_thang_bo_hang_doi_sinh(mau):
    """Bấm nút "Tạo mẫu" thêm lần nữa thì thư mục có hai bộ — chỉ lấy bộ có cặp.

    Hàng đợi đặt tên `001_<slug>.jpg`; bộ ship kèm tool tên `01.jpg`/`01.mp4`.
    Trộn cả hai thì thẻ hiện 6 ảnh (khách tưởng có sáu cảnh) và ô ▶ mất hình
    đại diện vì không ảnh nào cùng tên với video.
    """
    kenh, tmp = mau
    for t in ("001_pixar-3d.jpg", "002_pixar-3d.jpg", "003_pixar-3d.jpg",
              "01.jpg", "02.jpg", "03.jpg", "01.mp4"):
        _cham(tmp / "pixar-3d" / t)
    assert [os.path.basename(p) for p in kenh._anh_mau_cua(0, "pixar-3d")] \
        == ["01.jpg", "02.jpg", "03.jpg"]


def test_mau_xem_duoc_xen_video_ngay_sau_anh_cung_canh(mau):
    """Dải xem: ảnh 1 → video 1 → ảnh 2 → … và video mượn ảnh cùng cảnh."""
    kenh, tmp = mau
    for t in ("01.jpg", "02.jpg", "03.jpg", "01.mp4", "02.mp4", "03.mp4"):
        _cham(tmp / "pixar-3d" / t)
    ra = kenh._mau_xem_duoc(0, "pixar-3d")
    assert [(os.path.basename(p), v, n) for p, v, _t, n in ra] == [
        ("01.jpg", False, "Ảnh 1"), ("01.mp4", True, "▶ Video 1"),
        ("02.jpg", False, "Ảnh 2"), ("02.mp4", True, "▶ Video 2"),
        ("03.jpg", False, "Ảnh 3"), ("03.mp4", True, "▶ Video 3"),
    ]
    # Ô ▶ lấy ảnh cùng cảnh làm hình đại diện — khỏi trích khung hình video.
    for p, la_video, thumb, _n in ra:
        if la_video:
            assert os.path.splitext(os.path.basename(thumb))[0] \
                == os.path.splitext(os.path.basename(p))[0]


def test_mau_xem_duoc_video_le_khong_bi_bo_roi(mau):
    """Video không khớp ảnh nào (bộ cũ `video.mp4`) vẫn phải vào cuối dải."""
    kenh, tmp = mau
    _cham(tmp / "pixar-3d" / "01.jpg")
    _cham(tmp / "pixar-3d" / "video.mp4")
    ra = kenh._mau_xem_duoc(0, "pixar-3d")
    assert [os.path.basename(p) for p, _v, _t, _n in ra] \
        == ["01.jpg", "video.mp4"]
    assert ra[1][1] is True


def test_lui_ve_tep_phang_cua_ban_cu(mau):
    """Khách cập nhật từ bản cũ chỉ có `<slug>.jpg` — gallery vẫn phải có ảnh."""
    kenh, tmp = mau
    _cham(tmp / "anime-net-phang.jpg")
    ra = kenh._anh_mau_cua(1, "anime-net-phang")
    assert [os.path.basename(p) for p in ra] == ["anime-net-phang.jpg"]


def test_lui_ve_ten_do_hang_doi_sinh(mau):
    """Chạy qua nút trong tool thì tệp mang tên `002_*` — cũng phải bắt được."""
    kenh, tmp = mau
    _cham(tmp / "002_anime.png")
    ra = kenh._anh_mau_cua(1, "khong-co-thu-muc")
    assert [os.path.basename(p) for p in ra] == ["002_anime.png"]
    # Phong cách thứ nhất (001_) không được ăn ảnh của phong cách thứ hai.
    assert kenh._anh_mau_cua(0, "khong-co-thu-muc") == []


def test_thu_muc_con_uu_tien_hon_tep_phang(mau):
    """Có cả hai thì lấy bố cục mới, không lấy tệp phẳng cũ sót lại."""
    kenh, tmp = mau
    _cham(tmp / "pixar-3d.jpg")
    _cham(tmp / "pixar-3d" / "01.jpg")
    _cham(tmp / "pixar-3d" / "02.jpg")
    ra = kenh._anh_mau_cua(0, "pixar-3d")
    assert [os.path.basename(p) for p in ra] == ["01.jpg", "02.jpg"]


def test_tep_la_trong_thu_muc_khong_lam_vo(mau):
    """Thư mục có tệp lạ (.txt, .DS_Store) thì bỏ qua, không coi là ảnh."""
    kenh, tmp = mau
    _cham(tmp / "pixar-3d" / "ghi-chu.txt")
    _cham(tmp / "pixar-3d" / "01.webp")
    assert [os.path.basename(p) for p in kenh._anh_mau_cua(0, "pixar-3d")] \
        == ["01.webp"]


def test_mot_video_thi_nhan_khong_danh_so(mau):
    """Bộ ship kèm tool chỉ có MỘT video — nhãn phải là "▶ Video" trần.

    Đánh số "▶ Video 1" khi chỉ có một cái là mời khách đi tìm Video 2 không có.
    """
    kenh, tmp = mau
    for t in ("01.jpg", "02.jpg", "03.jpg", "01.mp4"):
        _cham(tmp / "pixar-3d" / t)
    ra = kenh._mau_xem_duoc(0, "pixar-3d")
    assert [(os.path.basename(p), n) for p, _v, _t, n in ra] == [
        ("01.jpg", "Ảnh 1"), ("01.mp4", "▶ Video"),
        ("02.jpg", "Ảnh 2"), ("03.jpg", "Ảnh 3"),
    ]


def test_moi_phong_cach_that_su_co_bo_anh_mau():
    """Bộ mẫu ship kèm tool: mỗi phong cách phải có ≥3 ảnh VÀ ≥1 video.

    Không dùng `tmp_path` — bài này soi thư mục THẬT trong repo, để lần sau ai
    thêm phong cách thứ 13 mà quên tạo bộ mẫu thì biết ngay, chứ không phải để
    khách nhìn thấy thẻ xám "Ảnh mẫu chưa tạo".

    Đòi ≥3 ảnh vì cửa sổ xem to chỉ đáng mở khi có nhiều hơn một ảnh — một ảnh
    thì khách không có gì để bấm qua lại. Đòi ≥1 video vì "phong cách này khi
    chuyển động ra sao" là câu khách không đoán được từ ảnh tĩnh. Chỉ đòi MỘT
    video, không đòi đủ cho từng ảnh: chủ dự án, 23/08/2026 — "vì git nên nhẹ
    thôi, mỗi mẫu 1 video và làm nó bé". Ba video 720p mỗi phong cách là 105 MB
    nằm vĩnh viễn trong lịch sử git; một video 640×360 là 177 KB.
    """
    from ui_qt.kenh import (PHONG_CACH, _anh_mau_cua, _mau_xem_duoc,
                            _video_mau_cua_nhieu)

    thieu = []
    for i, (ten, kv) in enumerate(PHONG_CACH):
        slug = str(kv.get("slug", ""))
        anh = _anh_mau_cua(i, slug)
        video = _video_mau_cua_nhieu(slug)
        if len(anh) < 3:
            thieu.append("{0}: {1} ảnh".format(ten, len(anh)))
        if len(video) < 1:
            thieu.append("{0}: {1} video".format(ten, len(video)))
        # Video nào cũng phải trùng tên với một ảnh — lệch tên thì ô ▶ mất hình
        # đại diện, và dải xem hụt một ô so với số tệp có thật.
        so_o = len(_mau_xem_duoc(i, slug))
        if so_o != len(anh) + len(video):
            thieu.append("{0}: dải xem {1} ô, đáng ra {2}".format(
                ten, so_o, len(anh) + len(video)))
    assert not thieu, "phong cách thiếu bộ mẫu: {0}".format("; ".join(thieu))


def test_anh_va_video_mau_la_tep_that():
    """Tệp mẫu phải là ảnh/video thật, không phải tệp 0 byte hay tệp hỏng.

    Tải hỏng giữa đường vẫn để lại tệp có tên đúng; gallery thấy tên là hiện
    thẻ, khách bấm vào mới ra ô trống. Bài này soi mấy byte đầu nên bắt được.
    """
    from ui_qt.kenh import PHONG_CACH, _anh_mau_cua, _video_mau_cua_nhieu

    xau = []
    for i, (_ten, kv) in enumerate(PHONG_CACH):
        slug = str(kv.get("slug", ""))
        for p in _anh_mau_cua(i, slug):
            with open(p, "rb") as f:
                dau = f.read(4)
            # JPEG bắt đầu bằng FF D8, PNG bằng 89 P N G, WEBP bằng "RIFF".
            if not (dau[:2] == b"\xff\xd8" or dau == b"\x89PNG"
                    or dau == b"RIFF"):
                xau.append(p)
        for v in _video_mau_cua_nhieu(slug):
            with open(v, "rb") as f:
                dau = f.read(12)
            if dau[4:8] != b"ftyp":           # hộp đầu của mọi tệp MP4/MOV
                xau.append(v)
    assert not xau, "tệp mẫu không phải ảnh/video hợp lệ: {0}".format(xau)
