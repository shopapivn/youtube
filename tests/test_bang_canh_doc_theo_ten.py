"""Sắp lại cột bảng cảnh cho NGƯỜI ĐỌC — 21/09/2026, chủ dự án: *"không thể edit
được vì đâu biết scene nào ở giây nào"*.

Mốc thời gian (`srt_start`/`srt_end`/`duration`) vốn đã có trong file, nhưng
chìm giữa 20+ cột đặt tên kỹ thuật (`prompt_json`, `media_id`, `status_vid`…).
Việc sửa: đưa cột NGƯỜI đọc/sửa lên đầu (mốc + lời đọc + hai cột thật sự sửa
được), thêm trang "Hướng dẫn" đứng đầu sổ, khoá hàng tiêu đề, nới cột — mà
KHÔNG được đổi TÊN cột nào, vì mọi bộ đọc trong tool tra cột theo tên.

Ba bài kiểm ở đây khoá đúng ba thứ đó:
1. Cột người cần đứng trước, giữ nguyên tên.
2. File CŨ (thứ tự cột trước 21/09/2026, khách đã có sẵn trên máy) vẫn phải
   nạp được ở mọi nơi đọc bảng cảnh — không nơi nào được đoán vị trí cột.
3. Trang "Hướng dẫn" mới thêm không được xen vào bất cứ chỗ nào đi tìm sheet
   `scenes` theo tên.

Không bài nào gọi mạng.
"""

from __future__ import annotations

import importlib.util
import os
import sys

import pytest

openpyxl = pytest.importorskip("openpyxl")

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Thứ tự cột TRƯỚC 21/09/2026 — dùng để dựng file "cũ" mô phỏng file khách đã
#: có sẵn trên máy trước khi tool đổi thứ tự. KHÔNG đổi tuple này theo mã
#: nguồn hiện tại — nó phải đứng yên, đại diện cho một file có thật trong quá
#: khứ, để bài kiểm còn nghĩa là "khả năng tương thích ngược".
COT_CANH_CU = ("scene_id", "srt_start", "srt_end", "duration", "planned_duration",
              "srt_text", "scene_kind", "subject_mode", "primary_subject",
              "primary_action", "visual_anchor", "must_not_show", "img_prompt",
              "prompt_json", "video_prompt", "img_path", "video_path",
              "status_img", "status_vid", "characters_used", "location_used",
              "reference_files", "media_id", "video_note", "segment_id")

SCENE_COLUMNS_CU = COT_CANH_CU + ("srt_text_vi",)

_DONG_CU = {
    "scene_id": 1, "srt_start": "00:00:00,000", "srt_end": "00:00:04,500",
    "duration": 4.5, "planned_duration": 4.5, "srt_text": "Ngay xua co ba chu heo con.",
    "scene_kind": "establish", "subject_mode": "single", "primary_subject": "heo con",
    "primary_action": "dung nhin", "visual_anchor": "can nha rom", "must_not_show": "",
    "img_prompt": "a piglet in a straw house", "prompt_json": "{}",
    "video_prompt": "slow push in", "img_path": "", "video_path": "",
    "status_img": "pending", "status_vid": "pending", "characters_used": "nv1",
    "location_used": "loc1", "reference_files": "nv1.png", "media_id": "",
    "video_note": "", "segment_id": 1, "srt_text_vi": "Ngày xưa có ba chú heo con.",
}


def _xlsx_cu(tmp_path, cot, them_hd=False):
    """Một file `.xlsx` với thứ tự cột CŨ — mô phỏng file khách đã có sẵn."""
    wb = openpyxl.Workbook()
    if them_hd:
        # File thật tool xuất ra hôm nay có thêm trang "Hướng dẫn" đứng đầu —
        # bài kiểm này dựng cả hai kiểu để chắc mọi bộ đọc bỏ qua đúng cách.
        hd = wb.active
        hd.title = "Hướng dẫn"
        hd.append(["Đây là trang hướng dẫn, không phải bảng cảnh."])
        ws = wb.create_sheet("scenes")
    else:
        ws = wb.active
        ws.title = "scenes"
    ws.append(list(cot))
    ws.append([_DONG_CU.get(c, "") for c in cot])
    duong = str(tmp_path / "bang-canh-cu.xlsx")
    wb.save(duong)
    return duong


def _nap_run_py():
    duong = os.path.join(GOC, "tool-catalog", "prompt.workbook", "run.py")
    spec = importlib.util.spec_from_file_location("prompt_workbook_run_thu_tu", duong)
    mo_dun = importlib.util.module_from_spec(spec)
    sys.modules["prompt_workbook_run_thu_tu"] = mo_dun
    spec.loader.exec_module(mo_dun)
    return mo_dun


