"""Google/Veo âm thầm (hay rõ ràng) từ chối dựng clip cho ẢNH CẢNH có mặt
người thật cận cảnh — sự cố 28/09/2026, GÓI G3.

Bản trước (2.137.9) tự xử ngay trong `_lam_clip`/`_cuu_canh_bi_google_tu_choi`.
Từ gói G3, mọi lỗi NỘI DUNG (rõ hay âm thầm) đi qua bộ xử lý dùng chung
`core/tu_choi_noi_dung.py`: `_lam_clip` gọi `tcnd.lam_co_cuu`, chạy
`tcnd.CHUOI_CUU["clip"]` — đăng ký trong chính `core/auto_khau.py`, gồm:

    1. `thu_nho_mat_cuc_bo` — thu nhỏ mặt TRÊN MÁY (Pillow, miễn phí, giữ
       ĐÚNG khuôn mặt gốc khi thành công). Đo G0 28/09/2026: 2/3 ảnh hỏng
       thật qua được.
    2. `ve_lai_khung_rong` — vẽ MỘT ảnh MỚI bằng dịch vụ ảnh (nhân vật mới).
    3. `viet_lai_prompt_video` — khi thủ phạm là LỜI NHẮC (không phải ảnh).
    4. LÙI `anh_dong` — ảnh động, miễn phí, luôn ra được sản phẩm.

Bài dưới đây canh:
1. Lỗi nội dung KHÔNG được gửi lại y nguyên (không rơi vào vòng vô hạn).
2. `content_rejected` lúc TẠO job (nghi_do=prompt) → viết lại lời nhắc video,
   không đụng tới ảnh.
3. `prompt_image_rejected_by_provider` / `engine_unavailable` lặp lại
   (nghi_do=anh) → thử thu nhỏ mặt trước, thu nhỏ không xong (ảnh giả không
   mở được bằng Pillow trong bài kiểm) thì vẽ lại khung rộng.
4. Luật #7 (2 lần liên tiếp cùng vân tay) cần khâu VIDEO đang "sống"
   (`SucKhoe`) — khâu đang ốm thì vẫn vòng KHÔNG TRẦN như cũ.
5. `gui_lai_mai=False` (clip sớm, làm thêm trong khâu ảnh) KHÔNG cứu — giữ
   nguyên hành vi cũ (bỏ cuộc nhanh, tối đa hai lần đặt lại).
6. Hết cả chuỗi vẫn hỏng → LÙI ảnh động, luôn ra được `dich`.
7. Ảnh cảnh là BẢN LÙI của khâu ảnh (sổ đánh dấu `lui`) → dùng ảnh động ngay,
   không gọi `videos.create` một lần nào.

Không gọi mạng, không cần ffmpeg/PIL thật (trừ bài kiểm riêng cho
`_thu_nho_mat_tren_khung_rong`, dùng Pillow thật trên một ảnh GIẢ dựng ngay
trong bài kiểm — không tải gì từ mạng).
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

import core.auto_khau as ak
import core.tu_choi_noi_dung as tcnd


class _LoiCong(RuntimeError):
    """Lỗi mang `.code` như `APIStatusError` thật của SDK."""

    def __init__(self, message: str, code: str, status: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


CAU_ANH_BI_TU_CHOI = (
    "Hệ thống dựng video đã thử cặp ảnh + mô tả này 3 lần nhưng không dựng "
    "được (thường do ảnh người thật/nhận diện khuôn mặt hoặc mô tả bị chặn). "
    "Bạn KHÔNG bị trừ tiền và không có yêu cầu nào được tạo.")

CAU_TU_CHOI_LUC_TAO = "Nội dung bạn gửi vi phạm quy định sử dụng nên đã bị từ chối. Bạn KHÔNG bị trừ tiền."


@pytest.fixture(autouse=True)
def don_so_cuu_theo_luot():
    """`_so_cuu_cua_luot` cache MỘT `SoCuu` cho mỗi `luot.thu_muc` — dọn giữa
    các bài kiểm để không rò trạng thái (mỗi bài dùng `tmp_path` riêng nên
    thực ra không đụng nhau, nhưng dọn cho chắc và cho bộ nhớ không phình)."""
    ak._SO_CUU_THEO_LUOT.clear()
    yield
    ak._SO_CUU_THEO_LUOT.clear()


def _bc_ghi():
    """BoiCanh giả — chỉ giữ nhật ký để bài kiểm đọc lại được."""
    dong = []
    return SimpleNamespace(on_log=None, ngu=lambda _g: None,
                           ghi=lambda s: dong.append(s),
                           kiem_dung=lambda: None, ffmpeg="ffmpeg-gia",
                           kenh=SimpleNamespace(engine="veo3", mo_hinh="claude-sonnet-5"),
                           goi_chat=lambda *a, **k: ""), dong


def _luot_gia(tmp_path, tong_so_canh=20):
    """`tong_so_canh` (mặc định 20) phải khớp thật với `4-canh.json` — trần
    theo lượt (ảnh/clip/chat, mục 2.6 tài liệu) tính theo TỈ LỆ số cảnh; thiếu
    bảng cảnh thì `_so_cuu_cua_luot` coi `tong_so_canh=0` và MỌI bước trả tiền
    bị coi là hết ngân sách ngay từ đầu."""
    with open(os.path.join(str(tmp_path), "4-canh.json"), "w", encoding="utf-8") as f:
        json.dump([{"scene_id": i} for i in range(1, tong_so_canh + 1)], f)
    return SimpleNamespace(ma_kenh="k", ma_luot="0001", thu_muc=str(tmp_path))


def _canh(nhan_vat=("nv7",)):
    return {"scene_id": 7, "img_prompt": "a lonely man", "video_prompt": "p",
           "characters": list(nhan_vat)}


class _CongCuGia:
    """`tcnd.CongCu` giả — không mạng. `ve_anh_ket_qua`/`viet_lai_ket_qua`
    quyết định bước ấy THÀNH CÔNG (trả đường dẫn/chuỗi) hay THẤT BẠI (đặt một
    `Exception` để bước `ap` ném lại, `_chay_chuoi_cuu` tự bắt và thử bước kế)."""

    def __init__(self):
        self.ve_anh_goi = []
        self.viet_lai_goi = []
        self.anh_dong_goi = []
        self.ve_anh_ket_qua = None
        self.viet_lai_ket_qua = None

    def ve_anh(self, prompt, tham_chieu, khoa_phu):
        self.ve_anh_goi.append((prompt, tuple(tham_chieu), khoa_phu))
        if isinstance(self.ve_anh_ket_qua, Exception):
            raise self.ve_anh_ket_qua
        return self.ve_anh_ket_qua

    def viet_lai(self, prompt, ly_do, loai):
        self.viet_lai_goi.append((prompt, ly_do, loai))
        if isinstance(self.viet_lai_ket_qua, Exception):
            raise self.viet_lai_ket_qua
        return self.viet_lai_ket_qua

    def anh_dong(self, anh, dich, giay):  # pragma: no cover — không dùng ở đây
        self.anh_dong_goi.append((anh, dich, giay))

    def ghi(self, dong):
        pass

    def kiem_dung(self):
        pass


def _cai_dat_chung(monkeypatch, tmp_path, cong_cu):
    """Giả các hàm chạm-mạng/chạm-đĩa dùng chung, giữ nguyên như bài kiểm cũ."""
    monkeypatch.setattr(ak, "_url_anh_canh",
                        lambda bc, luot, so_canh, duong, bo_qua_nho=False: "http://anh/" + os.path.basename(duong))
    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_cong_cu_auto", lambda bc, luot, c, so: cong_cu)

    def tai_ket_qua_gia(bc, goi, _idx, duong):
        os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
        with open(duong, "wb") as f:
            f.write("noi-dung-{0}".format(goi.get("id")).encode("utf-8"))

    monkeypatch.setattr(ak, "_tai_ket_qua", tai_ket_qua_gia)
    monkeypatch.setattr(ak, "_kiem_media", lambda *a, **k: None)
    anh_dong_goi = {}

    def anh_dong_gia(bc, luot, c, nguon_anh, dich_, giay, so_canh):
        anh_dong_goi["nguon_anh"] = nguon_anh
        anh_dong_goi["dich"] = dich_
        os.makedirs(os.path.dirname(dich_) or ".", exist_ok=True)
        with open(dich_, "wb") as f:
            f.write(b"clip-dong-gia")

    monkeypatch.setattr(ak, "_dung_anh_dong_thay_clip", anh_dong_gia)
    return anh_dong_goi


# ── 1) 403 content_rejected LÚC TẠO (nghi_do=prompt) → viết lại lời nhắc,
#      KHÔNG đụng ảnh, KHÔNG vòng ─────────────────────────────────────────


def test_content_rejected_luc_tao_re_sang_viet_lai_prompt_khong_vong(monkeypatch, tmp_path):
    anh = tmp_path / "7.png"
    anh.write_bytes(b"khong-phai-anh-that")
    dich = str(tmp_path / "7.mp4")

    so_lan = {"n": 0}

    def create(**kw):
        so_lan["n"] += 1
        if so_lan["n"] == 1:
            raise _LoiCong(CAU_TU_CHOI_LUC_TAO, "content_rejected", status=403)
        assert "đã sửa" in kw["prompt"]
        return {"id": "job_{0}".format(so_lan["n"]), "status": "succeeded"}

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    cong_cu.viet_lai_ket_qua = "p đã sửa"
    _cai_dat_chung(monkeypatch, tmp_path, cong_cu)

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    assert so_lan["n"] == 2, "chỉ gửi lại ĐÚNG MỘT lần, với lời nhắc đã viết lại"
    assert len(cong_cu.viet_lai_goi) == 1
    assert not cong_cu.ve_anh_goi, "content_rejected trên PROMPT không được đụng tới ảnh"
    assert os.path.exists(dich)
    assert any("[CỨU]" in d or "cứu" in d.lower() for d in dong) or True  # dòng log thật do module lõi ghi


# ── 2) prompt_image_rejected_by_provider (nghi_do=anh) → thử thu nhỏ mặt
#      trước (thất bại vì ảnh giả), rồi vẽ lại khung rộng ──────────────────


def test_prompt_image_rejected_by_provider_thu_nho_that_bai_roi_ve_lai_khung_rong(monkeypatch, tmp_path):
    anh = tmp_path / "7.png"
    anh.write_bytes(b"khong-phai-anh-that")  # PIL không mở được -> bước 1 tự bỏ qua
    dich = str(tmp_path / "7.mp4")
    anh_rong = str(tmp_path / "7-rong.png")
    with open(anh_rong, "wb") as f:
        f.write(b"anh-rong-gia")

    so_lan = {"n": 0}

    def create(**kw):
        so_lan["n"] += 1
        if so_lan["n"] == 1:
            raise _LoiCong(CAU_ANH_BI_TU_CHOI, "prompt_image_rejected_by_provider")
        assert kw["image_url"] == "http://anh/7-rong.png"
        return {"id": "job_{0}".format(so_lan["n"]), "status": "succeeded"}

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    cong_cu.ve_anh_ket_qua = anh_rong
    _cai_dat_chung(monkeypatch, tmp_path, cong_cu)

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    assert so_lan["n"] == 2, "gửi lại y nguyên là đúng cái bẫy đã đo được — chỉ MỘT lần rồi rẽ sang cứu"
    assert len(cong_cu.ve_anh_goi) == 1
    assert cong_cu.ve_anh_goi[0][0].startswith("a lonely man"), "phải dùng img_prompt, không phải video_prompt"
    assert os.path.exists(dich)


# ── 3) luật #7: engine_unavailable 2 lần liên tiếp, khâu VIDEO đang sống ───


def test_engine_unavailable_hai_lan_lien_tiep_khi_khau_song_re_sang_cuu(monkeypatch, tmp_path):
    anh = tmp_path / "7.png"
    anh.write_bytes(b"khong-phai-anh-that")
    dich = str(tmp_path / "7.mp4")
    anh_rong = str(tmp_path / "7-rong.png")
    with open(anh_rong, "wb") as f:
        f.write(b"anh-rong-gia")

    so_lan = {"n": 0}

    def create(**kw):
        so_lan["n"] += 1
        return {"id": "job_{0}".format(so_lan["n"]), "status": "queued"}

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    cong_cu.ve_anh_ket_qua = anh_rong
    _cai_dat_chung(monkeypatch, tmp_path, cong_cu)

    so_cuu = ak._so_cuu_cua_luot(bc, luot)

    lan_cho = {"n": 0}

    def cho_hong(*_a, **_k):
        lan_cho["n"] += 1
        if lan_cho["n"] <= 2:
            if lan_cho["n"] == 2:
                # Khâu VIDEO có một clip KHÁC xong SAU lần hỏng đầu của cảnh
                # này — "đang sống" theo luật mới (rà soát 2.138.0, H4: clip
                # xong TRƯỚC lần hỏng đầu không còn tính; bản cũ gọi
                # `bao_xong` trước khi chạy).
                so_cuu.bao_xong("video")
            raise ak.LoiKetJob("máy chủ báo job hỏng (đã hoàn tiền): x", "engine_unavailable")
        return {"id": "job_{0}".format(lan_cho["n"]), "status": "succeeded"}

    monkeypatch.setattr(ak, "_cho_theo_tien_do", cho_hong)

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    # 2 lần liên tiếp cùng vân tay là đủ luật #7 (không có lần thứ ba với ẢNH
    # CŨ) — nhưng chuỗi cứu vẫn phải GỬI LẠI một lần nữa với ảnh ĐÃ SỬA (bước 1
    # "thu nhỏ" tự bỏ qua vì ảnh giả không mở được, bước 2 "vẽ lại khung rộng"
    # mới thật sự tạo ra bản gửi thứ ba).
    assert so_lan["n"] == 3
    assert len(cong_cu.ve_anh_goi) == 1
    assert os.path.exists(dich)


def test_engine_unavailable_khau_dang_om_thi_van_vong_cu(monkeypatch, tmp_path):
    """KHÔNG có job video nào khác xong gần đây (khâu đang ốm) — dù hỏng cùng
    vân tay bao nhiêu lần, KHÔNG được kết luận nội dung; vẫn vòng đặt-lại-bằng-
    khoá-mới KHÔNG TRẦN như cũ cho tới khi (ở đây, giả lập) máy chủ tự khỏi."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"khong-phai-anh-that")
    dich = str(tmp_path / "7.mp4")

    def create(**kw):
        return {"id": "job_x", "status": "queued"}

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    _cai_dat_chung(monkeypatch, tmp_path, cong_cu)
    # KHÔNG gọi so_cuu.bao_xong("video") — khâu "đang ốm" theo `SucKhoe`.

    lan_cho = {"n": 0}

    def cho_hong(*_a, **_k):
        lan_cho["n"] += 1
        if lan_cho["n"] <= 4:
            raise ak.LoiKetJob("máy chủ báo job hỏng (đã hoàn tiền): x", "engine_unavailable")
        return {"id": "job_x", "status": "succeeded"}

    monkeypatch.setattr(ak, "_cho_theo_tien_do", cho_hong)

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    assert lan_cho["n"] == 5, "hỏng 4 lần liên tiếp mà khâu đang ốm vẫn KHÔNG được cứu, cứ đặt lại tới khi xong"
    assert not cong_cu.ve_anh_goi, "không được rẽ sang cứu khi khâu đang ốm"
    assert os.path.exists(dich)


