"""Không trang nào được tràn quá mép cửa sổ.

CLAUDE.md: *"Chữ trong nút không tự xuống dòng; nhãn dài kéo cả trang rộng quá
mép cửa sổ."* Và file này chính là bài kiểm mà CLAUDE.md hứa có ở bước 5 của
"Cách thêm một tab" — hứa từ lâu, tới 14/08/2026 mới thật sự tồn tại.

Lỗi này khách nhìn thấy nhưng **không mô tả được**: nút nằm ngoài mép phải,
kéo cửa sổ hẹp lại là nó biến mất. Họ chỉ biết bảo "giao diện bị lỗi". Đã dính
thật ba lần (tab Nghiên cứu đối thủ 932px, tab Ví 807px).

Đo `minimumSizeHint`, **không phải** `sizeHint`. `sizeHint` là bề rộng trang
*muốn* có — trang muốn rộng 1400px vẫn hoàn toàn ổn nếu nó co được. Cái làm
tràn mép là bề rộng trang **không chịu co xuống dưới**. Đã đo nhầm một lần và
suýt đi sửa sáu trang vốn không sao.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")

#: Bề rộng cửa sổ hẹp nhất tool cho phép. Trang nào không co xuống dưới mức này
#: là có phần bị đẩy ra ngoài mép.
TRAN_RONG = 760

#: Chiều cao màn hình laptop 768px trừ thanh tác vụ và thanh tiêu đề.
TRAN_CAO = 660

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def cua_so():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    from ui_qt.app import CuaSoChinh

    app = QApplication.instance() or QApplication([])
    cs = CuaSoChinh(GOC)
    cs.resize(TRAN_RONG, 900)
    cs.show()
    app.processEvents()
    yield cs, app
    cs.close()


def test_moi_trang_co_duoc_xuong_760px(cua_so):
    cs, app = cua_so
    tran = []
    for khoa, trang in cs._trang.items():
        cs.show_page(khoa)
        app.processEvents()
        rong = trang.minimumSizeHint().width()
        if rong > TRAN_RONG:
            tran.append("{0} cần {1}px".format(khoa, rong))
    assert not tran, (
        "Trang không co xuống dưới {0}px thì phần thừa bị đẩy ra khỏi mép "
        "phải — khách kéo hẹp cửa sổ là nút biến mất: {1}"
        .format(TRAN_RONG, "; ".join(tran)))


def test_trang_cao_qua_man_hinh_thi_cuon_duoc(cua_so):
    """Màn hình laptop 1366×768 vẫn là loại phổ biến nhất.

    Trang cao hơn vùng nội dung là chuyện bình thường — tab Tự động cần 897px
    vì nó có thẻ chạy, bảng tám khâu và ô nhật ký chồng lên nhau. Cái KHÔNG
    bình thường là phần dư bị cắt mất. Nên bài này không đòi trang phải thấp,
    nó đòi trang phải **cuộn được**.
    """
    from PyQt5.QtWidgets import QScrollArea

    cs, app = cua_so
    thieu = []
    for khoa, trang in cs._trang.items():
        cs.show_page(khoa)
        app.processEvents()
        if trang.minimumSizeHint().height() <= TRAN_CAO:
            continue                      # thấp hơn màn hình, không cần cuộn
        vo = cs._chong.currentWidget()
        if not isinstance(vo, QScrollArea):
            thieu.append("{0} cao {1}px".format(
                khoa, trang.minimumSizeHint().height()))
    assert not thieu, (
        "Trang cao quá {0}px mà không nằm trong vùng cuộn thì đáy bị cắt, "
        "khách không biết là có phần đó: {1}".format(TRAN_CAO, "; ".join(thieu)))


def test_moi_trang_deu_nam_trong_vung_cuon(cua_so):
    """Trang thứ chín viết sau này cũng phải được che, không cần ai nhớ."""
    from PyQt5.QtWidgets import QScrollArea

    cs, app = cua_so
    for khoa in cs._trang:
        cs.show_page(khoa)
        app.processEvents()
        assert isinstance(cs._chong.currentWidget(), QScrollArea),             "trang {0} chưa được bọc vùng cuộn".format(khoa)


def test_du_tam_trang_deu_dung_len_duoc(cua_so):
    """Thêm tab mà quên khai trong xưởng dựng thì nó im lặng thành trang trống."""
    cs, _app = cua_so
    from ui_qt.app import TRANG

    khai = [k for k, _bt, _nh in TRANG]
    thieu = [k for k in khai if k not in cs._trang]
    assert not thieu, "khai trong TRANG nhưng chưa dựng: {0}".format(thieu)


def test_tab_tu_dong_dung_dau_va_khong_co_icon(cua_so):
    """Chủ dự án, 21/08/2026: Tài khoản lên đầu, không có icon."""
    from ui_qt.app import TRANG

    assert TRANG[0][0] == "wallet", "tab Tài khoản phải đứng đầu"
    co_icon = [k for k, bt, _nh in TRANG if str(bt).strip()]
    assert not co_icon, "thanh bên không được có icon: {0}".format(co_icon)


def test_moi_tab_deu_co_bai_huong_dan(cua_so):
    """Nút “? Hướng dẫn” của một tab mà rỗng thì khách bấm vào thấy không có gì."""
    from ui_qt.app import TRANG
    from ui_qt.huong_dan import HUONG_DAN

    def co_bai(khoa: str) -> bool:
        # Tab có tab con thì mỗi tab con một bài, khoá dạng "media.thu_cong" —
        # tra thẳng "media" sẽ trượt dù bài viết đủ cả.
        for ten, bai in HUONG_DAN.items():
            if ten != khoa and not ten.startswith(khoa + "."):
                continue
            if (bai.get("tom_tat") or "").strip() or bai.get("buoc"):
                return True
        return False

    thieu = [k for k, _bt, _nh in TRANG if not co_bai(k)]
    assert not thieu, "chưa có bài hướng dẫn: {0}".format(thieu)


# ── Hộp thoại cũng phải vừa màn hình ─────────────────────────────────────────
#
# Mấy bài trên chỉ soi các TRANG trong thanh bên. Hộp thoại nằm ngoài tầm với
# của chúng, nên một hộp cao hơn màn hình sẽ lọt qua cả bộ test — và thứ bị cắt
# đầu tiên luôn là hàng nút dưới cùng, tức đúng cái nút để bấm xong việc.
#
# Hộp "Tạo kênh mới" từng đòi 846px chiều cao lúc mới viết, trên màn hình laptop
# 1366×768. Bài này bắt được ngay.


@pytest.fixture(scope="module")
def hop_tao_kenh(cua_so):
    from ui_qt.kenh import HopKenh

    cs, app = cua_so
    hop = HopKenh(cs, "", cs)          # rỗng = mở ở chế độ tạo kênh mới
    app.processEvents()
    yield hop, app
    hop.close()


def test_hop_tao_kenh_vua_man_hinh(hop_tao_kenh):
    hop, _app = hop_tao_kenh
    goi = hop.minimumSizeHint()
    assert goi.width() <= TRAN_RONG, "hộp Kênh cần {0}px bề rộng".format(
        goi.width())
    assert goi.height() <= TRAN_CAO, "hộp Kênh cần {0}px chiều cao".format(
        goi.height())


def test_hop_tao_kenh_co_du_ba_o_chon(hop_tao_kenh):
    """Thiếu một ô là khuôn không ghép đủ ba mảnh."""
    hop, _app = hop_tao_kenh
    assert hop._c_nganh.count() >= 1
    assert hop._c_ve.count() >= 3
    assert hop._c_vh.count() >= 3


def test_hop_tao_kenh_hien_ten_tieng_viet_chu_khong_hien_ma(hop_tao_kenh):
    """CLAUDE.md: không dùng từ kỹ thuật trên giao diện.

    Để lọt mã thư mục (`ao-len-than`) lên ô chọn là khách nhìn thấy chữ không
    dấu viết dính.
    """
    hop, _app = hop_tao_kenh
    for o in (hop._c_nganh, hop._c_ve, hop._c_vh):
        for i in range(o.count()):
            assert o.itemText(i) != o.itemData(i), o.itemText(i)


def test_chon_phong_cach_thi_dien_san_loi_ta(hop_tao_kenh):
    """Chọn một phong cách ở Bước 3 phải điền sẵn ô lời tả + các khoá hình.

    Đây là cả điểm của bộ chọn: khách không phải tự viết khoá tiếng Anh nào,
    và đổi phong cách thì lời tả ảnh lẫn chuyển động video đổi theo — nhờ vậy
    prompt ảnh/video mới đồng bộ một kiểu.
    """
    from ui_qt.kenh import PHONG_CACH

    hop, app = hop_tao_kenh
    thay_anh = set()
    thay_video = set()
    for i in range(len(PHONG_CACH)):
        hop._chon_phong(i)
        app.processEvents()
        assert hop._o_style.text().strip(), "phong cách rỗng lời tả ảnh"
        thay_anh.add(hop._o_style.text())
        thay_video.add(hop._o_ve_khac["video_style"].text())
    assert len(thay_anh) == len(PHONG_CACH), "lời tả ảnh không đổi theo phong cách"
    assert len(thay_video) == len(PHONG_CACH), "video_style không đổi theo phong cách"


def test_moi_phong_cach_du_khoa_dong_bo_prompt(hop_tao_kenh):
    """Mỗi phong cách phải đủ bốn khoá prompt thật sự đọc, không được rỗng.

    `7-canh.md` cắm `image_style`/`video_style`/`palette`/`negative_prompt` vào
    đuôi mỗi prompt ảnh + video. Rỗng một khoá là một phong cách nhìn nhạt hơn
    hẳn các phong cách khác mà khách không hiểu vì sao.
    """
    import re

    from ui_qt.kenh import PHONG_CACH

    thieu = []
    for ten, kv in PHONG_CACH:
        for khoa in ("image_style", "video_style", "palette", "negative_prompt"):
            if not (kv.get(khoa) or "").strip():
                thieu.append("{0}: {1}".format(ten, khoa))
    assert not thieu, "phong cách thiếu khoá: {0}".format("; ".join(thieu))

    # Mỗi phong cách cần một `slug` duy nhất, kebab-case (đặt tên file ảnh mẫu +
    # cho AI trả về khi đoán từ ảnh khách tải lên).
    slugs = [kv.get("slug", "") for _t, kv in PHONG_CACH]
    assert all(slugs), "có phong cách thiếu slug"
    assert len(set(slugs)) == len(slugs), "slug trùng nhau"
    for s in slugs:
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s), "slug không kebab: " + s


def test_chon_slug_tu_tra_loi():
    """Hàm thuần rút slug từ câu trả lời AI — không gọi mạng."""
    from ui_qt.kenh import PHONG_CACH, _chon_slug_tu_tra_loi

    slugs = [kv.get("slug", "") for _t, kv in PHONG_CACH]
    assert "anime-net-phang" in slugs
    # Trả lời sạch → đúng slug.
    assert _chon_slug_tu_tra_loi("anime-net-phang", slugs) == "anime-net-phang"
    # Trả lời lẫn chữ thừa → vẫn rút được.
    assert _chon_slug_tu_tra_loi(
        "Tôi nghĩ là pixar-3d nhé", slugs) == "pixar-3d"
    # Trả lời rác → None (khách chọn tay).
    assert _chon_slug_tu_tra_loi("không biết", slugs) is None
    assert _chon_slug_tu_tra_loi("", slugs) is None



def test_di_het_nam_buoc_khong_tran_760px(hop_tao_kenh):
    """Bấm Tiếp đi hết 5 bước — không bước nào đẩy nút ra ngoài mép 760px.

    Trình thiết kế kênh giờ là một QStackedWidget năm trang. Bề rộng tối thiểu
    của hộp bằng trang rộng nhất, nên phải soi từng bước chứ không chỉ bước mở
    ra đầu tiên.
    """
    hop, app = hop_tao_kenh
    hop._di_toi(0)
    app.processEvents()
    tran = []
    for _ in range(10):                    # dư số bước, dừng ở bước cuối
        rong = hop.minimumSizeHint().width()
        if rong > TRAN_RONG:
            tran.append("bước {0} cần {1}px".format(hop._buoc + 1, rong))
        if hop._buoc >= len(hop._trang) - 1:
            break
        hop._tiep()                        # chưa tới bước cuối nên không tạo kênh
        app.processEvents()
    assert len(hop._trang) == 5, "phải có 5 bước, đang có {0}".format(
        len(hop._trang))
    assert not tran, "; ".join(tran)


def test_che_do_sua_nap_dung_kenh(cua_so):
    """Mở HopKenh với một mã kênh → vào thẳng chế độ sửa, năm bước nạp sẵn."""
    from ui_qt.kenh import HopKenh
    from core.kenh import liet_ke_kenh

    cs, app = cua_so
    ds = liet_ke_kenh(cs.base_dir)
    if not ds:
        pytest.skip("máy test chưa có kênh nào để mở chế độ sửa")
    hop = HopKenh(cs, ds[0], cs)
    app.processEvents()
    try:
        assert hop._che_do == "sua"
        assert hop._ma_sua == ds[0]
        assert len(hop._trang) == 5
        # Lời nhắc của kênh phải nạp được vào các ô sửa.
        assert hop._o_prompt, "chế độ sửa chưa nạp ô lời nhắc nào"
        for i in range(len(hop._trang)):
            hop._di_toi(i)
            app.processEvents()
            assert hop.minimumSizeHint().width() <= TRAN_RONG, \
                "bước {0} tràn mép".format(i + 1)
    finally:
        hop.close()


def test_buoc_cuoi_tao_duoc_kenh_chay_duoc(cua_so, monkeypatch):
    """Đi tới bước cuối rồi tạo → ra kênh mà `kiem_kenh` không kêu gì.

    Đây là cả điểm của luồng "bắt đầu từ mẫu": chọn kiểu vẽ + khán giả, điền
    giọng đọc, bấm Tạo là ra kênh chạy được — không phải tự viết khoá nào.
    """
    import shutil as _sh
    from ui_qt.kenh import HopKenh
    from core.kenh import doc_kenh, duong_kenh, kiem_kenh

    cs, app = cua_so
    hop = HopKenh(cs, "", cs)
    app.processEvents()
    if len(hop._trang) != 5:
        hop.close()
        pytest.skip("máy test chưa có mẫu khuôn để dựng kênh")

    ma = "ZZ-TEST-KENH"
    dich = duong_kenh(cs.base_dir, ma)
    _sh.rmtree(dich, ignore_errors=True)
    monkeypatch.setattr(cs, "show_message", lambda *a, **k: None)
    hop._o_ma.setText(ma)
    hop._o_giong.setText("test_voice_id")
    app.processEvents()
    try:
        hop._tao()
        assert os.path.isdir(dich), "chưa tạo được thư mục kênh"
        assert hop.ma_kenh_moi == ma
        assert kiem_kenh(doc_kenh(cs.base_dir, ma)) == [], \
            "kênh mới tạo mà vẫn thiếu điều kiện chạy"
    finally:
        hop.close()
        _sh.rmtree(dich, ignore_errors=True)



# ── Hộp "Sửa khuôn" ──────────────────────────────────────────────────────────
#
# Hộp này dựng lại form động mỗi lần đổi loại (Bộ vẽ có 18 ô, đổi sang Chiến
# lược chỉ còn 3 ô + tab lời nhắc). Một lỗi ở nhánh nào cũng chỉ lộ ra khi bấm
# đúng loại ấy — nên bài này quét cả bốn loại, không chỉ loại mở ra đầu tiên.


@pytest.fixture(scope="module")
def hop_soan_khuon(cua_so):
    from ui_qt.soan_khuon import HopSoanKhuon

    cs, app = cua_so
    hop = HopSoanKhuon(cs, cs)
    app.processEvents()
    yield hop, app
    hop.close()


def test_hop_soan_khuon_vua_be_rong_man_hinh(hop_soan_khuon):
    hop, _app = hop_soan_khuon
    goi = hop.minimumSizeHint()
    assert goi.width() <= TRAN_RONG, "hộp Sửa khuôn cần {0}px bề rộng".format(
        goi.width())


def test_hop_soan_khuon_dung_duoc_ca_bon_loai(hop_soan_khuon):
    """Đổi qua từng loại phải dựng form không văng, và ô mã theo đúng chế độ."""
    hop, app = hop_soan_khuon
    from core.soan_khuon import LOAI

    for i in range(hop._chon_loai.count()):
        hop._chon_loai.setCurrentIndex(i)
        app.processEvents()
        assert hop._chon_loai.currentData() in LOAI
        # Có ít nhất một ô nhãn được dựng cho loại này.
        assert hop._o, "loại {0} không dựng được ô nào".format(
            hop._chon_loai.currentData())


def test_hop_soan_khuon_chon_tao_moi_thi_mo_khoa_ma(hop_soan_khuon):
    """“➕ Tạo mới…” mở khoá ô mã; sửa bộ có sẵn thì khoá lại."""
    hop, app = hop_soan_khuon
    from ui_qt.soan_khuon import _TAO_MOI

    hop._chon_loai.setCurrentIndex(0)     # Bộ vẽ — chắc chắn có bộ sẵn
    app.processEvents()
    hop._chon_bo.setCurrentIndex(0)       # bộ có sẵn
    app.processEvents()
    assert not hop._o_ma.isEnabled(), "sửa bộ có sẵn phải khoá ô mã"

    i = hop._chon_bo.findData(_TAO_MOI)
    hop._chon_bo.setCurrentIndex(i)
    app.processEvents()
    assert hop._o_ma.isEnabled(), "Tạo mới phải mở khoá ô mã"

