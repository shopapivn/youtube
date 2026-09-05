"""Lớp LUẬT CỨNG của khâu gán tuyến — chạy bằng mã, không tốn một lượt gọi nào.

Vì sao cần (đo trên sổ TL4-T7 ngày 05/09/2026, 218 dòng mang nhãn "sống lệch nhịp số đông"):

* **41 dòng có 雑学 trong tiêu đề hoặc tên kênh** — sổ tay kênh xếp 雑学 vào danh sách LOẠI
  TRỪ ("dính là loại"), và pool 雑学 chính là nhóm lệch ngách đã kéo CTR video 1 xuống.
* **17 dòng mang mốc tuổi** (年齢を重ねると · 中年以降 · 60代 · 人生後半…) — `tuyen.csv` phân xử
  rõ: *"lấy TUỔI TÁC làm nhân vật chính thì thuộc tệp trung niên"*.

Cả hai luật ấy ĐÃ nằm trong lời nhắc (cột "Từ khoá nhận biết" đi thẳng vào `dau_hieu`). Model
có luật trong tay mà vẫn vi phạm — nên thứ cần thêm không phải chữ, mà là một lớp kiểm bằng mã
đứng SAU model. Hai lần chọn nhầm ứng viên V8 trong một buổi đều vì tin nhãn máy gán.

Giới hạn ghi thẳng ở đây: lớp này chỉ bắt được lỗi CÓ DẤU HIỆU TRONG CHỮ. Lỗi nghĩa — như
「電話が鳴ると緊張する人」 (một triệu chứng lo âu, không phải một lối sống khác số đông) — không có
dấu hiệu nào để bắt bằng mã; bài cuối cùng ghi nhận đúng giới hạn đó để không ai tưởng đã xong.
"""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import doi_thu_kenh as so  # noqa: E402
from core import phan_tuyen as pt  # noqa: E402

LECH = pt.MA_LECH_NHIP
TN = pt.MA_TRUNG_NIEN
CO = {LECH, TN, "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao"}


@pytest.mark.parametrize("tieu_de, kenh", [
    ("【雑学】一匹狼が向いている人の特徴", "人の本音研究所"),
    ("実は1960年代生まれに共通する「5つの力」", "おもしろ雑学ちゃんねる"),   # 雑学 ở tên kênh
    ("【漫画】一瞬で縁が切れる！絶対に言ってはいけないこと7選", "x"),
])
def test_tu_loai_tru_thi_ra_khac(tieu_de, kenh):
    assert pt.ap_luat_cung(tieu_de, kenh, LECH, CO) == pt.MA_KHAC


@pytest.mark.parametrize("tieu_de", [
    "【心理学】年齢を重ねると「友達がいなくても大丈夫」な理由｜成熟した脳の真実",
    "中年以降、友人がいなくても大丈夫な心理学的理由",
    "60代がお金をかけずに1人で楽しめる「最高の趣味」9選",
    "人生の後半で成功を収める理由",
])
def test_moc_tuoi_tren_tuyen_lech_nhip_thi_sang_trung_nien(tieu_de):
    """`tuyen.csv`: cùng nói "ở một mình" nhưng lấy tuổi tác làm nhân vật chính → trung niên."""
    assert pt.ap_luat_cung(tieu_de, "ひととき心理学", LECH, CO) == TN


def test_moc_tuoi_ma_so_khong_co_tuyen_trung_nien_thi_ra_khac():
    """Không được bịa mã: thiếu tuyến đích thì trả 'khác' chứ không giữ nhãn sai."""
    assert pt.ap_luat_cung("中年以降、友人がいなくても大丈夫な理由", "x", LECH, {LECH}) == pt.MA_KHAC


@pytest.mark.parametrize("tieu_de, ma", [
    ("【心理学】SNSをしない人に隠された「恐ろしい特徴」｜SNSをやらない人が幸福であり続ける理由", LECH),
    ("一人でいるのが好きな人の多くは、「こんな」子供時代を過ごしてきました", LECH),   # 子供時代 ≠ mốc tuổi người xem
    ("家がずっと綺麗な人に共通する「特別な能力」とは？", "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao"),
    ("なぜか部屋が汚くなる人の「恐ろしい特徴」", ""),                                  # ô trống giữ trống
])
def test_khong_dinh_luat_thi_giu_nguyen(tieu_de, ma):
    assert pt.ap_luat_cung(tieu_de, "ひととき心理学", ma, CO) == ma


@pytest.mark.parametrize("tieu_de", [
    "ニュースや政治に全く興味がない人の、心理的特徴",
    "友達がいなくても、恋愛をしていなくても、一人で充実して過ごせる人の特徴",
    "スポーツに熱狂できない人の脳｜実は「考える力」が強い人の特徴だった",
    "野球やサッカーに興味がない人だけが持っている特徴",
])
def test_tu_loai_tru_bi_PHU_DINH_thi_khong_loai(tieu_de):
    """"Không màng tới X" là insight của tệp lệch nhịp, không phải video về X.

    Lượt áp luật đầu (05/09/2026) đã ném nhầm hai dòng đầu ra "khác" — đúng loại video V1 đã
    làm và là video có pool sạch nhất kênh.
    """
    assert pt.ap_luat_cung(tieu_de, "幸福心理学", LECH, CO) == LECH


