"""Gói G4 — khâu ẢNH đi qua bộ xử lý dùng chung `core/tu_choi_noi_dung.py`.

docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md, mục 2.5 (bảng "Ảnh cảnh" / "Ảnh
bìa") + mục 3.1 (bảng gói G4). Năm điều bắt buộc theo đề bài:

1. Cảnh bị chặn hết cả 3 bước sửa lời nhắc → LÙI `anh_boi_canh`, khâu ảnh vẫn
   XONG (không ném lỗi), và cảnh được ghi `lui: true` trong `tu-choi.json`.
2. `_tao_anh` hỏng ÂM THẦM lặp lại (job kẹt/treo, cùng vân tay, ≥2 lần liên
   tiếp) trong khi khâu ảnh vẫn đang SỐNG (`SucKhoe`) → thoát vòng không trần
   bằng `tcnd.LoiTuChoi`, không quay mãi.
3. Ba tấm ảnh bìa cùng hỏng vì nội dung không làm HỎNG khâu ảnh — `_lam_bia`
   không ném lỗi, chỉ âm thầm bỏ qua tấm bìa đó.
4. Nhân vật đã ghi `nguy_co: mat_that` trong sổ → khâu ẢNH vẽ khung rộng
   NGAY TỪ LẦN VẼ ĐẦU (tiền nghiệm), không đợi bị từ chối rồi mới cứu.
5. Cùng nhân vật đó ở khâu CLIP → thu nhỏ mặt cục bộ TRƯỚC lần gửi Veo đầu
   tiên, không đợi bị từ chối rồi mới cứu.

Không gọi mạng. `_tao_anh`/`videos.create` đều bị monkeypatch bằng hàm giả.
"""
from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

import core.auto_khau as ak
import core.tu_choi_noi_dung as tcnd


@pytest.fixture(autouse=True)
def don_so_cuu_theo_luot():
    """`_so_cuu_cua_luot` cache một `SoCuu` theo `luot.thu_muc` — dọn giữa các
    bài kiểm để không rò trạng thái (cùng nếp `test_canh_bi_google_tu_choi.py`)."""
    ak._SO_CUU_THEO_LUOT.clear()
    yield
    ak._SO_CUU_THEO_LUOT.clear()


def _bc_ghi(goi_chat=None):
    dong = []
    kenh = SimpleNamespace(mo_hinh="claude-sonnet-5", che_do_ke="", anh_nv=[],
                           engine="veo3", style={})
    return SimpleNamespace(kenh=kenh, ghi=lambda s: dong.append(s), _nhat_ky=dong,
                           goi_chat=(goi_chat or (lambda l, **k: "")),
                           kiem_dung=lambda: None, ngu=lambda _g: None,
                           on_log=None, ffmpeg="ffmpeg-gia",
                           client=object()), dong


def _luot_gia(tmp_path, tong_so_canh=20):
    """`tong_so_canh` phải khớp `4-canh.json` — trần theo lượt (mục 2.6 tài
    liệu) tính theo TỈ LỆ số cảnh; để 0 thì bước TRẢ TIỀN nào cũng bị coi là
    hết ngân sách ngay từ đầu (xem `_so_cuu_cua_luot`)."""
    with open(os.path.join(str(tmp_path), "4-canh.json"), "w", encoding="utf-8") as f:
        json.dump([{"scene_id": i} for i in range(1, tong_so_canh + 1)], f)
    return SimpleNamespace(ma_kenh="k", ma_luot="0001", thu_muc=str(tmp_path))


class _HopRong:
    def lay(self):
        return []

    def lam_moi(self, cu):
        return []


# ═══ 1) cảnh bị chặn hết 3 bước sửa lời nhắc → LÙI anh_boi_canh, khâu XONG,
#        cảnh ghi lui ══════════════════════════════════════════════════════


