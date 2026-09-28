"""Bài kiểm cho lõi `core/tu_choi_noi_dung.py` (gói G2).

Không mạng, không Qt, không phụ thuộc `auto_khau`/`dao_dien_auto`. Đồng hồ giả
ở khắp nơi để trần thời gian và "sức khoẻ khâu" kiểm được mà không phải ngồi
đợi thật. `CHUOI_CUU` bắt đầu RỖNG (G3+ mới đăng ký chuỗi thật) nên các bài
kiểm chuỗi cứu tự đăng ký một chuỗi GIẢ qua `dang_ky_chuoi`, rồi dọn lại bằng
fixture để không rò sang bài kiểm khác.
"""

from __future__ import annotations

import json
import os

import pytest

import core.tu_choi_noi_dung as m


# ── đồng hồ giả ──────────────────────────────────────────────────────────────


class DongHoGia:
    def __init__(self, bat_dau: float = 1_000_000.0) -> None:
        self.gio = bat_dau

    def __call__(self) -> float:
        return self.gio

    def qua(self, giay: float) -> None:
        self.gio += giay


@pytest.fixture(autouse=True)
def don_chuoi_cuu():
    """Mỗi bài kiểm chuỗi cứu chạy trên một `CHUOI_CUU` sạch, không rò sang
    bài khác (module dùng một `dict` toàn cục theo thiết kế đăng ký của G3+)."""
    truoc = dict(m.CHUOI_CUU)
    m.CHUOI_CUU.clear()
    yield
    m.CHUOI_CUU.clear()
    m.CHUOI_CUU.update(truoc)


# ── DauVao.van_tay(): băm BYTE, không băm đường dẫn ──────────────────────────


def test_van_tay_on_dinh_khi_doi_duong_dan_ma_byte_khong_doi(tmp_path):
    a = tmp_path / "a.png"
    b = tmp_path / "duong-dan-khac" / "b.png"
    b.parent.mkdir()
    a.write_bytes(b"noi-dung-anh-giong-het-nhau")
    b.write_bytes(b"noi-dung-anh-giong-het-nhau")

    dv1 = m.DauVao(khau="clip", canh=1, prompt="p", anh=str(a))
    dv2 = m.DauVao(khau="clip", canh=1, prompt="p", anh=str(b))

    assert dv1.van_tay() == dv2.van_tay(), \
        "tải lại đúng ảnh dưới URL/đường dẫn khác vẫn phải ra cùng vân tay"


def test_van_tay_doi_khi_byte_anh_doi(tmp_path):
    a = tmp_path / "a.png"
    a.write_bytes(b"anh-mot")
    dv1 = m.DauVao(khau="clip", canh=1, prompt="p", anh=str(a))
    vt1 = dv1.van_tay()  # tính NGAY, trước khi tệp bị ghi đè
    a.write_bytes(b"anh-hai")
    dv2 = m.DauVao(khau="clip", canh=1, prompt="p", anh=str(a))
    assert vt1 != dv2.van_tay()


def test_van_tay_doi_khi_prompt_doi_nhung_on_dinh_qua_khoang_trang():
    dv1 = m.DauVao(khau="anh_canh", canh=3, prompt="a lonely  man\nstanding")
    dv2 = m.DauVao(khau="anh_canh", canh=3, prompt="a lonely man standing")
    dv3 = m.DauVao(khau="anh_canh", canh=3, prompt="a different prompt")
    assert dv1.van_tay() == dv2.van_tay()
    assert dv1.van_tay() != dv3.van_tay()


# ── nhan_dien: các tín hiệu không cần trạng thái ─────────────────────────────


