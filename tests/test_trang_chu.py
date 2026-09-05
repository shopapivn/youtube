"""Cào trang chủ v2: extension gom hết link → trạm ghi sổ + lọc → tool tra, phân loại, đổ đối thủ.

Chủ dự án, 05/09/2026: *"mở trang chủ, thu nhỏ, lấy hết link về, chuyển cho tool — tool làm các
việc phía sau: lọc tiêu đề đúng tâm lý (có thể dùng API), đúng thì lấy đối thủ, danh bạ tăng, rồi
xử lý content đối thủ để phân tuyến và chấm"*.

Bản cũ (v2.4) chỉ gom LINK KÊNH rồi nối thẳng vào hộp thư — không tên, không lọc. Hai kênh 雑学
lọt vào sổ đối thủ TL4-T7 (150 dòng content) đi đúng đường ấy, và làm hỏng luôn bảng phân tuyến.
Mấy bài dưới canh bốn chỗ: trạm ghi được và lọc được · tool tra được và phân được · AI chỉ chạm
phần lưỡng lự · extension đúng dây nối (kiểm tĩnh, không chạy Chrome — giới hạn ghi rõ).
"""

import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chi_so_ytb as cs  # noqa: E402
from core import doi_thu_kenh as so  # noqa: E402
from core import trang_chu as tc  # noqa: E402
from core.chi_so_ytb.tram import Tram  # noqa: E402

KENH = "TL4-T7"


def _goc(tmp_path):
    (tmp_path / "CHANNEL" / KENH / "nghien-cuu").mkdir(parents=True)
    return str(tmp_path)


def _v(ma, tieu_de="", ten_kenh="", link_kenh="", short=False, vi_tri=1):
    return {"ma": ma, "tieu_de": tieu_de, "ten_kenh": ten_kenh, "link_kenh": link_kenh,
            "short": short, "vi_tri": vi_tri}


# ── trạm nhận ────────────────────────────────────────────────────────────────


def test_tram_ghi_moi_video_va_chi_noi_kenh_sach_vao_hop_thu(tmp_path):
    goc = _goc(tmp_path)
    tram = Tram(goc=goc)
    kq = tram.nhan_trang_chu(KENH, [
        _v("aaaaaaaaaaa", "【心理学】SNSをしない人の特徴", "心理学のおやつ", "https://www.youtube.com/@oyatsu", vi_tri=1),
        _v("bbbbbbbbbbb", "【雑学】一匹狼が向いている人の特徴", "大人の心理雑学", "https://www.youtube.com/@zatsu", vi_tri=2),
        _v("ccccccccccc", "ダンス動画", "ゆる", "https://www.youtube.com/@short", short=True, vi_tri=3),
    ], ["https://www.youtube.com/@hitomamezatugaku", "https://www.youtube.com/@shinri"])
    # @shinri là link RỜI không tên → không nối mù, chờ hoan_thien tra (bài học 267 kênh, 05/09)
    assert kq == {"video": 3, "kenh_moi": 1, "bi_loai": 3}
    dong = tc.doc(goc, KENH)
    assert [d["Mã video"] for d in dong] == ["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"]
    assert dong[1]["Bị loại"] == "từ loại trừ" and dong[2]["Bị loại"] == "short"
    hop = so.doc_doi_thu(goc, KENH).splitlines()
    assert "https://www.youtube.com/@oyatsu" in hop and "https://www.youtube.com/@shinri" not in hop
    assert not any("zatsu" in h or "zatugaku" in h or "@short" in h for h in hop), \
        "kênh 雑学 / Short vẫn lọt vào hộp thư — đúng lỗi cũ"


