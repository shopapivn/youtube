"""Khâu ảnh tab Tự động: bộ lọc từ chối thì viết lại lời nhắc một lần rồi thử lại.

Đo 25/08/2026: ba cảnh bị chặn vì "cheeks flushing", "violently", "coy" — trước đây
cảnh bị bỏ, dù tab Hàng loạt đã biết viết lại.

═══ CẬP NHẬT GÓI G4 (28/09/2026) ═══

`_lam_anh_canh` giờ đi qua `core.tu_choi_noi_dung.lam_co_cuu` +
`CHUOI_CUU["anh_canh"]` (docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md mục 2.5) thay
vì tự viết-lại/thay-từ-thô ngay trong hàm. Hai chỗ khác với bản cũ:

1. `_tao_anh` (bị monkeypatch ở đây) giờ nhận thêm hai đối `so_cuu=`/`dv=` —
   các hàm giả trong tệp này nhận `**kw` để không vỡ khi nhận thêm đối mới.
2. Cảnh bị chặn hết MỌI cách sửa lời nhắc không còn ném lỗi gốc lên nữa: nó
   rơi xuống chuỗi LÙI (ảnh bối cảnh không người / mượn ảnh liền kề — gói G4).
   Không có gì để lùi (như trong bài kiểm này: một cảnh duy nhất, không tham
   chiếu bối cảnh) thì `lam_co_cuu` ném `tcnd.LoiTuChoi` — SoCuu.tests riêng
   cho hai bước LÙI nằm ở `tests/test_g4_anh_bi_tu_choi.py`.
"""
import json
import os
from types import SimpleNamespace

import pytest

from core import auto_khau
from core import tu_choi_noi_dung as tcnd


def _bc(tra_ai):
    nhat_ky = []
    kenh = SimpleNamespace(mo_hinh="claude-sonnet-5", che_do_ke="", anh_nv=[], engine="veo3")
    return SimpleNamespace(kenh=kenh, ghi=nhat_ky.append, _nhat_ky=nhat_ky,
                           goi_chat=lambda loi_nhac, **kw: tra_ai(loi_nhac), client=object())


class _Hop:
    def lay(self):
        return []


def _luot(tmp_path, canh):
    d = tmp_path / "0001"
    d.mkdir()
    (d / "4-canh.json").write_text(json.dumps(canh, ensure_ascii=False), encoding="utf-8")
    return SimpleNamespace(thu_muc=str(d), ma_luot="0001", ma_kenh="x")


def test_bi_tu_choi_thi_viet_lai_va_thu_lai(tmp_path, monkeypatch):
    c = {"scene_id": 64, "img_prompt": "her cheeks flushing pink, a cat by the river. Style: 3D"}
    luot = _luot(tmp_path, [c])
    goi = []

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        goi.append(prompt)
        if "flushing" in prompt:
            raise RuntimeError("content_rejected: Nội dung bị bộ lọc an toàn từ chối")
        return {"id": "job1"}

    monkeypatch.setattr(auto_khau, "_tao_anh", tao_anh_gia)
    monkeypatch.setattr(auto_khau, "_tai_ket_qua", lambda bc, goi_, i, tep: open(tep, "wb").write(b"png"))
    monkeypatch.setattr(auto_khau, "_xoa_dau", lambda bc, tep: None)
    bc = _bc(lambda l: "her cheeks rosy, a cat by the river. Style: 3D")
    tep = str(tmp_path / "64.png")
    auto_khau._lam_anh_canh(bc, luot, c, tep, _Hop())
    assert len(goi) == 2 and "flushing" not in goi[1]
    assert os.path.exists(tep)
    assert c["img_prompt"] == "her cheeks rosy, a cat by the river. Style: 3D"
    # Ghi lại vào 4-canh.json để khâu clip / lần làm lại dùng bản đã qua.
    with open(os.path.join(luot.thu_muc, "4-canh.json"), encoding="utf-8") as f:
        assert "rosy" in json.load(f)[0]["img_prompt"]
    # Dòng báo dùng nhãn tiếng Việt, KHÔNG tên hàm (rà soát 2.138.0 — trước
    # là "viet_lai_prompt_anh", khách không đọc được).
    assert any("[CỨU]" in d and "cảnh 64" in d and "viết lại lời nhắc" in d
               for d in bc._nhat_ky), bc._nhat_ky
    assert not any("viet_lai_prompt_anh" in d for d in bc._nhat_ky), bc._nhat_ky