class TestThuTuCotNguoiDocTruoc:
    """`scene_id, srt_start, srt_end, duration, srt_text(_vi), img_prompt,
    video_prompt` phải đứng đầu — đúng cột người xem/sửa cần, không cột nào
    đổi TÊN so với bản cũ (chỉ đổi vị trí)."""

    def test_auto_khau_cot_canh(self):
        from core.auto_khau import COT_CANH

        assert COT_CANH[:7] == (
            "scene_id", "srt_start", "srt_end", "duration", "srt_text",
            "img_prompt", "video_prompt")
        # Không mất, không thêm cột nào — chỉ đổi chỗ.
        assert set(COT_CANH) == set(COT_CANH_CU)
        assert len(COT_CANH) == len(COT_CANH_CU)

    def test_workbook_tool_scene_columns(self):
        wb = _nap_run_py()
        assert list(wb.SCENE_COLUMNS[:8]) == [
            "scene_id", "srt_start", "srt_end", "duration", "srt_text",
            "srt_text_vi", "img_prompt", "video_prompt"]
        assert set(wb.SCENE_COLUMNS) == set(SCENE_COLUMNS_CU)
        assert len(wb.SCENE_COLUMNS) == len(SCENE_COLUMNS_CU)


class TestTrangHuongDanDauSo:
    """Sheet "Hướng dẫn" phải là tab ĐẦU TIÊN của cả hai workbook tool ghi ra,
    và không được làm bất cứ bộ đọc nào lẫn nó với sheet `scenes`."""

    def test_auto_khau_viet_xlsx(self, tmp_path):
        from types import SimpleNamespace

        from core.auto_khau import _viet_xlsx

        k = SimpleNamespace(style={"default_character_prompt": "a cat", "reference_lock": ""})
        duong = str(tmp_path / "4-canh.xlsx")
        _viet_xlsx(duong, [{"scene_id": 1, "img_prompt": "x", "video_prompt": "y",
                            "srt_start": "0", "srt_end": "1"}], k)
        wb = openpyxl.load_workbook(duong)
        assert wb.sheetnames[0] == "Hướng dẫn"
        assert wb.sheetnames[1] == "scenes"
        assert wb["scenes"].freeze_panes == "A2"

    def test_workbook_tool_render_workbook(self, tmp_path):
        wb_tool = _nap_run_py()
        manifest = {"scenes": [{"scene_id": 1, "srt_start": "00:00:00,000",
                                "srt_end": "00:00:02,000", "duration": 2.0,
                                "srt_text": "cau mot", "img_prompt": "a",
                                "video_prompt": "b"}],
                    "characters": [], "locations": [], "story": {},
                    "director_plan": [], "title": "", "thumb_text": "",
                    "thumbnails": [], "music": []}
        duong = tmp_path / "scene-prompts.xlsx"
        wb_tool.render_workbook(duong, manifest)
        wb = openpyxl.load_workbook(str(duong))
        assert wb.sheetnames[0] == "Hướng dẫn"
        assert wb.sheetnames[1] == "scenes"
        assert wb["scenes"].freeze_panes == "A2"
        # Trang hướng dẫn nói tiếng người, không phải tên cột kỹ thuật.
        chu = "\n".join(str(o.value or "") for hang in wb["Hướng dẫn"].iter_rows() for o in hang)
        assert "img_prompt" in chu and "video_prompt" in chu
        assert "srt_start" in chu


class TestTuongThichNguoc:
    """File cũ (thứ tự cột trước 21/09/2026) phải nạp được ở MỌI nơi đọc bảng
    cảnh — mọi bộ đọc tra cột theo TÊN, không theo vị trí."""

    @pytest.mark.parametrize("them_hd", [False, True],
                             ids=["file-cu-tran", "file-cu-co-huong-dan"])
    def test_dung_video_doc_bang_canh(self, tmp_path, them_hd):
        from core.dung_video import doc_bang_canh

        duong = _xlsx_cu(tmp_path, COT_CANH_CU, them_hd=them_hd)
        canh = doc_bang_canh(duong)
        assert canh and canh[0]["so"] == 1
        assert canh[0]["bat_dau"] == pytest.approx(0.0)
        assert canh[0]["ket_thuc"] == pytest.approx(4.5)

    @pytest.mark.parametrize("them_hd", [False, True],
                             ids=["file-cu-tran", "file-cu-co-huong-dan"])
    def test_moc_canh_doc_canh_co_chu(self, tmp_path, them_hd):
        from core.moc_canh import doc_canh_co_chu

        duong = _xlsx_cu(tmp_path, COT_CANH_CU, them_hd=them_hd)
        canh = doc_canh_co_chu(duong)
        assert canh and canh[0]["so"] == 1
        assert "heo con" in canh[0]["chu"]

    def test_nap_san_kiem_bang_canh_chap_nhan_file_cu(self, tmp_path):
        from core.nap_san import kiem_file

        duong = _xlsx_cu(tmp_path, COT_CANH_CU)
        kiem_file("bang-canh", duong)  # không ném là qua bài

    def test_prompt_visuals_canh_de_xem(self, tmp_path):
        from core.prompt_visuals import canh_de_xem

        duong = _xlsx_cu(tmp_path, SCENE_COLUMNS_CU)
        wb = openpyxl.load_workbook(duong, read_only=True, data_only=True)
        try:
            hang = [list(r) for r in wb["scenes"].iter_rows(values_only=True)]
        finally:
            wb.close()
        ra = canh_de_xem(hang)
        assert ra and ra[0]["scene_id"] == 1
        assert "heo con" in ra[0]["srt_text"]
        assert ra[0]["img_prompt"] == "a piglet in a straw house"