def test_tram_giu_so_luot_tai_cua_tung_video_va_hai_cot_trung_nhau(tmp_path):
    """Extension 2.6.1 tải lại trang chủ 3 lượt; cột "Lượt tải" đo lượt 2–3 ra thêm bao nhiêu video."""
    from core.chi_so_ytb.tram import Tram as T
    assert tuple(T.COT_TRANG_CHU) == tuple(tc.COT), "trạm và module phải cùng một bộ cột, lệch là bảng vỡ"
    goc = _goc(tmp_path)
    T(goc=goc).nhan_trang_chu(KENH, [dict(_v("aaaaaaaaaaa", "x", "k", "https://www.youtube.com/@a"), luot=1),
                                     dict(_v("bbbbbbbbbbb", "y", "k", "https://www.youtube.com/@a"), luot=3)])
    dong = {d["Mã video"]: d for d in tc.doc(goc, KENH)}
    assert dong["aaaaaaaaaaa"]["Lượt tải"] == "1" and dong["bbbbbbbbbbb"]["Lượt tải"] == "3"
    tc.luu(goc, KENH, tc.doc(goc, KENH))          # ghi lại qua module không được làm mất cột
    assert {d["Mã video"]: d["Lượt tải"] for d in tc.doc(goc, KENH)} == {"aaaaaaaaaaa": "1", "bbbbbbbbbbb": "3"}


def test_tram_giao_quet_day_du_xep_studio_truoc_trang_chu_sau(tmp_path):
    """Chủ dự án 05/09: một nút = Studio + trang chủ. Agent cũ trên máy ảo làm tuần tự theo hộp việc."""
    goc = _goc(tmp_path)
    tram = Tram(goc=goc)
    a, b = tram.giao_quet_day_du(KENH)
    cho = tram.viec_cho()
    assert [v["loai"] for v in cho] == ["quet-studio", "quet-trang-chu"] and (a, b) == (cho[0]["id"], cho[1]["id"])
    assert tram._lenh_tien_ich.get(KENH) == {"chup": "het"}, "lệnh Studio phải kèm dặn tiện ích chụp lại tất cả"


def test_tram_ghi_NOI_theo_luot_khong_ghi_de(tmp_path):
    goc = _goc(tmp_path)
    tram = Tram(goc=goc)
    tram.nhan_trang_chu(KENH, [_v("aaaaaaaaaaa", "x", "k", "https://www.youtube.com/@a")])
    tram.nhan_trang_chu(KENH, [_v("bbbbbbbbbbb", "y", "k2", "https://www.youtube.com/@b")])
    assert len(tc.doc(goc, KENH)) == 2, "lượt sau ghi đè lượt trước — mất lịch sử trang chủ"


def test_tram_KHONG_noi_mu_link_kenh_khong_ten_vao_hop_thu(tmp_path):
    """Extension 2.4 chỉ gửi `danh_sach` link kênh — không tên, không tiêu đề.

    Lượt cào thật đầu tiên 05/09/2026 nối 267 kênh Việt/Anh/Tây Ban Nha vào hộp thư của một kênh
    tiếng Nhật đúng theo đường này. Link không tên thì KHÔNG nối: từ loại trừ vẫn lọc được ở handle,
    phần còn lại chờ `hoan_thien` tra bằng yt-dlp rồi mới quyết.
    """
    goc = _goc(tmp_path)
    kq = Tram(goc=goc).nhan_trang_chu(KENH, [], ["https://www.youtube.com/@abc",
                                                  "https://www.youtube.com/@zatsugaku_tv"])
    assert kq["kenh_moi"] == 0 and kq["bi_loai"] == 1
    assert "@abc" not in so.doc_doi_thu(goc, KENH)


def _kenh_ja(goc):
    io.open(os.path.join(goc, "CHANNEL", KENH, "kenh.yaml"), "w", encoding="utf-8").write("ngon_ngu: ja\n")


