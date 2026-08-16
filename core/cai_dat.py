"""Những nút gạt của tool — một chỗ duy nhất, một tệp duy nhất.

═══ VÌ SAO TÁCH KHỎI `config.json` ═══

`config.json` và `secrets.json` giữ **khoá API và tài khoản** của khách. Trộn
mấy nút gạt giao diện vào đó nghĩa là mỗi lần khách bật/tắt một tuỳ chọn là một
lần ghi đè lên tệp có khoá — và một lần ghi hỏng ở đó thì khách mất đường vào
tài khoản, không phải mất một tuỳ chọn.

Nên tuỳ chọn nằm riêng ở `workspace/cai-dat.json`. Mất tệp này thì tool quay về
mặc định và chạy tiếp bình thường; đó là toàn bộ thiệt hại.

═══ MẶC ĐỊNH LÀ THỨ 90% KHÁCH KHÔNG BAO GIỜ ĐỔI ═══

Người dùng tool này không biết lập trình. Mỗi tuỳ chọn để họ tự quyết là một
câu hỏi họ không có cơ sở để trả lời, nên mặc định phải là **thứ đúng cho phần
đông**, còn nút gạt chỉ dành cho người có lý do riêng.

`tu_cap_nhat` bật sẵn chính vì thế: cả một ngày sửa lỗi chỉ tới được máy khách
khi họ bấm Cập nhật, mà phần lớn không bấm — họ không biết là có bản mới, và
cũng không có lý do gì để đi tìm.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict

__all__ = ["doc", "ghi", "dat", "MAC_DINH", "duong_tep"]

TEN_TEP = "cai-dat.json"

#: Mọi tuỳ chọn và giá trị mặc định của nó.
MAC_DINH: Dict[str, Any] = {
    # Mở tool lên là tự tải bản mới rồi khởi động lại, không hỏi.
    #
    # Bật sẵn vì bản vá chỉ có giá trị khi tới được máy khách. Cả một ngày sửa
    # lỗi mà khách không bấm Cập nhật thì bằng không — và họ không bấm, vì họ
    # không biết là có bản mới.
    #
    # Tắt được, dành cho người đang chạy dở một mẻ dài và không muốn tool tự
    # khởi động lại giữa chừng.
    "tu_cap_nhat": True,

    # Hỏi GitHub xem có bản mới không, mỗi lần mở tool.
    #
    # Tắt cái này là tắt luôn cả `tu_cap_nhat` — không hỏi thì không biết có gì
    # để cập nhật. Dành cho máy không nối mạng ra ngoài.
    "hoi_ban_moi": True,

    # Hiện hộp thoại khi tool gặp lỗi trong lúc chạy.
    #
    # Tắt thì lỗi vẫn được ghi vào `workspace/su-co.log`, chỉ là không hiện lên
    # màn hình. Dành cho người để tool chạy qua đêm.
    "bao_su_co": True,

    # Xoá dấu nguồn gốc AI trong phần thông tin của tệp trước khi giao.
    # Phủ cả bốn loại kết quả: chữ, giọng đọc, ảnh, video.
    #
    # ═══ VÌ SAO TẮT SẴN ═══
    #
    # Chủ dự án chốt 16/08/2026: *"mặc định sẽ là tắt nhé"*. Và đó là mặc định
    # đúng, vì hai lẽ:
    #
    # Một, C2PA là **chuẩn minh bạch nguồn gốc**, không phải thứ nhà cung cấp
    # cài để làm khó ai. Bỏ nó đi là một lựa chọn, và lựa chọn thì nên do người
    # dùng bấm chứ không nên là thứ tool tự làm sau lưng họ.
    #
    # Hai, nó **làm được ít hơn cái tên nghe thấy**, nên bật sẵn là để khách
    # tin vào một thứ bảo hộ không có thật. Đo 16/08/2026 trên kết quả thật:
    # video cuối và giọng đọc vốn đã sạch (khâu dựng mã hoá lại nên thẻ mất
    # hết), chữ cũng sạch. Chỗ hở thật **chỉ có ảnh bìa** — nó cũng lên YouTube
    # mà lại gần như nguyên vẹn từ nhà cung cấp.
    #
    # Và nó **không** xoá được SynthID: dấu ấy nằm trong chính điểm ảnh, không
    # nằm trong thẻ. Xoá thẻ chỉ bỏ đi lời khai rằng có SynthID.
    #
    # Xem `core/lam_sach.py` để biết vì sao nó không gỡ được hạn chế của
    # YouTube, và vì sao tin nhầm chỗ đó thì mất kênh chứ không mất công.
    "lam_sach_dau_ai": False,

    # Chèn thẻ cảm xúc ElevenLabs v3 vào kịch bản trước khi đem đi đọc.
    #
    # ═══ TẮT SẴN ═══
    #
    # Chủ dự án chốt lại 16/08/2026: *"sẽ cài ở setting để mặc định là tắt"*.
    # Đúng: tài liệu ElevenLabs KHÔNG nói gì về thẻ cảm xúc với tiếng không
    # phải tiếng Anh, mà kênh đang chạy viết tiếng Nhật. Bật sẵn một thứ chưa
    # ai kiểm được trên đúng thứ tiếng khách dùng là bắt họ làm chuột bạch mà
    # không hỏi.
    #
    # Tốn thêm **một lượt gọi AI viết chữ** cho mỗi lượt chạy — cùng loại với
    # bước nắn độ dài, không phải loại đắt như ảnh hay clip.
    #
    # Ba lớp chặn cho một luật "AI không được đổi chữ": nói trong lời nhắc, lọc
    # thẻ lạ, rồi gỡ hết thẻ ra so lại với bản gốc. Sai một chữ là vứt, đọc bản
    # sạch. Xem `core/the_cam_xuc.py`.
    "the_cam_xuc": False,

    # Đổi nhẹ cao độ giọng đọc (60 cent, hơn nửa nốt nhạc).
    #
    # Công tắc RIÊNG, không gộp với `lam_sach_dau_ai`, vì nó khác hẳn về mức
    # độ: cái kia chỉ bỏ thẻ ở vỏ tệp, cái này đụng vào **chính âm thanh** và
    # phải mã hoá lại tệp giọng đọc. Hai mức rủi ro khác nhau thì phải hai nút.
    #
    # Tắt sẵn, cùng lý do: đây là thứ đổi sản phẩm của khách, phải do họ bấm.
    #
    # Xem `core/lam_sach.py` mục "Đổi nhẹ cao độ giọng đọc" — trong đó có cả
    # phần nói rõ tool KHÔNG tự kiểm chứng được là dấu đã mất hay chưa.
    "doi_cao_do_giong": False,

    # Độ phân giải video ra của tab Tự động: "4K", "1440p", "1080p" hay
    # "Giữ nguyên". Kênh nào khai riêng trong `kenh.yaml` thì lấy theo kênh.
    #
    # ═══ VÌ SAO MẶC ĐỊNH LÀ 4K ═══
    #
    # Đo 16/08/2026 trên bảy lượt chạy thật: mọi clip nhà cung cấp trả về đều
    # **1280×720**, và đường dựng cũ không có bước đổi độ phân giải nào — nên
    # video giao cho khách chưa tới cả 1080p mà không ai biết. Đó là mặc định
    # tệ nhất trong bốn lựa chọn, và nó tệ một cách âm thầm.
    #
    # 4K không tạo thêm chi tiết có thật — phần nét thêm ra là máy đoán. Cái
    # được thật: YouTube cấp bộ mã hoá tốt hơn cho video tải lên ở 2160p, nên
    # người xem ở 1080p vẫn thấy sạch hơn.
    #
    # Cái mất: khâu dựng lâu hơn khoảng bốn lần (đo trên clip thật: 8 giây
    # video mất 3 giây ở 720p, 12 giây ở 4K) và tệp to hơn khoảng năm lần. Cả
    # hai đều là thời gian máy khách, **không tốn thêm đồng API nào** — nên
    # đánh đổi này nghiêng hẳn về phía nên bật.
    "do_phan_giai": "4K",
}

_KHOA = threading.Lock()


def duong_tep(goc: str) -> str:
    return os.path.join(goc, "workspace", TEN_TEP)


def doc(goc: str) -> Dict[str, Any]:
    """Đọc cài đặt. Thiếu tệp hoặc tệp hỏng đều trả về mặc định.

    **Không bao giờ ném lỗi.** Đây là thứ được hỏi lúc tool đang khởi động; một
    tệp JSON gõ hỏng không được phép chặn tool mở lên.
    """
    ra = dict(MAC_DINH)
    try:
        with open(duong_tep(goc), "r", encoding="utf-8") as tep:
            tren_dia = json.load(tep)
    except (OSError, ValueError):
        return ra
    if isinstance(tren_dia, dict):
        # Chỉ nhận những khoá tool biết, và chỉ khi đúng kiểu. Tệp do người sửa
        # tay có thể có khoá lạ hoặc giá trị lạ; lấy bừa là lỗi nổ ở chỗ khác,
        # xa chỗ gõ sai, và không ai lần ra.
        for ten, mac_dinh in MAC_DINH.items():
            gia_tri = tren_dia.get(ten, mac_dinh)
            if isinstance(gia_tri, type(mac_dinh)):
                ra[ten] = gia_tri
    return ra


def ghi(goc: str, cai: Dict[str, Any]) -> bool:
    """Ghi cài đặt xuống đĩa. Trả về ghi được hay không.

    Ghi qua tệp tạm rồi đổi tên: máy tắt giữa chừng thì còn bản cũ nguyên vẹn,
    chứ không phải một tệp JSON cụt làm lần mở sau đọc không ra.
    """
    duong = duong_tep(goc)
    goi = {ten: cai.get(ten, mac) for ten, mac in MAC_DINH.items()}
    with _KHOA:
        try:
            os.makedirs(os.path.dirname(duong), exist_ok=True)
            tam = duong + ".tam"
            with open(tam, "w", encoding="utf-8") as tep:
                json.dump(goi, tep, ensure_ascii=False, indent=2)
            os.replace(tam, duong)
            return True
        except OSError:
            return False


def dat(goc: str, ten: str, gia_tri: Any) -> bool:
    """Đổi đúng một tuỳ chọn."""
    if ten not in MAC_DINH:
        return False
    cai = doc(goc)
    cai[ten] = gia_tri
    return ghi(goc, cai)