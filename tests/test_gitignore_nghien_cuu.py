"""`nghien-cuu/` chỉ được để LỌT đúng một tệp: `tuyen.csv`.

Thư mục ấy chở hai thứ khác hẳn nhau:

* `content.csv`, `doi-thu.txt` — **sổ đối thủ**: link, view, ngày đăng của
  từng video đối thủ. Dữ liệu kinh doanh, kho này công khai nên không được lên.
* `tuyen.csv` — **bản đồ tệp khán giả**: các kiểu người xem của ngành, kèm
  insight và cửa vào. Khuôn sản xuất, cùng họ với `prompt/`. Thiếu nó thì tính
  năng tuyến của tab Nghiên cứu vô dụng với mọi khách nhân bản kênh mẫu.

Bài này canh cả hai chiều vì luật ấy **mong manh theo đúng nghĩa kỹ thuật**:
git không cho re-include một tệp khi THƯ MỤC CHA đã bị loại. Viết
`CHANNEL/*/nghien-cuu/` (có gạch chéo cuối) rồi `!.../tuyen.csv` thì dòng phủ
định im lặng không ăn — không lỗi, không cảnh báo, chỉ là bản đồ không bao giờ
tới được máy khách. Phải viết `nghien-cuu/*` mới đúng.

Ngược lại, sửa hớ tay thành `nghien-cuu/` trần là **sổ đối thủ lên kho công
khai** — hỏng nặng hơn nhiều, và cũng không có tiếng động nào.
"""

from __future__ import annotations

import os
import subprocess

import pytest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bi_bo_qua(duong: str) -> bool:
    """`git check-ignore` nói tệp này có bị `.gitignore` bỏ qua không."""
    ket = subprocess.run(["git", "check-ignore", "-q", duong],
                         cwd=GOC, capture_output=True)
    if ket.returncode not in (0, 1):
        pytest.skip("không chạy được git check-ignore ở đây")
    return ket.returncode == 0


@pytest.mark.parametrize("ten", [
    "content.csv",          # sổ đối thủ — link/view/ngày đăng của đối thủ
    "doi-thu.txt",          # danh sách kênh đối thủ
    "BAN-DO-TEP-KHAN-GIA.md",   # phân tích thị trường của chủ dự án
    "anh/abc.jpg",          # ảnh thumbnail tải về
])
def test_du_lieu_kinh_doanh_KHONG_len_kho(ten):
    assert _bi_bo_qua("CHANNEL/TL4-T7/nghien-cuu/" + ten), (
        "{0} là dữ liệu kinh doanh của khách — kho này công khai".format(ten))


def test_ban_do_tuyen_CO_len_kho():
    assert not _bi_bo_qua("CHANNEL/TL4-T7/nghien-cuu/tuyen.csv"), (
        "tuyen.csv phải theo bản cập nhật tới khách; nếu bài này đỏ thì rất có "
        "thể ai đó đã đổi `nghien-cuu/*` về `nghien-cuu/` — git sẽ im lặng bỏ "
        "qua dòng phủ định bên dưới")


def test_kenh_mau_khac_cung_theo_luat_ay():
    # Luật viết theo `CHANNEL/*/`, không đóng đinh vào TL4-T7.
    assert _bi_bo_qua("CHANNEL/timelapse/nghien-cuu/content.csv")
    assert not _bi_bo_qua("CHANNEL/timelapse/nghien-cuu/tuyen.csv")