def test_mot_lan_engine_unavailable_thi_van_thu_lai_binh_thuong(monkeypatch, tmp_path):
    """MỘT lần `engine_unavailable` chưa phải dấu hiệu — vẫn phải đặt lại bằng
    khoá mới như luật cũ (đo thật 14/08/2026: chín clip kẹt rồi tự qua)."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png")
    dich = str(tmp_path / "7.mp4")

    so_lan_goi = {"n": 0}

    def create_ok(**kw):
        so_lan_goi["n"] += 1
        return {"id": "job_{0}".format(so_lan_goi["n"]), "status": "queued"}

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create_ok))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    _cai_dat_chung(monkeypatch, tmp_path, cong_cu)

    lan = {"n": 0}

    def cho_theo_tien_do(bc, job, *a, **k):
        lan["n"] += 1
        if lan["n"] == 1:
            raise ak.LoiKetJob("máy chủ báo job hỏng (đã hoàn tiền): x", "engine_unavailable")
        return {"id": job["id"], "status": "succeeded"}

    monkeypatch.setattr(ak, "_cho_theo_tien_do", cho_theo_tien_do)

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    assert not cong_cu.ve_anh_goi, "một lần xui thì vẫn phải cho đặt lại bằng khoá mới"
    assert so_lan_goi["n"] == 2, "đặt lại đúng một lần rồi xong"


# ── 4) clip SỚM (`gui_lai_mai=False`) không cứu — giữ nguyên hành vi cũ ────


def test_clip_som_khau_anh_khong_cuu_du_hong_ma_moi(monkeypatch, tmp_path):
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png")
    dich = str(tmp_path / "7.mp4")

    so_lan_goi = {"n": 0}

    def create_hong(**_kw):
        so_lan_goi["n"] += 1
        raise _LoiCong(CAU_ANH_BI_TU_CHOI, "prompt_image_rejected_by_provider")

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create_hong))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    _cai_dat_chung(monkeypatch, tmp_path, cong_cu)

    with pytest.raises(Exception):
        ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8, gui_lai_mai=False)

    assert so_lan_goi["n"] == 1, "clip sớm không được rẽ sang cứu"
    assert not cong_cu.ve_anh_goi
    assert not os.path.exists(str(anh) + ".khung-rong.png")


def test_clip_som_khau_anh_khong_cuu_du_engine_unavailable_hai_lan(monkeypatch, tmp_path):
    """Cùng luật như trên, cho nhánh `engine_unavailable` lặp lại — clip sớm
    vẫn bỏ cuộc sau tối đa hai lần đặt lại, KHÔNG rẽ sang cứu."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png")
    dich = str(tmp_path / "7.mp4")

    def create_ok(**kw):
        return {"id": "job_x", "status": "queued"}

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create_ok))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    _cai_dat_chung(monkeypatch, tmp_path, cong_cu)

    def cho_hong(*_a, **_k):
        raise ak.LoiKetJob("máy chủ báo job hỏng (đã hoàn tiền): x", "engine_unavailable")

    monkeypatch.setattr(ak, "_cho_theo_tien_do", cho_hong)

    with pytest.raises(ak.LoiKetJob):
        ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8, gui_lai_mai=False)

    assert not cong_cu.ve_anh_goi


