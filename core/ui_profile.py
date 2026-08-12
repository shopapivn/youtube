"""Ho so giao dien ca nhan: moi tab la mot tool con cua khach."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

PROFILE_VERSION = 4
#: Mọi khoá tab hai vỏ giao diện từng dùng.
#:
#: Nửa đầu là khoá của bản tkinter (`ui/app.py`), nửa sau là khoá **riêng của
#: bản Qt** (`ui_qt/app.py`). Hai vỏ đặt tên khác nhau cho cùng một việc — bản
#: tkinter gọi tab video là ``veo3``, bản Qt gọi là ``video`` — nên danh sách
#: phải chứa cả hai, nếu không `save_tab_label` từ chối đúng những tab đang hiện
#: trên bản Qt và Agent lại phải nói “không làm được”.
KNOWN_TABS = ("wallet", "agent", "research", "content", "voice", "srt_excel",
              "image", "veo3", "seedance", "project", "queue",
              "skill", "video", "edit")
#: Tab hiện sẵn khi khách mở tool lần đầu.
#:
#: Ảnh và video nằm trong này vì **API đã có sẵn hai dịch vụ đó** — giấu đi thì
#: khách trả tiền cho thứ họ không nhìn thấy, và phải hỏi Agent mới biết là có.
#: Seedance để Agent bật khi khách cần, vì nó cùng việc với Veo3 nhưng đắt gấp
#: đôi; bày cả hai cạnh nhau chỉ làm người mới phân vân.
DEFAULT_VISIBLE_TABS = ("agent", "research", "content", "voice",
                        "image", "veo3", "queue")


def normalize_visible_tabs(values: Iterable[str]) -> Tuple[str, ...]:
    requested = {str(value).strip() for value in values}
    requested.add("agent")
    return tuple(key for key in KNOWN_TABS if key in requested)


def load_visible_tabs(path: Path) -> Tuple[str, ...]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if int(data.get("version", 0)) < PROFILE_VERSION:
            return DEFAULT_VISIBLE_TABS
        values = data.get("visible_tabs", [])
        if not isinstance(values, list):
            raise ValueError("visible_tabs")
        return normalize_visible_tabs(values)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return DEFAULT_VISIBLE_TABS


def load_tab_labels(path: Path) -> Dict[str, str]:
    labels = _doc(path).get("tab_labels", {})
    if not isinstance(labels, dict):
        return {}
    return {str(key): str(value).strip()[:40] for key, value in labels.items()
            if key in KNOWN_TABS and isinstance(value, str) and value.strip()}


def load_hidden_tabs(path: Path) -> Tuple[str, ...]:
    """Tab khách bảo Agent giấu đi.

    Cố ý lưu tab **bị ẩn** thay vì tab được hiện, vì hai vỏ không cùng bộ khoá:
    một danh sách “được hiện” viết từ bản Qt sẽ giấu sạch tab của bản tkinter và
    ngược lại. Mặc định rỗng nên hồ sơ chưa có gì thì không tab nào biến mất —
    hỏng theo hướng bày ra hết vẫn đỡ hơn hỏng theo hướng giấu mất tool khách
    đang trả tiền.
    """
    values = _doc(path).get("hidden_tabs", [])
    if not isinstance(values, list):
        return ()
    xin = {str(value).strip() for value in values} - {"agent"}
    return tuple(key for key in KNOWN_TABS if key in xin)


def save_visible_tabs(path: Path, values: Iterable[str]) -> Tuple[str, ...]:
    visible = normalize_visible_tabs(values)
    _ghi(path, {"visible_tabs": list(visible)})
    return visible


def save_tab_label(path: Path, key: str, label: str) -> str:
    if key not in KNOWN_TABS:
        raise ValueError("Tab không tồn tại.")
    clean = " ".join(str(label).strip().split())
    if not 1 <= len(clean) <= 40:
        raise ValueError("Tên tab cần từ 1 đến 40 ký tự.")
    labels = load_tab_labels(path)
    labels[key] = clean
    _ghi(path, {"tab_labels": labels})
    return clean


def save_hidden_tab(path: Path, key: str, an: bool) -> Tuple[str, ...]:
    """Ẩn hoặc hiện lại một tab; trả về danh sách tab đang bị ẩn sau thay đổi."""
    if key not in KNOWN_TABS:
        raise ValueError("Tab không tồn tại.")
    if an and key == "agent":
        # Ẩn tab Agent là cắt mất đúng chỗ khách nói chuyện để bật nó trở lại.
        raise ValueError("Không ẩn được tab Agent — đó là chỗ bạn ra lệnh.")
    dang_an = set(load_hidden_tabs(path))
    dang_an.add(key) if an else dang_an.discard(key)
    con = tuple(item for item in KNOWN_TABS if item in dang_an)
    _ghi(path, {"hidden_tabs": list(con)})
    return con


# ── Đọc/ghi ──────────────────────────────────────────────────────────────────


def _doc(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def _ghi(path: Path, thay_doi: Dict[str, Any]) -> None:
    """Ghi đè đúng phần cần đổi, **giữ nguyên các phần khác của hồ sơ**.

    Trước đây mỗi hàm lưu tự dựng lại cả tệp; thêm một mục mới là lặng lẽ xoá
    mục của hàm kia. Đổi tên tab rồi ẩn tab là mất tên vừa đặt.
    """
    path = Path(path)
    du_lieu: Dict[str, Any] = {
        "version": PROFILE_VERSION,
        "visible_tabs": list(load_visible_tabs(path)),
        "tab_labels": load_tab_labels(path),
        "hidden_tabs": list(load_hidden_tabs(path)),
    }
    du_lieu.update(thay_doi)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)
