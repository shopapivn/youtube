"""Nhân bản kênh mẫu → kênh riêng; cập nhật tool đè mẫu, không đụng kênh riêng.

Chủ dự án, 26/08/2026: *"các template đó tao có cập nhật nên nếu khách dùng và
tùy chỉnh thì khi update sẽ bị đè, nên tao muốn những template khách tạo sẽ
không bị đè, nên thêm tính năng đó để khách nhân bản và giữ cho mình để tùy
chỉnh"*.

Không bài nào gọi mạng, không dựng cửa sổ.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.kenh import doc_kenh, kiem_ma_kenh_moi, liet_ke_kenh, nhan_ban_kenh
from core.safe_update import apply_tai_cho

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KENH_MAU = ("TL4-T7", "story-3d", "hoathinh-3d", "story-mau-nuoc")


def _kenh(goc: Path, ma: str, *, mau=False, rieng=False, prompt="p") -> Path:
    d = goc / "CHANNEL" / ma
    (d / "prompt").mkdir(parents=True, exist_ok=True)
    (d / "nv").mkdir(exist_ok=True)
    dong = ['ma: "{0}"'.format(ma), 'ten: "Kênh {0}"'.format(ma), 'ngon_ngu: "vi"',
            'voice_id: "v"']
    if mau:
        dong.insert(0, "mau_cua_tool: true")
    if rieng:
        dong.append("kenh_rieng: true")
    (d / "kenh.yaml").write_text("\n".join(dong) + "\n", encoding="utf-8")
    (d / "style.yaml").write_text('image_style: "x"\n', encoding="utf-8")
    (d / "prompt" / "2-viet.md").write_text(prompt, encoding="utf-8")
    (d / "prompt" / "7-canh.md").write_text("c", encoding="utf-8")
    (d / "nv" / "nv1.png").write_bytes(b"\x89PNG anh")
    return d


# ── Nhân bản ────────────────────────────────────────────────────────────────

class TestNhanBan:
    def test_ban_sao_mang_du_do_va_thanh_kenh_rieng(self, tmp_path):
        goc = str(tmp_path)
        _kenh(tmp_path, "TL4-T7", mau=True, prompt="loi nhac mau")
        dich = nhan_ban_kenh(goc, "TL4-T7", "TL4-T7-rieng", "Kênh của tôi")
        assert Path(dich).is_dir()
        k = doc_kenh(goc, "TL4-T7-rieng")
        assert k.ma == "TL4-T7-rieng" and k.ten == "Kênh của tôi"
        assert k.kenh_rieng is True and k.mau_cua_tool is False
        assert k.prompt["2-viet.md"] == "loi nhac mau"
        assert (Path(dich) / "nv" / "nv1.png").read_bytes() == b"\x89PNG anh"
        assert "kenh_rieng: true" in (Path(dich) / "kenh.yaml").read_text(encoding="utf-8")
        # Mẫu gốc không suy suyển.
        assert doc_kenh(goc, "TL4-T7").mau_cua_tool is True
        assert sorted(liet_ke_kenh(goc)) == ["TL4-T7", "TL4-T7-rieng"]

    def test_khong_de_len_kenh_dang_co_va_ma_xau_bi_chan(self, tmp_path):
        goc = str(tmp_path)
        _kenh(tmp_path, "TL4-T7", mau=True)
        _kenh(tmp_path, "DA-CO")
        with pytest.raises(ValueError):
            nhan_ban_kenh(goc, "TL4-T7", "DA-CO")
        with pytest.raises(ValueError):
            nhan_ban_kenh(goc, "TL4-T7", "_nhap")
        with pytest.raises(ValueError):
            nhan_ban_kenh(goc, "KHONG-CO", "x")
        assert kiem_ma_kenh_moi(goc, "a/b")
        assert kiem_ma_kenh_moi(goc, "") and not kiem_ma_kenh_moi(goc, "OK-1")

    def test_ten_trong_thi_giu_ten_goc(self, tmp_path):
        goc = str(tmp_path)
        _kenh(tmp_path, "story-3d", mau=True)
        nhan_ban_kenh(goc, "story-3d", "co-tich-cua-toi")
        assert doc_kenh(goc, "co-tich-cua-toi").ten == "Kênh story-3d"


# ── Kênh mẫu ship kèm tool phải được đánh dấu ───────────────────────────────

@pytest.mark.parametrize("ma", KENH_MAU)
def test_kenh_mau_ship_kem_tool_co_co_mau(ma):
    k = doc_kenh(GOC, ma)
    assert k.mau_cua_tool is True and k.kenh_rieng is False, ma


def test_tao_kenh_moi_la_kenh_rieng(tmp_path):
    """`dung_kenh` (Tạo kênh mới) đánh dấu kenh_rieng — cập nhật không đụng."""
    import shutil

    from core.khuon import dung_kenh

    goc = tmp_path / "goc"
    shutil.copytree(os.path.join(GOC, "CHANNEL", "_KHUON"), str(goc / "CHANNEL" / "_KHUON"))
    dung_kenh(str(goc), "K-MOI", ma_nganh="tam-ly", ma_ve="trang-tron-nen-dao",
              ma_van_hoa="vi", voice_id="g")
    k = doc_kenh(str(goc), "K-MOI")
    assert k.kenh_rieng is True and k.mau_cua_tool is False


# ── Cập nhật: mẫu thì đè, riêng thì giữ ─────────────────────────────────────

def _dung_ban(thu_muc: Path, ban: str) -> Path:
    thu_muc.mkdir(parents=True, exist_ok=True)
    (thu_muc / "shopapi_studio_qt.py").write_text("# tool", encoding="utf-8")
    (thu_muc / "VERSION").write_text(ban + "\n", encoding="utf-8")
    for ten in ("core", "ui_qt", "tool-catalog"):
        (thu_muc / ten).mkdir(exist_ok=True)
        (thu_muc / ten / "__init__.py").write_text("", encoding="utf-8")
    (thu_muc / "tool-catalog" / "mau").mkdir(exist_ok=True)
    (thu_muc / "tool-catalog" / "mau" / "tool.json").write_text("{}", encoding="utf-8")
    return thu_muc


@pytest.fixture
def san(tmp_path):
    cai = _dung_ban(tmp_path / "ShopAPI-Studio", "2.40.0")
    moi = _dung_ban(tmp_path / "cho-dung" / "2.41.0", "2.41.0")
    return cai, moi


class TestCapNhat:
    def test_kenh_mau_khach_da_sua_BI_DE_bang_mau_moi(self, san):
        """Đúng ý chủ dự án: mẫu được cập nhật theo tool. Muốn giữ thì nhân bản."""
        cai, moi = san
        _kenh(cai, "TL4-T7", mau=True, prompt="KHACH SUA VAO MAU")
        _kenh(moi, "TL4-T7", mau=True, prompt="mau moi cua tool")
        apply_tai_cho(moi, cai)
        assert (cai / "CHANNEL" / "TL4-T7" / "prompt" / "2-viet.md").read_text(
            encoding="utf-8") == "mau moi cua tool"

    def test_kenh_rieng_KHONG_bi_dung_ke_ca_trung_ten_voi_ban_moi(self, san):
        cai, moi = san
        _kenh(cai, "TL4-T7", rieng=True, prompt="CUA TOI")
        _kenh(moi, "TL4-T7", mau=True, prompt="mau moi")
        apply_tai_cho(moi, cai)
        assert (cai / "CHANNEL" / "TL4-T7" / "prompt" / "2-viet.md").read_text(
            encoding="utf-8") == "CUA TOI"
        assert "kenh_rieng: true" in (cai / "CHANNEL" / "TL4-T7" / "kenh.yaml").read_text(
            encoding="utf-8")

    def test_kenh_nhan_ban_song_sot_qua_cap_nhat_con_mau_thi_moi(self, san):
        cai, moi = san
        _kenh(cai, "TL4-T7", mau=True, prompt="mau cu")
        nhan_ban_kenh(str(cai), "TL4-T7", "TL4-T7-rieng")
        (cai / "CHANNEL" / "TL4-T7-rieng" / "prompt" / "2-viet.md").write_text(
            "TOI SUA BAN RIENG", encoding="utf-8")
        _kenh(moi, "TL4-T7", mau=True, prompt="mau moi")
        apply_tai_cho(moi, cai)
        assert (cai / "CHANNEL" / "TL4-T7" / "prompt" / "2-viet.md").read_text(
            encoding="utf-8") == "mau moi"
        assert (cai / "CHANNEL" / "TL4-T7-rieng" / "prompt" / "2-viet.md").read_text(
            encoding="utf-8") == "TOI SUA BAN RIENG"

    def test_kenh_rieng_van_nhan_tep_moi_con_thieu(self, san):
        """Kênh riêng không bị đè, nhưng tệp bản mới THÊM (prompt mới) vẫn tới."""
        cai, moi = san
        _kenh(cai, "K", rieng=True, prompt="cua toi")
        _kenh(moi, "K", mau=True, prompt="mau")
        (moi / "CHANNEL" / "K" / "prompt" / "9-nhac.md").write_text("moi", encoding="utf-8")
        apply_tai_cho(moi, cai)
        assert (cai / "CHANNEL" / "K" / "prompt" / "9-nhac.md").exists()
        assert (cai / "CHANNEL" / "K" / "prompt" / "2-viet.md").read_text(
            encoding="utf-8") == "cua toi"

    def test_khuon_duoc_cap_nhat_nhung_bo_ve_rieng_cua_khach_giu(self, san):
        cai, moi = san
        (cai / "CHANNEL" / "_KHUON" / "ve" / "cua-toi").mkdir(parents=True)
        (cai / "CHANNEL" / "_KHUON" / "ve" / "cua-toi" / "ve.yaml").write_text("mine", encoding="utf-8")
        (cai / "CHANNEL" / "_KHUON" / "ve" / "mau").mkdir(parents=True)
        (cai / "CHANNEL" / "_KHUON" / "ve" / "mau" / "ve.yaml").write_text("cu", encoding="utf-8")
        (moi / "CHANNEL" / "_KHUON" / "ve" / "mau").mkdir(parents=True)
        (moi / "CHANNEL" / "_KHUON" / "ve" / "mau" / "ve.yaml").write_text("moi", encoding="utf-8")
        apply_tai_cho(moi, cai)
        assert (cai / "CHANNEL" / "_KHUON" / "ve" / "mau" / "ve.yaml").read_text(encoding="utf-8") == "moi"
        assert (cai / "CHANNEL" / "_KHUON" / "ve" / "cua-toi" / "ve.yaml").read_text(encoding="utf-8") == "mine"

    def test_kenh_khach_tao_truoc_khi_co_co_van_con(self, san):
        """Kênh cũ không cờ nào, bản mới không mang theo → không đụng."""
        cai, moi = san
        _kenh(cai, "KENH-CU-CUA-TOI", prompt="x")
        _kenh(moi, "TL4-T7", mau=True)
        apply_tai_cho(moi, cai)
        assert (cai / "CHANNEL" / "KENH-CU-CUA-TOI" / "prompt" / "2-viet.md").exists()
