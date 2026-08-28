# -*- coding: utf-8 -*-
"""Tệp `.srt` phải mang **đúng chữ của tệp `.txt`**, không có ngoại lệ nào.

Khách báo 28/08/2026: *"có tình trạng srt bị sai nội dung — có thể việc nhận
diện nó bị sai"*.

Họ nói đúng, và chỗ hở nằm ngay trong mã: khi tỉ lệ khớp giữa kịch bản và thứ
máy nghe được tụt xuống dưới `NGUONG_KHOP`, `core/phu_de.py` **quay về dùng
nguyên thứ máy nghe được** làm chữ phụ đề. Nghĩa là đúng lúc bộ nghe tỏ ra tệ
nhất thì tool lại tin nó nhất — và ghi cái nghe nhầm ấy vào tệp giao cho khách.

Ba bài đầu khoá lại luật mới: **có kịch bản thì chữ luôn là chữ kịch bản.** Tỉ
lệ khớp thấp chỉ còn ảnh hưởng tới mốc thời gian, không bao giờ tới chữ.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.phu_de import (  # noqa: E402
    NGUONG_KHOP, do_khop_voi_kich_ban, doc_srt, sua_srt_theo_txt, tao_phu_de,
    viet_srt,
)
from core.phu_de_lo import Cap, ghep_cap, lam_mot_cap  # noqa: E402

#: Kịch bản thật của khách: có tên riêng, có số — đúng những thứ bộ nghe nhỏ
#: hay nghe nhầm nhất.
KICH_BAN = (
    "Năm 1258, quân Nguyên Mông lần đầu tràn qua ải Bắc. "
    "Trần Thủ Độ nói một câu mà cả triều đình còn nhắc mãi. "
    "Đầu thần chưa rơi xuống đất, xin bệ hạ đừng lo. "
    "Ba mươi năm sau, họ quay lại lần thứ ba."
)


def _bo_nghe(chu: str, giay_moi_tu: float = 0.4):
    """Dựng một bộ nghe giả đọc ra `chu`, mỗi từ `giay_moi_tu` giây."""
    tu = chu.split()

    def nghe(*_a, **_k):
        return [(t, i * giay_moi_tu, (i + 1) * giay_moi_tu)
                for i, t in enumerate(tu)]

    return nghe


class TestChuLuonLaChuKichBan:

    def test_may_nghe_sai_hoan_toan_thi_chu_van_dung(self, monkeypatch):
        """Đây chính là lỗi khách báo, viết lại thành một bài kiểm."""
        from core import phu_de

        monkeypatch.setattr(phu_de, "do_dai_tieng", lambda _d: 40.0)
        nghe = _bo_nghe("con mèo trèo lên cây cau hỏi thăm chú chuột đi đâu "
                        "vắng nhà chú chuột đi chợ đường xa mua mắm mua muối")
        ket = tao_phu_de("a.mp3", KICH_BAN, ngon_ngu="vi", nghe=nghe)

        assert ket.cau, "sai chữ thì chữa chữ, không phải bỏ cả tệp"
        assert ket.ty_le_khop < NGUONG_KHOP, "bài này phải chạy đúng nhánh hỏng"
        assert do_khop_voi_kich_ban(ket.cau, KICH_BAN) == 1.0
        gop = " ".join(c.chu for c in ket.cau)
        assert "Trần Thủ Độ" in gop and "1258" in gop
        assert "mèo" not in gop, "không một chữ nào của máy nghe được lọt vào"

    def test_tu_khai_la_moc_gio_chi_uoc_luong(self, monkeypatch):
        """Chữ cứu được, mốc giờ thì không — và phải nói thẳng ra."""
        from core import phu_de

        monkeypatch.setattr(phu_de, "do_dai_tieng", lambda _d: 40.0)
        ket = tao_phu_de("a.mp3", KICH_BAN, ngon_ngu="vi",
                         nghe=_bo_nghe("hoàn toàn không liên quan gì cả"))
        assert ket.chu_dung_kich_ban and ket.moc_uoc_luong
        assert not ket.dang_tin, "tool phải tự khai để khách còn xem lại"

    def test_rai_het_do_dai_file_tieng_khong_dung_o_cho_may_nghe_bo_do(
            self, monkeypatch):
        """Bộ nghe bỏ dở giữa chừng là lý do thường gặp nhất làm tỉ lệ tụt.

        Lúc ấy mốc cuối của nó chỉ là chỗ nó dừng. Rải cả kịch bản vào quãng
        cụt đó thì phụ đề chạy hết từ giữa video.
        """
        from core import phu_de

        monkeypatch.setattr(phu_de, "do_dai_tieng", lambda _d: 120.0)
        ket = tao_phu_de("a.mp3", KICH_BAN, ngon_ngu="vi",
                         nghe=_bo_nghe("nghe được vài chữ rồi thôi", 0.3))
        assert ket.tong_giay > 100, (
            "phải rải theo độ dài THẬT của file tiếng, không theo chỗ bộ nghe "
            "dừng lại")

    def test_khong_co_kich_ban_thi_moi_duoc_dung_thu_may_nghe(self):
        """Đường duy nhất còn lại — và nó phải tự khai là không đáng tin."""
        ket = tao_phu_de("a.mp3", "   ", ngon_ngu="vi",
                         nghe=_bo_nghe("máy nghe được chừng này thôi"))
        assert ket.cau and not ket.chu_dung_kich_ban
        assert not ket.dang_tin


class TestNgheDungTuNhungSaiDau:
    """Bộ nghe nhỏ sai **dấu** nhiều hơn sai từ. Đừng tính đó là nghe nhầm.

    Mỗi ký tự không khớp là một ký tự **mất mốc thời gian thật**, phải nội suy
    từ hai bên. Một bài tiếng Việt bị bỏ dấu hết là 30% số ký tự mất mốc — chưa
    đủ để rơi xuống dưới `NGUONG_KHOP`, nhưng đủ để ranh giới từng câu xê dịch.
    So sau khi bỏ dấu thì cùng bài ấy khớp trọn vẹn.
    """

    #: Đúng từng từ, sai dấu ở mười mấy chỗ. Kiểu sai thật của `whisper base`.
    NGHE_SAI_DAU = (
        "Năm 1258, quan Nguyên Mong lan đầu tran qua ai Bắc. "
        "Tran Thu Đo nói một câu mà cả triều đinh còn nhắc mai. "
        "Đầu thần chưa rơi xuong đất, xin bệ hạ đừng lo. "
        "Ba mươi năm sau, họ quay lai lần thứ ba."
    )

    #: Bộ nghe trả về bản không dấu hoàn toàn — cũng là chuyện thường gặp.
    NGHE_KHONG_DAU = (
        "Nam 1258, quan Nguyen Mong lan dau tran qua ai Bac. "
        "Tran Thu Do noi mot cau ma ca trieu dinh con nhac mai. "
        "Dau than chua roi xuong dat, xin be ha dung lo. "
        "Ba muoi nam sau, ho quay lai lan thu ba."
    )

    def test_sai_dau_van_khop_tron_ven(self):
        ket = tao_phu_de("a.mp3", KICH_BAN, ngon_ngu="vi",
                         nghe=_bo_nghe(self.NGHE_SAI_DAU))
        assert ket.ty_le_khop == 1.0, (
            "sai dấu không phải là nghe nhầm — mọi ký tự vẫn phải có mốc thật")
        assert ket.dang_tin
        assert do_khop_voi_kich_ban(ket.cau, KICH_BAN) == 1.0

    def test_bo_dau_hoan_toan_van_khop_tron_ven(self):
        ket = tao_phu_de("a.mp3", KICH_BAN, ngon_ngu="vi",
                         nghe=_bo_nghe(self.NGHE_KHONG_DAU))
        assert ket.ty_le_khop == 1.0
        assert ket.dang_tin and do_khop_voi_kich_ban(ket.cau, KICH_BAN) == 1.0


class TestChuaTepSrtCoSan:
    """Đã có `.srt` mốc giờ đúng, chữ sai — chỉ thay chữ, giữ nguyên giờ."""

    def _srt_sai_chu(self, tmp_path):
        that = tao_phu_de("a.mp3", KICH_BAN, ngon_ngu="vi",
                          nghe=_bo_nghe(KICH_BAN))
        assert that.dang_tin
        hong = []
        for c in that.cau:
            hong.append(type(c)(so=c.so, bat_dau=c.bat_dau,
                                ket_thuc=c.ket_thuc,
                                chu="máy nghe nhầm ra câu này"))
        duong = str(tmp_path / "cu.srt")
        viet_srt(duong, hong)
        return duong, that

    def test_thay_chu_va_giu_moc_gio(self, tmp_path):
        cu, that = self._srt_sai_chu(tmp_path)
        moi = str(tmp_path / "moi.srt")
        ket = sua_srt_theo_txt(cu, KICH_BAN, moi, ngon_ngu="vi")

        assert do_khop_voi_kich_ban(ket.cau, KICH_BAN) == 1.0
        assert os.path.isfile(moi)
        doc_lai = doc_srt(open(moi, encoding="utf-8").read())
        assert len(doc_lai) == len(ket.cau)
        # Tệp cũ chỉ sai chữ nên tổng thời lượng phải giữ nguyên.
        assert abs(doc_lai[-1].ket_thuc - that.cau[-1].ket_thuc) < 1.0

    def test_khong_de_ghi_de_mat_tep_cu(self, tmp_path):
        """Chữa xong mà tệp cũ biến mất là khách hết đường đối chiếu."""
        cu, _ = self._srt_sai_chu(tmp_path)
        cu_truoc = open(cu, encoding="utf-8").read()
        ket = lam_mot_cap(Cap(srt_cu=cu, chu=str(tmp_path / "kb.txt")))
        # Chưa có tệp kịch bản thì phải báo lỗi, đừng ghi bừa.
        assert not ket.xong

        (tmp_path / "kb.txt").write_text(KICH_BAN, encoding="utf-8")
        ket = lam_mot_cap(Cap(srt_cu=cu, chu=str(tmp_path / "kb.txt")),
                          ngon_ngu="vi")
        assert ket.xong and ket.khop_chu == 1.0
        assert os.path.abspath(ket.srt) != os.path.abspath(cu)
        assert open(cu, encoding="utf-8").read() == cu_truoc


class TestGhepCap:
    """Ghép sai một cặp là một video mang phụ đề của video khác."""

    def test_trung_ten_du_khac_dau_va_khac_cach_viet(self):
        cap = ghep_cap(["v/Bài 01.mp3"], ["c/bai-01.txt"])
        assert cap[0].chay_duoc and cap[0].chu == "c/bai-01.txt"

    def test_trung_so_khi_ten_khac_han(self):
        cap = ghep_cap(["v/voice_12.mp3"], ["c/kich-ban-12.txt"])
        assert cap[0].chay_duoc

    def test_mot_luot_chay_cua_tab_tu_dong(self):
        """`2-giong-doc.mp3` và `1-kich-ban.txt`: tên chẳng liên quan gì nhau."""
        cap = ghep_cap(["r/2-giong-doc.mp3"], ["r/1-kich-ban.txt"])
        assert cap[0].chay_duoc

    def test_khong_ghep_duoc_thi_noi_ra_chu_khong_doan_bua(self):
        cap = ghep_cap(["v/a.mp3", "v/b.mp3"], ["c/hoan-toan-khac.txt"])
        assert len(cap) == 2
        assert not any(c.chay_duoc for c in cap)
        assert all(c.van_de for c in cap)

    def test_mot_file_kich_ban_khong_dung_cho_hai_file_tieng(self):
        """Dùng lại một kịch bản cho file thứ hai là ghép bừa."""
        cap = ghep_cap(["v/bai-01.mp3", "v/bai-01-ban-2.mp3"],
                       ["c/bai-01.txt"])
        assert sum(1 for c in cap if c.chay_duoc) <= 1


class TestDonKichBanTruocKhiEp:
    """Chữ ghi lên màn hình phải là chữ đã thành tiếng, không hơn không kém."""

    def test_ghi_chu_trong_ngoac_vuong_khong_lot_vao_phu_de(self, tmp_path):
        from core.phu_de_lo import doc_kich_ban

        duong = tmp_path / "kb.txt"
        duong.write_text("[nhạc nền] Xin chào **các bạn**.\n"
                         "Hôm nay trời đẹp.", encoding="utf-8")
        sach = doc_kich_ban(str(duong))
        assert "nhạc nền" not in sach and "**" not in sach
        assert "Xin chào các bạn" in sach
