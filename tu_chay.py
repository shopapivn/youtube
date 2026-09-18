"""CLI: chạy chu kỳ ngày cho kênh "tự chạy" — không mở giao diện.

    python tu_chay.py --kenh TL4-T7           chạy THẬT một kênh (tốn ví)
    python tu_chay.py --kenh TL4-T7 --thu      chế độ THỬ: chọn nguồn, không tốn tiền
    python tu_chay.py --tat-ca                 mọi kênh có `tu_chay: true`, lần lượt
    python tu_chay.py --tat-ca --thu           như trên, chế độ thử

Dùng đúng `config.json` / kho bí mật của thư mục này — cùng ví ShopAPI mà tab
"Tự động" của giao diện đang dùng. Mai kia trạm chạy lệnh này qua lịch của VPS,
một lần một kênh một ngày; xem `core/tu_chay.py` cho luật đầy đủ (nghiên cứu →
chọn nguồn → van ngân sách → sản xuất → bàn giao).
"""

from __future__ import annotations

import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.api import build_client  # noqa: E402
from core.config import CONFIG_FILENAME, load_config  # noqa: E402
from core.tu_chay import bo_log_tat_ca, chay_nhieu_kenh, chay_tat_ca  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Chạy chu kỳ ngày cho kênh tự chạy.")
    nhom = ap.add_mutually_exclusive_group(required=True)
    nhom.add_argument("--kenh", help="Mã một kênh, ví dụ TL4-T7 (đúng tên thư mục trong CHANNEL/).")
    nhom.add_argument("--tat-ca", action="store_true",
                      help="Mọi kênh có `tu_chay: true` trong kenh.yaml, chạy LẦN LƯỢT.")
    ap.add_argument("--thu", action="store_true",
                    help="Chế độ thử: nghiên cứu + chọn nguồn, KHÔNG sản xuất, không tốn ví.")
    args = ap.parse_args(argv)

    config = load_config(os.path.join(BASE_DIR, CONFIG_FILENAME))
    if config.problem:
        print("Không đọc được cấu hình: " + config.problem)
        return 1
    client = build_client(config)
    che_do = "thu" if args.thu else "that"

    if args.tat_ca:
        # `pythonw.exe` (Task Scheduler gọi tới, xem `core/lich_tu_chay.py`)
        # không có console — mọi dòng in phải qua đường ghi-đĩa an toàn này,
        # KHÔNG được gọi `print()` trực tiếp ở nhánh này.
        log = bo_log_tat_ca(BASE_DIR)
        log("─" * 60)
        log("Bắt đầu `tu_chay.py --tat-ca` (chế độ {0}).".format(che_do))
        try:
            bao_cao = chay_tat_ca(BASE_DIR, client=client, che_do=che_do, on_log=log)
        except Exception as loi:  # noqa: BLE001 — không ai đọc traceback trên console pythonw, phải tự ghi
            log("LỖI NGOÀI DỰ KIẾN, dừng --tat-ca: {0}".format(loi))
            return 1
        log("")
        for dong in bao_cao["ket_qua"]:
            log(("[OK]  " if dong["ok"] else "[LỖI] ") + dong["tom_tat"])
        log("Xong `--tat-ca` — {0}.".format("CÓ lỗi" if bao_cao["co_loi"] else "không lỗi"))
        return 1 if bao_cao["co_loi"] else 0

    bao_cao = chay_nhieu_kenh(BASE_DIR, [args.kenh], client=client, che_do=che_do, on_log=print)
    print("")
    for dong in bao_cao["ket_qua"]:
        print(("[OK]  " if dong["ok"] else "[LỖI] ") + dong["tom_tat"])
    return 1 if bao_cao["co_loi"] else 0


if __name__ == "__main__":
    sys.exit(main())
