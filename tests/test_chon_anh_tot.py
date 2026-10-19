"""Vẽ nhiều, AI biên tập chọn tấm tốt nhất, chưa đạt thì sửa lời nhắc (17/10/2026).

Chủ dự án: *"nhiều đoạn ảnh kinh dị… không mô tả được nội dung… tạo ra vài cái
chọn ra cái tốt nhất, nếu chưa đủ tốt thì phải chỉnh prompt"*. Không bài nào gọi
mạng: vẽ / chấm / viết lại đều là hàm giả.
"""
from __future__ import annotations

import json
import os

from PIL import Image

from core import chon_anh_tot as cat
from core.kenh import doc_kenh

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _anh(p, mau=(120, 120, 120)):
    Image.new("RGB", (64, 36), mau).save(p)
    return str(p)


def _ve_gia(tmp_path, nhat_ky):
    def ve(loi_nhac, vong, k):
        nhat_ky.append((loi_nhac, vong, k))
        return _anh(tmp_path / "v{0}-{1}.png".format(vong, k))
    return ve


def test_ve_du_so_ung_vien_va_giu_tam_diem_cao_nhat(tmp_path):
    ve_ra = []
    dau = _anh(tmp_path / "dau.png")

    def cham(ung, p):
        return {"ung_vien": ung, "diem": [5, 9, 6], "tot": 1, "loi": "", "sua": ""}

    kq = cat.chon_va_sua(_ve_gia(tmp_path, ve_ra), cham, lambda p, l, s: p,
                         loi_nhac="P", co_san=[dau], so_ung_vien=3, so_vong_sua=2)
    assert len(ve_ra) == 2, "đã có tấm đầu → vẽ thêm 2"
    assert kq.duong.endswith("v0-1.png") and kq.diem == 9
    assert len(kq.nhat_ky) == 1, "đạt ngưỡng thì không sửa lời nhắc"


def test_chua_dat_thi_sua_loi_nhac_va_so_cung_tam_cu(tmp_path):
    ve_ra = []
    lan = [0]

    def cham(ung, p):
        lan[0] += 1
        if lan[0] == 1:
            return {"ung_vien": ung, "diem": [4, 5], "tot": 1,
                    "loi": "tiny figure in an empty room", "sua": "medium shot, two people"}
        # Vòng 2: tấm giữ từ vòng 1 đứng đầu danh sách, tấm mới thắng.
        assert ung[0].endswith("v0-1.png")
        return {"ung_vien": ung, "diem": [5, 9, 6], "tot": 1, "loi": "", "sua": ""}

    viet = []
    kq = cat.chon_va_sua(_ve_gia(tmp_path, ve_ra), cham,
                         lambda p, l, s: (viet.append((l, s)) or "P2 medium shot"),
                         loi_nhac="P1", so_ung_vien=2, so_vong_sua=2)
    assert viet == [("tiny figure in an empty room", "medium shot, two people")]
    assert kq.loi_nhac == "P2 medium shot" and kq.diem == 9
    assert {v[0] for v in ve_ra} == {"P1", "P2 medium shot"}


def test_tam_cu_van_thang_thi_giu_loi_nhac_cu(tmp_path):
    lan = [0]

    def cham(ung, p):
        lan[0] += 1
        return {"ung_vien": ung, "diem": [5, 3] if lan[0] == 1 else [5, 4, 2],
                "tot": 0, "loi": "x", "sua": "y"}

    kq = cat.chon_va_sua(_ve_gia(tmp_path, []), cham, lambda p, l, s: "P2",
                         loi_nhac="P1", so_ung_vien=2, so_vong_sua=1)
    assert kq.loi_nhac == "P1", "tấm thắng vẽ từ lời nhắc cũ → giữ lời nhắc cũ"


def test_cham_hong_thi_giu_tam_dau(tmp_path):
    dau = _anh(tmp_path / "dau.png")
    kq = cat.chon_va_sua(_ve_gia(tmp_path, []), lambda u, p: None, lambda p, l, s: p,
                         loi_nhac="P", co_san=[dau], so_ung_vien=3)
    assert kq.duong == dau


