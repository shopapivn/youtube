"""Khuôn tạo kênh — ghép ba mảnh thành một kênh chạy được ngay.

Phép kiểm quan trọng nhất trong tệp này là `test_kenh_moi_chay_duoc_ngay`: dựng
kênh xong thì `kiem_kenh` phải im lặng. Vì thứ khuôn thay thế — *Nhân bản rồi
nhớ sửa ba chỗ* — đã hỏng theo đúng cách đó ngoài đời thật: kênh `TL4-T7` trên
đĩa là bản chép của `TL1-T1` khác đúng một dòng `ma:`, vẫn dùng chung `voice_id`
với kênh gốc. Một khuôn mà vẫn để lại việc "nhớ sửa" thì không hơn gì nút cũ.

Phép kiểm quan trọng thứ hai là `TestMayKhongCoPyYAML`. Tệp sinh ra phải đọc
đúng bằng **cả hai** bộ đọc YAML: `PyYAML` trên máy đã cài, và bộ đọc dự phòng
tự viết trong `core/kenh.py` trên máy chưa cài. Lệch nhau thì lời nhắc gửi lên
cổng khác nhau tuỳ máy — mà đó là thứ không ai nghĩ tới khi đi tìm nguyên nhân.

Không gọi mạng, không tốn một đồng nào.
"""

from __future__ import annotations

import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kenh import (  # noqa: E402
    BUOC_PROMPT, TEP_KENH, TEP_STYLE, THU_MUC_NV, THU_MUC_PROMPT, doc_kenh,
    doc_yaml, duong_kenh, kiem_kenh, liet_ke_kenh,
)
from core.khuon import (  # noqa: E402
    KHOA_VAN_HOA, KHOA_VE, THU_MUC_KHUON, LoiKhuon, doc_van_hoa, dung_kenh,
    duong_khuon, kiem_ma_kenh, liet_ke_nganh, liet_ke_van_hoa, liet_ke_ve,
)

KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Một bộ ba dùng được, để các phép kiểm khỏi lặp lại ba mã.
NGANH, VE, VAN_HOA = "tam-ly", "ao-len-than", "vi"


@pytest.fixture(scope="module")
def goc(tmp_path_factory):
    """Một thư mục gốc giả, chỉ có khuôn — không có kênh nào.

    Chép khuôn thật ra chứ không dựng khuôn giả: phép kiểm phải bắt được cả lỗi
    nằm trong dữ liệu khuôn đi kèm tool, không chỉ lỗi trong mã.
    """
    d = tmp_path_factory.mktemp("goc")
    shutil.copytree(os.path.join(KHO, "CHANNEL", THU_MUC_KHUON),
                    os.path.join(str(d), "CHANNEL", THU_MUC_KHUON))
    return str(d)


# ── Đọc khuôn ────────────────────────────────────────────────────────────────


