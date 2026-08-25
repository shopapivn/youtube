"""Nhật ký khâu kịch bản kể đúng luồng hiện tại: viết N bản → chấm & chọn →
hoàn thiện → rà soát. Chủ dự án, 25/08/2026: *"sửa log ở tự động để nó đúng
với luồng logic hiện tại"*.
"""
import json
import os

from core.auto import LuotChay
from core.auto_khau import BoiCanh, _viet_nhieu_ban

GOC = "bản gốc đối thủ。"
BAN = ["一人の夜。" * 40, "静かな部屋で。" * 45, "雨の音。" * 30]


class _K:
    mo_hinh = "m"
    ngon_ngu = "ja"
    giong_van = "ja"
    style: dict = {}
    so_ban_nhap = 3
    hoan_thien = True
    ky_tu_moi_phut = 300
    prompt = {"2-viet.md": "viet <<COMPETITOR_TRANSCRIPT>>",
              "2b-cham.md": "cham <<SO_DO>> <<CAC_BAN>>",
              "2c-hoan-thien.md": "ht <<DIEM_YEU>> <<DRAFT>>"}


def _chay(tmp_path, tra):
    tra = list(tra)
    log = []
    bc = BoiCanh(goc=".", kenh=_K(), goi_chat=lambda p, **_k: tra.pop(0),
                 on_log=log.append, ngu=lambda _g: None)
    luot = LuotChay(ma_kenh="K", ma_luot="L", thu_muc=str(tmp_path))
    ra = _viet_nhieu_ban(bc, luot, _K(), {"PHUT": "13"}, _K.prompt["2-viet.md"],
                         GOC, 200, str(tmp_path))
    return ra, "\n".join(log)


def _thu_tu(log, *cac_doan):
    """Các đoạn phải xuất hiện theo đúng thứ tự này."""
    vi_tri = -1
    for doan in cac_doan:
        moi = log.find(doan, vi_tri + 1)
        assert moi > vi_tri, (doan, log)
        vi_tri = moi


class TestNhatKyHoanThien:
    def test_hoan_thien_duoc_chon(self, tmp_path):
        ht = BAN[1].replace("静かな部屋で。", "静かな夜の部屋で。", 8)
        ra, log = _chay(tmp_path, BAN + [
            json.dumps({"chon": "B", "ly_do": "bám gốc", "diem_manh": "mở nhanh",
                        "diem_yeu": "giữa mỏng"}),
            ht, json.dumps({"chon": "B", "ly_do": "mượt hơn"})])
        assert ra == ht
        _thu_tu(log, "viết bản A/3", "viết bản B/3", "viết bản C/3",
                "chấm 3 bản", "chọn bản B:", "phút", "bộ chấm chê bản B: giữa mỏng",
                "hoàn thiện bản đã chọn", "đã hoàn thiện: giữ",
                "so bản B chưa hoàn thiện với bản B đã hoàn thiện",
                "chọn bản B đã hoàn thiện:", "→ dùng bản B đã hoàn thiện")
        assert "chọn bản A" not in log, "so hai bản mà in A/B là không ai hiểu"

    def test_hoan_thien_khong_hon(self, tmp_path):
        ht = BAN[1].replace("静かな部屋で。", "静かな夜の部屋で。", 8)
        ra, log = _chay(tmp_path, BAN + [
            json.dumps({"chon": "B", "ly_do": "bám gốc", "diem_yeu": "giữa mỏng"}),
            ht, json.dumps({"chon": "A", "ly_do": "bản cũ gọn hơn"})])
        assert ra == BAN[1]
        _thu_tu(log, "chọn bản B chưa hoàn thiện:",
                "bản hoàn thiện không hơn — dùng bản B chưa hoàn thiện",
                "→ dùng bản B;")

    def test_bo_cham_khong_neu_diem_thi_noi_ro(self, tmp_path):
        ra, log = _chay(tmp_path, BAN + [json.dumps({"chon": "C", "ly_do": "ok"})])
        assert ra == BAN[2]
        assert "bộ chấm không nêu điểm mạnh/yếu — bỏ qua hoàn thiện" in log
        assert "→ dùng bản C;" in log


class TestNhanBuoc:
    def test_nhan_viet_va_ra_soat_theo_luong_moi(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "core", "auto_khau.py"), encoding="utf-8") as t:
            chu = t.read()
        assert '"đối chiếu và sửa")' not in chu, "nhãn cũ của bước 3 (chú thích thì được)"
        assert "rà soát bản cuối" in chu
        assert "chấm & chọn một bản" in chu
