"""Rà soát VÒNG 2 trước phát hành 2.138.0 — bộ xử lý "nội dung bị từ chối".

Mỗi bài dưới đây canh ĐÚNG một lỗi rà soát vòng 2 đã tìm ra (HIGH-1, HIGH-2,
MED-1, MED-2). Không gọi mạng. Xem thiết kế:
`docs/noi-bo/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md`.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

import core.auto_khau as ak
from core.auto import Cancelled, LuotChay, TrangThaiKhau
import core.tu_choi_noi_dung as t

_KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def _don_so_cuu():
    t._SO_CUU_THEO_LUOT.clear()
    yield
    t._SO_CUU_THEO_LUOT.clear()


# ── HIGH-1: node video ghép ảnh↔prompt theo scene_id, không theo VỊ TRÍ ─────
#
# Node ảnh có thể BỎ một cảnh bị từ chối nội dung (GÓI G8) rồi trả về ÍT ảnh
# hơn scene manifest. Ghép theo vị trí (zip) khi đó làm lệch: ảnh cảnh 4 bị
# gán nhầm prompt của cảnh 3. Xem `tool-catalog/video.shopapi/run.py`.


def _tai_video_run():
    spec = importlib.util.spec_from_file_location(
        "vrun_test", os.path.join(_KHO, "tool-catalog", "video.shopapi", "run.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _ClientVideoGia:
    def __init__(self):
        self.videos = self
        self.jobs = self
        self.uploads = self
        self.goi = []

    def request(self, *a, **k):
        return {"limits": {"concurrent_jobs": {"video": 4}}}

    def upload_file(self, p):
        return "https://x/" + Path(p).name

    def create(self, **kw):
        self.goi.append((kw["image_url"], kw["prompt"], kw["idempotency_key"]))
        return {"id": "j{0}".format(len(self.goi)), "status": "queued"}

    def wait(self, i):
        return {"id": i, "output": {"url": "https://x/{0}.mp4".format(i)}}

    def close(self):
        pass


def test_HIGH1_video_ghep_theo_scene_id_khong_theo_vi_tri(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOPAPI_API_KEY", "sk_test_fake")
    v = _tai_video_run()
    ws = tmp_path / "ws"
    ws.mkdir()
    # Node ảnh đã BỎ cảnh 3 (bị từ chối nội dung) -> chỉ trả ảnh 1, 2, 4.
    imgs = []
    for sid in (1, 2, 4):
        p = ws / "scene-{0:04d}.png".format(sid)
        p.write_bytes(b"png%d" % sid)
        imgs.append({"path": str(p), "metadata": {"scene_id": sid}})
    scenes = {"scenes": [{"scene_id": i, "video_prompt": "PROMPT CANH {0}".format(i)}
                         for i in (1, 2, 3, 4)]}
    client = _ClientVideoGia()
    out = v.handle(
        {"inputs": {"images": imgs, "scenes": scenes}, "workspace": str(ws),
         "run_id": "r", "node_id": "video"},
        client_factory=lambda **kw: client,
        downloader=lambda u, tgt: tgt.write_bytes(b"mp4"))

    goi_theo_url = {u: p for u, p, _k in client.goi}
    assert goi_theo_url["https://x/scene-0004.png"] == "PROMPT CANH 4", (
        "ảnh cảnh 4 phải đi kèm ĐÚNG prompt cảnh 4, không phải prompt cảnh 3")
    clip_ids = sorted(c["metadata"]["scene_id"] for c in out["clips"])
    assert clip_ids == [1, 2, 4]
    assert 3 not in clip_ids


def test_HIGH1_video_fallback_zip_khi_thieu_metadata(tmp_path, monkeypatch):
    """Đối chứng: KHÔNG có metadata scene_id hợp lệ thì vẫn zip theo thứ tự
    (đường lùi cũ) — không được vỡ ca ảnh không có metadata."""
    monkeypatch.setenv("SHOPAPI_API_KEY", "sk_test_fake")
    v = _tai_video_run()
    ws = tmp_path / "ws"
    ws.mkdir()
    imgs = []
    for i in (1, 2, 3):
        p = ws / "img{0}.png".format(i)
        p.write_bytes(b"png%d" % i)
        imgs.append({"path": str(p), "metadata": {}})
    scenes = {"scenes": [{"scene_id": i, "video_prompt": "PROMPT CANH {0}".format(i)}
                         for i in (1, 2, 3)]}
    client = _ClientVideoGia()
    out = v.handle(
        {"inputs": {"images": imgs, "scenes": scenes}, "workspace": str(ws),
         "run_id": "r", "node_id": "video"},
        client_factory=lambda **kw: client,
        downloader=lambda u, tgt: tgt.write_bytes(b"mp4"))
    assert len(out["clips"]) == 3


# ── HIGH-2: đoạn giọng bị chặn — "Chạy tiếp" phải thử viết lại LẦN NỮA ──────


def _chuan_bi_tts(tmp_path, monkeypatch, goi_chat):
    import test_g6_giong_du_phong as g6

    monkeypatch.setattr(ak, "_tai_ket_qua_mot_lan",
                        lambda bc, goi, cs, dich: open(dich, "wb").write(b"ID3") and dich)
    monkeypatch.setattr(ak, "_tim_ffmpeg", lambda: "")
    monkeypatch.setattr(ak, "_noi_mp3", lambda bc, manh, dich, nghi=None: open(dich, "wb").write(b"ID3"))
    monkeypatch.setattr(ak, "_doi_cao_do_giong", lambda bc, mp3: False)
    monkeypatch.setattr(ak, "_lam_sach_ket_qua", lambda bc, *tep: None)
    doan_cam = "Câu văn bị bộ lọc nội dung từ chối vì mô tả bạo lực."
    kb = doan_cam + "\n---\nMột buổi sáng yên bình ở ngôi làng nhỏ."
    client = g6._tts_chan_mot_cau(doan_cam, "")
    kenh = g6._kenh(voice_id="giong-goc")
    dong = []
    bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=goi_chat, client=client,
                    on_log=dong.append, ngu=lambda s: None, ffmpeg="")
    luot = g6._luot(tmp_path, kb)
    return bc, luot, client, dong


def test_HIGH2_viet_lai_hong_thoang_qua_thi_chay_tiep_thu_lai(tmp_path, monkeypatch):
    """AI viết lại hỏng THOÁNG QUA (mạng chập chờn) ở lần chạy đầu -> sổ đã
    ghi kết luận 'bị chặn nội dung', nhưng "Chạy tiếp" phải THỬ VIẾT LẠI lần
    nữa, không được ném thẳng `LoiTuChoi` mãi mãi."""
    trang = {"loi": True, "n": 0}

    def goi_chat(loi_nhac, **kw):
        trang["n"] += 1
        if trang["loi"]:
            raise RuntimeError("mạng chập chờn")
        return "Một buổi sáng căng thẳng nhưng không đổ máu, kể nhẹ nhàng."

    bc, luot, client, dong = _chuan_bi_tts(tmp_path, monkeypatch, goi_chat)
    lam = ak._khau_giong_doc(bc)
    with pytest.raises(Exception):
        lam(luot, TrangThaiKhau(ma="giong_doc"))

    trang["loi"] = False
    ket = lam(luot, TrangThaiKhau(ma="giong_doc"))
    assert ket["so_doan"] == 2
    assert trang["n"] >= 2, "phải gọi AI viết lại thêm ít nhất một lần ở 'Chạy tiếp'"


def test_HIGH2_dung_giua_luc_viet_lai_roi_chay_tiep_thanh_cong(tmp_path, monkeypatch):
    trang = {"huy": True, "n": 0}

    def goi_chat(loi_nhac, **kw):
        trang["n"] += 1
        if trang["huy"]:
            raise Cancelled("bấm Dừng")
        return "Một buổi sáng căng thẳng nhưng không đổ máu, kể nhẹ nhàng."

    bc, luot, client, dong = _chuan_bi_tts(tmp_path, monkeypatch, goi_chat)
    lam = ak._khau_giong_doc(bc)
    with pytest.raises(Cancelled):
        lam(luot, TrangThaiKhau(ma="giong_doc"))

    trang["huy"] = False
    t._SO_CUU_THEO_LUOT.clear()
    lam2 = ak._khau_giong_doc(bc)
    ket = lam2(luot, TrangThaiKhau(ma="giong_doc"))
    assert ket["so_doan"] == 2


def test_HIGH2_runtime_error_da_dung_khong_bi_nuot(tmp_path):
    """`kiem_dung()` của Tự động (`ui_qt/trang_auto.py`) ném thẳng
    `RuntimeError("đã dừng")`, KHÔNG PHẢI `Cancelled` — `_viet_lai_doan_doc`
    phải để nó đi xuyên qua (không nuốt thành chuỗi rỗng)."""
    from core.kenh import Kenh

    kenh = Kenh(ma="k1", ten="t", ngon_ngu="vi", voice_id="v", giong_du_phong="",
               gioi_nguoi_ke="", mo_hinh="claude-sonnet-5", giay_nghi_phan=0.0)
    luot = LuotChay(ma_kenh="k1", ma_luot="0001", thu_muc=str(tmp_path))

    def goi_chat(*a, **k):
        raise RuntimeError("đã dừng")

    bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=goi_chat, client=None,
                    on_log=[].append, ngu=lambda s: None, ffmpeg="")

    with pytest.raises(RuntimeError, match="đã dừng"):
        ak._viet_lai_doan_doc(bc, luot, 1, "Đoạn gốc cần viết lại.", "content_rejected")


def test_HIGH2_runtime_error_thuong_van_bi_nuot_tra_rong(tmp_path):
    """Đối chứng: RuntimeError THƯỜNG (không phải "đã dừng") vẫn phải bị nuốt
    thành chuỗi rỗng như cũ — không được coi MỌI RuntimeError là tín hiệu
    Dừng."""
    from core.kenh import Kenh

    kenh = Kenh(ma="k1", ten="t", ngon_ngu="vi", voice_id="v", giong_du_phong="",
               gioi_nguoi_ke="", mo_hinh="claude-sonnet-5", giay_nghi_phan=0.0)
    luot = LuotChay(ma_kenh="k1", ma_luot="0001", thu_muc=str(tmp_path))

    def goi_chat(*a, **k):
        raise RuntimeError("máy chủ AI tạm gián đoạn")

    bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=goi_chat, client=None,
                    on_log=[].append, ngu=lambda s: None, ffmpeg="")

    ra = ak._viet_lai_doan_doc(bc, luot, 1, "Đoạn gốc cần viết lại.", "content_rejected")
    assert ra == ""


def test_HIGH2_la_huy_ngang_qua_nhan_dung_thong_diep():
    assert t._la_huy_ngang_qua(RuntimeError("đã dừng")) is True
    assert t._la_huy_ngang_qua(RuntimeError("đã dừng ")) is True  # khoảng trắng mép
    assert t._la_huy_ngang_qua(RuntimeError("máy chủ AI tạm gián đoạn")) is False


# ── MED-1: sổ SoCuu dùng chung KHÔNG được "sống lại" sau khi xoá lượt ───────


class _Luot:
    def __init__(self, thu_muc):
        self.thu_muc = thu_muc


class _Bc:
    def __init__(self):
        self.dong = []
        self.ghi = self.dong.append


def test_MED1_so_cu_khong_song_lai_khi_thu_muc_xoa_roi_tao_lai(tmp_path):
    d = str(tmp_path / "0005")
    os.makedirs(d)
    so = t.so_cuu_cua_luot(_Bc(), _Luot(d))
    so.ghi_nguy_co_nhan_vat(["nv1"], "mat_that", [3], xac_nhan=["tham_chieu"])
    so.ghi_chi_phi("anh", 9)

    shutil.rmtree(d)
    os.makedirs(d)

    so_moi = t.so_cuu_cua_luot(_Bc(), _Luot(d))
    assert so_moi is not so, "bản đệm SoCuu cũ sống lại sau khi lượt bị xoá"
    assert so_moi.nguy_co_nhan_vat(["nv1"]) is None
    assert so_moi._so["chi_phi"]["anh"] == 0


def test_MED1_bo_so_cuu_luot_chu_dong_tu_cho_xoa(tmp_path):
    d = str(tmp_path / "0006")
    os.makedirs(d)
    so = t.so_cuu_cua_luot(_Bc(), _Luot(d))
    so.ghi_chi_phi("anh", 3)

    t.bo_so_cuu_luot(d)
    assert t._SO_CUU_THEO_LUOT.get(t._chuan_duong(d)) is None

    shutil.rmtree(d)
    os.makedirs(d)
    so_moi = t.so_cuu_cua_luot(_Bc(), _Luot(d))
    assert so_moi is not so
    assert so_moi._so["chi_phi"]["anh"] == 0


def test_MED1_khong_dung_duong_dan_khac_van_khong_dung_chung(tmp_path):
    """Đối chứng: hai lượt CÒN SỐNG, đường dẫn khác nhau, không được lẫn."""
    d1 = str(tmp_path / "0001")
    d2 = str(tmp_path / "0002")
    os.makedirs(d1)
    os.makedirs(d2)
    so1 = t.so_cuu_cua_luot(_Bc(), _Luot(d1))
    so2 = t.so_cuu_cua_luot(_Bc(), _Luot(d2))
    assert so1 is not so2
    # Đọc lại (không xoá) phải ra ĐÚNG bản cũ — không bị bản vá MED-1 làm cho
    # bị tạo mới oan mỗi lần đọc.
    assert t.so_cuu_cua_luot(_Bc(), _Luot(d1)) is so1


# ── MED-2: thay-the.json áp theo SỐ ĐOẠN phải kiểm bam_cu ───────────────────


def test_MED2_thay_the_khong_ap_khi_bam_cu_khong_khop(tmp_path, monkeypatch):
    import test_g6_giong_du_phong as g6

    monkeypatch.setattr(ak, "_tai_ket_qua_mot_lan",
                        lambda bc, goi, cs, dich: open(dich, "wb").write(b"ID3") and dich)
    monkeypatch.setattr(ak, "_tim_ffmpeg", lambda: "")
    monkeypatch.setattr(ak, "_noi_mp3", lambda bc, manh, dich, nghi=None: open(dich, "wb").write(b"ID3"))
    monkeypatch.setattr(ak, "_doi_cao_do_giong", lambda bc, mp3: False)
    monkeypatch.setattr(ak, "_lam_sach_ket_qua", lambda bc, *tep: None)

    # Lượt trước: đoạn 2 (văn bản CŨ) đã viết lại -> thay-the.json; khách SỬA
    # kịch bản tay -> đoạn 2 giờ là văn bản HOÀN TOÀN KHÁC, cùng SỐ đoạn.
    kb_moi = "Đoạn một giữ nguyên.\n---\nĐoạn hai khách vừa sửa tay hoàn toàn khác.\n---\nĐoạn ba."
    luot = g6._luot(tmp_path, kb_moi)
    d2 = os.path.join(luot.thu_muc, "2-doan")
    os.makedirs(d2)
    cu = "Đoạn hai bản cũ đã bị chặn."
    json.dump({"2": {"doan_cu": cu, "doan_moi": "BẢN VIẾT LẠI CỦA ĐOẠN CŨ",
                     "bam_cu": hashlib.sha256(cu.encode()).hexdigest()}},
              open(os.path.join(d2, "thay-the.json"), "w", encoding="utf-8"), ensure_ascii=False)

    client = g6._TtsGia()
    bc = ak.BoiCanh(goc=str(tmp_path), kenh=g6._kenh(), goi_chat=lambda *a, **k: "",
                    client=client, on_log=[].append, ngu=lambda s: None, ffmpeg="")
    ak._khau_giong_doc(bc)(luot, TrangThaiKhau(ma="giong_doc"))

    gui = [g["text"] for g in client.goi]
    assert "BẢN VIẾT LẠI CỦA ĐOẠN CŨ" not in gui, (
        "đoạn 2 bị đọc bằng bản viết lại của văn bản CŨ dù kịch bản đã đổi tay")
    assert "Đoạn hai khách vừa sửa tay hoàn toàn khác." in gui


# ── LOW: `bo_tham_chieu_nghi_van` không được ĐẾM TRÙNG chi phí ảnh ──────────


def test_LOW_bo_tham_chieu_nghi_van_khong_dem_trung_anh():
    so_cuu = t.SoCuu()
    dv = t.DauVao(khau="anh_canh", canh=5, prompt="a cat",
                  tham_chieu=("ref.png",))

    trang = {"n": 0}

    def gui(dv_, hau_to):
        trang["n"] += 1
        if trang["n"] == 1:
            loi = RuntimeError("tệp ảnh tham chiếu không đọc được")
            loi.code = "reference_image_unreadable"
            raise loi
        assert not dv_.tham_chieu, "lần gửi thứ hai phải đã bỏ tham chiếu"
        return {"ok": 1}

    ket = ak.tcnd.lam_co_cuu(so_cuu, dv, gui=gui, xong=lambda g, dv_: None)
    assert ket.buoc == ["bo_tham_chieu_nghi_van"]
    assert so_cuu._so["chi_phi"]["anh"] == 1, (
        "một ảnh THẬT được vẽ (lượt gửi lại thành công) nhưng chi phí bị "
        "đếm gấp đôi — xem đăng ký BuocCuu('bo_tham_chieu_nghi_van', ...)")


# ── LOW: tín hiệu #8 của `nhan_dien` phải dùng `la_cau_tu_choi` (khớp cụm
# NGAY ĐẦU câu, không phải bất kỳ đâu trong câu) ────────────────────────────


def test_LOW_tin_hieu_8_khong_bat_nham_cum_tu_choi_giua_cau():
    """Đúng lỗ hổng H6: một đoạn văn kể chuyện THẬT chứa chữ "tôi không thể"
    ở GIỮA câu (lời thoại nhân vật) không được coi là lời từ chối của LLM."""
    dv = t.DauVao(khau="kich_ban", canh=None, prompt="viết tiếp câu chuyện")
    doan_that = (
        "Cô bé đứng trước cánh cửa, nước mắt lưng tròng, và thì thầm: "
        "'Tôi không thể quay lại nhà được nữa, mẹ đã không còn ở đó.' "
    ) * 8  # đủ dài để không bị sàn 30% bắt nhầm
    ket = t.nhan_dien(doan_that, dv, do_dai_ky_vong=len(doan_that) * 3)
    assert ket is None, "câu chuyện thật có chữ 'tôi không thể' GIỮA câu bị coi nhầm là từ chối"


def test_LOW_tin_hieu_8_van_bat_dung_khi_tu_choi_that_dung_dau_cau():
    dv = t.DauVao(khau="kich_ban", canh=None, prompt="viết một cảnh bạo lực")
    tu_choi_that = "Tôi không thể viết nội dung này vì nó vi phạm chính sách."
    ket = t.nhan_dien(tu_choi_that, dv, do_dai_ky_vong=len(tu_choi_that) * 5)
    assert ket is not None
    assert ket.nghi_do == "prompt"


# ── LOW: sổ SoCuu dùng chung phải cập nhật hàm log theo LẦN GỌI HIỆN TẠI ────


def test_LOW_so_cuu_cap_nhat_on_log_theo_lan_goi(tmp_path):
    d = str(tmp_path / "0001")
    os.makedirs(d)

    bc_a = _Bc()
    so1 = t.so_cuu_cua_luot(bc_a, _Luot(d))
    assert so1.on_log is bc_a.ghi

    bc_b = _Bc()
    so2 = t.so_cuu_cua_luot(bc_b, _Luot(d))

    assert so2 is so1, "vẫn phải là CÙNG một SoCuu (bản đệm dùng chung)"
    assert so2.on_log is bc_b.ghi, (
        "on_log phải cập nhật theo lần gọi HIỆN TẠI, không giữ mãi hàm log "
        "của lần gọi ĐẦU TIÊN tạo ra sổ")

    so1._ghi_log("dòng test")
    assert bc_b.dong == ["dòng test"]
    assert bc_a.dong == [], "log không được rơi vào bc CŨ nữa"


def test_LOW_so_cuu_khong_xoa_on_log_khi_bc_moi_khong_khai(tmp_path):
    d = str(tmp_path / "0001")
    os.makedirs(d)

    bc_a = _Bc()
    so1 = t.so_cuu_cua_luot(bc_a, _Luot(d))

    class _BcTrong:
        pass

    so2 = t.so_cuu_cua_luot(_BcTrong(), _Luot(d))
    assert so2 is so1
    assert so2.on_log is bc_a.ghi, "bc mới không khai ghi/on_log thì giữ nguyên log cũ"


# ── LOW: `_dung_tao_anh_that` (ảnh tham chiếu) phải truyền so_cuu/dv vào
# `_tao_anh`, để luật #7 (lỗi âm thầm lặp lại) không quay vô hạn ──────────


def test_LOW_anh_tham_chieu_truyen_so_cuu_dv_vao_tao_anh(tmp_path, monkeypatch):
    import core.dao_dien_auto as dd

    goi_nhan = []

    def _tao_anh_gia(bc_, luot_, prompt, hop, khoa, ten_hien="", so=None,
                     ty_le="16:9", so_cuu=None, dv=None):
        goi_nhan.append({"so_cuu": so_cuu, "dv": dv})
        return {"id": "j"}

    monkeypatch.setattr("core.auto_khau._tao_anh", _tao_anh_gia)
    monkeypatch.setattr("core.auto_khau._tai_ket_qua",
                        lambda bc_, g, i, d: open(d, "wb").write(b"x"))
    monkeypatch.setattr("core.auto_khau.khoa_viec", lambda *a, **k: "khoa-x")

    bc = SimpleNamespace(kenh=SimpleNamespace(mo_hinh="claude-sonnet-5"),
                         client=object(), ghi=lambda s: None)
    luot = LuotChay(ma_kenh="k1", ma_luot="0001", thu_muc=str(tmp_path))

    lam = dd._dung_tao_anh_that(bc, luot)
    lam("nv1", "a cat sitting", os.path.join(str(tmp_path), "nv1.png"))

    assert len(goi_nhan) == 1
    assert goi_nhan[0]["so_cuu"] is not None, "phải truyền so_cuu (luật #7 cần nó)"
    dv = goi_nhan[0]["dv"]
    assert dv is not None and dv.khau == "tham_chieu" and dv.prompt == "a cat sitting"


# ── LOW: kenh.yaml `cuu_noi_dung: {tat: true}` phải nối tới CauHinhTran.tat ─


def test_LOW_kenh_yaml_cuu_noi_dung_doc_duoc(tmp_path):
    from core.kenh import doc_kenh

    goc = str(tmp_path)
    thu_muc = os.path.join(goc, "CHANNEL", "kx")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write('ma: "kx"\nvoice_id: "a"\ncuu_noi_dung:\n  tat: true\n')
    k = doc_kenh(goc, "kx")
    assert k.cuu_noi_dung_tat is True


def test_LOW_kenh_khong_khai_cuu_noi_dung_mac_dinh_bat_cuu(tmp_path):
    from core.kenh import doc_kenh

    goc = str(tmp_path)
    thu_muc = os.path.join(goc, "CHANNEL", "ky")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write('ma: "ky"\nvoice_id: "a"\n')
    k = doc_kenh(goc, "ky")
    assert k.cuu_noi_dung_tat is False


def test_LOW_so_cuu_cua_luot_ap_dung_tat_tu_kenh(tmp_path):
    from core.kenh import Kenh

    kenh = Kenh(ma="k1", ten="t", ngon_ngu="vi", voice_id="v", giong_du_phong="",
               gioi_nguoi_ke="", mo_hinh="claude-sonnet-5", giay_nghi_phan=0.0,
               cuu_noi_dung_tat=True)
    bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=lambda *a, **k: "",
                    client=object(), on_log=[].append, ngu=lambda s: None, ffmpeg="")
    luot = LuotChay(ma_kenh="k1", ma_luot="0001", thu_muc=str(tmp_path))

    so_cuu = ak._so_cuu_cua_luot(bc, luot)
    assert so_cuu.cau_hinh.tat is True


# ── LOW: sổ kênh "thấy lại ở lượt khác" phải kiểm mã lượt khác THẬT ─────────


def test_LOW_so_kenh_khong_chot_khi_thay_lai_trong_cung_mot_luot(tmp_path):
    duong = os.path.join(str(tmp_path), ak.TEP_SO_KENH_GIONG)
    dong = []
    bc = type("_Bc", (), {"ghi": staticmethod(dong.append)})()

    cau_mo_ho = "Giọng đọc voice_id không tồn tại."
    # "Chạy tiếp" gọi lại ĐÚNG khâu của CÙNG một lượt (ma_luot="0001") hai
    # lần — trước bản vá, lần thứ hai bị hiểu nhầm là "đã thấy ở lượt khác".
    chot_1 = ak._ghi_giong_bi_khoa_neu_du_ro(
        bc, duong, "giong-goc", "giong-du-phong", cau_mo_ho, ma_luot="0001")
    chot_2 = ak._ghi_giong_bi_khoa_neu_du_ro(
        bc, duong, "giong-goc", "giong-du-phong", cau_mo_ho, ma_luot="0001")
    assert chot_1 is False and chot_2 is False, (
        "thấy lại trong CÙNG một lượt (retry) không được coi là 'thấy lại ở "
        "lượt khác' — sổ kênh không được chốt")
    so = json.load(open(duong, encoding="utf-8"))
    assert "giong-goc" not in (so.get("giong_thay_the") or {})

    # Lượt THẬT SỰ khác (ma_luot="0002") mới được chốt.
    chot_3 = ak._ghi_giong_bi_khoa_neu_du_ro(
        bc, duong, "giong-goc", "giong-du-phong", cau_mo_ho, ma_luot="0002")
    assert chot_3 is True
    so2 = json.load(open(duong, encoding="utf-8"))
    assert so2["giong_thay_the"]["giong-goc"]["giong_moi"] == "giong-du-phong"


# ── LOW: ghi thay-the.json/van-ban-bam.json phải khoá theo tệp (không mất
# bản ghi khi nhiều đoạn ghi song song — "lost update") ─────────────────────


def test_LOW_ghi_thay_the_song_song_khong_mat_ban_ghi(tmp_path):
    import threading as _th

    d = str(tmp_path)
    N = 20
    hang_rao = _th.Barrier(N)

    def viet(so):
        hang_rao.wait(timeout=5)
        ak._ghi_thay_the_doan_mot(d, so, "cu {0}".format(so), "moi {0}".format(so))

    luong = [_th.Thread(target=viet, args=(i,)) for i in range(N)]
    for t_ in luong:
        t_.start()
    for t_ in luong:
        t_.join(timeout=10)

    goi = ak._doc_thay_the_doan(d)
    thieu = [i for i in range(N) if str(i) not in goi]
    assert not thieu, "mất bản ghi khi ghi song song (lost update): thiếu {0}".format(thieu)


def test_LOW_ghi_bam_van_ban_song_song_khong_mat_ban_ghi(tmp_path):
    import threading as _th

    d = str(tmp_path)
    N = 20
    hang_rao = _th.Barrier(N)

    def viet(so):
        hang_rao.wait(timeout=5)
        ak._ghi_bam_van_ban_doan(d, so, "văn bản {0}".format(so))

    luong = [_th.Thread(target=viet, args=(i,)) for i in range(N)]
    for t_ in luong:
        t_.start()
    for t_ in luong:
        t_.join(timeout=10)

    goi = ak._doc_bam_van_ban_doan(d)
    thieu = [i for i in range(N) if str(i) not in goi]
    assert not thieu, "mất bản ghi khi ghi song song (lost update): thiếu {0}".format(thieu)


# ── LOW: dòng [LÙI] phải ghi ĐÚNG chi phí khi `anh_boi_canh` vẽ ảnh MỚI ─────


def test_LOW_lui_anh_boi_canh_ve_moi_ghi_dung_chi_phi(tmp_path, monkeypatch):
    from core.kenh import Kenh

    kenh = Kenh(ma="k1", ten="t", ngon_ngu="vi", voice_id="v", giong_du_phong="",
               gioi_nguoi_ke="", mo_hinh="claude-sonnet-5", giay_nghi_phan=0.0)
    dong = []
    bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=lambda *a, **k: "",
                    client=object(), on_log=dong.append, ngu=lambda s: None, ffmpeg="")
    luot = LuotChay(ma_kenh="k1", ma_luot="0001", thu_muc=str(tmp_path))
    os.makedirs(os.path.join(luot.thu_muc, "5-anh"), exist_ok=True)

    monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: {"id": "j"})
    monkeypatch.setattr(ak, "_tai_ket_qua", lambda bc_, g, i, d: open(d, "wb").write(b"x"))
    monkeypatch.setattr(ak, "_xoa_dau", lambda bc_, d: None)

    so_cuu = t.so_cuu_cua_luot(bc, luot)
    dv = t.DauVao(khau="anh_canh", canh=3, prompt="a cat", tham_chieu=())
    cong_cu = ak._cong_cu_auto(bc, luot, {"scene_id": 3, "img_prompt": "a cat"}, None)

    def gui(dv_, hau_to):
        loi = RuntimeError("Nội dung bạn gửi vi phạm quy định sử dụng nên đã bị từ chối.")
        loi.code = "content_rejected"
        raise loi

    def xong(g, dv_):
        pass

    # Ép chuỗi cứu nhảy thẳng tới bước LÙI `anh_boi_canh`: đăng ký một chuỗi
    # tạm chỉ có đúng bước đó cho khâu "anh_canh" (không đụng chuỗi thật).
    truoc = dict(t.CHUOI_CUU)
    t.CHUOI_CUU["anh_canh"] = (
        t.BuocCuu("anh_boi_canh", frozenset(t.NGHI_DO), {}, True, ak._buoc_anh_boi_canh),
    )
    try:
        ket = t.lam_co_cuu(so_cuu, dv, gui=gui, xong=xong, cong_cu=cong_cu)
    finally:
        t.CHUOI_CUU.clear()
        t.CHUOI_CUU.update(truoc)

    assert ket.la_duong_lui is True
    assert ket.chi_phi.get("anh") == 1, (
        "anh_boi_canh vừa vẽ MỘT ảnh mới (+1 anh, đã ghi qua duoc_chi_them) "
        "nhưng dòng [LÙI]/KetQuaCuu.chi_phi không phản ánh đúng")
    assert so_cuu._so["chi_phi"]["anh"] == 1, "không được đếm trùng (ghi hai lần)"
    assert any("[LÙI]" in d and "vừa vẽ mới" in d for d in dong)


# ── LOW: câu `LoiTuChoi` phải là tiếng Việt thân thiện, không lộ thuật ngữ ──


def test_LOW_loi_tu_choi_cau_than_thien_khong_lo_thuat_ngu():
    kl = t.KetLuanTuChoi("tts", "van_ban", "content_rejected", t.RO, 1, "câu gốc")
    cau = str(t.LoiTuChoi(kl))
    assert "khâu=" not in cau
    assert "nghi_do=" not in cau
    assert "ma=" not in cau
    assert "content_rejected" not in cau
    assert "giọng đọc" in cau.lower()
    assert "văn bản" in cau


# ── MED: `_doc_qua_dai_bang_hai_nua` phải thử lại bằng KHOÁ MỚI khi máy chủ
# nhận việc rồi bỏ đó (`LoiKetJob`), như vòng đọc đoạn THƯỜNG ─────────────────


def test_MED_doc_qua_dai_thu_lai_khoa_moi_khi_LoiKetJob(tmp_path, monkeypatch):
    from core.kenh import Kenh

    kenh = Kenh(ma="k1", ten="t", ngon_ngu="vi", voice_id="v", giong_du_phong="",
               gioi_nguoi_ke="", mo_hinh="claude-sonnet-5", giay_nghi_phan=0.0)
    luot = LuotChay(ma_kenh="k1", ma_luot="0001", thu_muc=str(tmp_path))

    goi_tao = []

    class _Client:
        def __init__(self):
            self.tts = self

        def create(self, **kw):
            goi_tao.append(kw)
            return {"id": "job{0}".format(len(goi_tao)), "status": "queued"}

    bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=lambda *a, **k: "",
                    client=_Client(), on_log=[].append, ngu=lambda s: None, ffmpeg="")

    trang = {"n": 0}

    def _cho_job_gia(bc_, job, tran=0, ten_viec="", so=None):
        trang["n"] += 1
        if trang["n"] == 1:
            raise ak.LoiKetJob("máy chủ nhận việc rồi bỏ đó", "engine_unavailable")
        return {"id": "job", "status": "succeeded", "outputs": [{"url": "http://x/a.mp3"}]}

    monkeypatch.setattr(ak, "_cho_job", _cho_job_gia)
    monkeypatch.setattr(ak, "_tai_ket_qua",
                        lambda bc_, goi, cs, dich: open(dich, "wb").write(b"ID3") and dich)
    monkeypatch.setattr(ak, "_noi_mp3", lambda bc_, manh, dich, nghi=None: open(dich, "wb").write(b"ID3"))

    tep = os.path.join(str(tmp_path), "001.mp3")
    chu = ("Một câu khá dài để chia đôi được. " * 5).strip()
    ok = ak._doc_qua_dai_bang_hai_nua(bc, luot, 1, chu, "v", tep, theo_doi=None)

    assert ok is True
    assert os.path.exists(tep)
    khoa_nua_1 = [g["idempotency_key"] for g in goi_tao if ":qua-dai-1" in g["idempotency_key"]]
    assert len(khoa_nua_1) == 2, "phải THỬ LẠI (tạo job lần 2) sau LoiKetJob ở nửa 1"
    assert khoa_nua_1[0] != khoa_nua_1[1], "khoá phải ĐỔI khi thử lại sau LoiKetJob"


def test_MED_doc_qua_dai_het_tran_thi_nem_loi(tmp_path, monkeypatch):
    """Đối chứng: hết trần 3 lần vẫn `LoiKetJob` thì ném lên, không im lặng
    lặp vô hạn."""
    from core.kenh import Kenh

    kenh = Kenh(ma="k1", ten="t", ngon_ngu="vi", voice_id="v", giong_du_phong="",
               gioi_nguoi_ke="", mo_hinh="claude-sonnet-5", giay_nghi_phan=0.0)
    luot = LuotChay(ma_kenh="k1", ma_luot="0001", thu_muc=str(tmp_path))

    class _Client:
        def __init__(self):
            self.tts = self

        def create(self, **kw):
            return {"id": "j", "status": "queued"}

    bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=lambda *a, **k: "",
                    client=_Client(), on_log=[].append, ngu=lambda s: None, ffmpeg="")

    def _cho_job_gia(bc_, job, tran=0, ten_viec="", so=None):
        raise ak.LoiKetJob("máy chủ nhận việc rồi bỏ đó", "engine_unavailable")

    monkeypatch.setattr(ak, "_cho_job", _cho_job_gia)

    tep = os.path.join(str(tmp_path), "001.mp3")
    chu = ("Một câu khá dài để chia đôi được. " * 5).strip()
    with pytest.raises(ak.LoiKetJob):
        ak._doc_qua_dai_bang_hai_nua(bc, luot, 1, chu, "v", tep, theo_doi=None)


# ── LOW-MED: `_ep_loi_thanh_loi_tu_choi` — kết luận từ bảng dò chữ RỘNG phải
# CÓ HẠN (không được khoá vân tay VĨNH VIỄN như một mã rõ ràng của máy chủ) ──


class _LoiGia(RuntimeError):
    """Không có `.code` — chỉ khớp bảng DÒ CHỮ rộng (`la_bi_tu_choi`), không
    khớp bảng HẸP đọc mã của `tcnd.nhan_dien`."""


def test_LOWMED_ep_loi_ket_luan_bang_rong_co_han_khong_vinh_vien(tmp_path):
    dh = {"t": 1_000_000.0}

    def dong_ho():
        return dh["t"]

    so_cuu = t.SoCuu(duong_tep=os.path.join(str(tmp_path), "tu-choi.json"),
                     dong_ho=dong_ho)
    dv = t.DauVao(khau="anh_canh", canh=1, prompt="a cat")
    loi = _LoiGia("Máy chủ từ chối vì vi phạm policy nội bộ của nhà cung cấp.")

    ket_luan = ak._ep_loi_thanh_loi_tu_choi(so_cuu, dv, loi)
    assert isinstance(ket_luan, t.LoiTuChoi)
    assert ket_luan.ket_luan.do_chac == t.AM_THAM_CUC_BO, (
        "kết luận từ bảng dò chữ RỘNG phải CÓ HẠN như kết luận âm thầm, "
        "không được khoá vân tay vĩnh viễn (tcnd.RO)")

    # Còn hạn -> vẫn chặn gửi lại.
    assert not so_cuu.cho_gui(dv)
    # Qua hạn (`phut_han_am_tham`, mặc định) -> phải cho gửi lại, không khoá
    # oan mãi mãi một suy đoán từ bảng RỘNG có thể là dương tính giả.
    dh["t"] += (so_cuu.cau_hinh.phut_han_am_tham + 1) * 60.0
    assert so_cuu.cho_gui(dv)


def test_LOWMED_ep_loi_van_uu_tien_ket_luan_CHI_TIET_tu_bang_hep(tmp_path):
    """Đối chứng: khi bảng HẸP (`tcnd.nhan_dien`) nhận ra được — mã RÕ RÀNG
    của máy chủ — kết luận đó (với `do_chac` riêng của nó) vẫn được dùng
    nguyên, không bị ép về `AM_THAM_CUC_BO`."""
    so_cuu = t.SoCuu(duong_tep=os.path.join(str(tmp_path), "tu-choi.json"))
    dv = t.DauVao(khau="anh_canh", canh=2, prompt="a dog")

    class _LoiRo(RuntimeError):
        def __init__(self, message, code):
            super().__init__(message)
            self.code = code

    loi = _LoiRo("Nội dung bạn gửi vi phạm quy định sử dụng nên đã bị từ chối.",
                 "content_rejected")
    ket_luan = ak._ep_loi_thanh_loi_tu_choi(so_cuu, dv, loi)
    assert ket_luan.ket_luan.do_chac == t.RO
    assert ket_luan.ket_luan.ma == "content_rejected"


def test_MED2_thay_the_van_ap_khi_bam_cu_khop(tmp_path, monkeypatch):
    """Đối chứng: băm KHỚP thì vẫn phải áp bản viết lại như cũ — không được
    tắt luôn tính năng."""
    import test_g6_giong_du_phong as g6

    monkeypatch.setattr(ak, "_tai_ket_qua_mot_lan",
                        lambda bc, goi, cs, dich: open(dich, "wb").write(b"ID3") and dich)
    monkeypatch.setattr(ak, "_tim_ffmpeg", lambda: "")
    monkeypatch.setattr(ak, "_noi_mp3", lambda bc, manh, dich, nghi=None: open(dich, "wb").write(b"ID3"))
    monkeypatch.setattr(ak, "_doi_cao_do_giong", lambda bc, mp3: False)
    monkeypatch.setattr(ak, "_lam_sach_ket_qua", lambda bc, *tep: None)

    cu = "Đoạn hai bản cũ đã bị chặn."
    kb = "Đoạn một giữ nguyên.\n---\n{0}\n---\nĐoạn ba.".format(cu)
    luot = g6._luot(tmp_path, kb)
    d2 = os.path.join(luot.thu_muc, "2-doan")
    os.makedirs(d2)
    json.dump({"2": {"doan_cu": cu, "doan_moi": "BẢN VIẾT LẠI KHỚP BĂM",
                     "bam_cu": hashlib.sha256(cu.encode()).hexdigest()}},
              open(os.path.join(d2, "thay-the.json"), "w", encoding="utf-8"), ensure_ascii=False)

    client = g6._TtsGia()
    bc = ak.BoiCanh(goc=str(tmp_path), kenh=g6._kenh(), goi_chat=lambda *a, **k: "",
                    client=client, on_log=[].append, ngu=lambda s: None, ffmpeg="")
    ak._khau_giong_doc(bc)(luot, TrangThaiKhau(ma="giong_doc"))

    gui = [g["text"] for g in client.goi]
    assert "BẢN VIẾT LẠI KHỚP BĂM" in gui
    assert cu not in gui
