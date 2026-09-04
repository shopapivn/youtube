# -*- coding: utf-8 -*-
"""Chạy CẢ khâu kịch bản với một AI bẩn, và đòi tệp ra phải sạch.

Khác `test_ghi_chu_ky_thuat.py` ở chỗ: bài ấy kiểm từng hàm rời, bài này chạy
đúng đường dây thật — `_khau_kich_ban` → viết → chấm → hoàn thiện → rà soát →
nắn độ dài → ghi `1-kich-ban.txt` — với một `goi_chat` giả bôi ghi chú kỹ
thuật vào **mọi** lượt trả về.

Vì lỗi khách báo 28/08/2026 không nằm ở một hàm nào cả. Nó nằm ở chỗ **nối**:
hàm dọn có sẵn, nhưng chỉ được gọi ở hai trong năm cửa AI trả chữ về, và cửa
không ai gác lại đúng là cửa CUỐI. Bài kiểm từng hàm sẽ xanh hết mà khách vẫn
nghe thấy "Đã chèn 32 thẻ cảm xúc" giữa video.

Ba tầng chắn, và bài kiểm này đòi cả ba cùng đứng:

    lời nhắc hệ thống   `core.goi_van_ban.CHI_TRA_NOI_DUNG` — đừng viết ra
    dọn                 `_don_ban` ở cả năm cửa
    chặn                `_kiem_ban_sach` — còn sót thì DỪNG, đừng đem đi đọc
"""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auto import LuotChay, TrangThaiKhau  # noqa: E402
from core.auto_khau import BoiCanh, _do_doc, _khau_kich_ban  # noqa: E402
from core.kenh import Kenh  # noqa: E402
from core.su_co import LoiNoiDung  # noqa: E402

#: Những bước lời nhắc SINH RA CHỮ ĐEM ĐI ĐỌC. Bước chấm điểm (trả JSON),
#: SEO, chia cảnh, ảnh bìa, nhạc không nằm đây — chữ của chúng không vào
#: giọng đọc, nên không cần và không nên dặn giống.
RA_CHU = ("2-viet.md", "2c-hoan-thien.md", "3-sua.md", "4-do-dai.md",
          "5-hoan-thien.md")

#: Thân bài giả, đủ dài để qua sàn "kịch bản quá ngắn".
LOI_DOC = "Ngày xưa có một chú mèo nhỏ sống bên bờ suối.\n" * 90

#: Đúng những thứ khách nghe thấy trong video, chép theo lời họ báo:
#: *"nó là cái AI miêu tả kết quả lại đi kèm vào"*.
BAN_GHI_CHU = (
    "Dưới đây là kịch bản đã rà soát, sẵn sàng đưa vào voice:\n"
    "\n"
    + LOI_DOC +
    "\n"
    "---\n"
    "\n"
    "Ghi chú: đã chèn 32 thẻ cảm xúc ElevenLabs v3.\n"
    "- Sửa 3 chỗ lệch tiếng\n"
    "- Tách câu ở đoạn 4\n"
    "Tổng: 4.850 ký tự.\n"
)

#: Mọi mảnh KHÔNG được còn lại trong tệp đem đi đọc.
RAC = ("Dưới đây là", "rà soát", "Ghi chú", "ElevenLabs", "lệch tiếng",
       "Tách câu ở đoạn", "4.850", "---")


class _AIBan:
    """AI trả về bài kèm ghi chú ở **mọi** lượt gọi.

    Cố ý bẩn ở mọi bước chứ không chỉ bước cuối: chính vì bản trước chỉ dọn ở
    bước đầu mà ghi chú của bước nắn độ dài đi thẳng ra tệp.
    """

    def __init__(self, ban=BAN_GHI_CHU):
        self.lan = []
        self._ban = ban

    def __call__(self, loi_nhac, mo_hinh="", khoa="", toi_da_token=8192, **kw):
        self.lan.append(khoa)
        return self._ban


def _kenh(**kw):
    mac = dict(
        ma="T-BAN", ngon_ngu="vi", voice_id="v", phut_muc_tieu=10,
        ky_tu_moi_phut=300,
        prompt={"2-viet.md": "viết <<COMPETITOR_TRANSCRIPT>>",
                "3-sua.md": "rà soát <<DRAFT>>",
                "4-do-dai.md": "nắn <<CHARS>> <<DRAFT>>"})
    mac.update(kw)
    return Kenh(**mac)


