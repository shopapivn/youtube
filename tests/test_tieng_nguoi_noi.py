"""Clip có TIẾNG NGƯỜI NÓI thì tắt tiếng clip ấy, giữ nguyên hình.

═══ CHỦ DỰ ÁN, 28/08/2026 ═══

*"tao thấy vẫn có tiếng người đó"* … *"tiếng nói chuyện — nó bị khác ngôn ngữ
nên tao muốn tận dụng âm thanh ngoài, còn chỗ nào có âm thanh nói chuyện thì
thôi"*.

Lời nhắc đã cấm thoại (`auto_khau.LUAT_TIENG_CANH`) — cấm rồi engine vẫn thoại,
nên phải soi lại bản đã về.

Bài kiểm dựng SÓNG GIẢ chứ không cần clip thật: một sóng ồn có bao hình dập
dình 4 lần/giây là "tiếng nói", một sóng ồn phẳng là "tiếng nước". Nhờ vậy
chạy được trên máy không có FFmpeg và không có phim nào trên đĩa.
"""
from __future__ import annotations

import numpy as np

import core.auto_khau as ak
from core.tieng_canh import (NGUONG_TIENG_NGUOI, TAN_SO_DO, clip_co_nguoi_noi,
                             diem_tieng_noi)


def _on(giay=4.0, hat=1):
    """Ồn trắng — tiếng nước, tiếng gió: không có nhịp âm tiết nào."""
    r = np.random.RandomState(hat)
    return r.standard_normal(int(TAN_SO_DO * giay)).astype(np.float32) * 0.1


def _tieng_noi_gia(giay=4.0, nhip=4.0, hat=2):
    """Ồn trong dải tiếng nói, bao hình dập dình `nhip` lần mỗi giây."""
    t = np.arange(int(TAN_SO_DO * giay)) / float(TAN_SO_DO)
    r = np.random.RandomState(hat)
    song = r.standard_normal(len(t)).astype(np.float32)
    # đẩy năng lượng vào 300–3400 Hz cho giống giọng người
    n = 1 << int(np.ceil(np.log2(len(song))))
    f = np.fft.rfftfreq(n, 1.0 / TAN_SO_DO)
    X = np.fft.rfft(song, n)
    X[(f < 300) | (f > 3400)] = 0.0
    song = np.fft.irfft(X)[:len(t)]
    bao = 0.5 * (1.0 + np.sin(2.0 * np.pi * nhip * t))
    return (song * bao).astype(np.float32)


# ── 1. Phép đo phân biệt được hai loại ───────────────────────────────────────

def test_on_nen_diem_thap_tieng_noi_diem_cao():
    d_on = diem_tieng_noi(_on())
    d_noi = diem_tieng_noi(_tieng_noi_gia())
    assert d_noi > d_on * 2, (d_noi, d_on)
    assert d_on < NGUONG_TIENG_NGUOI, "tiếng nước mà bị coi là người nói"
    assert d_noi >= NGUONG_TIENG_NGUOI, "tiếng nói mà lọt qua"


def test_nhip_qua_nhanh_khong_phai_am_tiet():
    """Nhịp 12 Hz là rung, là cánh chim vỗ — không phải nhịp nói."""
    assert diem_tieng_noi(_tieng_noi_gia(nhip=12.0)) < NGUONG_TIENG_NGUOI


def test_khong_do_duoc_thi_tra_0_chu_khong_no():
    assert diem_tieng_noi(None) == 0.0
    assert diem_tieng_noi(np.zeros(10, dtype=np.float32)) == 0.0
    assert diem_tieng_noi(np.zeros(TAN_SO_DO * 2, dtype=np.float32)) == 0.0


# ── 2. Khâu dựng dùng kết quả ấy ─────────────────────────────────────────────

def test_clip_bi_ghi_ten_thi_lap_duong_im_lang(tmp_path, monkeypatch):
    """Clip có người nói → cắt bằng `anullsrc`, tức mất tiếng mà còn hình."""
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: True)
    # clip thứ hai (chỉ số 1) bị coi là có người nói
    monkeypatch.setattr("core.tieng_canh.clip_co_nguoi_noi",
                        lambda _ff, _c, **_k: {1})
    clip = []
    for i in range(2):
        p = tmp_path / ("%d.mp4" % (i + 1))
        p.write_bytes(b"MP4")
        clip.append(str(p))
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    ak._ghep_video("ffmpeg", clip, str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0, 4.0], base_dir=".", giu_tieng=True)
    mot, hai = bat[0], bat[1]
    assert "apad" in " ".join(mot), "clip sạch phải GIỮ tiếng"
    assert "anullsrc" in " ".join(hai), "clip có người nói phải bị tắt tiếng"
    assert "-an" not in hai, "vẫn phải có luồng tiếng, chỉ là im"


