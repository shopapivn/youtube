"""Tab **Cài đặt** — mọi nút gạt của tool gom về một chỗ.

Chủ dự án, 15/08/2026: *"cho tool có mục setting để những cài đặt ở tool sẽ tập
trung ở đó"*.

Trước đó tuỳ chọn nằm rải rác: cập nhật thì ở nút cuối thanh bên, cách dựng
video thì trong hộp Quản lý kênh, còn lại thì không có. Người dùng muốn đổi một
thứ phải đoán xem nó nấp ở tab nào.

═══ MỘT DÒNG MỘT VIỆC, VÀ NÓI RÕ TẮT ĐI THÌ SAO ═══

Mỗi tuỳ chọn ở đây là một ô đánh dấu kèm **một câu nói hậu quả**, không phải
một cái tên kỹ thuật. Người dùng tool này không biết lập trình; "bật/tắt
`tu_cap_nhat`" không giúp họ quyết được gì, còn "tắt thì bạn tự bấm khi nào
muốn" thì có.

Lưu ngay khi bấm, không có nút Lưu. Một nút Lưu ở màn hình toàn ô đánh dấu chỉ
tạo thêm một cách để mất thay đổi.
"""

from __future__ import annotations

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QComboBox, QVBoxLayout, QWidget

from core import cai_dat
from core.kenh import GIU_NGUYEN

from .widgets import HangXuongDong, mo_thu_muc, nhan, nut_phu, the, tieu_de_trang

__all__ = ["TrangCaiDat"]

#: Các cỡ video chọn được, xếp từ nét nhất xuống nhanh nhất.
DO_PHAN_GIAI = ("4K", "1440p", "1080p", GIU_NGUYEN)

#: Tuỳ chọn **không phải ô đánh dấu**, nên không nằm trong `MUC` mà có ô riêng.
#:
#: Có danh sách này để bài kiểm vẫn chốt được luật gốc: thêm một tuỳ chọn vào
#: `cai_dat.MAC_DINH` mà quên dựng ô cho nó thì bài kiểm đỏ. Thiếu chốt ấy thì
#: một ngày nào đó có tuỳ chọn chỉ sửa được bằng cách mở tệp JSON — đúng thứ
#: tab này sinh ra để dẹp.
MUC_RIENG = ("do_phan_giai", "muc_song_song")

#: Các mốc công suất gửi việc, `(khoá lưu, nhãn ngắn hiện trên ô chọn)`.
#: Thứ tự = thứ tự hiện ra, từ nhẹ tới mạnh nhất.
MUC_SONG_SONG = (
    ("mac_dinh", "Mặc định"),
    ("nhanh", "Nhanh"),
    ("toi_da", "Tối đa"),
)