class TestDocKhuon:
    def test_co_du_ba_loai_manh(self, goc):
        assert liet_ke_nganh(goc), "không thấy ngách nào"
        assert len(liet_ke_ve(goc)) >= 3, "phải có ít nhất ba bộ vẽ"
        assert len(liet_ke_van_hoa(goc)) >= 3, "phải có ít nhất ba bộ khán giả"

    def test_moi_bo_co_nhan_tieng_viet(self, goc):
        """Nhãn hiện thẳng lên ô chọn của người dùng, nên phải là tiếng Việt.

        Để lọt mã thư mục (`ao-len-than`) lên giao diện là khách nhìn thấy chữ
        không dấu viết dính — thứ `CLAUDE.md` gọi là "từ kỹ thuật trên giao
        diện".
        """
        for bo in liet_ke_nganh(goc) + liet_ke_ve(goc) + liet_ke_van_hoa(goc):
            assert bo.nhan != bo.ma, "bộ “{0}” chưa đặt `ten:`".format(bo.ma)
            assert bo.nhan.strip() == bo.nhan

    def test_khuon_khong_hien_ra_nhu_mot_kenh(self, goc):
        """`_KHUON` bắt đầu bằng gạch dưới nên không được coi là kênh."""
        assert liet_ke_kenh(goc) == []

    def test_bo_ve_nao_cung_co_du_16_khoa_va_anh_nhan_vat(self, goc):
        for bo in liet_ke_ve(goc):
            thieu = [k for k in KHOA_VE if k not in bo.du_lieu]
            assert not thieu, "bộ vẽ “{0}” thiếu {1}".format(bo.ma, thieu)
            assert os.path.isfile(os.path.join(bo.duong, "nv1.png")), bo.ma

    def test_bo_khan_gia_nao_cung_co_du_5_khoa_va_so_ky_tu(self, goc):
        for bo in liet_ke_van_hoa(goc):
            thieu = [k for k in KHOA_VAN_HOA if k not in bo.du_lieu]
            assert not thieu, "bộ “{0}” thiếu {1}".format(bo.ma, thieu)
            assert int(bo.du_lieu["ky_tu_moi_phut"]) > 0, bo.ma
            assert bo.du_lieu.get("ngon_ngu"), bo.ma

    def test_khong_bo_nao_lan_sang_nua_kia(self, goc):
        """16 khoá hình và 5 khoá văn hoá không được dẫm chân nhau.

        Nếu bộ vẽ cũng khai `audience_culture_note` thì đổi khán giả sẽ không
        đổi hết được phần văn hoá — và triệu chứng là video tiếng Việt mà đạo
        cụ vẫn của Nhật.
        """
        for bo in liet_ke_ve(goc):
            assert not [k for k in KHOA_VAN_HOA if k in bo.du_lieu], bo.ma
        for bo in liet_ke_van_hoa(goc):
            assert not [k for k in KHOA_VE if k in bo.du_lieu], bo.ma


# ── Dựng kênh ────────────────────────────────────────────────────────────────


