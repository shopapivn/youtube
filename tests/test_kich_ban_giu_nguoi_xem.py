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

    def test_do_dai_noi_ca_san_lan_tran(self, nhan, thu_muc):
        """Chỉ nói một con số đích thì AI viết theo độ dài BẢN GỐC (dôi 84%);
        chỉ nói trần thì nó lộn sang đầu kia (hụt 63%). Phải có cả hai đầu."""
        v = _doc(thu_muc, "2-viet.md")
        assert "<<CHARS_MIN>>" in v and "<<CHARS_MAX>>" in v, (
            "{0}: lời nhắc viết phải nêu cả sàn lẫn trần độ dài".format(nhan))

    def test_do_bang_so_cau(self, nhan, thu_muc):
        """AI không bám được số ký tự tiếng Nhật — xem ghi chú đầu tệp."""
        v = _doc(thu_muc, "2-viet.md")
        assert "câu**" in v or "câu," in v, (
            "{0}: lời nhắc viết phải đo thân bài bằng SỐ CÂU".format(nhan))
        # ═══ CÂU NGẮN, KHÔNG PHẢI CÂU DÀI (sửa 29/08/2026) ═══
        #
        # Bài này từng đòi lời nhắc ép câu 40–50 ký tự, để bài khỏi hụt độ dài.
        # Đo lại trên chính kênh: video giữ chân TỐT NHẤT (28% tới cuối) viết câu
        # trung bình **29 ký tự**; video tệ nhất (12%) viết 30. Câu dài không phải
        # thứ phân biệt hai bên — ép 40–50 là ép ngược với video đang thắng.
        # Đủ độ dài bài bằng NHIỀU CÂU hơn, không phải câu dài hơn.
        assert "29 ký tự" in v, (
            "{0}: phải nêu độ dài câu đo trên video giữ chân tốt nhất "
            "(~29 ký tự), và đạt độ dài bài bằng nhiều câu hơn".format(nhan))

    def test_60_giay_dau_theo_bon_tieu_chi_do_duoc(self, nhan, thu_muc):
        """Ghép đường giữ chân với câu chữ tại đúng thời điểm đó (29/08/2026):
        trong 52 giây đầu, video tốt rớt 25 điểm, video tệ rớt 52 — gấp đôi.
        Bốn thứ khác nhau, mỗi thứ một dòng trong lời nhắc."""
        v = _doc(thu_muc, "2-viet.md")
        for manh, vi_sao in (
                ("VẬT THỂ NHÌN ĐƯỢC", "mở bằng cảm giác trừu tượng là chỗ rớt nặng nhất"),
                ("10–20 ký tự", "câu 35 ký tự ở giây 26 làm bản tệ mất 35 điểm"),
                ("CÂU HỎI", "bản tốt hỏi ở giây 52 rồi gần như không rớt thêm"),
                ("CHƯA GIẢI THÍCH CƠ CHẾ", "bản tệ giải thích ở giây 54 và tụt còn 49%")):
            assert manh in v, "{0}: thiếu '{1}' — {2}".format(nhan, manh, vi_sao)

    def test_cham_cung_soi_60_giay_dau(self, nhan, thu_muc):
        """Lời nhắc viết đòi bốn thứ thì bộ chấm phải soi được đúng bốn thứ đó,
        nếu không cả năm bản mở sai kiểu vẫn được chọn một bản."""
        c = _doc(thu_muc, "2b-cham.md")
        assert "VẬT THỂ NHÌN ĐƯỢC" in c and "CÂU HỎI" in c, (
            "{0}: bộ chấm phải chấm 60 giây đầu theo cùng tiêu chí".format(nhan))

    def test_y_thu_nhat_phai_vao_som(self, nhan, thu_muc):
        """Chỗ chết đo được của kênh là giây 15–60. Tiêu đề hứa N mục thì mục
        đầu phải nằm trong vùng người xem còn ở lại."""
        v = _doc(thu_muc, "2-viet.md")
        # Đo bằng TỈ LỆ BÀI, không đếm câu: hai tiêu chí "câu ngắn" và "ý 1 trong
        # 8 câu" đá nhau — lượt 0002 viết câu 23 ký tự nên 12 câu mở đầu chỉ tốn
        # 250 ký tự (6,5% bài, sớm gấp đôi V2) mà vẫn bị đếm là "quá 8 câu".
        assert "10% đầu bài" in v, (
            "{0}: ràng buộc ý thứ nhất phải đo bằng tỉ lệ bài".format(nhan))

    def test_hoan_thien_duoc_phep_nen(self, nhan, thu_muc):
        """Bản cũ ra lệnh 'giữ nguyên độ dài' nên bản cuối phình 7.093 → 7.589."""
        h = _doc(thu_muc, "2c-hoan-thien.md")
        assert "NÉN" in h, (
            "{0}: bước hoàn thiện phải được phép nén khi bản vượt trần".format(nhan))
        assert "giữ nguyên cấu trúc, các ý, nghiên cứu, con số, ẩn dụ và độ dài" not in h, (
            "{0}: câu 'giữ nguyên … độ dài' khoá tay bước nén".format(nhan))

    def test_cham_phat_nang_ban_vuot_tran(self, nhan, thu_muc):
        """Bộ chấm phải trừ đủ nặng, nếu không cả 5 bản dôi thì chọn bản nào cũng thế."""
        c = _doc(thu_muc, "2b-cham.md")
        assert "TỐI ĐA 5 điểm" in c, (
            "{0}: bộ chấm phải chặn trần điểm cho bản vượt độ dài".format(nhan))


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