def test_tram_loai_video_khong_dung_tieng_cua_kenh(tmp_path):
    """Kênh `ja` mà tiêu đề + tên kênh không có một chữ Nhật → không phải nguồn remake, bất kể đề tài."""
    goc = _goc(tmp_path)
    _kenh_ja(goc)
    kq = Tram(goc=goc).nhan_trang_chu(KENH, [
        _v("aaaaaaaaaaa", "5 dấu hiệu tâm lý của người thích ở một mình", "Bài Học Cuộc Sống",
           "https://www.youtube.com/@baihoccuocsong", vi_tri=1),
        _v("bbbbbbbbbbb", "La psicología de la soledad", "La Psicología Invisible",
           "https://www.youtube.com/@psicologiainvisible", vi_tri=2),
        _v("ccccccccccc", "SNSをしない人の特徴", "心理学のおやつ", "https://www.youtube.com/@oyatsu", vi_tri=3),
        _v("ddddddddddd", "", "", "https://www.youtube.com/@khongten", vi_tri=4),   # không tên → chờ tra
    ])
    assert kq == {"video": 4, "kenh_moi": 1, "bi_loai": 2}
    dong = {d["Mã video"]: d for d in tc.doc(goc, KENH)}
    assert dong["aaaaaaaaaaa"]["Bị loại"] == "không đúng tiếng" and dong["bbbbbbbbbbb"]["Bị loại"] == "không đúng tiếng"
    assert dong["ccccccccccc"]["Bị loại"] == "" and dong["ddddddddddd"]["Bị loại"] == ""
    hop = so.doc_doi_thu(goc, KENH)
    assert "@oyatsu" in hop and "@baihoccuocsong" not in hop and "@psicologiainvisible" not in hop
    assert "@khongten" not in hop, "link không tên phải chờ tra, không nối mù"


def test_kenh_khong_khai_ngon_ngu_thi_khong_loc_theo_tieng(tmp_path):
    goc = _goc(tmp_path)   # không có kenh.yaml
    kq = Tram(goc=goc).nhan_trang_chu(KENH, [_v("aaaaaaaaaaa", "Why lonely people are smarter", "Psych2Go",
                                                 "https://www.youtube.com/@psych2go")])
    assert kq["kenh_moi"] == 1 and kq["bi_loai"] == 0, "không biết tiếng kênh thì không đoán, không loại"


@pytest.mark.parametrize("chu, lang, kq", [
    ("SNSをしない人の特徴", "ja", True),
    ("心理学のおやつ", "ja", True),
    ("Bài Học Cuộc Sống", "ja", False),
    ("PEWPEW", "ja", False),
    ("PEWPEW", "", True),          # không biết tiếng → không lọc
    ("", "ja", True),              # chữ trống → không kết luận
    ("Why lonely people", "en", True),
])
def test_dung_tieng(chu, lang, kq):
    assert tc.dung_tieng(chu, lang) is kq


@pytest.mark.parametrize("ten, link, kq", [
    ("本要約チャンネル【毎日18時更新】", "https://www.youtube.com/@youyaku", True),     # tóm sách — lọt 05/09
    ("アバタロー", "https://www.youtube.com/@Aba_Book_Tuber", True),                  # book tuber
    ("シニアの整え知恵", "https://www.youtube.com/@lifehackzatsugaku", True),          # 雑学 ở handle
    ("フェルミ漫画大学", "https://www.youtube.com/@ferumi", True),                    # 漫画
    ("心理学のおやつ", "https://www.youtube.com/@oyatsu", False),
    ("こころのクセ図鑑", "https://www.youtube.com/@kokoro_zukan", False),
])
def test_kenh_bi_loai_theo_the_loai_ten_kenh(ten, link, kq):
    assert tc.kenh_bi_loai(ten, link) is kq


def test_phan_loai_tu_khoa_loai_tieu_de_khong_dung_tieng():
    assert tc.phan_loai_tam_ly("Psychology of lonely people", ["psychology"], "", "Psych2Go", lang="ja") == "lech"
    # không biết tiếng kênh thì không loại — từ khoá toàn tiếng Nhật nên ra "lưỡng lự", không "lệch"
    assert tc.phan_loai_tam_ly("Psychology of lonely people", ["psychology"], "", "Psych2Go") == "lung"


# ── tool: tra + phân loại + đổ đối thủ ───────────────────────────────────────


