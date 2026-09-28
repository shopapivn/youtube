"""Google/Veo âm thầm không dựng clip cho ẢNH CẢNH có mặt người thật cận cảnh
— bài kiểm cho sự cố 28/09/2026.

Chẩn đoán đã xác minh (thí nghiệm đối chứng 28/09): cùng prompt KHÔNG kèm ảnh
thì Veo dựng xong; cùng ảnh CẮT bỏ người thì xong; bỏ hẳn khối "IDENTITY LOCK"
vẫn hỏng. API shopapi trả 422 mã `prompt_image_rejected_by_provider` khi cặp
prompt+ảnh đã hỏng ≥3 lần/3h; câu báo có cụm "Bạn KHÔNG bị trừ tiền" — CÙNG
cụm `TAM_NGHI` dùng để nhận diện trục trặc tạm.

Trước bản sửa: mã này không có trong `core/su_co._MA_CODE` → rơi vào
`TAM_NGHI` qua câu chữ → `_loi_gui_thanh_ket` đổi thành `LoiKetJob` → vòng
"KHÔNG TRẦN SỐ LẦN" trong `_lam_clip` gửi lại ĐÚNG prompt+ảnh cũ mỗi phút, vô
hạn — cho một cặp mà chính máy chủ đã nói thẳng là không bao giờ dựng được.

Bài dưới đây canh ba việc:
1. Lỗi này KHÔNG được gửi lại y nguyên (không rơi vào vòng vô hạn).
2. `_lam_clip` rẽ sang vẽ lại ảnh khung rộng hơn rồi thử clip lại một lần.
3. Vẽ lại + thử lại vẫn hỏng thì thay bằng ảnh động (`_anh_thanh_clip`), viết
   thẳng ra `dich`, và ghi lại đúng câu "Google không dựng được... ảnh động".

Không gọi mạng, không cần ffmpeg/PIL thật — mọi hàm chạm tới máy đều bị giả.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import core.auto_khau as ak


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


def _bc_ghi():
    """BoiCanh giả — chỉ giữ nhật ký để bài kiểm đọc lại được."""
    dong = []
    return SimpleNamespace(on_log=None, ngu=lambda _g: None,
                           ghi=lambda s: dong.append(s),
                           kiem_dung=lambda: None, ffmpeg="ffmpeg-gia",
                           kenh=SimpleNamespace(engine="veo3")), dong


def _luot_gia(tmp_path):
    return SimpleNamespace(ma_kenh="k", ma_luot="0001", thu_muc=str(tmp_path))


def _canh():
    return {"scene_id": 7, "img_prompt": "a lonely man", "video_prompt": "p"}


# ── `_lam_clip` không gửi lại y nguyên, rẽ sang cứu cảnh ────────────────────


def test_loi_ma_moi_khong_lap_lai_gui_ma_re_sang_cuu_canh(monkeypatch, tmp_path):
    """`videos.create` hỏng NGAY LẦN ĐẦU với mã mới — `_lam_clip` phải rẽ sang
    cứu cảnh chứ không lặp vô hạn, và chỉ gọi `create` đúng MỘT lần."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png")
    dich = str(tmp_path / "7.mp4")

    so_lan_goi = {"n": 0}

    def create_hong(**_kw):
        so_lan_goi["n"] += 1
        raise _LoiCong(CAU_ANH_BI_TU_CHOI, "prompt_image_rejected_by_provider")

    client = SimpleNamespace(videos=SimpleNamespace(create=create_hong))
    bc, dong = _bc_ghi()
    bc.client = client
    luot = _luot_gia(tmp_path)

    monkeypatch.setattr(ak, "_url_anh_canh", lambda *a, **k: "http://anh/7.png")
    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))

    goi_cuu_canh = {}

    def cuu_canh_gia(bc, luot, c, anh, dich, giay, so_canh, so, goi_clip):
        goi_cuu_canh["duoc_goi"] = True
        with open(dich, "wb") as f:
            f.write(b"mp4-gia")

    monkeypatch.setattr(ak, "_cuu_canh_bi_google_tu_choi", cuu_canh_gia)

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    assert so_lan_goi["n"] == 1, "gửi lại y nguyên là đúng cái bẫy đã đo được"
    assert goi_cuu_canh.get("duoc_goi"), "phải rẽ sang cứu cảnh, không tự nuốt lỗi"


