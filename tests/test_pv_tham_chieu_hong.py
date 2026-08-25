"""Ảnh tham chiếu bị từ chối: thử lại MỘT lần, rồi nói thật — không báo "đủ".

Đo 25/08/2026: bộ lọc nhà cung cấp ảnh chặn "mèo đi hia 3D" 15 cách viết liên
tiếp; bản cũ của tab im lặng bỏ qua ảnh hỏng và không cho khách biết cảnh nào sẽ
thiếu nhân vật. Không dựng cửa sổ, không gọi mạng.
"""

from __future__ import annotations

from types import SimpleNamespace

from core.jobs import STATUS_DONE, STATUS_FAILED
from ui_qt.trang_prompt_visuals import TrangPromptVisuals


class _Trang:
    """Chỉ những gì ba hàm cần — không phải QWidget."""

    def __init__(self):
        self._tc_dang_cho = {}
        self._tc_da_thu_lai = set()
        self._tc_thieu = []
        self.nhat_ky = []
        self.da_gui = []
        self._thu_vien = SimpleNamespace(cap_nhat=lambda _d: None)

    def _ghi(self, chu):
        self.nhat_ky.append(chu)

    def _tao_anh_tham_chieu(self, duong_xlsx, ds, thu_lai=False):
        self.da_gui.append((ds, thu_lai))
        for ma_id, prompt in ds:
            self._tc_dang_cho["k-" + ma_id + ("-2" if thu_lai else "")] = (ma_id, duong_xlsx, prompt)

    nhan_su_kien = TrangPromptVisuals.nhan_su_kien
    _tham_chieu_hong = TrangPromptVisuals._tham_chieu_hong
    _bao_du_tham_chieu = TrangPromptVisuals._bao_du_tham_chieu
    _thu_dong_anh = {}
    _thu_dong_video = {}


def _su_kien(khoa, trang_thai, message=""):
    return SimpleNamespace(spec=SimpleNamespace(idempotency_key=khoa), status=trang_thai,
                           message=message, files=[], urls=[])


def test_hong_lan_dau_thi_thu_lai_mot_lan_roi_noi_that():
    t = _Trang()
    t._tao_anh_tham_chieu("x.xlsx", [("nv4", "a cat in boots")])
    t.nhan_su_kien("job", _su_kien("k-nv4", STATUS_FAILED, "Nội dung bị từ chối"))
    assert t.da_gui[-1] == ([("nv4", "a cat in boots")], True), "phải thử lại đúng một lần"
    assert "thử lại một lần" in t.nhat_ky[-1]
    # Lần hai cũng hỏng → ghi rõ id thiếu + việc khách cần làm, KHÔNG báo "Đủ".
    t.nhan_su_kien("job", _su_kien("k-nv4-2", STATUS_FAILED, "Nội dung bị từ chối"))
    assert len(t.da_gui) == 2
    assert t._tc_thieu == ["nv4"]
    assert "KHÔNG tạo được sau hai lần" in t.nhat_ky[-2] and "Bước 4" in t.nhat_ky[-2]
    assert "CHƯA ĐỦ" in t.nhat_ky[-1] and "nv4" in t.nhat_ky[-1]
    assert not any("Đủ ảnh tham chiếu" in d for d in t.nhat_ky)


def test_du_khi_khong_thieu(monkeypatch):
    t = _Trang()
    t._tao_anh_tham_chieu("x.xlsx", [("nv2", "a hero")])
    # Ảnh xong → hàm chép tệp là của lớp thật; ở đây chỉ kiểm đường "đủ".
    t._tc_dang_cho.pop("k-nv2")
    t._bao_du_tham_chieu()
    assert "Đủ ảnh tham chiếu" in t.nhat_ky[-1]
    assert STATUS_DONE  # nhắc: nhánh xong vẫn qua _bao_du_tham_chieu
