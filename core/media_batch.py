"""Bắn một mẻ job media mà không tự bóp cổ mình.

Hai việc, đều là chuyện tiền:

**Gộp job.** Nhiều cảnh dùng chung một mô tả ảnh thì gộp thành một job `n=k`.
Không phải để tiết kiệm tiền ảnh — giá vẫn tính theo từng ảnh — mà để tiết kiệm
**chỗ trong trần song song và lượt xếp hàng**: k ảnh gộp chiếm 1 chỗ thay vì k.

**Cổng hàng chờ.** Máy chủ trả `queue_position` và `estimated_seconds` ngay
trong phản hồi 202, tức là nó nói thẳng "đang có bao nhiêu người trước bạn". Ai
không đọc thì cứ bắn tiếp cho tới khi job hết hạn **ngay trong hàng chờ** — job
chết mà nhà máy vẫn rảnh, vì hàng chờ mới là chỗ tắc chứ không phải máy.

Sự cố có thật ngày 07/08/2026: một tool bắn 66 job vào nhà máy tiêu hoá được 16
job cùng lúc. 27 job chết trong hàng chờ (14 "vượt quá thời gian chờ", 13 "không
còn đủ thời gian thử lại") trong khi kho tài khoản còn nguyên. Tỉ lệ 66/16 ≈ 4,0
chính là con số :data:`HE_SO_DANG_BAY` sinh ra để chặn.

Module thuần tuý: không mạng, không ngủ, không đọc ghi file. Nơi gọi quyết định
lúc nào gửi, lúc nào ngủ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

__all__ = [
    "MAX_IMAGES_PER_JOB",
    "HE_SO_DANG_BAY",
    "HE_SO_NGUONG_VI_TRI",
    "BIEN_AN_TOAN_HAN",
    "ImageBatch",
    "QueueGate",
    "plan_image_batches",
]

#: Trần ảnh trong một job. Máy chủ nhận tối đa 8 (`n`: 1..8).
#:
#: Xin 9 là **400 cho cả job** — mất luôn 8 ảnh hợp lệ đi kèm. Nên phải cắt ở
#: đây chứ không để máy chủ từ chối.
MAX_IMAGES_PER_JOB = 8

#: Cho phép bao nhiêu job đang bay so với trần nhà máy.
#:
#: 1,0 thì nhà máy ngồi không giữa hai lượt gửi. 4,0 chính là tỉ lệ của sự cố
#: 07/08. 1,5 là chỗ đứng giữa: luôn có sẵn việc cho nhà máy nhận, mà hàng chờ
#: không dài tới mức job hết hạn trong đó.
HE_SO_DANG_BAY = 1.5

#: Đứng sau ngần này người thì **ngừng gửi hẳn**, không gửi chậm lại.
#:
#: Vị trí hàng chờ vượt trần nghĩa là job mới sẽ phải đợi trọn một lượt nhà máy
#: mới tới lượt. Gửi thêm lúc đó chỉ làm hàng dài ra.
HE_SO_NGUONG_VI_TRI = 1.0

#: Nhân vào `estimated_seconds` trước khi so với hạn chờ.
#:
#: Ước tính của máy chủ là ước tính. Job dự tính chờ 900 giây với hạn chờ 900
#: giây thì gần như chắc chắn chết — phải coi là quá hạn từ trước.
BIEN_AN_TOAN_HAN = 1.2


@dataclass(frozen=True)
class ImageBatch:
    """Một job ảnh, có thể phục vụ nhiều cảnh cùng lúc."""

    prompt: str
    aspect_ratio: str
    reference_images: Tuple[str, ...]
    scene_ids: Tuple[int, ...]

    @property
    def n(self) -> int:
        return len(self.scene_ids)


def plan_image_batches(scenes: Sequence[Mapping[str, Any]], *, aspect_ratio: str,
                       max_per_job: int = MAX_IMAGES_PER_JOB) -> List[ImageBatch]:
    """Gộp các cảnh **trùng cả mô tả, tỉ lệ lẫn bộ ảnh tham chiếu** vào chung job.

    Trùng cả ba mới gộp: khác một thứ là ảnh ra khác, gộp vào là giao nhầm ảnh
    cho cảnh — hỏng lặng lẽ, không lỗi nào báo.

    >>> scenes = [{"scene_id": 1, "img_prompt": "biển"}, {"scene_id": 2, "img_prompt": "biển"},
    ...           {"scene_id": 3, "img_prompt": "núi"}]
    >>> [(b.prompt, b.scene_ids) for b in plan_image_batches(scenes, aspect_ratio="16:9")]
    [('biển', (1, 2)), ('núi', (3,))]

    Thứ tự cảnh được giữ nguyên theo lần xuất hiện đầu tiên, để nơi gọi ghép kết
    quả theo vị trí mà không lệch.

    Quá trần thì cắt thành nhiều job chứ không xin `n` lớn hơn máy chủ nhận:

    >>> batches = plan_image_batches(
    ...     [{"scene_id": i, "img_prompt": "x"} for i in range(1, 12)], aspect_ratio="1:1")
    >>> [b.n for b in batches]
    [8, 3]
    """
    if max_per_job < 1:
        raise ValueError("max_per_job phai it nhat la 1")
    thu_tu: List[Tuple[str, str, Tuple[str, ...]]] = []
    nhom: Dict[Tuple[str, str, Tuple[str, ...]], List[int]] = {}
    for index, scene in enumerate(scenes, 1):
        prompt = str(scene.get("img_prompt") or "").strip()
        if not prompt:
            raise ValueError("Scene {0} thieu img_prompt".format(scene.get("scene_id") or index))
        refs = tuple(str(item) for item in (scene.get("reference_images") or []))
        khoa = (prompt, str(aspect_ratio), refs)
        if khoa not in nhom:
            nhom[khoa] = []
            thu_tu.append(khoa)
        nhom[khoa].append(int(scene.get("scene_id") or index))
    batches: List[ImageBatch] = []
    for khoa in thu_tu:
        ids = nhom[khoa]
        for offset in range(0, len(ids), max_per_job):
            batches.append(ImageBatch(khoa[0], khoa[1], khoa[2], tuple(ids[offset:offset + max_per_job])))
    return batches


@dataclass
class QueueGate:
    """Quyết định có được gửi thêm job nữa không, dựa trên tín hiệu 202.

    Thuần tuý và không ngủ: nó chỉ trả lời "được" hay "chưa, chờ chừng này giây".

    >>> gate = QueueGate(limit=4)
    >>> gate.can_send()
    True
    >>> for _ in range(6): gate.sent()
    >>> gate.can_send()          # 6 job đang bay, trần 4 × 1,5 = 6
    False
    """

    #: Trần song song đọc từ `GET /v1/me`. `0` nghĩa là **nhà máy đang dừng**,
    #: KHÔNG phải "chạy một job" — đây là chỗ rất dễ hiểu nhầm.
    limit: int = 1
    #: Hạn chờ tối đa cho một job, giây. Dùng để đoán job có chết trong hàng không.
    timeout: float = 900.0
    _dang_bay: int = field(default=0, init=False)
    _dung_lai: bool = field(default=False, init=False)

    def set_limit(self, limit: Optional[int]) -> None:
        """Ghi nhận trần mới. Hỏi lại mỗi lô chứ không mỗi job."""
        if limit is None:
            return
        self.limit = max(0, int(limit))

    @property
    def factory_stopped(self) -> bool:
        """Máy chủ báo trần 0 — nhà máy loại này đang dừng, phải chờ rồi hỏi lại."""
        return self.limit <= 0

    def can_send(self) -> bool:
        """Được bắn thêm một job ngay bây giờ không?"""
        if self.factory_stopped or self._dung_lai:
            return False
        return self._dang_bay < self.max_in_flight

    @property
    def max_in_flight(self) -> int:
        return max(1, int(self.limit * HE_SO_DANG_BAY))

    def sent(self) -> None:
        self._dang_bay += 1

    def done(self) -> None:
        """Một job đã xong (hoặc hỏng). **Phải gọi trong `finally`.**

        Quên gọi là cổng khoá cứng cả mẻ mà không dòng log nào nói vì sao.
        """
        self._dang_bay = max(0, self._dang_bay - 1)

    def observe(self, job: Any) -> Optional[str]:
        """Đọc phản hồi 202. Trả về lời cảnh báo tiếng Việt, hoặc `None` nếu ổn.

        Hai tín hiệu, ý nghĩa khác hẳn nhau:

        * `queue_position` vượt trần → hàng đã dài hơn sức nhà máy, **ngừng gửi**.
        * `estimated_seconds` × biên an toàn vượt hạn chờ → job này sẽ chết trong
          hàng, nói cho khách biết ngay thay vì để họ chờ 15 phút rồi nhận lỗi.

        >>> gate = QueueGate(limit=4, timeout=600)
        >>> gate.observe({"queue_position": 2, "estimated_seconds": 30}) is None
        True
        >>> gate.observe({"queue_position": 9})
        'Hàng chờ đang dài (đứng thứ 9, nhà máy nhận 4 việc một lúc) — tạm ngừng gửi thêm.'
        >>> gate.can_send()
        False
        """
        if not isinstance(job, Mapping):
            return None
        canh_bao = None
        vi_tri = job.get("queue_position")
        if isinstance(vi_tri, int) and self.limit > 0:
            if vi_tri > self.limit * HE_SO_NGUONG_VI_TRI:
                self._dung_lai = True
                canh_bao = ("Hàng chờ đang dài (đứng thứ {0}, nhà máy nhận {1} việc một lúc) "
                            "— tạm ngừng gửi thêm.").format(vi_tri, self.limit)
        uoc = job.get("estimated_seconds")
        if isinstance(uoc, (int, float)) and uoc * BIEN_AN_TOAN_HAN > self.timeout:
            return ("Việc này dự tính chờ {0:.0f} giây, quá hạn chờ {1:.0f} giây — "
                    "nhiều khả năng hết hạn ngay trong hàng.").format(uoc, self.timeout)
        return canh_bao

    def resume(self) -> None:
        """Mở lại cổng sau khi đã chờ. Nơi gọi quyết định chờ bao lâu."""
        self._dung_lai = False