def test_engine_unavailable_hai_lan_lien_tiep_cung_re_sang_cuu_canh(monkeypatch, tmp_path):
    """Không có mã `prompt_image_rejected_by_provider` — nhưng job hỏng
    `engine_unavailable` (render timeout) HAI LẦN LIÊN TIẾP cho ĐÚNG cảnh này
    cũng là dấu hiệu Google không dựng nổi, không phải xui một lần."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png")
    dich = str(tmp_path / "7.mp4")

    so_lan_goi = {"n": 0}

    def create_ok(**kw):
        so_lan_goi["n"] += 1
        return {"id": "job_{0}".format(so_lan_goi["n"]), "status": "queued"}

    client = SimpleNamespace(videos=SimpleNamespace(create=create_ok))
    bc, dong = _bc_ghi()
    bc.client = client
    luot = _luot_gia(tmp_path)

    monkeypatch.setattr(ak, "_url_anh_canh", lambda *a, **k: "http://anh/7.png")
    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)

    # Mọi job đều "hỏng, đã hoàn tiền" với code=engine_unavailable — đúng
    # đường `_ket_job` raise `LoiKetJob(..., ma_loi="engine_unavailable")`.
    def cho_hong(*_a, **_k):
        raise ak.LoiKetJob("máy chủ báo job hỏng (đã hoàn tiền): x",
                           "engine_unavailable")

    monkeypatch.setattr(ak, "_cho_theo_tien_do", cho_hong)

    goi_cuu_canh = {"n": 0}

    def cuu_canh_gia(bc, luot, c, anh, dich, giay, so_canh, so, goi_clip):
        goi_cuu_canh["n"] += 1
        with open(dich, "wb") as f:
            f.write(b"mp4-gia")

    monkeypatch.setattr(ak, "_cuu_canh_bi_google_tu_choi", cuu_canh_gia)

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    # Lần 1 (goi_clip(url_anh)) + lần 2 trong vòng đặt lại = 2 lần liên tiếp.
    assert so_lan_goi["n"] == 2, "phải rẽ sang cứu cảnh ngay sau lần liên tiếp thứ hai"
    assert goi_cuu_canh["n"] == 1


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

    client = SimpleNamespace(videos=SimpleNamespace(create=create_ok))
    bc, dong = _bc_ghi()
    bc.client = client
    luot = _luot_gia(tmp_path)

    monkeypatch.setattr(ak, "_url_anh_canh", lambda *a, **k: "http://anh/7.png")
    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_tai_ket_qua", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_kiem_media", lambda *a, **k: None)

    lan = {"n": 0}

    def cho_theo_tien_do(bc, job, *a, **k):
        lan["n"] += 1
        if lan["n"] == 1:
            raise ak.LoiKetJob("máy chủ báo job hỏng (đã hoàn tiền): x",
                               "engine_unavailable")
        return {"id": job["id"], "status": "succeeded"}

    monkeypatch.setattr(ak, "_cho_theo_tien_do", cho_theo_tien_do)

    goi_cuu_canh = {"n": 0}
    monkeypatch.setattr(ak, "_cuu_canh_bi_google_tu_choi",
                        lambda *a, **k: goi_cuu_canh.__setitem__("n", goi_cuu_canh["n"] + 1))

    ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8)

    assert goi_cuu_canh["n"] == 0, "một lần xui thì vẫn phải cho đặt lại bằng khoá mới"
    assert so_lan_goi["n"] == 2, "đặt lại đúng một lần rồi xong"


def test_clip_som_khau_anh_khong_cuu_canh_du_hong_ma_moi(monkeypatch, tmp_path):
    """`gui_lai_mai=False` là lần clip SỚM, bắn kèm trong khâu ảnh — cố ý bỏ
    cuộc nhanh (tối đa hai lần) rồi để khâu clip CHÍNH THỨC làm lại sau.

    Sự cố đo được (`test_day_chuyen.py::test_clip_hong_khong_lam_hong_khau_anh`,
    kho-github có sẵn): rẽ sang cứu cảnh ở CẢ lần gọi sớm này làm khâu ảnh vẽ
    thêm ảnh "khung rộng" cho MỌI cảnh clip hỏng — tốn tiền oan (vẽ hai lần:
    một ở đây, một nữa khi khâu clip chính thức gặp lại đúng lỗi) và làm khâu
    ảnh có NHIỀU tệp hơn số ảnh thật (bài kiểm kia đếm đúng `len(canh)` tệp
    trong `5-anh`). Phải KHÔNG cứu ở đây — cứ hỏng và trả lại như cũ, để khâu
    clip chính thức (gọi lại với `gui_lai_mai=True`) mới là nơi cứu cảnh."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png")
    dich = str(tmp_path / "7.mp4")

    def create_hong(**_kw):
        raise _LoiCong(CAU_ANH_BI_TU_CHOI, "prompt_image_rejected_by_provider")

    client = SimpleNamespace(videos=SimpleNamespace(create=create_hong))
    bc, _dong = _bc_ghi()
    bc.client = client
    luot = _luot_gia(tmp_path)

    monkeypatch.setattr(ak, "_url_anh_canh", lambda *a, **k: "http://anh/7.png")
    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))

    def cuu_canh_khong_duoc_goi(*_a, **_k):  # pragma: no cover
        raise AssertionError("lần clip sớm không được rẽ sang cứu cảnh")

    monkeypatch.setattr(ak, "_cuu_canh_bi_google_tu_choi", cuu_canh_khong_duoc_goi)

    with pytest.raises(Exception):
        ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8, gui_lai_mai=False)

    assert not __import__("os").path.exists(str(anh) + ".khung-rong.png"), \
        "không được vẽ thêm ảnh khung rộng ở lần clip sớm"