@pytest.fixture(autouse=True)
def _thao_van_nhip():
    """Tháo van nhịp gọi chung trong lúc chạy bài kiểm này.

    `core.su_co.NHIP` là **một cái van cho cả tiến trình**: 60 lượt gọi mỗi
    phút. Bài kiểm này chạy khâu kịch bản cho từng kênh mẫu, mỗi lượt vài lời
    gọi — đầy van rất nhanh.

    Và khi đầy, `NhipGoi.xin` gọi `ngu(cho)`. Bài kiểm truyền `ngu` rỗng (để
    khỏi ngồi đợi thật), nên vòng lặp ấy **quay không, đốt một lõi CPU** cho
    tới khi đồng hồ thật trôi qua 60 giây. Đo được: cả tệp kiểm mất đúng
    60,0 giây, và toàn bộ nằm trong vòng quay ấy.

    Không đụng gì tới nhịp thật lúc chạy — van vẫn nguyên với người dùng.
    Ở đây chỉ dựng một cái van rộng riêng cho tiến trình test, rồi trả lại.
    """
    from core import su_co

    cu = su_co.NHIP
    su_co.NHIP = su_co.NhipGoi(moi_phut=1_000_000)
    try:
        yield
    finally:
        su_co.NHIP = cu


def _khong_ra_mang(*_a, **_k):
    """Chặn mọi đường ra mạng của khâu này.

    Kênh `story-mau-nuoc` khai `che_do_tieu_de: nguyen_goc` — nó đi TẢI ảnh
    bìa đối thủ về để đọc chữ trên đó. Không chặn thì bài kiểm ngồi chờ hết
    60 giây timeout của HTTP, đúng một lần cho mỗi kênh mẫu kiểu ấy: bộ test
    chậm là bộ test không ai chạy, mà `CLAUDE.md` luật 3 cũng cấm gọi mạng
    trong test. Trả rỗng thì khâu tự đi đường lui (lấy tiêu đề làm chữ bìa).
    """
    return b""


def _chay(d, goi_chat, kenh=None, dau_vao=None):
    bc = BoiCanh(goc=".", kenh=kenh or _kenh(), goi_chat=goi_chat,
                 on_log=lambda _s: None, ngu=lambda _g: None,
                 tai_anh=_khong_ra_mang)
    luot = LuotChay(ma_kenh=bc.kenh.ma, ma_luot="T01", thu_muc=d,
                    dau_vao=dau_vao or {"kich_ban": LOI_DOC})
    _khau_kich_ban(bc)(luot, TrangThaiKhau(ma="kich-ban"))
    with open(os.path.join(d, "1-kich-ban.txt"), encoding="utf-8") as t:
        return t.read()


