"""Ảnh làm lại thì clip của nó phải làm lại; clip làm lại thì video cuối phải dựng lại.

Đo 25/08/2026 (story-3d/0001): 18 ảnh mèo làm lại lúc 20:05 nhưng 18 clip vẫn là bản
19:3x và video cuối vẫn là con mèo cũ — "Làm lại khâu ảnh" không làm mất hiệu lực gì cả.

═══ NHƯNG KHÔNG SO MTIME (09/09/2026) ═══

Bản trước so giờ sửa tệp. Ảnh bị ghi lại sau khi có clip (xoá dấu, làm sạch) mà hình
không đổi → sáu clip làm lại vô cớ, 3.000 ₫. Giờ so NỘI DUNG ảnh qua sổ
`_van-tay-clip-anh.json`: clip làm từ ảnh vân tay nào, ảnh giờ vân tay khác → lỗi thời.
Không có sổ thì không đoán.
"""
import os
import time
from types import SimpleNamespace

from core.auto_khau import VanTay, _bo_clip_cu_hon_anh, _dau_tep, _nguon_moi_hon_video


def _bc():
    nk = []
    return SimpleNamespace(ghi=nk.append, _nk=nk)


def _cham(p, t):
    os.utime(p, (t, t))


def _so(tmp_path):
    return VanTay(str(tmp_path / VanTay.TEN_CLIP_ANH))


def test_anh_bi_thay_tam_khac_thi_cat_clip(tmp_path):
    anh = tmp_path / "5.png"; clip = tmp_path / "5.mp4"
    anh.write_bytes(b"anh luc lam clip"); clip.write_bytes(b"c")
    so = _so(tmp_path)
    so.dat(5, _dau_tep(str(anh)))
    anh.write_bytes(b"anh khac han")                       # khách thay tấm khác
    _cham(anh, time.time() - 1000)                          # dù giờ tệp CŨ hơn clip
    bc = _bc()
    assert _bo_clip_cu_hon_anh(bc, str(clip), str(anh), so)
    assert not clip.exists() and (tmp_path / "5.mp4.cu").exists()
    assert any("làm lại clip" in d for d in bc._nk)


def test_anh_ghi_lai_nhung_noi_dung_y_cu_thi_giu(tmp_path):
    """Đúng vụ 25/08: ảnh MỚI HƠN clip theo mtime nhưng là cùng một tấm."""
    anh = tmp_path / "5.png"; clip = tmp_path / "5.mp4"
    anh.write_bytes(b"a"); clip.write_bytes(b"c")
    so = _so(tmp_path)
    so.dat(5, _dau_tep(str(anh)))
    goc = time.time()
    _cham(clip, goc - 100); _cham(anh, goc)                 # ảnh "mới hơn" clip
    assert not _bo_clip_cu_hon_anh(_bc(), str(clip), str(anh), so)
    assert clip.exists()


def test_khong_co_so_thi_khong_doan(tmp_path):
    """Lượt chạy bằng bản tool cũ: không có sổ → giữ clip, không tiêu tiền theo phỏng đoán."""
    anh = tmp_path / "5.png"; clip = tmp_path / "5.mp4"
    anh.write_bytes(b"a"); clip.write_bytes(b"c")
    goc = time.time()
    _cham(clip, goc - 100); _cham(anh, goc)
    assert not _bo_clip_cu_hon_anh(_bc(), str(clip), str(anh), _so(tmp_path))
    assert clip.exists()
    # Thiếu một trong hai thì không đụng gì.
    so = _so(tmp_path); so.dat(5, "x")
    assert not _bo_clip_cu_hon_anh(_bc(), str(tmp_path / "khong.mp4"), str(anh), so)


def test_dau_tep_theo_noi_dung():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        a = os.path.join(d, "a.png"); b = os.path.join(d, "b.png")
        open(a, "wb").write(b"xyz"); open(b, "wb").write(b"xyz")
        assert _dau_tep(a) == _dau_tep(b) and len(_dau_tep(a)) == 16
        open(b, "wb").write(b"xyw")
        assert _dau_tep(a) != _dau_tep(b)
    assert _dau_tep(os.path.join(d, "khong-co.png")) == ""


