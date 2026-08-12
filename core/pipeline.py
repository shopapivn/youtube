"""Dây chuyền chạy dự án: xếp hàng tuần tự, cảnh nào hỏng thì bỏ qua cảnh đó.

## Vì sao chạy MỘT việc một lúc

Máy chủ ShopAPI là mô hình nhà máy **một hàng chờ cho mỗi khách** — cố ý như vậy.
Bắn 50 job cùng lúc không làm xong nhanh hơn: chúng xếp hàng ở phía máy chủ, còn
tool thì ăn `429` và khách ngồi nhìn một bảng đầy chữ đỏ. Nên ở đây đúng **một**
luồng nền, chạy hết việc này mới sang việc khác, và luôn hiện *đang ở vị trí nào
trong hàng* để khách biết còn phải chờ bao lâu.

(Khác với :class:`~core.jobs.JobManager` của mấy tab lẻ — ở đó mỗi job độc lập nên
chạy song song được. Dây chuyền dự án thì có phụ thuộc: clip lấy chính tấm ảnh của
cảnh đó làm khung hình mở đầu.)

## Thứ tự và phụ thuộc

```
Cảnh 1:  giọng đọc ──►  ảnh ──► video          (video cần URL ảnh)
Cảnh 2:  giọng đọc ──►  ảnh ──► video
   ...
```

Giọng đọc **không** liên quan tới hình, nên giọng hỏng vẫn làm tiếp ảnh và video
của cảnh đó — khách vẫn có hình để dùng. Ngược lại ảnh hỏng thì bỏ video của đúng
cảnh đó (không có khung hình mở đầu thì clip lạc phong cách so với cả tập).

## Một cảnh hỏng không kéo cả dự án chết

Cảnh hỏng được ghi lại rồi **đi tiếp cảnh sau**. Cuối buổi tool nói rõ cảnh nào
cần làm lại, và khách chạy lại **riêng** cảnh đó. Job hỏng thì máy chủ tự hoàn
100% tiền, nên tool không tính toán lại đồng nào ở phía mình — nó chỉ đọc `cost`
và `refunded` máy chủ trả về.

Ngoại lệ duy nhất được phép dừng cả dự án: **ví hết tiền**. Lúc đó mọi việc còn
lại chuyển sang “chưa chạy” mà không gửi request nào — chưa gửi thì chưa mất tiền.
"""

from __future__ import annotations

import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from shopapi import ShopAPI, poll_delays

from .api import extract_outputs
from .batch import guess_extension
from .config import redact
from .download import DownloadError, download_to
from .errors import describe, retry_after_seconds
from .project import (
    ENGINE_AUTO,
    MAX_STAGE_ATTEMPTS,
    PIPELINE,
    ST_DONE,
    ST_FAILED,
    ST_INTERRUPTED,
    ST_OFF,
    ST_RUNNING,
    ST_SKIPPED,
    ST_WAITING,
    STAGE_IMAGE,
    STAGE_LABEL,
    STAGE_VIDEO,
    STAGE_VOICE,
    Project,
    Scene,
    StageState,
)

__all__ = [
    "STAGE_NEEDS",
    "IMAGE_URL_MAX_AGE",
    "RunProgress",
    "ProjectSummary",
    "ProjectRunner",
    "plan_jobs",
]

#: Bước nào cần kết quả của bước nào. Chỉ có đúng một phụ thuộc trong cả dây chuyền.
STAGE_NEEDS: Dict[str, str] = {STAGE_VIDEO: STAGE_IMAGE}

#: Link kết quả sống 7 ngày (CONTRACT.md §2.2). Quá 6 ngày thì tool **không** đưa
#: URL ảnh cũ sang bước video nữa: link chết làm job video trượt ngay từ lúc tạo,
#: mà lỗi đó đọc lên chẳng ai hiểu tại sao. Thà làm clip không có khung hình mở
#: đầu còn hơn báo một lỗi vô nghĩa.
IMAGE_URL_MAX_AGE = 6 * 24 * 3600

