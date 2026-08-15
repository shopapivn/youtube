"""Ảnh tạo ở **tab nào** cũng phải sạch dấu trước khi tới tay khách.

Chủ dự án, 16/08/2026: *"khách tải về thì tao muốn tạo ảnh sẽ luôn xoá logo, có
thể họ tạo ở tab Auto, có thể ở tab Ảnh & Video, thủ công hàng loạt"*.

Bộ bài này canh **cái funnel**, không canh từng tab. Tool có đúng hai đường ghi
tệp kết quả xuống máy khách:

    tab Tự động  →  core/auto_khau.py  `_tai_ket_qua`
    mọi tab khác →  core/jobs.py       `_download_outputs`

Tab Ảnh & Video (cả Thủ công lẫn Hàng loạt) và tab Skill đều dựng `JobSpec` rồi
gọi `app.start_batch`, tức đều rơi vào đường thứ hai. Bịt hai đường ấy là bịt
hết, kể cả tab chưa ai viết.

Không bài nào gọi mạng: `download_to` bị thay bằng hàm chép tệp tại chỗ.
"""

from __future__ import annotations

import os
import queue
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("PIL")

from PIL import Image  # noqa: E402

from core.jobs import JobManager, JobRecord, JobSpec  # noqa: E402
from core.pricing import KIND_IMAGE, KIND_VIDEO  # noqa: E402
from core.xoa_dau_anh import TEP_DAU, la_anh, xoa_dau  # noqa: E402

GOC = Path(__file__).resolve().parent.parent


# ── Dựng ảnh có dấu ──────────────────────────────────────────────────────────

def _nhieu(w=1376, h=768, hat=11):
    r = np.random.RandomState(hat)
    A = r.randint(60, 190, size=(h, w, 3)).astype(np.float64)
    for _ in range(3):
        A = (A + np.roll(A, 1, 0) + np.roll(A, 1, 1)) / 3.0
    return Image.fromarray(A.astype(np.uint8))


def _dan_dau(im, alpha=0.32):
    d = np.load(TEP_DAU)
    hinh = d["hinh"].astype(np.float64)
    s = hinh.shape[0]
    A = np.asarray(im.convert("RGB"), dtype=np.float64)
    H, W = A.shape[:2]
    x0 = W - int(d["le_phai"]) - int(d["canh"]) - int(d["bien"])
    y0 = H - int(d["le_duoi"]) - int(d["canh"]) - int(d["bien"])
    a = np.clip(hinh * alpha, 0.0, 0.93)[:, :, None]
    A[y0:y0 + s, x0:x0 + s, :] = (a * 255.0
                                  + (1 - a) * A[y0:y0 + s, x0:x0 + s, :])
    return Image.fromarray(A.astype(np.uint8))


def _con_dau(duong: str) -> bool:
    """Còn dấu trên tệp này không — hỏi chính bộ xoá dấu."""
    with Image.open(duong) as im:
        im.load()
        _ra, am = xoa_dau(im, tra_alpha=True)
    return am > 0.0


# ── Đường của mọi tab trừ tab Tự động ────────────────────────────────────────

@pytest.fixture
def hang_doi():
    """`JobManager` thật, chỉ thiếu mạng. Dựng nó không gọi ra ngoài."""
    return JobManager(lambda: None, queue.Queue(), max_workers=1)


def _chay_tai_ve(hang_doi, monkeypatch, tmp_path, *, kind, duoi, lam_tep):
    """Cho hàng đợi tải một kết quả về, trả lại đường dẫn tệp đã lưu."""
    def tai_gia(url, dest, **_kw):
        lam_tep(dest)

    monkeypatch.setattr("core.jobs.download_to", tai_gia)
    ban = JobRecord(spec=JobSpec(kind=kind, content="mot canh",
                                 label="canh 1", out_dir=str(tmp_path)))
    hang_doi._download_outputs(
        ban, {"outputs": [{"url": "https://vi-du/khong-goi-that",
                           "content_type": "image/png" if duoi == "png"
                           else "video/mp4"}]})
    assert ban.files, "hàng đợi phải lưu được tệp thì bài kiểm mới có nghĩa"
    return ban.files[0]


