"""Lời nhắc nói "viết bằng tiếng Nhật", không phải "viết bằng ja".

Chủ dự án, 25/08/2026: *"viết bằng ja thì phải rõ là viết bằng ngôn ngữ tiếng
Nhật"*. `<<NGON_NGU>>` là tên tiếng bằng tiếng Việt; `<<LANGUAGE>>` vẫn là mô
tả giọng văn của kênh như cũ.
"""

from __future__ import annotations

import os

from core.kenh import doc_kenh, ten_tieng

GOC = os.path.join(os.path.dirname(__file__), "..")


class TestTenTieng:
    def test_ma_quen(self):
        assert ten_tieng("ja") == "tiếng Nhật"
        assert ten_tieng("VI") == "tiếng Việt"
        assert ten_tieng("en-US") == "tiếng Anh"

    def test_ma_la_thi_tra_nguyen(self):
        assert ten_tieng("xx") == "xx"
        assert ten_tieng("") == ""


class TestPromptTL4:
    def test_prompt_viet_noi_ro_tieng(self):
        k = doc_kenh(GOC, "TL4-T7")
        assert "<<NGON_NGU>>" in k.prompt["2-viet.md"]
        assert "viết lại cho tôi" in k.prompt["2-viet.md"]
        assert "cho t " not in k.prompt["2-viet.md"]

    def test_khau_kich_ban_dien_o_NGON_NGU(self):
        with open(os.path.join(GOC, "core", "auto_khau.py"), encoding="utf-8") as t:
            chu = t.read()
        assert '"NGON_NGU": ten_tieng(k.ngon_ngu)' in chu