#: Chờ tối đa ngần này giây cho một job, **theo từng bước**.
#:
#: Vì sao không dùng một con số chung như :mod:`core.jobs`: đo trên máy chủ thật
#: thì một clip Veo3 chạy **hơn 25 phút** lúc đông, trong khi ảnh xong sau ~9 phút.
#: Lấy chung 15 phút thì tool bỏ theo dõi đúng lúc clip đã chạy tới 74% — job vẫn
#: xong trên máy chủ và khách vẫn bị trừ tiền, chỉ là phải bấm “Chạy tiếp” mới lấy
#: được về. Bỏ tiền ra rồi mà phải thao tác thêm là hỏng trải nghiệm, nên video
#: được cho hạn rộng hẳn.
#:
#: Vẫn phải có trần: một job kẹt thật sự mà chờ mãi thì cả hàng đợi đứng theo.
#: Hết hạn thì bước đó thành **gián đoạn** (không phải lỗi) — tiền đã trả vẫn còn
#: nguyên giá trị, lần chạy sau tool đi hỏi lại `job_id` cũ chứ không mua lần nữa.
JOB_WAIT_TIMEOUT_BY_STAGE: Dict[str, int] = {
    STAGE_VOICE: 15 * 60,
    STAGE_IMAGE: 20 * 60,
    STAGE_VIDEO: 45 * 60,
}

#: Dùng khi không tra được theo bước.
JOB_WAIT_TIMEOUT = 15 * 60

#: Thử lại tối đa mấy lần khi *tạo* job gặp lỗi tạm thời (429, 503, mất mạng).
_CREATE_ATTEMPTS = 4

#: Trạng thái kết thúc phía máy chủ.
_TERMINAL = ("succeeded", "failed", "cancelled", "rejected")


def plan_jobs(project: Project, *, only_scenes: Optional[Sequence[int]] = None) -> List[Tuple[int, str]]:
    """Danh sách `(số_cảnh, bước)` cần chạy — **đây chính là hàng chờ**.

    Hàm thuần, không mạng: nhờ vậy tab Dự án hiện được độ dài hàng chờ và vị trí
    hiện tại mà không phải chạy thử.

    Bước đã xong hoặc đã tắt không bao giờ lọt vào đây — đó là cách “chạy tiếp”
    không mua lại thứ đã mua.
    """
    wanted = set(only_scenes) if only_scenes is not None else None
    plan: List[Tuple[int, str]] = []
    for scene in sorted(project.scenes, key=lambda s: s.index):
        if wanted is not None and scene.index not in wanted:
            continue
        for stage in scene.pending_stages():
            plan.append((scene.index, stage))
    return plan


@dataclass
class RunProgress:
    """Ảnh chụp “đang ở đâu trong hàng chờ” để vẽ lên giao diện."""

    total: int = 0
    done: int = 0
    scene_index: int = 0
    stage: str = ""
    started_at: float = field(default_factory=time.time)

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.done)

    def phrase(self) -> str:
        """Một dòng đọc là biết còn phải chờ bao lâu."""
        if self.total <= 0:
            return "Chưa có việc nào trong hàng."
        if self.done >= self.total:
            # Chạy hết hàng rồi. Không có nhánh này thì dòng cuối cùng hiện
            # “Việc 3/2” — một con số vô nghĩa đúng vào lúc khách đọc kỹ nhất.
            return "Đã chạy hết {0}/{0} việc trong hàng.".format(self.total)
        if self.scene_index <= 0:
            return "Đang chuẩn bị hàng chờ ({0} việc).".format(self.total)
        return "Việc {0}/{1} — cảnh {2}, bước {3}. Còn {4} việc xếp sau.".format(
            self.done + 1,
            self.total,
            self.scene_index,
            STAGE_LABEL.get(self.stage, self.stage),
            max(0, self.remaining - 1),
        )