class TestDungKenh:
    def test_kenh_moi_chay_duoc_ngay(self, goc):
        """Điền giọng đọc là xong — không còn "nhớ sửa ba chỗ" nào cả."""
        dung_kenh(goc, "K-CHAY", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA, voice_id="giong-thu")
        assert kiem_kenh(doc_kenh(goc, "K-CHAY")) == []

    def test_thieu_giong_doc_thi_keu_dung_mot_cau_ve_giong_doc(self, goc):
        """Giọng đọc là thứ duy nhất khuôn không đoán hộ được.

        Nên khi thiếu, nó phải là lời phàn nàn DUY NHẤT — người dùng biết chính
        xác còn một việc phải làm, không phải dò trong một danh sách.
        """
        dung_kenh(goc, "K-THIEU-GIONG", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA)
        thieu = kiem_kenh(doc_kenh(goc, "K-THIEU-GIONG"))
        assert len(thieu) == 1, thieu
        assert "giọng đọc" in thieu[0].lower()

    def test_kenh_moi_hien_ra_trong_o_chon_kenh(self, goc):
        dung_kenh(goc, "K-HIEN", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA, voice_id="g")
        assert "K-HIEN" in liet_ke_kenh(goc)

    def test_style_co_du_ca_21_khoa(self, goc):
        dung_kenh(goc, "K-21", ma_nganh=NGANH, ma_ve=VE, ma_van_hoa=VAN_HOA,
                  voice_id="g")
        st = doc_yaml(os.path.join(duong_kenh(goc, "K-21"), TEP_STYLE))
        thieu = [k for k in KHOA_VE + KHOA_VAN_HOA if k not in st]
        assert not thieu, thieu

    def test_du_tam_tep_loi_nhac_va_giong_ban_goc_tung_byte(self, goc):
        """Lời nhắc là phần nặng nhất của ngách — chép thiếu là kịch bản hỏng."""
        dung_kenh(goc, "K-PROMPT", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA, voice_id="g")
        thu = os.path.join(duong_kenh(goc, "K-PROMPT"), THU_MUC_PROMPT)
        nguon = duong_khuon(goc, "nganh", NGANH, THU_MUC_PROMPT)
        co = [t for t, _m in BUOC_PROMPT
              if os.path.isfile(os.path.join(nguon, t))]
        assert len(co) >= 2, "ngách phải có ít nhất bước 2-viet và 7-canh"
        for t in co:
            a = open(os.path.join(nguon, t), "rb").read()
            b = open(os.path.join(thu, t), "rb").read()
            assert a == b, t

    def test_anh_nhan_vat_lay_dung_cua_bo_ve(self, goc):
        """Đổi nét vẽ mà giữ ảnh cũ là mỗi cảnh một nét khác nhau."""
        dung_kenh(goc, "K-NV", ma_nganh=NGANH, ma_ve="phan-bang-den",
                  ma_van_hoa=VAN_HOA, voice_id="g")
        a = open(duong_khuon(goc, "ve", "phan-bang-den", "nv1.png"), "rb").read()
        b = open(os.path.join(duong_kenh(goc, "K-NV"), THU_MUC_NV,
                              "nv1.png"), "rb").read()
        assert a == b

    def test_anh_nhan_vat_rieng_cua_khach_duoc_uu_tien(self, goc, tmp_path):
        rieng = tmp_path / "cua-toi.png"
        rieng.write_bytes(b"\x89PNG\r\n\x1a\n" + b"anh cua khach")
        dung_kenh(goc, "K-NV-RIENG", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA, voice_id="g", anh_nv=str(rieng))
        b = open(os.path.join(duong_kenh(goc, "K-NV-RIENG"), THU_MUC_NV,
                              "nv1.png"), "rb").read()
        assert b == rieng.read_bytes()

    def test_do_dai_tuy_chon_de_lai(self, goc):
        dung_kenh(goc, "K-PHUT", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA, voice_id="g", phut_muc_tieu=3)
        assert doc_kenh(goc, "K-PHUT").phut_muc_tieu == 3


class TestConSoDiTheoTiengNoi:
    """Ba thứ mà `CHANNEL/README.md` cảnh báo "lấy nhầm của tiếng khác là hỏng".

    Chúng đi kèm bộ khán giả, nên chọn "Nhật Bản" là được trọn bộ số của tiếng
    Nhật. Người dùng không có ô nào để điền sai.
    """

    @pytest.mark.parametrize("vh,ngon_ngu,hoa", [
        ("ja", "ja", False), ("vi", "vi", True), ("en", "en", True)])
    def test_ngon_ngu_va_chu_bia_hoa(self, goc, vh, ngon_ngu, hoa):
        ma = "K-TIENG-" + vh
        dung_kenh(goc, ma, ma_nganh=NGANH, ma_ve=VE, ma_van_hoa=vh,
                  voice_id="g")
        k = doc_kenh(goc, ma)
        assert k.ngon_ngu == ngon_ngu
        assert k.chu_bia_hoa is hoa

    def test_so_ky_tu_moi_phut_lay_dung_bo_khan_gia(self, goc):
        """Nhật 298 chứ không phải 832 hay 920 — chênh nhau gần ba lần."""
        for vh in ("ja", "vi", "en"):
            ma = "K-SOKT-" + vh
            dung_kenh(goc, ma, ma_nganh=NGANH, ma_ve=VE, ma_van_hoa=vh,
                      voice_id="g")
            assert (doc_kenh(goc, ma).ky_tu_moi_phut
                    == int(doc_van_hoa(goc, vh).du_lieu["ky_tu_moi_phut"]))

    def test_tieng_nhat_khong_viet_hoa_chu_anh_bia(self, goc):
        dung_kenh(goc, "K-JA-HOA", ma_nganh=NGANH, ma_ve=VE, ma_van_hoa="ja",
                  voice_id="g")
        assert doc_kenh(goc, "K-JA-HOA").chu_bia_hoa is False