@pytest.mark.parametrize("tieu_de", [
    "賢い人ほど恋愛で不器用になる理由",            # 恋愛で — không phủ định
    "【雑学】ワールドカップ観戦が苦手な人の特徴",     # 雑学 không bao giờ được cứu
    "野球観戦が好きな人の特徴",
])
def test_tu_loai_tru_khong_phu_dinh_thi_van_loai(tieu_de):
    assert pt.ap_luat_cung(tieu_de, "x", LECH, CO) == pt.MA_KHAC


def test_luat_cung_KHONG_bat_duoc_loi_nghia():
    """Ghi nhận giới hạn, không phải lỗi: 電話が苦手 là triệu chứng, không có dấu hiệu trong chữ."""
    t = "【心理学】電話が鳴ると緊張する人に隠された5つの才能｜科学が証明した「電話が苦手な人」の正体"
    assert pt.ap_luat_cung(t, "ひととき心理学", LECH, CO) == LECH


def test_gan_tuyen_ap_luat_cung_sau_khi_ai_tra_loi():
    """AI gán 雑学 vào tệp lệch nhịp thì lớp luật cứng phải chặn TRƯỚC khi ra sổ."""
    tuyen = [pt.TuyenDeXuat(ma=LECH, ten="lệch nhịp"), pt.TuyenDeXuat(ma=TN, ten="trung niên")]

    def goi_gia(client, msgs, **kw):        # AI "ngu": gán tất cả vào t1
        return '{"1": {"ma": "t1", "do_tin": 95}, "2": {"ma": "t1", "do_tin": 95}, "3": {"ma": "t1", "do_tin": 95}}'

    ket = pt.gan_tuyen(None, ["【雑学】一匹狼が向いている人の特徴",
                              "中年以降、友人がいなくても大丈夫な理由",
                              "SNSをしない人に隠された特徴"],
                       tuyen, goi=goi_gia, kenh_nguon=["x", "x", "x"])
    assert ket[0].ma == pt.MA_KHAC and not ket[0].dung_duoc, "雑学 vẫn lọt ra sổ"
    assert ket[1].ma == TN, "mốc tuổi không được chuyển sang trung niên"
    assert ket[2].ma == LECH and ket[2].do_tin == 95, "dòng đúng bị đụng vào"


def test_sua_so_theo_luat_cung_chi_sua_dung_dong(tmp_path):
    """Lượt sửa lại sổ: đúng dòng thì đổi, dòng khác giữ nguyên từng ký tự, và có đếm để báo."""
    goc = str(tmp_path)
    kenh = "TL4-T7"
    os.makedirs(os.path.join(goc, "CHANNEL", kenh, "nghien-cuu"))
    cot = ["Kênh", "Tiêu đề video", so.COT_LINK, so.COT_TUYEN, "Ghi chú"]
    hang = [
        ["人の本音研究所", "【雑学】一匹狼が向いている人の特徴", "https://youtu.be/a1", LECH, ""],
        ["ひととき心理学", "年齢を重ねると「友達がいなくても大丈夫」な理由", "https://youtu.be/a2", LECH, "ghi chú của khách"],
        ["ひととき心理学", "SNSをしない人に隠された「恐ろしい特徴」", "https://youtu.be/a3", LECH, ""],
        ["幸福心理学", "家がずっと綺麗な人に共通する「特別な能力」", "https://youtu.be/a4", "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao", ""],
        ["x", "chưa gán gì", "https://youtu.be/a5", "", ""],
    ]
    so.luu_bang(goc, kenh, cot, hang)
    dem = pt.sua_so_theo_luat_cung(goc, kenh, CO)
    assert dem == {"loai_tru": 1, "sang_trung_nien": 1, "tong_da_xem": 4}
    # `doc_bang` trả cột ĐÃ CHUẨN HOÁ (chèn thêm cột máy quét) — tra theo TÊN,
    # không theo vị trí của danh sách cột lúc ghi.
    cot_moi, moi = so.doc_bang(goc, kenh)
    j, jg = cot_moi.index(so.COT_TUYEN), cot_moi.index("Ghi chú")
    assert moi[0][j] == pt.MA_KHAC
    assert moi[1][j] == TN and moi[1][jg] == "ghi chú của khách", "sửa tuyến mà đụng ghi chú khách"
    assert moi[2][j] == LECH and moi[3][j] == "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao"
    assert moi[4][j] == "", "ô trống phải giữ trống — đó là việc của AI, không phải luật cứng"
    # chạy lần hai không đổi gì thêm
    assert pt.sua_so_theo_luat_cung(goc, kenh, CO)["loai_tru"] == 0


def test_loi_nhac_gan_co_noi_ve_trieu_chung_va_moc_tuoi():
    """Luật cứng bắt phần có chữ; phần nghĩa vẫn phải nhờ model — nên lời nhắc phải nói rõ hai bẫy."""
    assert "triệu chứng" in pt.DE_BAI_GAN.lower() or "TRIỆU CHỨNG" in pt.DE_BAI_GAN
    assert "tuổi" in pt.DE_BAI_GAN.lower()