class TestTepDemDiDocPhaiSach:
    def test_khong_con_mot_manh_ghi_chu_nao(self):
        with tempfile.TemporaryDirectory() as d:
            ra = _chay(d, _AIBan())
        for x in RAC:
            assert x not in ra, x
        assert ra.strip().startswith("Ngày xưa")
        assert ra.strip().endswith("bờ suối.")

    def test_van_giu_du_loi_doc(self):
        """Dọn không được ăn vào bài — đây là nửa quan trọng hơn của phép dọn."""
        with tempfile.TemporaryDirectory() as d:
            ra = _chay(d, _AIBan())
        assert ra.count("Ngày xưa có một chú mèo nhỏ sống bên bờ suối.") == 90

    def test_ghi_chu_o_buoc_NAN_DO_DAI_cung_bi_don(self):
        """Bước nắn độ dài là lượt gọi CUỐI của phần lớn kênh, và là bước
        trước 28/08/2026 không ai gác."""

        class _BanODungBuocCuoi(_AIBan):
            def __call__(self, loi_nhac, **kw):
                self.lan.append(kw.get("khoa", ""))
                if loi_nhac.startswith("nắn"):
                    return BAN_GHI_CHU
                return LOI_DOC

        with tempfile.TemporaryDirectory() as d:
            ra = _chay(d, _BanODungBuocCuoi(),
                       # mục tiêu lệch hẳn để chắc chắn bước nắn có chạy
                       kenh=_kenh(phut_muc_tieu=20))
        for x in RAC:
            assert x not in ra, x

    def test_ra_soat_chay_SAU_buoc_nan_do_dai(self):
        """═══ THỨ TỰ: VIẾT → NẮN → RÀ SOÁT (đảo lại 04/09/2026) ═══

        `3-sua.md` tách mỗi câu một dòng, chèn thẻ cảm xúc và đặt dấu `---`
        ngăn phần. Cả ba đều gắn với BẢN CHỮ CỤ THỂ.

        Thứ tự cũ là viết → rà soát → nắn, nên mỗi lần bước nắn chạy là nó
        viết lại cả bài và thẻ vừa chèn không còn khớp — mã phải vứt bản có
        thẻ đi (`_bo_tep(TEP_CO_THE)`) và bắt khâu giọng đọc chèn lại từ đầu.
        Một lượt gọi AI đổ đi, mỗi lần nắn.

        Bài này giữ thứ tự mới. Nó không đỏ khi có ai đảo lại — nó đỏ khi
        `3-sua.md` chạy TRƯỚC `4-do-dai.md`.
        """
        with tempfile.TemporaryDirectory() as d:
            ai = _AIBan()
            _chay(d, ai,
                  # mục tiêu lệch hẳn để chắc chắn bước nắn có chạy
                  kenh=_kenh(phut_muc_tieu=20))
        buoc = [x for x in ai.lan if "do-dai" in x or "sua" in x]
        assert buoc, ai.lan
        nan = [i for i, x in enumerate(buoc) if "do-dai" in x]
        sua = [i for i, x in enumerate(buoc) if "sua" in x]
        assert nan and sua, (nan, sua, buoc)
        assert max(nan) < min(sua), (
            "bước rà soát phải chạy SAU mọi vòng nắn — nếu không, thẻ cảm xúc "
            "và chỗ tách câu bị bước nắn viết đè lên: {0}".format(buoc))

    def test_do_dai_do_tren_bai_SACH(self):
        """Ghi chú cũng là ký tự. Đo cả ghi chú thì bước nắn tưởng bài đã đủ
        dài, rồi nó cắt bớt lời đọc thật để bù vào.

        ═══ MỞ RỘNG 04/09/2026: XUỐNG DÒNG CŨNG KHÔNG ĐỌC LÊN ═══

        Bài này vốn đòi con số báo ra bằng ĐÚNG `len()` của tệp. Nhưng bước
        `3-sua.md` tách mỗi câu một dòng cho giọng đọc, nên tệp mang 210–406
        ký tự xuống dòng, cộng 6–10 dấu `---` (tool đổi thành quãng lặng thật).

        Đo bốn lượt TL4-T7 — tệp `1-kich-ban.txt` so với chính giọng đọc
        `2-giong-doc.mp3` — thì phần thừa ấy là **5–10%** con số đem đi so:

            lượt   len()   đọc lên   xuống dòng   giọng đọc thật
            0002   3.834    3.404       406        11,97 phút
            0004   4.076    3.848       210        14,90 phút
            0005   4.051    3.820       213        14,84 phút
            0006   4.529    4.143       356        15,05 phút

        Lượt 0006 bị đá ra khỏi dải ±15% đúng **14 ký tự** trong khi nó mang
        356 ký tự xuống dòng — bước nắn bị gọi dậy bởi thứ không có trong
        video. Nên con số báo ra (và con số bước nắn so) phải là chữ ĐỌC LÊN.
        """
        dong = []

        class _Ghi(_AIBan):
            pass

        with tempfile.TemporaryDirectory() as d:
            bc = BoiCanh(goc=".", kenh=_kenh(), goi_chat=_Ghi(),
                         on_log=dong.append, ngu=lambda _g: None)
            luot = LuotChay(ma_kenh="T-BAN", ma_luot="T01", thu_muc=d,
                            dau_vao={"kich_ban": LOI_DOC})
            _khau_kich_ban(bc)(luot, TrangThaiKhau(ma="kich-ban"))
            with open(os.path.join(d, "1-kich-ban.txt"), encoding="utf-8") as t:
                tep = t.read().rstrip("\n")
        that = _do_doc(tep)
        bao = [x for x in dong if "kịch bản:" in x]
        assert bao, dong
        assert str(that) in bao[-1], (bao[-1], that)
        # Nửa còn lại: phải là chữ ĐỌC LÊN, không phải `len()` của tệp — nếu
        # không thì bài trên vẫn xanh khi ai đó lặng lẽ đo lại bằng `len()`.
        assert that < len(tep), (
            "bản mẫu phải CÓ xuống dòng thì bài kiểm mới phân biệt được hai "
            "cách đo")
        assert str(len(tep)) not in bao[-1], (
            "đang báo len() của tệp — xuống dòng và dấu --- không được đọc lên")


