"""Viết nhiều bản rồi chấm chọn một (`_viet_nhieu_ban`).

Chủ dự án, 25/08/2026: *"cho nó viết nhiều lần, và chấm điểm các lần tức là
chọn bản tốt nhất ok nhất khi viết ví dụ 3 lần chẳng hạn"*.
"""

from __future__ import annotations

import json
import os

from core.auto import LuotChay
from core.auto_khau import (TEP_BAN_VIET, TEP_CHAM_DIEM, BoiCanh,
                            _trung_nguyen_van, _viet_nhieu_ban)

GOC_DOI_THU = "一人の時間が長いほどストレスは低くなります。研究チームは二十一日間の日記を集めました。"


class _KenhGia:
    mo_hinh = "m"
    ngon_ngu = "ja"
    giong_van = "ja"
    style: dict = {}

    def __init__(self, so_ban=3, co_cham=True):
        self.so_ban_nhap = so_ban
        self.prompt = {"2-viet.md": "viet <<CHARS>> <<COMPETITOR_TRANSCRIPT>>"}
        if co_cham:
            self.prompt["2b-cham.md"] = "cham <<SO_DO>> <<CAC_BAN>>"


def _luot(d):
    return LuotChay(ma_kenh="K", ma_luot="L", thu_muc=d)


class _AiGia:
    """Mỗi lượt gọi trả về mục kế tiếp; nhớ lại lời nhắc để kiểm."""

    def __init__(self, tra):
        self.tra = list(tra)
        self.nhan = []

    def __call__(self, loi_nhac, **_k):
        self.nhan.append(loi_nhac)
        return self.tra.pop(0)


def _bc(ai):
    return BoiCanh(goc=".", kenh=_KenhGia(), goi_chat=ai, on_log=lambda _d: None,
                   ngu=lambda _g: None)


BAN = ["一人の夜。" * 40, "静かな部屋で。" * 45, "雨の音。" * 30]


class TestChamChon:
    def test_ba_ban_roi_cham_chon_B(self, tmp_path):
        ai = _AiGia(BAN + [json.dumps({"chon": "B", "diem": {"A": 6, "B": 8, "C": 5},
                                       "ly_do": "bám gốc nhất"})])
        k = _KenhGia(3)
        ra = _viet_nhieu_ban(_bc(ai), _luot(str(tmp_path)), k, {}, k.prompt["2-viet.md"],
                             GOC_DOI_THU, 200, str(tmp_path))
        assert ra == BAN[1]
        assert len(ai.nhan) == 4                    # 3 bản + 1 chấm
        # Số đo có mặt trong lời nhắc chấm.
        assert "Bản A" in ai.nhan[3] and "trùng nguyên văn" in ai.nhan[3]
        # Ba bản và bản chấm nằm lại trên đĩa cho chủ kênh soi.
        for nhan in "ABC":
            assert os.path.isfile(os.path.join(str(tmp_path), TEP_BAN_VIET.format(nhan)))
        with open(os.path.join(str(tmp_path), TEP_CHAM_DIEM), encoding="utf-8") as t:
            assert "Chọn: bản B" in t.read()

    def test_cham_hong_thi_chon_theo_so_do(self, tmp_path):
        """JSON hỏng → chọn bản gần mục tiêu nhất.

        A = 200, B = 315, C = 120 ký tự; mục tiêu 140 → C (lệch 14%) gần hơn
        A (43%)."""
        ai = _AiGia(BAN + ["không phải json"])
        k = _KenhGia(3)
        ra = _viet_nhieu_ban(_bc(ai), _luot(str(tmp_path)), k, {}, k.prompt["2-viet.md"],
                             GOC_DOI_THU, 140, str(tmp_path))
        assert ra == BAN[2]

    def test_khong_co_prompt_cham_thi_khong_goi_AI_cham(self, tmp_path):
        ai = _AiGia(list(BAN))
        k = _KenhGia(3, co_cham=False)
        _viet_nhieu_ban(_bc(ai), _luot(str(tmp_path)), k, {}, k.prompt["2-viet.md"],
                        GOC_DOI_THU, 300, str(tmp_path))
        assert len(ai.nhan) == 3

    def test_chep_qua_nua_ban_goc_bi_phat_khi_chon_theo_so_do(self, tmp_path):
        chep = GOC_DOI_THU * 4                     # gần đúng độ dài nhưng chép
        viet = "静かな部屋で。" * 24                 # cùng độ dài, không chép
        ai = _AiGia([chep, viet, "x"])
        k = _KenhGia(2, co_cham=False)
        ra = _viet_nhieu_ban(_bc(ai), _luot(str(tmp_path)), k, {}, k.prompt["2-viet.md"],
                             GOC_DOI_THU, len(chep), str(tmp_path))
        assert ra == viet

    def test_chay_tiep_nhat_lai_ban_da_viet(self, tmp_path):
        """Đứt sau bản B: chạy lại chỉ viết bản C, không viết lại A/B."""
        for nhan, chu in zip("AB", BAN):
            with open(os.path.join(str(tmp_path), TEP_BAN_VIET.format(nhan)), "w",
                      encoding="utf-8") as t:
                t.write(chu)
        ai = _AiGia([BAN[2], json.dumps({"chon": "A"})])
        k = _KenhGia(3)
        ra = _viet_nhieu_ban(_bc(ai), _luot(str(tmp_path)), k, {}, k.prompt["2-viet.md"],
                             GOC_DOI_THU, 200, str(tmp_path))
        assert ra == BAN[0] and len(ai.nhan) == 2

    def test_mot_ban_thi_khong_cham(self, tmp_path):
        ai = _AiGia([BAN[0]])
        k = _KenhGia(1)
        assert _viet_nhieu_ban(_bc(ai), _luot(str(tmp_path)), k, {},
                               k.prompt["2-viet.md"], GOC_DOI_THU, 200,
                               str(tmp_path)) == BAN[0]
        assert len(ai.nhan) == 1


