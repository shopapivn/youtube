"""Prompt Visuals → ⚙ Nâng cao: mạch chia cảnh + prompt chia cảnh sửa được.

Chủ dự án 26/08/2026: *"sau khi khách chọn phong cách, chọn all mọi thứ thì ở
nâng cao có thể chỉnh được prompt, ví dụ là mạch chia là 3-8s hay là chia kiểu
khác"* — và *"mọi thứ hơi khó và trùng lặp cũng như loạn quá"*.

Không bài nào gọi mạng, không dựng cửa sổ thật.
"""

from __future__ import annotations

import importlib.util
import os

from core.chia_canh import KHUON_MAC_DINH, MIN_GIAY_CANH, loi_nhac_chia
from core.prompt_visuals import (
    CHO_TRONG_KHUON_CHIA, NHIP_CHIA, dung_boi_canh, khuon_chia_dung_duoc,
    nhip_giay,
)

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run():
    duong = os.path.join(GOC, "tool-catalog", "prompt.workbook", "run.py")
    spec = importlib.util.spec_from_file_location("pw_run_nang_cao", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cue(i, dai=2.0):
    return {"index": i, "start": (i - 1) * dai, "end": i * dai, "text": "cau {0}".format(i)}


# ── Mạch chia cảnh ──────────────────────────────────────────────────────────

class TestNhipChia:
    def test_muc_dau_la_mac_dinh_va_khong_gui_gi(self):
        assert nhip_giay(NHIP_CHIA[0][0]) is None
        assert nhip_giay("") is None and nhip_giay("la") is None
        assert "scene_pacing" not in dung_boi_canh(nhip=NHIP_CHIA[0][0])

    def test_moi_muc_khac_deu_co_san_tran_hop_le(self):
        for ma, ten, (san, tran) in NHIP_CHIA[1:]:
            assert ten.strip() and 1.0 <= san < tran <= 8.0, ma
            assert nhip_giay(ma) == (san, tran)
            bc = dung_boi_canh(nhip=ma)
            assert bc["scene_pacing"] == {"min_sec": san, "max_sec": tran}

    def test_run_py_doc_nhip_va_kep_theo_tran_engine(self):
        run = _run()
        assert run._nhip_canh({}, "veo3") == (float(MIN_GIAY_CANH), 8.0)
        assert run._nhip_canh({"scene_pacing": {"min_sec": 5, "max_sec": 8}}, "veo3") == (5.0, 8.0)
        # Trần không vượt engine; sàn không vượt trần.
        assert run._nhip_canh({"scene_pacing": {"min_sec": 3, "max_sec": 30}}, "veo3")[1] == 8.0
        san, tran = run._nhip_canh({"scene_pacing": {"min_sec": 9, "max_sec": 5}}, "veo3")
        assert san < tran
        # Rác thì về mặc định, không ném.
        assert run._nhip_canh({"scene_pacing": {"min_sec": "x"}}, "veo3") == (float(MIN_GIAY_CANH), 8.0)
        assert run._nhip_canh("khong phai dict", "veo3") == (float(MIN_GIAY_CANH), 8.0)

    def test_loi_nhac_chia_in_dung_san_khach_chon(self):
        chu = loi_nhac_chia("a <<MIN_SEC>>-<<MAX_SEC>> b", [cue(1)], 6.0, san=4.0)
        assert "a 4-6 b" in chu
        # Mặc định y như cũ.
        assert "a 3-8 b" in loi_nhac_chia("a <<MIN_SEC>>-<<MAX_SEC>> b", [cue(1)], 8.0)


# ── Prompt chia cảnh sửa được ────────────────────────────────────────────────

class TestKhuonChia:
    def test_khuon_mac_dinh_du_cho_trong(self):
        assert khuon_chia_dung_duoc(KHUON_MAC_DINH)
        for ct in CHO_TRONG_KHUON_CHIA:
            assert ct in KHUON_MAC_DINH, ct

    def test_thieu_cho_trong_thi_khong_dung_va_khong_gui(self):
        assert not khuon_chia_dung_duoc("chia di <<SRT>>")
        assert not khuon_chia_dung_duoc("")
        assert "storyboard_template" not in dung_boi_canh(khuon_chia="chia di <<SRT>>")

    def test_giong_mac_dinh_thi_khong_gui(self):
        assert "storyboard_template" not in dung_boi_canh(khuon_chia=KHUON_MAC_DINH)
        assert "storyboard_template" not in dung_boi_canh(khuon_chia=KHUON_MAC_DINH + "\n\n")

    def test_khac_mac_dinh_va_du_cho_trong_thi_gui_nguyen_van(self):
        k = KHUON_MAC_DINH.replace("RETENTION", "GIU CHAN")
        bc = dung_boi_canh(khuon_chia=k)
        assert bc["storyboard_template"] == k

    def test_run_py_dung_dung_khuon_khach_sua(self):
        run = _run()
        k = KHUON_MAC_DINH.replace("RETENTION", "GIU CHAN")
        assert run._khuon_chia({"storyboard_template": k}) == k
        assert run._CHO_TRONG_KHUON_CHIA == CHO_TRONG_KHUON_CHIA


# ── Mẫu đã lưu mang theo Nâng cao ───────────────────────────────────────────

def test_mau_luu_ca_nhip_va_khuon_chia(tmp_path):
    from core.mau_pv import doc_mau, luu_mau

    luu_mau(str(tmp_path), "Kênh A", {"phong_cach": "auto", "nhip": "day",
                                       "khuon_chia": "x <<SRT>>"})
    m = doc_mau(str(tmp_path))[0]
    assert m["nhip"] == "day" and m["khuon_chia"] == "x <<SRT>>"


# ── Bố cục: bốn thẻ, phong cách chọn ở MỘT chỗ ─────────────────────────────

def test_tab_bon_the_va_mot_cua_chon_phong_cach():
    """Đọc mã nguồn — không dựng Qt: Bước 5 đã gộp vào Bước 4, nút lưu chỉ một."""
    with open(os.path.join(GOC, "ui_qt", "trang_prompt_visuals.py"),
              encoding="utf-8") as t:
        chu = t.read()
    assert "def _the_thu(" not in chu, "Bước 5 riêng đã gộp vào Bước 4"
    assert chu.count("nut_phu(\"💾 Lưu") == 1, "một nút Lưu duy nhất"
    assert "Bước 2 — Phong cách & nhân vật" in chu
    assert "Bước 4 — Xem, sửa prompt và thử vài cảnh thật" in chu
    # Nâng cao có đủ ba ô.
    for o in ("_o_chi_dan", "_o_nhip", "_o_khuon_chia", "_khoi_phuc_khuon_chia"):
        assert o in chu, o
    # Ô "Nhân vật" và "Dùng lại" nằm trong _the_phong_cach, không còn ở _the_nhap.
    dau = chu.index("def _the_nhap("); cuoi = chu.index("# ── Nhân vật cố định")
    assert "_o_che_do" not in chu[dau:cuoi] and "_o_kenh" not in chu[dau:cuoi]
