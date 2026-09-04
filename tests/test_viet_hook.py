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


# ── 1. Lời nhắc phải NÊU MỤC TIÊU, không đóng khung cách làm ────────────────
#
# ═══ VÌ SAO GỠ BỘ LUẬT CỨNG (04/09/2026, cùng ngày viết ra nó) ═══
#
# Bộ chấm hook từng đóng khung rất chặt: "câu đầu phải hỏi thẳng người xem",
# "mở bằng chuỗi tả cảnh (đèn, mưa, tách trà) là trừ nặng nhất", "nhát đâm
# trước giây 25", "hook 110–150 ký tự".
#
# Đo lại đoạn mở của chính ba video đối thủ ĐÃ THẮNG thì luật ấy tự mâu thuẫn:
#
#   ĐT-A 一人で旅行  : mở bằng CẢNH sân ga sáng sớm, cầm một tấm vé
#   ĐT-B 休日に出ない: mở bằng CẢNH sáng ngày nghỉ, không đặt chuông
#   ĐT-C 子供時代    : mở bằng câu hỏi thẳng
#
# HAI TRONG BA video thắng mở bằng tả cảnh — đúng thứ luật ghi "trừ nặng
# nhất". Và đoạn mở của chúng dài ~240 ký tự, trong khi luật ép 110–150: tức
# ép hook của mình NGẮN HƠN bản đã thắng.
#
# Chủ dự án, 04/09/2026: *"những cái cứng, những thứ đóng khung không ổn…
# chỉ cần cho AI nó biết mục tiêu, giữ chân người xem, khán giả thấy hay…
# template sẽ làm nhiều kịch bản nên việc đóng khung sẽ làm mọi thứ sai"*.
#
# Nay: lời nhắc nêu MỤC TIÊU (giữ người qua giây 30) và đưa BẢN GỐC làm chuẩn
# đối chiếu, để model tự đọc xem bản đã thắng làm gì. Ràng buộc cứng chỉ còn
# thứ khách quan: độ dài, không chép, đúng tiếng.

@pytest.mark.parametrize("nhan,thu_muc", KENH)
class TestLoiNhacHook:
    def test_co_du_ba_tep(self, nhan, thu_muc):
        """Thiếu tệp nào thì bước đó tự tắt trong im lặng."""
        for ten, vi_sao in (
                ("2d-hook.md", "bước viết hook sẽ tự tắt"),
                ("2e-cham-hook.md", "hook viết ra không ai chấm"),
                ("2f-va-hook.md", "lời chê của bộ chấm rơi vào hư không")):
            assert _doc(thu_muc, ten).strip(), "{0}: thiếu {1} — {2}".format(
                nhan, ten, vi_sao)

    def test_loi_nhac_hook_phai_GON(self, nhan, thu_muc):
        """Bản gốc đã thắng CHÍNH LÀ đặc tả — cho model xem nó là đủ."""
        for ten in ("2d-hook.md", "2f-va-hook.md"):
            v = _doc(thu_muc, ten)
            assert len(v) <= 900, "{0}: {1} phình lên {2} ký tự".format(
                nhan, ten, len(v))

    def test_dua_NGUYEN_ban_goc_cho_ai_tu_doc(self, nhan, thu_muc):
        """Từng cắt sẵn "đoạn mở của bản gốc" bằng bộ tách từ khoá rồi mới đưa
        cho AI. Cắt bằng từ khoá là cách thô: bản gốc có thể không dùng dấu nào
        trong danh sách, cắt sai thì chuẩn đối chiếu sai theo."""
        for ten in ("2d-hook.md", "2e-cham-hook.md", "2f-va-hook.md"):
            v = _doc(thu_muc, ten)
            assert "<<COMPETITOR_TRANSCRIPT>>" in v, (
                "{0}: {1} phải nhận NGUYÊN kịch bản gốc, không phải đoạn cắt "
                "sẵn".format(nhan, ten))

    def test_hook_biet_anh_bia_va_than_bai(self, nhan, thu_muc):
        """Thiếu hai ô này thì hook viết mù: không biết ảnh bìa hứa gì với
        người xem, và không biết phải dẫn vào đâu."""
        v = _doc(thu_muc, "2d-hook.md")
        for o in ("<<THUMB>>", "<<THAN_BAI>>"):
            assert o in v, "{0}: 2d-hook.md thiếu ô {1}".format(nhan, o)

    def test_cham_neu_MUC_TIEU_chu_khong_dong_khung(self, nhan, thu_muc):
        """Bộ chấm phải nói mục tiêu và lấy bản gốc làm chuẩn, để model tự
        nhận ra cách giữ người của TỪNG đề tài."""
        c = _doc(thu_muc, "2e-cham-hook.md")
        assert "giây thứ 30" in c or "0:30" in c, (
            "{0}: bộ chấm hook phải nêu mục tiêu giữ người qua giây 30"
            .format(nhan))
        assert "bản gốc" in c, (
            "{0}: bộ chấm hook phải lấy bản gốc làm chuẩn đối chiếu".format(nhan))
        assert "khuôn có sẵn" in c, (
            "{0}: bộ chấm phải nói rõ ĐỪNG chấm theo khuôn có sẵn — mỗi đề tài "
            "giữ người một kiểu".format(nhan))

    def test_KHONG_con_luat_cung_bi_bac_bo(self, nhan, thu_muc):
        """Ba luật này bị chính đoạn mở của đối thủ đã thắng bác bỏ."""
        for ten in ("2d-hook.md", "2e-cham-hook.md", "2f-va-hook.md",
                    "2b-cham.md"):
            v = _doc(thu_muc, ten)
            assert "tách trà" not in v, (
                "{0}/{1}: còn cấm mở bằng tả cảnh — mà 2/3 video đối thủ THẮNG "
                "mở bằng tả cảnh".format(nhan, ten))
            assert "110–150" not in v, (
                "{0}/{1}: còn ép hook 110–150 ký tự — đoạn mở của đối thủ đã "
                "thắng dài ~240".format(nhan, ten))
            assert "NHÁT ĐÂM" not in v, (
                "{0}/{1}: còn đóng khung 'nhát đâm' rút từ một ca hỏng"
                .format(nhan, ten))


