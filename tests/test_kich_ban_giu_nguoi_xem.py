"""Lời nhắc viết kịch bản — những ràng buộc GIỮ NGƯỜI XEM, khoá lại bằng bài kiểm.

═══ VÌ SAO CÓ TỆP NÀY ═══

Lượt chạy thật TL4-T7/0001 (29/08/2026) ra video **24 phút 32** cho một kênh nhắm
13 phút, và **ý thứ nhất nằm ở phút 4:41** trong khi tiêu đề hứa "6 đặc điểm".
Đối chiếu đường giữ chân đo được của kênh: người xem rớt mạnh nhất ở giây 15–60,
tới giây 90 chỉ còn 40%. Tức quá nửa khán giả bỏ đi TRƯỚC khi nghe được thứ tiêu
đề hứa.

Năm chỗ hỏng nối nhau, mỗi chỗ một bài dưới đây:

1. Kênh thiếu `4-do-dai.md` → `_nan_do_dai` thoát trong im lặng, không ai nắn.
2. Lời nhắc viết chỉ nói "khoảng N phút" → cả 5 bản dôi 81–90%.
3. Lời nhắc hoàn thiện ra lệnh "giữ nguyên độ dài" → bản cuối còn phình thêm.
4. Rào chắn trong `hoan_thien_ban` chặn mọi bản ngắn hơn 0,8 lần → nén bị vứt.
5. `CHENH_CHO_PHEP = 0,25` → bản 10,0 phút trên đích 13,0 vẫn tính là "đạt".

═══ VÌ SAO ĐO BẰNG SỐ CÂU, KHÔNG BẰNG KÝ TỰ ═══

Đo trực tiếp: vòng nắn khai 3.926 ký tự thì AI trả 2.554; khai 5.889 thì trả
2.437 — khai CAO hơn lại ra NGẮN hơn. Cơ chế "thiếu thì khai cao hơn" ghi trong
`_nan_do_dai` chỉ chạy nếu AI phản ứng với con số ký tự, mà với tiếng Nhật thì
không. Đổi lời nhắc sang đếm SỐ CÂU mỗi ý: cùng model, cùng tư liệu, bản viết đi
từ 1.799 lên 3.465 ký tự. Ba lượt kiểm sau đó ra 11,5 · 12,0 · 11,2 phút.
"""

import io
import os

import pytest

GOC = os.path.join(os.path.dirname(__file__), "..")
KENH = [("TL4-T7", os.path.join(GOC, "CHANNEL", "TL4-T7", "prompt")),
        ("khuôn tâm-lý", os.path.join(GOC, "CHANNEL", "_KHUON", "nganh", "tam-ly", "prompt"))]


def _doc(thu_muc, ten):
    p = os.path.join(thu_muc, ten)
    if not os.path.exists(p):
        return ""
    return io.open(p, encoding="utf-8").read()


