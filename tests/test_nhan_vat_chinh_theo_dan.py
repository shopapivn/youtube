"""Nhân vật chính của phim đọc theo DÀN, không theo tiền tố `nv`.

Đo 25/09/2026 (story-dien-anh-my/0001): AI đặt mã nhân vật theo tên (`laura`,
`char_daniel`). Hàm cũ chỉ đếm mã `nv*` → trả rỗng → ảnh bìa và nhân vật tách
nền của phụ đề rơi về `nv1.png` của kênh — một con mèo mascot của kênh khác,
ngồi giữa nhà hàng trên cả ba ảnh bìa.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

from core.dao_dien_auto import TEP_DAN, THU_MUC_THAM_CHIEU, nhan_vat_chinh_cua_luot


def _luot(tmp_path, dan=True):
    (tmp_path / THU_MUC_THAM_CHIEU).mkdir()
    for ten in ("laura", "mark", "emily", "loc_kitchen"):
        (tmp_path / THU_MUC_THAM_CHIEU / (ten + ".png")).write_bytes(b"png")
    canh = [{"reference_files": json.dumps(r)} for r in (
        ["laura.png", "loc_kitchen.png"], ["laura.png", "mark.png", "loc_kitchen.png"],
        ["laura.png", "emily.png", "loc_kitchen.png"], ["mark.png", "loc_kitchen.png"],
        ["loc_kitchen.png"])]
    (tmp_path / "4-canh.json").write_text(json.dumps(canh), encoding="utf-8")
    if dan:
        (tmp_path / TEP_DAN).write_text(json.dumps({
            "characters": [{"id": "laura"}, {"id": "mark"}, {"id": "emily"}],
            "locations": [{"id": "loc_kitchen"}]}), encoding="utf-8")
    return SimpleNamespace(thu_muc=str(tmp_path), ma_kenh="k", ma_luot="0001")


def _ten(ds):
    return [p.replace("\\", "/").split("/")[-1] for p in ds]


def test_ma_theo_ten_van_ra_nhan_vat_chinh(tmp_path):
    assert _ten(nhan_vat_chinh_cua_luot(_luot(tmp_path), 2)) == ["laura.png", "mark.png"]


def test_boi_canh_xuat_hien_nhieu_nhat_khong_bi_coi_la_nhan_vat(tmp_path):
    # loc_kitchen có mặt ở MỌI cảnh — nhiều hơn mọi nhân vật — mà không được chọn.
    assert "loc_kitchen.png" not in _ten(nhan_vat_chinh_cua_luot(_luot(tmp_path), 3))


def _gia_ve(monkeypatch):
    """Thay máy chủ vẽ bằng bản ghi lại lời nhắc; không gọi mạng."""
    import core.auto_khau as ak
    import core.dao_dien_auto as dda

    goi = []

    class Hop:
        def __init__(self, _bc, duong):
            self.duong = list(duong)

        def lay(self):
            return ["http://x/" + os.path.basename(p) for p in self.duong]

    monkeypatch.setattr(dda, "ThamChieuCanh", Hop)
    monkeypatch.setattr(dda, "che_do_dao_dien", lambda _k: True)
    monkeypatch.setattr(ak, "_tao_anh", lambda bc, luot, p, hop, khoa, **kw: (
        goi.append((p, hop.lay(), kw.get("ty_le"))) or {"status": "succeeded"}))
    monkeypatch.setattr(ak, "_tai_ket_qua", lambda bc, g, i, dich: open(dich, "wb").write(b"png"))
    monkeypatch.setattr(ak, "_xoa_dau", lambda bc, tep: None)
    return goi


def _bc(kieu="karaoke", prompt=None):
    return SimpleNamespace(kenh=SimpleNamespace(kieu_phu_de=kieu, prompt=prompt or {},
                                                che_do_ke="tu_xay", anh_nv=[]),
                           ghi=lambda _s: None)


def test_nguoi_ke_ve_rieng_nhan_vat_chinh_nua_than(tmp_path, monkeypatch):
    """Chủ dự án 26/09/2026: không dán ảnh tham chiếu toàn thân — vẽ riêng nhân
    vật chính nửa thân trên, đẹp, như đang kể; nền trắng để tách nền."""
    import core.auto_khau as ak

    goi = _gia_ve(monkeypatch)
    luot = _luot(tmp_path)
    dan = json.loads((tmp_path / TEP_DAN).read_text(encoding="utf-8"))
    dan["characters"][0]["english_prompt"] = "A 44-year-old woman with honey-brown hair"
    (tmp_path / TEP_DAN).write_text(json.dumps(dan), encoding="utf-8")

    ra = ak._lam_nguoi_ke(_bc(), luot)
    assert ra.endswith(ak.TEP_NGUOI_KE) and os.path.exists(ra)
    (p, tham_chieu, ty_le), = goi
    assert "honey-brown" in p and "waist-up" in p and "white" in p
    assert tham_chieu == ["http://x/laura.png"] and ty_le == "9:16"
    # Có rồi thì không vẽ lại (không tiêu tiền lần hai).
    ak._lam_nguoi_ke(_bc(), luot)
    assert len(goi) == 1


def test_nguoi_ke_dung_loi_nhac_cua_kenh(tmp_path, monkeypatch):
    import core.auto_khau as ak

    goi = _gia_ve(monkeypatch)
    ak._lam_nguoi_ke(_bc(prompt={"10-nguoi-ke.md": "KOREAN <<NHAN_VAT>> END"}), _luot(tmp_path))
    assert goi[0][0].startswith("KOREAN ") and goi[0][0].endswith(" END")


def test_kenh_khong_karaoke_thi_khong_ve(tmp_path, monkeypatch):
    import core.auto_khau as ak

    goi = _gia_ve(monkeypatch)
    assert ak._lam_nguoi_ke(_bc(kieu=""), _luot(tmp_path)) == "" and goi == []


def test_thieu_tep_dan_thi_loai_ma_boi_canh(tmp_path):
    ra = _ten(nhan_vat_chinh_cua_luot(_luot(tmp_path, dan=False), 2))
    assert ra == ["laura.png", "mark.png"]
