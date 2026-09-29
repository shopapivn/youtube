"""Tiếng dài thì bộ nghe nghe TỪNG ĐOẠN, cộng bù mốc — bộ nhớ không tăng theo
độ dài. Đo 29/09/2026 (story-reup-han/0001): tiếng gốc 3 tiếng, bộ nghe chết
"mã 1" sau 33 giây, phụ đề rơi về rải ước lượng."""

from __future__ import annotations

import sys
import types

import core.phu_de as pd


class _Tu:
    def __init__(self, w, a, b):
        self.word, self.start, self.end = w, a, b


class _Muc:
    def __init__(self, w):
        self.words = [_Tu(w, 1.0, 2.0)]
        self.text = w


def _gia(monkeypatch, tmp_path, dai):
    nghe = []

    class May:
        def __init__(self, *a, **k):
            pass

        def transcribe(self, tep, **kw):
            nghe.append(tep)
            return [_Muc("tu{0}".format(len(nghe)))], None

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=May))
    monkeypatch.setattr(pd, "do_dai_tieng", lambda p: dai)
    cat = []

    def chay(args, **kw):
        cat.append(args)
        open(args[-1], "wb").write(b"wav")

    import subprocess

    monkeypatch.setattr(subprocess, "run", chay)
    import core.dung_video as dv

    monkeypatch.setattr(dv, "tim_ffmpeg", lambda *a: "ffmpeg")
    mp3 = tmp_path / "g.mp3"
    mp3.write_bytes(b"mp3")
    return str(mp3), nghe, cat


def test_tieng_dai_nghe_tung_doan_cong_bu_moc(monkeypatch, tmp_path):
    mp3, nghe, cat = _gia(monkeypatch, tmp_path, 50 * 60.0)
    ra = pd.nghe_trong_tien_trinh_nay(mp3, thu_muc_model=str(tmp_path))
    assert len(cat) == 3 and len(nghe) == 3          # 0–20, 20–40, 40–50 phút
    assert [r[1] for r in ra] == [1.0, 1201.0, 2401.0]
    assert all("-ac" in a and "16000" in a for a in cat), "mono 16 kHz cho bộ nghe"


def test_tieng_ngan_nghe_mot_luot(monkeypatch, tmp_path):
    mp3, nghe, cat = _gia(monkeypatch, tmp_path, 10 * 60.0)
    ra = pd.nghe_trong_tien_trinh_nay(mp3, thu_muc_model=str(tmp_path))
    assert cat == [] and nghe == [mp3] and ra[0][1] == 1.0