class _LoiMa(RuntimeError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


def test_tin_hieu_1_ma_ro_tren_anh_va_tren_tts():
    dv_anh = m.DauVao(khau="anh_canh", canh=1, prompt="p")
    loi = _LoiMa("vi phạm quy định. Bạn KHÔNG bị trừ tiền", "content_rejected")
    kl = m.nhan_dien(loi, dv_anh)
    assert kl is not None
    assert kl.nghi_do == "prompt"
    assert kl.do_chac == m.RO

    dv_tts = m.DauVao(khau="tts", canh=None, van_ban="xin chào")
    kl2 = m.nhan_dien(_LoiMa("vi phạm", "content_rejected"), dv_tts)
    assert kl2.nghi_do == "van_ban"


def test_tin_hieu_2_prompt_image_rejected_by_provider():
    dv = m.DauVao(khau="clip", canh=7, prompt="p", anh="7.png")
    loi = _LoiMa("đã thử 3 lần. Bạn KHÔNG bị trừ tiền", "prompt_image_rejected_by_provider")
    kl = m.nhan_dien(loi, dv)
    assert kl.nghi_do == "anh"
    assert kl.do_chac == m.AM_THAM_MAY_CHU

    dv_khong_anh = m.DauVao(khau="clip", canh=7, prompt="p")
    kl2 = m.nhan_dien(loi, dv_khong_anh)
    assert kl2.nghi_do == "prompt"


def test_tin_hieu_3_engine_unavailable_can_dung_cau_render_lap_lai():
    dv = m.DauVao(khau="clip", canh=1, prompt="p", anh="a.png")
    # Có mã nhưng câu KHÔNG nói "hai lần liền" -> không phải tín hiệu #3 (đây
    # là lỗi hạ tầng thường, để `nhan_dien` trả None).
    loi_thuong = _LoiMa("Hệ thống đang quá tải", "engine_unavailable")
    assert m.nhan_dien(loi_thuong, dv) is None

    loi_lap_lai = _LoiMa(
        "Google đã nhận yêu cầu nhưng hai lần liền không dựng xong clip",
        "engine_unavailable")
    kl = m.nhan_dien(loi_lap_lai, dv)
    assert kl is not None
    assert kl.nghi_do == "anh"
    assert kl.do_chac == m.AM_THAM_MAY_CHU


def test_tin_hieu_4_tep_anh():
    dv = m.DauVao(khau="anh_canh", canh=2, tham_chieu=("x.png",))
    kl = m.nhan_dien(_LoiMa("ảnh hỏng", "reference_image_unreadable"), dv)
    assert kl.nghi_do == "tep_anh"
    assert kl.do_chac == m.RO


def test_tin_hieu_5_giong_bi_khoa_goi_tra_phi():
    dv = m.DauVao(khau="tts", giong="mai")
    kl = m.nhan_dien(
        _LoiMa("Giọng này yêu cầu gói trả phí (subscription_required)", "invalid_request"), dv)
    assert kl is not None
    assert kl.nghi_do == "giong"

    # invalid_request nhưng không nói gì về giọng -> không phải tín hiệu #5.
    assert m.nhan_dien(_LoiMa("tham số sai", "invalid_request"), dv) is None


def test_tin_hieu_6_van_ban_qua_dai():
    dv = m.DauVao(khau="tts", van_ban="x" * 5000)
    kl = m.nhan_dien(_LoiMa("text quá dài, tối đa 4000 ký tự", "invalid_request"), dv)
    assert kl.nghi_do == "van_ban"


def test_tin_hieu_8_llm_tra_200_nhung_la_cau_tu_choi():
    dv = m.DauVao(khau="kich_ban", prompt="viết truyện")
    cau_ngan = "I cannot help with that request."
    kl = m.nhan_dien(cau_ngan, dv, do_dai_ky_vong=1000)
    assert kl is not None
    assert kl.nghi_do == "prompt"

    # Câu DÀI có chữ "cannot" ở giữa một bài viết bình thường -> KHÔNG bị coi
    # là từ chối (tỉ lệ độ dài không đạt).
    cau_dai = "Ngày xưa có một chàng trai không biết mình cannot làm gì. " * 40
    assert m.nhan_dien(cau_dai, dv, do_dai_ky_vong=1000) is None

    # Không có `do_dai_ky_vong` thì không kết luận được (thiếu cơ sở so sánh).
    assert m.nhan_dien(cau_ngan, dv, do_dai_ky_vong=None) is None


def test_loi_khong_lien_quan_thi_tra_none():
    dv = m.DauVao(khau="clip", canh=1, prompt="p")
    assert m.nhan_dien(ConnectionError("network unreachable"), dv) is None
    assert m.nhan_dien(_LoiMa("Hệ thống quá tải", "service_unavailable"), dv) is None


# ── SucKhoe: sống/ốm theo cửa sổ 30' ─────────────────────────────────────────


def test_suc_khoe_song_khi_du_nguong_trong_cua_so():
    dh = DongHoGia()
    sk = m.SucKhoe(dong_ho=dh)
    assert sk.khau_dang_song("video") is False
    sk.ghi_xong("video")
    assert sk.khau_dang_song("video") is True  # ngưỡng video = 1

    assert sk.khau_dang_song("anh") is False
    sk.ghi_xong("anh")
    sk.ghi_xong("anh")
    assert sk.khau_dang_song("anh") is False  # ngưỡng ảnh = 3
    sk.ghi_xong("anh")
    assert sk.khau_dang_song("anh") is True


def test_suc_khoe_het_han_ngoai_cua_so_30_phut():
    dh = DongHoGia()
    sk = m.SucKhoe(dong_ho=dh)
    sk.ghi_xong("video")
    assert sk.khau_dang_song("video") is True
    dh.qua(31 * 60)
    assert sk.khau_dang_song("video") is False


# ── SoCuu: sổ đọc/ghi, ghi hỏng không ném ────────────────────────────────────


def test_so_cuu_ghi_roi_doc_lai(tmp_path):
    duong = str(tmp_path / "tu-choi.json")
    so1 = m.SoCuu(duong_tep=duong)
    dv = m.DauVao(khau="clip", canh=9, prompt="p", anh="")
    kl = m.KetLuanTuChoi("clip", "prompt", "content_rejected", m.RO, 1, "vi phạm")
    so1.ghi_ket_luan(dv, kl)

    assert os.path.exists(duong)
    with open(duong, "r", encoding="utf-8") as f:
        tho = json.load(f)
    assert dv.van_tay() in tho["dau_vao"]

    so2 = m.SoCuu(duong_tep=duong)
    assert so2.cho_gui(dv) is False
    kl2 = so2.ket_luan_da_biet(dv)
    assert kl2 is not None and kl2.ma == "content_rejected"


def test_so_cuu_ghi_hong_khong_nem(tmp_path):
    # Trỏ đường ghi vào một THƯ MỤC (không phải tệp) -> `ghi_json` chắc chắn
    # hỏng khi mở để ghi. `_luu` phải nuốt lỗi, không được ném lên.
    thu_muc_gia = tmp_path / "day-la-thu-muc"
    thu_muc_gia.mkdir()
    dong_bao = []
    so = m.SoCuu(duong_tep=str(thu_muc_gia), on_log=dong_bao.append)
    dv = m.DauVao(khau="clip", canh=1, prompt="p")
    kl = m.KetLuanTuChoi("clip", "prompt", "content_rejected", m.RO, 1, "x")
    so.ghi_ket_luan(dv, kl)  # không được ném
    assert any("[sổ]" in d for d in dong_bao)


def test_so_cuu_cho_gui_va_bat_bien_khong_gui_lai():
    so = m.SoCuu()
    dv = m.DauVao(khau="clip", canh=1, prompt="p")
    assert so.cho_gui(dv) is True
    kl = m.KetLuanTuChoi("clip", "prompt", "content_rejected", m.RO, 1, "x")
    so.ghi_ket_luan(dv, kl)
    assert so.cho_gui(dv) is False
    # Vân tay khác (prompt khác) thì được gửi bình thường.
    dv2 = m.DauVao(khau="clip", canh=1, prompt="p khac")
    assert so.cho_gui(dv2) is True


# ── luật #7 (`bao_hong`): cần sức khoẻ khâu ───────────────────────────────────


class _LoiKetJobGia(RuntimeError):
    """Mô phỏng `auto_khau.LoiKetJob`/`LoiQuaHan` — mang `.ma_loi`, không có
    `.code` (module đọc `.code` trước, `.ma_loi` sau, xem `_doc_ma_va_cau`)."""

    def __init__(self, message: str, ma_loi: str = "") -> None:
        super().__init__(message)
        self.ma_loi = ma_loi


def test_bao_hong_ket_luan_khi_du_2_lan_va_khau_con_song():
    dh = DongHoGia()
    so = m.SoCuu(dong_ho=dh)
    dv = m.DauVao(khau="clip", canh=5, prompt="p", anh="a.png")
    loi = _LoiKetJobGia("máy chủ báo job hỏng (đã hoàn tiền): x", "engine_unavailable")

    # Lần 1: chưa đủ.
    assert so.bao_hong(dv, loi) is None
    # Chưa có job nào khác của khâu "video" xong -> dù đến lần 2 vẫn KHÔNG kết
    # luận, vì không phân biệt được với "cả khâu đang ốm" (hạ tầng).
    assert so.bao_hong(dv, loi) is None

    # Bây giờ có ít nhất một clip khác đã xong trong lượt -> khâu "video" đang
    # sống -> lần hỏng liên tiếp thứ 3 (>=2 kể từ đây) mới đủ điều kiện.
    so.bao_xong("video")
    kl = so.bao_hong(dv, loi)
    assert kl is not None
    assert kl.nghi_do == "chua_ro"
    assert kl.do_chac == m.AM_THAM_CUC_BO
    # Đã kết luận -> vân tay bị chặn gửi lại.
    assert so.cho_gui(dv) is False


def test_bao_hong_khong_ket_luan_khi_khau_dang_om():
    """KHÔNG có job nào cùng loại xong gần đây (cả khâu ốm) -> dù hỏng lặp lại
    bao nhiêu lần với cùng vân tay, đây vẫn không phải kết luận nội dung."""
    dh = DongHoGia()
    so = m.SoCuu(dong_ho=dh)
    dv = m.DauVao(khau="clip", canh=5, prompt="p", anh="a.png")
    loi = _LoiKetJobGia("máy chủ báo job hỏng (đã hoàn tiền): x", "engine_unavailable")
    for _ in range(6):
        assert so.bao_hong(dv, loi) is None
    assert so.cho_gui(dv) is True


def test_anh_la_ban_lui_doc_dung_dau_khau_khac_da_ghi():
    """Cầu nối GIỮA khâu (mục 2.5 tài liệu): khâu ẢNH ghi cảnh này là LÙI
    (mượn/bối cảnh không người) — khâu CLIP đọc lại đúng cờ ấy, không cần biết
    gì về `DauVao`/`KetLuanTuChoi` của khâu ảnh."""
    so = m.SoCuu()
    dv_anh = m.DauVao(khau="anh_canh", canh=5, prompt="p")
    ket_lui = m.KetQuaLui("anh_boi_canh", dv_anh, "mượn ảnh bối cảnh", {})
    so.ghi_ket_qua_canh(dv_anh, ["viet_lai_prompt", "anh_boi_canh"], lui=True)
    assert so.anh_la_ban_lui(5) is True
    assert so.anh_la_ban_lui(6) is False
    assert so.anh_la_ban_lui(None) is False


def test_thu_nho_da_that_bai_theo_nhan_vat():
    so = m.SoCuu()
    assert so.thu_nho_da_that_bai(("nv1",)) is False
    so.danh_dau_thu_nho_that_bai(("nv1", "nv2"))
    assert so.thu_nho_da_that_bai(("nv1",)) is True
    assert so.thu_nho_da_that_bai(("nv2",)) is True
    assert so.thu_nho_da_that_bai(("nv3",)) is False
    assert so.thu_nho_da_that_bai(()) is False


def test_gui_nem_loi_tu_choi_thi_dung_thang_ket_luan_khong_goi_nhan_dien_lai():
    """Móc "hai đầu vào" (mục 2.9): một `gui()` tự canh vòng thử-lại-không-trần
    CỦA NÓ, tự gọi `so_cuu.bao_hong` và tự ném `LoiTuChoi` khi đủ luật #7 —
    `lam_co_cuu` phải DÙNG THẲNG `.ket_luan` mang theo, không gọi lại
    `nhan_dien` (vốn sẽ không nhận ra một `LoiTuChoi` là gì) và không ghi sổ
    hai lần (đã ghi trong `bao_hong` rồi)."""
    so = m.SoCuu()
    dv = m.DauVao(khau="clip", canh=1, prompt="p", anh="a.png")
    ket_luan_da_ghi = m.KetLuanTuChoi("clip", "chua_ro", "engine_unavailable",
                                      m.AM_THAM_CUC_BO, 2, "treo")
    so.ghi_ket_luan(dv, ket_luan_da_ghi)  # mô phỏng: `bao_hong` đã ghi rồi

    def gui(dv_, hau_to):
        raise m.LoiTuChoi(ket_luan_da_ghi)

    def xong(goi, dv_):  # pragma: no cover
        raise AssertionError("không tới đây")

    with pytest.raises(m.LoiTuChoi):
        m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    # `so_lan` không bị tăng thêm lần thứ hai bởi `ghi_ket_luan` gọi lại.
    assert so.ket_luan_da_biet(dv).so_lan == 1


def test_bao_hong_re_hang_ngay_qua_nhan_dien_neu_co_ma_ro():
    """`bao_hong` cũng phải bắt được tín hiệu RÕ (không chỉ luật #7)."""
    so = m.SoCuu()
    dv = m.DauVao(khau="anh_canh", canh=1, prompt="p")
    loi = _LoiMa("vi phạm quy định", "content_rejected")
    kl = so.bao_hong(dv, loi)
    assert kl is not None
    assert kl.do_chac == m.RO


# ── trần theo cảnh: số bước trả tiền + thời gian ─────────────────────────────


def test_tran_so_buoc_tra_tien_moi_canh():
    so = m.SoCuu(cau_hinh=m.CauHinhTran(buoc_moi_canh=2))
    dv = m.DauVao(khau="anh_canh", canh=1, prompt="p")
    assert so.con_buoc(dv) is True
    so.ghi_buoc_tra_tien(dv)
    assert so.con_buoc(dv) is True
    so.ghi_buoc_tra_tien(dv)
    assert so.con_buoc(dv) is False
    # Cảnh KHÁC không bị ảnh hưởng.
    dv2 = m.DauVao(khau="anh_canh", canh=2, prompt="p")
    assert so.con_buoc(dv2) is True


def test_tran_thoi_gian_moi_canh():
    dh = DongHoGia()
    so = m.SoCuu(dong_ho=dh, cau_hinh=m.CauHinhTran(phut_moi_canh=1.0))
    dv = m.DauVao(khau="clip", canh=1, prompt="p")
    so.bat_dau_canh_neu_chua(dv)
    assert so.con_thoi_gian(dv) is True
    dh.qua(61)
    assert so.con_thoi_gian(dv) is False


def test_tran_ngan_sach_theo_luot():
    so = m.SoCuu(tong_so_canh=10, cau_hinh=m.CauHinhTran(tran_anh=2))
    assert so.con_ngan_sach("anh") is True
    so.ghi_chi_phi("anh", 2)
    assert so.con_ngan_sach("anh") is False
    # Loại không được cấu hình trần (rỗng) luôn được coi là còn ngân sách.
    assert so.con_ngan_sach("") is True


def test_tran_ngan_sach_cong_thuc_mac_dinh_theo_ty_le_va_san():
    so_it_canh = m.SoCuu(tong_so_canh=4)  # 15% * 4 = 0 -> sàn 10
    assert so_it_canh._tran("anh") == 10
    so_nhieu_canh = m.SoCuu(tong_so_canh=200)  # 15% * 200 = 30 > sàn
    assert so_nhieu_canh._tran("anh") == 30


# ── `lam_co_cuu`: bất biến, Cancelled/HET_TIEN xuyên qua, chuỗi cứu ─────────


class Cancelled(RuntimeError):
    """Trùng TÊN LỚP với `core.auto.Cancelled` — module nhận diện theo tên."""


def test_gui_thanh_cong_ngay_khong_dung_den_chuoi_cuu():
    so = m.SoCuu()
    dv = m.DauVao(khau="clip", canh=1, prompt="p")
    so_lan = {"gui": 0, "xong": 0}

    def gui(dv_, hau_to):
        so_lan["gui"] += 1
        return {"id": "job1"}

    def xong(goi, dv_):
        so_lan["xong"] += 1

    ket = m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    assert so_lan == {"gui": 1, "xong": 1}
    assert ket.la_duong_lui is False
    assert ket.buoc == []


def test_hang_ha_tang_nem_lai_nguyen_van_khong_dung_module():
    so = m.SoCuu()
    dv = m.DauVao(khau="clip", canh=1, prompt="p")

    def gui(dv_, hau_to):
        raise _LoiMa("Hệ thống đang quá tải", "service_unavailable")

    def xong(goi, dv_):  # pragma: no cover
        raise AssertionError("không tới đây")

    with pytest.raises(_LoiMa):
        m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    # Lỗi hạ tầng KHÔNG được ghi vào sổ như một kết luận nội dung.
    assert so.cho_gui(dv) is True


def test_cancelled_di_xuyen_qua_khong_bi_nuot():
    so = m.SoCuu()
    dv = m.DauVao(khau="clip", canh=1, prompt="p")

    def gui(dv_, hau_to):
        raise Cancelled("người dùng bấm Dừng")

    def xong(goi, dv_):  # pragma: no cover
        raise AssertionError("không tới đây")

    with pytest.raises(Cancelled):
        m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    assert so.cho_gui(dv) is True


def test_het_tien_di_xuyen_qua():
    so = m.SoCuu()
    dv = m.DauVao(khau="clip", canh=1, prompt="p")

    def gui(dv_, hau_to):
        raise _LoiMa("Ví của bạn không đủ số dư để thực hiện yêu cầu này", "insufficient_balance")

    def xong(goi, dv_):  # pragma: no cover
        raise AssertionError("không tới đây")

    with pytest.raises(_LoiMa):
        m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    assert so.cho_gui(dv) is True


def test_khong_bao_gio_gui_lai_van_tay_da_ket_luan():
    """Bất biến cốt lõi: gọi `lam_co_cuu` hai lần với CÙNG `dv` đã bị kết luận
    nội dung ở lần đầu (chuỗi cứu rỗng nên DỪNG hẳn) — lần hai KHÔNG được gọi
    `gui` một lần nào nữa."""
    so = m.SoCuu()
    dv = m.DauVao(khau="clip", canh=1, prompt="p")
    so_lan_gui = {"n": 0}

    def gui(dv_, hau_to):
        so_lan_gui["n"] += 1
        raise _LoiMa("vi phạm quy định", "content_rejected")

    def xong(goi, dv_):  # pragma: no cover
        raise AssertionError("không tới đây")

    with pytest.raises(m.LoiTuChoi):
        m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    assert so_lan_gui["n"] == 1

    with pytest.raises(m.LoiTuChoi) as exc:
        m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    assert so_lan_gui["n"] == 1, "lần hai không được gọi gui() lại"
    assert exc.value.ket_luan.ma == "content_rejected"


def test_gui_hong_ngau_nhien_cuoi_cung_van_khong_gui_lai_van_tay_bi_chan(monkeypatch):
    """`gui` giả hỏng NGẪU NHIÊN theo nhiều vân tay khác nhau (nhiều cảnh) —
    dù thứ tự có xáo trộn thế nào, một khi MỘT vân tay đã bị kết luận thì đúng
    vân tay ấy không bao giờ được gửi lần hai."""
    import random
    rnd = random.Random(42)
    so = m.SoCuu()
    da_ket_luan = set()
    tong_so_lan_gui = {}

    for _ in range(200):
        canh = rnd.randint(1, 5)
        dv = m.DauVao(khau="clip", canh=canh, prompt="p{0}".format(canh))
        vt = dv.van_tay()
        if vt in da_ket_luan:
            assert so.cho_gui(dv) is False
            continue

        def gui(dv_, hau_to):
            tong_so_lan_gui[vt] = tong_so_lan_gui.get(vt, 0) + 1
            raise _LoiMa("vi phạm quy định", "content_rejected")

        def xong(goi, dv_):  # pragma: no cover
            raise AssertionError("không tới đây")

        with pytest.raises(m.LoiTuChoi):
            m.lam_co_cuu(so, dv, gui=gui, xong=xong)
        da_ket_luan.add(vt)

    assert all(n == 1 for n in tong_so_lan_gui.values())


# ── `lam_co_cuu` với một chuỗi cứu (giả) đăng ký qua `dang_ky_chuoi` ─────────


def _chuoi_gia_sua_prompt_thanh_cong():
    """Một bước: viết lại prompt (giả), rồi gửi lại — THÀNH CÔNG."""

    def ap(so_cuu, dv, ket_luan, cong_cu):
        return __import__("dataclasses").replace(dv, prompt=dv.prompt + " (đã viết lại)")

    return m.BuocCuu("viet_lai_gia", frozenset({"prompt", "chua_ro"}), {"chat": 1}, False, ap)


def _chuoi_gia_lui():
    def ap(so_cuu, dv, ket_luan, cong_cu):
        return m.KetQuaLui("lui_gia", dv, "hết cách, dùng bản lùi", {"nguon": dv.anh})

    return m.BuocCuu("lui_gia", frozenset(m.NGHI_DO), {}, True, ap)


def test_chuoi_cuu_thanh_cong_o_buoc_dau():
    m.dang_ky_chuoi("anh_canh", [_chuoi_gia_sua_prompt_thanh_cong(), _chuoi_gia_lui()])
    so = m.SoCuu(tong_so_canh=10)
    dv = m.DauVao(khau="anh_canh", canh=3, prompt="a lonely man")
    so_lan = {"n": 0}

    def gui(dv_, hau_to):
        so_lan["n"] += 1
        if so_lan["n"] == 1:
            raise _LoiMa("vi phạm quy định", "content_rejected")
        assert "đã viết lại" in dv_.prompt
        return {"id": "job2"}

    def xong(goi, dv_):
        pass

    ket = m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    assert ket.la_duong_lui is False
    assert ket.buoc == ["viet_lai_gia"]
    assert ket.chi_phi.get("chat") == 1
    assert ket.chi_phi.get("anh") == 1  # `_LOAI_CHI_PHI_THEO_KHAU["anh_canh"] == "anh"`
    # Sổ đã ghi cảnh này là "xong", không phải "lùi". Khoá "khâu:cảnh" (rà
    # soát 2.138.0, H3 — trước là "3" trần, trùng giữa các khâu).
    assert so._so["canh"]["anh_canh:3"]["ket_qua"] == "xong"


def test_chuoi_cuu_roi_xuong_buoc_lui_khi_buoc_dau_van_hong():
    m.dang_ky_chuoi("clip", [_chuoi_gia_sua_prompt_thanh_cong(), _chuoi_gia_lui()])
    so = m.SoCuu(tong_so_canh=10)
    dv = m.DauVao(khau="clip", canh=8, prompt="p", anh="8.png")
    dong_bao = []
    so.on_log = dong_bao.append

    goi_lui = {}

    def xong_lui(ket_qua_lui, dv_dung):
        goi_lui["nguon"] = ket_qua_lui.du_lieu.get("nguon")

    def gui(dv_, hau_to):
        raise _LoiMa("vi phạm quy định", "content_rejected")

    def xong(goi, dv_):  # pragma: no cover
        raise AssertionError("không tới đây")

    ket = m.lam_co_cuu(so, dv, gui=gui, xong=xong, xong_lui=xong_lui)
    assert ket.la_duong_lui is True
    assert ket.buoc == ["viet_lai_gia", "lui_gia"]
    assert goi_lui["nguon"] == "8.png"
    assert any("[LÙI]" in d for d in dong_bao)
    assert so._so["canh"]["clip:8"]["lui"] is True  # khoá "khâu:cảnh" (H3)


def test_chuoi_cuu_het_tran_buoc_nhay_thang_toi_buoc_lui():
    """`buoc_moi_canh=0` (đã hết trần trả tiền ngay từ đầu) -> bước sửa prompt
    (trả tiền) phải bị BỎ QUA, và rơi thẳng xuống bước LÙI miễn phí."""
    m.dang_ky_chuoi("clip", [_chuoi_gia_sua_prompt_thanh_cong(), _chuoi_gia_lui()])
    so = m.SoCuu(tong_so_canh=10, cau_hinh=m.CauHinhTran(buoc_moi_canh=0))
    dv = m.DauVao(khau="clip", canh=1, prompt="p", anh="1.png")

    def gui(dv_, hau_to):
        raise _LoiMa("vi phạm quy định", "content_rejected")

    def xong(goi, dv_):  # pragma: no cover
        raise AssertionError("không tới đây")

    ket = m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    assert ket.la_duong_lui is True
    assert ket.buoc == ["lui_gia"]


def test_het_chuoi_ma_khong_co_buoc_lui_thi_dung_han():
    m.dang_ky_chuoi("clip", [_chuoi_gia_sua_prompt_thanh_cong()])  # không có bước lùi
    so = m.SoCuu(tong_so_canh=10)
    dv = m.DauVao(khau="clip", canh=1, prompt="p", anh="1.png")

    def gui(dv_, hau_to):
        raise _LoiMa("vi phạm quy định", "content_rejected")

    def xong(goi, dv_):  # pragma: no cover
        raise AssertionError("không tới đây")

    with pytest.raises(m.LoiTuChoi):
        m.lam_co_cuu(so, dv, gui=gui, xong=xong)


def test_buoc_tra_ve_vao_tay_da_ket_luan_khong_goi_mang_lai():
    """Một bước cứu vô tình trả về đúng `DauVao` (cùng vân tay) đã bị kết luận
    ở lần gửi đầu — bất biến #2 phải thắng NGAY TẠI ĐÂY: không được gọi
    `gui()` thêm một lần nào cho đúng vân tay đã chặn, kể cả khi lời gọi đó
    đến từ một bước cứu, không phải từ vòng thử-lại-y-nguyên bên ngoài."""

    def ap_tra_ve_y_het(so_cuu, dv, ket_luan, cong_cu):
        return dv  # cố tình không sửa gì — mô phỏng một bước lỗi/vô tác dụng

    buoc_loi = m.BuocCuu("buoc_loi", frozenset({"prompt", "chua_ro"}), {}, False, ap_tra_ve_y_het)
    m.dang_ky_chuoi("clip", [buoc_loi, _chuoi_gia_lui()])
    so = m.SoCuu(tong_so_canh=10)
    dv = m.DauVao(khau="clip", canh=1, prompt="p", anh="1.png")
    so_lan_goi = {"n": 0}

    def gui(dv_, hau_to):
        so_lan_goi["n"] += 1
        raise _LoiMa("vi phạm quy định", "content_rejected")

    def xong(goi, dv_):  # pragma: no cover
        raise AssertionError("không tới đây")

    ket = m.lam_co_cuu(so, dv, gui=gui, xong=xong)
    assert ket.la_duong_lui is True
    assert ket.buoc == ["buoc_loi", "lui_gia"]
    # CHỈ lần gửi đầu tiên gọi mạng — bước cứu trả về cùng vân tay thì module
    # tự nhận ra (qua `cho_gui`) và đi thẳng vào kết luận cũ, không gửi lại.
    assert so_lan_goi["n"] == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