class TestNutTrenGUI:
    """Đặt được số bản và tiêu chí chọn ngay trong Quản lý kênh, không mở tệp."""

    def _kenh_py(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "ui_qt", "kenh.py"), encoding="utf-8") as t:
            return t.read()

    def test_o_so_ban_luu_vao_kenh_yaml(self):
        chu = self._kenh_py()
        assert "self._o_so_ban = QSpinBox()" in chu
        assert '("so_ban_nhap", str(self._o_so_ban.value()))' in chu

    def test_o_va_cho_rot_luu_vao_kenh_yaml(self):
        chu = self._kenh_py()
        assert "self._o_va = QCheckBox(" in chu
        assert '("va_cho_rot", "true" if self._o_va.isChecked() else "false")' in chu

    def test_the_cham_chon_co_ten_de_sua_tieu_chi(self):
        from ui_qt.kenh import _NHAN_PROMPT, _VIEC_PROMPT

        assert "2b-cham.md" in _NHAN_PROMPT and "2b-cham.md" in _VIEC_PROMPT

    def test_kenh_yaml_doc_so_ban_nhap(self, tmp_path):
        from core.kenh import doc_kenh

        d = os.path.join(str(tmp_path), "CHANNEL", "K1")
        os.makedirs(d)
        with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
            t.write("ma: K1\nso_ban_nhap: 3\n")
        assert doc_kenh(str(tmp_path), "K1").so_ban_nhap == 3
        with open(os.path.join(d, "kenh.yaml"), "w", encoding="utf-8") as t:
            t.write("ma: K1\nso_ban_nhap: 99\nva_cho_rot: true\n")
        k = doc_kenh(str(tmp_path), "K1")
        assert k.so_ban_nhap == 5, "kẹp 1..5"
        assert k.va_cho_rot is True


class TestTrungNguyenVan:
    def test_chep_nguyen_la_100(self):
        assert _trung_nguyen_van(GOC_DOI_THU, GOC_DOI_THU) == 1.0

    def test_khac_han_la_0(self):
        assert _trung_nguyen_van("静かな部屋で。" * 10, GOC_DOI_THU) == 0.0

    def test_bo_qua_dau_cau_va_khoang_trang(self):
        co_dau = GOC_DOI_THU.replace("。", "。\n\n")
        assert _trung_nguyen_van(co_dau, GOC_DOI_THU) == 1.0
