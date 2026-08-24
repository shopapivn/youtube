"""MAX phải khai thác triệt để nhà máy, và lô 1000 việc không được báo nhầm "120".

Khách 23/08/2026: *"MAX rồi mà 1000 ảnh/video chạy mãi không xong"* và *"tab
Hàng loạt 1000 prompt nó lại chỉ hiển thị 120"*. Bài này canh HAI gốc rễ, không
gọi mạng:

  1. **Trần tool phải bám trần máy chủ.** `HARD_CAPS` cũ `{16,384,64}` bóp tool
     xuống dưới nhà máy (server `{16,6144,832}`, nhà máy thật image ~3072, video
     ~320). Pool luồng = `sum(HARD_CAPS)` nên trần thấp = pool nhỏ = nút thắt
     câm. MAX (`toi_da`) khởi đầu phải đủ cao để "đẩy một phát", không bò lên.
  2. **Số đếm tiến độ tách khỏi số thẻ vẽ.** Lưới chỉ giữ `TRAN_THE` thẻ (vẽ
     nghìn thẻ là treo), nhưng thanh tiến độ phải đếm ĐỦ 1000, không phải 120.
"""
from __future__ import annotations

import queue

from core.cai_dat import luong_khoi_dau
from core.config import HARD_CAPS
from core.jobs import JobManager


# ── 1. Trần tool bám trần máy chủ ────────────────────────────────────────────

def test_hard_caps_bam_tran_may_chu():
    """Trần cứng phải khớp `HARD_MAX_CONCURRENT_PER_USER` của máy chủ, không được
    thấp hơn — thấp hơn là tool tự bóp mình dưới nhà máy."""
    assert HARD_CAPS["tts"] == 16
    assert HARD_CAPS["image"] >= 6144, "image phải theo kịp nhà máy 96×32"
    assert HARD_CAPS["video"] >= 832, "video Veo3 phải theo kịp nhà máy 10×32"


def test_pool_du_rong_cho_ca_nghin_viec():
    """Pool luồng = tổng trần cứng. Phải đủ rộng để chạy đồng thời cả nghìn ảnh
    + vài trăm video — pool 464 cũ là nút thắt câm khiến MAX vô nghĩa."""
    assert sum(HARD_CAPS.values()) >= 1000 + 320, (
        "pool phải ôm được ~1000 ảnh song song + trần video của một khách")


def test_max_khoi_dau_cao_khong_bo_len():
    """Mốc "toi_da" phải bắt đầu NGAY ở trần cứng (đẩy một phát), không phải ở
    con số nhỏ rồi để vòng tự dò bò lên mất chục phút."""
    kd = luong_khoi_dau("toi_da")
    assert kd == HARD_CAPS
    # Video là loại từng bị bóp nặng nhất (khởi đầu 64 cũ): giờ phải bung cao.
    assert kd["video"] >= 320, "MAX phải bung video ngay, không bò từ 64"


def test_cong_max_mo_dung_theo_max_khi_khong_hoi_tran():
    """Không có client để hỏi `/v1/me` (test không mạng): cổng vẫn mở đúng mốc
    MAX ngay từ đầu, không bị kẹp về trần cũ 384/64."""
    jm = JobManager(lambda: None, queue.Queue(),
                    max_by_kind=luong_khoi_dau("toi_da"), tu_do_nhip=True)
    assert jm._cong["image"].suc_chua == HARD_CAPS["image"]
    assert jm._cong["video"].suc_chua == HARD_CAPS["video"]


def test_nhip_max_leo_toi_tran_may_chu_khong_bi_kep_boi_hard_cap():
    """Vòng tự dò nhận trần THẬT máy chủ (vd video 288 cho khách chạy một mình)
    và mở cổng đúng bằng đó — HARD_CAPS chỉ là trần trên, không phải mức chạy."""
    jm = JobManager(lambda: None, queue.Queue(),
                    max_by_kind=luong_khoi_dau("toi_da"), tu_do_nhip=True)

    class _ClientGia:
        # Máy chủ báo trần thật của một khách chạy một mình: ~90% nhà máy.
        def tran_song_song(self, loai):
            return {"tts": 16, "image": 2764, "video": 288}[loai]

    jm._client = _ClientGia()
    jm._dong_bo_nhip("video")
    # Cổng bám đúng trần máy chủ (288), KHÔNG bị HARD_CAPS (832) kéo cao vô căn
    # cứ, cũng KHÔNG bị trần cũ (64) bóp thấp.
    assert jm._cong["video"].suc_chua == 288
    jm._dong_bo_nhip("image")
    assert jm._cong["image"].suc_chua == 2764


