"""Gói G8, phần A — ba chỗ khâu ẢNH mà gói G4 để lại chưa nối vào bộ xử lý
"nội dung bị từ chối" dùng chung (`core/tu_choi_noi_dung.py`).

docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md, mục 2.5 (bảng "Khung cuối" / "Ảnh
bìa") — `_anh_khung_cuoi`, `_lam_nguoi_ke`, `_lam_bia_hai_lop` gọi thẳng
`_tao_anh` không qua `tcnd`, nên bị chặn nội dung thì vòng gửi lại không trần
của `_tao_anh` quay mãi với đúng ảnh/lời nhắc đã biết không qua được.

Ba điều bắt buộc theo đề bài (mỗi chỗ một đường lùi hợp lý):

1. Khung cuối bị chặn lặp lại, đã thử hết cách sửa lời nhắc → THOÁT VÒNG,
   LÙI đúng: bỏ khung cuối (clip chỉ ghim khung đầu) — không ném lỗi.
2. Ảnh người kể bị chặn lặp lại → THOÁT VÒNG, LÙI đúng: bỏ qua (khâu dựng
   dùng ảnh tham chiếu nhân vật) — không ném lỗi.
3. Nền bìa hai lớp bị chặn lặp lại → THOÁT VÒNG, LÙI đúng: bỏ qua như bìa
   thường (không tạo `nen`/`tep`) — không chặn khâu ảnh.

Đối chứng: lỗi HẠ TẦNG thật ở khung cuối/người kể vẫn rơi về đúng dòng báo cũ
("ghim một đầu" / bỏ qua) — hành vi gốc trước G8 vẫn còn; ở bìa hai lớp thì
lỗi hạ tầng vẫn phải NÉM LÊN như `_lam_bia`/`_lam_anh_canh` (chỉ nội dung mới
được nuốt êm).

Không gọi mạng. `_tao_anh` bị monkeypatch bằng hàm giả.
"""
from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

import core.auto_khau as ak


@pytest.fixture(autouse=True)
def don_so_cuu_theo_luot():
    """`_so_cuu_cua_luot` cache một `SoCuu` theo `luot.thu_muc` — dọn giữa các
    bài kiểm để không rò trạng thái (cùng nếp `test_g4_anh_bi_tu_choi.py`)."""
    ak._SO_CUU_THEO_LUOT.clear()
    yield
    ak._SO_CUU_THEO_LUOT.clear()


def _bc_ghi(goi_chat=None, **kenh_them):
    dong = []
    mac_dinh = dict(mo_hinh="claude-sonnet-5", che_do_ke="", anh_nv=[],
                    engine="veo3", style={}, kieu_phu_de="", kieu_bia="")
    mac_dinh.update(kenh_them)
    kenh = SimpleNamespace(**mac_dinh)
    return SimpleNamespace(kenh=kenh, ghi=lambda s: dong.append(s), _nhat_ky=dong,
                           goi_chat=(goi_chat or (lambda l, **k: "")),
                           kiem_dung=lambda: None, ngu=lambda _g: None,
                           on_log=None, ffmpeg="ffmpeg-gia",
                           client=object()), dong


def _luot_gia(tmp_path, tong_so_canh=20):
    """`tong_so_canh` phải khớp `4-canh.json` — trần theo lượt (mục 2.6 tài
    liệu) tính theo TỈ LỆ số cảnh."""
    with open(os.path.join(str(tmp_path), "4-canh.json"), "w", encoding="utf-8") as f:
        json.dump([{"scene_id": i} for i in range(1, tong_so_canh + 1)], f)
    return SimpleNamespace(ma_kenh="k", ma_luot="0001", thu_muc=str(tmp_path))


class _HopRong:
    def lay(self):
        return []

    def lam_moi(self, cu):
        return []


class _ThamChieuGia:
    """Thay `ak.ThamChieu` thật (`.lay()` gọi `anh_len.tai_len` — mạng) bằng
    hộp trống, để `_lam_nguoi_ke` không cần mạng khi kênh KHÔNG đi đường đạo
    diễn (`che_do_ke=""`)."""

    def __init__(self, bc):
        pass

    def lay(self):
        return []

    def lam_moi(self, cu):
        return []


# ═══ 1) khung cuối bị chặn lặp lại → THOÁT VÒNG, LÙI bỏ khung cuối ═════════