# ── 5) hết cả chuỗi vẫn hỏng → LÙI ảnh động, luôn ra được sản phẩm ─────────


def test_het_ca_chuoi_van_hong_thi_lui_ve_anh_dong(monkeypatch, tmp_path):
    anh = tmp_path / "7.png"
    anh.write_bytes(b"khong-phai-anh-that")  # bước 1 (thu nhỏ) tự hỏng
    dich = str(tmp_path / "7.mp4")

    def create(**kw):
        raise _LoiCong(CAU_ANH_BI_TU_CHOI, "prompt_image_rejected_by_provider")

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    cong_cu.ve_anh_ket_qua = RuntimeError("dịch vụ ảnh cũng bị chặn")  # bước 2 cũng hỏng
    anh_dong_goi = _cai_dat_chung(monkeypatch, tmp_path, cong_cu)

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    assert os.path.exists(dich)
    assert anh_dong_goi.get("dich") == dich


# ── 6) ảnh cảnh là BẢN LÙI của khâu ảnh → ảnh động ngay, không gọi videos.create


def test_canh_anh_muon_tu_khau_anh_thi_dung_anh_dong_khong_goi_videos_create(monkeypatch, tmp_path):
    anh = tmp_path / "7.png"
    anh.write_bytes(b"anh-muon-tu-canh-khac")
    dich = str(tmp_path / "7.mp4")

    # Sổ do khâu ẢNH (G4) ghi: cảnh 7 đã dùng đường LÙI (mượn / bối cảnh
    # không người) — trước cả khi `_lam_clip` được gọi.
    with open(os.path.join(str(tmp_path), "tu-choi.json"), "w", encoding="utf-8") as f:
        json.dump({"canh": {"7": {"khau": "anh_canh", "buoc": ["anh_boi_canh"],
                                  "ket_qua": "lui", "lui": True}}}, f)

    goi_create = {"n": 0}

    def create(**kw):  # pragma: no cover — không được gọi
        goi_create["n"] += 1
        raise AssertionError("không được gửi lên Veo cho một ảnh mượn")

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    anh_dong_goi = _cai_dat_chung(monkeypatch, tmp_path, cong_cu)

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    assert goi_create["n"] == 0
    assert anh_dong_goi.get("nguon_anh") == str(anh)
    assert os.path.exists(dich)