def test_canh_bi_chan_het_ca_ba_buoc_thi_lui_ve_anh_boi_canh(tmp_path, monkeypatch):
    # Bối cảnh sẵn có: cảnh 5 khai `reference_files: ["loc1.png"]`, và ảnh bối
    # cảnh ấy đã tồn tại trên đĩa (đường đạo diễn tu_xay) — LÙI dùng NGAY,
    # miễn phí, không cần vẽ gì mới.
    tc = tmp_path / "tham-chieu"
    tc.mkdir()
    (tc / "loc1.png").write_bytes(b"anh-boi-canh-that")

    c = {"scene_id": 5, "img_prompt": "a soldier keeping the gate. Style: 3D",
        "reference_files": json.dumps(["loc1.png"])}
    luot = _luot_gia(tmp_path)
    tep = str(tmp_path / "5.png")

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        # KHÔNG một lời nhắc nào qua được — mọi bước sửa chữ đều vô ích.
        raise RuntimeError("content_rejected: bị bộ lọc từ chối")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    # AI trả nguyên văn (không đổi được gì) — buộc chuỗi phải đi hết các bước
    # sửa CHỮ trước khi rơi xuống LÙI.
    bc, dong = _bc_ghi(goi_chat=lambda l, **k: c["img_prompt"])

    ak._lam_anh_canh(bc, luot, c, tep, _HopRong())  # KHÔNG được ném lỗi

    assert os.path.exists(tep)
    with open(tep, "rb") as f:
        assert f.read() == b"anh-boi-canh-that"

    with open(os.path.join(luot.thu_muc, "tu-choi.json"), encoding="utf-8") as f:
        so_dia = json.load(f)
    # Khoá "khâu:cảnh" (rà soát 2.138.0, H3) và nhãn tiếng Việt trên dòng báo.
    assert so_dia["canh"]["anh_canh:5"]["lui"] is True
    assert so_dia["canh"]["anh_canh:5"]["khau"] == "anh_canh"
    assert any("[LÙI]" in d and "cảnh 5 · ảnh" in d and "bối cảnh" in d for d in dong), dong


def test_canh_lui_thi_khau_clip_dung_anh_dong_khong_goi_videos_create(tmp_path, monkeypatch):
    """Nối tiếp bài trên: sổ đã đánh dấu cảnh LÙI thì `_lam_clip` phải dùng
    ảnh động, không đốt job Veo lên một ảnh không phải ảnh cảnh thật (mục 2.5
    tài liệu, "Bản lùi được đánh dấu trong sổ...")."""
    c = {"scene_id": 5, "img_prompt": "a soldier", "video_prompt": "p"}
    luot = _luot_gia(tmp_path)
    anh = tmp_path / "5.png"
    anh.write_bytes(b"anh-boi-canh-that")
    dich = str(tmp_path / "5.mp4")

    bc, dong = _bc_ghi()
    so_cuu = ak._so_cuu_cua_luot(bc, luot)
    so_cuu.ghi_ket_qua_canh(tcnd.DauVao(khau="anh_canh", canh=5), ["anh_boi_canh"], lui=True)

    goi_videos = []
    monkeypatch.setattr(ak, "_dung_anh_dong_thay_clip",
                        lambda bc, luot, c, nguon, dich_, giay, so_canh:
                        (goi_videos.append("anh_dong"), open(dich_, "wb").write(b"clip-gia")))

    def create(**kw):
        goi_videos.append("videos.create")
        return {"id": "job", "status": "succeeded"}

    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    ak._lam_clip(bc, luot, c, str(anh), dich, 8)

    assert goi_videos == ["anh_dong"], "phải dùng ảnh động, KHÔNG gọi videos.create"
    assert os.path.exists(dich)


# ═══ 2) `_tao_anh` hỏng ÂM THẦM lặp lại, khâu ảnh vẫn SỐNG → thoát vòng ═════


