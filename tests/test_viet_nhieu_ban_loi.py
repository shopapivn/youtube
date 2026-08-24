"""Lõi dùng chung `core/viet_nhieu_ban.py` — tab Viết kịch bản gọi thẳng vào đây."""

from __future__ import annotations

import json

import pytest

from core.viet_nhieu_ban import (TIEU_CHI_MAC_DINH, bang_so_do, cham_va_chon,
                                 trung_nguyen_van, viet_va_chon)

GOC = "一人の時間が長いほどストレスは低くなります。研究チームは二十一日間の日記を集めました。"
BAN = ["一人の夜。" * 40, "静かな部屋で。" * 45, "雨の音。" * 30]


class _Ai:
    def __init__(self, tra):
        self.tra = list(tra)
        self.nhan = []

    def __call__(self, p):
        self.nhan.append(p)
        return self.tra.pop(0)


class TestVietVaChon:
    def test_viet_ba_ban_roi_chon(self):
        ai = _Ai(BAN + [json.dumps({"chon": "C", "diem": {"C": 9}, "ly_do": "hook"})])
        chon, ban, bien_ban = viet_va_chon(ai, "viết đi", 3, GOC,
                                           tieu_chi="hook trước", muc_tieu=120)
        assert chon == BAN[2] and ban == BAN
        assert len(ai.nhan) == 4
        # Tiêu chí của người dùng đi vào lời nhắc chấm, kèm số đo và bản gốc.
        assert "hook trước" in ai.nhan[3] and "Bản A" in ai.nhan[3] and GOC in ai.nhan[3]
        assert "Chọn: bản C" in bien_ban and "hook" in bien_ban

    def test_tieu_chi_trong_thi_dung_mac_dinh(self):
        ai = _Ai(BAN[:2] + [json.dumps({"chon": "B"})])
        viet_va_chon(ai, "viết", 2, GOC)
        assert TIEU_CHI_MAC_DINH.splitlines()[0] in ai.nhan[2]

    def test_mot_ban_thi_khong_cham(self):
        ai = _Ai([BAN[0]])
        chon, ban, _ = viet_va_chon(ai, "viết", 1, GOC)
        assert chon == BAN[0] and len(ai.nhan) == 1

    def test_bam_dung_dung_ngay(self):
        class Dung(Exception):
            pass

        def kiem():
            raise Dung()

        with pytest.raises(Dung):
            viet_va_chon(_Ai(BAN), "viết", 3, GOC, kiem_dung=kiem)


class TestChamVaChon:
    def test_json_hong_thi_theo_so_do(self):
        # A=200, B=315, C=120; mục tiêu 140 → C.
        chon, ly_do, _diem, _bang = cham_va_chon(lambda _p: "rác", BAN, GOC,
                                                 muc_tieu=140)
        assert chon == 2 and "số đo" in ly_do

    def test_chon_chu_la_thi_theo_so_do(self):
        chon, _l, _d, _b = cham_va_chon(lambda _p: '{"chon": "Z"}', BAN, GOC,
                                        muc_tieu=140)
        assert chon == 2

    def test_khong_muc_tieu_thi_bang_khong_co_lech(self):
        _so, bang = bang_so_do(BAN, GOC, 0)
        assert "lệch" not in bang and "Bản C" in bang


class TestTrung:
    def test_chep_nguyen(self):
        assert trung_nguyen_van(GOC, GOC) == 1.0