# ── 2. Lời nhắc viết cả bài cũng phải gọn và nêu mục tiêu ────────────────────

@pytest.mark.parametrize("nhan,thu_muc", KENH)
class TestLoiNhacVietDaCapNhat:
    def test_2b_cham_lay_ban_goc_lam_chuan(self, nhan, thu_muc):
        c = _doc(thu_muc, "2b-cham.md")
        assert "CHUẨN ĐỂ ĐỐI CHIẾU LÀ BẢN GỐC" in c, (
            "{0}: 2b-cham.md phải lấy bản gốc làm chuẩn, không phải một khuôn "
            "tự chế".format(nhan))
        assert "khuôn có sẵn" in c, (
            "{0}: 2b-cham.md phải nói rõ đừng chấm theo khuôn có sẵn".format(nhan))

    def test_2b_cham_giu_rang_buoc_KHACH_QUAN(self, nhan, thu_muc):
        """Gỡ luật cứng không có nghĩa là bỏ hết: những thứ ĐO ĐƯỢC và không
        đổi theo đề tài thì vẫn phải giữ."""
        c = _doc(thu_muc, "2b-cham.md")
        for manh, vi_sao in (
                ("ĐỘ DÀI", "trần phút đọc là ràng buộc khách quan"),
                ("CON SỐ", "cả 3 lượt đều mất sạch số liệu của bản gốc"),
                ("KHÔNG CHÉP", "remake không phải chép")):
            assert manh in c, "{0}: 2b-cham.md thiếu '{1}' — {2}".format(
                nhan, manh, vi_sao)


