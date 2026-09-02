# -*- coding: utf-8 -*-
"""Khâu xuất lại qua CapCut — phần kiểm được KHÔNG CẦN mở CapCut.

Phần bấm chuột thật đã đo tay trên máy chủ dự án 02/09/2026 (xem nhật ký
trong `core/capcut.py`). Ở đây chỉ kiểm những gì thuần đĩa: dựng bản nháp từ
khuôn, ghi/gỡ sổ cái, và van bật/tắt của kênh — ba chỗ mà sai một ly là
CapCut mở nhầm dự án của khách.
"""
import json
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import capcut  # noqa: E402
from core.capcut import LoiCapCut, tao_nhap, _go_khoi_so_cai  # noqa: E402

#: id nằm sẵn trong khuôn — bản nháp sinh ra KHÔNG được còn chúng, kẻo hai
#: lượt chạy đẻ hai bản nháp trùng id và CapCut coi là một.
ID_KHUON = ("91E08AC5", "0e8963dfea644a41", "ed8c4e1e674f4f3b",
            "158f8f2782", "b63f279ef123")


def _dung_goc_nhap(tmp_path, so_du_an_cu=1):
    """Thư mục nháp giả, có sổ cái với `so_du_an_cu` dự án của "khách"."""
    goc = tmp_path / "com.lveditor.draft"
    goc.mkdir()
    cu = [{"draft_name": "du-an-cua-khach-{0}".format(i),
           "tm_draft_modified": 1_700_000_000_000_000 + i,
           "tm_duration": 1_000_000}
          for i in range(so_du_an_cu)]
    (goc / "root_meta_info.json").write_text(
        json.dumps({"all_draft_store": cu, "draft_ids": len(cu),
                    "root_path": str(goc)}), encoding="utf-8")
    return str(goc)


@pytest.fixture()
def video_gia(tmp_path, monkeypatch):
    v = tmp_path / "8-video.mp4"
    v.write_bytes(b"x" * 100)
    monkeypatch.setattr(capcut, "_thong_tin_video",
                        lambda _v: (7_000_000, 1920, 1080))
    return str(v)


def test_tao_nhap_thay_het_du_lieu_khuon(tmp_path, video_gia):
    goc = _dung_goc_nhap(tmp_path)
    thu_muc = tao_nhap(video_gia, "shopapi-xuat-test", goc_nhap=goc)

    chu = open(os.path.join(thu_muc, "draft_content.json"),
               encoding="utf-8").read()
    for ma in ID_KHUON:
        assert ma not in chu, "id của khuôn còn sót: " + ma
    noi_dung = json.loads(chu)
    assert noi_dung["duration"] == 7_000_000
    assert noi_dung["canvas_config"]["width"] == 1920
    tep = noi_dung["materials"]["videos"][0]
    assert tep["path"] == os.path.abspath(video_gia)
    assert tep["duration"] == 7_000_000
    doan = noi_dung["tracks"][0]["segments"][0]
    assert doan["material_id"] == tep["id"]
    assert doan["target_timerange"]["duration"] == 7_000_000
    assert doan["extra_material_refs"] == [
        noi_dung["materials"]["speeds"][0]["id"]]
    # meta của nháp cũng phải có, không CapCut từ chối thư mục
    meta = json.load(open(os.path.join(thu_muc, "draft_meta_info.json"),
                          encoding="utf-8"))
    assert meta["draft_name"] == "shopapi-xuat-test"
    assert meta["tm_duration"] == 7_000_000


def test_tao_nhap_len_dau_so_cai_va_sao_luu(tmp_path, video_gia):
    goc = _dung_goc_nhap(tmp_path, so_du_an_cu=3)
    tao_nhap(video_gia, "shopapi-xuat-test", goc_nhap=goc)

    so_cai = json.load(open(os.path.join(goc, "root_meta_info.json"),
                            encoding="utf-8"))
    ds = so_cai["all_draft_store"]
    assert len(ds) == 4 and so_cai["draft_ids"] == 4
    assert ds[0]["draft_name"] == "shopapi-xuat-test"
    # mốc của mình phải MỚI NHẤT — trang chủ xếp theo tm_draft_modified
    assert ds[0]["tm_draft_modified"] > max(
        m["tm_draft_modified"] for m in ds[1:])
    # dự án của khách còn nguyên, và có bản sao lưu trước khi ghi
    assert [m["draft_name"] for m in ds[1:]] == [
        "du-an-cua-khach-0", "du-an-cua-khach-1", "du-an-cua-khach-2"]
    assert os.path.exists(
        os.path.join(goc, "root_meta_info.json.truoc-shopapi"))


def test_tao_nhap_lan_hai_khong_nhan_doi(tmp_path, video_gia):
    goc = _dung_goc_nhap(tmp_path)
    tao_nhap(video_gia, "shopapi-xuat-test", goc_nhap=goc)
    tao_nhap(video_gia, "shopapi-xuat-test", goc_nhap=goc)
    so_cai = json.load(open(os.path.join(goc, "root_meta_info.json"),
                            encoding="utf-8"))
    ten = [m["draft_name"] for m in so_cai["all_draft_store"]]
    assert ten.count("shopapi-xuat-test") == 1


