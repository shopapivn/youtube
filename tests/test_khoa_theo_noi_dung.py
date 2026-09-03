"""Khoá phải đi theo NỘI DUNG, và hỏng hết thì phải dừng.

Ca thật, máy khách 03/09/2026, lượt 0016 (openstory), bước *"Cắt cảnh và viết
lời nhắc"*: năm lần bấm "Chạy tiếp" trong 24 giờ, cả năm chết y hệt nhau.

Dây chuyền của lỗi, ba mắt nối nhau — bài dưới đây canh cả ba:

1. Bước "đọc phim" chạy lại trả **11 màn** thay vì 7. Đầu vào không đổi một
   chữ nào; chỉ kết quả của máy đổi. Nên lời nhắc các bước sau khác đi, trong
   khi khoá của chúng chỉ gồm `(lần chạy, nút, việc)` — cổng thấy cùng khoá mà
   khác nội dung và từ chối, mãi mãi.
2. Cổng từ chối bằng câu *"Idempotency-Key này đã được dùng cho một yêu cầu có
   nội dung khác"*. `core/su_co.py` phân đúng nó thành `KHOA_LECH` với nhịp đợi
   RỖNG — nhưng `core/goi_van_ban.py` chưa bao giờ kể tên loại ấy trong danh
   sách được đổi khoá. Nhịp rỗng nên không ai đợi, danh sách thiếu nên không ai
   đổi: loại duy nhất sinh ra để đổi khoá là loại duy nhất không được đổi.
3. Mọi màn cùng hỏng, mỗi màn chỉ báo bằng một dòng **tiến độ**, rồi khâu sau
   vẫn chạy. Khách trả đủ tiền cho một video không có kế hoạch đạo diễn nào.

Không bài nào gọi mạng.
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _nap_run_py():
    """Nạp `tool-catalog/prompt.workbook/run.py` — tên thư mục có dấu chấm."""
    duong = os.path.join(GOC, "tool-catalog", "prompt.workbook", "run.py")
    spec = importlib.util.spec_from_file_location("prompt_workbook_run", duong)
    mo_dun = importlib.util.module_from_spec(spec)
    sys.modules["prompt_workbook_run"] = mo_dun
    spec.loader.exec_module(mo_dun)
    return mo_dun


@pytest.fixture(scope="module")
def wb():
    return _nap_run_py()


def cue(so: int, dai: float = 2.0):
    dau = (so - 1) * dai
    return {"index": so, "start": dau, "end": dau + dai,
            "text": "cau so {0}".format(so)}


def man(so: int, tu: int, den: int):
    return {"segment_id": so, "srt_from": tu, "srt_to": den,
            "name": "man {0}".format(so), "message": "y", "emotion": "buon",
            "motif": "mua"}


class TestLoiNhacNamTrongKhoa:
    """Cùng lời nhắc thì cùng khoá; khác lời nhắc thì khác khoá.

    Vế đầu là TIỀN: chạy lại y nguyên phải nhặt lại bài đã trả tiền, không trả
    lần hai. Vế sau là chỗ đã cắn — thiếu nó thì kẹt 409 vĩnh viễn.
    """

    def _bat_khoa(self, wb, monkeypatch, loi_nhac, viec="man-1"):
        bat = {}

        def goi_gia(_client, tin_nhan, **k):
            bat["khoa"] = k.get("khoa")
            return "xong"

        monkeypatch.setattr(wb, "goi_van_ban", goi_gia)
        monkeypatch.setenv("SHOPAPI_API_KEY", "khoa-gia-khong-goi-mang")
        goi = wb._hop_goi({"run_id": "luot16", "node_id": "auto"}, "claude-sonnet-5")
        goi(loi_nhac, viec)
        return bat["khoa"]

    def test_cung_loi_nhac_thi_cung_khoa(self, wb, monkeypatch):
        a = self._bat_khoa(wb, monkeypatch, "cắt cảnh cho màn 1")
        b = self._bat_khoa(wb, monkeypatch, "cắt cảnh cho màn 1")
        assert a == b, "chạy lại y nguyên mà đổi khoá là bắt khách trả tiền hai lần"

    def test_doi_loi_nhac_thi_doi_khoa(self, wb, monkeypatch):
        # Đúng cảnh lượt 0016: bước trước ra 7 màn rồi ra 11 màn, nên khối chữ
        # đưa vào bước này khác đi dù đầu vào của cả lượt không đổi.
        bay = self._bat_khoa(wb, monkeypatch, "kế hoạch cho 7 màn")
        muoi_mot = self._bat_khoa(wb, monkeypatch, "kế hoạch cho 11 màn")
        assert bay != muoi_mot, (
            "cùng khoá mà khác nội dung là cổng từ chối, và mọi lần "
            "'Chạy tiếp' về sau đều đi vào đúng ngõ cụt ấy")

    def test_khoa_van_doc_duoc_la_buoc_nao(self, wb, monkeypatch):
        # Băm đặt ở CUỐI, không thay phần tên việc: mở nhật ký ra vẫn biết ngay
        # khoá này của bước nào.
        khoa = self._bat_khoa(wb, monkeypatch, "x", viec="man-3")
        assert khoa.startswith("luot16:auto:man-3:")

    def test_hai_viec_khac_nhau_van_khac_khoa(self, wb, monkeypatch):
        a = self._bat_khoa(wb, monkeypatch, "cùng một lời nhắc", viec="man-1")
        b = self._bat_khoa(wb, monkeypatch, "cùng một lời nhắc", viec="man-2")
        assert a != b


class TestHongHetThiDung:
    """Hỏng một phần thì đi tiếp; hỏng hết thì phải dừng.

    Cùng lý lẽ với ghi chú đầu `tests/test_chia_canh.py`: lùi im lặng thì khách
    mở tệp ra thấy đủ số cảnh, không cách nào biết là đã hỏng.
    """

    def _chay(self, wb, ke_hoach_fn):
        return wb._ke_hoach_dao_dien(
            None, [cue(i) for i in range(1, 13)],
            {"segments": [man(1, 1, 4), man(2, 5, 8), man(3, 9, 12)],
             "context_lock": ""},
            {"characters": []}, engine="veo3", ke_hoach_fn=ke_hoach_fn)

    def test_hong_het_thi_bao_loi_chu_khong_tra_ve_rong(self, wb):
        def luon_hong(_seg, _dong, _cast):
            raise RuntimeError("Idempotency-Key này đã được dùng cho một "
                               "yêu cầu có nội dung khác.")

        with pytest.raises(RuntimeError, match="man nao"):
            self._chay(wb, luon_hong)

    def test_hong_mot_phan_thi_van_giu_phan_chay_duoc(self, wb):
        # Các màn còn lại có kế hoạch thật; vứt đi là vứt bài đã trả tiền.
        def hong_man_hai(seg, _dong, _cast):
            if seg["segment_id"] == 2:
                raise RuntimeError("máy chủ trả về nội dung rỗng")
            return {"beats": [{"srt_from": seg["srt_from"], "srt_to": seg["srt_to"],
                               "purpose": "ke chuyen"}]}

        ra = self._chay(wb, hong_man_hai)
        assert ra, "hỏng một màn không được giết cả phim"
        assert {b["segment_id"] for b in ra} == {1, 3}

    def test_khong_man_nao_hong_thi_chay_binh_thuong(self, wb):
        def ngon(seg, _dong, _cast):
            return {"beats": [{"srt_from": seg["srt_from"], "srt_to": seg["srt_to"],
                               "purpose": "ke chuyen"}]}

        ra = self._chay(wb, ngon)
        assert {b["segment_id"] for b in ra} == {1, 2, 3}