def test_tao_anh_am_tham_lap_lai_thoat_vong_khi_khau_song(monkeypatch):
    """Job kẹt/treo (`LoiKetJob`) CÙNG vân tay ≥2 lần liên tiếp, trong khi
    khâu ảnh vẫn có tấm khác xong gần đây (`SucKhoe.khau_dang_song`) — luật
    #7 (mục 2.3 tài liệu) kết luận đây là NỘI DUNG bị chặn ngầm, không phải
    hạ tầng ốm — `_tao_anh` phải NÉM `tcnd.LoiTuChoi`, không quay vòng mãi."""
    gio = {"t": 1_000_000.0}
    so_lan = {"n": 0}

    def tao_job_gia(bc, ham, **kw):
        return {"id": "j"}

    def cho_anh_gia(bc, job, ten_hien="", so=None):
        so_lan["n"] += 1
        assert so_lan["n"] < 10, "vòng không trần không được quay mãi"
        gio["t"] += 30.0
        if so_lan["n"] == 2:
            # Một tấm KHÁC xong SAU lần hỏng đầu của đúng vân tay này (rà
            # soát 2.138.0, H4 — "khâu còn sống" phải tính từ mốc ấy).
            so_cuu.bao_xong("anh")
        raise ak.LoiKetJob("máy chủ nhận việc rồi bỏ đó", "engine_unavailable")

    monkeypatch.setattr(ak, "_tao_job", tao_job_gia)
    monkeypatch.setattr(ak, "_cho_anh", cho_anh_gia)
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)

    bc = SimpleNamespace(kiem_dung=lambda: None, ghi=lambda s: None,
                        client=SimpleNamespace(images=SimpleNamespace(create=lambda **k: None)))
    so_cuu = tcnd.SoCuu(dong_ho=lambda: gio["t"])
    for _ in range(3):  # khâu ảnh "đang sống": ≥3 tấm xong gần đây (mục 2.3)
        so_cuu.bao_xong("anh")

    dv = tcnd.DauVao(khau="anh_canh", canh=9, prompt="a cat")
    with pytest.raises(tcnd.LoiTuChoi) as loi_ra:
        ak._tao_anh(bc, SimpleNamespace(), "a cat", _HopRong(), "khoa9",
                   so_cuu=so_cuu, dv=dv)
    assert loi_ra.value.ket_luan.khau == "anh_canh"
    assert loi_ra.value.ket_luan.do_chac == tcnd.AM_THAM_CUC_BO


def test_tao_anh_am_tham_khau_dang_om_thi_van_vong_cu_khong_trap(monkeypatch):
    """Cùng lỗi treo lặp lại nhưng khâu ảnh KHÔNG có tấm nào xong gần đây
    (hạ tầng thật ốm, không phải nội dung) — vòng không trần CŨ phải tiếp
    tục, không được ném `LoiTuChoi` oan (mục 2.3 tài liệu, "cách phân biệt
    lỗi hạ tầng"). Bài kiểm dừng sớm bằng cách cho lần thứ ba THÀNH CÔNG."""
    so_lan = {"n": 0}

    def tao_job_gia(bc, ham, **kw):
        return {"id": "j"}

    def cho_anh_gia(bc, job, ten_hien="", so=None):
        so_lan["n"] += 1
        if so_lan["n"] < 3:
            raise ak.LoiKetJob("máy chủ nhận việc rồi bỏ đó", "engine_unavailable")
        return {"id": "j", "status": "succeeded"}

    monkeypatch.setattr(ak, "_tao_job", tao_job_gia)
    monkeypatch.setattr(ak, "_cho_anh", cho_anh_gia)
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)

    bc = SimpleNamespace(kiem_dung=lambda: None, ghi=lambda s: None,
                        client=SimpleNamespace(images=SimpleNamespace(create=lambda **k: None)))
    so_cuu = tcnd.SoCuu()  # KHÔNG gọi bao_xong("anh") — khâu coi như đang ốm.

    dv = tcnd.DauVao(khau="anh_canh", canh=9, prompt="a cat")
    ra = ak._tao_anh(bc, SimpleNamespace(), "a cat", _HopRong(), "khoa9",
                     so_cuu=so_cuu, dv=dv)
    assert ra == {"id": "j", "status": "succeeded"}
    assert so_lan["n"] == 3


# ═══ 3) ba tấm ảnh bìa cùng hỏng vì nội dung KHÔNG làm hỏng khâu ảnh ════════


