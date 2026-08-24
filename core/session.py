"""Nhớ những việc đang chạy dở, để đóng tool giữa chừng không mất tiền oan.

**Vì sao cần cái này.** Khách chạy 40 clip, tới clip thứ 12 thì lỡ tay đóng cửa
sổ, hoặc máy sập nguồn. Tiền cho 12 clip đó đã trừ rồi và máy chủ vẫn làm xong,
nhưng nếu tool không nhớ mã việc thì mở lại là mất trắng kết quả — khách phải trả
tiền lần hai cho đúng nội dung đã mua.

Nên mỗi khi một việc được máy chủ nhận (có `job_id`), tool ghi ngay mã đó xuống
file `viec-dang-lam.json` cạnh `config.json`. Mở lại tool là đọc file này lên và
hỏi khách có muốn lấy kết quả về không. Link kết quả sống 7 ngày nên gần như lúc
nào cũng kịp.

File này **không chứa khoá API**, chỉ có mã việc và mô tả — mở ra xem bằng Notepad
cũng không lộ gì.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

__all__ = ["SESSION_FILENAME", "records_to_data", "data_to_specs", "save_session", "load_session"]

#: Đặt cạnh `config.json`.
SESSION_FILENAME = "viec-dang-lam.json"

#: Chỉ nhớ ngần này việc gần nhất — file không phình vô hạn sau vài tháng dùng.
#:
#: Trần cũ là 500, đặt từ thời một lô lớn nhất là 40 clip. Chạy MAX thì một lô
#: **2000 việc** (1000 ảnh + 1000 clip) là chuyện thường, và trần 500 nghĩa là
#: 1500 việc đầu bị **quên lặng lẽ** — đúng những việc đã trả tiền mà chưa lấy
#: được file về, tức đúng thứ tệp này tồn tại để cứu.
_MAX_REMEMBERED = 4000

#: Cắt mô tả còn ngần này ký tự khi ghi xuống.
#:
#: ═══ VÌ SAO CẮT ═══
#:
#: Prompt thật của khách dài 2–3 nghìn ký tự. Nhân 4000 việc là ~20 MB kết xuất
#: lại **mỗi lượt ghi**, mà lượt ghi thì mỗi giây một lần trong suốt mẻ chạy.
#:
#: Cắt được vì phần đọc lại (`data_to_specs` → `JobManager.restore`) **không bao
#: giờ gửi việc lên máy chủ lần nữa** — việc đã tạo và đã trả tiền từ lần chạy
#: trước; nó chỉ cần `job_id` để đi lấy kết quả về. `idempotency_key` và `label`
#: đều được ghi riêng, nên tên tệp tải về và chống-trùng-tiền không phụ thuộc
#: vào đoạn mô tả này.
_MAX_CONTENT = 300


def records_to_data(records: List[Any]) -> List[Dict[str, Any]]:
    """Rút gọn `JobRecord` thành dữ liệu ghi được ra JSON.

    Chỉ giữ những việc **đã gửi đi mà chưa lấy được file về** — đó đúng là phần
    có nguy cơ mất tiền. Việc đã tải xong rồi thì file nằm trên ổ cứng, không cần nhớ.
    """
    kept: List[Dict[str, Any]] = []
    for record in records:
        job_id = getattr(record, "job_id", None)
        if not job_id or getattr(record, "files", None):
            continue
        spec = record.spec
        kept.append(
            {
                "job_id": job_id,
                "kind": spec.kind,
                "content": spec.content[:_MAX_CONTENT],
                "params": dict(spec.params),
                "out_dir": spec.out_dir,
                "estimate_micro": int(spec.estimate_micro or 0),
                "index": int(spec.index),
                "label": spec.label,
                "idempotency_key": spec.idempotency_key,
                "status": getattr(record, "status", ""),
            }
        )
    return kept[-_MAX_REMEMBERED:]


def data_to_specs(data: Any) -> List[Dict[str, Any]]:
    """Đọc lại danh sách đã ghi, bỏ qua mục hỏng thay vì làm sập tool."""
    if not isinstance(data, list):
        return []
    result: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if not item.get("job_id") or not item.get("kind"):
            continue
        result.append(item)
    return result


def save_session(path: str, records: List[Any]) -> None:
    """Ghi danh sách việc đang dở. Ghi hỏng thì im lặng bỏ qua.

    Đây là tính năng phụ trợ: không ghi được (ổ đầy, thư mục chỉ đọc) thì tool
    vẫn phải chạy bình thường, không được ném lỗi lên mặt khách.
    """
    data = records_to_data(records)
    try:
        if not data:
            # Không còn gì dở dang → xoá file cho sạch, lần mở sau khỏi hỏi thừa.
            if os.path.exists(path):
                os.remove(path)
            return
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_path, path)
    except OSError:
        pass


def load_session(path: str) -> List[Dict[str, Any]]:
    """Đọc danh sách việc dở của lần chạy trước. Không có file → danh sách rỗng."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return []
    return data_to_specs(data)
