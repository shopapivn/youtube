"""Chấm chân dung tham chiếu so với mô tả + vai (core.cham_anh.cham_chan_dung)."""
from core.cham_anh import cham_chan_dung


def test_tra_diem_va_thieu(tmp_path):
    anh = tmp_path / "nv5.png"; anh.write_bytes(b"png")
    nhan = []

    def goi(noi_dung):
        nhan.append(noi_dung)
        return '{"diem": 3, "thieu": "golden crown, royal robe"}'

    assert cham_chan_dung(goi, str(anh), "a jolly king", "the king") == (3, "golden crown, royal robe")
    chu = nhan[0][0]["text"]
    assert "the king" in chu and "a jolly king" in chu and len(nhan[0]) == 2


def test_thieu_anh_hoac_rac(tmp_path):
    assert cham_chan_dung(lambda n: "x", str(tmp_path / "khong.png"), "a", "b") == (None, "")
    anh = tmp_path / "a.png"; anh.write_bytes(b"png")
    assert cham_chan_dung(lambda n: "không phải json", str(anh), "a", "b") == (None, "")
