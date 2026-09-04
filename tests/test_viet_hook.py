"""Bước viết riêng ĐOẠN MỞ ĐẦU (hook) — khoá lại bằng bài kiểm.

═══ VÌ SAO CÓ TỆP NÀY ═══

Lượt TL4-T7/0005 (03/09/2026) được bộ chấm cả bài cho 9/10, nhưng đo trên phụ
đề thật thì đoạn mở tiêu **46,3 giây** mới chạm tới thứ ảnh bìa hứa, và trong
38 giây đầu **không có một cảm giác tiêu cực nào** — toàn cảnh dễ chịu.

Đo ba kịch bản gốc của đối thủ đã thắng (04/09/2026, quy giây theo 302 ký
tự/phút của chính giọng đọc kênh):

    ĐT-A 一人で旅行   : cảnh 0s → người khác 18,3s → CƠN NHÓI 29,6s → lật 46,7s
    ĐT-B 休日に出ない : cảnh 0s → đối chiếu 19,1s → CƠN NHÓI 39,7s → lật 62,0s
    ĐT-C 子供時代    : hỏi thẳng 0s → nhãn 10,9s → LẬT DANH TÍNH 16,7s → trả bài 23,4s

Cả ba đều cắm một nhát đâm ở giây 17–40. Đối chiếu chính kênh: video giữ chân
TỐT nhất (34,5%) có nhát đâm ở giây 52 「あなたの心は縮こまっていますか」 rồi
đường giữ chân đứng yên (74% → 72%); video TỆ nhất (19,5%) thay bằng câu dễ
chịu 「胸のあたりが静かに落ち着いている」 và rơi không phanh.

Bốn nhóm bài dưới đây khoá bốn thứ:
1. Lời nhắc viết hook đòi đủ bốn nhịp, và bộ chấm soi được đúng bốn nhịp đó.
2. Chỗ cắt hook rơi đúng ranh giới đoạn mở / ý thứ nhất.
3. Rào chắn: hook hỏng thì bị bỏ, bài không bao giờ vỡ.
4. Lời nhắc viết cả bài không còn dạy luật cũ đã bị số liệu bác bỏ.
"""

import io
import os

import pytest

from core.viet_nhieu_ban import (DAI_HOOK, HOOK_MAX, HOOK_MIN, hook_dung_duoc,
                                 tach_hook, thay_hook, vi_tri_cat_hook)

GOC = os.path.join(os.path.dirname(__file__), "..")
KENH = [("TL4-T7", os.path.join(GOC, "CHANNEL", "TL4-T7", "prompt")),
        ("khuôn tâm-lý", os.path.join(GOC, "CHANNEL", "_KHUON", "nganh",
                                      "tam-ly", "prompt"))]

#: Đoạn mở THẬT của lượt 0005, cắt từ phụ đề. 203 ký tự, đọc hết 49,4 giây.
HOOK_THAT = ("夜の部屋に、小さな明かり。窓の外では、静かな雨の音。手の中には、温かいお茶。"
             "スマホは、裏返したまま。誰にも会わない夜が、一番落ち着く。"
             "あなたにも、そんな夜がありませんか。時計の針の音だけが、部屋に響く。"
             "この静けさが、ごちそうに感じる。人混みより、一人の部屋が好き。"
             "誘いを断って、ほっとしたことがある。周りからは「強い人」と呼ばれる。"
             "でも、その好みは偶然ではありません。多くの場合、子供時代に理由があります。")
THAN_THAT = "一つ目は、予測できない愛情です。まず、ある場面を思い出してください。玄関のドアが開く、あの音です。"
BAN_THAT = HOOK_THAT + THAN_THAT

#: Bài THẬT dài ~3.800 ký tự. Rào chắn "cả bài lệch quá 25%" chỉ đúng nghĩa
#: trên bài cỡ thật: thay 203 ký tự trong bài 3.800 là đổi 2%, còn thay trong
#: một mẩu 250 ký tự là đổi 33% — nên các bài kiểm rào chắn phải dùng bản này.
THAN_DAI = THAN_THAT + "".join(
    "子供のあなたは、テレビの音を小さくした。そして、足音を聞いた。" for _ in range(120))
BAN_DAI = HOOK_THAT + THAN_DAI


def _doc(thu_muc, ten):
    p = os.path.join(thu_muc, ten)
    return io.open(p, encoding="utf-8").read() if os.path.exists(p) else ""