@pytest.mark.parametrize("nhan,thu_muc", KENH)
class TestLoiNhacViet:
    def test_co_tep_nan_do_dai(self, nhan, thu_muc):
        """Thiếu tệp này thì bước nắn tự tắt và không báo gì — xem `_nan_do_dai`."""
        assert _doc(thu_muc, "4-do-dai.md").strip(), (
            "{0}: thiếu 4-do-dai.md, bước nắn độ dài sẽ tự tắt".format(nhan))

    def test_do_dai_chi_noi_MOT_CON_SO(self, nhan, thu_muc):
        """═══ ĐỘ DÀI CHỈ CÒN MỘT DÒNG, KHÔNG SÀN KHÔNG TRẦN (04/09/2026) ═══

        Bài này vốn đòi lời nhắc viết phải nêu CẢ sàn lẫn trần
        (`<<CHARS_MIN>>`–`<<CHARS_MAX>>`), rút từ lượt 0001 dôi 84%.

        Chủ dự án, 04/09/2026: *"11 phút cũng được, 13, 15, 17 cũng được, tao
        thấy chả sao — quan trọng là content hay, khán giả xem hết"*, và
        *"đôi khi vụ độ dài chỉ cần yêu cầu đơn giản ví dụ là khoảng bao nhiêu
        ký tự, model AI thông minh nó khắc tự biết; việc nhồi prompt các yếu
        tố phụ làm nó tưởng cái đó quan trọng"*.

        Đó là chỗ mấu chốt: mỗi câu thêm vào về độ dài là một lần nữa nói với
        model rằng độ dài đáng quan tâm. Kênh chịu được 11–17 phút thì không
        có gì để canh, và mọi chữ tiêu vào việc canh nó là chữ lấy khỏi việc
        viết hay.
        """
        v = _doc(thu_muc, "2-viet.md")
        assert "<<CHARS>>" in v, (
            "{0}: lời nhắc viết vẫn phải nói một con số độ dài".format(nhan))
        assert "<<CHARS_MIN>>" not in v and "<<CHARS_MAX>>" not in v, (
            "{0}: bỏ sàn/trần đi — kênh chịu được 11–17 phút, nêu ba con số "
            "chỉ làm model tưởng độ dài là tiêu chí".format(nhan))

    def test_loi_nhac_viet_phai_GON(self, nhan, thu_muc):
        """═══ TIÊU CHÍ Ở BỘ CHẤM, KHÔNG Ở PROMPT VIẾT (chốt lại 04/09/2026) ═══

        Chủ dự án đã chốt nguyên tắc này một lần rồi, commit `319bee3`:
        *"Prompt càng phức tạp càng cứng và càng dễ fail"* — tiêu chí hay/hook/
        CTA/không chép đặt ở bộ chấm, không ở prompt viết. Bản gọn khi ấy: **232
        ký tự**.

        Rồi nó bị nhồi lại hai lần (`ca83565` đo bằng số câu, `babb159` bốn quy
        tắc 60 giây) và một lần nữa ngày 04/09 — lên **7.156 ký tự, gấp 30 lần**.

        Đo hậu quả trên chính kênh, ở CÙNG cỡ mẫu 16–20 người xem:
            V2 (viết bằng prompt gần bản gọn) : giữ chân **59%**
            V5 (viết bằng prompt đã nhồi)     : 32%
            V6 (viết bằng prompt đã nhồi)     : 26%

        Cơ chế: viết nhiều bản rồi chọn chỉ có tác dụng khi các bản KHÁC NHAU.
        Prompt nhồi chặt thì cả ba bản ra cùng một khuôn — hết cái để chọn.
        Chỗ đúng của mọi tiêu chí là BỘ CHẤM, nơi nó lọc chứ không ép.

        Bài này canh không cho phình lần thứ tư.
        """
        v = _doc(thu_muc, "2-viet.md")
        assert len(v) <= 900, (
            "{0}: 2-viet.md phình lên {1} ký tự. Tiêu chí craft (hook, nhịp, "
            "độ dài câu, cảnh vs giải thích) phải nằm ở 2b-cham.md — prompt "
            "viết chỉ giữ ràng buộc CƠ HỌC: tiếng, độ dài sàn/trần, định dạng "
            "trả về.".format(nhan, len(v)))

    def test_cham_khong_ep_KHUON_CAU_CHU(self, nhan, thu_muc):
        """═══ BỎ NỐT CÁC CON SỐ VỀ CÂU CHỮ (04/09/2026) ═══

        Bộ chấm từng ép "câu trung bình ~29 ký tự", rút từ đúng MỘT video giữ
        chân tốt nhất của kênh. Đối chiếu lại: video tệ nhất viết câu 30 ký tự
        — chênh một ký tự. Con số ấy không phân biệt được hai bên, nó chỉ là
        đặc điểm của giọng kênh mà thôi.

        Ép một con số như thế lên MỌI đề tài thì bộ chấm hết là bộ lọc, nó
        thành cái khuôn. Chủ dự án, 04/09/2026: *"template sẽ làm nhiều kịch
        bản nên việc đóng khung sẽ làm mọi thứ sai"*.

        Nay bản gốc đã thắng làm chuẩn: nhịp câu của nó là nhịp đúng cho đề tài
        của nó, và model tự đọc ra được.
        """
        v = _doc(thu_muc, "2b-cham.md")
        assert "29 ký tự" not in v and "40–50" not in v, (
            "{0}: 2b-cham.md còn ép độ dài câu bằng con số — mà video giữ chân "
            "TỐT nhất (29) và TỆ nhất (30) của kênh chỉ chênh nhau 1 ký "
            "tự".format(nhan))

    def test_cham_neu_MUC_TIEU_30_giay_dau(self, nhan, thu_muc):
        """═══ BỘ LUẬT MỞ ĐẦU ĐỔI LẦN BA — VÀ LẦN NÀY LÀ GỠ (04/09/2026) ═══

        Lần một: "mở bằng VẬT THỂ NHÌN ĐƯỢC, câu 10–20 ký tự, có CÂU HỎI trước
        giây 60". Rút từ V2 vs V3 hồi 29/08, khi CẢ HAI video đều có ảnh bìa
        yếu (2,8% và 2,1%) nên chỉ hút người đã sẵn tâm thế.

        Lần hai: bốn nhịp bắt buộc (hỏi thẳng → người khác xuất hiện → nhát đâm
        → trả lời hứa của ảnh bìa), rút từ ba kịch bản đối thủ đã thắng.

        Cả hai lần đều cùng một lỗi: lấy một mẫu nhỏ rồi biến nó thành luật cho
        mọi đề tài. Đo lại chính ba đối thủ ấy thì hai trong ba mở bằng TẢ CẢNH
        — đúng thứ luật lần một cấm nặng nhất; và đoạn mở của họ dài ~240 ký tự
        trong khi luật ép 110–150, tức ép mình viết NGẮN HƠN bản đã thắng.

        Nay bộ chấm chỉ nêu MỤC ĐÍCH (giữ người qua mốc 0:30, ngưỡng chính thức
        của YouTube là còn ≥50%) và đưa bản gốc làm chuẩn đối chiếu. Ràng buộc
        cứng chỉ còn thứ đo được và không đổi theo đề tài — xem
        `test_2b_cham_giu_rang_buoc_KHACH_QUAN` ở `tests/test_viet_hook.py`.
        """
        v = _doc(thu_muc, "2b-cham.md")
        assert "CHUẨN ĐỂ ĐỐI CHIẾU LÀ BẢN GỐC" in v, (
            "{0}: 2b-cham.md phải lấy bản gốc đã thắng làm chuẩn".format(nhan))
        assert "0:30" in v or "30–60 GIÂY ĐẦU" in v, (
            "{0}: 2b-cham.md phải nêu mục tiêu giữ người qua chỗ rớt nhiều "
            "nhất".format(nhan))
        assert "khuôn có sẵn" in v, (
            "{0}: 2b-cham.md phải nói rõ ĐỪNG chấm theo khuôn có sẵn — mỗi đề "
            "tài giữ người một kiểu".format(nhan))

    def test_y_thu_nhat_phai_vao_som(self, nhan, thu_muc):
        """Chỗ chết đo được của kênh là giây 15–60. Tiêu đề hứa N mục thì mục
        đầu phải nằm trong vùng người xem còn ở lại. Chấm ở BỘ CHẤM."""
        v = _doc(thu_muc, "2b-cham.md")
        # Đo bằng TỈ LỆ BÀI, không đếm câu: hai tiêu chí "câu ngắn" và "ý 1 trong
        # 8 câu" đá nhau — lượt 0002 viết câu 23 ký tự nên 12 câu mở đầu chỉ tốn
        # 250 ký tự (6,5% bài, sớm gấp đôi V2) mà vẫn bị đếm là "quá 8 câu".
        assert "10% đầu bài" in v, (
            "{0}: ràng buộc ý thứ nhất phải đo bằng tỉ lệ bài".format(nhan))

    def test_hoan_thien_khong_bi_khoa_tay_ve_do_dai(self, nhan, thu_muc):
        """Bản cũ ra lệnh 'giữ nguyên độ dài' nên bản cuối phình 7.093 → 7.589.

        Nay lời nhắc chỉ nói một con số, không ra lệnh nén cũng không cấm nén
        — đủ để model tự xử.
        """
        h = _doc(thu_muc, "2c-hoan-thien.md")
        assert "<<CHARS>>" in h, (
            "{0}: bước hoàn thiện phải biết độ dài nhắm tới".format(nhan))
        assert "giữ nguyên cấu trúc, các ý, nghiên cứu, con số, ẩn dụ và độ dài" not in h, (
            "{0}: câu 'giữ nguyên … độ dài' khoá tay bước nén".format(nhan))

    def test_do_dai_KHONG_phai_tieu_chi_cham(self, nhan, thu_muc):
        """═══ ĐỘ DÀI RA KHỎI BỘ CHẤM (04/09/2026) ═══

        Bộ chấm từng có: *"Vượt trần trên 20% thì TỐI ĐA 5 điểm"* và *"nếu MỌI
        bản đều vượt trần thì vẫn chọn bản GẦN TRẦN NHẤT"*.

        Câu thứ hai là chỗ hỏng nặng nhất: nó bảo chọn theo độ dài chứ không
        theo chất lượng. Lượt 0007 cho thấy hậu quả — ba bản bị chấm 6/6/8 với
        lý do xoay quanh độ dài, rồi bước hoàn thiện nén 27%, cắt mất đoạn
        レジリエンス của ý 1, đoạn 「感情を観客の前で演じません」 của ý 2 và
        ẩn dụ lái xe trong sương của ý 3 — toàn nội dung thật.

        Chủ dự án, 04/09/2026: *"11 phút cũng được, 13, 15, 17 cũng được… quan
        trọng là content hay, khán giả xem hết"* và *"việc mày cho nó điểm cao
        cũng không phải giải pháp hay"*.

        Số đo độ dài vẫn được đưa vào qua `<<SO_DO>>` — đó là DỮ LIỆU, model
        tự nhìn. Cái bỏ đi là LỜI RA LỆNH chấm theo nó.
        """
        c = _doc(thu_muc, "2b-cham.md")
        assert "TỐI ĐA 5 điểm" not in c, (
            "{0}: bộ chấm còn chặn trần điểm theo độ dài — một bản hay mà dài "
            "sẽ thua một bản vừa vặn mà nhạt".format(nhan))
        assert "gần trần nhất" not in c, (
            "{0}: bộ chấm còn bảo chọn bản GẦN TRẦN NHẤT — đó là chọn theo độ "
            "dài, không phải theo chất lượng".format(nhan))
        assert "<<SO_DO>>" in c, (
            "{0}: vẫn phải đưa số đo cho model tự nhìn".format(nhan))


