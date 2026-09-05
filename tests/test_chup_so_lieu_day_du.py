"""Bộ CHỤP phải lấy đủ, và phải để lại bằng chứng nhìn được.

Bốn lỗi ngày 05/09/2026 đều xảy ra trong lúc **mọi gói vẫn về đều đặn**: lấy nhầm thẻ, dán
nhãn thẻ này lên số thẻ kia, bỏ gói theo tên thư mục, chia hai cửa sổ khác nhau. Không có
một dấu hiệu nào báo động, vì thứ duy nhất được kiểm là "gói có về không".

Nên từ đây canh hai lớp:

* **đủ** — lịch chụp phải có mốc mà sổ tay kênh dùng để phán (13h), và phải lấy được bảng
  hiển thị theo từng bề mặt (Trang chủ · Tiếp theo · …), thứ trả lời câu hỏi của cổng 1;
* **nhìn được** — mỗi tab số liệu để lại một ảnh chụp màn hình, để khi nghi số sai thì còn
  cái đối chiếu với mắt người, và để bắt loại hỏng mà JSON không kể (đăng xuất, trang trắng).

Mấy bài này đọc thẳng `background.js` chứ không chạy Chrome. Đó là giới hạn thật và ghi rõ
ở đây: chúng canh phần DÂY NỐI (mốc, danh sách link, tên cửa, quyền trong manifest) — không
chứng minh Chrome chụp được ảnh. Việc ấy chỉ máy ảo trả lời được.
"""

import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import chi_so_ytb as cs  # noqa: E402
from core.chi_so_ytb.tram import Tram  # noqa: E402

GOC = cs.thu_muc_extension()


def _nen():
    return io.open(os.path.join(GOC, "background.js"), encoding="utf-8").read()


def test_lich_chup_co_moc_13h():
    """Sổ tay kênh phán một video sống/chết bằng số ở mốc 13h — mà lịch cũ không có mốc ấy.

    `MOC = [24, 48, 72, …]`: mọi con số 13h trong kho đều là ăn may (lượt "chụp ngay" lúc phát
    hiện video rơi trúng, hoặc chụp tay). Đo 05/09/2026: không video nào có mốc 13h do lịch đặt.
    """
    m = re.search(r"const MOC = \[([^\]]+)\]", _nen())
    assert m, "không tìm thấy danh sách mốc"
    moc = [int(x) for x in m.group(1).split(",")]
    assert 13 in moc, "thiếu mốc 13h — mốc sổ tay kênh dùng để phán sống/chết"
    assert 30 in moc, "thiếu mốc 30h — luật 30 giờ của sổ tay chấm ở đây"
    assert moc == sorted(moc), "mốc phải tăng dần"
    assert len([h for h in moc if h <= 48]) >= 6, \
        "hai ngày đầu quá thưa — đó là quãng mọi quyết định xảy ra"


def test_chup_du_bon_bang_gom_ca_nguon_theo_loai():
    """Thiếu bảng theo LOẠI bề mặt thì không trả lời được cổng 1 đói ở đâu.

    Trước 05/09 chỉ có hai thứ rời nhau: TỔNG hiển thị của video, và SỐ LƯỢT theo bề mặt.
    Không có hiển thị theo bề mặt ⇒ không so được CTR giữa "Trang chủ" và "Tiếp theo", trong
    khi hai video lớn nhất kênh có hình dạng ngược hẳn nhau (V3: 519/361 · V4: 11/824).
    """
    nen = _nen()
    m = re.search(r"const LINK_VIDEO = \(id\) => \[(.+?)\n\];", nen, re.S)
    assert m, "không tìm thấy danh sách link"
    than = m.group(1)
    assert "TRAFFIC_SOURCE_TYPE'" in than or 'TRAFFIC_SOURCE_TYPE"' in than, \
        "thiếu bảng nguồn theo LOẠI bề mặt"
    assert "TRAFFIC_SOURCE_DETAIL" in than, "thiếu bảng pool đề xuất"
    assert "COUNTRY" in than, "thiếu bảng vùng"
    assert "tab-overview" in than, "thiếu tab tổng quan"
    assert len([d for d in than.split("\n") if d.strip().startswith("[")]) >= 4