class TestChanKhiKhongDonDuoc:
    def test_ghi_chu_GIUA_bai_thi_dung_ca_luot(self):
        """Giữa bài thì cắt mà đoán là mất một câu của bài. Nên dừng — rẻ hơn
        nhiều so với đi tiếp qua giọng đọc, phụ đề và hàng trăm tấm ảnh."""
        ban = (LOI_DOC[:2000]
               + "\nGhi chú của tôi: đã chèn thẻ ElevenLabs v3 vào đây.\n"
               + LOI_DOC[2000:])
        with tempfile.TemporaryDirectory() as d:
            with pytest.raises(LoiNoiDung):
                _chay(d, _AIBan(ban))
            # …và dời bản hỏng sang một bên, không thì lượt sau đọc lại nó.
            assert not os.path.exists(os.path.join(d, "1-kich-ban.txt"))
            assert os.path.exists(
                os.path.join(d, "1-kich-ban-KHONG-DUNG-DUOC.txt"))

    def test_tep_ban_CU_con_ban_hong_thi_cung_bi_chan(self):
        """Khách chạy bản tool cũ đã có sẵn tệp bẩn trên đĩa. Khâu này mở đầu
        bằng `if not ban_nhap:` nên nó bỏ qua cả phần viết — chốt chặn phải
        đứng NGOÀI nhánh ấy thì mới với tới được."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "1-kich-ban.txt"), "w",
                      encoding="utf-8") as t:
                t.write(LOI_DOC + "\nĐã chèn thẻ ElevenLabs v3.\n")
            with pytest.raises(LoiNoiDung):
                _chay(d, _AIBan())
            assert os.path.exists(
                os.path.join(d, "1-kich-ban-KHONG-DUNG-DUOC.txt"))

    def test_bai_sach_thi_khong_ai_dung_toi(self):
        with tempfile.TemporaryDirectory() as d:
            ra = _chay(d, _AIBan(LOI_DOC))
        assert ra.rstrip("\n") == LOI_DOC.strip()


class TestChayThatTungKenhMau:
    """Chạy khâu kịch bản bằng **lời nhắc thật của từng kênh mẫu**.

    Mấy bài trên dùng kênh giả với lời nhắc ba chữ — chúng kiểm cái máy dọn.
    Bài này kiểm **thứ tool phát đi**: nạp đúng `CHANNEL/<kênh>/`, chạy đúng
    chuỗi bước của kênh ấy, với một AI bôi ghi chú vào mọi lượt trả về, rồi
    mở `1-kich-ban.txt` ra soi.

    Kênh mẫu là thứ tool chịu trách nhiệm; kênh khách tự nhân bản thì không.
    Thêm một kênh mẫu mới mà quên câu dặn là bài này đỏ, không cần ai nhớ ra.
    """

    GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _cac_kenh_mau(self):
        from core.kenh import doc_kenh, liet_ke_kenh

        ra = []
        for ma in liet_ke_kenh(self.GOC):
            try:
                k = doc_kenh(self.GOC, ma)
            except Exception:  # noqa: BLE001 — kênh hỏng là việc của bài kiểm khác
                continue
            if k.prompt.get("2-viet.md"):
                ra.append(k)
        return ra

    def test_co_kenh_mau_de_ma_kiem(self):
        assert len(self._cac_kenh_mau()) >= 5

    def test_moi_kenh_mau_ra_tep_sach(self):
        hong = []
        for k in self._cac_kenh_mau():
            with tempfile.TemporaryDirectory() as d:
                try:
                    ra = _chay(d, _AIBan(), kenh=k)
                except LoiNoiDung as loi:
                    # Chốt chặn nổ = chưa dọn được. Với kênh mẫu thì đó vẫn là
                    # hỏng: khách mất một lượt viết, dù không mất video.
                    hong.append("{0}: bị chặn — {1}".format(k.ma, str(loi)[:60]))
                    continue
            con = [x for x in RAC if x in ra]
            if con:
                hong.append("{0}: còn {1}".format(k.ma, con))
            elif not ra.strip().startswith("Ngày xưa"):
                hong.append("{0}: cắt cả vào bài".format(k.ma))
        assert not hong, "kênh mẫu ra tệp bẩn:\n  " + "\n  ".join(hong)


class TestLoiNhacHeThong:
    """Tầng chắn thứ nhất: đừng để AI viết ra ghi chú ngay từ đầu.

    Chốt bằng mã chỉ chặn được bản đã hỏng — mà mỗi bản hỏng là một lượt viết
    mười phút và một lần trừ tiền.
    """

    def test_moi_luot_viet_deu_co_tin_nhan_he_thong(self):
        from core.goi_van_ban import CHI_TRA_NOI_DUNG, tin_nhan_viet

        tin = tin_nhan_viet("viết bài")
        assert tin[0] == {"role": "system", "content": CHI_TRA_NOI_DUNG}
        assert tin[1] == {"role": "user", "content": "viết bài"}

    def test_kem_anh_van_giu_nguyen_khoi(self):
        """Lượt đọc chữ trên ảnh bìa gửi `content` dạng mảng khối — bọc thêm
        tin nhắn hệ thống không được làm hỏng cái mảng ấy."""
        from core.goi_van_ban import tin_nhan_viet

        khoi = [{"type": "text", "text": "đọc"}, {"type": "image"}]
        assert tin_nhan_viet(khoi)[1]["content"] == khoi

    def test_dan_dung_ba_dieu_da_lam_hong_luot_chay_that(self):
        from core.goi_van_ban import CHI_TRA_NOI_DUNG

        chu = CHI_TRA_NOI_DUNG.lower()
        # AI "diễn" một pha ghi tệp vì lời nhắc kênh nói "xuất dạng file txt"
        # (lượt thật TL4-T7/0011, 24/08/2026).
        assert "tệp" in chu
        # Lời dẫn "Đây là…" đi thẳng vào giọng đọc (lượt thật 0019).
        assert "đây là" in chu
        # Ghi chú tả việc vừa làm — đúng thứ khách báo 28/08/2026.
        assert "tóm tắt việc bạn vừa làm" in chu

    def test_tab_TU_DONG_that_su_gui_no_len_cong(self):
        """Đây là chỗ từng thiếu, và là chỗ ra tiền của khách.

        Dò trên mã nguồn vì hàm này nằm trong lớp giao diện: dựng nổi nó cần
        cả cửa sổ Qt lẫn một client thật, mà thứ cần chốt chỉ là *nó có bọc
        lời nhắc hệ thống vào không*.
        """
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(goc, "ui_qt", "trang_auto.py"),
                  encoding="utf-8") as t:
            ma = t.read()
        assert "tin_nhan_viet(noi_dung)" in ma
        assert '[{"role": "user", "content": noi_dung}]' not in ma

    def test_MOI_buoc_ra_chu_cua_MOI_kenh_mau_deu_co_cau_dan(self):
        """Quét thẳng `CHANNEL/` — kênh mẫu là thứ tool phát đi, tool chịu.

        Bài kiểm này quét **mọi bước sinh ra chữ đem đi đọc** của **mọi** kênh
        mẫu, không kể tên từng kênh: thêm kênh mẫu mới mà quên câu dặn là đỏ
        ngay, không cần ai nhớ ra.

        Bước chấm điểm (JSON), SEO, chia cảnh, ảnh bìa, nhạc **không** nằm đây
        — chữ của chúng không đi vào giọng đọc.
        """
        goc = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CHANNEL")
        # Nhiều cách nói cùng một ý, vì lời nhắc mỗi kênh một giọng (có kênh
        # viết bằng tiếng Anh). Đủ MỘT là được.
        cach_noi = ("không tạo file", "không mô tả việc đã làm", "không ghi chú",
                    "no notes", "no code fences")
        thieu = []
        for thu, _t, teps in os.walk(goc):
            for ten in teps:
                if ten not in RA_CHU:
                    continue
                with open(os.path.join(thu, ten), encoding="utf-8") as t:
                    chu = " ".join(t.read().lower().split())
                if not any(c in chu for c in cach_noi):
                    thieu.append(os.path.relpath(os.path.join(thu, ten), goc))
        assert not thieu, "kênh mẫu thiếu câu dặn trả bài sạch:\n  " + \
            "\n  ".join(sorted(thieu))

    def test_chi_co_MOT_ban_loi_dan_trong_ca_tool(self):
        """Bốn bản chép tay là cách lỗi này sống sót: sửa một chỗ, ba chỗ kia
        không ai nhớ. Xem `core/goi_van_ban.CHI_TRA_NOI_DUNG`."""
        goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dem = 0
        for thu in ("core", "ui_qt"):
            for ten in os.listdir(os.path.join(goc, thu)):
                if not ten.endswith(".py"):
                    continue
                with open(os.path.join(goc, thu, ten), encoding="utf-8") as t:
                    if "Chỉ trả về đúng nội dung được yêu cầu" in t.read():
                        dem += 1
        assert dem == 1, "lời nhắc hệ thống bị chép ra {0} chỗ".format(dem)
