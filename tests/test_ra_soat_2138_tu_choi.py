"""Rà soát trước phát hành 2.138.0 — bộ xử lý "nội dung bị từ chối".

Mỗi bài dưới đây canh ĐÚNG một lỗi rà soát đã tìm ra (H1–H5, MEDIUM, LOW).
Không gọi mạng: mọi hàm chạm máy chủ (`_tao_anh`, `videos.create`, tải kết
quả…) đều thay bằng hàm giả; đồng hồ giả ở chỗ cần đo trần thời gian.
"""
from __future__ import annotations

import json
import os
import threading
from types import SimpleNamespace

import pytest

import core.auto_khau as ak
import core.dao_dien_auto as dd
import core.tu_choi_noi_dung as tcnd


@pytest.fixture(autouse=True)
def don_so_cuu_theo_luot():
    ak._SO_CUU_THEO_LUOT.clear()
    yield
    ak._SO_CUU_THEO_LUOT.clear()


@pytest.fixture
def chuoi_sach():
    """Cho các bài tự đăng ký chuỗi giả — trả lại chuỗi thật sau bài."""
    truoc = dict(tcnd.CHUOI_CUU)
    yield
    tcnd.CHUOI_CUU.clear()
    tcnd.CHUOI_CUU.update(truoc)