@pytest.mark.parametrize("tieu_de, tags, ten_kenh, kq", [
    ("【心理学】SNSをしない人の特徴", [], "心理学のおやつ", "dung"),
    ("人に執着しない人が手放したもの", ["心理学"], "x", "dung"),          # từ mạnh trong tag
    ("一人でいると疲れる人の特徴", [], "x", "dung"),                     # 2 từ yếu: 一人 + 疲れ + 特徴
    ("今日のニュースまとめ", [], "x", "lech"),
    ("【心理学】賢い人の特徴", [], "大人の心理雑学", "lech"),             # 雑学 ở TÊN KÊNH thắng
    ("レジで「お願いします」と言う人は", [], "裏まめ学", "lung"),          # không từ nào — lưỡng lự
])
def test_phan_loai_bang_tu_khoa(tieu_de, tags, ten_kenh, kq):
    assert tc.phan_loai_tam_ly(tieu_de, tags, "", ten_kenh) == kq


def _tra_gia(ma, lang="", cancel=None):
    return {
        "ddddddddddd": {"tieu_de": "【脳科学】片付けられない人の脳", "ten_kenh": "ひとり時間の脳科学",
                        "link_kenh": "https://www.youtube.com/@hitori", "luot_xem": "248000",
                        "dang": "2026-05-04", "dai": "13:05", "short": False, "tags": ["脳科学"], "mo_ta": ""},
        "eeeeeeeeeee": {"tieu_de": "レジで「お願いします」と言う人は", "ten_kenh": "裏まめ学",
                        "link_kenh": "https://www.youtube.com/@hitomamezatugaku", "luot_xem": "705756",
                        "dang": "2026-06-20", "dai": "1:57", "short": True, "tags": ["雑学"], "mo_ta": ""},
        "fffffffffff": {"tieu_de": "夜中に目が覚める人へ", "ten_kenh": "ひととき心理学",
                        "link_kenh": "https://www.youtube.com/@hitotoki", "luot_xem": "1000",
                        "dang": "2026-08-01", "dai": "20:00", "short": False, "tags": ["50代", "60代"],
                        "mo_ta": ""},
    }.get(ma, {})


def test_hoan_thien_tra_dap_phan_loai_va_do_kenh(tmp_path):
    goc = _goc(tmp_path)
    tram = Tram(goc=goc)
    tram.nhan_trang_chu(KENH, [_v("ddddddddddd", vi_tri=1), _v("eeeeeeeeeee", vi_tri=2),
                               _v("fffffffffff", vi_tri=3)])
    dem = tc.hoan_thien(goc, KENH, tra=_tra_gia)
    assert dem["da_tra"] == 3 and dem["video"] == 3
    dong = {d["Mã video"]: d for d in tc.doc(goc, KENH)}
    assert dong["ddddddddddd"]["Kênh"] == "ひとり時間の脳科学" and dong["ddddddddddd"]["Bị loại"] == ""
    assert dong["eeeeeeeeeee"]["Short"] == "x" and dong["eeeeeeeeeee"]["Bị loại"], \
        "Short 雑学 phải bị loại sau khi tra"
    assert dong["fffffffffff"]["Bị loại"] == "", "tiêu đề không từ khoá nhưng là lưỡng lự — chưa loại khi không có AI"
    hop = so.doc_doi_thu(goc, KENH)
    assert "@hitori" in hop and "@hitomamezatugaku" not in hop
    assert "@hitotoki" not in hop, "kênh của video LƯỜNG LỰ không được vào hộp thư khi chưa có AI"
    assert dem["tam_ly"] == 1 and dem["lung"] == 1 and dem["kenh_moi"] == 1
    # kênh 50代/60代 được ĐẾM (để bảng chấm dùng) nhưng không tự loại
    assert dem["kenh_the_tuoi"] == 0        # chưa vào kenh_dung vì lưỡng lự


def test_hoan_thien_doc_ngon_ngu_kenh_va_loai_video_sai_tieng(tmp_path):
    goc = _goc(tmp_path)
    _kenh_ja(goc)
    Tram(goc=goc).nhan_trang_chu(KENH, [_v("ggggggggggg")])

    def tra(ma, lang="", cancel=None):
        assert lang == "ja", "hoan_thien phải tự đọc ngon_ngu từ kenh.yaml khi không được truyền"
        return {"tieu_de": "5 dấu hiệu tâm lý", "ten_kenh": "Bài Học Cuộc Sống",
                "link_kenh": "https://www.youtube.com/@bhcs", "luot_xem": "1", "dang": "", "dai": "10:00",
                "short": False, "tags": ["tâm lý"], "mo_ta": ""}
    dem = tc.hoan_thien(goc, KENH, tra=tra)
    assert dem["loai"] == 1 and dem["kenh_moi"] == 0
    assert "@bhcs" not in so.doc_doi_thu(goc, KENH)