def test_khung_cuoi_bi_chan_lap_lai_thi_lui_ghim_mot_dau(tmp_path, monkeypatch):
    c = {"scene_id": 5, "img_prompt": "a soldier keeping the gate. Style: 3D"}
    luot = _luot_gia(tmp_path)
    anh_dau = str(tmp_path / "5.png")
    with open(anh_dau, "wb") as f:
        f.write(b"anh-dau-that")

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        # KHÔNG một lời nhắc nào qua được — mọi bước sửa chữ đều vô ích.
        raise RuntimeError("content_rejected: bị bộ lọc từ chối")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    bc, dong = _bc_ghi(goi_chat=lambda l, **k: "khong doi gi ca, giu nguyen y")

    dich = ak._anh_khung_cuoi(bc, luot, c, anh_dau, _HopRong())

    assert dich == "", "hết cách cứu thì trả rỗng — clip ghim một đầu, không ném lỗi"
    assert not os.path.exists(os.path.join(str(tmp_path), "5-cuoi.png"))

    with open(os.path.join(luot.thu_muc, "tu-choi.json"), encoding="utf-8") as f:
        so_dia = json.load(f)
    # Khoá sổ "khâu:cảnh" (rà soát 2.138.0, H3) — "khung_cuoi:5" KHÔNG trùng
    # "anh_canh:5" của khâu ảnh cảnh; mẹo "kc5" cũ không còn cần (và từng lọt
    # ra dòng báo khách thành "cảnh kc5").
    assert "5" not in so_dia["canh"], "không được đụng khoá sổ của ảnh cảnh"
    assert "anh_canh:5" not in so_dia["canh"], "không được đụng khoá sổ của ảnh cảnh"
    assert so_dia["canh"]["khung_cuoi:5"]["khau"] == "khung_cuoi"
    assert so_dia["canh"]["khung_cuoi:5"]["lui"] is True
    assert any("[LÙI]" in d and "khung cuối cảnh 5" in d for d in dong), dong
    assert not any("kc5" in d or "khung_cuoi" in d for d in dong), dong

    # Khâu clip đọc `anh_la_ban_lui(5)` để quyết có dùng ảnh động thay Veo
    # không — khung cuối lùi KHÔNG được làm nó tưởng nhầm ảnh CHÍNH của cảnh
    # là bản lùi (xem ghi chú ở `_anh_khung_cuoi`).
    so_cuu = ak._so_cuu_cua_luot(bc, luot)
    assert so_cuu.anh_la_ban_lui(5) is False


def test_khung_cuoi_ha_tang_that_van_ghim_mot_dau_nhu_cu(tmp_path, monkeypatch):
    """Lỗi HẠ TẦNG thật (không phải nội dung) vẫn phải rơi về đúng dòng báo
    "ghim một đầu" như HÀNH VI GỐC trước G8 — khung cuối là phần thêm, không
    được để nó chặn cả clip vì một trục trặc mạng."""
    c = {"scene_id": 6, "img_prompt": "a soldier. Style: 3D"}
    luot = _luot_gia(tmp_path)
    anh_dau = str(tmp_path / "6.png")
    with open(anh_dau, "wb") as f:
        f.write(b"anh-dau-that")

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        raise RuntimeError("mạng đứt giữa chừng")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    bc, dong = _bc_ghi()

    dich = ak._anh_khung_cuoi(bc, luot, c, anh_dau, _HopRong())

    assert dich == ""
    assert any("ghim một đầu" in d for d in dong), dong


# ═══ 2) ảnh người kể bị chặn lặp lại → THOÁT VÒNG, LÙI bỏ qua ══════════════