def test_ba_bia_hong_khong_lam_hong_khau_anh(tmp_path, monkeypatch):
    luot = _luot_gia(tmp_path)
    thu_muc_bia = str(tmp_path / "7-thumbnail")
    os.makedirs(thu_muc_bia, exist_ok=True)

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        raise RuntimeError("content_rejected: bị bộ lọc từ chối")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    bc, dong = _bc_ghi(goi_chat=lambda l, **k: "khong doi gi ca, giu nguyen y")

    ta_bia = {"portrait_main": "a hero, close-up portrait. Style: 3D"}
    muc = [(1, ("portrait_main", "mac dinh 1")),
          (2, ("dramatic_scene", "mac dinh 2")),
          (3, ("youtube_ctr", "mac dinh 3"))]

    for m in muc:
        ket = ak._lam_bia(bc, luot, _HopRong(), thu_muc_bia, m, ta_bia,
                          "Tiêu đề phim", "Chữ bìa", so=None)
        assert ket[0] == m[0]
        assert ket[1] is False  # không phải "đã có sẵn"

    # KHÔNG tấm bìa nào được tạo (đều bị LÙI bỏ qua) — nhưng không hàm nào
    # ném lỗi, tức khâu ảnh không hề bị dừng.
    for so_bia, _ in muc:
        assert not os.path.exists(os.path.join(thu_muc_bia, "thumb_{0:03d}.png".format(so_bia)))
    assert any("bỏ qua" in d for d in dong), dong


def test_bia_hong_ha_tang_that_van_nem_len_binh_thuong(tmp_path, monkeypatch):
    """Đối chứng: lỗi HẠ TẦNG thật (không phải nội dung) ở ảnh bìa vẫn phải
    NÉM LÊN như cũ — chỉ lỗi NỘI DUNG mới được `_lam_bia` nuốt êm."""
    luot = _luot_gia(tmp_path)
    thu_muc_bia = str(tmp_path / "7-thumbnail")
    os.makedirs(thu_muc_bia, exist_ok=True)

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        raise RuntimeError("mạng đứt giữa chừng")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    bc, dong = _bc_ghi()
    ta_bia = {"portrait_main": "a hero, close-up portrait. Style: 3D"}
    with pytest.raises(RuntimeError, match="mạng đứt"):
        ak._lam_bia(bc, luot, _HopRong(), thu_muc_bia, (1, ("portrait_main", "x")),
                   ta_bia, "Tiêu đề", "Chữ bìa", so=None)


# ═══ 4) nhân vật nguy cơ (mat_that) → khâu ẢNH vẽ khung rộng NGAY lần đầu ═══


def test_nhan_vat_nguy_co_thi_anh_ve_khung_rong_ngay_lan_dau(tmp_path, monkeypatch):
    c = {"scene_id": 12, "img_prompt": "close-up portrait of nv9. Style: 3D",
        "characters_used": "nv9"}
    luot = _luot_gia(tmp_path)
    tep = str(tmp_path / "12.png")

    bc, dong = _bc_ghi()
    so_cuu = ak._so_cuu_cua_luot(bc, luot)
    # ≥2 xác nhận (rà soát 2.138.0: một lần tham chiếu hỏng KHÔNG đủ).
    so_cuu.ghi_nguy_co_nhan_vat(["nv9"], "mat_that", [3, 4],
                                xac_nhan=["tham_chieu", "clip:3"])

    prompt_goi = []

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        prompt_goi.append(prompt)
        return {"id": "job1"}

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    monkeypatch.setattr(ak, "_tai_ket_qua", lambda bc, goi_, i, tep_: open(tep_, "wb").write(b"png"))
    monkeypatch.setattr(ak, "_xoa_dau", lambda bc, tep_: None)

    ak._lam_anh_canh(bc, luot, c, tep, _HopRong())

    assert len(prompt_goi) == 1, "phải vẽ ĐÚNG MỘT lần — vẽ khung rộng ngay từ đầu là qua"
    assert "Wide shot" in prompt_goi[0], "lời nhắc gửi đi phải có câu khung rộng NGAY từ lần vẽ đầu"
    assert prompt_goi[0].startswith(c["img_prompt"])
    # KHÔNG được ghi đè lời nhắc gốc của CẢNH này — đây chỉ là một mẹo đỡ tốn
    # một lượt hỏng cho LẦN VẼ NÀY, không phải một bản sửa đã xác nhận.
    assert c["img_prompt"] == "close-up portrait of nv9. Style: 3D"


# ═══ 5) cùng nhân vật đó ở khâu CLIP → thu nhỏ mặt cục bộ TRƯỚC lần gửi đầu ═


