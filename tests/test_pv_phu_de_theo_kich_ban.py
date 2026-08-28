# -*- coding: utf-8 -*-
"""Tab Prompt Visuals: có kịch bản thì phụ đề phải mang chữ của kịch bản.

Đây là chỗ **đắt nhất** trong cả tool để một tệp `.srt` sai chữ đi qua. Dây
chuyền là: nghe mp3 → `.srt` → cắt cảnh → AI viết prompt từng cảnh → khách trả
tiền ảnh và clip cho từng cảnh ấy. Chữ sai ở bước đầu không dừng lại ở phụ đề:
nó thành lời nhắc sai, rồi thành ảnh sai, và tiền đã tiêu rồi mới nhìn ra.

Tab này vốn đã nhận file kịch bản `.txt`, nhưng trước 28/08/2026 nó chỉ đưa
kịch bản cho **AI viết prompt đọc tham khảo** (`context.script`), còn tệp `.srt`
vẫn chép nguyên lời máy nghe. Hai bài dưới khoá cả hai đầu dây lại.
"""

from __future__ import annotations

import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.phu_de import do_khop_voi_kich_ban, doc_srt  # noqa: E402
from core.prompt_visuals import dung_workflow  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KICH_BAN = ("Năm 1258, quân Nguyên Mông lần đầu tràn qua ải Bắc. "
            "Trần Thủ Độ nói một câu mà cả triều đình còn nhắc mãi.")

#: Đúng kiểu máy nghe nhầm: nghe ra chữ khác hẳn, mốc thời gian thì vẫn đúng.
NGHE_NHAM = "Năm một nghìn hai trăm năm mươi tám quân nguyên mong chần thu đô"


def _nap_run_py():
    """Nạp `tool-catalog/transcribe.local/run.py` như một module.

    Nạp thẳng tệp thật chứ không chép lại logic: bài kiểm phải chạy đúng đoạn
    mã mà runtime chạy, nếu không nó chỉ kiểm chính nó.
    """
    duong = os.path.join(GOC, "tool-catalog", "transcribe.local", "run.py")
    spec = importlib.util.spec_from_file_location("transcribe_local_run", duong)
    mo_dun = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mo_dun)
    return mo_dun


class _Tu:
    def __init__(self, chu, start, end):
        self.word, self.start, self.end = chu, start, end


class _Doan:
    def __init__(self, chu, start, end, words=None):
        self.text, self.start, self.end = chu, start, end
        self.words = words or []


def _bo_nghe_gia(chu: str):
    tu = chu.split()

    def transcribe_fn(_audio, **_k):
        moc = [_Tu(t, i * 0.5, (i + 1) * 0.5) for i, t in enumerate(tu)]
        return [_Doan(chu, 0.0, len(tu) * 0.5, moc)], {"language": "vi"}

    return transcribe_fn


def _yeu_cau(tmp_path, **cau_hinh):
    mp3 = tmp_path / "giong.mp3"
    mp3.write_bytes(b"khong phai mp3 that, bo nghe da bi thay")
    cau_hinh.setdefault("model", "small")
    cau_hinh.setdefault("language", "vi")
    return {"inputs": {"audio": {"path": str(mp3)}},
            "config": cau_hinh,
            "workspace": str(tmp_path / "ws")}


class TestBuocNghe:

    def test_co_kich_ban_thi_srt_mang_chu_kich_ban(self, tmp_path):
        run = _nap_run_py()
        ra = run.handle(_yeu_cau(tmp_path, script=KICH_BAN),
                        transcribe_fn=_bo_nghe_gia(NGHE_NHAM))

        srt = os.path.join(str(tmp_path / "ws"), "narration.srt")
        cau = doc_srt(open(srt, encoding="utf-8").read())
        assert cau, "phải ra được tệp .srt đọc lại được"
        assert do_khop_voi_kich_ban(cau, KICH_BAN) == 1.0
        assert ra["subtitles"]["metadata"]["text_source"] == "kich-ban"
        gop = " ".join(c.chu for c in cau)
        assert "Trần Thủ Độ" in gop, "tên riêng phải đúng như kịch bản"
        assert "chần thu đô" not in gop

    def test_khong_co_kich_ban_thi_van_chay_nhu_cu(self, tmp_path):
        """Không có kịch bản thì lời máy nghe là thứ duy nhất còn lại."""
        run = _nap_run_py()
        ra = run.handle(_yeu_cau(tmp_path),
                        transcribe_fn=_bo_nghe_gia(NGHE_NHAM))

        srt = os.path.join(str(tmp_path / "ws"), "narration.srt")
        gop = " ".join(c.chu for c in doc_srt(open(srt, encoding="utf-8").read()))
        assert "chần thu đô" in gop
        assert ra["subtitles"]["metadata"]["text_source"] == "may-nghe"


class TestToKhaiWorkflow:

    def test_kich_ban_di_ca_hai_duong(self):
        """Một tệp `.txt`, hai việc: ép khớp phụ đề, và cho AI đọc hiểu."""
        wf = dung_workflow("art:1", kich_ban=KICH_BAN,
                           ma_artifact_context="art:ctx")
        nghe = next(n for n in wf["nodes"] if n["tool_id"] == "transcribe.local")
        assert nghe["config"]["script"] == KICH_BAN

    def test_khong_co_kich_ban_thi_khong_moc_them_khoa_thua(self):
        wf = dung_workflow("art:1")
        nghe = next(n for n in wf["nodes"] if n["tool_id"] == "transcribe.local")
        assert "script" not in nghe["config"], (
            "tool.json khai config đóng (additionalProperties: false) — nhét "
            "một khoá rỗng vào là đổi cả chữ ký lượt chạy mà không được gì")