# ── 1. Lời nhắc và bộ chấm phải đòi cùng bốn nhịp ───────────────────────────

@pytest.mark.parametrize("nhan,thu_muc", KENH)
class TestLoiNhacHook:
    def test_co_du_hai_tep(self, nhan, thu_muc):
        """Thiếu một trong hai thì bước hook tự tắt trong im lặng."""
        assert _doc(thu_muc, "2d-hook.md").strip(), (
            "{0}: thiếu 2d-hook.md — bước viết hook sẽ tự tắt".format(nhan))
        assert _doc(thu_muc, "2e-cham-hook.md").strip(), (
            "{0}: thiếu 2e-cham-hook.md — hook viết ra không ai chấm".format(nhan))

    def test_loi_nhac_hook_phai_GON(self, nhan, thu_muc):
        """Cùng nguyên tắc với `2-viet.md` (commit 319bee3 của chủ dự án):
        *"Prompt càng phức tạp càng cứng và càng dễ fail"*.

        Bản gốc đã thắng CHÍNH LÀ đặc tả của hook — đưa đoạn mở của nó cho model
        xem rồi bảo viết một bản tương tự, đúng tinh thần remake. Bốn nhịp là
        thứ để BỘ CHẤM lọc, không phải thứ để ép lúc viết: viết bốn bản mà cả
        bốn bị ép cùng khuôn thì không còn gì để chọn.
        """
        v = _doc(thu_muc, "2d-hook.md")
        assert len(v) <= 900, (
            "{0}: 2d-hook.md phình lên {1} ký tự — bốn nhịp phải nằm ở "
            "2e-cham-hook.md".format(nhan, len(v)))

    def test_hook_co_du_o_can_thiet(self, nhan, thu_muc):
        """Ba ô này thiếu thì hook viết mù: không biết ảnh bìa hứa gì, không có
        chuẩn nhịp của bản gốc, không biết phải dẫn vào đâu."""
        v = _doc(thu_muc, "2d-hook.md")
        for o in ("<<THUMB>>", "<<HOOK_GOC>>", "<<THAN_BAI>>"):
            assert o in v, "{0}: 2d-hook.md thiếu ô {1}".format(nhan, o)
        assert "110–150" in v, (
            "{0}: phải nêu khoảng độ dài hook (110–150 ký tự ≈ 30 giây)"
            .format(nhan))

    def test_nhat_dam_bat_buoc_o_bo_cham(self, nhan, thu_muc):
        """Nhịp quyết định: 3/3 đối thủ thắng có, video tệ nhất của kênh không.
        Đòi ở BỘ CHẤM để nó lọc, chứ không ép lúc viết."""
        c = _doc(thu_muc, "2e-cham-hook.md")
        assert "NHÁT ĐÂM" in c, (
            "{0}: bộ chấm hook phải chấm nhịp nhát đâm".format(nhan))
        assert "胸に引っかかる" in c or "トゲが刺さる" in c, (
            "{0}: phải nêu ví dụ cơn đau đặt trong cơ thể lấy từ đối thủ"
            .format(nhan))

    def test_cham_phat_mo_bang_ta_canh(self, nhan, thu_muc):
        """Luật cũ 'mở bằng vật thể' bị hiểu thành 11 giây tả tĩnh vật —
        bộ chấm phải phạt đúng lỗi đó."""
        c = _doc(thu_muc, "2e-cham-hook.md")
        assert "tả cảnh" in c, (
            "{0}: bộ chấm phải phạt bản mở bằng chuỗi tả cảnh".format(nhan))

    def test_cam_hua_hen_tu_ngoai(self, nhan, thu_muc):
        """Bálint 2017: trì hoãn phi-truyện làm GIẢM mức đắm chìm; căng thẳng
        phải nằm trong đời người xem."""
        c = _doc(thu_muc, "2e-cham-hook.md")
        assert "xem đến cuối" in c, (
            "{0}: bộ chấm phải phạt lối hứa hẹn từ ngoài".format(nhan))

    def test_cham_soi_dung_bon_nhip(self, nhan, thu_muc):
        """Lời nhắc đòi bốn nhịp thì bộ chấm phải soi được đúng bốn nhịp đó,
        nếu không mọi bản mở sai kiểu vẫn được chọn một bản."""
        c = _doc(thu_muc, "2e-cham-hook.md")
        for manh in ("HỎI THẲNG NGƯỜI XEM", "NGƯỜI KHÁC XUẤT HIỆN",
                     "NHÁT ĐÂM", "TRẢ LỜI HỨA CỦA ẢNH BÌA"):
            assert manh in c, (
                "{0}: bộ chấm hook thiếu tiêu chí '{1}'".format(nhan, manh))

    def test_cham_phat_ban_de_chiu(self, nhan, thu_muc):
        """Không phạt thì bản êm ru vẫn thắng — đúng lỗi của lượt 0005."""
        c = _doc(thu_muc, "2e-cham-hook.md")
        assert "DỄ CHỊU" in c and "TỐI ĐA 4 điểm" in c, (
            "{0}: bộ chấm phải phạt bản thay nhát đâm bằng cảm giác dễ chịu"
            .format(nhan))

    def test_cham_doi_khop_anh_bia(self, nhan, thu_muc):
        """Người xem bấm vào vì dòng chữ trên ảnh bìa — hook phải chạm tới nó."""
        c = _doc(thu_muc, "2e-cham-hook.md")
        assert "<<THUMB>>" in c, (
            "{0}: bộ chấm hook phải biết chữ trên ảnh bìa mới chấm được việc "
            "khớp lời hứa".format(nhan))