def test_moi_tab_so_lieu_deu_de_lai_mot_anh():
    """Chủ dự án 05/09: chụp ảnh các tab để khi hỏng thì còn biết."""
    nen = _nen()
    assert "captureVisibleTab" in nen, "không chụp ảnh màn hình"
    m = re.search(r"const LINK_VIDEO = \(id\) => \[(.+?)\n\];", nen, re.S)
    dong = [d for d in m.group(1).split("\n") if d.strip().startswith("[")]
    for d in dong:
        assert re.search(r",\s*'[a-z0-9-]+'\s*\]", d), f"link này không có tên ảnh: {d.strip()[:60]}"
    assert "chupAnh(tabId" in nen, "có hàm chụp nhưng không ai gọi"
    # Ảnh chụp TRƯỚC khi số về chỉ ra khung xám — phải gọi sau vòng chờ gói.
    i_mo, i_anh = nen.index("const r = await moLink(tabId"), nen.index("await chupAnh(tabId, maKenh, videoId")
    assert i_mo < i_anh, "chụp ảnh trước khi số liệu về thì ảnh rỗng"


def test_manifest_du_quyen_chup_anh():
    """`activeTab` KHÔNG đủ — bài này từng xanh trong khi tính năng hỏng hoàn toàn.

    Bản 2.5.0 khai `activeTab` và bài kiểm cũ nhận nó là đủ. Chạy thật: mọi bảng số về đủ,
    **không một tấm ảnh nào**. Vì `captureVisibleTab` kiểm quyền bằng
    `CaptureRequirement::kActiveTabOrAllUrls`, mà `activeTab` chỉ được cấp sau MỘT CÚ BẤM của
    người dùng — lượt chụp theo lịch không bao giờ có cú bấm ấy. Quyền theo từng miền
    (`https://studio.youtube.com/*`) cũng không được tính.

    Đây đúng loại bài kiểm tệ nhất: xanh, và cho cảm giác an toàn giả. Nay đòi đúng thứ chạy được.
    """
    d = json.load(io.open(os.path.join(GOC, "manifest.json"), encoding="utf-8"))
    assert "<all_urls>" in d.get("host_permissions", []), (
        "captureVisibleTab đòi <all_urls>; activeTab chỉ có sau cú bấm của người dùng nên "
        "lượt chụp theo lịch luôn ném lỗi quyền — và ném im lặng")
    assert "tabs" in d["permissions"] and "scripting" in d["permissions"]


def test_van_lay_duoc_CHU_khi_khong_chup_duoc_anh():
    """Ảnh là để người soi; CHỮ mới là thứ máy so được — và nó phải sống sót khi ảnh chết.

    Màn hình không vẽ (phiên RDP ngắt, cửa sổ thu nhỏ) thì ảnh hỏng hoặc ra khung đen. Nếu mất
    luôn chữ thì lượt quét ấy không để lại bằng chứng nào, đúng cảnh 05/09/2026.
    """
    nen = _nen()
    assert "async function docChu" in nen, "không đọc chữ trên trang"
    assert "shadowRoot" in nen.split("async function docChu")[1][:1200], \
        "Studio dựng bằng web component — không đi xuống shadowRoot là đọc trượt gần hết chữ"
    # Chữ phải đọc TRƯỚC khi thử chụp, để lỗi chụp không cuốn theo cả chữ.
    than = nen.split("async function chupAnh")[1][:900]
    assert than.index("docChu(tabId)") < than.index("captureVisibleTab"), \
        "đọc chữ sau khi chụp thì ảnh hỏng là mất luôn chữ"
    assert "loi" in than and "log(`ảnh hỏng" in than, "nuốt lỗi chụp là lần sau vẫn mù"


