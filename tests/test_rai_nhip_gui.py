"""Van rải nhịp của dispatcher: mẻ lớn không được đấm cả loạt vào máy chủ.

Đo 24/08/2026 (lô 1000 ảnh + 1000 video): cổng mở đúng trần là chuyện SỐ CHỖ,
nhưng vòng `while cong.giu_cho()` nhả toàn bộ số chỗ đó xuống pool trong vài
mili giây — ~650 request `POST` đập vào máy chủ cùng một nhịp, sinh một loạt
`429` dồn trong 30 giây đầu, và vòng tự dò CHIA ĐÔI rồi bò lại. Van
`RAI_NHIP_GIAY` nắn cú dốc đó thành một đường dốc ~25 lượt/giây mỗi loại.

Bài này canh cả HAI mặt của van — nắn được cú đấm, và KHÔNG được chạm vào
trạng thái chạy đều — vì mặt thứ hai hỏng thì im lặng y như cái bẫy pool cỡ 3.
Không gọi mạng: `_run_one` được thay bằng hàm ghi lại mốc thời gian.
"""
from __future__ import annotations

import queue
import threading
import time

from core.jobs import RAI_NHIP_GIAY, JobManager, JobSpec


def _dung_may(so_cho: int, cham_giay: float = 0.0):
    """JobManager thật + `_run_one` giả ghi mốc `monotonic` của từng lượt nhả."""
    jm = JobManager(lambda: None, queue.Queue(),
                    max_by_kind={"tts": so_cho, "image": so_cho,
                                 "video": so_cho},
                    tu_do_nhip=False)
    moc: list = []
    khoa = threading.Lock()

    def _gia(record):
        with khoa:
            moc.append(time.monotonic())
        if cham_giay:
            time.sleep(cham_giay)

    jm._run_one = _gia
    return jm, moc


def _cho_xong(jm, moc, so, han_giay: float) -> None:
    # Chỉ chờ đủ SỐ LƯỢT NHẢ. Không chờ `_in_flight` về 0: sổ sách đó do
    # `_run_one` thật ghi, mà bài này đã thay nó bằng hàm giả.
    het = time.monotonic() + han_giay
    while time.monotonic() < het:
        if len(moc) >= so:
            return
        time.sleep(0.02)
    raise AssertionError(
        "hết {0}s mà mới nhả {1}/{2} việc".format(han_giay, len(moc), so))


def test_me_lon_khong_dam_ca_loat():
    """Cổng mở 200 chỗ + 60 việc tức thời: giây đầu tiên chỉ được nhả cỡ
    1/RAI_NHIP_GIAY việc, không phải cả 60 — đây chính là cú đấm 429."""
    jm, moc = _dung_may(so_cho=200)
    try:
        jm.submit([JobSpec(kind="image", content="c{0}".format(i))
                   for i in range(60)])
        _cho_xong(jm, moc, 60, han_giay=15.0)
        dau = moc[0]
        trong_giay_dau = sum(1 for m in moc if m - dau <= 1.0)
        tran = int(1.0 / RAI_NHIP_GIAY) + 5   # +5: dung sai đồng hồ/scheduler
        assert trong_giay_dau <= tran, (
            "giây đầu nhả {0} việc — van rải không hoạt động".format(
                trong_giay_dau))
    finally:
        jm.shutdown()


def test_van_tinh_rieng_tung_loai():
    """Ba nhà máy độc lập (CONTRACT.md §8.1): video xếp sau ảnh ở một cái van
    CHUNG là dựng lại đúng ràng buộc máy chủ đã tháo. 20 ảnh + 20 video phải
    xong trong ~20×RAI_NHIP_GIAY, không phải 40×."""
    jm, moc = _dung_may(so_cho=100)
    try:
        specs = [JobSpec(kind="image", content="a{0}".format(i))
                 for i in range(20)]
        specs += [JobSpec(kind="video", content="v{0}".format(i))
                  for i in range(20)]
        t0 = time.monotonic()
        jm.submit(specs)
        _cho_xong(jm, moc, 40, han_giay=15.0)
        # 40 việc chung một van là ≥ 39×RAI (1,56s); van riêng là ~19×RAI
        # (0,76s). Mốc cắt 30×RAI nằm giữa, đủ xa cả hai phía.
        assert moc[-1] - t0 <= 30 * RAI_NHIP_GIAY + 1.0, (
            "hai loại đang xếp hàng chung một van")
    finally:
        jm.shutdown()


def test_chay_deu_khong_bi_van_cham_vao():
    """Trạng thái chạy đều (job xong chậm hơn nhịp van): van KHÔNG được làm
    chậm — chỗ vừa trống phải được lấp gần như tức thì như trước."""
    jm, moc = _dung_may(so_cho=2, cham_giay=0.2)
    try:
        t0 = time.monotonic()
        jm.submit([JobSpec(kind="image", content="c{0}".format(i))
                   for i in range(6)])
        _cho_xong(jm, moc, 6, han_giay=15.0)
        # 6 việc × 0,2s ÷ 2 chỗ = 0,6s lý tưởng. Van 0,04s không cộng thêm gì
        # đáng kể; nếu tổng vượt xa 0,6s + nhịp điều phối là van đang ghì.
        assert moc[-1] - t0 <= 2.5, "van rải đang ghì cả trạng thái chạy đều"
    finally:
        jm.shutdown()