def test_video_cu_hon_clip_thi_bao_dung_lai(tmp_path):
    (tmp_path / "6-clip").mkdir()
    video = tmp_path / "8-video.mp4"; video.write_bytes(b"v")
    mp3 = tmp_path / "2-giong-doc.mp3"; mp3.write_bytes(b"m")
    c7 = tmp_path / "6-clip" / "7.mp4"; c7.write_bytes(b"c")
    goc = time.time()
    _cham(mp3, goc - 300); _cham(c7, goc - 200); _cham(video, goc - 100)
    assert _nguon_moi_hon_video(str(video), str(tmp_path / "6-clip"), str(mp3)) == ""
    _cham(c7, goc)                                          # clip 7 làm lại sau khi dựng
    assert _nguon_moi_hon_video(str(video), str(tmp_path / "6-clip"), str(mp3)) == "clip 7"
    _cham(mp3, goc + 1)
    assert _nguon_moi_hon_video(str(video), str(tmp_path / "6-clip"), str(mp3)) == "giọng đọc"


from core.auto_khau import _bo_clip_cu, _loi_ffmpeg


def test_anh_vua_lam_lai_thi_cat_clip_cu(tmp_path):
    clip = tmp_path / "9.mp4"; clip.write_bytes(b"c")
    bc = _bc()
    assert _bo_clip_cu(bc, str(clip))
    assert not clip.exists() and (tmp_path / "9.mp4.cu").exists()
    assert not _bo_clip_cu(bc, str(clip))          # không còn gì để cất


def test_loi_ffmpeg_lay_dong_loi_khong_lay_thong_ke():
    stderr = """[libx264 @ 0x1] frame I:12 Avg QP:18
[mp4 @ 0x2] Could not write header for output file #0 (incorrect codec parameters ?): Invalid argument
Error initializing output stream 0:0 --
[libx264 @ 0x1] i8c dc,h,v,p: 35% 23% 21% 21%
Conversion failed!"""
    ra = _loi_ffmpeg(stderr)
    assert "Could not write header" in ra and "Conversion failed" in ra
    assert "i8c" not in ra
    assert _loi_ffmpeg("") == ""


from types import SimpleNamespace as _NS

from core import auto_khau as _ak


def test_loai_clip_hong_cat_sang_hong(tmp_path, monkeypatch):
    d = tmp_path / "6-clip"; d.mkdir()
    for n in (1, 2, 3):
        (d / "{0}.mp4".format(n)).write_bytes(b"x")

    def run_gia(lenh, **kw):
        tep = lenh[lenh.index("-i") + 1]
        if tep.endswith("2.mp4"):
            return _NS(returncode=1, stderr="[h264 @ 0x1] Invalid NAL unit size (-5 > 9)")
        return _NS(returncode=0, stderr="")

    monkeypatch.setattr(_ak.subprocess, "run", run_gia)
    bc = _bc()
    canh = [{"scene_id": 1}, {"scene_id": 2}, {"scene_id": 3}, {"scene_id": 4}]
    assert _ak._loai_clip_hong(bc, "ffmpeg", str(d), canh) == [2]
    assert not (d / "2.mp4").exists() and (d / "2.mp4.hong").exists()
    assert (d / "1.mp4").exists() and (d / "3.mp4").exists()
    assert any("clip cảnh 2 hỏng" in x and "Invalid NAL" in x for x in bc._nk)


def test_kiem_media_giai_ma_ca_tep(tmp_path, monkeypatch):
    tep = tmp_path / "9.mp4"; tep.write_bytes(b"x")
    goi = []

    def run_gia(lenh, **kw):
        goi.append(lenh)
        return _NS(returncode=1, stderr="Error while decoding stream #0:0: Invalid data found")

    monkeypatch.setattr(_ak.subprocess, "run", run_gia)
    bc = _NS(ffmpeg="ffmpeg", ghi=lambda d: None)
    import pytest as _pt
    with _pt.raises(_ak.LoiNoiDung, match="không mở được"):
        _ak._kiem_media(bc, str(tep))
    assert not tep.exists()
    assert "-xerror" in goi[0] and "-t" not in goi[0]          # cả tệp, không chỉ 0,1 giây