def test_nguoi_ke_bi_chan_lap_lai_thi_lui_bo_qua(tmp_path, monkeypatch):
    luot = _luot_gia(tmp_path)

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        raise RuntimeError("content_rejected: bị bộ lọc từ chối")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    monkeypatch.setattr(ak, "ThamChieu", _ThamChieuGia)
    bc, dong = _bc_ghi(goi_chat=lambda l, **k: "khong doi gi ca, giu nguyen y",
                       kieu_phu_de="karaoke", anh_nv=[str(tmp_path / "nv1.png")])
    with open(str(tmp_path / "nv1.png"), "wb") as f:
        f.write(b"nv1")

    dich = ak._lam_nguoi_ke(bc, luot)

    assert dich == "", "hết cách cứu thì trả rỗng — khâu dựng dùng ảnh tham chiếu nhân vật"
    assert not os.path.exists(os.path.join(luot.thu_muc, ak.TEP_NGUOI_KE))

    with open(os.path.join(luot.thu_muc, "tu-choi.json"), encoding="utf-8") as f:
        so_dia = json.load(f)
    # Khoá "khâu:cảnh" (rà soát 2.138.0, H3); nhãn tiếng Việt trên dòng báo.
    assert so_dia["canh"]["nguoi_ke:-"]["khau"] == "nguoi_ke"
    assert so_dia["canh"]["nguoi_ke:-"]["lui"] is True
    assert any("[LÙI]" in d and "ảnh người kể" in d for d in dong), dong
    assert not any("cảnh None" in d for d in dong), dong


def test_nguoi_ke_ha_tang_that_van_bo_qua_nhu_cu(tmp_path, monkeypatch):
    luot = _luot_gia(tmp_path)

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        raise RuntimeError("mạng đứt giữa chừng")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    monkeypatch.setattr(ak, "ThamChieu", _ThamChieuGia)
    bc, dong = _bc_ghi(kieu_phu_de="karaoke", anh_nv=[str(tmp_path / "nv1.png")])
    with open(str(tmp_path / "nv1.png"), "wb") as f:
        f.write(b"nv1")

    dich = ak._lam_nguoi_ke(bc, luot)

    assert dich == ""
    assert any("chưa vẽ được ảnh người kể" in d for d in dong), dong


# ═══ 3) nền bìa hai lớp bị chặn lặp lại → THOÁT VÒNG, LÙI bỏ qua như bìa
#        thường, không chặn khâu ảnh ════════════════════════════════════════


def test_bia_hai_lop_bi_chan_lap_lai_thi_lui_bo_qua(tmp_path, monkeypatch):
    luot = _luot_gia(tmp_path)
    thu_muc_bia = str(tmp_path / "7-thumbnail")
    os.makedirs(thu_muc_bia, exist_ok=True)

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        raise RuntimeError("content_rejected: bị bộ lọc từ chối")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    bc, dong = _bc_ghi(goi_chat=lambda l, **k: "khong doi gi ca, giu nguyen y",
                       kieu_bia="khong_chu")

    ta_bia = {"portrait_main": "a hero, close-up portrait. Style: 3D"}
    muc = (1, ("portrait_main", "mac dinh 1"))

    ket = ak._lam_bia_hai_lop(bc, luot, _HopRong(), thu_muc_bia, muc, ta_bia,
                              "Tiêu đề phim", "Chữ bìa", so=None)

    assert ket == (1, False)
    assert not os.path.exists(os.path.join(thu_muc_bia, "nen", "thumb_001.png"))
    assert not os.path.exists(os.path.join(thu_muc_bia, "thumb_001.png"))
    assert any("[LÙI]" in d and "ảnh bìa 1" in d for d in dong), dong  # nhãn tiếng Việt (2.138.0)


def test_bia_hai_lop_ha_tang_that_van_nem_len_binh_thuong(tmp_path, monkeypatch):
    """Đối chứng: lỗi HẠ TẦNG thật vẫn phải NÉM LÊN như cũ — chỉ lỗi NỘI DUNG
    mới được nuốt êm (cùng luật với `_lam_bia`/`_lam_anh_canh`)."""
    luot = _luot_gia(tmp_path)
    thu_muc_bia = str(tmp_path / "7-thumbnail")
    os.makedirs(thu_muc_bia, exist_ok=True)

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        raise RuntimeError("mạng đứt giữa chừng")

    monkeypatch.setattr(ak, "_tao_anh", tao_anh_gia)
    bc, dong = _bc_ghi(kieu_bia="khong_chu")
    ta_bia = {"portrait_main": "a hero, close-up portrait. Style: 3D"}

    with pytest.raises(RuntimeError, match="mạng đứt"):
        ak._lam_bia_hai_lop(bc, luot, _HopRong(), thu_muc_bia,
                            (1, ("portrait_main", "x")), ta_bia,
                            "Tiêu đề", "Chữ bìa", so=None)
