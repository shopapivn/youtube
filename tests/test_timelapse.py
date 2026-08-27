"""Kênh TIMELAPSE: một chỗ, ngàn năm, máy quay đứng yên, KHÔNG lời đọc.

Mọi con số trong bài kiểm này đo từ chính tệp video của đối thủ ngày 27/08/2026
— xem đầu `core/timelapse.py`.
"""
import json
import os
from types import SimpleNamespace

import pytest

from core import timelapse as tl
from core.kenh import doc_kenh

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bang():
    return tl.doc_bang_moc({
        "noi": "the Colosseum valley, Rome",
        "noi_vi": "thung lũng Colosseum",
        "goc_may": "A fixed view from the valley floor looking north along the road",
        "moc": [
            {"nam": 80, "nhan": "80 — the arena opens", "canh": "a new stone amphitheatre fills the valley",
             "bien_co": "crowds stream through the arches"},
            {"nam": -750, "nhan": "753 BC — first huts", "canh": "wooden huts on a marshy valley floor",
             "bien_co": "shepherds drive goats along the track"},
            {"nam": 1500, "nhan": "1500 — half buried", "canh": "the arena half buried, cattle graze",
             "bien_co": "a market sets up between the arches"},
        ]})


class TestBangMoc:
    def test_doc_bang_moc_sap_theo_nam_va_bo_moc_hong(self):
        b = _bang()
        assert [m["nam"] for m in b["moc"]] == [-750, 80, 1500], "phải sắp theo năm tăng dần"
        # mốc thiếu năm hoặc mô tả quá ngắn thì bỏ — thà ít mốc còn hơn một mốc rỗng
        b2 = tl.doc_bang_moc({"moc": [{"nam": "x", "canh": "abcdefghijk"},
                                      {"nam": 10, "canh": "ngan"},
                                      {"nam": 20, "canh": "a proper description here"}]})
        assert [m["nam"] for m in b2["moc"]] == [20]

    def test_so_moc_theo_do_dai_phim(self):
        assert tl.so_moc_cho_phut(8) == 60        # 8 phút ÷ 8 giây một mốc
        assert tl.so_moc_cho_phut(1) == 8
        assert tl.so_moc_cho_phut(0.1) == 4       # sàn: phim ngắn tới đâu cũng ≥ 4 mốc

    def test_loi_nhac_mang_du_luat_cua_dinh_dang(self):
        p = tl.loi_nhac_bang_moc("Thăng Long 1000 năm", 40)
        assert "40 milestones" in p and "Thăng Long 1000 năm" in p
        assert "camera never moves" in p          # luật số một của format
        assert "goc_may" in p and "moc" in p


class TestLoiNhac:
    def test_anh_moc_luon_mang_khoa_goc_may(self):
        b = _bang()
        p = tl.prompt_anh_moc(b, b["moc"][1])
        assert tl.KHOA_GOC_MAY in p
        assert b["goc_may"] in p
        assert "SAME view as the attached previous frame" in p
        # ảnh mốc ĐẦU không có khung trước để mà bám
        assert "attached previous frame" not in tl.prompt_anh_moc(b, b["moc"][0], dau_phim=True)

    def test_clip_chuyen_cam_moi_cu_dong_may(self):
        b = _bang()
        p = tl.prompt_clip_chuyen(b["moc"][0], b["moc"][1])
        assert "THE CAMERA DOES NOT MOVE AT ALL" in p
        for cam in ("no pan", "no tilt", "no zoom", "no drift"):
            assert cam in p
        assert "never as a cut or a dissolve" in p
        assert "shepherds drive goats" in p and "crowds stream" in p


class TestBangCanh:
    def test_canh_la_buoc_chuyen_giua_hai_moc(self):
        c = tl.canh_tu_bang_moc(_bang())
        assert len(c) == 2, "3 mốc thì có 2 bước chuyển"
        assert [x["scene_id"] for x in c] == [1, 2]
        assert c[0]["nam_tu"] == -750 and c[0]["nam_den"] == 80
        assert c[1]["nam_tu"] == 80 and c[1]["nam_den"] == 1500

    def test_moc_thoi_gian_gia_cong_don(self):
        """Không có giọng đọc thì nhịp lấy từ bảng mốc — mọi khâu sau vẫn chạy."""
        c = tl.canh_tu_bang_moc(_bang())
        assert c[0]["srt_start"] == "00:00:00,000" and c[0]["srt_end"] == "00:00:08,000"
        assert c[1]["srt_start"] == "00:00:08,000" and c[1]["srt_end"] == "00:00:16,000"
        assert all(x["duration"] == tl.GIAY_MOT_MOC for x in c)

    def test_moi_canh_dung_chung_mot_boi_canh(self):
        """Một chỗ duy nhất — nên mọi cảnh cùng `location_used`, không nhân vật."""
        c = tl.canh_tu_bang_moc(_bang())
        assert {x["location_used"] for x in c} == {"loc1"}
        assert all(x["characters_used"] == "" for x in c)
        assert all(json.loads(x["reference_files"]) == ["loc1.png"] for x in c)

    def test_it_hon_hai_moc_thi_khong_co_canh_nao(self):
        assert tl.canh_tu_bang_moc({"moc": [{"nam": 1, "canh": "x" * 20}]}) == []
        assert tl.canh_tu_bang_moc({}) == []

    def test_nam_theo_giay_de_in_len_goc_hinh(self):
        c = tl.canh_tu_bang_moc(_bang())
        assert tl.nam_theo_giay(c, 0.0) == -750
        assert tl.nam_theo_giay(c, 8.0) == 80
        assert tl.nam_theo_giay(c, 4.0) == pytest.approx(-335, abs=1)   # nội suy giữa hai mốc
        assert tl.nam_theo_giay(c, 999.0) == 1500                       # quá cuối thì giữ mốc cuối


class TestKenh:
    def test_kenh_mau_khai_dung_ba_thu_quyet_dinh(self):
        k = doc_kenh(GOC, "timelapse")
        assert tl.la_timelapse(k)
        assert k.khung_dau is True, "ghim hai đầu là toàn bộ ý nghĩa của kênh này"
        assert k.engine == "veo3"
        assert k.dot_phu_de is False and float(k.am_luong_nhac) == 1.0, "không lời đọc: nhạc chạy một mình"

    def test_kenh_khac_khong_bi_coi_la_timelapse(self):
        for ma in ("story-3d", "hoathinh-3d"):
            assert not tl.la_timelapse(doc_kenh(GOC, ma))


def test_bo_viec_timelapse_bo_hai_khau_tieng():
    """Không có lời đọc thì hai khâu tiếng phải BIẾN MẤT khỏi bảng khâu.

    `core.auto.chay` đánh dấu khâu vắng mặt là "bỏ qua", nên đây là cách tắt
    khâu mà không phải sửa bảng KHAU dùng chung.
    """
    from core.auto_khau import BoiCanh, dung_bo_viec

    def bo(ma):
        k = doc_kenh(GOC, ma)
        bc = BoiCanh(goc=GOC, kenh=k, goi_chat=lambda *a, **kw: "", client=object(),
                     on_log=lambda d: None)
        return set(dung_bo_viec(bc))

    assert "giong-doc" not in bo("timelapse") and "phu-de" not in bo("timelapse")
    assert {"kich-ban", "bang-canh", "anh", "clip", "thumbnail", "dung"} <= bo("timelapse")
    # kênh thường thì vẫn đủ tám khâu
    assert {"giong-doc", "phu-de"} <= bo("story-3d")
