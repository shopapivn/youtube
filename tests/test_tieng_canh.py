"""Giữ TIẾNG CẢNH của clip (bước chân, chim hót, nước, gió) khi dựng.

═══ CHỦ DỰ ÁN, 28/08/2026 ═══

*"khi edit đang tắt toàn bộ âm thanh — tao có ý tưởng những âm thanh không phải
người nói có thể giữ lại được không, kiểu nó sẽ làm cho video sinh động hơn…
tức bỏ nhạc nền của video gốc và âm thanh người nói, giữ các âm thanh phụ (ví
dụ tiếng bước chân, chim hót…)"*.

Không tách được nhạc/lời ra khỏi tiếng động **sau khi** engine đã trộn chúng.
Nên bài toán chia đôi:

* **đặt hàng đúng** — `LUAT_TIENG_CANH` ghim vào mọi lời nhắc clip, cấm nhạc
  và cấm mọi lời nói. Tool ghim, không trông vào AI nhớ: đo trên phim
  `openstory/0008` thì lời nhắc AI viết có `ambient:` ở 25/30 cảnh nhưng
  **0/30** cảnh nhắc "no music, no speech".
* **dựng đúng** — khâu cắt không được vứt tiếng (`-an`), và lần trộn cuối cho
  tiếng cảnh né giọng đọc y như nhạc nền vẫn né.

Không gọi FFmpeg thật: bắt lấy chuỗi lệnh và đọc.
"""
from __future__ import annotations

import os

import core.auto_khau as ak
from core.kenh import doc_kenh

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _dung_media(tmp_path, so=2):
    clip = []
    for i in range(so):
        p = tmp_path / ("%d.mp4" % (i + 1))
        p.write_bytes(b"MP4")
        clip.append(str(p))
    mp3 = tmp_path / "loi.mp3"
    mp3.write_bytes(b"MP3")
    return clip, str(mp3)


def _bat_lenh(tmp_path, monkeypatch, giu_tieng, co_tieng_clip=True, **kw):
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: co_tieng_clip)
    clip, mp3 = _dung_media(tmp_path)
    ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"),
                   giay=[4.0, 4.0], base_dir=".", giu_tieng=giu_tieng, **kw)
    return bat


# ── 1. Đặt hàng: cấm nhạc và cấm lời ngay trong lời nhắc clip ────────────────

def test_luat_tieng_canh_cam_ca_nhac_lan_moi_loi_noi():
    chu = ak.LUAT_TIENG_CANH.lower()
    assert "ambient and sound effects only" in chu
    for cam in ("no music", "no song", "no score",
                "no speech", "no dialogue", "no voice-over", "no singing"):
        assert cam in chu, cam
    # và kể tên thứ ĐƯỢC giữ, không chỉ toàn cấm
    for giu in ("footsteps", "water", "wind", "birds"):
        assert giu in chu, giu


def test_kenh_openstory_bat_co_va_khong_dot_phu_de():
    """Hai ô chủ dự án dặn 28/08: phụ đề để CapCut làm, tiếng cảnh thì giữ."""
    k = doc_kenh(GOC, "openstory")
    assert k.giu_tieng_canh is True
    assert k.dot_phu_de is False


def test_co_tat_thi_khong_ghim_luat_vao_loi_nhac():
    """Kênh không giữ tiếng thì đừng bắt engine làm tiếng — thừa lời dặn."""
    import types

    bc = types.SimpleNamespace(kenh=types.SimpleNamespace(giu_tieng_canh=False))
    assert ak._giu_tieng_canh(bc) is False
    bc.kenh.giu_tieng_canh = True
    assert ak._giu_tieng_canh(bc) is True
    # thiếu hẳn trường (đồ giả trong bài kiểm) cũng không được nổ
    assert ak._giu_tieng_canh(types.SimpleNamespace()) is False


# ── 2. Dựng: khâu cắt không được vứt tiếng ───────────────────────────────────

