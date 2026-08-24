"""Kiểm ba sửa lỗi của lượt TL4-T7/0010 — KHÔNG gọi mạng, KHÔNG gọi API.

1. `go_boc_tool_gia`  — bóc lớp vỏ "gọi công cụ" giả để voice không đọc rác.
2. `go_cach_cjk`      — bỏ khoảng trắng thừa YouTube chèn giữa chữ tiếng Nhật.
3. `_chon_phu_de`     — ưu tiên ĐÚNG thứ tiếng (`ja`), không vớ bản dịch `aa`.
4. `_muc_tieu_do_dai` — đo độ dài theo SỐ GIÂY video, không theo ký tự bản dịch.
"""

from core.lam_sach import go_boc_tool_gia, go_cach_cjk
from core.script_video import _chon_phu_de
from core.auto_khau import _muc_tieu_do_dai
from core.kenh import Kenh


# ── 1. Bóc vỏ "gọi công cụ" giả ──────────────────────────────────────────────

_VO_GIA = (
    "```bash\nmkdir -p /tmp/out\n```\n\n"
    "Let me write the polished script.\n\n"
    "name write_file\n"
    '{"path": "/tmp/out/x.txt", "content": "金曜日の夜。\\n\\n今日やるべきことは終わった。"}\n'
    "</function_results>\n"
)


class TestGoBocToolGia:
    def test_boc_lay_dung_content(self):
        ra = go_boc_tool_gia(_VO_GIA)
        assert ra == "金曜日の夜。\n\n今日やるべきことは終わった。"
        # \n đã bung thành xuống dòng thật, không còn là hai ký tự.
        assert "\\n" not in ra

    def test_khong_con_dau_vo(self):
        ra = go_boc_tool_gia(_VO_GIA)
        for dau in ("write_file", "</function", "```bash", "mkdir", "/tmp/"):
            assert dau not in ra

    def test_kich_ban_sach_giu_nguyen(self):
        sach = "金曜日の夜。今日やるべきことは、もう全部終わりました。"
        assert go_boc_tool_gia(sach) == sach

    def test_co_chu_content_nhung_khong_co_dau_vo_thi_giu_nguyen(self):
        # Kịch bản thật có thể nhắc tới chữ "content" — không được bóc nhầm.
        chu = 'Bài nói về content marketing và "content" chất lượng cao.'
        assert go_boc_tool_gia(chu) == chu

    def test_nhieu_content_lay_cai_dai_nhat(self):
        chu = ('write_file\n{"content": "ngắn", "content": '
               '"đây là lời đọc dài hơn hẳn nên phải lấy cái này"}')
        assert go_boc_tool_gia(chu) == "đây là lời đọc dài hơn hẳn nên phải lấy cái này"

    def test_rong_tra_rong(self):
        assert go_boc_tool_gia("") == ""


# ── 2. Bỏ khoảng trắng thừa cho tiếng viết liền ──────────────────────────────

class TestGoCachCjk:
    def test_nhat_bo_cach(self):
        assert go_cach_cjk("日曜日 の 夕方", "ja") == "日曜日の夕方"

    def test_viet_giu_cach(self):
        assert go_cach_cjk("xin chào các bạn", "vi") == "xin chào các bạn"

    def test_han_giu_cach(self):
        # Tiếng Hàn DÙNG khoảng trắng giữa từ — không được dính lại.
        assert go_cach_cjk("나는 학생 입니다", "ko") == "나는 학생 입니다"

    def test_latin_nhung_trong_nhat_giu_nguyen(self):
        # "YouTube" là một từ La-tinh — chữ trong nó không bị tách/dính.
        assert go_cach_cjk("私 は YouTube を 見る", "ja") == "私はYouTubeを見る"

    def test_ma_ngon_ngu_co_duoi(self):
        assert go_cach_cjk("日曜日 の", "ja-JP") == "日曜日の"


# ── 3. Chọn phụ đề đúng thứ tiếng, không vớ bản dịch abc ──────────────────────

def _kho(*ma):
    return {"automatic_captions": {
        m: [{"ext": "json3", "url": "http://sub/{0}".format(m)}] for m in ma}}


class TestChonPhuDeNgonNgu:
    def test_uu_tien_dung_tieng_yeu_cau(self):
        # Có 'aa' (Afar, xếp đầu abc) lẫn 'ja' — xin 'ja' phải ra 'ja'.
        _, ma = _chon_phu_de(_kho("aa", "en", "ja", "vi"), False,
                             ngon_ngu_uu_tien="ja")
        assert ma == "ja"

    def test_khop_tien_to_khi_khong_co_ma_day_du(self):
        _, ma = _chon_phu_de(_kho("aa", "ja-orig"), False,
                             ngon_ngu_uu_tien="ja")
        assert ma == "ja-orig"

    def test_khong_co_tieng_ay_thi_ve_net_cu_uu_tien_viet(self):
        _, ma = _chon_phu_de(_kho("aa", "en", "vi"), False,
                             ngon_ngu_uu_tien="ja")
        assert ma == "vi"

    def test_khong_yeu_cau_thi_uu_tien_viet_nhu_cu(self):
        _, ma = _chon_phu_de(_kho("aa", "en", "vi", "ja"), False)
        assert ma == "vi"


# ── 4. Mục tiêu độ dài đo theo số giây video ──────────────────────────────────

def _kenh(**kw):
    mac = dict(do_dai_theo_goc=True, ky_tu_moi_phut=298, phut_muc_tieu=20)
    mac.update(kw)
    return Kenh(**mac)


class TestMucTieuDoDai:
    def test_remake_do_theo_giay(self):
        # 975 giây × 298 ÷ 60 = 4842 — khớp số chữ Nhật gốc thật (~4847).
        assert _muc_tieu_do_dai(_kenh(), "x" * 9999, 975) == 4842

    def test_thieu_giay_lui_ve_so_ky_tu(self):
        assert _muc_tieu_do_dai(_kenh(), "y" * 4847, 0) == 4847

    def test_khong_remake_thi_theo_phut(self):
        k = _kenh(do_dai_theo_goc=False)
        assert _muc_tieu_do_dai(k, "z" * 4847, 975) == k.ky_tu_muc_tieu

    def test_remake_nhung_khong_co_tu_lieu_thi_theo_phut(self):
        k = _kenh()
        assert _muc_tieu_do_dai(k, "", 975) == k.ky_tu_muc_tieu