class TestMayKhongCoPyYAML:
    """Tệp sinh ra phải đọc y hệt nhau bằng cả hai bộ đọc YAML.

    `core/kenh.py` không bắt khách cài `PyYAML` — nó có bộ đọc dự phòng tự
    viết. Bộ đó không hiểu escape `\\n`, `\\"`, hay `''`. Nên nếu khuôn ghi ra
    một giá trị cần escape, hai loại máy sẽ đọc ra hai chuỗi khác nhau, gửi lên
    cổng hai lời nhắc khác nhau, và không ai đoán ra vì sao.
    """

    def test_hai_bo_doc_cho_cung_ket_qua(self, goc):
        from core.kenh import _yaml_toi_gian

        dung_kenh(goc, "K-YAML", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA, voice_id="g")
        thu = duong_kenh(goc, "K-YAML")
        for ten in (TEP_KENH, TEP_STYLE):
            duong = os.path.join(thu, ten)
            day_du = doc_yaml(duong)
            with open(duong, encoding="utf-8") as tep:
                du_phong = _yaml_toi_gian(tep.read())
            lech = [k for k in day_du
                    if str(day_du[k]) != str(du_phong.get(k))]
            assert not lech, "{0} lệch ở {1}".format(ten, lech)

    def test_moi_khoa_gon_trong_mot_dong(self, goc):
        """Bộ đọc dự phòng đọc theo dòng — giá trị tràn dòng là mất khoá."""
        dung_kenh(goc, "K-DONG", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA, voice_id="g")
        for ten in (TEP_KENH, TEP_STYLE):
            with open(os.path.join(duong_kenh(goc, "K-DONG"), ten),
                      encoding="utf-8") as tep:
                dong = [d for d in tep.read().splitlines()
                        if d.strip() and not d.lstrip().startswith("#")]
            assert all(":" in d and not d.startswith((" ", "\t")) for d in dong)


class TestChanTruocKhiHong:
    def test_ma_kenh_rong_bi_chan(self, goc):
        assert kiem_ma_kenh(goc, "  ")
        with pytest.raises(LoiKhuon):
            dung_kenh(goc, "", ma_nganh=NGANH, ma_ve=VE, ma_van_hoa=VAN_HOA)

    @pytest.mark.parametrize("xau", ["a/b", "a:b", "a*b", 'a"b', "a|b", "a?b"])
    def test_ky_tu_windows_cam_bi_chan(self, goc, xau):
        assert kiem_ma_kenh(goc, xau)

    def test_ma_bat_dau_bang_gach_duoi_bi_chan(self, goc):
        """`_x` sẽ tạo ra một kênh mà chính tool không hiện ra — kênh ma."""
        assert kiem_ma_kenh(goc, "_an")
        assert kiem_ma_kenh(goc, ".an")

    def test_khong_de_len_kenh_dang_co(self, goc):
        dung_kenh(goc, "K-CU", ma_nganh=NGANH, ma_ve=VE, ma_van_hoa=VAN_HOA,
                  voice_id="giong-cu")
        with pytest.raises(LoiKhuon):
            dung_kenh(goc, "K-CU", ma_nganh=NGANH, ma_ve="phan-bang-den",
                      ma_van_hoa="ja", voice_id="giong-moi")
        assert doc_kenh(goc, "K-CU").voice_id == "giong-cu"

    def test_manh_khuon_khong_co_thi_bao_ro(self, goc):
        for kw in ({"ma_nganh": "khong-co"}, {"ma_ve": "khong-co"},
                   {"ma_van_hoa": "khong-co"}):
            tham = {"ma_nganh": NGANH, "ma_ve": VE, "ma_van_hoa": VAN_HOA}
            tham.update(kw)
            with pytest.raises(LoiKhuon):
                dung_kenh(goc, "K-THIEU-MANH", **tham)
            assert not os.path.exists(duong_kenh(goc, "K-THIEU-MANH"))