def test_loi_khac_khong_viet_lai(tmp_path, monkeypatch):
    c = {"scene_id": 1, "img_prompt": "a cat"}
    luot = _luot(tmp_path, [c])

    def tao_anh_gia(*a, **k):
        raise RuntimeError("mạng đứt")

    monkeypatch.setattr(auto_khau, "_tao_anh", tao_anh_gia)
    bc = _bc(lambda l: pytest.fail("không được gọi AI"))
    with pytest.raises(RuntimeError, match="mạng đứt"):
        auto_khau._lam_anh_canh(bc, luot, c, str(tmp_path / "1.png"), _Hop())


def test_viet_lai_khong_ra_thi_het_cach_cuu(tmp_path, monkeypatch):
    """AI không đổi được gì (trả nguyên văn) và không có bối cảnh/cảnh liền kề
    nào để LÙI (một cảnh duy nhất, không tham chiếu) — hết cả chuỗi cứu thì
    `lam_co_cuu` ném `LoiTuChoi`, không còn ném thẳng lỗi gốc như bản cũ."""
    c = {"scene_id": 2, "img_prompt": "a cat"}
    luot = _luot(tmp_path, [c])

    def tao_anh_gia(*a, **k):
        raise RuntimeError("content_rejected")

    monkeypatch.setattr(auto_khau, "_tao_anh", tao_anh_gia)
    bc = _bc(lambda l: "a cat")           # AI trả y nguyên → không có gì để thử lại
    with pytest.raises(tcnd.LoiTuChoi) as ei:
        auto_khau._lam_anh_canh(bc, luot, c, str(tmp_path / "2.png"), _Hop())
    assert ei.value.ket_luan.khau == "anh_canh"
    # Không có ảnh bối cảnh, không có cảnh liền kề nào khác trong 4-canh.json.
    assert any("[DỪNG]" in d for d in bc._nhat_ky), bc._nhat_ky


def test_lan_ba_thay_tu_tho(tmp_path, monkeypatch):
    c = {"scene_id": 28, "img_prompt": "the wolf scooping honey toward his open mouth and licking it, at the shop. Style: 3D"}
    luot = _luot(tmp_path, [c])
    goi = []

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        goi.append(prompt)
        if "mouth" in prompt or "lick" in prompt:
            raise RuntimeError("content_rejected")
        return {"id": "job"}

    monkeypatch.setattr(auto_khau, "_tao_anh", tao_anh_gia)
    monkeypatch.setattr(auto_khau, "_tai_ket_qua", lambda bc, goi_, i, tep: open(tep, "wb").write(b"png"))
    monkeypatch.setattr(auto_khau, "_xoa_dau", lambda bc, tep: None)
    # AI viết lại vẫn giữ "mouth" → lần 3 thay từ thô mới qua.
    bc = _bc(lambda l: "the wolf scooping honey toward his open mouth, at the shop. Style: 3D")
    auto_khau._lam_anh_canh(bc, luot, c, str(tmp_path / "28.png"), _Hop())
    assert len(goi) == 3 and "mouth" not in goi[2] and "lick" not in goi[2]
    assert "toward his face" in goi[2] or "big smile" in goi[2]


def test_lam_lanh_tho_thu_truyen():
    from core.viet_lai_prompt import lam_lanh_tho
    ra = lam_lanh_tho("the wolf swallows them whole, then licks his lips, fangs showing")
    assert "swallow" not in ra and "lick" not in ra and "fangs" not in ra
    assert "hides them in his big round belly" in ra


def test_loi_nhac_da_sua_luu_khong_kem_duoi_noi_canh(tmp_path, monkeypatch):
    from core.noi_canh import DUOI_NOI_CANH
    c = {"scene_id": 9, "img_prompt": "her cheeks flushing, a cat" + DUOI_NOI_CANH}
    luot = _luot(tmp_path, [{"scene_id": 9, "img_prompt": "her cheeks flushing, a cat"}])
    goi = []

    def tao_anh_gia(bc, luot, prompt, hop, khoa, ten_hien="", so=None, **kw):
        goi.append(prompt)
        if "flushing" in prompt:
            raise RuntimeError("content_rejected")
        return {"id": "job1"}

    monkeypatch.setattr(auto_khau, "_tao_anh", tao_anh_gia)
    monkeypatch.setattr(auto_khau, "_tai_ket_qua", lambda bc, goi_, i, tep: open(tep, "wb").write(b"png"))
    monkeypatch.setattr(auto_khau, "_xoa_dau", lambda bc, tep: None)
    bc = _bc(lambda l: "her cheeks rosy, a cat" + DUOI_NOI_CANH)
    auto_khau._lam_anh_canh(bc, luot, c, str(tmp_path / "9.png"), _Hop())
    with open(os.path.join(luot.thu_muc, "4-canh.json"), encoding="utf-8") as f:
        luu = json.load(f)[0]["img_prompt"]
    assert "rosy" in luu and "NEXT moment" not in luu