def test_MAU_GON_cung_da_go_luat_cung():
    """`_MAU-GON` là bản mẫu dùng để khai sinh kênh mới — sửa xong hai kênh kia
    mà quên nó thì mọi kênh sinh sau lại mang nguyên luật cũ, và sẽ không ai
    phát hiện cho tới lúc đo lại đường giữ chân.

    ═══ VÌ SAO CHỈ QUÉT BA THƯ MỤC NÀY, KHÔNG QUÉT CẢ `CHANNEL/` ═══

    Bài này thoạt đầu quét mọi thư mục `prompt/`, và bắt ngay
    `CHANNEL/hoathinh-3d/prompt/2b-cham.md` — kênh hoạt hình cho trẻ em, cũng
    có câu "mở đầu tả cảnh dài, vòng vo là trừ nặng nhất".

    Nhưng bằng chứng gỡ luật là ba kịch bản đối thủ **ngách tâm lý**. Nó không
    nói gì về chuyện kể cho trẻ con. Ép luật của ngách này sang ngách kia chính
    là cái lỗi mà cả đợt sửa này đang gỡ — chỉ khác chiều. Kênh ngách khác tự
    đo, tự chỉnh.
    """
    for ten_kenh in ("_MAU-GON",):
        thu_muc = os.path.join(GOC, "CHANNEL", ten_kenh, "prompt")
        v = _doc(thu_muc, "2b-cham.md")
        assert v.strip(), "{0}: thiếu 2b-cham.md".format(ten_kenh)
        assert "tả cảnh dài" not in v, (
            "{0}/2b-cham.md còn trừ nặng bản mở bằng tả cảnh — mà 2/3 video "
            "đối thủ THẮNG mở bằng tả cảnh".format(ten_kenh))
        assert "CHUẨN ĐỂ ĐỐI CHIẾU LÀ BẢN GỐC" in v, (
            "{0}/2b-cham.md phải lấy bản gốc đã thắng làm chuẩn".format(ten_kenh))


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

    def test_mau_khong_kem_dau_phay(self):
        """Lượt 0006 viết 「まず前提となる話から始めましょう」 — không có phẩy.
        Dấu cũ 「まず、」 trượt, chỗ cắt rơi về đếm ký tự và để SÓT 24 giây lộ
        trình cũ (kèm câu "xem đến cuối") dính vào sau hook mới."""
        b = ("友人との集まりより、誰もいない部屋の隅にいる方が呼吸が楽だと感じたとき。" * 3
             + "まず前提となる話から始めましょう。" + "人の集まりの中にいると消耗します。" * 20)
        hook, than = tach_hook(b)
        assert than.startswith("まず前提"), (
            "phải cắt trọn đoạn mở cũ, không để sót lộ trình dính vào hook mới")

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


# ── 4b. Vá hook theo lời chê ────────────────────────────────────────────────

class TestVaHook:
    """Thân bài có bước hoàn thiện, hook thì không — nên lời chê của bộ chấm
    hook rơi vào hư không. Lượt 0006: bộ chấm chọn bản tốt nhất, chỉ cho 6/10,
    và viết sẵn cách sửa ("Không có nhát đâm… cần thay bằng một nhát đâm lật
    danh tính, đặt trước giây 25") — mà không ai dùng.

    Đây cũng là chỗ DUY NHẤT hook vượt được bản gốc: bốn bản viết ra đều bắt
    chước hook đối thủ nên thừa hưởng cả điểm yếu của nó.
    """

    HOOK = "あなたもそうではありませんか。" * 8
    VA = "一人が楽なのは、あなたが選んだからではありません。" * 4

    #: Bản thứ hai — phải có ≥2 hook qua rào chắn thì bộ chấm mới chạy và mới
    #: có lời chê để vá. Chỉ một bản sống sót thì không có lời chê: đó là giới
    #: hạn chấp nhận được (kênh viết 4 hook, rào chắn chỉ loại bản dị dạng).
    HOOK2 = "誰にも会わない夜が落ち着きますよね。" * 6

    def _chay(self, cham, khuon_va="vá <<DRAFT>> <<DIEM_YEU>>"):
        ban = [self.HOOK, self.HOOK2]

        def viet(_p):
            return ban.pop(0)

        return thay_hook(viet, cham, BAN_DAI, "goc", so_ban=2,
                         khuon_viet="viết hook", khuon_cham="chấm <<CAC_BAN>>",
                         khuon_va=khuon_va, goi_va=lambda _p: self.VA)

    def test_bo_cham_thich_ban_va_thi_lay_ban_va(self):
        # Bộ chấm: vòng 1 chọn A (chỉ 1 bản), vòng so sánh chọn B = bản vá.
        tra = ['{"chon":"A","ly_do":"x","diem_yeu":"thiếu nhát đâm"}',
               '{"chon":"B","ly_do":"bản vá có nhát đâm"}']
        ban, da, ghi = self._chay(lambda _p: tra.pop(0))
        assert da is True
        assert ban.startswith(self.VA[:12]), "phải dùng hook ĐÃ VÁ"
        assert "ĐÃ VÁ" in ghi

    def test_bo_cham_khong_thich_thi_giu_ban_cu(self):
        tra = ['{"chon":"A","ly_do":"x","diem_yeu":"thiếu nhát đâm"}',
               '{"chon":"A","ly_do":"bản cũ vẫn hơn"}']
        ban, da, ghi = self._chay(lambda _p: tra.pop(0))
        assert ban.startswith(self.HOOK[:12]), "không hơn thì giữ hook đã chọn"
        assert "chưa vá" in ghi

    def test_khong_co_loi_nhac_va_thi_bo_qua(self):
        ban, da, ghi = self._chay(
            lambda _p: '{"chon":"A","ly_do":"x","diem_yeu":"thiếu"}',
            khuon_va="")
        assert ban.startswith(self.HOOK[:12])
        assert "Vá hook" not in ghi

    def test_ban_va_hong_thi_giu_ban_cu(self):
        """Vá ra bản cụt → rào chắn `hook_dung_duoc` chặn, không vỡ bài."""
        ban = [self.HOOK, self.HOOK2]
        ket, _da, ghi = thay_hook(
            lambda _p: ban.pop(0),
            lambda _p: '{"chon":"A","ly_do":"x","diem_yeu":"thiếu"}',
            BAN_DAI, "goc", so_ban=2, khuon_viet="viết",
            khuon_cham="chấm <<CAC_BAN>>",
            khuon_va="vá <<DRAFT>>", goi_va=lambda _p: "短い。")
        assert ket.startswith(self.HOOK[:12]) and "bỏ bản vá" in ghi

    def test_goi_va_nem_loi_thi_giu_ban_cu(self):
        def no(_p):
            raise RuntimeError("mạng đứt")

        ban = [self.HOOK, self.HOOK2]
        ket, _da, ghi = thay_hook(
            lambda _p: ban.pop(0),
            lambda _p: '{"chon":"A","ly_do":"x","diem_yeu":"thiếu"}',
            BAN_DAI, "goc", so_ban=2, khuon_viet="viết",
            khuon_cham="chấm <<CAC_BAN>>",
            khuon_va="vá <<DRAFT>>", goi_va=no)
        assert ket.startswith(self.HOOK[:12]) and "hỏng" in ghi