class TestKhuonDinhKhoaKhongDeRaKenh:
    """Khuôn là thứ người ta chép cho nhau — chặn khoá ngay ở cửa vào.

    `kiem_kenh` cũng quét, nhưng nó quét SAU khi kênh đã nằm trên đĩa. Một
    khuôn dính khoá không được đẻ ra dù chỉ một kênh.
    """

    @staticmethod
    def _goc_dinh_khoa(tmp_path, duong_tuong_doi, dong):
        goc = str(tmp_path / "goc")
        shutil.copytree(os.path.join(KHO, "CHANNEL", THU_MUC_KHUON),
                        os.path.join(goc, "CHANNEL", THU_MUC_KHUON))
        with open(duong_khuon(goc, *duong_tuong_doi), "a",
                  encoding="utf-8") as tep:
            tep.write(dong)
        return goc

    def test_chan_va_khong_tao_thu_muc_nao(self, tmp_path):
        goc = self._goc_dinh_khoa(
            tmp_path, ("ve", VE, "ve.yaml"),
            '\npalette_phu: "sk-abcdefghijklmnopqrstuvwxyz0123"\n')
        with pytest.raises(LoiKhuon) as e:
            dung_kenh(goc, "K-KHOA", ma_nganh=NGANH, ma_ve=VE,
                      ma_van_hoa=VAN_HOA, voice_id="g")
        assert "khoá" in str(e.value).lower()
        assert not os.path.exists(duong_kenh(goc, "K-KHOA"))
        assert liet_ke_kenh(goc) == []

    def test_khoa_giau_trong_tep_loi_nhac_cung_bi_chan(self, tmp_path):
        """Tám tệp lời nhắc được chép NGUYÊN VĂN sang kênh mới.

        Chúng không đi qua chỗ ghép YAML nên không có gì soi chúng — mà
        `7-canh.md` dài hơn tám nghìn ký tự, thừa chỗ giấu một dòng khoá.
        Phép kiểm này từng đỏ: bản đầu chỉ quét hai tệp cấu hình sinh ra.
        """
        goc = self._goc_dinh_khoa(
            tmp_path, ("nganh", NGANH, "prompt", "7-canh.md"),
            "\nAIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q\n")
        with pytest.raises(LoiKhuon) as e:
            dung_kenh(goc, "K-KHOA-MD", ma_nganh=NGANH, ma_ve=VE,
                      ma_van_hoa=VAN_HOA, voice_id="g")
        assert "7-canh.md" in str(e.value)
        assert not os.path.exists(duong_kenh(goc, "K-KHOA-MD"))


class TestKhongDeLaiKenhNuaVoi:
    def test_hong_giua_chung_thi_khong_con_dau_vet(self, goc, monkeypatch):
        """Kênh nửa vời vẫn có `kenh.yaml` nên vẫn hiện trong ô chọn kênh.

        Người dùng chọn phải, bấm Chạy, và tiêu tiền cho một kênh thiếu lời
        nhắc. Nên dựng ở chỗ tạm rồi mới đổi tên vào — hỏng ở đâu cũng không có
        kênh nào ra đời.
        """
        import core.khuon as m

        def gay(*a, **kw):
            raise OSError("đĩa đầy")

        monkeypatch.setattr(m.shutil, "copy2", gay)
        with pytest.raises(LoiKhuon):
            dung_kenh(goc, "K-DUT", ma_nganh=NGANH, ma_ve=VE,
                      ma_van_hoa=VAN_HOA, voice_id="g")
        assert not os.path.exists(duong_kenh(goc, "K-DUT"))
        assert not os.path.exists(duong_kenh(goc, "_tao-K-DUT"))
        assert "K-DUT" not in liet_ke_kenh(goc)