def test_ve_hong_mot_ung_vien_van_cham_phan_con_lai(tmp_path):
    def ve(p, vong, k):
        return None if k == 1 else _anh(tmp_path / "x{0}.png".format(k))

    def cham(ung, p):
        assert len(ung) == 2
        return {"ung_vien": ung, "diem": [6, 8], "tot": 1, "loi": "", "sua": ""}

    kq = cat.chon_va_sua(ve, cham, lambda p, l, s: p, loi_nhac="P", so_ung_vien=3)
    assert kq.duong.endswith("x2.png")


def test_cham_ung_vien_gui_moi_anh_va_tin_diem(tmp_path, monkeypatch):
    monkeypatch.setattr(cat, "SO_LUOT_CHAM", 1)
    ung = [_anh(tmp_path / "a.png"), _anh(tmp_path / "b.png", (200, 0, 0))]
    ref = [_anh(tmp_path / "r.png")]
    gui = []

    def goi(noi_dung):
        gui.append(noi_dung)
        # AI ghi "tot_nhat": 0 nhưng chấm tấm 1 cao hơn → tin điểm.
        return json.dumps({"diem": [4, 9], "tot_nhat": 0, "loi": "", "sua": ""})

    ch = cat.cham_ung_vien(goi, ung, cau_ke="She laughs", mo_ta="two women", tham_chieu=ref,
                           kenh_style={"image_style": "flat vector cartoon",
                                       "negative_prompt": "no blood"})
    assert ch["tot"] == 1
    anh = [k for k in gui[0] if k.get("type") == "image"]
    assert len(anh) == 3, "1 tham chiếu + 2 ứng viên"
    chu = gui[0][0]["text"]
    assert "She laughs" in chu
    # Tiêu chí lấy từ CHÍNH kênh (17/10/2026: "luật cứng dễ fail").
    assert "flat vector cartoon" in chu and "no blood" in chu


def test_viet_lai_tra_rac_thi_giu_ban_cu():
    p = "Medium shot of nv1 (Image 1) laughing at the kitchen island, warm light"
    assert cat.viet_lai_loi_nhac(lambda _c: "K", p, cau_ke="x", loi="y", sua="z") == p


def test_kenh_drama_bat_ve_nhieu():
    for ma in ("story-dien-anh-my", "story-dien-anh-my-sang", "story-dien-anh-han",
               "story-reup-han"):
        k = doc_kenh(GOC, ma)
        assert k.so_ung_vien_anh >= 3 and k.so_vong_sua_anh >= 1 and k.so_ung_vien_bia >= 6, ma


def test_kenh_khong_khai_thi_tat():
    from types import SimpleNamespace  # noqa: F401
    from core.kenh import Kenh

    assert Kenh.__dataclass_fields__["so_ung_vien_anh"].default == 1


