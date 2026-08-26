"""Đánh dấu làm lại khâu "một sản phẩm" thì kết quả cũ phải được cất đi — không thì khâu
thấy tệp còn đó là "đã có, dùng lại" và "Làm lại" thành vô nghĩa (đo 26/08/2026)."""
import os

from core.auto import CHO, XONG, dat_lam_lai, moi_luot


def _luot(tmp_path):
    luot = moi_luot(str(tmp_path), "k", "0001", {"link": "x"})
    os.makedirs(luot.thu_muc, exist_ok=True)
    for t in ("1-kich-ban.txt", "1-kich-ban-the.txt", "1-nhap-2.txt", "1-ban-A.txt", "1-cham-diem.txt", "1-seo.txt",
              "2-giong-doc.mp3", "3-phu-de.srt", "4-canh.json", "4-canh-dan.json", "8-video.mp4"):
        open(os.path.join(luot.thu_muc, t), "w").write("cu")
    os.makedirs(os.path.join(luot.thu_muc, "2-doan")); os.makedirs(os.path.join(luot.thu_muc, "5-anh"))
    open(os.path.join(luot.thu_muc, "5-anh", "1.png"), "wb").write(b"anh")
    os.makedirs(os.path.join(luot.thu_muc, "tham-chieu")); open(os.path.join(luot.thu_muc, "tham-chieu", "nv1.png"), "wb").write(b"tc")
    for m in luot.khau:
        luot.tt(m).trang_thai = XONG
    return luot


def test_lam_lai_kich_ban_cat_ca_chuoi_sau(tmp_path):
    luot = _luot(tmp_path)
    doi = dat_lam_lai(luot, "kich-ban")
    assert "kich-ban" in doi and "giong-doc" in doi and luot.tt("kich-ban").trang_thai == CHO
    d = luot.thu_muc
    for t in ("1-kich-ban.txt", "1-kich-ban-the.txt", "1-nhap-2.txt", "1-ban-A.txt", "1-cham-diem.txt", "1-seo.txt",
              "2-giong-doc.mp3", "2-doan", "3-phu-de.srt", "4-canh.json", "4-canh-dan.json", "8-video.mp4"):
        assert not os.path.exists(os.path.join(d, t)), t
    kho = os.path.join(d, "_lam-lai"); assert os.path.isdir(kho)
    lan = os.listdir(kho); assert len(lan) == 1
    assert os.path.exists(os.path.join(kho, lan[0], "1-kich-ban.txt"))
    # Ảnh và tham chiếu (đắt) không bị cất: luật của chúng là chỉ làm phần thiếu.
    assert os.path.exists(os.path.join(d, "5-anh", "1.png")) and os.path.exists(os.path.join(d, "tham-chieu", "nv1.png"))


def test_lam_lai_rieng_mot_khau(tmp_path):
    luot = _luot(tmp_path)
    assert dat_lam_lai(luot, "phu-de", ca_sau=False) == ["phu-de"]
    assert not os.path.exists(os.path.join(luot.thu_muc, "3-phu-de.srt"))
    assert os.path.exists(os.path.join(luot.thu_muc, "1-kich-ban.txt")) and os.path.exists(os.path.join(luot.thu_muc, "4-canh.json"))


def test_lam_lai_anh_khong_cat_gi(tmp_path):
    luot = _luot(tmp_path)
    dat_lam_lai(luot, "anh", ca_sau=False)
    assert os.path.exists(os.path.join(luot.thu_muc, "5-anh", "1.png"))
    assert not os.path.isdir(os.path.join(luot.thu_muc, "_lam-lai"))