class TestDoBangChuDocLen:
    """═══ THƯỚC ĐO ĐỘ DÀI PHẢI LÀ CHỮ ĐỌC LÊN (04/09/2026) ═══

    Chủ dự án: *"về độ dài tao không quá quan trọng trong khoảng từ 10-15
    phút… ở phần viết đã có target độ dài rồi thì có lệch cũng chẳng nhiều"*.

    Đúng — nhưng chỉ đúng nếu cái thước đo đúng. Đo bốn lượt TL4-T7 bằng chính
    giọng đọc `2-giong-doc.mp3` (không phải ước lượng):

        lượt   len()   đọc lên   xuống dòng   dấu ---   giọng đọc thật
        0002   3.834    3.404       406          8       11,97 phút
        0004   4.076    3.848       210          6       14,90 phút
        0005   4.051    3.820       213          6       14,84 phút
        0006   4.529    4.143       356         10       15,05 phút

    Bước `3-sua.md` tách mỗi câu một dòng, và dấu `---` được tool đổi thành
    quãng lặng thật. Cả hai đều KHÔNG được đọc lên, mà `len()` vẫn đếm chúng —
    5–10% con số đem đi so.

    Hậu quả đo được: lượt 0006 vượt trần dải ±15% đúng **14 ký tự** trong khi
    nó mang 356 ký tự xuống dòng. Bước nắn bị gọi dậy bởi thứ không có trong
    video, rồi chạy lời nhắc `4-do-dai.md` lên một bài đã xong.
    """

    DICH = 3926          # 13 phút × 302 ký tự/phút, đích của TL4-T7

    def test_bo_xuong_dong_dau_ngan_va_the(self):
        from core.auto_khau import _do_doc

        assert _do_doc("あい\nうえ\n") == 4, "xuống dòng không được đọc lên"
        assert _do_doc("あい\n---\nうえ") == 4, (
            "dấu --- là quãng lặng, tool chèn im lặng chứ không đọc")
        assert _do_doc("[sighs] あい") == 2, (
            "thẻ cảm xúc là chỉ đạo cho giọng, không phải lời đọc")

    def test_luot_0006_khong_con_bi_da_ra_khoi_dai(self):
        """Chính con số thật của lượt 0006 — bài kiểm này là ca đã xảy ra."""
        from core.auto_khau import CHENH_CHO_PHEP

        tren = self.DICH * (1 + CHENH_CHO_PHEP)
        assert 4529 > tren, (
            "số liệu nền sai: lượt 0006 đo bằng len() phải là VƯỢT trần")
        assert 4143 <= tren, (
            "đo bằng chữ đọc lên thì lượt 0006 phải nằm trong dải — nếu không, "
            "bước nắn vẫn nổ vì 356 ký tự xuống dòng")

    def test_bon_luot_that_deu_nam_trong_dai(self):
        """Chủ dự án nói đúng: bước viết đã tự về đích, không cần bước nắn.

        Nhưng chỉ khi đo bằng chữ đọc lên — đo bằng `len()` thì 0006 rơi ra.
        """
        from core.auto_khau import CHENH_CHO_PHEP

        duoi = self.DICH * (1 - CHENH_CHO_PHEP)
        tren = self.DICH * (1 + CHENH_CHO_PHEP)
        for luot, doc_len in (("0002", 3404), ("0004", 3848),
                              ("0005", 3820), ("0006", 4143)):
            assert duoi <= doc_len <= tren, (
                "lượt {0}: {1} ký tự đọc lên nằm ngoài dải {2:.0f}–{3:.0f} — "
                "bước nắn sẽ chạy".format(luot, doc_len, duoi, tren))