def test_khong_bat_co_thi_khong_do_gi_ca(tmp_path, monkeypatch):
    """Kênh không giữ tiếng thì đừng giải mã 30 clip cho tốn CPU."""
    goi = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: None)
    monkeypatch.setattr("core.tieng_canh.clip_co_nguoi_noi",
                        lambda *_a, **_k: goi.append(1) or set())
    p = tmp_path / "1.mp4"
    p.write_bytes(b"MP4")
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    ak._ghep_video("ffmpeg", [str(p)], str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0], base_dir=".", giu_tieng=False)
    assert goi == []


# ── 3. Không đo được thì nghiêng về phía TẮT ─────────────────────────────────

def test_ghi_ro_da_tat_nhung_clip_nao(tmp_path, monkeypatch):
    """Tắt tiếng lặng lẽ thì không ai kiểm được — phải ghi tên clip ra."""
    import core.tieng_canh as tc

    nhat_ky = []
    monkeypatch.setattr(tc, "doc_pcm", lambda _ff, _p: _tieng_noi_gia())
    for i in range(2):
        (tmp_path / ("%d.mp4" % (i + 1))).write_bytes(b"MP4")
    cam = clip_co_nguoi_noi("ffmpeg",
                            [str(tmp_path / "1.mp4"), str(tmp_path / "2.mp4")],
                            ghi=nhat_ky.append)
    assert cam == {0, 1}
    assert nhat_ky and "tắt tiếng 2/2" in nhat_ky[0]
    assert "hình giữ nguyên" in nhat_ky[0]


def test_clip_von_cam_thi_khong_tinh_la_co_nguoi_noi(tmp_path, monkeypatch):
    import core.tieng_canh as tc

    monkeypatch.setattr(tc, "doc_pcm", lambda _ff, _p: None)
    (tmp_path / "1.mp4").write_bytes(b"MP4")
    assert clip_co_nguoi_noi("ffmpeg", [str(tmp_path / "1.mp4")]) == set()


# ── 4. Ngưỡng riêng theo kênh ────────────────────────────────────────────────

def test_kenh_dat_duoc_nguong_rieng(tmp_path, monkeypatch):
    """Nhịp 3–6 Hz không chỉ có ở tiếng nói.

    Phiên kho-github-77 nêu ca thật 28/08/2026: kênh timelapse có tiếng chợ
    đông và tiếng người hò hét lúc cháy — cũng dồn vào 300–3400 Hz, cũng dập
    dình, nên có thể bị bắt oan. Kênh ấy nâng ngưỡng của mình lên là xong;
    ngưỡng chung 0,25 có khoảng trống đo được đỡ lưng, đừng lung lay nó.
    """
    nhan = {}
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: None)
    monkeypatch.setattr("core.tieng_canh.clip_co_nguoi_noi",
                        lambda _ff, _c, **kw: nhan.update(kw) or set())
    p = tmp_path / "1.mp4"
    p.write_bytes(b"MP4")
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    ak._ghep_video("ffmpeg", [str(p)], str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0], base_dir=".", giu_tieng=True,
                   nguong_tieng_nguoi=0.45)
    assert nhan["nguong"] == 0.45


def test_kenh_khong_dat_thi_dung_nguong_chung(tmp_path, monkeypatch):
    from core.tieng_canh import NGUONG_TIENG_NGUOI

    nhan = {}
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: None)
    monkeypatch.setattr("core.tieng_canh.clip_co_nguoi_noi",
                        lambda _ff, _c, **kw: nhan.update(kw) or set())
    p = tmp_path / "1.mp4"
    p.write_bytes(b"MP4")
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    ak._ghep_video("ffmpeg", [str(p)], str(mp3), "", str(tmp_path / "ra.mp4"),
                   giay=[4.0], base_dir=".", giu_tieng=True)
    assert nhan["nguong"] == NGUONG_TIENG_NGUOI