#: `(khoá, nhãn, câu giải thích)`. Thứ tự trên màn hình theo đúng thứ tự này.
MUC = (
    ("tu_cap_nhat", "Tự cập nhật khi mở tool",
     "Mở tool lên là tôi tự tải bản mới rồi khởi động lại, xong mới đưa bạn "
     "dùng. Tắt thì tôi chỉ báo có bản mới, bạn tự bấm khi nào tiện — hợp khi "
     "bạn hay để tool chạy dở một mẻ dài."),
    ("hoi_ban_moi", "Hỏi xem có bản mới không",
     "Tắt cái này là tắt luôn cả dòng trên: không hỏi thì không biết có gì để "
     "cập nhật. Chỉ nên tắt khi máy không nối được ra Internet."),
    ("bao_su_co", "Hiện thông báo khi tool gặp lỗi",
     "Tắt thì lỗi vẫn được ghi lại đầy đủ vào workspace/su-co.log, chỉ là "
     "không hiện lên màn hình. Hợp khi bạn để tool chạy qua đêm."),
    # Nhãn phải ngắn: chữ trong ô đánh dấu không tự xuống dòng, nên một nhãn
    # dài kéo cả trang rộng quá mép cửa sổ. Đã đo: thêm hai chữ "(tắt sẵn)" là
    # tab này cần 793px, quá mức 760px, và `test_bo_cuc` đỏ ngay.
    # Trạng thái tắt/bật thì nhìn chính ô đánh dấu là biết.
    ("lam_sach_dau_ai", "Xoá dấu nguồn gốc AI trong tệp",
     "Tắt sẵn. Bật thì trước khi giao, tôi bỏ mấy thẻ dữ liệu ẩn khỏi cả bốn "
     "loại kết "
     "quả — chữ, giọng đọc, ảnh, video. Thẻ đó là “Made with Google AI” và "
     "C2PA, do nhà cung cấp gắn vào. Ảnh KHÔNG bị nén lại nên không mất nét, "
     "video chỉ chép lại nên không mất giây nào.\n"
     "Tôi đo trên kết quả thật của bạn rồi, và phải nói thẳng: kịch bản, giọng "
     "đọc và video cuối VỐN ĐÃ sạch. Chỗ duy nhất còn thẻ là ẢNH BÌA — nó cũng "
     "lên YouTube mà lại gần như nguyên vẹn từ nhà cung cấp.\n"
     "Và nó KHÔNG xoá được SynthID: dấu đó nằm trong chính điểm ảnh, không nằm "
     "trong thẻ. Không công cụ xoá thẻ nào làm được việc đó.\n"
     "Quan trọng nhất: nó KHÔNG thay bạn khai báo với YouTube. Nhãn “nội dung "
     "tổng hợp” là ô bạn tự tích trong Studio, YouTube không đọc thẻ tệp để "
     "quyết. YouTube nói tích ô đó không giảm hiển thị hay tiền — còn KHÔNG "
     "khai mới là thứ khoá kiếm tiền 90 ngày rồi gỡ kênh khỏi YPP."),
    ("the_cam_xuc", "Chèn thẻ cảm xúc trước khi đọc",
     "Tắt sẵn. Bật thì ngay trước lúc gửi chữ đi đọc, tôi nhờ AI cài thẻ cảm "
     "xúc vào những chỗ đáng — chỗ chuyển giọng, chỗ có câu lật, chỗ đáng thở "
     "dài. Áp dụng cho cả tab Tự động lẫn tab Voice.\n"
     "Cổng giọng nói chạy model eleven_v3, đúng loại hiểu được mấy thẻ này.\n"
     "Chèn THƯA, khoảng một thẻ cho 4–6 câu, và chia bài ra từng khúc 2.000 "
     "chữ để AI chèn đều tay chứ không kỹ đầu bài rồi bỏ bê phần sau.\n"
     "AI chỉ được CHÈN, cấm sửa chữ. Tôi gỡ hết thẻ ra so lại với bản gốc — "
     "sai một chữ là tôi vứt khúc đó, đọc bản gốc. Kịch bản của bạn không bao "
     "giờ bị viết lại sau lưng.\n"
     "Thẻ chỉ nằm trong bản đem đi đọc. Phụ đề vẫn là bản sạch — tôi đã thử "
     "thật với cả tiếng Nhật lẫn tiếng Anh: giọng đọc KHÔNG đọc to tên thẻ "
     "lên, và phụ đề không dính ngoặc vuông nào.\n"
     "LƯU Ý QUAN TRỌNG: thẻ làm giọng đọc DÀI RA. Đo thật: tiếng Nhật dài thêm "
     "5%, tiếng Anh dài thêm tới 32%. Kịch bản vốn đã nắn cho khớp độ dài "
     "video bạn nhắm tới, nên bật cái này rồi thì hãy đo lại video ĐẦU TIÊN "
     "trước khi cho chạy hàng loạt.\n"
     "Tốn thêm vài lượt gọi AI viết chữ mỗi lượt chạy — loại rẻ, không phải "
     "loại đắt như ảnh hay clip."),
    ("kich_ban_bang_claude_code", "Kịch bản viết bằng Claude Code",
     "Tắt sẵn. Chỉ bật nếu máy này đã cài Claude Code và đăng nhập gói thuê "
     "bao Claude (Pro/Max) của chính bạn.\n"
     "Bật thì khâu KỊCH BẢN của tab Tự động viết bằng thuê bao đó — không trừ "
     "ví ShopAPI cho phần viết chữ. Ảnh, clip, giọng đọc và lời nhắc ảnh/video "
     "vẫn chạy qua ví ShopAPI như cũ.\n"
     "Khoá ShopAPI KHÔNG được đưa vào Claude Code: lượt viết chạy bằng phiên "
     "đăng nhập của máy, trong một thư mục rỗng, không đọc được gì của tool.\n"
     "Nếu Claude Code chưa cài hoặc chưa đăng nhập, tôi tự quay về ví ShopAPI "
     "và ghi một dòng vào nhật ký — lượt chạy không hỏng vì nút này."),
    ("doi_cao_do_giong", "Đổi nhẹ cao độ giọng đọc",
     "Tắt sẵn. Đây là nút DUY NHẤT trong nhóm này đụng vào chính nội dung, chứ "
     "không chỉ vào thẻ dữ liệu — nên nó tách riêng.\n"
     "Cổng giọng nói chạy trên ElevenLabs, mà ElevenLabs nhúng dấu chìm "
     "SynthID vào âm thanh. Dấu đó nằm trong sóng tiếng nên xoá thẻ không tới "
     "được. Nghiên cứu cho thấy dịch cao độ làm gãy dấu này.\n"
     "Tôi dịch 60 cent — hơn nửa nốt nhạc. Nhạc công mới phân biệt được, người "
     "nghe kể chuyện thì không. Độ dài giữ nguyên tuyệt đối nên phụ đề và cảnh "
     "không xê dịch một mi-li-giây nào.\n"
     "PHẢI NÓI THẬT: tôi KHÔNG tự kiểm được là dấu đã mất hay chưa — máy dò "
     "của Google không công khai. Bạn tự kiểm miễn phí bằng Audio Detector của "
     "ElevenLabs: tải lên bản trước và sau rồi so."),
)


