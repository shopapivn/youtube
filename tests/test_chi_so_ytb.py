"""Bộ đọc số liệu YouTube Studio — kiểm trên dữ liệu dựng sẵn, không cần Chrome.

Ba thứ bài này canh, đều là chỗ đã hỏng thật trong lúc làm:

1. **Tiện ích đi kèm phải còn đủ tệp.** Người dùng bấm "Lưu tiện ích ra máy…" rồi chọn
   thư mục đó trong Chrome. Thiếu một tệp là Chrome từ chối nạp, và họ không có cách nào
   biết vì sao.
2. **`_thong-tin.json` phải được ghép vào.** Tiêu đề, thời lượng và mốc giờ không nằm
   trong gói nào của Studio nên tiện ích ghi riêng. Quên bước ghép thì bảng hiện ra toàn
   mã video — vẫn "chạy", chỉ là không ai đọc nổi.
3. **Báo cáo cho AI phải kèm chú giải cột.** Nó được dán vào ChatGPT, nơi không ai giải
   thích "AVD" hay "pool" là gì. Bảng số trần thì mô hình đoán, và đoán sai.
"""

import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chi_so_ytb as cs  # noqa: E402


def test_tien_ich_di_kem_con_du_tep():
    goc = cs.thu_muc_extension()
    assert os.path.isdir(goc), "thiếu hẳn thư mục tiện ích đi kèm"
    for ten in ("manifest.json", "background.js", "inject.js", "content.js",
                "popup.html", "popup.js", "nghi.html", "nghi.js"):
        assert os.path.exists(os.path.join(goc, ten)), f"tiện ích thiếu {ten}"


def test_manifest_hop_le_va_khong_tro_ve_may_chu_noi_bo():
    d = json.load(io.open(os.path.join(cs.thu_muc_extension(), "manifest.json"),
                          encoding="utf-8"))
    assert d.get("manifest_version") == 3
    assert d.get("name") and d.get("version")
    # Bản giao cho người dùng KHÔNG được trỏ sẵn vào máy chủ nội bộ nào: họ không có
    # máy đó, và mỗi gói số liệu sẽ mất vài giây chờ hết giờ trước khi rơi về đĩa.
    nen = io.open(os.path.join(cs.thu_muc_extension(), "background.js"),
                  encoding="utf-8").read()
    assert "const HOST_MAC_DINH = '';" in nen, "mặc định phải là lưu vào máy người dùng"


def _dung_du_lieu(tmp_path, co_thong_tin=True):
    """Dựng một bản chụp tối thiểu đúng hình dạng tiện ích ghi ra."""
    snap = tmp_path / "UCkenh" / "video123abc" / "24h"
    (snap / "raw").mkdir(parents=True)
    tq = {"video_id": "video123abc", "impressions": 1000, "ctr": 4.5, "views": 45,
          "unique_viewers": 40, "avd_giay": 300, "watch_hours": 3.75, "subs": 2}
    (snap / "tong-quan.json").write_text(json.dumps(tq, ensure_ascii=False), encoding="utf-8")
    if co_thong_tin:
        tt = {"kenh": "UCkenh", "id": "video123abc", "label": "24h",
              "tieu_de": "Tiêu đề thật của video", "thoi_luong": 900, "gio": 24,
              "ngay_dang": "2026-08-20T10:00:00.000Z"}
        (snap / "_thong-tin.json").write_text(json.dumps(tt, ensure_ascii=False), encoding="utf-8")
    return snap


def test_ghep_thong_tin_vao_ban_chup(tmp_path):
    _dung_du_lieu(tmp_path)
    bg = cs.doc_kenh("UCkenh", goc=str(tmp_path))
    assert len(bg) == 1
    b = bg[0]
    assert b.tieu_de == "Tiêu đề thật của video", "quên ghép _thong-tin.json"
    assert b.thoi_luong_giay == 900
    assert b.ngay_dang == "2026-08-20"
    assert b.moc_gio == 24
    # % độ dài suy ra được từ thời lượng, không cần Studio nói
    assert b.avd_pct == pytest.approx(33.3, abs=0.2)


def test_thieu_thong_tin_thi_van_doc_duoc_so(tmp_path):
    """Mất `_thong-tin.json` là mất tên video, KHÔNG được mất luôn số liệu."""
    _dung_du_lieu(tmp_path, co_thong_tin=False)
    bg = cs.doc_kenh("UCkenh", goc=str(tmp_path))
    assert len(bg) == 1
    assert bg[0].impressions == 1000
    assert bg[0].views == 45


def test_bao_cao_cho_ai_co_chu_giai_va_so_that(tmp_path):
    _dung_du_lieu(tmp_path)
    bg = cs.doc_kenh("UCkenh", goc=str(tmp_path))
    vb = cs.bao_cao_cho_ai(bg, "UCkenh")
    for phai_co in ("Ý NGHĨA CÁC CỘT", "Lượt hiển thị", "Tỷ lệ bấm", "Mốc"):
        assert phai_co in vb, f"báo cáo thiếu {phai_co!r}"
    assert "Tiêu đề thật của video" in vb
    assert "1,000" in vb, "số lượt hiển thị phải hiện ra"
    assert vb.rstrip().endswith("?"), "phải kết bằng câu hỏi để người dùng gửi đi là hỏi được luôn"


def test_khong_co_du_lieu_thi_noi_ro_chu_khong_ra_bang_rong():
    vb = cs.bao_cao_cho_ai([], "kenh")
    assert "Chưa có dữ liệu" in vb


def test_liet_ke_kenh_bo_qua_thu_muc_he_thong(tmp_path):
    (tmp_path / "UCthat").mkdir()
    (tmp_path / "_tam").mkdir()
    assert cs.liet_ke_kenh(str(tmp_path)) == ["UCthat"]