def test_clip_tai_ve_hong_thi_tao_lai_khoa_moi(tmp_path, monkeypatch):
    """Tệp hỏng từ nguồn: tải lại cùng job vô ích — phải là job mới (khoá ':hong2')."""
    khoa = []

    def tao_job_gia(bc, ham, **kw):
        khoa.append(kw.get("idempotency_key", ""))
        return {"id": "job%d" % len(khoa)}

    def kiem_gia(bc, duong):
        if len(khoa) == 1:
            raise _ak.LoiNoiDung("tệp tải về không mở được: Invalid NAL")

    monkeypatch.setattr(_ak, "_tao_job", tao_job_gia)
    monkeypatch.setattr(_ak, "_cho_job", lambda bc, job, **kw: job)
    monkeypatch.setattr(_ak, "_url_anh_canh", lambda *a, **k: "https://u/anh.png")
    monkeypatch.setattr(_ak, "_tai_ket_qua", lambda bc, goi, i, dich: open(dich, "wb").write(b"v"))
    monkeypatch.setattr(_ak, "_kiem_media", kiem_gia)
    monkeypatch.setattr(_ak, "khoa_viec", lambda luot, *a: "k")
    bc = _NS(kenh=_NS(engine="veo3"), client=_NS(videos=_NS(create=None)), ghi=lambda d: None)
    luot = _NS(thu_muc=str(tmp_path), ma_luot="0001", ma_kenh="x")
    c = {"scene_id": 7, "video_prompt": "cat walks"}
    (tmp_path / "7.png").write_bytes(b"png")
    _ak._lam_clip(bc, luot, c, str(tmp_path / "7.png"), str(tmp_path / "7.mp4"), 8)
    assert khoa == ["k", "k:hong2"]


# ═══ Tiến độ khâu clip không được hiện "0/134" suốt lúc chờ một cảnh kẹt ═══


def test_dem_tien_do_cu_muoi_viec_la_ghi_du_van_nhip(tmp_path):
    """09/09/2026 (TL4-T7-v2/0001): 133 clip có sẵn báo dồn trong nửa giây, van
    nhịp 0,4 s nuốt hết, bảng đứng ở 0/134 suốt 24 phút chờ cảnh 123."""
    from core.auto_khau import BoiCanh, dem_tien_do
    from core.auto import DANG, TrangThaiKhau

    ghi = []
    bc = BoiCanh(goc=str(tmp_path), kenh=None, goi_chat=lambda *_a, **_k: "",
                 on_nhip=lambda luot: ghi.append(tt.ghi_chu["xong"]))
    tt = TrangThaiKhau(ma="clip", trang_thai=DANG)
    bao = dem_tien_do(bc, _NS(thu_muc=str(tmp_path)), tt, "clip", giu_nhip=60.0)
    for n in range(0, 134):
        bao(n, 134)                                     # 134 lượt báo trong tích tắc
    assert ghi[0] == 0 and ghi[-1] >= 130, ghi
    assert all(b - a <= 10 for a, b in zip(ghi, ghi[1:])), "không được nhảy cóc quá 10 việc"


def test_dong_tien_do_noi_ro_phan_da_co_san(tmp_path):
    from core.auto_khau import BoiCanh, _chay_song_song

    nk = []
    bc = BoiCanh(goc=str(tmp_path), kenh=None, goi_chat=lambda *_a, **_k: "",
                 on_log=nk.append)
    muc = [{"scene_id": i} for i in range(1, 21)]
    # 19 mục có sẵn, 1 mục làm mới.
    _chay_song_song(bc, muc, lambda c: (c["scene_id"], c["scene_id"] != 7), "clip",
                    mac_dinh=4)
    dong = [d for d in nk if d.strip().startswith("clip: ")]
    assert dong and all("đã có sẵn, không làm lại" in d for d in dong), nk
    assert any("(19 đã có sẵn, không làm lại)" in d for d in nk), nk