class TestChienLuocDeLen:
    """Chiến lược đè lời nhắc lên ngách — đè, không nhân bản cả bộ."""

    def test_cover_de_dung_ba_tep(self, goc):
        """Ba tệp, không hơn.

        Bản đầu của cover có năm bước: mổ bản gốc ra JSON, dàn ý có ngân sách
        ký tự từng phần, viết từng phần, chấm bảy phép, khâu lại. Chủ dự án bỏ
        nó ngày 19/08/2026: *"đừng quá nhiều yêu cầu vì bản chất AI quá nhiều
        thứ nó sẽ cứng và không hay"* — và bộ hai lời nhắc của TL4 **đã bật
        kiếm tiền nhiều kênh**.

        Sau đó thêm lại đúng MỘT bước, do chính chủ dự án đề: *"có thể có 1
        bước trước khi viết đó là việc phân tích kịch bản đối thủ, để biết nó
        hay chỗ nào và chưa hay chỗ nào"*. Một bước đọc, không phải một cỗ máy.

        Phép kiểm này giữ cover ở đúng cỡ ấy.
        """
        dung_kenh(goc, "K-CL", ma_nganh=NGANH, ma_ve=VE, ma_van_hoa=VAN_HOA,
                  ma_chien_luoc="cover", voice_id="g")
        thu = os.path.join(duong_kenh(goc, "K-CL"), THU_MUC_PROMPT)
        goc_nganh = duong_khuon(goc, "nganh", NGANH, THU_MUC_PROMPT)

        def khac_nganh(ten):
            """Tệp này do chiến lược mang tới — đè lên ngách, hoặc ngách không có."""
            cua_kenh = os.path.join(thu, ten)
            cua_nganh = os.path.join(goc_nganh, ten)
            if not os.path.isfile(cua_kenh):
                return False
            if not os.path.isfile(cua_nganh):
                return True          # chiến lược THÊM tệp mới, không phải đè
            return (open(cua_kenh, "rb").read()
                    != open(cua_nganh, "rb").read())

        khac = [t for t, _m in BUOC_PROMPT if khac_nganh(t)]
        assert sorted(khac) == ["2-viet.md", "2a-phan-tich.md",
                                "3-sua.md"], khac

    def test_cover_hoi_DA_HON_chu_khong_hoi_DA_GIONG(self, goc):
        """Cả khác biệt của cover nằm ở đúng câu hỏi này.

        `3-sua.md` của remake hỏi "đã giống bản gốc chưa" — với cover thì câu
        ấy ngược dấu: bước 2 vừa cố viết hơn, bước 3 lại chấm theo độ giống và
        kéo bài về lại bản gốc.
        """
        dung_kenh(goc, "K-HON", ma_nganh=NGANH, ma_ve=VE, ma_van_hoa=VAN_HOA,
                  ma_chien_luoc="cover", voice_id="g")
        thu = os.path.join(duong_kenh(goc, "K-HON"), THU_MUC_PROMPT)
        with open(os.path.join(thu, "3-sua.md"), encoding="utf-8") as t:
            sua = t.read()
        # Gộp khoảng trắng: lời nhắc bọc dòng ở 79 cột nên câu hỏi có thể bị
        # cắt làm đôi giữa "HƠN" và "CHƯA".
        gon = " ".join(sua.split())
        assert "ĐÃ HAY HƠN BẢN GỐC CHƯA" in gon
        # ═══ BẢN GỐC KHÔNG ĐƯỢC NẰM TRONG BƯỚC SỬA ═══
        #
        # Đo từng mốc trên một lượt chạy thật 19/08/2026, ba mẫu:
        #
        #     sau bước viết  30,5% / 21,4% / 56,9% trùng nguyên văn bản gốc
        #     sau bước sửa   77,6% / 77,0% / 77,5%
        #
        # Bước sửa có bản gốc trong tay thì nó viết về phía bản gốc, bất kể
        # lời nhắc dặn gì — bốn cách diễn đạt khác nhau đều cho cùng kết quả.
        # Bỏ bản gốc ra khỏi bước này, để lại ghi chú của bước phân tích, thì
        # ba mẫu tiếp theo cho 1,8% / 1,5% / 1,5%.
        #
        # Đây là phép kiểm chặn việc ai đó "tiện tay" đính bản gốc lại vào.
        assert "<<COMPETITOR_TRANSCRIPT>>" not in sua
        assert "<<PHAN_TICH>>" in sua
        assert "GIỐNG" not in sua.upper(), "cover không hỏi đã giống chưa"
        # Bước đọc bản gốc phải hỏi cả hai chiều — chỉ hỏi "hay chỗ nào" thì
        # bước viết không có chỗ nào để mà vượt.
        with open(os.path.join(thu, "2a-phan-tich.md"), encoding="utf-8") as t:
            pt = t.read()
        assert "HAY ở chỗ nào" in pt and "CHƯA HAY ở chỗ nào" in pt
        # Câu ElevenLabs là nguyên văn của chủ dự án — đừng "viết lại cho hay".
        for x in ("ElevenLabs", "không bị đều đều", "KHÔNG liền nhau",
                  "KHÔNG BỊ dính chữ"):
            assert x in sua, x

    def test_khong_chon_chien_luoc_thi_giong_het_nganh(self, goc):
        dung_kenh(goc, "K-KHONG-CL", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA, voice_id="g")
        thu = os.path.join(duong_kenh(goc, "K-KHONG-CL"), THU_MUC_PROMPT)
        goc_nganh = duong_khuon(goc, "nganh", NGANH, THU_MUC_PROMPT)
        for t, _m in BUOC_PROMPT:
            p = os.path.join(thu, t)
            if os.path.isfile(p):
                assert (open(p, "rb").read()
                        == open(os.path.join(goc_nganh, t), "rb").read()), t

    def test_kenh_mang_theo_tep_khai_chien_luoc(self, goc):
        """Kênh phải TỰ CHỨA sau khi tạo — khuôn không đụng vào nữa."""
        from core.kenh import TEP_CHIEN_LUOC

        dung_kenh(goc, "K-TU-CHUA", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa=VAN_HOA, ma_chien_luoc="cover", voice_id="g")
        k = doc_kenh(goc, "K-TU-CHUA")
        assert os.path.isfile(os.path.join(duong_kenh(goc, "K-TU-CHUA"),
                                           TEP_CHIEN_LUOC))
        assert k.chien_luoc.get("can_ban_goc") is True