def test_cat_clip_KHONG_vut_tieng_khi_bat_co(tmp_path, monkeypatch):
    bat = _bat_lenh(tmp_path, monkeypatch, giu_tieng=True)
    cat = bat[0]
    assert "-an" not in cat, "vứt tiếng ở khâu cắt thì không còn gì để giữ"
    assert "-c:a" in cat and cat[cat.index("-c:a") + 1] == "aac"
    # `apad`: cảnh dài hơn clip thì hình được `tpad` giữ khung cuối, tiếng mà
    # không đệm là concat lệch dần.
    assert "-af" in cat and "apad" in cat[cat.index("-af") + 1]


def test_co_tat_thi_van_cat_bo_tieng_nhu_cu(tmp_path, monkeypatch):
    bat = _bat_lenh(tmp_path, monkeypatch, giu_tieng=False)
    assert "-an" in bat[0]


def test_clip_CAM_thi_lap_duong_im_lang_cho_du_bo_luong(tmp_path, monkeypatch):
    """`concat` chép thẳng luồng nên đòi mọi mảnh cùng bộ luồng.

    Một clip câm lọt vào giữa 30 mảnh có tiếng là hỏng cả video.
    """
    bat = _bat_lenh(tmp_path, monkeypatch, giu_tieng=True, co_tieng_clip=False)
    cat = bat[0]
    assert "anullsrc=channel_layout=stereo:sample_rate=48000" in cat
    assert "-an" not in cat
    assert cat.count("-map") == 2, "một luồng hình, một luồng tiếng im"


# ── 3. Trộn: tiếng cảnh né giọng đọc, và có bản rời cho CapCut ───────────────

def test_tieng_canh_ne_giong_doc(tmp_path, monkeypatch):
    bat = _bat_lenh(tmp_path, monkeypatch, giu_tieng=True)
    cuoi = bat[-1]
    assert "-filter_complex" in cuoi
    loc = cuoi[cuoi.index("-filter_complex") + 1]
    assert "sidechaincompress" in loc, "không né thì tiếng động lấn lời kể"
    assert "{0:.3f}".format(ak.AM_LUONG_TIENG_CANH) in loc
    assert "[ra]" in cuoi


def test_xuat_them_duong_tieng_ROI_cho_capcut(tmp_path, monkeypatch):
    """Bản đã trộn với giọng đọc thì không tách ra được nữa — phải xuất riêng."""
    bat = _bat_lenh(tmp_path, monkeypatch, giu_tieng=True)
    rieng = [l for l in bat if any(str(x).endswith("8-tieng-canh.m4a") for x in l)]
    assert rieng, "thiếu tệp tiếng cảnh rời"
    l = rieng[0]
    assert "-vn" in l and l[l.index("-c:a") + 1] == "copy", "đừng nén lại lần nữa"


def test_khong_bat_co_thi_khong_sinh_tep_thua(tmp_path, monkeypatch):
    bat = _bat_lenh(tmp_path, monkeypatch, giu_tieng=False)
    assert not [l for l in bat
                if any(str(x).endswith("8-tieng-canh.m4a") for x in l)]


# ── 4. Kênh KHÔNG có giọng đọc (timelapse) ───────────────────────────────────

def _bat_khong_giong(tmp_path, monkeypatch, nhac=""):
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: True)
    clip, _mp3 = _dung_media(tmp_path)
    ak._ghep_video("ffmpeg", clip, str(tmp_path / "khong-co.mp3"), "",
                   str(tmp_path / "ra.mp4"), giay=[4.0, 4.0], base_dir=".",
                   giu_tieng=True, nhac=nhac, am_luong=0.2)
    return bat