class TestRaoChanTrongMa:
    def test_nguong_dat_khong_duoc_long_qua(self):
        """0,25 biến mục tiêu 13 phút thành 'từ 10 tới 16' — mất nghĩa."""
        from core.auto_khau import CHENH_CHO_PHEP
        assert CHENH_CHO_PHEP <= 0.15, (
            "ngưỡng 'đạt' lỏng quá thì bản hụt 23% vẫn lọt, vòng nắn không chạy")

    def test_nen_sau_duoc_phep_khi_vuot_tran(self):
        """Rào chắn 1/1.25 sinh ra để chặn viết lại từ đầu, nhưng nó chặn luôn
        việc nén — mà nén chính là việc đúng khi bản dôi gần gấp đôi."""
        from core.viet_nhieu_ban import hoan_thien_ban

        ban = "".join("文{0}。これは説明の一文であり長さを稼ぐためのものです。".format(i)
                      for i in range(100))
        tran = int(len(ban) * 0.55)
        nen = ban[:int(len(ban) * 0.56)]
        _ra, da, _g = hoan_thien_ban(lambda _p: nen, ban, "goc",
                                     diem_yeu="dài gấp đôi", chars=tran)
        assert da, "bản vượt trần phải được nén về mức trần"

    def test_van_chan_nen_qua_da(self):
        """Nén sâu hơn cả mục tiêu vẫn phải bị bỏ — đó là viết lại từ đầu."""
        from core.viet_nhieu_ban import hoan_thien_ban

        ban = "".join("文{0}。これは説明の一文であり長さを稼ぐためのものです。".format(i)
                      for i in range(100))
        tran = int(len(ban) * 0.55)
        _ra, da, _g = hoan_thien_ban(lambda _p: ban[:int(len(ban) * 0.30)], ban,
                                     "goc", diem_yeu="dài", chars=tran)
        assert not da, "nén quá đà phải bị bỏ"

    def test_khong_vuot_tran_thi_van_chan_nen_sau(self):
        from core.viet_nhieu_ban import hoan_thien_ban

        ban = "".join("文{0}。これは説明の一文です。".format(i) for i in range(100))
        _ra, da, _g = hoan_thien_ban(lambda _p: ban[:int(len(ban) * 0.56)], ban,
                                     "goc", diem_yeu="sửa câu", chars=len(ban))
        assert not da, "bản không vượt trần thì nén sâu vẫn là viết lại từ đầu"