def test_hoan_thien_KHONG_tra_lai_ma_da_tra(tmp_path):
    """Trang chủ ngày nào cũng lặp lại vài chục video — tra lại là đốt thời gian."""
    goc = _goc(tmp_path)
    Tram(goc=goc).nhan_trang_chu(KENH, [_v("ddddddddddd")])
    dem1 = tc.hoan_thien(goc, KENH, tra=_tra_gia)
    Tram(goc=goc).nhan_trang_chu(KENH, [_v("ddddddddddd"), _v("eeeeeeeeeee")])
    goi = []

    def tra_dem(ma, lang="", cancel=None):
        goi.append(ma)
        return _tra_gia(ma)
    dem2 = tc.hoan_thien(goc, KENH, tra=tra_dem)
    assert dem1["da_tra"] == 1 and dem2["da_tra"] == 1 and goi == ["eeeeeeeeeee"]


def test_ai_chi_nhan_phan_luong_lu_va_ket_qua_duoc_ap(tmp_path):
    goc = _goc(tmp_path)
    Tram(goc=goc).nhan_trang_chu(KENH, [_v("ddddddddddd"), _v("fffffffffff")])
    nhan = []

    def ai_gia(tds):
        nhan.extend(tds)
        return {t: "dung" for t in tds}
    dem = tc.hoan_thien(goc, KENH, tra=_tra_gia, goi_ai=ai_gia)
    assert nhan == ["夜中に目が覚める人へ"], "AI phải chỉ thấy tiêu đề LƯỠNG LỰ, không thấy cái từ khoá đã phân"
    assert dem["lung"] == 0 and dem["tam_ly"] == 2
    assert "@hitotoki" in so.doc_doi_thu(goc, KENH)
    assert dem["kenh_the_tuoi"] == 1, "kênh gắn 50代/60代 phải được đếm để bảng chấm trừ điểm"


def test_phan_loai_bang_ai_doc_json_theo_so_thu_tu():
    def goi_gia(client, msgs, **kw):
        return '{"1": "dung", "2": "lech", "3": "gì đó"}'
    kq = tc.phan_loai_bang_ai(None, ["a", "b", "c"], goi=goi_gia)
    assert kq == {"a": "dung", "b": "lech"}, "giá trị lạ phải bị bỏ, không bịa"


def test_tom_tat_noi_luot_gan_nhat(tmp_path):
    goc = _goc(tmp_path)
    assert "chưa có" in tc.tom_tat(goc, KENH)
    Tram(goc=goc).nhan_trang_chu(KENH, [_v("aaaaaaaaaaa", "x", "", ""), _v("bbbbbbbbbbb", "y", "k", "https://www.youtube.com/@k")])
    tt = tc.tom_tat(goc, KENH)
    assert "2 video" in tt and "1 chưa tra" in tt


def test_tom_tat_gom_ba_goi_cua_mot_dot_va_dem_moi_theo_luot_tai(tmp_path):
    """3 lượt tải gửi 3 gói cách nhau vài phút — tóm tắt phải coi là MỘT đợt, và nói lượt 2–3 ra thêm gì."""
    goc = _goc(tmp_path)
    dong = [
        {"Lúc quét": "2026-09-05 22:00", "Mã video": "a" * 11, "Kênh": "k", "Lượt tải": "1"},
        {"Lúc quét": "2026-09-05 22:00", "Mã video": "b" * 11, "Kênh": "k", "Lượt tải": "1"},
        {"Lúc quét": "2026-09-05 22:02", "Mã video": "c" * 11, "Kênh": "k", "Lượt tải": "2"},
        {"Lúc quét": "2026-09-05 22:04", "Mã video": "d" * 11, "Kênh": "", "Lượt tải": "3"},
        {"Lúc quét": "2026-09-04 22:03", "Mã video": "e" * 11, "Kênh": "k", "Lượt tải": "1"},   # đợt hôm trước
    ]
    tc.luu(goc, KENH, dong)
    tt = tc.tom_tat(goc, KENH)
    assert "4 video" in tt and "1 chưa tra" in tt and "2/1/1" in tt, tt


