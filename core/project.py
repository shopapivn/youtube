"""Dự án làm video: mô hình dữ liệu, cách đặt tên file, và cách nhớ đang dở tới đâu.

Một **dự án** là cả một tập video: kịch bản → nhiều cảnh → mỗi cảnh có ba bước
*giọng đọc → ảnh → video*. Đây là thứ tách tool khỏi mấy tab lẻ: tab Giọng nói
làm được một file mp3, còn ở đây khách dán một bài viết vào và nhận về nguyên
bộ nguyên liệu đã đánh số sẵn để kéo vào phần mềm dựng.

## Ba quy tắc giữ tiền cho khách

**1. Trạng thái “xong” không bao giờ bị hạ xuống.** Bước nào đã tải được file về
ổ cứng là đã trả tiền rồi; không có đường nào trong module này đưa nó ngược về
“chờ”. Chạy lại một cảnh chỉ chạy lại những bước *chưa* có file.

**2. Tin file trên ổ cứng hơn tin trạng thái trong JSON.** File `du-an.json` có
thể cũ (tool bị tắt đột ngột), nhưng file mp3 nằm đó thì chắc chắn đã tải xong.
:meth:`Scene.sync_with_disk` đối chiếu lại mỗi lần mở dự án.

**3. Có `job_id` là đã tốn tiền.** Bước nào đã gửi đi mà chưa lấy được file thì
đánh dấu **gián đoạn** chứ không đánh dấu lỗi, và lần chạy tiếp phải đi *hỏi lại*
job cũ trước khi dám tạo job mới. Kết quả sống 7 ngày — trong 7 ngày đó tạo lại
là trả tiền hai lần cho đúng một nội dung.

Module này **không gọi mạng**. Nó chỉ mô tả dữ liệu và đọc/ghi đĩa, nên test được
toàn bộ bằng thư mục tạm.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .pricing import ENGINE_VEO3, VIDEO_DURATION_BY_ENGINE
from .scenes import SceneDraft, make_scenes

__all__ = [
    "PROJECT_FILENAME",
    "SCRIPT_FILENAME",
    "CONCAT_FILENAME",
    "STAGE_VOICE",
    "STAGE_IMAGE",
    "STAGE_VIDEO",
    "PIPELINE",
    "STAGE_LABEL",
    "STAGE_FOLDER",
    "ENGINE_AUTO",
    "ST_WAITING",
    "ST_RUNNING",
    "ST_DONE",
    "ST_FAILED",
    "ST_INTERRUPTED",
    "ST_SKIPPED",
    "ST_OFF",
    "STATUS_LABEL",
    "MAX_STAGE_ATTEMPTS",
    "StageState",
    "Scene",
    "ProjectOptions",
    "Project",
    "slugify",
    "projects_root",
    "list_projects",
]

#: Sổ ghi của dự án, nằm ngay trong thư mục dự án.
PROJECT_FILENAME = "du-an.json"
#: Bản sao kịch bản gốc — để khách mở lại xem mình đã dán gì vào.
SCRIPT_FILENAME = "kich-ban.txt"
#: Danh sách ghép cho ffmpeg, sinh ra khi có ít nhất một clip xong.
CONCAT_FILENAME = "ghep-video.txt"

# ── Ba bước của một cảnh ──────────────────────────────────────────────────────

STAGE_VOICE = "voice"
STAGE_IMAGE = "image"
STAGE_VIDEO = "video"

#: **Thứ tự cố định.** Ảnh phải xong trước video vì clip lấy chính tấm ảnh đó làm
#: khung hình đầu (`image_url`) — nhờ vậy cả tập giữ được một phong cách hình.
PIPELINE = (STAGE_VOICE, STAGE_IMAGE, STAGE_VIDEO)

STAGE_LABEL: Dict[str, str] = {
    STAGE_VOICE: "Giọng đọc",
    STAGE_IMAGE: "Ảnh",
    STAGE_VIDEO: "Video",
}

#: Thư mục con cho từng bước. Tên tiếng Việt không dấu để mọi phần mềm dựng đều mở được.
STAGE_FOLDER: Dict[str, str] = {
    STAGE_VOICE: "giong-noi",
    STAGE_IMAGE: "anh",
    STAGE_VIDEO: "video",
}

#: Để máy chủ tự chọn engine video. **Cẩn thận**: nó có thể định tuyến sang
#: Seedance, đắt gấp đôi Veo3 — mọi ước tính phải lấy giá Seedance làm mốc.
ENGINE_AUTO = "auto"

# ── Trạng thái một bước ───────────────────────────────────────────────────────

ST_WAITING = "cho"
ST_RUNNING = "dang-chay"
ST_DONE = "xong"
ST_FAILED = "loi"
#: Đã gửi đi (có `job_id`) nhưng chưa lấy được file — **đã tốn tiền**. Lần chạy
#: tiếp phải hỏi lại job cũ chứ không được tạo job mới.
ST_INTERRUPTED = "gian-doan"
#: Chưa từng gửi đi vì ví hết tiền hoặc khách bấm dừng. Không tốn đồng nào.
ST_SKIPPED = "chua-chay"
#: Khách tắt bước này cho cả dự án (ví dụ chỉ cần ảnh, không cần video).
ST_OFF = "tat"

STATUS_LABEL: Dict[str, str] = {
    ST_WAITING: "⏳ Chờ",
    ST_RUNNING: "⚙️ Đang chạy",
    ST_DONE: "✅ Xong",
    ST_FAILED: "❌ Lỗi",
    ST_INTERRUPTED: "🔁 Gián đoạn",
    ST_SKIPPED: "⏸ Chưa chạy",
    ST_OFF: "— Tắt",
}

#: Trạng thái coi như đã kết thúc tốt đẹp, **không bao giờ chạy lại**.
_TERMINAL_GOOD = (ST_DONE, ST_OFF)

#: Thử lại tối đa ngần này lần cho một bước rồi mới chịu thua và báo khách.
#: Kinh nghiệm vận hành: cứ thử mãi là đốt tiền trong im lặng.
MAX_STAGE_ATTEMPTS = 3

#: Ký tự không dùng được trong tên thư mục.
_SLUG_BAD = re.compile(r"[^0-9a-zA-ZÀ-ỹ _-]+")
_SLUG_SPACE = re.compile(r"[\s_]+")


def slugify(name: str, *, fallback: str = "du-an") -> str:
    """Đổi tên dự án khách gõ thành tên thư mục dùng được trên Windows.

    Giữ lại chữ có dấu — Windows xử lý được, và khách nhìn thư mục là nhận ra
    ngay dự án của mình. Chỉ bỏ những ký tự hệ điều hành thật sự cấm.

    >>> slugify("Tập 12: Bí ẩn sao Hoả")
    'Tập-12-Bí-ẩn-sao-Hoả'
    """
    cleaned = _SLUG_BAD.sub(" ", name or "")
    cleaned = _SLUG_SPACE.sub("-", cleaned.strip())
    cleaned = cleaned.strip("-.")
    if not cleaned:
        return fallback
    return cleaned[:60].rstrip("-.") or fallback


def projects_root(output_dir: str) -> str:
    """Thư mục chứa tất cả dự án, nằm cạnh `giong-noi/`, `anh/`, `video/`."""
    return os.path.join(output_dir, "du-an")


@dataclass
class StageState:
    """Một bước của một cảnh: nó đang ở đâu, đã tốn bao nhiêu, file nằm chỗ nào."""

    stage: str
    status: str = ST_WAITING
    #: Mã việc máy chủ cấp. **Có giá trị này nghĩa là đã tốn tiền.**
    job_id: Optional[str] = None
    #: Sinh một lần cho mỗi lần thử, giữ nguyên khi tool tự thử lại trong cùng lần đó.
    idempotency_key: str = field(default_factory=lambda: str(uuid.uuid4()))
    #: File đã tải về máy (đường dẫn tuyệt đối).
    files: List[str] = field(default_factory=list)
    #: Link kết quả trên máy chủ — bước sau dùng nó làm đầu vào (ảnh → video).
    url: str = ""
    cost_micro: str = ""
    refunded_micro: str = ""
    message: str = ""
    attempts: int = 0
    updated_at: float = field(default_factory=time.time)

    @property
    def is_done(self) -> bool:
        return self.status == ST_DONE

    @property
    def needs_recheck(self) -> bool:
        """Đã gửi đi mà chưa có file → phải đi hỏi lại thay vì tạo job mới."""
        return bool(self.job_id) and not self.files

    @property
    def is_parked(self) -> bool:
        """Đã thử đủ số lần cho phép — dừng lại, chờ khách xem tay."""
        return self.status == ST_FAILED and self.attempts >= MAX_STAGE_ATTEMPTS

    def label(self) -> str:
        return STATUS_LABEL.get(self.status, self.status)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "job_id": self.job_id,
            "idempotency_key": self.idempotency_key,
            "files": list(self.files),
            "url": self.url,
            "cost_micro": self.cost_micro,
            "refunded_micro": self.refunded_micro,
            "message": self.message,
            "attempts": int(self.attempts),
            "updated_at": float(self.updated_at),
        }

    @classmethod
    def from_dict(cls, data: Any, *, stage: str) -> "StageState":
        if not isinstance(data, dict):
            return cls(stage=stage)
        state = cls(
            stage=str(data.get("stage") or stage),
            status=str(data.get("status") or ST_WAITING),
            job_id=(str(data["job_id"]) if data.get("job_id") else None),
            files=[str(p) for p in (data.get("files") or []) if p],
            url=str(data.get("url") or ""),
            cost_micro=str(data.get("cost_micro") or ""),
            refunded_micro=str(data.get("refunded_micro") or ""),
            message=str(data.get("message") or ""),
            attempts=_as_int(data.get("attempts")),
        )
        key = data.get("idempotency_key")
        if key:
            state.idempotency_key = str(key)
        try:
            state.updated_at = float(data.get("updated_at") or time.time())
        except (TypeError, ValueError):
            state.updated_at = time.time()
        # Đang chạy dở lúc tool bị tắt → **gián đoạn**, không phải lỗi. Khác biệt
        # này quyết định lần sau tool đi hỏi lại job cũ hay tạo job mới (tốn tiền).
        if state.status == ST_RUNNING:
            state.status = ST_INTERRUPTED if state.job_id else ST_WAITING
            state.message = (
                "Tool bị đóng khi bước này đang chạy. Job đã gửi đi rồi nên bấm "
                "“Chạy tiếp” là tool đi lấy kết quả về, KHÔNG tạo job mới."
                if state.job_id
                else "Tool bị đóng trước khi bước này được gửi đi — chưa tốn đồng nào."
            )
        return state


@dataclass
class Scene:
    """Một cảnh: lời đọc, mô tả hình, và trạng thái ba bước."""

    index: int
    narration: str
    image_prompt: str = ""
    video_prompt: str = ""
    stages: Dict[str, StageState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for stage in PIPELINE:
            self.stages.setdefault(stage, StageState(stage=stage))

    # ── Truy vấn ─────────────────────────────────────────────────────────────

    def stage(self, name: str) -> StageState:
        return self.stages[name]

    def active_stages(self) -> List[str]:
        """Những bước dự án này thật sự chạy (bỏ bước khách đã tắt)."""
        return [s for s in PIPELINE if self.stages[s].status != ST_OFF]

    @property
    def is_done(self) -> bool:
        """Xong khi **mọi** bước còn bật đều xong."""
        active = self.active_stages()
        return bool(active) and all(self.stages[s].is_done for s in active)

    @property
    def is_failed(self) -> bool:
        return any(self.stages[s].status == ST_FAILED for s in self.active_stages())

    @property
    def is_running(self) -> bool:
        return any(self.stages[s].status == ST_RUNNING for s in self.active_stages())

    def status_word(self) -> str:
        """Một từ tóm tắt cả cảnh, để tô màu dòng trên bảng tiến độ."""
        if self.is_running:
            return ST_RUNNING
        if self.is_done:
            return ST_DONE
        if self.is_failed:
            return ST_FAILED
        if any(self.stages[s].status == ST_INTERRUPTED for s in self.active_stages()):
            return ST_INTERRUPTED
        if any(self.stages[s].status == ST_SKIPPED for s in self.active_stages()):
            return ST_SKIPPED
        return ST_WAITING

    def pending_stages(self) -> List[str]:
        """Những bước còn phải làm, đúng thứ tự dây chuyền.

        Bước đã xong hoặc đã tắt **không bao giờ** xuất hiện ở đây — đó là cách
        “chạy tiếp” không bao giờ mua lại thứ đã mua.
        """
        return [s for s in PIPELINE if self.stages[s].status not in _TERMINAL_GOOD]

    def spent_micro(self) -> int:
        """Tiền thật đã tiêu cho cảnh này (đã trừ phần hoàn lại)."""
        total = 0
        for state in self.stages.values():
            total += _as_int(state.cost_micro) - _as_int(state.refunded_micro)
        return max(0, total)

    # ── Đối chiếu với ổ cứng ─────────────────────────────────────────────────

    def sync_with_disk(self) -> bool:
        """Sửa lại trạng thái theo file thật đang có. Trả `True` nếu có thay đổi.

        Hai hướng, cùng một nguyên tắc *file nói thật hơn JSON*:

        * Ghi “xong” mà file đã bị xoá → hạ xuống “chờ” để chạy lại. Đây là ngoại
          lệ duy nhất của quy tắc không-hạ-cấp: không còn file thì cũng chẳng còn
          gì để bảo vệ.
        * Chưa ghi “xong” mà file đã nằm đó (tool tắt ngay sau khi tải xong) →
          nâng lên “xong”, khỏi bắt khách trả tiền lần hai.
        """
        changed = False
        for state in self.stages.values():
            if state.status == ST_OFF:
                continue
            existing = [p for p in state.files if os.path.isfile(p)]
            if state.status == ST_DONE and not existing:
                state.status = ST_WAITING
                state.files = []
                state.message = "File kết quả không còn trên ổ cứng nên bước này cần chạy lại."
                changed = True
            elif existing and state.status != ST_DONE:
                state.status = ST_DONE
                state.files = existing
                state.message = "Đã có sẵn file trên ổ cứng từ lần chạy trước."
                changed = True
            elif len(existing) != len(state.files):
                state.files = existing
                changed = True
        return changed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "narration": self.narration,
            "image_prompt": self.image_prompt,
            "video_prompt": self.video_prompt,
            "stages": {name: state.to_dict() for name, state in self.stages.items()},
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Scene":
        data = data if isinstance(data, dict) else {}
        raw_stages = data.get("stages") if isinstance(data.get("stages"), dict) else {}
        scene = cls(
            index=_as_int(data.get("index"), 1),
            narration=str(data.get("narration") or ""),
            image_prompt=str(data.get("image_prompt") or ""),
            video_prompt=str(data.get("video_prompt") or ""),
            stages={
                name: StageState.from_dict(raw_stages.get(name), stage=name) for name in PIPELINE
            },
        )
        return scene


@dataclass
class ProjectOptions:
    """Cài đặt áp cho cả dự án. Sửa ở đây là đổi cho mọi cảnh."""

    voice_id: str = "vi_female_01"
    speed: float = 1.0
    audio_format: str = "mp3"
    aspect_ratio: str = "16:9"
    engine: str = ENGINE_VEO3
    #: Số ảnh mỗi cảnh. Nhiều hơn 1 để chọn tấm ưng ý; tấm **đầu** được dùng làm
    #: khung hình mở đầu cho clip.
    images_per_scene: int = 1
    #: Phong cách hình, nối vào cuối mọi mô tả — thứ giữ cả tập trông cùng một tay làm.
    style: str = ""
    #: Bước nào được bật. Khách chỉ cần lời đọc thì tắt hai bước sau cho đỡ tốn.
    do_voice: bool = True
    do_image: bool = True
    do_video: bool = True
    #: Số ký tự lời đọc mỗi cảnh khi tự chia. 0 = tự tính theo độ dài clip của engine.
    target_chars: int = 0

    def video_duration(self) -> int:
        """Số giây của một clip, ghim theo engine (CONTRACT.md §2.1).

        `auto` để máy chủ chọn nên tool không biết trước; lấy 8 giây (Veo3) làm
        giá trị gửi đi, còn phần **tiền** thì luôn ước theo Seedance cho an toàn.
        """
        return VIDEO_DURATION_BY_ENGINE.get(self.engine, 8)

    def effective_target_chars(self) -> int:
        """Độ dài lời đọc mỗi cảnh — khớp với độ dài clip nếu khách không tự đặt."""
        if self.target_chars > 0:
            return int(self.target_chars)
        from .scenes import chars_for_duration

        # `auto` có thể ra clip 10 giây, nên cắt theo 10 giây: lời đọc ngắn hơn
        # hình thì thừa vài giây im lặng, dài hơn hình thì phải cắt tay.
        seconds = 10 if self.engine == ENGINE_AUTO else self.video_duration()
        return chars_for_duration(seconds)

    def enabled_stages(self) -> List[str]:
        flags = {
            STAGE_VOICE: self.do_voice,
            STAGE_IMAGE: self.do_image,
            STAGE_VIDEO: self.do_video,
        }
        return [s for s in PIPELINE if flags[s]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "speed": float(self.speed),
            "audio_format": self.audio_format,
            "aspect_ratio": self.aspect_ratio,
            "engine": self.engine,
            "images_per_scene": int(self.images_per_scene),
            "style": self.style,
            "do_voice": bool(self.do_voice),
            "do_image": bool(self.do_image),
            "do_video": bool(self.do_video),
            "target_chars": int(self.target_chars),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "ProjectOptions":
        if not isinstance(data, dict):
            return cls()
        options = cls()
        options.voice_id = str(data.get("voice_id") or options.voice_id)
        try:
            options.speed = float(data.get("speed", options.speed))
        except (TypeError, ValueError):
            pass
        options.audio_format = str(data.get("audio_format") or options.audio_format)
        options.aspect_ratio = str(data.get("aspect_ratio") or options.aspect_ratio)
        options.engine = str(data.get("engine") or options.engine)
        options.images_per_scene = max(1, min(8, _as_int(data.get("images_per_scene"), 1)))
        options.style = str(data.get("style") or "")
        options.do_voice = bool(data.get("do_voice", True))
        options.do_image = bool(data.get("do_image", True))
        options.do_video = bool(data.get("do_video", True))
        options.target_chars = max(0, _as_int(data.get("target_chars")))
        return options


@dataclass
class Project:
    """Cả một dự án: kịch bản, cài đặt, danh sách cảnh, và thư mục kết quả."""

    name: str
    folder: str
    script: str = ""
    options: ProjectOptions = field(default_factory=ProjectOptions)
    scenes: List[Scene] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    #: Ghi lại đúng câu đã hiện lúc khách bấm “Đồng ý chạy”. Có tranh cãi về tiền
    #: thì đây là bằng chứng khách đã thấy con số nào.
    approved_estimate: str = ""

    # ── Dựng mới ─────────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        *,
        name: str,
        root: str,
        script: str,
        options: Optional[ProjectOptions] = None,
    ) -> "Project":
        """Dựng dự án mới: chia cảnh, chọn thư mục chưa bị chiếm, chưa ghi gì cả."""
        options = options or ProjectOptions()
        folder = _free_folder(root, slugify(name))
        project = cls(name=name.strip() or "Dự án không tên", folder=folder, script=script,
                      options=options)
        project.resplit()
        return project

    def resplit(self) -> None:
        """Chia lại cảnh từ kịch bản hiện tại, giữ mô tả hình khách đã sửa tay.

        **Chỉ dùng khi chưa chạy gì.** Đổi số cảnh sau khi đã tốn tiền thì file cũ
        không còn khớp số thứ tự nữa — :meth:`can_resplit` là hàng rào cho việc đó.
        """
        drafts = make_scenes(
            self.script,
            target_chars=self.options.effective_target_chars(),
            style=self.options.style,
            overrides=[
                {
                    "narration": s.narration,
                    "image_prompt": s.image_prompt,
                    "video_prompt": s.video_prompt,
                }
                for s in self.scenes
            ],
        )
        self.scenes = [_scene_from_draft(d) for d in drafts]
        self.apply_stage_switches()

    def can_resplit(self) -> bool:
        """Chưa cảnh nào tốn tiền thì mới cho chia lại."""
        return not any(
            state.job_id or state.files
            for scene in self.scenes
            for state in scene.stages.values()
        )

    def apply_stage_switches(self) -> None:
        """Bật/tắt bước theo cài đặt hiện tại, **không đụng vào bước đã xong**.

        Tắt một bước đã có file là xoá mất dấu vết của tiền đã tiêu, nên bước đã
        xong luôn được giữ nguyên dù khách vừa gạt tắt nó.
        """
        enabled = set(self.options.enabled_stages())
        for scene in self.scenes:
            for name in PIPELINE:
                state = scene.stages[name]
                if state.is_done or state.job_id:
                    continue
                if name in enabled and state.status == ST_OFF:
                    state.status = ST_WAITING
                    state.message = ""
                elif name not in enabled and state.status != ST_OFF:
                    state.status = ST_OFF
                    state.message = "Bước này đang tắt cho cả dự án."

    # ── Đường dẫn file kết quả ───────────────────────────────────────────────

    def stage_dir(self, stage: str) -> str:
        return os.path.join(self.folder, STAGE_FOLDER[stage])

    def output_path(self, scene: Scene, stage: str, *, extension: str, order: int = 1) -> str:
        """Đường dẫn file kết quả của một cảnh — **đánh số 3 chữ số, có đệm 0**.

        `canh-007.mp4` sắp trước `canh-010.mp4` trong mọi trình quản lý file và
        mọi phần mềm dựng. Đánh số không đệm (`7.mp4`, `10.mp4`) thì máy sắp thành
        1, 10, 11, 2… và khách kéo cả thư mục vào timeline là lộn tung thứ tự.
        """
        suffix = "" if order <= 1 else "-{0}".format(order)
        name = "canh-{0:03d}{1}.{2}".format(scene.index, suffix, extension.lstrip("."))
        return os.path.join(self.stage_dir(stage), name)

    # ── Tổng kết ─────────────────────────────────────────────────────────────

    def counts(self) -> Dict[str, int]:
        """Đếm cảnh theo trạng thái, cho mấy ô thống kê ở đầu tab."""
        result = {ST_DONE: 0, ST_FAILED: 0, ST_RUNNING: 0, ST_WAITING: 0,
                  ST_INTERRUPTED: 0, ST_SKIPPED: 0}
        for scene in self.scenes:
            word = scene.status_word()
            result[word] = result.get(word, 0) + 1
        return result

    def spent_micro(self) -> int:
        return sum(scene.spent_micro() for scene in self.scenes)

    def scenes_needing_work(self) -> List[Scene]:
        """Những cảnh còn việc phải làm, đúng thứ tự."""
        return [s for s in self.scenes if not s.is_done]

    def pending_job_count(self) -> int:
        """Tổng số lượt gọi API còn phải chạy — chính là độ dài hàng chờ."""
        return sum(len(s.pending_stages()) for s in self.scenes)

    def failed_scene_numbers(self) -> List[int]:
        return [s.index for s in self.scenes if s.is_failed]

    def sync_with_disk(self) -> bool:
        changed = False
        for scene in self.scenes:
            changed = scene.sync_with_disk() or changed
        return changed

    # ── Đọc / ghi ────────────────────────────────────────────────────────────

    @property
    def path(self) -> str:
        return os.path.join(self.folder, PROJECT_FILENAME)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "name": self.name,
            "script": self.script,
            "options": self.options.to_dict(),
            "scenes": [s.to_dict() for s in self.scenes],
            "created_at": float(self.created_at),
            "updated_at": float(self.updated_at),
            "approved_estimate": self.approved_estimate,
        }

    @classmethod
    def from_dict(cls, data: Any, *, folder: str) -> "Project":
        data = data if isinstance(data, dict) else {}
        project = cls(
            name=str(data.get("name") or os.path.basename(folder)),
            folder=folder,
            script=str(data.get("script") or ""),
            options=ProjectOptions.from_dict(data.get("options")),
            scenes=[Scene.from_dict(s) for s in (data.get("scenes") or [])],
            approved_estimate=str(data.get("approved_estimate") or ""),
        )
        try:
            project.created_at = float(data.get("created_at") or time.time())
            project.updated_at = float(data.get("updated_at") or time.time())
        except (TypeError, ValueError):
            pass
        return project

    def save(self) -> None:
        """Ghi `du-an.json` (và bản sao kịch bản) — ghi tạm rồi đổi tên.

        Gọi sau **mỗi** thay đổi trạng thái. Mất điện giữa chừng thì file cũ vẫn
        nguyên vẹn, và tệ nhất là mất đúng một bước — không mất cả dự án.
        """
        os.makedirs(self.folder, exist_ok=True)
        self.updated_at = time.time()
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp, self.path)
        try:
            script_path = os.path.join(self.folder, SCRIPT_FILENAME)
            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write(self.script)
        except OSError:
            pass  # bản sao kịch bản chỉ để khách xem lại, hỏng cũng không sao

    @classmethod
    def load(cls, folder: str) -> Optional["Project"]:
        """Đọc một dự án từ thư mục. File hỏng/thiếu → `None` chứ không ném lỗi."""
        path = os.path.join(folder, PROJECT_FILENAME)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return None
        project = cls.from_dict(data, folder=folder)
        if project.sync_with_disk():
            # Sổ vừa lệch với ổ cứng và đã được chỉnh lại — ghi xuống ngay. Không
            # ghi thì lần mở sau lại lệch y như cũ, và một bước đã có file vẫn có
            # nguy cơ bị mua lại.
            try:
                project.save()
            except OSError:
                pass  # thư mục chỉ đọc: vẫn dùng được, chỉ là lần sau phải chỉnh lại
        return project

    def write_concat_list(self) -> Optional[str]:
        """Ghi danh sách ghép cho ffmpeg, để khách nối cả tập bằng một lệnh.

        Đây là mảnh ghép cuối của lời hứa “ghép lại được ngay”: có file này thì

            ffmpeg -f concat -safe 0 -i ghep-video.txt -c copy tap-phim.mp4

        là ra nguyên tập, không phải kéo tay 50 clip vào timeline.

        Trả về đường dẫn file, hoặc `None` khi chưa có clip nào xong.
        """
        clips: List[str] = []
        for scene in sorted(self.scenes, key=lambda s: s.index):
            state = scene.stages[STAGE_VIDEO]
            for path in state.files:
                if os.path.isfile(path):
                    clips.append(path)
        if not clips:
            return None
        target = os.path.join(self.folder, CONCAT_FILENAME)
        lines = [
            "# Danh sách ghép cho ffmpeg — sinh tự động, sửa tay thoải mái.",
            "# Ghép cả tập:  ffmpeg -f concat -safe 0 -i {0} -c copy tap-phim.mp4".format(
                CONCAT_FILENAME
            ),
        ]
        for path in clips:
            # ffmpeg đọc dấu `\` là ký tự thoát, nên đường dẫn Windows phải đổi
            # sang `/`; dấu nháy đơn trong tên file phải nhân đôi.
            safe = os.path.relpath(path, self.folder).replace("\\", "/").replace("'", "'\\''")
            lines.append("file '{0}'".format(safe))
        try:
            with open(target, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")
        except OSError:
            return None
        return target


# ── Tiện ích ──────────────────────────────────────────────────────────────────


def _scene_from_draft(draft: SceneDraft) -> Scene:
    return Scene(
        index=draft.index,
        narration=draft.narration,
        image_prompt=draft.image_prompt,
        video_prompt=draft.video_prompt,
    )


def _free_folder(root: str, slug: str) -> str:
    """Đường dẫn thư mục dự án chắc chắn chưa bị chiếm.

    Trùng tên là chuyện thường (“Tập 1” làm lại lần hai) và **đè lên dự án cũ là
    mất kết quả đã trả tiền**, nên luôn thêm hậu tố thay vì dùng lại.
    """
    candidate = os.path.join(root, slug)
    counter = 2
    while os.path.exists(candidate):
        candidate = os.path.join(root, "{0}-{1}".format(slug, counter))
        counter += 1
    return candidate


def list_projects(root: str) -> List[Dict[str, Any]]:
    """Liệt kê dự án đang có trong `root`, mới nhất lên đầu.

    Chỉ đọc phần đầu của mỗi `du-an.json` — thư mục có 200 dự án cũng mở tab
    trong nháy mắt, không phải nạp hết cảnh của tất cả.
    """
    found: List[Dict[str, Any]] = []
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return found
    for entry in entries:
        folder = os.path.join(root, entry)
        marker = os.path.join(folder, PROJECT_FILENAME)
        if not os.path.isfile(marker):
            continue
        try:
            with open(marker, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        scenes = data.get("scenes") or []
        found.append(
            {
                "folder": folder,
                "name": str(data.get("name") or entry),
                "scenes": len(scenes) if isinstance(scenes, list) else 0,
                "updated_at": _as_float(data.get("updated_at")),
            }
        )
    found.sort(key=lambda item: item["updated_at"], reverse=True)
    return found


def _as_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return fallback


def _as_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback
