"""Bản đồ hình (kế hoạch chương cho cả video) — KHÔNG gọi mạng, KHÔNG tốn tiền.

Vì sao có bước này — soi 487 cảnh của ba lượt thật TL4-T7 ngày 25/08/2026, xem
thẳng ảnh chứ không chỉ đọc prompt:

  1. 140/140 cảnh của lượt 0031 đặt trong cùng một sa mạc đào có đồi mây, vì
     `image_style` ép "peach sky, hills, clouds" vào ĐUÔI của mọi prompt. Câu
     "tối thứ Sáu tan làm, đồng nghiệp rủ đi nhậu" ra một ngã ba đường trống.
     Khán giả không thấy đời mình trong đó.
  2. Nhân vật cười ở mọi cảnh — cả lúc bị chỉ mặt, lúc đất nứt dưới chân — vì
     `reference_lock` khoá "open smiling mouth". Mặt trái lời là mất tin.
  3. 9 khúc chia song song không biết nhau → mỗi 5 giây một ẩn dụ rời, không
     chương, không chỗ đổi bối cảnh — thứ giữ chân người xem video dài.

Sửa ba tầng: `style.yaml` (thế giới + biểu cảm), `7-canh.md` (luật giữ chân),
và lượt `7-ke-hoach.md` lập bản đồ chương TRƯỚC khi chia khúc.
"""

import json
import os

import pytest

from core.chia_canh import dien_khuon, khoi_ke_hoach, sach_ke_hoach

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BA_NOI = (os.path.join("_KHUON", "nganh", "tam-ly"), "TL4-T7", "_MAU-GON")


def cue(i, dai=2.0):
    return {"index": i, "start": (i - 1) * dai, "end": i * dai, "text": "cau {0}".format(i)}


def chuong(a, b, **k):
    m = {"srt_from": a, "srt_to": b, "title": "c{0}".format(a), "place": "apartment",
         "time_light": "9 pm, desk lamp", "people": "nv1", "motif": "glass",
         "emotion": "tense -> calm", "key_line": a}
    m.update(k)
    return m


# ── sach_ke_hoach: dọn thứ AI trả về ─────────────────────────────────────────

class TestSachKeHoach:
    def test_nhan_ca_dict_chapters_lan_danh_sach(self):
        cues = [cue(i) for i in range(1, 11)]
        a = sach_ke_hoach({"chapters": [chuong(1, 10)]}, cues)
        b = sach_ke_hoach([chuong(1, 10)], cues)
        assert a == b and len(a) == 1

    def test_ho_thi_keo_chuong_truoc_chong_thi_cat_chuong_sau(self):
        cues = [cue(i) for i in range(1, 21)]
        kh = sach_ke_hoach([chuong(1, 5), chuong(9, 14), chuong(12, 20)], cues)
        assert [(c["srt_from"], c["srt_to"]) for c in kh] == [(1, 8), (9, 14), (15, 20)]

    def test_phu_het_dong_dau_va_cuoi(self):
        cues = [cue(i) for i in range(1, 21)]
        kh = sach_ke_hoach([chuong(3, 8), chuong(9, 15)], cues)
        assert kh[0]["srt_from"] == 1 and kh[-1]["srt_to"] == 20

    def test_so_dong_ngoai_phu_de_thi_kep_lai(self):
        cues = [cue(i) for i in range(1, 11)]
        kh = sach_ke_hoach([chuong(-3, 4), chuong(5, 99)], cues)
        assert [(c["srt_from"], c["srt_to"]) for c in kh] == [(1, 4), (5, 10)]

    def test_danh_so_chuong_va_kep_cau_ban_le(self):
        cues = [cue(i) for i in range(1, 11)]
        kh = sach_ke_hoach([chuong(1, 5, key_line=4), chuong(6, 10, key_line=2)], cues)
        assert [c["chuong"] for c in kh] == [1, 2]
        assert kh[0]["key_line"] == 4
        assert kh[1]["key_line"] == 0, "câu bản lề nằm ngoài chương thì bỏ, không trỏ bừa"

    def test_rac_thi_tra_rong_chu_khong_nem(self):
        cues = [cue(i) for i in range(1, 5)]
        assert sach_ke_hoach("khong phai json", cues) == []
        assert sach_ke_hoach({"chapters": "x"}, cues) == []
        assert sach_ke_hoach([{"srt_from": "a"}, 7, None], cues) == []
        assert sach_ke_hoach([chuong(1, 4)], []) == []

    def test_thieu_truong_thi_de_rong(self):
        cues = [cue(i) for i in range(1, 5)]
        kh = sach_ke_hoach([{"srt_from": 1, "srt_to": 4}], cues)
        assert kh[0]["place"] == "" and kh[0]["motif"] == ""
        assert kh[0]["key_line"] == 0


# ── khoi_ke_hoach: phần bản đồ cho MỘT khúc ──────────────────────────────────

class TestKhoiKeHoach:
    KH = [chuong(1, 10, title="opening", place="station exit"),
          chuong(11, 20, title="apartment", place="one-room apartment"),
          chuong(21, 30, title="study", place="university lab"),
          chuong(31, 40, title="close", place="riverside path")]

    def _kh(self):
        return sach_ke_hoach(self.KH, [cue(i) for i in range(1, 41)])

    def test_chi_dua_chuong_cham_vao_khuc(self):
        khoi = khoi_ke_hoach(self._kh(), [cue(i) for i in range(12, 25)])
        assert "Chapter 2 of 4" in khoi and "Chapter 3 of 4" in khoi
        assert "Chapter 1 of 4" not in khoi and "Chapter 4 of 4" not in khoi

    def test_noi_chuong_truoc_va_sau_de_khuc_biet_minh_o_dau(self):
        khoi = khoi_ke_hoach(self._kh(), [cue(i) for i in range(12, 25)])
        assert "Before your lines" in khoi and '"opening"' in khoi
        assert "After your lines" in khoi and '"close"' in khoi
        assert "do not restage" in khoi and "do not start" in khoi

    def test_khuc_dau_khong_co_chuong_truoc_khuc_cuoi_khong_co_chuong_sau(self):
        dau = khoi_ke_hoach(self._kh(), [cue(i) for i in range(1, 8)])
        cuoi = khoi_ke_hoach(self._kh(), [cue(i) for i in range(35, 41)])
        assert "Before your lines" not in dau and "After your lines" in dau
        assert "After your lines" not in cuoi and "Before your lines" in cuoi

    def test_co_cau_ban_le_va_bao_doi_bo_canh(self):
        khoi = khoi_ke_hoach(self._kh(), [cue(i) for i in range(1, 12)])
        assert "turns at line 1" in khoi
        assert "biggest visual change" in khoi
        assert "location_used" in khoi

    def test_khong_co_ban_do_thi_rong_va_loi_nhac_y_nhu_cu(self):
        assert khoi_ke_hoach([], [cue(1)]) == ""
        assert khoi_ke_hoach(self._kh(), []) == ""
        chu = dien_khuon("a\n<<KE_HOACH>>\nb", {"KE_HOACH": khoi_ke_hoach([], [cue(1)])})
        assert chu == "a\n\nb"


# ── Lượt gọi trong tab Tự động: không bao giờ làm hỏng lượt chạy ─────────────

class KenhGia:
    mo_hinh = "x"
    ngon_ngu = "ja"
    engine = "veo3"
    style = {"audience_language": "Japanese"}

    def __init__(self, prompt):
        self.prompt = prompt


def _bc(prompt, tra):
    from core.auto_khau import BoiCanh

    def goi(loi_nhac, **_k):
        goi.da_goi.append(loi_nhac)
        return tra
    goi.da_goi = []
    bc = BoiCanh(goc=".", kenh=KenhGia(prompt), goi_chat=goi, on_log=lambda _d: None)
    return bc, goi


def _luot(tmp_path):
    from core.auto import LuotChay
    return LuotChay(ma_kenh="TL4-T7", ma_luot="0001", thu_muc=str(tmp_path))


class TestKeHoachHinhTrongTabTuDong:
    def test_thieu_prompt_thi_khong_goi_AI(self, tmp_path):
        from core.auto_khau import _ke_hoach_hinh
        bc, goi = _bc({}, "")
        assert _ke_hoach_hinh(bc, _luot(tmp_path), [cue(1), cue(2)]) == []
        assert goi.da_goi == []

    def test_AI_tra_rac_thi_tra_rong_khong_nem(self, tmp_path):
        from core.auto_khau import _ke_hoach_hinh
        bc, goi = _bc({"7-ke-hoach.md": "map <<SRT>>"}, "khong phai json")
        assert _ke_hoach_hinh(bc, _luot(tmp_path), [cue(1), cue(2)]) == []
        assert len(goi.da_goi) == 2, "hỏi lại đúng một lần bằng khoá mới rồi thôi"

    def test_ra_ban_do_thi_ghi_tep_va_lan_sau_khong_goi_lai(self, tmp_path):
        from core.auto_khau import TEP_KE_HOACH, _ke_hoach_hinh
        tra = json.dumps({"chapters": [chuong(1, 2), chuong(3, 4, place="cafe")]})
        bc, goi = _bc({"7-ke-hoach.md": "map <<SRT>> <<SO_CHUONG>> <<TITLE>>"}, tra)
        cues = [cue(i) for i in range(1, 5)]
        kh = _ke_hoach_hinh(bc, _luot(tmp_path), cues)
        assert [c["place"] for c in kh] == ["apartment", "cafe"]
        assert os.path.isfile(os.path.join(str(tmp_path), TEP_KE_HOACH))
        assert "<<" not in goi.da_goi[0]
        # Chạy tiếp: đọc tệp, không hỏi AI lần hai.
        bc2, goi2 = _bc({"7-ke-hoach.md": "map <<SRT>>"}, "")
        assert _ke_hoach_hinh(bc2, _luot(tmp_path), cues) == kh
        assert goi2.da_goi == []

    def test_khuc_nhan_dung_phan_ban_do_cua_no(self, tmp_path):
        from core.auto_khau import _hoi_chia_canh
        tra = json.dumps({"scenes": [{"srt_from": 1, "srt_to": 2, "img_prompt": "a",
                                      "video_prompt": "b"}]})
        bc, goi = _bc({}, tra)
        kh = sach_ke_hoach([chuong(1, 2, place="station"), chuong(3, 4, place="cafe")],
                           [cue(i) for i in range(1, 5)])
        _hoi_chia_canh(bc, _luot(tmp_path), "x\n<<KE_HOACH>>\ny <<SRT>>", [cue(1), cue(2)],
                       0, 2, 8.0, ke_hoach=kh)
        assert "station" in goi.da_goi[0] and "STORY MAP" in goi.da_goi[0]
        assert "<<" not in goi.da_goi[0]
        # Không có bản đồ: lời nhắc y như trước, không sót chỗ trống.
        _hoi_chia_canh(bc, _luot(tmp_path), "x\n<<KE_HOACH>>\ny <<SRT>>", [cue(1), cue(2)],
                       0, 2, 8.0)
        assert "STORY MAP" not in goi.da_goi[1] and "<<" not in goi.da_goi[1]


# ── Ba nơi giữ prompt phải cùng một bản, và bản ấy phải nói đúng luật ────────

def _doc(kenh, ten):
    with open(os.path.join(GOC, "CHANNEL", kenh, "prompt", ten), encoding="utf-8") as t:
        return t.read()


class TestPromptBaNoi:
    @pytest.mark.parametrize("ten", ["7-canh.md", "7-ke-hoach.md"])
    def test_ba_noi_cung_mot_ban(self, ten):
        ban = {_doc(k, ten) for k in BA_NOI}
        assert len(ban) == 1, "{0} lệch giữa khuôn / TL4-T7 / _MAU-GON".format(ten)

    def test_7_canh_nhan_ban_do_va_noi_ro_ba_loi_thoat_cua_nguoi_xem(self):
        chu = " ".join(_doc("TL4-T7", "7-canh.md").split())
        assert "<<KE_HOACH>>" in chu
        # Ba lỗi đo được trên ảnh thật, mỗi lỗi một luật:
        assert "REAL, NAMED place" in chu                    # sa mạc đào
        assert "The expression is NOT locked" in chu         # cười mọi cảnh
        assert "ONLY pure-white figure" in chu               # ai là nv1?
        assert "a new chapter is a new place" in chu         # không có chương
        assert "at least one third of the frame height" in chu
        assert "not a metaphor" in chu                       # mở đầu = nhận ra mình
        # Luật cũ vẫn còn — chúng đo được trên video thật, không bỏ.
        assert "HARD CEILING" in chu and "DIFFERENT line of narration" in chu
        assert "NEVER describe its face" in chu
        assert '"expression"' in chu and '"location_used"' in chu

    def test_7_ke_hoach_co_du_o_dien_va_doi_JSON_chapters(self):
        chu = _doc("TL4-T7", "7-ke-hoach.md")
        for o in ("<<SRT>>", "<<DONG_CUOI>>", "<<SO_CHUONG>>", "<<TONG_GIAY>>",
                  "<<AUDIENCE_CULTURE_NOTE>>", "<<CULTURAL_METAPHORS>>"):
            assert o in chu, o
        assert '"chapters"' in chu and '"key_line"' in chu
        assert "No two consecutive chapters share a place" in chu

    def test_7_ke_hoach_nam_trong_danh_sach_buoc_de_kenh_doc_duoc(self):
        from core.kenh import BUOC_BAT_BUOC, BUOC_PROMPT
        ten = [t for t, _m in BUOC_PROMPT]
        assert "7-ke-hoach.md" in ten
        assert ten.index("7-ke-hoach.md") < ten.index("7-canh.md")
        assert "7-ke-hoach.md" not in BUOC_BAT_BUOC, "thiếu bản đồ vẫn phải chạy được"


class TestStyleKhongEpSaMacDaoVaNuCuoi:
    """`image_style` đi vào ĐUÔI của 100% prompt — nó ép gì là mọi cảnh có nấy."""

    def _style(self, duong):
        from core.kenh import doc_yaml
        return doc_yaml(os.path.join(GOC, "CHANNEL", *duong))

    @pytest.mark.parametrize("duong", [("TL4-T7", "style.yaml"),
                                       ("_KHUON", "ve", "trang-tron-nen-dao", "ve.yaml")])
    def test_khong_ep_doi_may_va_nu_cuoi_vao_moi_canh(self, duong):
        st = self._style(duong)
        for khoa in ("image_style", "reference_lock", "default_character_prompt"):
            chu = st[khoa].lower()
            assert "smiling" not in chu and "tongue" not in chu, (khoa, "khoá nụ cười")
            assert "hills" not in chu and "cloud" not in chu, (khoa, "ép đồi mây")
        assert "expression" in st["image_style"].lower()
        assert "everyday place" in st["image_style"].lower()
        assert "only pure-white figure" in st["image_style"].lower()
        assert "no second white figure" in st["negative_prompt"].lower()
        assert "no dark or cold palette" not in st["negative_prompt"].lower(), (
            "cấm tối là cấm luôn cảnh đêm phòng trọ, konbini — thứ khán giả nhận ra")