def test_clip_som_khau_anh_khong_cuu_canh_du_engine_unavailable_hai_lan(monkeypatch, tmp_path):
    """Cùng luật như trên, cho nhánh `engine_unavailable` hai lần liên tiếp."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png")
    dich = str(tmp_path / "7.mp4")

    def create_ok(**kw):
        return {"id": "job_x", "status": "queued"}

    client = SimpleNamespace(videos=SimpleNamespace(create=create_ok))
    bc, _dong = _bc_ghi()
    bc.client = client
    luot = _luot_gia(tmp_path)

    monkeypatch.setattr(ak, "_url_anh_canh", lambda *a, **k: "http://anh/7.png")
    monkeypatch.setattr(ak, "_tao_job", lambda bc, ham, **kw: ham(**kw))
    monkeypatch.setattr(ak, "_ngu_ngat", lambda *a, **k: None)

    def cho_hong(*_a, **_k):
        raise ak.LoiKetJob("máy chủ báo job hỏng (đã hoàn tiền): x",
                           "engine_unavailable")

    monkeypatch.setattr(ak, "_cho_theo_tien_do", cho_hong)

    def cuu_canh_khong_duoc_goi(*_a, **_k):  # pragma: no cover
        raise AssertionError("lần clip sớm không được rẽ sang cứu cảnh")

    monkeypatch.setattr(ak, "_cuu_canh_bi_google_tu_choi", cuu_canh_khong_duoc_goi)

    with pytest.raises(ak.LoiKetJob):
        ak._lam_clip(bc, luot, _canh(), str(anh), dich, 8, gui_lai_mai=False)


# ── `_cuu_canh_bi_google_tu_choi`: vẽ lại khung rộng, rồi ảnh động ──────────


def test_ve_lai_khung_rong_thanh_cong_thi_dung_ban_ay(monkeypatch, tmp_path):
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png-goc")
    dich = str(tmp_path / "7.mp4")

    bc, dong = _bc_ghi()
    luot = _luot_gia(tmp_path)
    c = _canh()

    monkeypatch.setattr(ak, "_hop_cho_canh", lambda bc, luot, c, hop: hop)
    monkeypatch.setattr(ak, "khoa_viec", lambda *a, **k: "khoa-gia")
    monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: {"id": "job_anh"})
    monkeypatch.setattr(ak, "_xoa_dau", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_url_anh_canh", lambda *a, **k: "http://anh/7-rong.png")
    monkeypatch.setattr(ak, "_kiem_media", lambda *a, **k: None)

    duong_tai = {}

    def tai_ket_qua_gia(bc, goi, _idx, duong):
        duong_tai[goi.get("id")] = duong
        with open(duong, "wb") as f:
            f.write("noi-dung-{0}".format(goi.get("id")).encode("utf-8"))

    monkeypatch.setattr(ak, "_tai_ket_qua", tai_ket_qua_gia)

    goi_clip_lan = {"n": 0}

    def goi_clip(dia_chi, hau_to=""):
        goi_clip_lan["n"] += 1
        assert hau_to == ":khungrong"
        assert dia_chi == "http://anh/7-rong.png"
        return {"id": "job_clip"}

    ak._cuu_canh_bi_google_tu_choi(bc, luot, c, str(anh), dich, 8, 7, None, goi_clip)

    assert goi_clip_lan["n"] == 1, "chỉ thử clip lại đúng MỘT lần với ảnh khung rộng"
    assert duong_tai.get("job_clip") == dich
    assert any("khung rộng" in d for d in dong)


def test_ve_lai_van_hong_thi_thay_bang_anh_dong(monkeypatch, tmp_path):
    """Vẽ lại + thử clip lại cũng hỏng — phải rơi xuống ảnh động, ghi thẳng ra
    `dich`, và nói RÕ vì sao (câu chủ dự án cần đọc được, không chỉ mã lỗi)."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png-goc")
    dich = str(tmp_path / "7.mp4")

    bc, dong = _bc_ghi()
    luot = _luot_gia(tmp_path)
    c = _canh()

    monkeypatch.setattr(ak, "_hop_cho_canh", lambda bc, luot, c, hop: hop)
    monkeypatch.setattr(ak, "khoa_viec", lambda *a, **k: "khoa-gia")
    monkeypatch.setattr(ak, "_tao_anh", lambda *a, **k: {"id": "job_anh"})
    monkeypatch.setattr(ak, "_xoa_dau", lambda *a, **k: None)
    monkeypatch.setattr(ak, "_url_anh_canh", lambda *a, **k: "http://anh/7-rong.png")

    def tai_ket_qua_ghi_thuc(bc, goi, _idx, duong):
        # Bước vẽ ảnh khung rộng THÀNH CÔNG (khác test dưới) — chỉ CLIP mới
        # hỏng. Phải thật sự có tệp trên đĩa để `os.path.exists` sau đó đọc
        # đúng, giống hành vi `_tai_ket_qua` thật.
        with open(duong, "wb") as f:
            f.write(b"anh-khung-rong")

    monkeypatch.setattr(ak, "_tai_ket_qua", tai_ket_qua_ghi_thuc)

    def goi_clip(dia_chi, hau_to=""):
        raise RuntimeError("vẫn bị Google từ chối")

    anh_dong_goi = {}

    def anh_dong_gia(bc, luot, c, nguon_anh, dich_, giay, so_canh):
        anh_dong_goi["nguon_anh"] = nguon_anh
        anh_dong_goi["dich"] = dich_
        with open(dich_, "wb") as f:
            f.write(b"clip-dong-gia")

    monkeypatch.setattr(ak, "_dung_anh_dong_thay_clip", anh_dong_gia)

    ak._cuu_canh_bi_google_tu_choi(bc, luot, c, str(anh), dich, 8, 7, None, goi_clip)

    assert anh_dong_goi["dich"] == dich
    # Ảnh khung rộng đã vẽ được (dù clip lại vẫn hỏng) — dùng bản đó, không
    # phải bản gốc, vì nó an toàn hơn cho khung động.
    assert anh_dong_goi["nguon_anh"] == str(anh) + ".khung-rong.png"
    assert any("Google không dựng được ảnh có mặt người thật" in d and
               "ảnh động" in d for d in dong), \
        "câu báo phải đúng như chủ dự án cần đọc, không phải câu kỹ thuật"