# ── extension: dây nối (kiểm tĩnh) ───────────────────────────────────────────

GOC_EXT = cs.thu_muc_extension()


def _doc(ten):
    return io.open(os.path.join(GOC_EXT, ten), encoding="utf-8").read()


def test_trang_chu_js_gom_video_cuon_toi_day_va_dung_khi_het_moi():
    js = _doc("trang-chu.js")
    # Link video được bắt bằng regex (`\\/watch\\?v=([\\w-]{11})`, `\\/shorts\\/…`) — kiểm ý,
    # không kiểm chuỗi nguyên văn: phải có mã video 11 ký tự cho cả video dài lẫn Shorts.
    assert re.search(r"watch\\\?v=\(\[\\w-\]\{11\}\)", js), "phải gom MÃ VIDEO 11 ký tự, không chỉ link kênh"
    assert re.search(r"shorts\\/\(\[\\w-\]\{11\}\)", js), "phải nhận cả Shorts để đánh dấu và loại"
    assert "scrollHeight" in js, "phải kéo tới ĐÁY để YouTube nạp trang kế"
    assert re.search(r"DUNG_SAU_KHONG_MOI\s*=\s*\d", js), "phải dừng khi vài lần cuộn liền không có link mới"
    assert re.search(r"MAX_LAN_CUON\s*=\s*\d", js), "phải có trần lần cuộn — không treo mãi"
    assert "type: 'zoom'" in js and "type: 'trang_chu'" in js


def test_trang_chu_js_tai_lai_vai_luot_va_doc_tieu_de_dung_cho():
    """Chủ dự án 05/09: *"quét trang chủ làm một lượt 2–3 lần, mỗi lần load ra dữ liệu mới"*.

    Đo thật v2.6.0: tiêu đề vớ được 3% vì chỉ đọc `title` — thẻ video để ở `aria-label`/`#video-title`.
    """
    js = _doc("trang-chu.js")
    m = re.search(r"SO_LUOT_TAI\s*=\s*(\d)", js)
    assert m and 2 <= int(m.group(1)) <= 3, "phải tải lại trang chủ 2–3 lượt"
    assert "sessionStorage" in js and "location.reload()" in js, "gom qua các lượt phải sống qua reload"
    assert "removeItem(KHO)" in js, "gửi xong phải xoá kho — không thì lượt quét sau kế thừa lượt trước"
    assert "aria-label" in js and "#video-title" in js
    # Gửi phần MỚI sau MỖI lượt (agent máy ảo có thể đóng Chrome sau ~90s — gom tới cuối là mất
    # trắng), nhưng mỗi video chỉ đi một lần: lọc theo lượt sinh ra + kho nhớ kênh đã gửi.
    assert js.count("type: 'trang_chu'") == 1
    assert "v.luot === luot" in js and "kenh_da_gui" in js, "phải lọc phần mới, không gửi trùng qua các lượt"


def test_background_js_nhan_trang_chu_va_rot_ve_duong_cu():
    js = _doc("background.js")
    assert "msg.type === 'trang_chu'" in js and "'/trang-chu'" in js
    than = js.split("msg.type === 'trang_chu'")[1][:2500]
    assert "'/doi-thu'" in than, "trạm cũ chưa có /trang-chu thì phải rớt về /doi-thu, không mất lượt quét"
    assert "msg.type === 'zoom'" in js and "chrome.tabs.setZoom" in js


def test_manifest_nap_trang_chu_js_tren_youtube_va_ban_moi():
    m = json.load(io.open(os.path.join(GOC_EXT, "manifest.json"), encoding="utf-8"))
    assert any("trang-chu.js" in cs_["js"] and any("www.youtube.com" in x for x in cs_["matches"])
               for cs_ in m["content_scripts"])
    assert tuple(int(x) for x in m["version"].split(".")[:2]) >= (2, 6)