def test_hai_bang_nguon_khong_ghi_de_len_nhau(tmp_path):
    """Hai bảng nguồn có dòng tiêu đề chỉ khác nhau ở cột thứ hai — nhận nhầm là mất cả hai."""
    import base64
    import zipfile

    tram = Tram(goc=str(tmp_path))
    snap = tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "video123abc" / "24h"
    (snap / "raw").mkdir(parents=True)

    def goi_zip(head, ten_trong_zip):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(ten_trong_zip, head + "\nTotal,1,2\n")
        return base64.urlsafe_b64encode(buf.getvalue()).decode().rstrip("=")

    for head, ten_zip in [("Traffic source,Source type,Source title,Thumbnail impressions", "a.csv"),
                          ("Traffic source,Impressions,Impressions click-through rate (%)", "b.csv")]:
        tram._bung_zip({"response": {"zippedData": goi_zip(head, ten_zip)}}, str(snap))

    assert (snap / "traffic-related.csv").exists(), "mất bảng pool đề xuất"
    assert (snap / "traffic-type.csv").exists(), "mất bảng nguồn theo loại bề mặt"
    assert "Source type" in (snap / "traffic-related.csv").read_text(encoding="utf-8")
    assert "Impressions" in (snap / "traffic-type.csv").read_text(encoding="utf-8")


def _anh_jpeg():
    """Một tệp JPEG bé xíu nhưng đúng dấu nhận dạng."""
    return b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 40 + b"\xff\xd9"


def test_tram_ghi_anh_va_tu_choi_thu_khong_phai_anh(tmp_path):
    import base64

    tram = Tram(goc=str(tmp_path))
    (tmp_path / "CHANNEL" / "TL4-T7" / "chi-so").mkdir(parents=True)
    b = {"kenh": "TL4-T7", "id": "video123abc", "label": "24h", "ten": "x_tong-quan.jpg",
         "anh": base64.b64encode(_anh_jpeg()).decode()}
    assert tram.nhan_anh(b) == "ok"
    p = tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "video123abc" / "24h" / "anh" / "x_tong-quan.jpg"
    assert p.exists() and p.read_bytes().startswith(b"\xff\xd8")

    # Không phải JPEG thì đừng ghi — cửa này nhận dữ liệu từ mạng.
    xau = dict(b, ten="rac.jpg", anh=base64.b64encode(b"<html>dang nhap lai</html>").decode())
    assert tram.nhan_anh(xau) == "anh la"
    assert not (p.parent / "rac.jpg").exists()


def test_don_anh_cu_giu_lai_moc_moi_va_khong_dung_toi_goi_json(tmp_path):
    """Ảnh là để đối chiếu, không phải kho lưu trữ — nhưng dọn nhầm gói JSON là mất số vĩnh viễn."""
    import base64

    tram = Tram(goc=str(tmp_path))
    (tmp_path / "CHANNEL" / "TL4-T7" / "chi-so").mkdir(parents=True)
    vid = tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "video123abc"
    for i in range(tram.GIU_ANH_MAY_MOC + 4):
        moc = f"{i + 1}h"
        (vid / moc / "raw").mkdir(parents=True)
        (vid / moc / "raw" / "goi.json").write_text("{}", encoding="utf-8")
        tram.nhan_anh({"kenh": "TL4-T7", "id": "video123abc", "label": moc, "ten": "a.jpg",
                       "anh": base64.b64encode(_anh_jpeg()).decode()})
    con = sorted(d.name for d in vid.iterdir() if (d / "anh").is_dir())
    assert len(con) == tram.GIU_ANH_MAY_MOC, f"dọn sai, còn {len(con)} mốc có ảnh"
    # Gói thô của MỌI mốc phải còn nguyên — kể cả mốc đã bị xoá ảnh.
    for d in vid.iterdir():
        assert (d / "raw" / "goi.json").exists(), f"dọn ảnh mà xoá mất gói của {d.name}"


def test_chup_kenh_bon_luot_mot_ngay():
    """1 lượt/ngày thì hai lần chụp cách nhau 24 tiếng, mà chuyện của kênh xảy ra trong vài giờ."""
    nen = _nen()
    m = re.search(r"alarms\.create\('kenh-ngay',[\s\S]{0,120}?periodInMinutes:\s*(\d+)", nen)
    assert m, "không tìm thấy lịch chụp kênh"
    assert int(m.group(1)) <= 360, "chụp kênh vẫn thưa hơn 4 lượt/ngày"