# ── 2. Số đếm tiến độ tách khỏi số thẻ vẽ ────────────────────────────────────

import os  # noqa: E402

import pytest  # noqa: E402

pytest.importorskip("PyQt5.QtWidgets", reason="máy chạy test không có giao diện")


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


class _Spec:
    def __init__(self, uid, kind, content="canh", index=0):
        self.idempotency_key = uid
        self.kind = kind
        self.content = content
        self.index = index
        self.params = {}


class _Ban:
    def __init__(self, uid, kind, status, index=0):
        self.spec = _Spec(uid, kind, index=index)
        self.uid = uid
        self.status = status
        self.progress = 100
        self.files = ()


def test_tong_dem_du_1000_du_luoi_chi_ve_120(qt_app):
    """Thêm 1000 việc: lưới cắt còn `TRAN_THE` thẻ, NHƯNG tổng đếm phải là 1000
    — đây chính là lỗi "1000 prompt chỉ hiển thị 120"."""
    from ui_qt.thu_vien_ket_qua import TRAN_THE, ThuVienKetQua

    tv = ThuVienKetQua()
    for i in range(1000):
        tv.them("u{0}".format(i), "canh {0}".format(i), False, so_canh=i + 1)

    assert tv.so_the == TRAN_THE, "số THẺ VẼ vẫn bị cắt để khỏi treo"
    xong, tong = tv.tom_tat_tien_do()
    assert tong == 1000, "tổng phải đếm đủ 1000, không phải 120"
    assert xong == 0


def test_tien_do_dem_du_ca_khi_the_bi_cat(qt_app):
    """Cập nhật 'xong' cho những việc mà thẻ ĐÃ bị cắt khỏi màn hình: số 'xong'
    vẫn phải tăng đủ, và KHÔNG dựng lại thẻ (churn làm treo)."""
    from ui_qt.thu_vien_ket_qua import TRAN_THE, STATUS_DONE, ThuVienKetQua

    tv = ThuVienKetQua()
    for i in range(1000):
        tv.them("u{0}".format(i), "canh", False, so_canh=i + 1)

    # Đánh 'xong' cho 300 việc ĐẦU (chắc chắn đã bị cắt khỏi lưới 120 cuối).
    for i in range(300):
        tv.cap_nhat(_Ban("u{0}".format(i), "image", STATUS_DONE, index=i + 1))

    assert tv.so_the == TRAN_THE, "không được dựng lại thẻ đã cắt"
    xong, tong = tv.tom_tat_tien_do()
    assert tong == 1000
    assert xong == 300, "phải đếm đủ 300 việc xong dù thẻ đã bị cắt"


def test_tach_anh_video_dem_du_khi_the_bi_cat(qt_app):
    """Số 'Ảnh x/n · Video x/n' cũng phải đếm từ sổ, không từ thẻ còn trên lưới."""
    from ui_qt.thu_vien_ket_qua import STATUS_DONE, ThuVienKetQua

    tv = ThuVienKetQua()
    # 600 ảnh + 600 video, ảnh mang số cảnh nhỏ nên bị cắt trước.
    for i in range(600):
        tv.them("a{0}".format(i), "anh", False, so_canh=i + 1)
    for i in range(600):
        tv.them("v{0}".format(i), "vid", True, so_canh=1000 + i)
    for i in range(600):
        tv.cap_nhat(_Ban("a{0}".format(i), "image", STATUS_DONE))

    (ax, av), (vx, vv) = tv.tom_tat_theo_loai()
    assert av == 600 and vv == 600, "tổng mỗi loại đếm đủ dù thẻ đã cắt"
    assert ax == 600 and vx == 0
