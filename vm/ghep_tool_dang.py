"""Ghép tool đăng (`dang.py` của D:\\upload) vào nguồn kế hoạch của tool.

═══ VÌ SAO GHÉP TẠI CHỖ, KHÔNG CHÉP `dang.py` VÀO KHO ═══

Kho này công khai trên GitHub. `dang.py` là đồ riêng của chủ dự án (máy đăng
YouTube bằng nhận diện ảnh) — chép nó vào kho là phát hành nó cho cả thế
giới. Nên chiều ngược lại: tệp này chạy Ở CHỖ có `dang.py` (trên máy ảo, cạnh
bản chép của D:\\upload), đọc nó, vá đúng BA điểm chạm trang tính, ghi ra
`dang-tool.py` — bản gốc không bị đụng một chữ.

Ba điểm chạm (đọc mã `dang.py` ngày 01/09/2026):

    get_rows_fast(...)        → đọc kế hoạch từ trạm (vm/nguon_tool.py)
    update_source_status(...) → báo "ĐÃ ĐĂNG" về trạm theo MÃ gói
    client = gs_client()      → khỏi cần Google khi nguồn là tool

Cách dùng trên máy ảo:

    1. Chép `nguon_tool.py` + `ghep_tool_dang.py` (thư mục vm/ của tool) vào
       cạnh `dang.py`.
    2. Thêm vào `config.json` của tool đăng:  "NGUON": "tool",
       "TRAM": "http://<địa chỉ trạm>:8765"   (CHANNEL_CODE đã có sẵn).
    3. Chạy:  python ghep_tool_dang.py   → ra `dang-tool.py`.
    4. Từ đó chạy `python dang-tool.py` thay cho `dang.py`. Muốn về trang
       tính thì đổi "NGUON" thành "sheets" — không phải ghép lại.

Chạy lại sau khi `dang.py` có bản mới cũng chỉ là bước 3 — neo vá là chuỗi
mã cụ thể, lệch neo là DỪNG VÀ NÓI, không vá bừa.
"""

from __future__ import annotations

import os
import sys

GOC = os.path.dirname(os.path.abspath(__file__))

#: (chuỗi neo, chuỗi thay, số lần bắt buộc gặp). Neo lệch — `dang.py` đã đổi —
#: thì assert nổ với lời chỉ chỗ, còn hơn ghi ra một bản vá sai chạy ngầm.
_VA = (
    # 1. Khai nguồn ngay sau khi đọc config.
    ('STATUS_COL        = CFG.get("STATUS_COL", 48)',
     'STATUS_COL        = CFG.get("STATUS_COL", 48)\n'
     'NGUON             = CFG.get("NGUON", "sheets")   # "tool" = ke hoach tu tool\n'
     'if NGUON == "tool":\n'
     '    import nguon_tool  # nam canh tep nay - chep tu vm/ cua tool chinh\n',
     1),
    # 2. Đọc dòng: nguồn tool thì khỏi gọi Google.
    ('def get_rows_fast(sheet_name, timeout=20, tries=4):',
     'def get_rows_fast(sheet_name, timeout=20, tries=4):\n'
     '    if NGUON == "tool":\n'
     '        return nguon_tool.get_rows(CFG, trang_thai_ok=STATUS_OK)\n',
     1),
    # 3. Ghi trạng thái: báo về trạm theo mã gói.
    ('def update_source_status(client, code, status="ĐÃ ĐĂNG"):',
     'def update_source_status(client, code, status="ĐÃ ĐĂNG"):\n'
     '    if NGUON == "tool":\n'
     '        return nguon_tool.bao_dang(CFG, code, status)\n',
     1),
    # 4. Hai chỗ dựng client Google — nguồn tool thì để None (mọi chỗ dùng
    #    client đều đã bọc try, None chỉ làm nhánh ấy rơi về cache/bỏ qua).
    ('client = gs_client()',
     'client = gs_client() if NGUON != "tool" else None',
     2),
)


def ghep(duong_dang: str = "", duong_ra: str = "") -> str:
    duong_dang = duong_dang or os.path.join(GOC, "dang.py")
    duong_ra = duong_ra or os.path.join(os.path.dirname(duong_dang),
                                        "dang-tool.py")
    with open(duong_dang, "r", encoding="utf-8") as tep:
        ma = tep.read()
    for neo, thay, so_lan in _VA:
        gap = ma.count(neo)
        assert gap == so_lan, (
            "Neo vá lệch ở '{0}…': mong {1} chỗ, gặp {2}. dang.py đã đổi — "
            "cập nhật vm/ghep_tool_dang.py cho khớp rồi chạy lại, đừng vá bừa."
            .format(neo[:40], so_lan, gap))
        ma = ma.replace(neo, thay)
    dau = ('# TAO RA TU dang.py BOI vm/ghep_tool_dang.py - DUNG SUA TAY.\n'
           '# Muon sua thi sua dang.py roi chay lai ghep_tool_dang.py.\n')
    with open(duong_ra, "w", encoding="utf-8") as tep:
        tep.write(dau + ma)
    return duong_ra


if __name__ == "__main__":
    ra = ghep(*(sys.argv[1:3]))
    print("da ghi", ra)
    print('chay bang:  python "{0}"  (config.json can "NGUON": "tool" va "TRAM")'
          .format(os.path.basename(ra)))