def test_ve_lai_anh_cung_hong_thi_dung_anh_goc_cho_anh_dong(monkeypatch, tmp_path):
    """Vẽ lại ảnh khung rộng THẤT BẠI ngay từ bước vẽ (không chỉ bước clip) —
    ảnh động phải rơi về dùng ẢNH GỐC, không phải một tệp không tồn tại."""
    anh = tmp_path / "7.png"
    anh.write_bytes(b"png-goc")
    dich = str(tmp_path / "7.mp4")

    bc, dong = _bc_ghi()
    luot = _luot_gia(tmp_path)
    c = _canh()

    monkeypatch.setattr(ak, "_hop_cho_canh", lambda bc, luot, c, hop: hop)
    monkeypatch.setattr(ak, "khoa_viec", lambda *a, **k: "khoa-gia")

    def tao_anh_hong(*_a, **_k):
        raise RuntimeError("vẽ lại cũng bị chặn")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_hong)

    anh_dong_goi = {}

    def anh_dong_gia(bc, luot, c, nguon_anh, dich_, giay, so_canh):
        anh_dong_goi["nguon_anh"] = nguon_anh
        with open(dich_, "wb") as f:
            f.write(b"clip-dong-gia")

    monkeypatch.setattr(ak, "_dung_anh_dong_thay_clip", anh_dong_gia)

    def goi_clip(dia_chi, hau_to=""):  # pragma: no cover — không nên được gọi
        raise AssertionError("không được thử clip khi chưa có ảnh khung rộng")

    ak._cuu_canh_bi_google_tu_choi(bc, luot, c, str(anh), dich, 8, 7, None, goi_clip)

    assert anh_dong_goi["nguon_anh"] == str(anh), "vẽ lại hỏng thì dùng ảnh gốc"