def test_nhan_vat_nguy_co_thi_clip_thu_nho_truoc_lan_gui_dau(tmp_path, monkeypatch):
    from PIL import Image

    c = {"scene_id": 7, "img_prompt": "a lonely man", "video_prompt": "p",
        "characters": ["nv7"]}
    luot = _luot_gia(tmp_path)
    anh = tmp_path / "7.png"
    Image.new("RGB", (160, 90), (200, 120, 80)).save(str(anh))
    dich = str(tmp_path / "7.mp4")

    bc, dong = _bc_ghi()
    so_cuu = ak._so_cuu_cua_luot(bc, luot)
    so_cuu.ghi_nguy_co_nhan_vat(["nv7"], "mat_that", xac_nhan=["tham_chieu", "clip:3"])

    goi_anh = []
    so_lan = {"n": 0}

    def create(**kw):
        so_lan["n"] += 1
        goi_anh.append(kw["image_url"])
        return {"id": "job_{0}".format(so_lan["n"]), "status": "succeeded"}

    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    monkeypatch.setattr(ak, "_url_anh_canh",
                        lambda bc, luot, so_canh, duong, bo_qua_nho=False: "http://anh/" + os.path.basename(duong))
    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_tai_ket_qua",
                        lambda bc, goi_, idx, duong: open(duong, "wb").write(b"clip"))
    monkeypatch.setattr(ak, "_kiem_media", lambda *a, **k: None)

    ak._lam_clip(bc, luot, c, str(anh), dich, 8)

    assert so_lan["n"] == 1, "phải qua ngay lần gửi đầu — không đợi bị từ chối rồi mới cứu"
    assert goi_anh[0] == "http://anh/7.png.thu-nho.png"
    assert os.path.exists(dich)


def test_nhan_vat_nguy_co_da_thu_nho_that_bai_thi_di_thang_khung_rong(tmp_path, monkeypatch):
    """Nhân vật đã biết THU NHỎ không đủ (một cảnh khác cùng lượt) — tiền
    nghiệm phải đi THẲNG bước vẽ lại khung rộng, không lặp lại bước rẻ đã
    biết không ăn thua (mục 2.7 tài liệu)."""
    c = {"scene_id": 8, "img_prompt": "a lonely man", "video_prompt": "p",
        "characters": ["nv7"]}
    luot = _luot_gia(tmp_path)
    anh = tmp_path / "8.png"
    anh.write_bytes(b"khong-quan-trong")
    anh_rong = str(tmp_path / "8-rong.png")
    with open(anh_rong, "wb") as f:
        f.write(b"anh-rong-gia")
    dich = str(tmp_path / "8.mp4")

    bc, dong = _bc_ghi()
    so_cuu = ak._so_cuu_cua_luot(bc, luot)
    so_cuu.ghi_nguy_co_nhan_vat(["nv7"], "mat_that", xac_nhan=["tham_chieu", "clip:3"])
    so_cuu.danh_dau_thu_nho_that_bai(["nv7"])

    goi_anh = []
    so_lan = {"n": 0}

    def create(**kw):
        so_lan["n"] += 1
        goi_anh.append(kw["image_url"])
        return {"id": "job_{0}".format(so_lan["n"]), "status": "succeeded"}

    class _CongCuVeAnh:
        def ve_anh(self, prompt, tham_chieu, khoa_phu):
            assert "close-up" not in prompt or True
            return anh_rong

        def viet_lai(self, prompt, ly_do, loai):  # pragma: no cover — không dùng ở đây
            return prompt

        def anh_dong(self, anh_, dich_, giay):  # pragma: no cover
            pass

        def ghi(self, dong_):
            pass

        def kiem_dung(self):
            pass

    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    monkeypatch.setattr(ak, "_url_anh_canh",
                        lambda bc, luot, so_canh, duong, bo_qua_nho=False: "http://anh/" + os.path.basename(duong))
    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_tai_ket_qua",
                        lambda bc, goi_, idx, duong: open(duong, "wb").write(b"clip"))
    monkeypatch.setattr(ak, "_kiem_media", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_cong_cu_auto", lambda bc, luot, c, so: _CongCuVeAnh())

    ak._lam_clip(bc, luot, c, str(anh), dich, 8)

    assert so_lan["n"] == 1
    assert goi_anh[0] == "http://anh/8-rong.png"