# ── 2. Lời nhắc viết cả bài phải bỏ luật cũ đã bị bác bỏ ─────────────────────

@pytest.mark.parametrize("nhan,thu_muc", KENH)
class TestLoiNhacVietDaCapNhat:
    def test_bo_luat_mo_bang_vat_the(self, nhan, thu_muc):
        """Luật cũ 'MỞ BẰNG VẬT THỂ NHÌN ĐƯỢC' rút từ V2 vs V3 — cả hai đều có
        ảnh bìa yếu (2,8% và 2,1%). Với ảnh bìa mới (8,9–13,4%) nó bị hiểu
        thành 11 giây tả tĩnh vật trước khi chạm tới người xem."""
        v = _doc(thu_muc, "2-viet.md")
        assert "MỞ BẰNG VẬT THỂ NHÌN ĐƯỢC" not in v, (
            "{0}: 2-viet.md còn dạy luật cũ 'mở bằng vật thể' — luật này đã bị "
            "thay bằng bốn nhịp".format(nhan))

    def test_2b_cham_theo_bon_nhip(self, nhan, thu_muc):
        c = _doc(thu_muc, "2b-cham.md")
        assert "NHÁT ĐÂM" in c, (
            "{0}: 2b-cham.md phải chấm nhịp nhát đâm".format(nhan))
        assert "VẬT THỂ NHÌN ĐƯỢC" not in c, (
            "{0}: 2b-cham.md còn chấm theo luật cũ".format(nhan))


# ── 3. Chỗ cắt hook ─────────────────────────────────────────────────────────

class TestTachHook:
    def test_cat_dung_ranh_gioi_that(self):
        """Trên chính đoạn mở của lượt 0005: phải cắt ở 203, ngay TRƯỚC 一つ目."""
        assert vi_tri_cat_hook(BAN_THAT) == len(HOOK_THAT)
        hook, than = tach_hook(BAN_THAT)
        assert hook == HOOK_THAT
        assert than.startswith("一つ目")

    def test_khong_co_dau_thi_cat_theo_ky_tu(self):
        """Bài không có dấu vào ý thì cắt ở ranh giới câu đầu tiên từ mốc."""
        b = "。".join("これはとても長い文章の一部です" for _ in range(40)) + "。"
        i = vi_tri_cat_hook(b)
        assert i >= DAI_HOOK
        assert b[i - 1] == "。", "phải cắt ở ranh giới câu, không cắt giữa câu"

    def test_dau_qua_som_thi_bo_qua(self):
        """「まず、」 nằm ngay câu đầu là chữ trong câu, không phải ranh giới."""
        b = "まず、" + "静かな夜です。" * 40
        assert vi_tri_cat_hook(b) >= DAI_HOOK

    def test_ban_rong(self):
        assert vi_tri_cat_hook("") == 0
        assert tach_hook("") == ("", "")


# ── 4. Rào chắn — hook hỏng không được làm vỡ bài ───────────────────────────