class DongHo:
    def __init__(self, t: float = 1_000_000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def qua(self, giay: float) -> None:
        self.t += giay


class _LoiMa(RuntimeError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


class Cancelled(RuntimeError):
    """Trùng TÊN LỚP `core.auto.Cancelled` — module nhận diện theo tên."""


def _bc(**kenh):
    dong = []
    k = dict(mo_hinh="claude-sonnet-5", che_do_ke="", anh_nv=[], engine="veo3", style={})
    k.update(kenh)
    return SimpleNamespace(kenh=SimpleNamespace(**k), ghi=dong.append, _nhat_ky=dong,
                           goi_chat=lambda l, **kw: "", kiem_dung=lambda: None,
                           ngu=lambda _g: None, on_log=None, ffmpeg="ffmpeg-gia",
                           client=object()), dong


def _luot(tmp_path, so_canh=20, thu_muc=None):
    d = str(thu_muc or tmp_path)
    os.makedirs(d, exist_ok=True)
    if so_canh:
        with open(os.path.join(d, "4-canh.json"), "w", encoding="utf-8") as f:
            json.dump([{"scene_id": i} for i in range(1, so_canh + 1)], f)
    return SimpleNamespace(ma_kenh="k", ma_luot="0001", thu_muc=d)


class _HopRong:
    def lay(self):
        return []

    def lam_moi(self, cu):
        return []


def _gia_clip(monkeypatch, cong_cu=None):
    monkeypatch.setattr(ak, "_url_anh_canh",
                        lambda bc, luot, so_canh, duong, bo_qua_nho=False:
                        "http://anh/" + os.path.basename(duong))
    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_kiem_media", lambda *a, **k: None)

    def tai(bc, goi, _i, duong):
        os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
        with open(duong, "wb") as f:
            f.write(b"clip-" + str(goi.get("id")).encode())

    monkeypatch.setattr(ak, "_tai_ket_qua", tai)
    dong = []

    def anh_dong(bc, luot, c, nguon, dich_, giay, so_canh):
        dong.append(nguon)
        with open(dich_, "wb") as f:
            f.write(b"anh-dong")

    monkeypatch.setattr(ak, "_dung_anh_dong_thay_clip", anh_dong)
    if cong_cu is not None:
        monkeypatch.setattr(ak, "_cong_cu_auto", lambda bc, luot, c, so: cong_cu)
    return dong


class _CongCuGia:
    def __init__(self, ve_anh=None, viet_lai=None):
        self._ve = ve_anh
        self._vl = viet_lai
        self.ve_anh_goi = []

    def ve_anh(self, prompt, tham_chieu, khoa_phu):
        self.ve_anh_goi.append((prompt, tuple(tham_chieu), khoa_phu))
        if isinstance(self._ve, BaseException):
            raise self._ve
        return self._ve

    def viet_lai(self, prompt, ly_do, loai):
        if isinstance(self._vl, BaseException):
            raise self._vl
        return self._vl

    def anh_dong(self, *a):  # pragma: no cover
        pass

    def ghi(self, d):
        pass

    def kiem_dung(self):
        pass


# ═══ H1: số cảnh đọc LÚC KIỂM TRẦN, không chốt 0 lúc tạo sổ ═══════════════════


def test_h1_so_tao_truoc_bang_canh_van_co_tran_chat(tmp_path):
    """Sổ tạo từ khâu GIỌNG (chưa có 4-canh.json) → trần chat từng chốt 0 cả
    phiên, tắt lặng lẽ bước AI viết lại (hồi quy so với 2.137.10)."""
    bc, _ = _bc()
    luot = _luot(tmp_path, so_canh=0)
    so_cuu = ak._so_cuu_cua_luot(bc, luot)          # tạo lúc CHƯA có bảng cảnh
    assert so_cuu.con_ngan_sach("chat") is False     # 0 cảnh → trần chat 0 là đúng lúc này
    with open(os.path.join(luot.thu_muc, "4-canh.json"), "w", encoding="utf-8") as f:
        json.dump([{"scene_id": i} for i in range(1, 21)], f)
    assert ak._so_cuu_cua_luot(bc, luot) is so_cuu  # vẫn CHUNG một sổ
    assert so_cuu._tran("chat") == 40                # 2 × 20 cảnh, đọc lại lúc kiểm
    assert so_cuu.con_ngan_sach("chat") is True


# ═══ H2: MỘT sổ cho cả lượt; ghi đọc-hợp-ghi ═════════════════════════════════


def test_h2_khau_bang_canh_truyen_so_chung_cho_tao_tham_chieu(tmp_path, monkeypatch):
    bc, _ = _bc(che_do_ke="tu_xay")
    luot = _luot(tmp_path, so_canh=0)
    d = luot.thu_muc
    with open(os.path.join(d, "3-phu-de.srt"), "w", encoding="utf-8") as f:
        f.write("1\n00:00:00,000 --> 00:00:01,000\nxin chao\n")
    with open(os.path.join(d, "4-canh.json"), "w", encoding="utf-8") as f:
        json.dump([{"scene_id": 1, "img_prompt": "a cat"}], f)
    with open(os.path.join(d, dd.TEP_DAN), "w", encoding="utf-8") as f:
        json.dump({"characters": [], "locations": []}, f)
    nhan = {}

    def tao_tham_chieu_gia(bc_, luot_, man, *, canh=None, so_cuu=None, **kw):
        nhan["so_cuu"] = so_cuu
        return []

    monkeypatch.setattr(dd, "che_do_dao_dien", lambda kenh: True)
    monkeypatch.setattr(dd, "tao_tham_chieu", tao_tham_chieu_gia)
    monkeypatch.setattr(ak, "_viet_xlsx", lambda *a, **k: None)

    ak._khau_bang_canh(bc)(luot, None)

    assert nhan["so_cuu"] is not None, "phải TRUYỀN sổ chung, không để khâu tham chiếu tự dựng"
    assert nhan["so_cuu"] is ak._so_cuu_cua_luot(bc, luot)


def test_h2_tao_tham_chieu_khong_truyen_so_van_dung_so_chung(tmp_path):
    bc, _ = _bc()
    luot = _luot(tmp_path)
    so_chung = ak._so_cuu_cua_luot(bc, luot)
    man = {"characters": [{"id": "nv1", "sheet_prompt": "a cat"}], "locations": []}

    def tao_anh(ma_id, prompt, dich, tham_chieu=None):
        raise RuntimeError("content_rejected")

    dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh, goi_ai=lambda l: "không có json")
    # Sổ CHUNG (trong bộ nhớ) thấy ngay phần khâu tham chiếu vừa ghi.
    assert so_chung.so_xac_nhan_nguy_co("nv1") == 1


def test_h2_hai_ban_so_cung_tep_khong_de_mat_phan_ghi_cua_nhau(tmp_path):
    duong = str(tmp_path / "tu-choi.json")
    a = tcnd.SoCuu(duong_tep=duong, tong_so_canh=20)
    b = tcnd.SoCuu(duong_tep=duong, tong_so_canh=20)
    a.ghi_ket_qua_canh(tcnd.DauVao(khau="anh_canh", canh=3), ["x"], lui=True)
    b.ghi_nguy_co_nhan_vat(["nv2"], "mat_that", [4], xac_nhan=["clip:4"])
    a.ghi_chi_phi("anh", 2)
    b.ghi_chi_phi("anh", 1)
    with open(duong, encoding="utf-8") as f:
        tren_dia = json.load(f)
    assert tren_dia["canh"]["anh_canh:3"]["lui"] is True, "phần ghi của bản A bị bản B đè mất"
    assert tren_dia["nhan_vat"]["nv2"]["xac_nhan"] == ["clip:4"]
    assert tren_dia["chi_phi"]["anh"] == 3, "chi phí hai bản phải CỘNG, không đè"


# ═══ H3: dấu lùi khoá theo "khâu:cảnh", xoá khi gửi thành công ═══════════════


def test_h3_dau_lui_cua_clip_hay_giong_khong_phai_anh_lui():
    so = tcnd.SoCuu()
    so.ghi_ket_qua_canh(tcnd.DauVao(khau="clip", canh=7), ["anh_dong"], lui=True)
    so.ghi_ket_qua_canh(tcnd.DauVao(khau="tts", canh=7), ["viet_lai_doan_doc"], lui=True)
    assert so.anh_la_ban_lui(7) is False
    so.ghi_ket_qua_canh(tcnd.DauVao(khau="anh_canh", canh=7), ["anh_boi_canh"], lui=True)
    assert so.anh_la_ban_lui(7) is True
    assert set(so._so["canh"]) == {"clip:7", "tts:7", "anh_canh:7"}


def test_h3_gui_thanh_cong_xoa_dau_lui_cu_cua_dung_khau_canh():
    so = tcnd.SoCuu()
    dv = tcnd.DauVao(khau="anh_canh", canh=5, prompt="a cat")
    so.ghi_ket_qua_canh(dv, ["anh_boi_canh"], lui=True)
    assert so.anh_la_ban_lui(5) is True
    tcnd.lam_co_cuu(so, dv, gui=lambda d, h: {"id": "j"}, xong=lambda g, d: None)
    assert so.anh_la_ban_lui(5) is False, "làm lại khâu ảnh ra ảnh thật thì hết là bản lùi"


def test_h3_so_kieu_cu_khoa_so_canh_van_doc_va_duoc_xoa():
    so = tcnd.SoCuu()
    so._so["canh"]["5"] = {"khau": "anh_canh", "buoc": ["anh_boi_canh"], "lui": True}
    so._so["canh"]["6"] = {"khau": "clip", "buoc": ["anh_dong"], "lui": True}
    assert so.anh_la_ban_lui(5) is True
    assert so.anh_la_ban_lui(6) is False, "dấu cũ của khâu CLIP không phải ảnh lùi"
    so.xoa_ket_qua_canh(tcnd.DauVao(khau="anh_canh", canh=5))
    assert so.anh_la_ban_lui(5) is False


def test_h3_lam_lai_khau_clip_gui_len_veo_khong_ra_anh_dong_mai(tmp_path, monkeypatch):
    """Lượt 1: cảnh 7 bị chặn hết cỡ → ảnh động (khâu clip ghi `lui`). Lượt
    "Làm lại khâu clip" (cùng sổ): phải GỬI LÊN VEO lại, không đọc dấu lùi
    của chính khâu clip như "ảnh cảnh là bản lùi"."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"khong-phai-anh-that")
    dich = str(tmp_path / "7.mp4")
    bc, _ = _bc()
    luot = _luot(tmp_path)
    cong_cu = _CongCuGia(ve_anh=RuntimeError("ve hong"), viet_lai=RuntimeError("vl hong"))
    anh_dong = _gia_clip(monkeypatch, cong_cu)
    goi = {"n": 0, "chan": True}

    def create(**kw):
        goi["n"] += 1
        if goi["chan"]:
            raise _LoiMa("vi phạm quy định", "content_rejected")
        return {"id": "job_ok", "status": "succeeded"}

    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    ak._lam_clip(bc, luot, {"scene_id": 7, "img_prompt": "a man", "video_prompt": "p"},
                 str(anh), dich, 8)
    assert anh_dong, "lượt 1 phải lùi về ảnh động"
    so_lan_luot_1 = goi["n"]

    # Người dùng sửa lời nhắc video rồi "Làm lại khâu clip"; Veo giờ nhận.
    goi["chan"] = False
    os.remove(dich)
    anh_dong.clear()
    ak._lam_clip(bc, luot, {"scene_id": 7, "img_prompt": "a man", "video_prompt": "p2"},
                 str(anh), dich, 8)
    assert goi["n"] == so_lan_luot_1 + 1, "lượt làm lại phải gửi lên Veo"
    assert not anh_dong, "lượt làm lại không được ra ảnh động mãi"
    assert "clip:7" not in ak._so_cuu_cua_luot(bc, luot)._so["canh"]


# ═══ H4: luật #7 chỉ đếm job ĐÃ CHẠY; sống phải là SAU lần hỏng đầu ═══════════


def test_h4_loi_luc_tao_job_khong_bao_gio_thanh_noi_dung():
    dh = DongHo()
    so = tcnd.SoCuu(dong_ho=dh)
    dv = tcnd.DauVao(khau="clip", canh=5, prompt="p")
    loi_503 = ak._loi_gui_thanh_ket(_LoiMa("Nhà máy chưa sẵn sàng", "engine_unavailable"))
    assert isinstance(loi_503, ak.LoiKetJob) and loi_503.luc_tao_job is True
    for _ in range(6):
        dh.qua(60)
        so.bao_xong("video")  # khâu vẫn có clip khác xong
        assert so.bao_hong(dv, loi_503) is None
    assert so.cho_gui(dv) is True


def test_h4_qua_han_cua_anh_khong_tinh_luat_7():
    dh = DongHo()
    so = tcnd.SoCuu(dong_ho=dh)
    dv = tcnd.DauVao(khau="anh_canh", canh=2, prompt="p")
    for _ in range(5):
        dh.qua(60)
        for _ in range(3):
            so.bao_xong("anh")
        assert so.bao_hong(dv, ak.LoiQuaHan("đợi 8 phút mà máy chủ vẫn chưa trả kết quả",
                                            "job_abc")) is None
    assert so.cho_gui(dv) is True


def test_h4_song_phai_la_job_xong_sau_lan_hong_dau():
    dh = DongHo()
    so = tcnd.SoCuu(dong_ho=dh)
    dv = tcnd.DauVao(khau="clip", canh=5, prompt="p")
    loi = ak.LoiKetJob("máy chủ báo job hỏng (đã hoàn tiền): x", "engine_unavailable")
    so.bao_xong("video")          # clip khác xong TRƯỚC khi cảnh này hỏng
    dh.qua(60)
    assert so.bao_hong(dv, loi) is None
    dh.qua(60)
    assert so.bao_hong(dv, loi) is None, "xong TRƯỚC lần hỏng đầu không chứng minh khâu còn sống"
    dh.qua(60)
    so.bao_xong("video")          # giờ mới có clip khác xong SAU mốc
    dh.qua(60)
    kl = so.bao_hong(dv, loi)
    assert kl is not None and kl.nghi_do == "chua_ro"


def test_h4_qua_han_cua_clip_van_dem_va_khong_ghi_ma_job_lam_ma_loi():
    dh = DongHo()
    so = tcnd.SoCuu(dong_ho=dh)
    dv = tcnd.DauVao(khau="clip", canh=5, prompt="p")
    loi = ak.LoiQuaHan("đợi 6 phút mà máy chủ vẫn chưa trả kết quả", "job_abc123")
    assert so.bao_hong(dv, loi) is None
    dh.qua(60)
    so.bao_xong("video")
    kl = so.bao_hong(dv, loi)
    assert kl is not None
    assert "job_abc123" not in kl.ma, "mã JOB không phải mã lỗi"
    assert so._so["dau_vao"][dv.van_tay()]["ma"] != "job_abc123"


def test_h4_ket_luan_am_tham_khong_chan_vinh_vien_luot_sau(tmp_path):
    duong = str(tmp_path / "tu-choi.json")
    dh = DongHo()
    so = tcnd.SoCuu(duong_tep=duong, dong_ho=dh)
    dv = tcnd.DauVao(khau="clip", canh=5, prompt="p")
    so.ghi_ket_luan(dv, tcnd.KetLuanTuChoi("clip", "chua_ro", "engine_unavailable",
                                           tcnd.AM_THAM_CUC_BO, 2, "treo"))
    assert so.cho_gui(dv) is False, "trong phiên, còn hạn: chặn gửi lại y nguyên"
    # Phiên sau (mở lại tool / lượt sau đọc cùng sổ): không chặn nữa.
    so2 = tcnd.SoCuu(duong_tep=duong, dong_ho=dh)
    assert so2.cho_gui(dv) is True
    # Cùng phiên nhưng quá hạn: cũng không chặn nữa.
    dh.qua(61 * 60)
    assert so.cho_gui(dv) is True
    # Kết luận RÕ thì vẫn vĩnh viễn (bất biến #2).
    dv_ro = tcnd.DauVao(khau="clip", canh=6, prompt="p")
    so.ghi_ket_luan(dv_ro, tcnd.KetLuanTuChoi("clip", "prompt", "content_rejected", tcnd.RO))
    assert tcnd.SoCuu(duong_tep=duong, dong_ho=dh).cho_gui(dv_ro) is False


def test_h4_tao_anh_503_luc_tao_lap_lai_khong_thanh_loi_tu_choi(monkeypatch):
    """503 `engine_unavailable` lúc TẠO job ảnh, lặp lại — vòng không trần cũ
    tiếp tục tới khi máy chủ nhận, KHÔNG rẽ vào chuỗi cứu tốn tiền."""
    so_lan = {"n": 0}
    so_cuu = tcnd.SoCuu()

    def create(**kw):
        so_lan["n"] += 1
        so_cuu.bao_xong("anh")
        if so_lan["n"] <= 4:
            raise _LoiMa("Nhà máy ảnh đang nghỉ, thử lại sau", "engine_unavailable")
        return {"id": "j"}

    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))
    monkeypatch.setattr(ak, "_loi_gui_thanh_ket",
                        lambda loi: ak.LoiKetJob("máy chủ chưa nhận việc: x",
                                                 "engine_unavailable", luc_tao_job=True))
    monkeypatch.setattr(ak, "_cho_anh", lambda bc, job, ten_hien="", so=None: job)
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)
    bc = SimpleNamespace(kiem_dung=lambda: None, ghi=lambda s: None,
                         client=SimpleNamespace(images=SimpleNamespace(create=create)))
    dv = tcnd.DauVao(khau="anh_canh", canh=9, prompt="a cat")
    ra = ak._tao_anh(bc, SimpleNamespace(), "a cat", _HopRong(), "k9", so_cuu=so_cuu, dv=dv)
    assert ra == {"id": "j"}
    assert so_cuu.cho_gui(dv) is True


# ═══ H5: bấm Dừng / hết tiền đi XUYÊN chuỗi cứu và công cụ ═══════════════════


@pytest.mark.parametrize("loi", [Cancelled("bấm Dừng"),
                                 _LoiMa("Ví của bạn không đủ số dư", "insufficient_balance")])
def test_h5_buoc_cuu_nem_huy_hoac_het_tien_thi_khong_chay_buoc_lui(chuoi_sach, loi):
    lui_da_chay = []

    def ap_hong(so_cuu, dv, kl, cc):
        raise loi

    def ap_lui(so_cuu, dv, kl, cc):
        lui_da_chay.append(1)
        return tcnd.KetQuaLui("lui", dv, "lùi", {})

    tcnd.dang_ky_chuoi("anh_canh", [
        tcnd.BuocCuu("sua", frozenset(tcnd.NGHI_DO), {}, False, ap_hong),
        tcnd.BuocCuu("lui", frozenset(tcnd.NGHI_DO), {}, True, ap_lui)])
    so = tcnd.SoCuu(tong_so_canh=20)
    dv = tcnd.DauVao(khau="anh_canh", canh=4, prompt="p")

    def gui(d, h):
        raise _LoiMa("vi phạm quy định", "content_rejected")

    with pytest.raises(type(loi)):
        tcnd.lam_co_cuu(so, dv, gui=gui, xong=lambda g, d: None)
    assert not lui_da_chay, "bước lùi không được chạy sau khi bấm Dừng / hết tiền"
    assert so.anh_la_ban_lui(4) is False


def test_h5_anh_boi_canh_khong_nuot_cancelled(tmp_path, monkeypatch):
    bc, _ = _bc()
    luot = _luot(tmp_path)

    def tao_anh_huy(*a, **k):
        raise Cancelled("bấm Dừng")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_huy)
    cc = ak._cong_cu_auto(bc, luot, {"scene_id": 3, "img_prompt": "a cat"}, None)
    with pytest.raises(Cancelled):
        cc.anh_boi_canh(tcnd.DauVao(khau="anh_canh", canh=3, prompt="a cat"))
    assert ak._so_cuu_cua_luot(bc, luot)._so["chi_phi"]["anh"] == 0, "huỷ thì hoàn chỗ ngân sách"


def test_h5_tien_nghiem_clip_khong_nuot_cancelled(tmp_path):
    so = tcnd.SoCuu(tong_so_canh=20)
    so.ghi_nguy_co_nhan_vat(["nv7"], "mat_that", xac_nhan=["tham_chieu", "clip:1"])
    so.danh_dau_thu_nho_that_bai(["nv7"])
    cc = _CongCuGia(ve_anh=Cancelled("bấm Dừng"))
    bc, _ = _bc()
    dv = tcnd.DauVao(khau="clip", canh=7, prompt="p", anh=str(tmp_path / "7.png"),
                     nhan_vat=("nv7",))
    with pytest.raises(Cancelled):
        ak._tien_nghiem_nhan_vat_nguy_co_clip(bc, so, cc, dv, 7)


# ═══ MEDIUM ══════════════════════════════════════════════════════════════════


def test_medium_tran_30_phut_tinh_tu_luc_co_ket_luan(chuoi_sach):
    """Lần gửi đầu mất 40' (chờ clip bình thường) rồi mới bị từ chối — bước
    sửa trả tiền vẫn phải được chạy (trần tính từ KẾT LUẬN, không từ lần gửi)."""
    dh = DongHo()
    sua = []

    def ap_sua(so_cuu, dv, kl, cc):
        sua.append(1)
        return tcnd.DauVao(khau=dv.khau, canh=dv.canh, prompt=dv.prompt + " (sửa)")

    tcnd.dang_ky_chuoi("clip", [tcnd.BuocCuu("sua", frozenset(tcnd.NGHI_DO), {"chat": 1},
                                             False, ap_sua)])
    so = tcnd.SoCuu(tong_so_canh=20, dong_ho=dh)
    dv = tcnd.DauVao(khau="clip", canh=1, prompt="p")

    def gui(d, h):
        if "(sửa)" in d.prompt:
            return {"id": "ok"}
        dh.qua(40 * 60)
        raise _LoiMa("vi phạm quy định", "content_rejected")

    ket = tcnd.lam_co_cuu(so, dv, gui=gui, xong=lambda g, d: None)
    assert sua == [1] and ket.buoc == ["sua"]


def test_medium_tran_thoi_gian_khong_song_qua_luot_cuu_truoc(chuoi_sach):
    dh = DongHo()
    sua = []

    def ap_sua(so_cuu, dv, kl, cc):
        sua.append(1)
        raise RuntimeError("không sửa được")

    def ap_lui(so_cuu, dv, kl, cc):
        return tcnd.KetQuaLui("lui", dv, "lùi", {})

    tcnd.dang_ky_chuoi("clip", [
        tcnd.BuocCuu("sua", frozenset(tcnd.NGHI_DO), {"chat": 1}, False, ap_sua),
        tcnd.BuocCuu("lui", frozenset(tcnd.NGHI_DO), {}, True, ap_lui)])
    so = tcnd.SoCuu(tong_so_canh=20, dong_ho=dh)

    def gui(d, h):
        raise _LoiMa("vi phạm quy định", "content_rejected")

    tcnd.lam_co_cuu(so, tcnd.DauVao(khau="clip", canh=1, prompt="p"), gui=gui,
                    xong=lambda g, d: None)
    dh.qua(2 * 3600)  # "Làm lại khâu" hai giờ sau, người dùng đã sửa lời nhắc
    tcnd.lam_co_cuu(so, tcnd.DauVao(khau="clip", canh=1, prompt="p mới"), gui=gui,
                    xong=lambda g, d: None)
    assert sua == [1, 1], "lượt cứu mới phải được chạy lại bước sửa, không kế thừa trần cũ"


def test_medium_anh_boi_canh_qua_co_tat_va_tran(tmp_path, monkeypatch):
    bc, _ = _bc()
    luot = _luot(tmp_path)
    goi = []
    monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: goi.append(1) or {"id": "j"})
    monkeypatch.setattr(ak, "_tai_ket_qua", lambda bc, g, i, d: open(d, "wb").write(b"x"))
    monkeypatch.setattr(ak, "_xoa_dau", lambda bc, d: None)
    os.makedirs(os.path.join(luot.thu_muc, "5-anh"), exist_ok=True)
    so = ak._so_cuu_cua_luot(bc, luot)
    cc = ak._cong_cu_auto(bc, luot, {"scene_id": 3, "img_prompt": "a cat"}, None)
    dv = tcnd.DauVao(khau="anh_canh", canh=3, prompt="a cat")

    # RÀ SOÁT 28/09/2026 (LOW): `anh_boi_canh` giờ trả `(đường_dẫn,
    # đã_vẽ_mới)` — cờ thứ hai cho dòng [LÙI] biết có tốn tiền hay không.
    so.cau_hinh.tat = True
    assert cc.anh_boi_canh(dv) == (None, False) and goi == [], "kênh tắt bước trả tiền thì không vẽ"
    so.cau_hinh.tat = False
    so.cau_hinh.tran_anh = 0
    assert cc.anh_boi_canh(dv) == (None, False) and goi == [], "hết trần ảnh thì không vẽ"
    so.cau_hinh.tran_anh = None
    duong, ve_moi = cc.anh_boi_canh(dv)
    assert duong and ve_moi is True and goi == [1]
    assert so._so["chi_phi"]["anh"] == 1


def test_medium_anh_boi_canh_khong_dinh_tham_chieu_nhan_vat(tmp_path, monkeypatch):
    bc, _ = _bc()
    luot = _luot(tmp_path)
    hop_da_gui = []

    class _HopNhanVat:
        def lay(self):
            return ["http://anh/nv1.png"]

        def lam_moi(self, cu):
            return self.lay()

    monkeypatch.setattr(ak, "_hop_cho_canh", lambda bc, luot, c, hop: _HopNhanVat())
    monkeypatch.setattr(ak, "_tao_anh", lambda bc, luot, p, hop, k, **kw:
                        hop_da_gui.append(hop.lay()) or {"id": "j"})
    monkeypatch.setattr(ak, "_tai_ket_qua", lambda bc, g, i, d: open(d, "wb").write(b"x"))
    monkeypatch.setattr(ak, "_xoa_dau", lambda bc, d: None)
    os.makedirs(os.path.join(luot.thu_muc, "5-anh"), exist_ok=True)
    cc = ak._cong_cu_auto(bc, luot, {"scene_id": 3, "img_prompt": "a cat"}, None)
    duong, ve_moi = cc.anh_boi_canh(tcnd.DauVao(khau="anh_canh", canh=3, prompt="a cat"))
    assert duong and ve_moi is True
    assert hop_da_gui == [[]], "ảnh bối cảnh KHÔNG người không được kèm chân dung nhân vật"


def test_medium_tien_nghiem_khung_rong_clip_qua_co_tat(tmp_path):
    so = tcnd.SoCuu(tong_so_canh=20, cau_hinh=tcnd.CauHinhTran(tat=True))
    so.ghi_nguy_co_nhan_vat(["nv7"], "mat_that", xac_nhan=["tham_chieu", "clip:1"])
    so.danh_dau_thu_nho_that_bai(["nv7"])
    cc = _CongCuGia(ve_anh=str(tmp_path / "rong.png"))
    bc, _ = _bc()
    dv = tcnd.DauVao(khau="clip", canh=7, prompt="p", anh="7.png", nhan_vat=("nv7",))
    assert ak._tien_nghiem_nhan_vat_nguy_co_clip(bc, so, cc, dv, 7) is dv
    assert cc.ve_anh_goi == [], "kênh tắt bước trả tiền: tiền nghiệm không được vẽ ảnh"


def test_medium_mot_xac_nhan_chua_bat_tien_nghiem(tmp_path, monkeypatch):
    c = {"scene_id": 12, "img_prompt": "close-up portrait of nv9. Style: 3D",
         "characters_used": "nv9"}
    bc, _ = _bc()
    luot = _luot(tmp_path)
    so = ak._so_cuu_cua_luot(bc, luot)
    so.ghi_nguy_co_nhan_vat(["nv9"], "mat_that", [3, 4, 5], xac_nhan=["tham_chieu"])
    prompt_goi = []
    monkeypatch.setattr(ak, "_tao_anh", lambda bc, luot, p, hop, k, **kw:
                        prompt_goi.append(p) or {"id": "j"})
    monkeypatch.setattr(ak, "_tai_ket_qua", lambda bc, g, i, d: open(d, "wb").write(b"x"))
    monkeypatch.setattr(ak, "_xoa_dau", lambda bc, d: None)
    ak._lam_anh_canh(bc, luot, c, str(tmp_path / "12.png"), _HopRong())
    assert "Wide shot" not in prompt_goi[0], "MỘT lần xác nhận chưa đủ bật tiền nghiệm"


def test_medium_tham_chieu_hong_ha_tang_khong_ghi_nguy_co(tmp_path):
    so = tcnd.SoCuu()
    dd._ghi_nguy_co_nhan_vat(so, [("nv1", "mạng đứt giữa chừng")], [])
    assert so.nguy_co_nhan_vat(["nv1"]) is None
    assert "nv1" not in so._so["nhan_vat"]
    dd._ghi_nguy_co_nhan_vat(so, [("nv2", "content_rejected: bộ lọc")], [])
    assert so.so_xac_nhan_nguy_co("nv2") == 1
    assert so.nguy_co_nhan_vat(["nv2"]) is None


def test_medium_clip_doc_characters_used_va_ghi_xac_nhan(tmp_path, monkeypatch):
    from PIL import Image

    bc, _ = _bc()
    luot = _luot(tmp_path)
    anh = tmp_path / "7.png"
    Image.new("RGB", (160, 90), (200, 120, 80)).save(str(anh))
    dich = str(tmp_path / "7.mp4")
    _gia_clip(monkeypatch)
    so = ak._so_cuu_cua_luot(bc, luot)
    so.ghi_nguy_co_nhan_vat(["nv7"], "mat_that", xac_nhan=["tham_chieu", "clip:2"])
    goi_anh = []

    def create(**kw):
        goi_anh.append(kw["image_url"])
        return {"id": "j", "status": "succeeded"}

    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    ak._lam_clip(bc, luot, {"scene_id": 7, "img_prompt": "a man", "video_prompt": "p",
                            "characters_used": "nv7, nv8"}, str(anh), dich, 8)
    assert goi_anh == ["http://anh/7.png.thu-nho.png"], \
        "khâu clip phải đọc `characters_used` như bảng cảnh ghi"


def test_medium_clip_bi_chan_vi_anh_ghi_mot_xac_nhan(tmp_path, monkeypatch):
    bc, _ = _bc()
    luot = _luot(tmp_path)
    anh = tmp_path / "7.png"
    anh.write_bytes(b"khong-phai-anh-that")
    anh_rong = tmp_path / "7-rong.png"
    anh_rong.write_bytes(b"rong")
    _gia_clip(monkeypatch, _CongCuGia(ve_anh=str(anh_rong)))
    lan = {"n": 0}

    def create(**kw):
        lan["n"] += 1
        if lan["n"] == 1:
            raise _LoiMa("ảnh có người thật", "prompt_image_rejected_by_provider")
        return {"id": "j", "status": "succeeded"}

    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    ak._lam_clip(bc, luot, {"scene_id": 7, "img_prompt": "a man", "video_prompt": "p",
                            "characters_used": "nv7"}, str(anh), str(tmp_path / "7.mp4"), 8)
    so = ak._so_cuu_cua_luot(bc, luot)
    assert so.so_xac_nhan_nguy_co("nv7") == 1
    assert so.nguy_co_nhan_vat(["nv7"]) is None


# ═══ LOW ═════════════════════════════════════════════════════════════════════


def test_low_doc_so_sai_kieu_coi_rong(tmp_path):
    duong = tmp_path / "tu-choi.json"
    duong.write_text(json.dumps({"canh": [], "chi_phi": "3", "dau_vao": {"x": 5},
                                 "nhan_vat": {"nv1": {"nguy_co": "mat_that"}}}),
                     encoding="utf-8")
    so = tcnd.SoCuu(duong_tep=str(duong))
    assert so._so["canh"] == {}
    assert so._so["chi_phi"] == {"anh": 0, "clip": 0, "chat": 0}
    assert so._so["dau_vao"] == {}
    so.ghi_ket_qua_canh(tcnd.DauVao(khau="anh_canh", canh=1), ["x"], lui=False)
    assert "Cứu nội dung: 1 cảnh" in so.tong_ket()


def test_low_ghi_so_hong_luc_dump_khong_de_tep_tam(tmp_path):
    duong = str(tmp_path / "tu-choi.json")
    dong = []
    so = tcnd.SoCuu(duong_tep=duong, on_log=dong.append)
    so.ghi_nguy_co_nhan_vat(["nv1"], "mat_that", [object()])  # không tuần tự hoá được
    assert any("[sổ]" in d for d in dong)
    assert [t for t in os.listdir(str(tmp_path)) if t != "tu-choi.json"] == [], \
        "dump hỏng không được để lại tệp tạm"


def test_low_bang_so_chung_khoa_theo_duong_chuan_hoa(tmp_path):
    bc, _ = _bc()
    d = str(tmp_path / "Luot")
    os.makedirs(d)
    a = ak._so_cuu_cua_luot(bc, SimpleNamespace(thu_muc=d))
    b = ak._so_cuu_cua_luot(bc, SimpleNamespace(thu_muc=d + os.sep + "." + os.sep))
    assert a is b
    if os.name == "nt":
        assert ak._so_cuu_cua_luot(bc, SimpleNamespace(thu_muc=d.upper())) is a


def test_low_van_tay_tham_chieu_anh_canh_theo_byte_tep_cuc_bo(tmp_path, monkeypatch):
    nv = tmp_path / "nv1.png"
    nv.write_bytes(b"chan-dung")
    luot_url = {"n": 0}

    class _HopCucBo:
        _duong = [str(nv)]

        def lay(self):
            luot_url["n"] += 1
            return ["https://kho/nv1.png?sig={0}".format(luot_url["n"])]  # chữ ký đổi mỗi lần

        def lam_moi(self, cu):
            return self.lay()

    bc, _ = _bc()
    luot = _luot(tmp_path)
    dv_da_gui = []
    monkeypatch.setattr(ak, "_tao_anh", lambda bc, luot, p, hop, k, **kw:
                        dv_da_gui.append(kw.get("dv")) or {"id": "j"})
    monkeypatch.setattr(ak, "_tai_ket_qua", lambda bc, g, i, d: open(d, "wb").write(b"x"))
    monkeypatch.setattr(ak, "_xoa_dau", lambda bc, d: None)
    ak._lam_anh_canh(bc, luot, {"scene_id": 1, "img_prompt": "a cat"}, str(tmp_path / "1.png"),
                     _HopCucBo())
    assert dv_da_gui[0].tham_chieu == (str(nv),)


def test_low_giu_ngan_sach_song_song_khong_vuot_tran():
    so = tcnd.SoCuu(cau_hinh=tcnd.CauHinhTran(tran_anh=5))
    ket = []
    rao = threading.Barrier(20)

    def mot():
        rao.wait()
        ket.append(so.giu_ngan_sach({"anh": 1}))

    luong = [threading.Thread(target=mot) for _ in range(20)]
    for t in luong:
        t.start()
    for t in luong:
        t.join()
    assert ket.count(True) == 5
    assert so._so["chi_phi"]["anh"] == 5


def test_low_dong_bao_nhan_tieng_viet_co_chi_phi(chuoi_sach):
    def ap(so_cuu, dv, kl, cc):
        return tcnd.DauVao(khau=dv.khau, canh=dv.canh, prompt=dv.prompt + " x")

    tcnd.dang_ky_chuoi("khung_cuoi", [tcnd.BuocCuu("viet_lai_prompt_anh", frozenset(tcnd.NGHI_DO),
                                                   {"chat": 1}, False, ap)])
    dong = []
    so = tcnd.SoCuu(tong_so_canh=20, on_log=dong.append)
    lan = {"n": 0}

    def gui(d, h):
        lan["n"] += 1
        if lan["n"] == 1:
            raise _LoiMa("vi phạm quy định", "content_rejected")
        return {"id": "ok"}

    tcnd.lam_co_cuu(so, tcnd.DauVao(khau="khung_cuoi", canh=5, prompt="p"), gui=gui,
                    xong=lambda g, d: None)
    dong_cuu = [d for d in dong if "[CỨU]" in d]
    assert dong_cuu, dong
    assert "khung cuối cảnh 5" in dong_cuu[0]
    assert "viết lại lời nhắc" in dong_cuu[0]
    assert "+1 lượt viết lại" in dong_cuu[0] and "+1 ảnh" in dong_cuu[0]
    for xau in ("viet_lai_prompt_anh", "khung_cuoi", "kc5", "None"):
        assert xau not in dong_cuu[0]
    assert tcnd.mo_ta_cho(tcnd.DauVao(khau="nguoi_ke")) == "ảnh người kể"
    assert tcnd.mo_ta_cho(tcnd.DauVao(khau="khung_cuoi", canh="kc5")) == "khung cuối cảnh 5"