def test_tram_ghi_chu_va_ghi_ca_LY_DO_khi_anh_hong(tmp_path):
    """Không ghi lý do thì lần sau vẫn mù đúng như 05/09: đủ mọi bảng, không một tấm ảnh, không biết vì sao."""
    tram = Tram(goc=str(tmp_path))
    (tmp_path / "CHANNEL" / "TL4-T7" / "chi-so").mkdir(parents=True)
    anh_dir = tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "video123abc" / "24h" / "anh"

    # ảnh chết, chữ sống → vẫn phải để lại bằng chứng
    assert tram.nhan_anh({
        "kenh": "TL4-T7", "id": "video123abc", "label": "24h", "ten": "20260905-1300_tong-quan",
        "anh": "", "chu": "Lượt hiển thị\n22.455\nTỷ lệ bấm\n2,1%",
        "loi": "Cannot access contents of the page.",
    }) == "ok"
    txt = (anh_dir / "20260905-1300_tong-quan.txt").read_text(encoding="utf-8")
    assert "KHÔNG CHỤP ĐƯỢC ẢNH" in txt and "Cannot access" in txt, "mất lý do ảnh hỏng"
    assert "22.455" in txt, "mất luôn chữ chỉ vì ảnh hỏng"
    assert not (anh_dir / "20260905-1300_tong-quan.jpg").exists()


def test_tram_ghi_ca_anh_lan_chu_khi_du_ca_hai(tmp_path):
    import base64

    tram = Tram(goc=str(tmp_path))
    (tmp_path / "CHANNEL" / "TL4-T7" / "chi-so").mkdir(parents=True)
    assert tram.nhan_anh({
        "kenh": "TL4-T7", "id": "video123abc", "label": "24h", "ten": "x_vung",
        "anh": base64.b64encode(_anh_jpeg()).decode(), "chu": "Nhật Bản 89,9%", "loi": "",
    }) == "ok"
    d = tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "video123abc" / "24h" / "anh"
    assert (d / "x_vung.jpg").read_bytes().startswith(b"\xff\xd8")
    assert "Nhật Bản" in (d / "x_vung.txt").read_text(encoding="utf-8")


def test_khong_co_gi_ca_thi_bao_la_chu_khong_tao_thu_muc_rong(tmp_path):
    tram = Tram(goc=str(tmp_path))
    (tmp_path / "CHANNEL" / "TL4-T7" / "chi-so").mkdir(parents=True)
    assert tram.nhan_anh({"kenh": "TL4-T7", "id": "video123abc", "label": "24h",
                          "ten": "rong", "anh": "", "chu": "", "loi": ""}) == "anh la"
    assert not (tmp_path / "CHANNEL" / "TL4-T7" / "chi-so" / "video123abc" / "24h" / "anh").exists()


def test_ban_chu_chi_lay_chu_DANG_HIEN():
    """Lấy cả nút ẩn thì lưới an toàn kêu oan mỗi lượt — và phiên sau sẽ học cách bỏ qua nó.

    Studio giữ sẵn khuôn "Rất tiếc, đã xảy ra lỗi. / Thử lại" ẩn trong DOM ở MỌI trang. Bản chụp
    05/09/2026 vì thế có câu ấy ở cả 24/24 tệp chữ, trong khi ảnh chụp cùng lượt không trang nào
    có banner lỗi. Một cảnh báo luôn bật là một cảnh báo vô dụng.
    """
    than = _nen().split("async function docChu")[1][:2200]
    assert "offsetParent" in than or "getClientRects" in than, "không lọc phần tử ẩn"
    assert "hidden" in than, "không bỏ phần tử mang thuộc tính hidden"
    for the in ("SCRIPT", "STYLE"):
        assert the in than, f"không bỏ thẻ {the} — chữ sẽ lẫn mã nguồn"