def test_khong_giong_khong_nhac_thi_tieng_canh_la_ca_duong_tieng(tmp_path, monkeypatch):
    """Kênh timelapse: không lời đọc. Trước 28/08 phim ra HOÀN TOÀN CÂM."""
    cuoi = _bat_khong_giong(tmp_path, monkeypatch)[-1]
    assert "-an" not in cuoi
    assert cuoi[cuoi.index("-map") + 1] == "0:v:0"
    assert "0:a:0" in cuoi


def test_khong_giong_MA_CO_nhac_thi_khong_duoc_nuot_mat_nhac(tmp_path, monkeypatch):
    """Thiếu nhánh này là nuốt nhạc lặng lẽ — nhánh "chỉ tiếng cảnh" map `0:a`
    và bỏ hẳn đầu vào nhạc.

    Kênh timelapse hôm nay để `nhac_nen: ""` nên chưa ai thấy; ngày chủ kênh
    thả tệp nhạc vào thì mới vỡ, và vỡ không một dòng báo.
    """
    tep_nhac = tmp_path / "nen.mp3"
    tep_nhac.write_bytes(b"MP3")
    cuoi = _bat_khong_giong(tmp_path, monkeypatch, nhac=str(tep_nhac))[-1]
    assert "-filter_complex" in cuoi
    loc = cuoi[cuoi.index("-filter_complex") + 1]
    assert "[0:a]" in loc and "[1:a]" in loc, "phải trộn CẢ HAI nguồn"
    assert "amix=inputs=2" in loc
    assert "volume=0.200" in loc, "nhạc phải hạ theo am_luong_nhac của kênh"
    assert "sidechaincompress" not in loc, "không có giọng thì không có gì để né"


# ── 5. Độ to tiếng cảnh: đổi được từ kênh, và mặc định phải NHỎ ─────────────

def test_muc_mac_dinh_du_nho_de_khong_lan_giong():
    """Đo trên phim 0008 (28/08/2026):

        giọng đọc    trung bình -14,7 dB   đỉnh -1,4 dB
        tiếng cảnh   trung bình -31,3 dB   đỉnh -1,6 dB   ← NGANG giọng đọc

    Bản đầu để 0,7 vì nhìn trung bình; chủ dự án nghe thì bảo lấn lời. Đỉnh mới
    là con số phải nhìn: tiếng nước bắn vọt lên bằng lời kể.
    """
    assert ak.AM_LUONG_TIENG_CANH <= 0.4, "to hơn mức này là lấn giọng đọc"
    assert ak.AM_LUONG_TIENG_CANH > 0.0


def test_kenh_dat_duoc_do_to_rieng(tmp_path, monkeypatch):
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: True)
    clip, mp3 = _dung_media(tmp_path)
    ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"),
                   giay=[4.0, 4.0], base_dir=".", giu_tieng=True,
                   am_luong_tieng=0.12)
    loc = bat[-1][bat[-1].index("-filter_complex") + 1]
    assert "volume=0.120" in loc
    assert "volume={0:.3f}".format(ak.AM_LUONG_TIENG_CANH) not in loc


def test_tep_tieng_canh_ROI_giu_MUC_GOC(tmp_path, monkeypatch):
    """Đưa khách bản đã hạ sẵn là lấy mất quyền chỉnh của họ ở CapCut."""
    bat = []
    monkeypatch.setattr(ak, "_chay", lambda ff, l, **_k: bat.append(list(l)))
    monkeypatch.setattr(ak, "_clip_co_tieng", lambda _ff, _p: True)
    clip, mp3 = _dung_media(tmp_path)
    ak._ghep_video("ffmpeg", clip, mp3, "", str(tmp_path / "ra.mp4"),
                   giay=[4.0, 4.0], base_dir=".", giu_tieng=True,
                   am_luong_tieng=0.12)
    [rieng] = [l for l in bat
               if any(str(x).endswith("8-tieng-canh.m4a") for x in l)]
    assert "volume" not in " ".join(rieng), "bản rời không được hạ độ to"
    assert rieng[rieng.index("-c:a") + 1] == "copy"