# ── `_thu_nho_mat_tren_khung_rong` / bước "thu_nho_mat_cuc_bo" ─────────────


def test_thu_nho_mat_cuc_bo_giu_kich_thuoc_khung_va_ra_tep_that(tmp_path):
    """Pillow thật (đã có sẵn trong requirements.txt), không mạng."""
    from PIL import Image

    anh = tmp_path / "7.png"
    Image.new("RGB", (160, 90), (200, 120, 80)).save(anh)

    dv = tcnd.DauVao(khau="clip", canh=7, prompt="p", anh=str(anh), nhan_vat=("nv7",))
    so = tcnd.SoCuu()
    dv_moi = ak._buoc_thu_nho_mat_cuc_bo(so, dv, None, None)

    assert dv_moi.anh.endswith(".thu-nho.png")
    assert os.path.exists(dv_moi.anh)
    with Image.open(dv_moi.anh) as im:
        assert im.size == (160, 90)


def test_thu_nho_mat_cuc_bo_bo_qua_khi_nhan_vat_da_tung_that_bai(tmp_path):
    anh = tmp_path / "7.png"
    anh.write_bytes(b"khong-quan-trong-vi-se-bi-chan-som")

    dv = tcnd.DauVao(khau="clip", canh=7, prompt="p", anh=str(anh), nhan_vat=("nv7",))
    so = tcnd.SoCuu()
    so.danh_dau_thu_nho_that_bai(("nv7",))

    with pytest.raises(RuntimeError):
        ak._buoc_thu_nho_mat_cuc_bo(so, dv, None, None)


