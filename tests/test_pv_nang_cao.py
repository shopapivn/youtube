"""Prompt Visuals → ⚙ Nâng cao: prompt chia cảnh sửa được, mạch chia NẰM TRONG prompt.

Chủ dự án 26/08/2026: *"sau khi khách chọn phong cách, chọn all mọi thứ thì ở
nâng cao có thể chỉnh được prompt"* — rồi bác ô chọn mạch: *"không đúng, mạch
chia cảnh tao không muốn chọn thế mà tao muốn là khống chế ở prompt gốc để khách
xem được và có thể tối ưu, ví dụ họ muốn 30s 1 cảnh thì họ tự tối ưu được"*.

Không bài nào gọi mạng, không dựng cửa sổ thật.
"""

from __future__ import annotations

import importlib.util
import os

from core.chia_canh import (
    KHUON_MAC_DINH, MIN_GIAY_CANH, canh_lai, loi_nhac_chia, nhip_tu_khuon,
)
from core.prompt_visuals import (
    CHO_TRONG_KHUON_CHIA, dung_boi_canh, khuon_chia_dung_duoc,
)

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BA_NOI = (os.path.join("_KHUON", "nganh", "tam-ly"), "TL4-T7", "_MAU-GON")


def _run():
    duong = os.path.join(GOC, "tool-catalog", "prompt.workbook", "run.py")
    spec = importlib.util.spec_from_file_location("pw_run_nang_cao", duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cue(i, dai=2.0):
    return {"index": i, "start": (i - 1) * dai, "end": i * dai, "text": "cau {0}".format(i)}


def _doi_max(khuon, so):
    return khuon.replace("MAX_SECONDS_PER_SCENE: 8", "MAX_SECONDS_PER_SCENE: {0}".format(so))


# ── Mạch chia là hai con số trong prompt ────────────────────────────────────

class TestNhipTrongPrompt:
    def test_khuon_mac_dinh_co_khoi_PACING_va_doc_ra_3_8(self):
        assert "MIN_SECONDS_PER_SCENE: 3" in KHUON_MAC_DINH
        assert "MAX_SECONDS_PER_SCENE: 8" in KHUON_MAC_DINH
        assert nhip_tu_khuon(KHUON_MAC_DINH) == (3.0, 8.0)

    def test_khach_sua_so_la_doi_mach(self):
        assert nhip_tu_khuon(_doi_max(KHUON_MAC_DINH, 30)) == (3.0, 30.0)
        assert nhip_tu_khuon("MIN_SECONDS_PER_SCENE: 2,5\nMAX_SECONDS_PER_SCENE: 5") == (2.5, 5.0)

    def test_so_vo_ly_hay_thieu_thi_None(self):
        assert nhip_tu_khuon("khong co gi") is None
        assert nhip_tu_khuon("MIN_SECONDS_PER_SCENE: 8\nMAX_SECONDS_PER_SCENE: 3") is None
        assert nhip_tu_khuon("MIN_SECONDS_PER_SCENE: 0\nMAX_SECONDS_PER_SCENE: 3") is None
        assert nhip_tu_khuon("MIN_SECONDS_PER_SCENE: 3") is None

    def test_khong_con_khoa_scene_pacing_hay_o_chon(self):
        import core.prompt_visuals as pv
        assert not hasattr(pv, "NHIP_CHIA") and not hasattr(pv, "nhip_giay")
        assert "scene_pacing" not in dung_boi_canh(khuon_chia=_doi_max(KHUON_MAC_DINH, 30))
        with open(os.path.join(GOC, "ui_qt", "trang_prompt_visuals.py"), encoding="utf-8") as t:
            assert "_o_nhip" not in t.read()

    def test_loi_nhac_dien_dung_san_tran_va_clip(self):
        chu = loi_nhac_chia("a <<MIN_SEC>>-<<MAX_SEC>> clip <<CLIP_SEC>> b",
                            [cue(1)], 30.0, san=3.0, clip=8.0)
        assert "a 3-30 clip 8 b" in chu
        # Mặc định y như cũ: clip = trần.
        assert "a 3-8 clip 8 b" in loi_nhac_chia("a <<MIN_SEC>>-<<MAX_SEC>> clip <<CLIP_SEC>> b",
                                                 [cue(1)], 8.0)

    def test_run_py_doc_nhip_tu_khuon_trong_context(self):
        run = _run()
        assert run._nhip_canh({}, "veo3") == (float(MIN_GIAY_CANH), 8.0)
        k30 = _doi_max(KHUON_MAC_DINH, 30)
        assert run._nhip_canh({"storyboard_template": k30}, "veo3") == (3.0, 30.0)
        # Khuôn thiếu chỗ trống thì run.py về khuôn mặc định → 3–8.
        assert run._nhip_canh({"storyboard_template": "MIN_SECONDS_PER_SCENE: 1\n"
                                                      "MAX_SECONDS_PER_SCENE: 40"}, "veo3") == (3.0, 8.0)

    def test_tran_mot_y_30s_van_cat_theo_clip_engine_moi_phan_mot_hinh(self):
        """30 giây một ý → AI trả một cảnh 30 s → tool cắt thành 4 phần ≤ 8 s,
        mỗi phần một prompt ảnh khác góc máy (không phải bốn lần một tấm)."""
        cues = [cue(i, dai=3.0) for i in range(1, 11)]     # 30 s
        ds = canh_lai([{"srt_from": 1, "srt_to": 10, "img_prompt": "A", "video_prompt": "B"}],
                      cues, 8.0)
        assert len(ds) == 4
        assert all(c["_ket_thuc"] - c["_bat_dau"] <= 8.0 + 1e-9 for c in ds)
        assert len({c["img_prompt"] for c in ds}) == 4


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
        k = _doi_max(KHUON_MAC_DINH, 30)
        assert dung_boi_canh(khuon_chia=k)["storyboard_template"] == k

    def test_run_py_dung_dung_khuon_khach_sua(self):
        run = _run()
        k = KHUON_MAC_DINH.replace("RETENTION", "GIU CHAN")
        assert run._khuon_chia({"storyboard_template": k}) == k
        assert run._CHO_TRONG_KHUON_CHIA == CHO_TRONG_KHUON_CHIA


# ── Kênh tab Tự động: 7-canh.md cũng mang hai con số ─────────────────────────

def test_7_canh_cua_kenh_co_khoi_PACING_ba_noi():
    for kenh in BA_NOI:
        with open(os.path.join(GOC, "CHANNEL", kenh, "prompt", "7-canh.md"),
                  encoding="utf-8") as t:
            chu = t.read()
        assert nhip_tu_khuon(chu) == (3.0, 8.0), kenh
        assert "<<CLIP_SEC>>" in chu and "<<MAX_SEC>>" in chu and "<<MIN_SEC>>" in chu


# ── Mẫu đã lưu mang theo prompt chia cảnh ───────────────────────────────────

def test_mau_luu_khuon_chia(tmp_path):
    from core.mau_pv import doc_mau, luu_mau

    luu_mau(str(tmp_path), "Kênh A", {"phong_cach": "auto", "khuon_chia": "x <<SRT>>"})
    assert doc_mau(str(tmp_path))[0]["khuon_chia"] == "x <<SRT>>"


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
    for o in ("_o_chi_dan", "_o_khuon_chia", "_khoi_phuc_khuon_chia"):
        assert o in chu, o
    # Ô "Nhân vật" và "Dùng lại" nằm trong _the_phong_cach, không còn ở _the_nhap.
    dau = chu.index("def _the_nhap("); cuoi = chu.index("# ── Nhân vật cố định")
    assert "_o_che_do" not in chu[dau:cuoi] and "_o_kenh" not in chu[dau:cuoi]
