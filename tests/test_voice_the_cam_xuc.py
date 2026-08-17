"""Thẻ cảm xúc cho **một mẻ việc đọc** — đường của tab Voice.

Tab Voice khác tab Tự động: nó dựng sẵn danh sách việc rồi mới chèn thẻ vào
từng việc. Bộ kiểm của tab Tự động không chạm tới đường này.

Cố ý **không dựng widget Qt** ở đây. Dựng Qt trong bài kiểm thì chết câm —
pytest không in nổi một dòng, mã thoát 0 — và đã dính đúng cái đó một lần hôm
nay ở tab Cài đặt. Nên vòng lặp thật nằm ở `core.the_cam_xuc.chen_the_hang_loat`
và bài kiểm gọi thẳng vào đó; phần còn lại của widget chỉ là dựng hàm gọi AI,
được chốt bằng bài đọc mã ở cuối tệp.
"""

from __future__ import annotations

import os

from core.jobs import JobSpec
from core.pricing import KIND_TTS
from core.the_cam_xuc import chen_the_hang_loat, kiem_the

BAI = "Ngay hom do troi mua rat to. Ai cung nghi chuyen se khac di."


def _viec(chu=BAI):
    return JobSpec(kind=KIND_TTS, content=chu, params={"voice_id": "x"})


class TestChenHangLoat:
    def test_chen_cho_tung_viec_trong_me(self):
        me = [_viec(), _viec(), _viec()]
        assert chen_the_hang_loat(me, lambda _l: "[sighs] " + BAI) == 3
        assert all("[sighs]" in v.content for v in me)
        assert all(kiem_the(BAI, v.content) for v in me)

    def test_AI_sua_chu_thi_viec_do_giu_ban_goc(self):
        """Cùng cái chốt với tab Tự động — không được lọt qua đường này."""
        me = [_viec()]
        chen_the_hang_loat(
            me, lambda _l: "[sighs] " + BAI.replace("rat to", "vo cung lon"))
        assert me[0].content == BAI

    def test_mot_viec_hong_khong_keo_ca_me_xuong(self):
        dem = {"n": 0}

        def ai(_l):
            dem["n"] += 1
            if dem["n"] == 1:
                raise RuntimeError("mang dut giua chung")
            return "[sighs] " + BAI

        me = [_viec(), _viec()]
        chen_the_hang_loat(me, ai)
        assert me[0].content == BAI, "việc hỏng phải giữ bản gốc"
        assert "[sighs]" in me[1].content, "việc sau vẫn phải được chèn"

    def test_viec_rong_thi_bo_qua(self):
        me = [_viec("   ")]
        assert chen_the_hang_loat(me, lambda _l: "[sighs] x") == 0
        assert me[0].content == "   "

    def test_me_rong_thi_khong_ne_loi(self):
        assert chen_the_hang_loat([], lambda _l: "x") == 0
        assert chen_the_hang_loat(None, lambda _l: "x") == 0


class TestNoiVaoTabVoice:
    """Đọc mã — phần duy nhất của tab không kiểm được bằng cách gọi hàm."""

    def _doc(self):
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "ui_qt", "trang_voice.py"),
                  encoding="utf-8") as tep:
            return tep.read()

    def test_chen_the_o_luong_nen(self):
        """Gọi mạng ở luồng vẽ là cửa sổ đứng hình cả phút."""
        chu = self._doc()
        khuc = chu[chu.index("def _chay_voi_the"):]
        khuc = khuc[:khuc.index("def _chen_the")]
        assert "run_bg" in khuc, "phải chèn thẻ ở luồng nền"

    def test_tat_thi_di_thang_khong_qua_luong_nen(self):
        """Tắt tính năng thì không được tốn thêm một nhịp nào."""
        chu = self._doc()
        khuc = chu[chu.index("def _chay_voi_the"):]
        khuc = khuc[:khuc.index("def _chen_the")]
        assert khuc.index("if not bat:") < khuc.index("run_bg")

    def test_chen_hong_van_ban_viec_di(self):
        """Chèn thẻ hỏng không được nuốt mất cả mẻ đọc của khách."""
        chu = self._doc()
        khuc = chu[chu.index("def _chay_voi_the"):]
        khuc = khuc[:khuc.index("def _chen_the")]
        assert "on_err" in khuc, "hỏng thì vẫn phải bắn việc đi"

    def test_dung_vong_lap_chung_o_core(self):
        assert "chen_the_hang_loat" in self._doc()
