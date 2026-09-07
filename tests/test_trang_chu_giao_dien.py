"""Nút "Quét trang chủ" phải nằm ở tab NGHIÊN CỨU, không còn ở tab Máy VM.

Chủ dự án, 05/09/2026: *"tính năng quét trang chủ không nên ở tab VPS mà nên ở phân tích nghiên
cứu"*. Việc tìm đối thủ là khâu nghiên cứu; máy ảo chỉ là tay quét. Hai bài này kiểm bằng cách
đọc mã nguồn (không dựng Qt) — canh việc DỌN: dời nút mà quên gỡ tham chiếu cũ là tab Máy VM sập
lúc nạp thiết lập (`self._o_quet_tc` không còn tồn tại).
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _doc(*duong):
    return io.open(os.path.join(GOC, *duong), encoding="utf-8").read()


def test_tab_nghien_cuu_co_du_bo_dieu_khien_trang_chu():
    s = _doc("ui_qt", "trang_quan_ly_doi_thu.py")
    for ten in ("def _quet_may_ao", "def _xu_ly_trang_chu", "def _mo_trang_chu",
                "def _luu_quet_tc", "self._o_quet_tc = QCheckBox", "self._nhan_trang_chu"):
        assert ten in s, "tab Nghiên cứu thiếu " + ten
    # Chủ dự án 05/09: "đồng bộ 1 nút đủ chức năng" — một nút giao CẢ Studio lẫn trang chủ
    than_quet = s.split("def _quet_may_ao")[1].split("def _luu_quet_tc")[0]
    assert "giao_quet_day_du" in than_quet, "nút phải giao đủ hai việc qua trạm (Studio rồi trang chủ)"
    assert "quet_trang_chu_hang_ngay" in s, "ô 'mỗi ngày' phải ghi đúng khoá trong may-ao.json"
    # MỘT NÚT THẬT (05/09, lần hai): bấm → giao VM → trạm gọi hook khi gói về → tự chạy core.mot_nut có AI.
    assert "self._hook_trang_chu = self._tin_trang_chu.emit" in s, (
        "hook phải là signal Qt — trạm gọi ở luồng của nó, không chạm widget")
    assert "tram_mod.dat_hook_trang_chu(self._hook_trang_chu)" in s, "phải đăng ký hook trạm"
    # 08/09: và phải GỠ khi trang chết. Bỏ quên là để lại một mục trong danh sách
    # TOÀN CỤC của trạm trỏ vào widget C++ đã xoá; luồng nền gọi trúng thì
    # `access violation` giết cả tiến trình (xem tram.go_hook_trang_chu).
    assert "self.destroyed.connect(" in s and "go_hook_trang_chu" in s, (
        "đăng ký một chiều là rò rỉ theo thiết kế — phải nối destroyed → gỡ hook")
    assert "_tin_trang_chu = pyqtSignal(str)" in s and "self._tin_trang_chu.connect(self._tu_chay_mot_nut)" in s
    than = s.split("def _chay_mot_nut")[1].split("def _xu_ly_trang_chu")[0]
    assert "mot_nut.chay(goc, kenh, client=client)" in than, "chuỗi phải nhận ví để AI chạy ở ba chỗ"
    assert "os.startfile(bc.tep_bao_cao)" in than, "xong phải mở báo cáo cho khách"
    assert "_kiem_may_ao_im" in s and "45 * 60 * 1000" in s, "máy ảo im 45 phút phải nói thật"
    # 06/09 (ảnh chụp của chủ dự án): nhãn dài bị cắt, thẻ MỘT NÚT phải lên đầu, trạm phải tìm đúng tab
    assert 'nut_chinh("MỘT NÚT", self._quet_may_ao, rong=130)' in s, "nhãn phải ngắn để không bị cắt"
    assert 'nut_phu("Xếp hạng lại", self._xu_ly_trang_chu, rong=130)' in s
    assert "def _the_mot_nut" in s and "def _mo_bao_cao" in s
    assert s.index("doc.addWidget(self._the_mot_nut())") < s.index("doc.addWidget(self._the_ket_qua(), 1)") \
        < s.index("doc.addWidget(self._the_danh_ba(), 1)") < s.index("doc.addWidget(self._the_hop_thu())"), \
        "thứ tự thẻ: Một nút → Kết quả → Đối thủ đang theo dõi → Thủ công"
    # 06/09 "quá khó dùng": bảng kết quả để CHỌN, danh bạ mặc định chỉ kênh theo dõi + 6 cột, thủ công thu gọn
    assert "def _the_ket_qua" in s and "mot_nut.doc_danh_sach(" in s and 'nut_chinh("Chép link để làm video"' in s
    assert 'QCheckBox("chỉ kênh đang quét")' not in s, "07/09: thị trường thì quét hết, không còn lọc 'chỉ kênh đang quét'"
    assert 'QCheckBox("cả kênh đã loại")' in s and "_COT_AN_MAC_DINH" in s
    assert 'nhan("Thị trường kênh tâm lý", "h2")' in s and "im lặng ≥" in s, "danh bạ là bản đồ thị trường: mới / đang chết"
    assert "return ca_loai" in s, "kênh đã loại (không phải tâm lý) phải ẩn sẵn"
    assert "_hang_hien" in s.split("def _o_doi")[1].split("def ")[0], "_o_doi phải ghi theo _hang_hien, không dựng lại sổ từ bảng đang lọc"
    assert "self._khung_thu_cong.setVisible(False)" in s, "thẻ thủ công thu gọn sẵn"
    assert 'nut_nguy_hiem("Xoá kênh đã chọn"' in s.split("def _the_hop_thu")[1].split("def _bat_tat_thu_cong")[0], "nút xoá nằm trong thẻ thủ công"
    assert "return tim_tram(self._app)" in s, "tìm trạm qua tram_chung, không đoán trang"
    assert 'self._app.trang("phan-tich")' not in s, "trạm không nằm ở trang Phân tích"
    than2 = s.split("def _xu_ly_trang_chu")[1].split("def ")[0]
    assert "_chay_mot_nut(self._kenh" in than2 and "QMessageBox.question" not in than2, "nút phụ dùng chung chuỗi, không hỏi lằng nhằng"


def test_tab_may_vm_khong_con_tham_chieu_nut_da_doi():
    s = _doc("ui_qt", "trang_phan_tich.py")
    assert "_o_quet_tc" not in s, "tab Máy VM còn đụng ô đã dời — sập lúc nạp thiết lập"
    assert "def _quet_trang_chu" not in s
    assert 'nut_phu("Quét trang chủ lấy đối thủ"' not in s
    # 05/09: nút Quét Studio cũng dời sang Nghiên cứu và gộp — tab Máy VM chỉ còn thiết lập
    assert 'nut_phu("Quét Studio ngay"' not in s and "def _quet_studio" not in s
    assert "def _giao" in s and '"dang-video"' in s, "gỡ nhầm đường giao việc đăng video"
    # thiết lập khác của máy ảo vẫn còn nguyên
    for ten in ("gio_quet=", "cho_quet_giay=", "giu_chrome_mo=", "dong_chrome_sau_quet="):
        assert ten in s, "gỡ nhầm thiết lập " + ten