@dataclass
class ProjectSummary:
    """Tổng kết một lượt chạy — trả lời đúng ba câu khách hỏi."""

    scenes_done: int = 0
    scenes_failed: List[int] = field(default_factory=list)
    jobs_done: int = 0
    jobs_failed: int = 0
    jobs_skipped: int = 0
    #: Đã gửi đi (**đã tốn tiền**) nhưng chưa lấy được file về. Đếm riêng khỏi
    #: `jobs_failed` vì hai thứ này khác nhau đúng ở chỗ quan trọng nhất: job hỏng
    #: được hoàn 100% tiền, còn job gián đoạn thì tiền đã đi và kết quả vẫn đang
    #: chờ trên máy chủ — không đi lấy là mất trắng sau 7 ngày.
    jobs_interrupted: int = 0
    spent_micro: int = 0
    stopped_for_money: bool = False
    stopped_by_user: bool = False
    concat_path: str = ""

    def to_text(self) -> str:
        from .money import format_vnd

        lines = ["Đã xong {0} cảnh trọn vẹn.".format(self.scenes_done)]
        lines.append("Đã tiêu: {0}".format(format_vnd(self.spent_micro)))
        if self.jobs_interrupted:
            lines += [
                "",
                "🔁 {0} việc ĐÃ TRẢ TIỀN nhưng tool chưa lấy được kết quả về máy "
                "(máy chủ chạy lâu hơn thường lệ, hoặc mạng đứt lúc tải).".format(
                    self.jobs_interrupted
                ),
                "Kết quả vẫn còn trên máy chủ 7 ngày. Bấm “▶ Chạy tiếp” là tool đi lấy "
                "về bằng đúng mã việc cũ — KHÔNG tạo job mới, KHÔNG trả tiền lần hai.",
            ]
        if self.scenes_failed:
            preview = ", ".join(str(n) for n in self.scenes_failed[:20])
            if len(self.scenes_failed) > 20:
                preview += "…"
            lines += [
                "",
                "❌ {0} cảnh cần làm lại: {1}".format(len(self.scenes_failed), preview),
                "Job hỏng đã được hoàn 100% tiền — bạn không mất đồng nào cho mấy cảnh này. "
                "Bấm “↻ Chạy lại cảnh hỏng” là tool chỉ chạy đúng những cảnh đó.",
            ]
        if self.stopped_for_money:
            lines += [
                "",
                "⏸ Ví hết tiền nên tool dừng lại. {0} việc còn lại CHƯA gửi đi, "
                "bạn không bị trừ đồng nào cho chúng.".format(self.jobs_skipped),
                "Nạp tiền xong bấm “▶ Chạy tiếp” là chạy đúng chỗ đã dừng.",
            ]
        elif self.stopped_by_user:
            lines += [
                "",
                "⏸ Bạn đã bấm dừng. Việc đang chạy dở đã được huỷ và hoàn tiền tạm giữ. "
                "Bấm “▶ Chạy tiếp” để làm nốt.",
            ]
        if self.concat_path:
            lines += [
                "",
                "📎 Đã ghi danh sách ghép: {0}".format(os.path.basename(self.concat_path)),
                "Ghép cả tập bằng một lệnh:",
                "   ffmpeg -f concat -safe 0 -i {0} -c copy tap-phim.mp4".format(
                    os.path.basename(self.concat_path)
                ),
            ]
        return "\n".join(lines)


