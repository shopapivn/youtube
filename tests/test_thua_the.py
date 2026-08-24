"""Thẻ cảm xúc không được dày hơn một thẻ mỗi 4 câu (`thua_the`).

Đo 24–25/08/2026 trên bốn lượt thật: dặn "4–6 câu một thẻ" mà AI chèn 29–43
thẻ cho ~150 câu. Giọng đọc đầy thẻ nghe như diễn kịch — chốt bằng mã.
"""

from __future__ import annotations

from core.the_cam_xuc import bo_the, kiem_the, thua_the

CAU = "静かな夜です。"


def _bai(*muc):
    """`muc` = chuỗi "T" (thẻ) hoặc "C" (câu) theo thứ tự."""
    ra = []
    for m in muc:
        ra.append("[curious] " if m == "T" else CAU)
    return "".join(ra)


class TestThuaThe:
    def test_giu_the_dau_bo_the_den_som(self):
        # Thẻ, 2 câu, thẻ (sớm — bỏ), 3 câu, thẻ (đủ 5 câu — giữ).
        bai = _bai("T", "C", "C", "T", "C", "C", "C", "T", "C")
        ra = thua_the(bai)
        assert ra.count("[curious]") == 2

    def test_khong_doi_mot_chu_nao(self):
        """Chỉ mất thẻ (và dấu cách đi kèm), không mất một chữ nào."""
        bai = _bai("T", "C", "T", "C", "T", "C")
        assert "".join(bo_the(thua_the(bai)).split()) == "".join(bo_the(bai).split())
        assert kiem_the(bo_the(bai), thua_the(bai))

    def test_the_thua_du_thi_giu_het(self):
        bai = _bai("T", "C", "C", "C", "C", "T", "C", "C", "C", "C", "T")
        assert thua_the(bai).count("[curious]") == 3

    def test_khong_de_lai_dau_cach_doi(self):
        bai = CAU + "[curious] [sad] " + CAU
        ra = thua_the(bai)
        assert "  " not in ra and ra.count("[") == 1

    def test_rong_thi_rong(self):
        assert thua_the("") == ""