class TestBaKenhNhatTrenDiaThat:
    """TL4 và TL6 chạy remake, TL5 chạy cover — đúng như đã chốt 19/08/2026."""

    @pytest.mark.parametrize("ma", ["TL4-T7", "TL6-T7"])
    def test_remake_dung_nguyen_bo_cua_nganh(self, ma):
        thu = os.path.join(KHO, "CHANNEL", ma)
        if not os.path.isdir(thu):
            pytest.skip("chưa có kênh " + ma)
        nguon = os.path.join(KHO, "CHANNEL", THU_MUC_KHUON, "nganh", NGANH,
                             THU_MUC_PROMPT)
        for t in ("2-viet.md", "3-sua.md"):
            assert (open(os.path.join(thu, THU_MUC_PROMPT, t), "rb").read()
                    == open(os.path.join(nguon, t), "rb").read()), \
                "{0} lệch khỏi bộ chuẩn của ngách".format(ma)

    def test_TL5_dung_cover(self):
        thu = os.path.join(KHO, "CHANNEL", "TL5-T7")
        if not os.path.isdir(thu):
            pytest.skip("chưa có kênh TL5-T7")
        with open(os.path.join(thu, THU_MUC_PROMPT, "3-sua.md"),
                  encoding="utf-8") as t:
            assert "ĐÃ HAY HƠN BẢN GỐC CHƯA" in " ".join(t.read().split())
