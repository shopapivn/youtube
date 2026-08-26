"""Kênh để ĐỘ DÀI TỰ DO (`do_dai_tu_do: true`): không mục tiêu phút/ký tự, không nắn,
không chấm lệch — chỉ còn sàn tuyệt đối chống bản rỗng / AI hỏi lại.

Chủ dự án 25/08/2026, kênh truyện cổ tích: "không cần giới hạn thời gian hay ký tự ở prompt".
"""
import os
from types import SimpleNamespace

import pytest

from core import auto_khau
from core.auto_khau import (SAN_KICH_BAN_TU_DO, _kiem_kich_ban_dung_duoc, _lech,
                            _muc_tieu_do_dai, _nan_do_dai)
from core.kenh import Kenh, doc_kenh


def test_doc_co_do_dai_tu_do(tmp_path):
    d = tmp_path / "CHANNEL" / "x"
    d.mkdir(parents=True)
    (d / "kenh.yaml").write_text("ma: x\ndo_dai_tu_do: true\nphut_muc_tieu: 8\n", encoding="utf-8")
    k = doc_kenh(str(tmp_path), "x")
    assert k.do_dai_tu_do is True
    assert _muc_tieu_do_dai(k, "tư liệu dài", 600) == 0
    # Kênh không khai: y như cũ.
    assert not Kenh().do_dai_tu_do
    assert _muc_tieu_do_dai(Kenh(phut_muc_tieu=8, ky_tu_moi_phut=800), "", 0) == 6400


def test_lech_bang_khong_khi_tu_do():
    assert _lech("x" * 5000, 0) == 0.0
    assert _lech("x" * 5000, 10000) == 0.5


def test_san_tuyet_doi_van_chan_ban_rong(tmp_path):
    kb = tmp_path / "1-kich-ban.txt"
    kb.write_text("Bạn có thể gửi lại kịch bản không?", encoding="utf-8")
    with pytest.raises(Exception):
        _kiem_kich_ban_dung_duoc(40, 0, str(kb), tu_do=True)
    assert not kb.exists() and (tmp_path / "1-kich-ban-KHONG-DUNG-DUOC.txt").exists()
    _kiem_kich_ban_dung_duoc(SAN_KICH_BAN_TU_DO + 1, 0, tu_do=True)   # bài thật thì qua
    _kiem_kich_ban_dung_duoc(20000, 0, tu_do=True)                    # dài bao nhiêu cũng qua
    _kiem_kich_ban_dung_duoc(40, 0)                                   # không biết mục tiêu, không tự do: như cũ, không chặn


def test_khong_nan_do_dai_khi_tu_do():
    nhat_ky = []
    bc = SimpleNamespace(ghi=nhat_ky.append)
    k = SimpleNamespace(prompt={"4-do-dai.md": "nắn về <<CHARS>>"}, ky_tu_muc_tieu=6400)
    ra = _nan_do_dai(bc, SimpleNamespace(thu_muc="."), k, {}, "bài gốc", 0)
    assert ra == "bài gốc" and any("tự do" in d for d in nhat_ky)


def test_kenh_story_3d_de_tu_do():
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    k = doc_kenh(goc, "story-3d")
    assert k.do_dai_tu_do
    assert "4-do-dai.md" not in k.prompt
    assert "<<PHUT>>" not in k.prompt.get("2-viet.md", "") and "<<CHARS>>" not in k.prompt.get("2-viet.md", "")
    assert "<<PHUT>>" not in k.prompt.get("2b-cham.md", "")


def test_token_viet_theo_do_dai_nguon():
    from core.auto_khau import TOKEN_VIET_SAN, TOKEN_VIET_TRAN, _token_viet
    assert _token_viet(0, 0) == TOKEN_VIET_SAN
    assert _token_viet(8000, 6400) == TOKEN_VIET_SAN          # truyện ngắn: sàn cũ, không đổi
    assert _token_viet(30000, 0) == int(30000 * 1.3 / 2)      # nguồn 30k ký tự ≈ 36 phút → 19.500 token
    assert _token_viet(0, 30000) == int(30000 * 1.3 / 2)      # hoặc theo mục tiêu phút của kênh thường
    assert _token_viet(200000, 0) == TOKEN_VIET_TRAN