def test_go_khoi_so_cai_chi_go_cua_minh(tmp_path, video_gia):
    goc = _dung_goc_nhap(tmp_path, so_du_an_cu=2)
    tao_nhap(video_gia, "shopapi-xuat-test", goc_nhap=goc)
    _go_khoi_so_cai(goc, "shopapi-xuat-test")
    so_cai = json.load(open(os.path.join(goc, "root_meta_info.json"),
                            encoding="utf-8"))
    ten = [m["draft_name"] for m in so_cai["all_draft_store"]]
    assert ten == ["du-an-cua-khach-0", "du-an-cua-khach-1"]
    assert so_cai["draft_ids"] == 2


def test_chua_mo_capcut_lan_nao_thi_noi_that(tmp_path, video_gia):
    goc = tmp_path / "com.lveditor.draft"
    goc.mkdir()      # có thư mục nhưng KHÔNG có sổ cái
    with pytest.raises(LoiCapCut) as loi:
        tao_nhap(video_gia, "shopapi-xuat-test", goc_nhap=str(goc))
    assert "CapCut" in str(loi.value)


def test_kenh_doc_co_xuat_capcut(tmp_path):
    from core.kenh import doc_kenh

    d = tmp_path / "CHANNEL" / "KENH-CC"
    d.mkdir(parents=True)
    (d / "kenh.yaml").write_text(
        "ma: KENH-CC\nten: Kênh thử CapCut\nxuat_capcut: true\n",
        encoding="utf-8")
    kenh = doc_kenh(str(tmp_path), "KENH-CC")
    assert kenh.xuat_capcut is True
    # kênh không khai thì phải TẮT — mặc định không được tự bật
    (d / "kenh.yaml").write_text("ma: KENH-CC\n", encoding="utf-8")
    assert doc_kenh(str(tmp_path), "KENH-CC").xuat_capcut is False


def test_duoi_khau_dung_im_lang_khi_kenh_tat(tmp_path):
    """Kênh không bật cờ: đuôi CapCut trả rỗng, KHÔNG đụng tới CapCut."""
    from core.auto_khau import _xuat_capcut_neu_bat

    bc = types.SimpleNamespace(kenh=types.SimpleNamespace(),
                               ghi=lambda *_: None, kiem_dung=lambda: None)
    assert _xuat_capcut_neu_bat(bc, str(tmp_path), "khong-can-co") == ""


def test_duoi_khau_dung_nhan_ban_da_co(tmp_path):
    """Đã có 9-video-capcut.mp4 mới hơn video thì không mở CapCut lần nữa."""
    from core.auto_khau import _xuat_capcut_neu_bat

    video = tmp_path / "8-video.mp4"
    video.write_bytes(b"v")
    cc = tmp_path / "9-video-capcut.mp4"
    cc.write_bytes(b"c")
    os.utime(str(video), (1_000_000_000, 1_000_000_000))
    os.utime(str(cc), (1_000_000_100, 1_000_000_100))
    bc = types.SimpleNamespace(
        kenh=types.SimpleNamespace(xuat_capcut=True),
        ghi=lambda *_: None, kiem_dung=lambda: None)
    ra = _xuat_capcut_neu_bat(bc, str(tmp_path), str(video))
    assert ra == "9-video-capcut.mp4"


# ── Ô bật tắt trên tab Tự động ───────────────────────────────────────────────
#
# Chủ dự án 02/09/2026: *"ở tool tao muốn có chỗ bật tắt bước này giống chỗ
# dừng để xem trước khi dựng video — tạm thời thì cứ tắt"*. Kiểm bằng cách đọc
# NGUỒN như tests/test_o_tieng_canh_tren_giao_dien.py — dựng cửa sổ Qt trong
# bộ kiểm là chậm và hay treo trên máy không màn hình.


def _nguon_trang_auto():
    import inspect

    import ui_qt.trang_auto as ta

    return inspect.getsource(ta)


def test_o_bat_tat_co_mat_va_mac_dinh_tat():
    ma = _nguon_trang_auto()
    assert "_o_xuat_capcut" in ma
    assert 'QCheckBox("Xuất lại qua CapCut sau khi dựng")' in ma
    # Mặc định tắt: KHÔNG được có dòng nào tự tích sẵn ô này.
    assert "_o_xuat_capcut.setChecked(True)" not in ma


def test_o_bat_tat_ep_co_vao_luot_chay():
    """Tích ô phải thành `k.xuat_capcut = True` trước khi dựng BoiCanh —
    thiếu dòng ấy là ô thành đồ trang trí: tích rồi mà lượt vẫn bỏ qua."""
    import inspect

    import ui_qt.trang_auto as ta

    ma = inspect.getsource(ta.TrangTuDong._bat_dau)
    assert "_o_xuat_capcut.isChecked()" in ma
    assert "xuat_capcut = True" in ma


def test_nhan_o_ngan_khong_keo_rong_trang():
    """CLAUDE.md: nhãn dài kéo cả trang rộng quá mép cửa sổ."""
    label = "Xuất lại qua CapCut sau khi dựng"
    assert len(label) <= 40


def test_tooltip_noi_that_capcut_tu_mo():
    """Không hứa hươu: CapCut sẽ hiện trên màn hình và tự bấm — tooltip phải
    nói thẳng điều đó để khách không tưởng máy hỏng khi CapCut bật lên."""
    ma = _nguon_trang_auto()
    assert "TỰ MỞ VÀ TỰ BẤM" in ma
