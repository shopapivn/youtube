"""Nhà máy không nhận việc thì KHÔNG được để khách nhìn chữ "Chờ" hàng giờ.

Khách báo 08/09/2026 (ảnh chụp tab Ảnh & Video → Hàng loạt): bấm "Chạy cả
loạt", dòng ghi "⏳ Chờ" rồi đứng như thế mãi. Hỏi máy chủ đúng lúc ấy::

    concurrent_jobs: tts 3 · image 0 · video 64
    image.reason: "Có 1 máy xử lý online … nhưng kho tài khoản không còn cái
                   nào dùng được (0/106 …)". queued: 11

Hai lỗi ở tool cộng lại thành một sự im lặng:

* `NhipDo.dat_tran(0)` đặt quãng dừng 30 giây, mà trần được hỏi lại mỗi 20
  giây — mỗi lần vẫn 0 là đặt LẠI từ đầu, quãng dừng không bao giờ hết, job
  thăm dò không bao giờ đi, cổng ở 0 vĩnh viễn.
* Câu giải thích của máy chủ bị nuốt; bảng chỉ có "⏳ Chờ".
"""

from __future__ import annotations

import queue

import core  # noqa: F401 — nhập trước để tìm thấy SDK trong _sdk/
from core.jobs import KIND_IMAGE, STATUS_WAITING, JobManager, JobSpec
from shopapi._client import LoiMoi  # noqa: E402
from shopapi._nhip_do import CHO_KHI_DUNG, NhipDo  # noqa: E402


class _DongHo:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class TestQuangDungPhaiHet:
    def test_hoi_lai_van_0_thi_khong_dat_lai_quang_dung(self):
        dh = _DongHo()
        nhip = NhipDo(_dong_ho=dh)
        nhip.dat_tran(0)
        assert nhip.cho_phep() == 0
        dh.t += 20.0                      # hỏi lại trần sau 20 giây, vẫn 0
        nhip.dat_tran(0)
        dh.t += 11.0                      # tổng 31 giây > CHO_KHI_DUNG
        assert nhip.cho_phep() == 1, "hết quãng dừng phải thăm dò MỘT job"

    def test_quang_dung_dai_dung_bang_CHO_KHI_DUNG(self):
        dh = _DongHo()
        nhip = NhipDo(_dong_ho=dh)
        nhip.dat_tran(0)
        assert abs(nhip.cho_bao_lau() - CHO_KHI_DUNG) < 1e-6

    def test_het_dung_roi_ma_may_chu_van_0_thi_dung_lai_moi(self):
        """Thăm dò xong (bị từ chối) rồi máy chủ vẫn 0 → dừng một quãng mới."""
        dh = _DongHo()
        nhip = NhipDo(_dong_ho=dh)
        nhip.dat_tran(0)
        dh.t += CHO_KHI_DUNG + 1
        assert nhip.cho_phep() == 1
        nhip.nha_may_dung()               # job thăm dò ăn 503
        assert nhip.cho_phep() == 0


class _ClientGia:
    def __init__(self, tran, ly_do=""):
        self.tran = tran
        self.ly_do = ly_do

    def cho_nha_may_dang_moi(self, loai):
        return LoiMoi(tran=self.tran, cho_trong=0, dang_chay=0, hang_doi=11,
                      ly_do=self.ly_do)


def _hang_doi_voi_mot_viec(client):
    jm = JobManager(lambda: client, queue.Queue(), tu_do_nhip=True)
    jm._client = client
    spec = JobSpec(kind=KIND_IMAGE, content="a cat", out_dir=".")
    from core.jobs import JobRecord

    rec = JobRecord(spec=spec)
    jm._records.append(rec)
    jm._hang_doi[KIND_IMAGE].append((rec, "chay"))
    jm._lan_hoi_tran[KIND_IMAGE] = -1e9    # ép hỏi trần ngay
    jm._lan_bao_cho[KIND_IMAGE] = -1e9
    return jm, rec


class TestNoiLyDoLenViecDangCho:
    def test_tran_0_thi_viec_cho_mang_ly_do_cua_may_chu(self):
        client = _ClientGia(0, "Có 1 máy xử lý online cho loại \"image\" nhưng kho "
                               "tài khoản không còn cái nào dùng được (0/106 tài "
                               "khoản sẵn sàng). Máy có mà tài khoản không có thì "
                               "vẫn không chạy được job nào.")
        jm, rec = _hang_doi_voi_mot_viec(client)
        jm._dong_bo_nhip(KIND_IMAGE)
        assert jm._cong[KIND_IMAGE].suc_chua == 0
        assert rec.status == STATUS_WAITING
        assert "không nhận việc" in rec.message
        assert "0/106" in rec.message, "phải nói đúng câu máy chủ nói"
        assert "chưa trừ tiền" in rec.message
        assert rec.message.startswith("Nhà máy ảnh"), "gọi tên nhà máy bằng tiếng Việt"

    def test_tran_mo_lai_thi_khong_con_ly_do(self):
        client = _ClientGia(0, "kho tài khoản 0/106")
        jm, rec = _hang_doi_voi_mot_viec(client)
        jm._dong_bo_nhip(KIND_IMAGE)
        assert jm._ly_do_dung[KIND_IMAGE]
        client.tran = 8
        jm._lan_hoi_tran[KIND_IMAGE] = -1e9
        jm._dong_bo_nhip(KIND_IMAGE)
        assert jm._ly_do_dung[KIND_IMAGE] == ""

    def test_o_trang_thai_tab_hang_loat_hien_ly_do(self):
        from ui_qt.trang_anh_video import TabHangLoat

        class _Ghi:
            status = STATUS_WAITING
            progress = 0
            message = "Nhà máy ảnh đang không nhận việc: kho tài khoản 0/106. Tự thử lại sau 30 giây — chưa trừ tiền."

        chu = TabHangLoat._nhan_ngan(_Ghi())
        assert chu.startswith("⏳ Chờ — Nhà máy ảnh")