class TrangCaiDat(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._o = {}

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(12)
        doc.addWidget(tieu_de_trang(
            "Cài đặt", "Những thứ bạn cài một lần rồi thôi."))
        doc.addWidget(self._the_cap_nhat())
        doc.addWidget(self._the_video())
        doc.addWidget(self._the_song_song())
        doc.addWidget(self._the_thu_muc())
        doc.addWidget(self._the_thu_vien())
        doc.addWidget(self._the_agent())
        doc.addStretch(1)

    def _phu(self, chu: str):
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    def _the_cap_nhat(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(6)
        v.addWidget(nhan("Cập nhật và thông báo", "h2"))

        dang = cai_dat.doc(self._app.base_dir)
        for khoa, nhan_o, giai_thich in MUC:
            o = QCheckBox(nhan_o)
            o.setChecked(bool(dang.get(khoa)))
            o.stateChanged.connect(
                lambda _s, k=khoa: self._doi(k))
            v.addWidget(o)
            mo = self._phu(giai_thich)
            mo.setContentsMargins(24, 0, 0, 8)
            v.addWidget(mo)
            self._o[khoa] = o
        return khung

    def _the_video(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(6)
        v.addWidget(nhan("Video ra", "h2"))
        v.addWidget(self._phu(
            "Nhà cung cấp trả clip 1280×720, nhỏ hơn cả 1080p. Tôi phóng lên "
            "cỡ bạn chọn ở bước dựng cuối."))

        hang = HangXuongDong()
        hang.addWidget(nhan("Độ phân giải:", "phu"))
        self._o_dpg = QComboBox()
        self._o_dpg.addItems(DO_PHAN_GIAI)
        dang = cai_dat.doc(self._app.base_dir).get("do_phan_giai", "4K")
        self._o_dpg.setCurrentIndex(max(0, self._o_dpg.findText(str(dang))))
        self._o_dpg.setFixedWidth(150)
        self._o_dpg.currentTextChanged.connect(self._doi_dpg)
        hang.addWidget(self._o_dpg)
        v.addLayout(hang)

        # Nói cả cái được lẫn cái mất, bằng số đo được. Chỉ nói "4K nét hơn" là
        # bán một thứ không đúng: phóng lên không tạo thêm chi tiết có thật.
        v.addWidget(self._phu(
            "4K dựng lâu hơn khoảng bốn lần và tệp to hơn khoảng năm lần so "
            "với Giữ nguyên, nhưng KHÔNG tốn thêm đồng nào — đây là thời gian "
            "máy bạn chạy, không phải tiền gọi API.\n"
            "Nói thật: phóng lên không tạo thêm chi tiết có thật, phần nét "
            "thêm ra là máy đoán. Cái được thật là YouTube dùng bộ mã hoá tốt "
            "hơn cho video 4K, nên người xem ở 1080p vẫn thấy sạch hơn.\n"
            "Kênh nào cần khác thì khai riêng trong Quản lý kênh → Dựng "
            "video; khai ở đó thì kênh ấy không theo ô này nữa."))
        return khung

    def _doi_dpg(self, ten: str) -> None:
        if not cai_dat.dat(self._app.base_dir, "do_phan_giai", ten):
            self._app.show_message(
                "Không lưu được cài đặt",
                "Tôi không ghi được vào thư mục workspace. Bạn kiểm tra xem ổ "
                "đĩa còn chỗ trống không.")

    def _the_song_song(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(6)
        v.addWidget(nhan("Công suất gửi", "h2"))
        v.addWidget(self._phu(
            "Máy chủ nhận được rất nhiều việc một lúc và tự xếp hàng. Đây là mức "
            "tôi đẩy việc lên lúc bắt đầu một mẻ."))

        hang = HangXuongDong()
        hang.addWidget(nhan("Mức gửi:", "phu"))
        self._o_ss = QComboBox()
        for _khoa, nhan_o in MUC_SONG_SONG:
            self._o_ss.addItem(nhan_o)
        dang = cai_dat.doc(self._app.base_dir).get("muc_song_song", "mac_dinh")
        self._o_ss.setCurrentIndex(max(0, self._chi_so_muc(dang)))
        self._o_ss.setFixedWidth(150)
        self._o_ss.currentIndexChanged.connect(self._doi_ss)
        hang.addWidget(self._o_ss)
        v.addLayout(hang)

        # Nói thật về tiền: mốc không đổi tổng tiền, chỉ đổi tốc độ tiêu.
        v.addWidget(self._phu(
            "Mặc định là như hiện nay: tăng tốc từ từ, an toàn cho máy yếu và "
            "mạng chậm.\n"
            "Tối đa đẩy cả mẻ đi gần như một phát — hợp khi bạn nhập cả nghìn "
            "ảnh hay clip và muốn xong nhanh nhất. Nó KHÔNG tốn thêm tiền (vẫn "
            "đúng bấy nhiêu việc), chỉ là tiền bị trừ dồn nhanh hơn.\n"
            "Dù chọn mức nào, nếu máy chủ báo quá tải thì tôi tự chậm lại — bạn "
            "không làm hỏng gì được."))
        return khung

    @staticmethod
    def _chi_so_muc(khoa: str) -> int:
        for i, (k, _n) in enumerate(MUC_SONG_SONG):
            if k == khoa:
                return i
        return 0

    def _doi_ss(self, chi_so: int) -> None:
        if not 0 <= chi_so < len(MUC_SONG_SONG):
            return
        khoa = MUC_SONG_SONG[chi_so][0]
        if not self._app.dat_muc_song_song(khoa):
            self._app.show_message(
                "Không lưu được cài đặt",
                "Tôi không ghi được vào thư mục workspace. Bạn kiểm tra xem ổ "
                "đĩa còn chỗ trống không.")

    def _the_thu_muc(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(8)
        v.addWidget(nhan("Thư mục", "h2"))
        v.addWidget(self._phu(
            "Kết quả bạn đã tạo nằm trong PROJECTS. Cập nhật tool không bao "
            "giờ đụng vào thư mục đó, cũng không đụng vào kênh và lời nhắc "
            "bạn đã sửa."))
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Mở thư mục kết quả", self._mo_ket_qua, rong=190))
        hang.addWidget(nut_phu("Mở thư mục tool", self._mo_goc, rong=170))
        hang.addWidget(nut_phu("Xem nhật ký sự cố", self._mo_su_co, rong=180))
        hang.addWidget(nut_phu("Gói nhật ký gửi hỗ trợ", self._goi_nhat_ky,
                               rong=210))
        v.addLayout(hang)
        return khung

    def _the_thu_vien(self) -> QWidget:
        # Bình thường tool tự lo phần này lúc khởi động (xem `core/tu_du.py`).
        # Nút đây là đường sửa tay cho lúc lần tự cài hỏng — mất mạng giữa
        # chừng, ổ đầy — mà bảo khách đi tìm `SETUP.bat` thì họ không tìm.
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(8)
        v.addWidget(nhan("Thư viện", "h2"))
        self._nhan_tv = nhan("", "phu")
        self._nhan_tv.setWordWrap(True)
        self._nhan_tv.setMinimumWidth(1)
        v.addWidget(self._nhan_tv)
        hang = HangXuongDong()
        hang.addWidget(nut_phu("Kiểm tra và cài phần thiếu", self._cai_thieu,
                               rong=230))
        v.addLayout(hang)

        # Công cụ nâng ảnh là một tệp chạy được tải từ mạng về, nên nó phải là
        # một nút bấm chứ không phải một bước tự động. Xem `core/nang_anh.py`.
        self._nhan_na = nhan("", "phu")
        self._nhan_na.setWordWrap(True)
        self._nhan_na.setMinimumWidth(1)
        self._nhan_na.setContentsMargins(0, 10, 0, 0)
        v.addWidget(self._nhan_na)
        hang2 = HangXuongDong()
        self._nut_na = nut_phu("Tải công cụ nâng ảnh", self._tai_nang_anh,
                               rong=210)
        hang2.addWidget(self._nut_na)
        v.addLayout(hang2)

        self._xem_thu_vien()
        return khung

    def _tai_nang_anh(self) -> None:
        from core import nang_anh

        self._nut_na.setEnabled(False)
        self._nhan_na.setText("Đang tải…")
        try:
            duoc, loi_nhan = nang_anh.tai_cong_cu(
                self._app.base_dir, ghi=self._nhan_na.setText)
        except Exception as loi:  # noqa: BLE001
            duoc, loi_nhan = False, str(loi)
        if not duoc:
            self._app.show_message(
                "Chưa tải được công cụ nâng ảnh",
                "{0}.\n\nKhông sao — tool vẫn phóng ảnh bằng phép thường, chỉ "
                "là không nét bằng. Bạn thử lại lúc mạng khoẻ hơn.".format(
                    loi_nhan))
        self._nut_na.setEnabled(True)
        self._xem_thu_vien()

    def _xem_thu_vien(self) -> None:
        try:
            from core import tu_du

            ly_do = tu_du.can_cai(self._app.base_dir)
        except Exception as loi:  # noqa: BLE001
            self._nhan_tv.setText("Không kiểm được: {0}".format(loi))
            return
        self._nhan_tv.setText(
            "Máy đã đủ thư viện, không cần làm gì." if not ly_do else
            "Cần cài thêm: {0}. Bấm nút dưới là tôi cài luôn.".format(ly_do))
        try:
            from core import nang_anh

            co = nang_anh.co_nang_that(self._app.base_dir)
        except Exception:  # noqa: BLE001
            return
        self._nut_na.setEnabled(not co)
        self._nhan_na.setText(nang_anh.mo_ta_cong_cu(self._app.base_dir))

    def _cai_thieu(self) -> None:
        from core import tu_du

        from .cua_so_tu_du import HopTuDu

        ly_do = tu_du.can_cai(self._app.base_dir) or "bạn bấm kiểm tra lại"
        hop = HopTuDu(self._app.base_dir, ly_do, tu_du.cai, self)
        hop.exec_()
        if hop.duoc:
            tu_du.ghi_nhan(self._app.base_dir, tu_du.dau_van(self._app.base_dir))
        self._xem_thu_vien()

    def _the_agent(self) -> QWidget:
        """Gộp "Agent xây tool" vào Cài đặt.

        Chủ dự án, 21/08/2026: *"đi cải thiện cái tab Agen xây tool cho vào cài
        đặt - thiết kế để nó dễ sử dụng"*. Trước đó nó là một tab riêng ở thanh
        bên; nhưng đó là thứ cài một lần rồi thôi — đúng chỗ của Cài đặt.

        Nhúng nguyên `TrangAgent` (chế độ `nhung=True`) thay vì chép lại: mọi
        chốt tiền bạc và logic dò máy nằm gọn một chỗ, sửa một lần ăn cả hai.
        """
        from .trang_agent import TrangAgent  # noqa: PLC0415 — tránh vòng nhập

        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(20, 16, 20, 18)
        v.setSpacing(8)
        v.addWidget(nhan("Agent xây tool", "h2"))
        v.addWidget(self._phu(
            "Cài Claude Code hoặc Codex rồi mở ngay trong thư mục tool, để nhờ "
            "nó sửa chính cái tool này."))
        self._agent = TrangAgent(self._app, nhung=True)
        v.addWidget(self._agent)
        return khung

    # ── Việc ─────────────────────────────────────────────────────────────────

    def _doi(self, khoa: str) -> None:
        bat = self._o[khoa].isChecked()
        if not cai_dat.dat(self._app.base_dir, khoa, bat):
            self._app.show_message(
                "Không lưu được cài đặt",
                "Tôi không ghi được vào thư mục workspace. Bạn kiểm tra xem ổ "
                "đĩa còn chỗ trống không.")
            return
        # Tắt "hỏi bản mới" thì "tự cập nhật" thành vô nghĩa — tắt luôn cho
        # khỏi để lại một ô bật mà không làm gì.
        if khoa == "hoi_ban_moi" and not bat and self._o["tu_cap_nhat"].isChecked():
            self._o["tu_cap_nhat"].setChecked(False)

    def _mo_ket_qua(self) -> None:
        mo_thu_muc(os.path.join(self._app.base_dir, "PROJECTS"))

    def _mo_goc(self) -> None:
        mo_thu_muc(self._app.base_dir)

    def _mo_su_co(self) -> None:
        duong = os.path.join(self._app.base_dir, "workspace", "su-co.log")
        if not os.path.isfile(duong):
            self._app.show_message(
                "Chưa có sự cố nào",
                "Tool chưa ghi nhận lỗi nào. Đó là tin tốt.")
            return
        from .thu_vien_ket_qua import mo_file  # noqa: PLC0415

        mo_file(duong)

    def _goi_nhat_ky(self) -> None:
        """Nén cả thư mục nhật ký thành MỘT tệp rồi mở thư mục chứa nó.

        Một nút chứ không phải một bài hướng dẫn "vào workspace, chọn ba tệp
        này, nén lại": khách đang bực vì tool vừa hỏng, và mỗi bước phải làm
        tay là một chỗ họ bỏ cuộc — rồi ta lại mất manh mối.
        """
        from core import nhat_ky  # noqa: PLC0415

        try:
            duong = nhat_ky.goi_gui_ho_tro(self._app.base_dir)
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        from .widgets import mo_thu_muc  # noqa: PLC0415

        self._app.show_message(
            "Đã gói xong nhật ký",
            "Tệp {0} nằm trong thư mục workspace. Gửi nguyên tệp đó cho hỗ "
            "trợ — trong đó có giờ tool mở, lúc nào đóng, và lần nào đóng "
            "không bình thường.".format(os.path.basename(duong)))
        try:
            mo_thu_muc(os.path.dirname(duong))
        except Exception:  # noqa: BLE001 — mở không được thì thôi, tệp vẫn còn
            pass

    def doi_du_an(self, _ten: str) -> None:
        """Đổi dự án không ảnh hưởng gì ở đây, nhưng cửa sổ chính vẫn gọi."""