# ── `_dung_anh_dong_thay_clip`: dùng đúng `_anh_thanh_clip` đã có ───────────


def test_dung_anh_dong_goi_dung_anh_thanh_clip_va_ghi_ra_dich(monkeypatch, tmp_path):
    import shutil

    anh = tmp_path / "7.png"
    anh.write_bytes(b"png")
    dich = str(tmp_path / "6-clip" / "7.mp4")

    bc, _dong = _bc_ghi()
    luot = _luot_gia(tmp_path)
    c = _canh()

    clip_dong = tmp_path / "6-clip-anh" / "7-zoom_in-8000ms-1920x1080.mp4"
    clip_dong.parent.mkdir(parents=True, exist_ok=True)
    clip_dong.write_bytes(b"clip-dong-thuc")

    goi_ghi = {}

    def anh_thanh_clip_gia(bc, ffmpeg, d, canh, manh, giay, them, chon):
        goi_ghi["canh"] = canh
        goi_ghi["manh"] = manh
        goi_ghi["giay"] = giay
        return [str(clip_dong)], (1920, 1080, 30.0)

    monkeypatch.setattr(ak, "_anh_thanh_clip", anh_thanh_clip_gia)

    ak._dung_anh_dong_thay_clip(bc, luot, c, str(anh), dich, 8, 7)

    assert goi_ghi["canh"] == [c]
    assert goi_ghi["manh"] == [str(anh)]
    assert goi_ghi["giay"] == [8]
    assert __import__("os").path.exists(dich)
    with open(dich, "rb") as f:
        assert f.read() == b"clip-dong-thuc"
