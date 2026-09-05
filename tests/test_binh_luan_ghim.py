"""Bình luận GHIM phải được sinh ra, và phải đi tới tận tay người đăng.

Vì sao thêm khâu này (đo trên TL4-T7 ngày 05/09/2026):

* cả kênh có **3 người xem cũ trong 28 ngày** — 99% là người mới, gần như không ai quay lại;
* video mới nhất: **0 bình luận, 0 lượt thích**;
* mọi kịch bản của kênh ĐÃ hỏi một câu ở cuối video, nhưng câu ấy chỉ nằm trong lời đọc —
  không ai thấy nó ở khung bình luận.

Bình luận ghim là chỗ rẻ nhất để mở lời. Nhưng nó chỉ ăn khi nhắc lại ĐÚNG câu hỏi kịch bản
vừa hỏi, và tự trả lời trước một câu — một câu hỏi ghim không ai trả lời thì đọc như lời nhờ vả.

Hai bài dưới canh hai chỗ dễ hỏng ÂM THẦM: lời nhắc bị nhồi cho tới lúc mọi bản ra cùng một
khuôn (đã xảy ra với `2-viet.md`: 232 → 7.156 ký tự), và tệp sinh ra rồi nằm lại trong thư mục
lượt, không bao giờ tới tay người đăng.
"""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ban_giao_dang, kenh as kenh_mod  # noqa: E402

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KHUON = [
    os.path.join(GOC, "CHANNEL", "TL4-T7", "prompt"),
    os.path.join(GOC, "CHANNEL", "_KHUON", "nganh", "tam-ly", "prompt"),
    os.path.join(GOC, "CHANNEL", "_MAU-GON", "prompt"),
]


def test_khau_binh_luan_duoc_khai_bao():
    ten = [t for t, _ in kenh_mod.BUOC_PROMPT]
    assert "6b-binh-luan.md" in ten, "khâu bình luận ghim chưa được khai báo"
    # Phải nằm SAU khâu SEO: cả hai đọc kịch bản đã chốt, và bình luận nhắc lại
    # câu hỏi mà mô tả cũng nhắc — đặt trước là hai bên nói hai câu khác nhau.
    assert ten.index("6b-binh-luan.md") > ten.index("6-seo.md")


@pytest.mark.parametrize("thu_muc", KHUON)
def test_moi_khuon_deu_co_loi_nhac(thu_muc):
    """Sửa một khuôn mà quên khuôn kia thì kênh nhân bản sau này mất khâu — im lặng."""
    assert os.path.isfile(os.path.join(thu_muc, "6b-binh-luan.md")), \
        "khuôn này thiếu 6b-binh-luan.md"


@pytest.mark.parametrize("thu_muc", KHUON)
def test_loi_nhac_binh_luan_phai_GON(thu_muc):
    """Cùng luật với lời nhắc viết: ràng buộc CƠ HỌC thôi, đừng dạy cách viết hay.

    `2-viet.md` từng phình 232 → 7.156 ký tự và kéo giữ chân từ 59% xuống 26%. Bình luận ghim
    chỉ dài 2–5 dòng; một lời nhắc dài hơn thứ nó sinh ra là dấu hiệu đang ép, không phải đang
    ràng buộc.
    """
    chu = io.open(os.path.join(thu_muc, "6b-binh-luan.md"), encoding="utf-8").read()
    assert len(chu) <= 900, f"lời nhắc {len(chu)} ký tự — quá 900, đang bị nhồi"


@pytest.mark.parametrize("thu_muc", KHUON)
def test_loi_nhac_dung_DOAN_CUOI_kich_ban(thu_muc):
    """Câu mời bình luận nằm ở CUỐI kịch bản. Đưa đoạn đầu vào là hỏi lạc câu."""
    chu = io.open(os.path.join(thu_muc, "6b-binh-luan.md"), encoding="utf-8").read()
    assert "<<SCRIPT_ENDING>>" in chu, "không nhận đoạn cuối kịch bản"
    assert "<<SCRIPT_OPENING>>" not in chu, "lấy nhầm đoạn mở đầu"
    assert "<<LANGUAGE>>" in chu, "không khoá ngôn ngữ — sẽ ra tiếng Anh"


def test_khau_sinh_ra_tep_binh_luan():
    """Có lời nhắc mà không ai gọi thì khâu không tồn tại."""
    nen = io.open(os.path.join(GOC, "core", "auto_khau.py"), encoding="utf-8").read()
    assert '"6b-binh-luan.md"' in nen, "chưa gọi lời nhắc bình luận"
    assert '"1-binh-luan.txt"' in nen, "chưa ghi ra tệp"
    assert "SCRIPT_ENDING=ban_nhap[-" in nen, "phải đưa ĐOẠN CUỐI kịch bản vào"


def _dung_luot(tmp_path, co_binh_luan=True):
    d = tmp_path / "luot"
    (d / "7-thumbnail").mkdir(parents=True)
    (d / ban_giao_dang.TEP_VIDEO).write_bytes(b"mp4")
    (d / ban_giao_dang.TEP_SRT).write_text("1\n", encoding="utf-8")
    (d / "7-thumbnail" / "CHON-a.jpg").write_bytes(b"jpg")
    (d / "1-tieu-de.txt").write_text("TITLE: Tiêu đề thật\n", encoding="utf-8")
    if co_binh_luan:
        (d / ban_giao_dang.TEP_BINH_LUAN).write_text(
            "どの場面が、一番あなたに近かったですか。\n私は、玄関の足音でした。",
            encoding="utf-8")
    return d


def test_binh_luan_di_theo_goi_ban_giao(tmp_path):
    """Sinh ra rồi nằm lại trong thư mục lượt thì người đăng không bao giờ thấy."""
    d = _dung_luot(tmp_path)
    dich = ban_giao_dang.xuat_goi(str(d), str(tmp_path / "done"), "TL4-T7-0009")
    p = os.path.join(dich, ban_giao_dang.TEP_BINH_LUAN)
    assert os.path.isfile(p), "bình luận ghim không đi theo gói"
    assert "玄関の足音" in io.open(p, encoding="utf-8").read()
    assert ban_giao_dang.doc_gioi_thieu(str(d))["binh_luan"].startswith("どの場面")


def test_thieu_binh_luan_thi_VAN_ban_giao_duoc(tmp_path):
    """Khâu này là thêm vào, không được biến thành cửa chặn video đã dựng xong."""
    d = _dung_luot(tmp_path, co_binh_luan=False)
    assert ban_giao_dang.kiem_du_bo(str(d)) == []
    dich = ban_giao_dang.xuat_goi(str(d), str(tmp_path / "done"), "TL4-T7-0009")
    assert os.path.isfile(os.path.join(dich, ban_giao_dang.TEP_VIDEO))
    assert ban_giao_dang.doc_gioi_thieu(str(d))["binh_luan"] == ""