class TestRaoChan:
    def test_hook_dat(self):
        ok, _ = hook_dung_duoc("あなたもそうではありませんか。" * 8, THAN_DAI, BAN_DAI)
        assert ok

    def test_hook_rong_bi_bo(self):
        assert hook_dung_duoc("", THAN_DAI, BAN_DAI)[0] is False

    def test_hook_cut_bi_bo(self):
        assert hook_dung_duoc("短い。", THAN_DAI, BAN_DAI)[0] is False

    def test_hook_tran_bi_bo(self):
        assert hook_dung_duoc("あ。" * (HOOK_MAX + 10), THAN_DAI, BAN_DAI)[0] is False

    def test_hook_khong_het_cau_bi_bo(self):
        """Bản cụt giữa chừng — dấu hiệu mô hình bị cắt token."""
        ok, vi_sao = hook_dung_duoc("あ" * (HOOK_MIN + 10), THAN_DAI, BAN_DAI)
        assert ok is False and "hết câu" in vi_sao

    def test_ca_bai_lech_qua_thi_bo(self):
        """Thay hook không được phép biến bài thành bài khác."""
        ok, vi_sao = hook_dung_duoc("あ。" * 60, "短い本文。", "短い本文。")
        assert ok is False and "lệch" in vi_sao


class TestThayHook:
    def test_thay_duoc_va_giu_than_bai(self):
        moi_hook = "一人が楽だと感じていませんか。" + "周りは強い人だと言います。" * 5
        ban, da_thay, _ = thay_hook(
            lambda _p: moi_hook, None, BAN_DAI, "対抗の冒頭",
            so_ban=1, khuon_viet="viết hook <<HOOK_GOC>> <<THAN_BAI>>")
        assert da_thay is True
        assert ban.startswith("一人が楽だと感じていませんか。")
        assert THAN_THAT in ban, "thân bài phải còn nguyên"
        assert "小さな明かり" not in ban, "đoạn mở cũ phải bị thay hẳn"

    def test_khong_co_loi_nhac_thi_giu_nguyen(self):
        ban, da_thay, _ = thay_hook(lambda _p: "x", None, BAN_DAI, "",
                                    so_ban=3, khuon_viet="")
        assert (ban, da_thay) == (BAN_DAI, False)

    def test_moi_hook_hong_thi_giu_nguyen(self):
        """Cửa cuối: mọi bản trượt rào chắn thì trả bài cũ, không vỡ."""
        ban, da_thay, ghi = thay_hook(
            lambda _p: "短い。", None, BAN_DAI, "", so_ban=3,
            khuon_viet="viết hook")
        assert (ban, da_thay) == (BAN_DAI, False)
        assert "rào chắn" in ghi

    def test_viet_rong_thi_giu_nguyen(self):
        ban, da_thay, _ = thay_hook(lambda _p: "", None, BAN_DAI, "",
                                    so_ban=2, khuon_viet="viết hook")
        assert (ban, da_thay) == (BAN_DAI, False)

    def test_nhat_lai_ban_da_viet(self):
        """Chạy tiếp lượt đứt giữa chừng: không gọi AI lại cho bản đã có."""
        goi = []
        cu = "一人が楽だと感じていませんか。" + "周りは強い人だと言います。" * 5

        def viet(_p):
            goi.append(1)
            return "あなたはどうですか。" + "周りは強い人だと言います。" * 5

        ban, da_thay, _ = thay_hook(
            viet, None, BAN_DAI, "", so_ban=2, khuon_viet="viết hook",
            da_co=lambda i: cu if i == 0 else "")
        assert len(goi) == 1, "bản 0 đã có trên đĩa thì không được gọi AI lại"
        assert da_thay is True

    def test_luu_tung_ban_ra_dia(self):
        luu = {}
        hook = "あなたはどうですか。" + "周りは強い人だと言います。" * 5
        thay_hook(lambda _p: hook, None, BAN_DAI, "", so_ban=2,
                  khuon_viet="viết hook",
                  luu_ban=lambda i, chu: luu.__setitem__(i, chu))
        assert set(luu) == {0, 1}, "mọi bản phải được ghi ra đĩa để soi lại"


# ── 5. Cấu hình kênh ────────────────────────────────────────────────────────

def test_kenh_bat_buoc_hook_va_giam_so_ban():
    """TL4-T7 phải bật bước hook, và số bản cả bài hạ 5 → 3 để dồn chữ sang."""
    from core.kenh import doc_kenh

    if not os.path.isdir(os.path.join(GOC, "CHANNEL", "TL4-T7")):
        pytest.skip("kho này chưa có kênh TL4-T7")
    k = doc_kenh(GOC, "TL4-T7")
    assert k.so_ban_nhap == 3, "số bản cả bài phải là 3"
    assert k.so_ban_hook >= 2, "phải viết ít nhất 2 hook mới có cái để chọn"