# ── 5. Bước hoàn thiện: tách câu KHÔNG được tính là "viết lại từ đầu" ───────

class TestRaoChanHoanThien:
    """Lượt 0006: bộ chấm ra lệnh cắt 544 ký tự + tách mọi câu dài về 29 ký tự.
    Bản hoàn thiện làm đúng thế (nén x0,87) nhưng chỉ giữ 46% câu nên bị bỏ —
    mất trắng toàn bộ phần sửa: bài vẫn dôi 14%, câu dài vẫn dài, ý thứ nhất
    vẫn ở 23% bài. Rào chắn đo bằng CÂU đá nhau với lệnh TÁCH CÂU.
    """

    def test_tach_cau_van_qua_duoc(self):
        from core.viet_nhieu_ban import hoan_thien_ban

        # Bản gốc: câu dài. Bản hoàn thiện: đúng chữ ấy, tách đôi mỗi câu.
        ban = "".join("あなたはとても疲れやすく、そしてよく眠れない人です。" for _ in range(40))
        moi = "".join("あなたはとても疲れやすい。そしてよく眠れない人です。" for _ in range(40))
        ra, da, ghi = hoan_thien_ban(
            lambda _p: moi, ban, "goc", diem_yeu="tách câu dài",
            khuon="x <<DRAFT>> <<DIEM_YEU>>")
        assert da is True, (
            "tách câu giữ gần trọn CHỮ mà mất trọn nhận dạng CÂU — không được "
            "tính là viết lại từ đầu. Ghi chú: " + ghi)
        assert ra == moi

    def test_viet_lai_tu_dau_van_bi_chan(self):
        from core.viet_nhieu_ban import hoan_thien_ban

        ban = "".join("あなたはとても疲れやすく、よく眠れない人です。" for _ in range(40))
        moi = "".join("今日の天気は晴れで、風がとても心地よいですね。" for _ in range(40))
        ra, da, _ = hoan_thien_ban(
            lambda _p: moi, ban, "goc", diem_yeu="sửa",
            khuon="x <<DRAFT>> <<DIEM_YEU>>")
        assert da is False and ra == ban, "bản viết lại từ đầu phải bị chặn"


# ── 6. Cấu hình kênh ────────────────────────────────────────────────────────

def test_kenh_bat_buoc_hook_va_giam_so_ban():
    """TL4-T7 phải bật bước hook, và số bản cả bài hạ 5 → 3 để dồn chữ sang."""
    from core.kenh import doc_kenh

    if not os.path.isdir(os.path.join(GOC, "CHANNEL", "TL4-T7")):
        pytest.skip("kho này chưa có kênh TL4-T7")
    k = doc_kenh(GOC, "TL4-T7")
    assert k.so_ban_nhap == 3, "số bản cả bài phải là 3"
    assert k.so_ban_hook >= 2, "phải viết ít nhất 2 hook mới có cái để chọn"