def test_chon_anh_canh_noi_vao_khau_anh(tmp_path, monkeypatch):
    monkeypatch.setattr(cat, "SO_LUOT_CHAM", 1)
    """`_chon_anh_canh`: vẽ thêm ứng viên qua `_tao_anh`, chọn tấm thắng chép vào
    ảnh cảnh, lời nhắc đã sửa ghi vào 4-canh.json, ứng viên thua dọn vào
    `_ung-vien/`, có sổ `_chon-anh.jsonl`."""
    from types import SimpleNamespace

    import core.auto_khau as ak
    import core.goi_van_ban as gvb

    d = tmp_path / "0001"
    (d / "5-anh").mkdir(parents=True)
    tep = str(d / "5-anh" / "7.png")
    _anh(tep, (10, 10, 10))
    c = {"scene_id": 7, "srt_text": "She smiles at him", "img_prompt": "P1"}
    k = SimpleNamespace(so_ung_vien_anh=3, so_vong_sua_anh=1, mo_hinh="m")
    # 19/10/2026: `_chon_anh_canh` chỉ chạy khi công tắc máy "AI chấm & chọn
    # ảnh đẹp nhất" BẬT (mặc định TẮT) — bài này kiểm đường khi đã bật.
    bc = SimpleNamespace(kenh=k, client=object(), ghi=lambda _s: None, kiem_dung=lambda: None,
                         ai_chon_anh=True)
    luot = SimpleNamespace(thu_muc=str(d), ma_kenh="k", ma_luot="0001")
    hop = SimpleNamespace(lay=lambda: [], _duong=[])
    monkeypatch.setattr(ak, "_tao_anh", lambda *a, **kw: {})
    monkeypatch.setattr(ak, "_tai_ket_qua", lambda bc_, goi, i, dich: _anh(
        dich, (50, 50, 50) if dich.endswith("uv1-0.png") else (200, 0, 0)))
    monkeypatch.setattr(ak, "_xoa_dau", lambda bc_, t: None)
    sua = []
    monkeypatch.setattr(ak, "_ghi_loi_nhac_da_sua", lambda l, so, p: sua.append((so, p)))
    lan = [0]

    def goi_van_ban(client, msgs, **kw):
        nd = msgs[0]["content"]
        if isinstance(nd, str):                    # viết lại lời nhắc
            return "P2 medium two-shot, she smiles warmly at him across the table"
        lan[0] += 1
        so_anh = sum(1 for x in nd if x.get("type") == "image")
        if lan[0] == 1:
            return json.dumps({"diem": [3, 5, 4][:so_anh], "tot_nhat": 1,
                               "loi": "eerie empty room", "sua": "closer two-shot"})
        # Vòng 2: [tấm giữ, uv1-0, uv1-1, uv1-2] → uv1-0 thắng.
        assert so_anh == 4
        return json.dumps({"diem": [5, 9, 6, 4], "tot_nhat": 1, "loi": "", "sua": ""})

    monkeypatch.setattr(gvb, "goi_van_ban", goi_van_ban)
    ak._chon_anh_canh(bc, luot, c, tep, hop)
    assert Image.open(tep).getpixel((1, 1))[:3] == (50, 50, 50), "tấm thắng vòng 2"
    assert sua == [(7, c["img_prompt"])] and c["img_prompt"].startswith("P2")
    assert not [f for f in os.listdir(d / "5-anh") if ".uv" in f]
    assert os.listdir(d / "5-anh" / "_ung-vien")
    so = [json.loads(x) for x in open(d / "5-anh" / "_chon-anh.jsonl", encoding="utf-8")]
    assert so[0]["canh"] == 7 and so[0]["diem"] == 9


def test_tieu_chi_lay_tu_kenh_va_tieu_chi_rieng_dung_dau():
    chu = cat.tieu_chi_kenh({"image_style": "photo", "tieu_chi_cham": "faces must be visible"})
    assert chu.index("faces must be visible") < chu.index("photo")
    assert "no goals" in cat.tieu_chi_kenh({})


def test_khuon_cham_khong_ghi_cung_loi_rieng_mot_the_loai():
    """Luật chung chỉ là mục tiêu; lỗi riêng một thể loại (phòng trống, quay lưng…)
    phải đến từ tiêu chí của kênh, không gõ cứng cho mọi kênh."""
    for khuon in (cat.LOI_NHAC_CHAM_CANH, cat.LOI_NHAC_CHAM_BIA):
        thap = khuon.lower()
        for cung in ("empty room", "corridor", "back of the head", "beautiful/handsome"):
            assert cung not in thap, cung


def test_cham_hai_luot_dao_thu_tu_lay_trung_binh(tmp_path):
    """Giám khảo thiên vị VỊ TRÍ đầu: lượt xuôi khen A, lượt ngược khen tấm đứng
    đầu (C). Trung bình theo TẤM thì tấm thật sự tốt (B, giữa) thắng."""
    ung = [_anh(tmp_path / "a.png"), _anh(tmp_path / "b.png"), _anh(tmp_path / "c.png")]
    lan = [0]

    def goi(_nd):
        lan[0] += 1
        return json.dumps({"diem": [10, 8, 1], "loi": "l%d" % lan[0], "sua": ""})

    ch = cat.cham_ung_vien(goi, ung, cau_ke="x", mo_ta="y")
    assert lan[0] == 2 and ch["so_luot"] == 2
    assert ch["diem"] == [5.5, 8.0, 5.5] and ch["tot"] == 1


def test_mot_luot_hong_van_dung_luot_con_lai(tmp_path):
    ung = [_anh(tmp_path / "a.png"), _anh(tmp_path / "b.png")]
    lan = [0]

    def goi(_nd):
        lan[0] += 1
        return "K" if lan[0] == 2 else json.dumps({"diem": [3, 9]})

    ch = cat.cham_ung_vien(goi, ung, cau_ke="x", mo_ta="y")
    assert ch["tot"] == 1 and ch["so_luot"] == 1