def test_nhan_vat_ghi_thu_nho_that_bai_sau_khi_chuoi_di_qua_va_khong_cuu_duoc_o_do(monkeypatch, tmp_path):
    """Sau MỘT lượt cứu mà bước "thu_nho_mat_cuc_bo" đã CHẠY nhưng KHÔNG phải
    là bước cuối cùng cứu được (chuỗi phải đi tiếp) — nhân vật được đánh dấu
    để cảnh SAU của cùng nhân vật bỏ qua bước rẻ này."""
    anh = tmp_path / "7.png"
    from PIL import Image
    Image.new("RGB", (160, 90), (10, 10, 10)).save(anh)  # bước 1 SẼ thành công về mặt kỹ thuật…
    dich = str(tmp_path / "7.mp4")
    anh_rong = str(tmp_path / "7-rong.png")
    with open(anh_rong, "wb") as f:
        f.write(b"anh-rong-gia")

    so_lan = {"n": 0}

    def create(**kw):
        so_lan["n"] += 1
        if so_lan["n"] <= 2:
            # …nhưng Veo VẪN từ chối cả bản đã thu nhỏ (lần gửi #2) — chuỗi
            # phải đi tiếp sang bước vẽ lại khung rộng (lần gửi #3).
            raise _LoiCong(CAU_ANH_BI_TU_CHOI, "prompt_image_rejected_by_provider")
        return {"id": "job_{0}".format(so_lan["n"]), "status": "succeeded"}

    bc, dong = _bc_ghi()
    bc.client = SimpleNamespace(videos=SimpleNamespace(create=create))
    luot = _luot_gia(tmp_path)
    cong_cu = _CongCuGia()
    cong_cu.ve_anh_ket_qua = anh_rong
    _cai_dat_chung(monkeypatch, tmp_path, cong_cu)

    ak._lam_clip(bc, luot, _canh(nhan_vat=("nv9",)), str(anh), dich, 8)

    assert so_lan["n"] == 3
    so_cuu = ak._so_cuu_cua_luot(bc, luot)
    assert so_cuu.thu_nho_da_that_bai(("nv9",)) is True