class ProjectRunner:
    """Chạy cả dự án ở một luồng nền duy nhất.

    Sự kiện đẩy vào `events` (cùng hàng đợi với :class:`~core.jobs.JobManager`):

    | Loại | Dữ liệu | Ý nghĩa |
    |---|---|---|
    | `"project"` | `None` | Có gì đó đổi, vẽ lại bảng cảnh |
    | `"project-log"` | `str` | Một dòng nhật ký (đã che khoá) |
    | `"project-done"` | `ProjectSummary` | Chạy xong cả lượt |
    """

    def __init__(self, client_factory: Callable[[], ShopAPI], events: "queue.Queue") -> None:
        self._client_factory = client_factory
        self._events = events
        self._client: Optional[ShopAPI] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._out_of_money = False
        self._project: Optional[Project] = None
        self.progress = RunProgress()

    # ── Truy vấn ─────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def project(self) -> Optional[Project]:
        return self._project

    # ── Điều khiển ───────────────────────────────────────────────────────────

    def start(self, project: Project, *, only_scenes: Optional[Sequence[int]] = None) -> bool:
        """Bắt đầu chạy. Trả `False` nếu đang có lượt khác chạy hoặc không còn việc."""
        if self.is_running:
            return False
        plan = plan_jobs(project, only_scenes=only_scenes)
        if not plan:
            return False

        self._project = project
        self._stop.clear()
        self._out_of_money = False
        self.progress = RunProgress(total=len(plan))
        if self._client is None:
            self._client = self._client_factory()

        self._thread = threading.Thread(
            target=self._run, args=(project, plan), daemon=True, name="shopapi-project"
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        """Dừng sau khi xử lý xong việc đang chạy (có huỷ job để hoàn tiền)."""
        self._stop.set()
        self._log("Đang dừng… việc đang chạy sẽ được huỷ và hoàn tiền tạm giữ.")

    def shutdown(self) -> None:
        self._stop.set()
        client, self._client = self._client, None
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001 — đang tắt, lỗi đóng kết nối không quan trọng
                pass

    def reset_for_retry(self, project: Project, scenes: Sequence[int]) -> int:
        """Chuẩn bị chạy lại một số cảnh. Trả về số **bước** sẽ chạy lại.

        Quy tắc khoá chống trùng (`Idempotency-Key`), y hệt :meth:`JobManager.retry`:

        * Bước đã gửi đi rồi mà hỏng → job cũ đã kết thúc thật sự, nên sinh khoá
          **mới**. Dùng lại khoá cũ trong 24 giờ chỉ nhận lại đúng phản hồi hỏng cũ.
        * Bước chưa từng gửi đi → **giữ** khoá cũ. Nó chưa được dùng nên vẫn còn
          nguyên giá trị bảo vệ: lỡ request cũ ĐÃ tới máy chủ thì lần này nhận lại
          job đó chứ không tạo thêm job thứ hai.

        **Không đụng vào bước đã xong.** Chạy lại cảnh 7 mà xoá mất file ảnh đã trả
        tiền của cảnh 7 là lỗi không sửa được.
        """
        wanted = set(scenes)
        touched = 0
        for scene in project.scenes:
            if scene.index not in wanted:
                continue
            for name in PIPELINE:
                state = scene.stages[name]
                if state.status in (ST_DONE, ST_OFF):
                    continue
                if state.job_id and not state.files:
                    # Còn cơ hội lấy lại kết quả đã trả tiền → giữ nguyên `job_id`
                    # để lượt chạy tới đi HỎI LẠI thay vì tạo job mới.
                    state.status = ST_INTERRUPTED
                else:
                    if state.job_id:
                        state.job_id = None
                        state.idempotency_key = str(uuid.uuid4())
                    state.status = ST_WAITING
                state.attempts = 0
                state.message = "Đang chờ chạy lại."
                touched += 1
        if touched:
            project.save()
            self._emit()
        return touched

    # ── Luồng nền ────────────────────────────────────────────────────────────

    def _run(self, project: Project, plan: List[Tuple[int, str]]) -> None:
        by_index = {s.index: s for s in project.scenes}
        summary = ProjectSummary()
        # Bước bị bỏ vì bước nó phụ thuộc đã hỏng — để không thử vô ích.
        broken: set = set()

        self._log("Bắt đầu chạy {0} việc cho dự án “{1}”.".format(len(plan), project.name))

        for position, (scene_index, stage) in enumerate(plan):
            scene = by_index.get(scene_index)
            if scene is None:
                continue
            self.progress.done = position
            self.progress.scene_index = scene_index
            self.progress.stage = stage

            state = scene.stages[stage]
            if state.status in (ST_DONE, ST_OFF):
                continue

            if self._out_of_money or self._stop.is_set():
                self._skip(state, summary)
                continue

            needed = STAGE_NEEDS.get(stage)
            if needed and (scene_index, needed) in broken:
                state.status = ST_SKIPPED
                state.message = (
                    "Bỏ qua vì bước {0} của cảnh này chưa xong. Làm lại bước đó rồi "
                    "chạy lại cảnh là có luôn.".format(STAGE_LABEL.get(needed, needed))
                )
                summary.jobs_skipped += 1
                self._save(project)
                continue

            ok = self._do_stage(project, scene, stage)
            if ok:
                summary.jobs_done += 1
            elif state.status == ST_SKIPPED:
                summary.jobs_skipped += 1
            else:
                if state.status == ST_INTERRUPTED:
                    summary.jobs_interrupted += 1
                else:
                    summary.jobs_failed += 1
                # Dù hỏng hay gián đoạn, bước sau vẫn thiếu đầu vào → bỏ, khỏi thử vô ích.
                broken.add((scene_index, stage))
            self._save(project)

        self.progress.done = len(plan)
        summary.stopped_for_money = self._out_of_money
        summary.stopped_by_user = self._stop.is_set() and not self._out_of_money
        summary.scenes_done = sum(1 for s in project.scenes if s.is_done)
        summary.scenes_failed = project.failed_scene_numbers()
        summary.spent_micro = project.spent_micro()
        summary.concat_path = project.write_concat_list() or ""
        self._save(project)
        self._events.put(("project-done", summary))

    def _skip(self, state: StageState, summary: ProjectSummary) -> None:
        """Đánh dấu một bước là chưa chạy — **chưa gửi đi nên chưa mất đồng nào**."""
        state.status = ST_SKIPPED
        state.message = (
            "Chưa chạy vì ví hết tiền. Bước này chưa gửi đi nên bạn chưa bị trừ đồng nào."
            if self._out_of_money
            else "Chưa chạy vì bạn đã bấm dừng. Chưa gửi đi nên chưa tốn đồng nào."
        )
        summary.jobs_skipped += 1
        self._emit()

    def _do_stage(self, project: Project, scene: Scene, stage: str) -> bool:
        """Chạy trọn một bước của một cảnh. Trả `True` khi có file về máy."""
        state = scene.stages[stage]
        state.attempts += 1
        if state.attempts > MAX_STAGE_ATTEMPTS:
            state.status = ST_FAILED
            state.message = (
                "Đã thử {0} lần vẫn không được nên tool dừng lại thay vì chạy vòng vo. "
                "Bạn sửa nội dung cảnh này rồi chạy lại giúp mình.".format(MAX_STAGE_ATTEMPTS)
            )
            self._emit()
            return False

        state.status = ST_RUNNING
        state.message = "Đang gửi lên máy chủ…"
        self._emit()

        try:
            final: Optional[Dict[str, Any]] = None

            # ── A. Đã gửi đi trước đó mà chưa lấy được file → HỎI LẠI ─────────
            # Đây là chỗ giữ tiền quan trọng nhất của cả module. Job này đã trừ
            # tiền rồi; tạo job mới là trả tiền lần hai cho đúng một nội dung.
            if state.needs_recheck:
                state.message = "Đang hỏi lại máy chủ về việc đã gửi lần trước…"
                self._emit()
                final = self._wait_job(state, state.job_id or "")
                if final is not None and final.get("status") != "succeeded":
                    # Job cũ đã kết thúc và hỏng thật → giờ mới được phép tạo mới.
                    self._log(
                        "Cảnh {0} · {1}: job cũ {2} đã hỏng, tạo job mới.".format(
                            scene.index, STAGE_LABEL.get(stage, stage), state.job_id
                        )
                    )
                    state.job_id = None
                    state.idempotency_key = str(uuid.uuid4())
                    final = None

            # ── B. Tạo job mới ───────────────────────────────────────────────
            if final is None and state.job_id is None:
                job = self._create_with_retry(project, scene, stage, state)
                if job is None:
                    return False
                state.job_id = str(job.get("id") or "")
                state.message = "Máy chủ đã nhận việc, đang xếp hàng…"
                self._save(project)  # ghi NGAY: có mã việc là đã tốn tiền
                final = self._wait_job(state, state.job_id, job.get("estimated_seconds"))

            if final is None:
                return False

            state.cost_micro = _as_text(final.get("cost"))
            state.refunded_micro = _as_text(final.get("refunded"))

            if final.get("status") != "succeeded":
                self._mark_job_failed(state, final)
                return False

            return self._download(project, scene, stage, state, final)

        except Exception as exc:  # noqa: BLE001 — một bước hỏng không được kéo sập tool
            advice = describe(exc)
            if advice.needs_topup:
                self._out_of_money = True
                state.status = ST_SKIPPED
                state.message = advice.one_line()
                self._log("Ví hết tiền — dừng cả dự án. Việc còn lại chưa gửi đi nên không mất tiền.")
            else:
                state.status = ST_FAILED
                state.message = advice.one_line()
            self._emit()
            return False

    # ── Gọi API ──────────────────────────────────────────────────────────────

    def _create_with_retry(
        self, project: Project, scene: Scene, stage: str, state: StageState
    ) -> Optional[Dict[str, Any]]:
        """Tạo job, tự chờ và thử lại với lỗi tạm thời (429/503/mất mạng)."""
        for attempt in range(_CREATE_ATTEMPTS):
            if self._stop.is_set():
                state.status = ST_SKIPPED
                state.message = "Bạn đã dừng trước khi bước này được gửi đi — chưa tốn tiền."
                self._emit()
                return None
            try:
                return self._create(project, scene, stage, state).to_dict()
            except Exception as exc:  # noqa: BLE001
                advice = describe(exc)
                if advice.needs_topup:
                    self._out_of_money = True
                    state.status = ST_SKIPPED
                    state.message = advice.one_line()
                    self._log(
                        "Ví hết tiền ở cảnh {0}. Những việc còn lại chưa gửi đi nên "
                        "không bị trừ tiền.".format(scene.index)
                    )
                    self._emit()
                    return None
                if not advice.retryable or attempt == _CREATE_ATTEMPTS - 1:
                    state.status = ST_FAILED
                    state.message = advice.one_line()
                    self._emit()
                    return None
                delay = retry_after_seconds(exc, attempt)
                state.message = "{0} — chờ {1:.0f} giây rồi thử lại.".format(advice.title, delay)
                self._emit()
                if self._sleep(delay):
                    state.status = ST_SKIPPED
                    state.message = "Bạn đã dừng trong lúc chờ thử lại — chưa tốn tiền."
                    self._emit()
                    return None
        return None

    def _create(self, project: Project, scene: Scene, stage: str, state: StageState):
        """Gọi đúng endpoint cho từng bước. Chỗ duy nhất dây chuyền chạm vào SDK."""
        client = self._client
        assert client is not None
        options = project.options

        if stage == STAGE_VOICE:
            return client.tts.create(
                text=scene.narration,
                voice_id=options.voice_id,
                speed=options.speed,
                format=options.audio_format,
                idempotency_key=state.idempotency_key,
            )
        if stage == STAGE_IMAGE:
            return client.images.create(
                prompt=scene.image_prompt or scene.narration,
                n=int(options.images_per_scene),
                aspect_ratio=options.aspect_ratio,
                idempotency_key=state.idempotency_key,
            )
        if stage == STAGE_VIDEO:
            return client.videos.create(
                prompt=scene.video_prompt or scene.narration,
                engine=options.engine,
                # `auto` → để SDK/máy chủ tự chọn thời lượng theo engine nó lấy.
                duration=None if options.engine == ENGINE_AUTO else options.video_duration(),
                aspect_ratio=options.aspect_ratio,
                image_url=self._first_frame(scene),
                idempotency_key=state.idempotency_key,
            )
        raise ValueError("Bước không hợp lệ: {0}".format(stage))

    def _first_frame(self, scene: Scene) -> Optional[str]:
        """URL ảnh dùng làm khung hình mở đầu clip, hoặc `None`.

        Chỉ dùng khi ảnh còn **mới**: link kết quả sống 7 ngày, đưa link chết vào
        job video là job trượt ngay lúc tạo kèm một thông báo lỗi khó hiểu.
        """
        image = scene.stages.get(STAGE_IMAGE)
        if image is None or not image.url or not image.is_done:
            return None
        if time.time() - image.updated_at > IMAGE_URL_MAX_AGE:
            self._log(
                "Cảnh {0}: link ảnh đã quá {1} ngày nên tool làm clip không kèm khung hình "
                "mở đầu. Muốn giống hệt ảnh thì chạy lại bước Ảnh trước.".format(
                    scene.index, IMAGE_URL_MAX_AGE // 86400
                )
            )
            return None
        return image.url

    def _wait_job(
        self,
        state: StageState,
        job_id: str,
        estimated_seconds: Optional[float] = None,
        *,
        timeout: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Hỏi trạng thái job tới khi kết thúc, vẫn nhả ra ngay khi bấm Dừng.

        Không dùng `client.jobs.wait()`: nó ngủ trong luồng và không dừng giữa
        chừng được, mà ở đây bấm Dừng là phải dừng.
        """
        client = self._client
        assert client is not None
        if not job_id:
            return None

        limit = float(
            timeout
            if timeout is not None
            else JOB_WAIT_TIMEOUT_BY_STAGE.get(state.stage, JOB_WAIT_TIMEOUT)
        )
        delays = poll_delays(estimated_seconds, None)
        started = time.monotonic()

        while True:
            if self._stop.is_set():
                return self._stop_job(state, job_id)
            if time.monotonic() - started > limit:
                state.status = ST_INTERRUPTED
                state.message = (
                    "Job chạy quá {0} phút nên tool ngừng theo dõi. Tiền đã trả và job vẫn "
                    "có thể xong trên máy chủ — bấm “▶ Chạy tiếp” là tool đi lấy kết quả "
                    "về, KHÔNG tạo job mới.".format(int(limit) // 60)
                )
                self._emit()
                return None

            if self._sleep(min(next(delays), 5.0)):
                return self._stop_job(state, job_id)

            try:
                job = client.jobs.retrieve(job_id).to_dict()
            except Exception as exc:  # noqa: BLE001
                advice = describe(exc)
                if not advice.retryable:
                    state.status = ST_FAILED
                    state.message = advice.one_line()
                    self._emit()
                    return None
                continue  # trục trặc lúc hỏi thăm: vòng sau hỏi lại

            status = job.get("status")
            note = job.get("message") or _STATUS_NOTE.get(status, "Đang xử lý…")
            state.message = str(note)
            self._emit()
            if status in _TERMINAL:
                return job

    def _stop_job(self, state: StageState, job_id: str) -> Optional[Dict[str, Any]]:
        """Khách bấm Dừng khi job đang chạy: huỷ để lấy lại tiền tạm giữ.

        **Nhưng vẫn hỏi lại một lần sau khi huỷ.** Job có thể vừa xong đúng lúc đó
        — tiền đã trả rồi thì phải lấy hàng về, chứ không bỏ cả tiền lẫn kết quả.
        """
        client = self._client
        if client is None:
            return None
        try:
            client.jobs.cancel(job_id)
        except Exception as exc:  # noqa: BLE001 — thường là job đã kết thúc trước khi kịp huỷ
            self._log("Không huỷ được job {0}: {1}".format(job_id, exc))
        try:
            job = client.jobs.retrieve(job_id).to_dict()
        except Exception:  # noqa: BLE001
            state.status = ST_INTERRUPTED
            state.message = "Đã dừng. Bấm “▶ Chạy tiếp” để tool hỏi lại việc này."
            self._emit()
            return None

        if job.get("status") == "succeeded":
            self._log("Job {0} đã kịp xong trước khi huỷ — tool tải kết quả về luôn.".format(job_id))
            return job
        state.status = ST_SKIPPED
        state.message = "Đã dừng theo yêu cầu. Tiền tạm giữ đã hoàn về ví bạn."
        self._emit()
        return None

    # ── Kết quả ──────────────────────────────────────────────────────────────

    def _download(
        self,
        project: Project,
        scene: Scene,
        stage: str,
        state: StageState,
        job: Dict[str, Any],
    ) -> bool:
        """Tải file kết quả về đúng tên có đánh số của dự án."""
        outputs = extract_outputs(job)
        if not outputs:
            state.status = ST_FAILED
            state.message = (
                "Máy chủ báo xong nhưng không kèm link kết quả. Bạn báo hỗ trợ kèm mã "
                "job {0} giúp mình.".format(state.job_id or "?")
            )
            self._emit()
            return False

        state.url = str(outputs[0].get("url") or "")
        saved: List[str] = []
        for order, output in enumerate(outputs, start=1):
            url = str(output.get("url") or "")
            if not url:
                continue
            extension = guess_extension(url, str(output.get("format") or ""))
            dest = project.output_path(scene, stage, extension=extension, order=order)
            state.message = "Đang tải file {0}/{1} về máy…".format(order, len(outputs))
            self._emit()
            try:
                download_to(url, dest, should_stop=self._stop.is_set)
            except DownloadError as exc:
                # Job đã xong và đã trả tiền — chỉ là chưa lấy được về. Đánh dấu
                # **gián đoạn** chứ không phải lỗi, để lần chạy tiếp đi tải lại
                # bằng chính `job_id` này thay vì mua lần nữa.
                state.status = ST_INTERRUPTED
                state.message = (
                    "{0} Kết quả vẫn còn trên máy chủ (7 ngày) — bấm “▶ Chạy tiếp” "
                    "để tải lại, không mất thêm tiền.".format(exc)
                )
                self._emit()
                return False
            saved.append(dest)

        state.files = saved
        state.status = ST_DONE
        state.updated_at = time.time()
        state.message = "Đã lưu {0}.".format(", ".join(os.path.basename(p) for p in saved))
        self._log(
            "Cảnh {0} · {1}: xong → {2}".format(
                scene.index, STAGE_LABEL.get(stage, stage),
                ", ".join(os.path.basename(p) for p in saved),
            )
        )
        self._emit()
        return True

    def _mark_job_failed(self, state: StageState, job: Dict[str, Any]) -> None:
        """Job kết thúc ở `failed`/`rejected`/`cancelled` — luôn nói rõ chuyện hoàn tiền."""
        error = job.get("error") if isinstance(job.get("error"), dict) else {}
        code = error.get("code")
        text = str(error.get("message") or "Job không hoàn thành được.")
        if code == "content_rejected" or job.get("status") == "rejected":
            text = "Nội dung cảnh này bị từ chối vì vi phạm quy định. Bạn sửa lời/mô tả rồi chạy lại."
        elif job.get("status") == "cancelled":
            text = "Job đã bị huỷ."

        refund = " Job hỏng không bị tính tiền."
        if state.refunded_micro:
            from .money import format_vnd

            try:
                if int(state.refunded_micro) > 0:
                    refund = " Đã hoàn {0} về ví bạn.".format(format_vnd(state.refunded_micro))
            except (TypeError, ValueError):
                pass
        state.status = ST_FAILED
        state.message = text + refund
        self._emit()

    # ── Tiện ích ─────────────────────────────────────────────────────────────

    def _sleep(self, seconds: float) -> bool:
        """Ngủ nhưng tỉnh ngay khi bấm Dừng. `True` = bị dừng giữa chừng."""
        return self._stop.wait(max(0.0, seconds))

    def _save(self, project: Project) -> None:
        """Ghi sổ sau **mỗi** thay đổi: tắt tool giữa chừng vẫn biết đang dở tới đâu."""
        try:
            project.save()
        except OSError as exc:
            self._log("Không ghi được sổ dự án: {0}".format(exc))
        self._emit()

    def _emit(self) -> None:
        self._events.put(("project", None))

    def _log(self, message: str) -> None:
        # Che khoá TRƯỚC khi rời luồng nền — không có đường nào để khoá lọt vào log.
        self._events.put(("project-log", redact(message)))


#: Chú thích thân thiện cho từng trạng thái máy chủ trả về.
_STATUS_NOTE = {
    "queued": "Đang xếp hàng chờ máy rảnh…",
    "running": "Máy đang tạo nội dung…",
    "retrying": "Máy gặp trục trặc, hệ thống đang tự thử lại…",
    "succeeded": "Xong! Đang chuẩn bị tải về.",
    "failed": "Job không thành công.",
    "cancelled": "Job đã bị huỷ.",
    "rejected": "Nội dung bị từ chối.",
}


def _as_text(value: Any) -> str:
    """Số tiền luôn là chuỗi µVND. Máy chủ lỡ trả số thì đổi sang chuỗi, không sang float."""
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, (int, str)):
        return str(value)
    return ""