class TestHangDoiViec:
    """Tab Ảnh & Video (Thủ công + Hàng loạt), tab Skill, và mọi tab sau này."""

    def test_anh_tai_ve_da_sach_dau(self, hang_doi, monkeypatch, tmp_path):
        tep = _chay_tai_ve(
            hang_doi, monkeypatch, tmp_path, kind=KIND_IMAGE, duoi="png",
            lam_tep=lambda p: _dan_dau(_nhieu()).save(p, format="PNG"))
        assert la_anh(tep)
        assert not _con_dau(tep), (
            "ảnh ra khỏi hàng đợi mà còn dấu — tab Ảnh & Video, tab Skill và "
            "mọi tab dựng JobSpec đều đi qua đúng chỗ này")

    def test_anh_sach_san_thi_khong_bi_dung_vao(self, hang_doi, monkeypatch,
                                                tmp_path):
        """Không phải ảnh nào cổng trả về cũng có dấu."""
        goc = {}

        def lam(p):
            im = _nhieu()
            im.save(p, format="PNG")
            goc["byte"] = im.tobytes()

        tep = _chay_tai_ve(hang_doi, monkeypatch, tmp_path, kind=KIND_IMAGE,
                           duoi="png", lam_tep=lam)
        with Image.open(tep) as im:
            im.load()
            assert im.tobytes() == goc["byte"], "ảnh vốn sạch mà vẫn bị trừ"

    def test_clip_khong_bi_mo_ra_soi(self, hang_doi, monkeypatch, tmp_path):
        """Lọc theo đuôi TRƯỚC khi mở tệp.

        Hàng đợi tải về cả clip lẫn tiếng nói. Mở một tệp mp4 trăm mê-ga bằng
        thư viện ảnh là phí công, mà làm hàng loạt thì thành chậm thấy được.
        """
        mo = []
        that = Image.open

        def dem(fp, *a, **k):
            mo.append(str(fp))
            return that(fp, *a, **k)

        monkeypatch.setattr(Image, "open", dem)
        tep = _chay_tai_ve(
            hang_doi, monkeypatch, tmp_path, kind=KIND_VIDEO, duoi="mp4",
            lam_tep=lambda p: open(p, "wb").write(b"\x00\x00\x00 ftypmp42"))
        assert tep.endswith(".mp4")
        assert not any(m.endswith(".mp4") for m in mo), \
            "đã mở tệp clip bằng thư viện ảnh: {0}".format(mo)

    def test_tai_hong_thi_khong_ai_dung_vao_tep(self, hang_doi, monkeypatch,
                                                tmp_path):
        """Tải hỏng thì thoát ngay, đừng xoá dấu trên một tệp dở dang."""
        from core.download import DownloadError

        def tai_hong(url, dest, **_kw):
            open(dest, "wb").write(b"mot nua")
            raise DownloadError("mang dut giua chung")

        monkeypatch.setattr("core.jobs.download_to", tai_hong)
        ban = JobRecord(spec=JobSpec(kind=KIND_IMAGE, content="x",
                                     label="canh 1", out_dir=str(tmp_path)))
        hang_doi._download_outputs(
            ban, {"outputs": [{"url": "https://vi-du/hong",
                               "content_type": "image/png"}]})
        assert not ban.files


# ── Canh cho cả hai đường, để lần sau thêm đường thứ ba thì biết ─────────────

class TestKhongDuongNaoSot:
    def test_moi_cho_tai_tep_ket_qua_deu_co_buoc_xoa_dau(self):
        """Ai thêm một đường tải mới mà quên bước này thì bài kiểm nói ngay."""
        for ten in ("core/jobs.py", "core/pipeline.py"):
            chu = (GOC / ten).read_text(encoding="utf-8")
            for i, dong in enumerate(chu.splitlines()):
                if "download_to(url, dest" not in dong:
                    continue
                # Cửa sổ rộng tay: bên `pipeline.py` có một khối `except` dài
                # giải thích chuyện job đã trả tiền, nằm chen giữa hai dòng này.
                sau = "\n".join(chu.splitlines()[i:i + 30])
                assert "_xoa_dau(dest)" in sau, (
                    "{0} dòng {1}: tải tệp về mà không xoá dấu".format(
                        ten, i + 1))

    def test_tab_tu_dong_van_co_duong_rieng_cua_no(self):
        chu = (GOC / "core" / "auto_khau.py").read_text(encoding="utf-8")
        assert chu.count("_xoa_dau(bc, tep)") >= 3, (
            "tab Tự động không đi qua hàng đợi việc — nó có đường tải riêng và "
            "phải tự xoá dấu ở cả ba chỗ")

    def test_khong_tab_nao_tu_tai_anh_ve_bang_duong_rieng(self):
        """Chỉ `core/` được ghi tệp kết quả. Tab nào tự tải là lọt lưới."""
        vi_pham = []
        for tep in (GOC / "ui_qt").glob("trang_*.py"):
            chu = tep.read_text(encoding="utf-8")
            if "download_to(" in chu or "urlretrieve(" in chu:
                vi_pham.append(tep.name)
        assert not vi_pham, (
            "{0} tự tải tệp về, không đi qua chỗ xoá dấu".format(vi_pham))


class TestClipLayKhungDauTuTepDaSach:
    """Ảnh sạch trên máy mà clip vẫn lấy link cũ trên máy chủ thì công cốc."""

    def test_auto_tai_len_tep_tren_dia_chu_khong_dung_lai_url_cu(self):
        chu = (GOC / "core" / "auto_khau.py").read_text(encoding="utf-8")
        dau = chu.index("def _url_anh_canh")
        than = chu[dau:dau + 3000]
        assert "upload_file(duong)" in than, (
            "khung đầu của clip phải tải lên từ TỆP trên đĩa — tệp ấy đã được "
            "xoá dấu; dùng lại URL kết quả của job ảnh là clip đeo dấu như cũ")

    def test_tab_hang_loat_cung_tai_len_tep_tren_dia(self):
        chu = (GOC / "ui_qt" / "trang_anh_video.py").read_text(encoding="utf-8")
        dau = chu.index("def _day_video")
        than = chu[dau:dau + 1200]
        assert "upload_file(duong)" in than, (
            "tab Hàng loạt phải tải lên tệp ảnh đã tải về máy, không phải URL "
            "kết quả của job ảnh")
