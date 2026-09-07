"""Mã ngôn ngữ cho giọng đọc: đường dây phải đúng, LỜI HỨA phải thật.

Ba chỗ cùng một luật: SDK (`build_body`), hàng đợi việc (`_call_create`), và
tab Tự động lấy mã từ `ngon_ngu` của kênh. Rỗng thì KHÔNG gửi gì.

═══ VÀ MỘT ĐIỀU ĐÃ ĐO, PHẢI GHIM LẠI ═══

Ngày 08/09/2026 tôi hỏi thẳng máy chủ bằng job thật, ba thước đo độc lập:

* **Thời lượng.** Chín lượt cùng một câu tiếng Việt: không mã 7,88 s · `vi`
  7,93 s · `en` (sai hẳn) 7,99 s. Chênh giữa nhóm 0,05–0,11 s, nhiễu trong một
  nhóm tới 0,65 s. Lặp với giọng đa ngữ + chữ Nhật: chênh 0,24–0,78 s / nhiễu 1,28 s.
* **Băm tệp.** Mọi tệp một băm khác nhau → audio sinh lại mỗi lượt.
* **Nghe lại bằng `faster-whisper`.** Tám tệp chữ Nhật, kể cả những lượt ghim
  SAI mã (`vi`), đều nghe ra tiếng Nhật đúng, tin cậy 0,99–1,00.

Tức **máy chủ hiện bỏ qua `language_code`**. Gửi vẫn 202 (nó bỏ qua mọi trường
lạ), và giữ đường dây là đúng — ngày máy chủ dùng tới thì khách bản cũ cũng
được hưởng. Nhưng lúc chưa có tác dụng thì **không được hứa với khách rằng
chọn mã làm giọng hay hơn, cũng không được doạ chọn nhầm là hỏng cả bài**.
Bài `test_khong_hua_dieu_chua_lam_duoc` canh đúng chỗ đó.
"""
import pytest

from core.kenh import DANH_SACH_TIENG, ma_ngon_ngu_tts


# ── Mã kênh -> mã gửi đi ─────────────────────────────────────────────────────

@pytest.mark.parametrize("khai, mong", [
    ("ja", "ja"),
    ("JA", "ja"),
    ("ja-JP", "ja"),          # kênh khai kiểu locale -> lấy hai chữ đầu
    ("", ""),                 # chưa khai -> không gửi
    ("x", ""),                # một chữ -> không phải mã -> không gửi
    ("12", ""),               # không phải chữ cái -> không gửi
    (None, ""),
])
def test_ma_ngon_ngu_tts(khai, mong):
    assert ma_ngon_ngu_tts(khai) == mong


def test_danh_sach_tieng_tieng_viet_dung_dau_va_khong_trung():
    ma = [m for m, _ in DANH_SACH_TIENG]
    assert ma[:3] == ["vi", "en", "ja"], "tiếng khách hay làm kênh phải lên đầu"
    assert len(ma) == len(set(ma))
    assert all(ma_ngon_ngu_tts(m) == m for m in ma)


# ── SDK: build_body ───────────────────────────────────────────────────────────

def test_sdk_khong_gui_ma_khi_khong_chon():
    from shopapi.resources.tts import build_body

    body = build_body(text="xin chào", voice_id="vi_female_01", speed=None,
                      format="mp3", webhook_url=None, extra_body=None)
    assert "language_code" not in body, "mặc định phải để máy chủ tự nhận diện"


def test_sdk_ha_chu_hoa_ve_thuong():
    from shopapi.resources.tts import build_body

    body = build_body(text="hello", voice_id="vi_female_01", speed=None,
                      format="mp3", webhook_url=None, extra_body=None,
                      language_code=" EN ")
    assert body["language_code"] == "en"


@pytest.mark.parametrize("xau", ["english", "v", "vi-VN", 12])
def test_sdk_tu_choi_ma_sai_khuon_truoc_khi_ton_mang(xau):
    from shopapi._exceptions import InvalidRequestError
    from shopapi.resources.tts import build_body

    with pytest.raises(InvalidRequestError) as loi:
        build_body(text="hello", voice_id="vi_female_01", speed=None,
                   format="mp3", webhook_url=None, extra_body=None,
                   language_code=xau)
    assert "language_code" in str(loi.value)


# ── Trình lập kênh (tab Tự động): Bước 2 phải có ô CHỌN ngôn ngữ ────────────
#
# Đọc NGUỒN chứ không dựng cửa sổ Qt (cùng cách với
# `test_o_tieng_canh_tren_giao_dien.py`). Chủ dự án 07/09/2026 mở đúng chỗ này
# ("chỗ video tự động ở template… điền id giọng không có chọn thêm ngôn ngữ").

def test_khong_hua_dieu_chua_lam_duoc():
    """Chữ khách ĐỌC ĐƯỢC không được hứa hiệu quả mà máy chủ chưa đưa ra.

    Ba câu dưới đây từng nằm trong tooltip, bài hướng dẫn và README kênh. Cả ba
    đều mô tả một hành vi mà phép đo 08/09/2026 chứng minh là chưa có. Bỏ quên
    một câu là khách chỉnh một ô không có tác dụng, rồi đổ cho tool khi giọng
    đọc không như họ mong.
    """
    import io
    import os

    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cam = ("ngắt nghỉ tự nhiên hơn", "đọc hỏng cả bài", "giọng ngắt nghỉ theo")
    # Chỉ soi chữ KHÁCH THẤY; bình luận trong mã được phép kể lại phép đo.
    for rel in ("ui_qt/trang_voice.py", "ui_qt/huong_dan.py", "ui_qt/kenh.py",
                "CHANNEL/README.md", "tool-catalog/voice.shopapi/tool.json"):
        chu = io.open(os.path.join(goc, rel), encoding="utf-8").read()
        for xau in cam:
            assert xau not in chu, (
                "{0} còn hứa “{1}” — máy chủ chưa dùng `language_code`, "
                "xem đầu tệp bài kiểm này".format(rel, xau))


def test_buoc_giong_doc_cua_kenh_co_o_chon_ngon_ngu():
    import inspect

    import ui_qt.kenh as uk

    ma = inspect.getsource(uk.HopKenh._trang_giong)
    assert "_o_ngon_ngu" in ma and "DANH_SACH_TIENG" in ma
    assert "QLineEdit" not in ma.split("_o_ngon_ngu", 1)[1].split("addWidget(self._o_ngon_ngu)")[0], (
        "ngôn ngữ phải là ô CHỌN, không phải ô gõ mã")


def test_ngon_ngu_kenh_duoc_ghi_xuong_yaml_va_nap_lai_khi_sua():
    import inspect

    import ui_qt.kenh as uk

    assert '"ngon_ngu"' in inspect.getsource(uk.HopKenh._ghi_de_kenh_yaml), (
        "vẽ ô ra mà không ghi là khách đổi xong, lưu, rồi mất")
    assert "_dat_ngon_ngu_kenh(self._kenh.ngon_ngu)" in inspect.getsource(uk.HopKenh._dung_sua)
    assert "_ngon_ngu_theo_khan_gia" in inspect.getsource(uk.HopKenh._dung_tao), (
        "lúc tạo, đổi khán giả ở Bước 1 thì tiếng giọng đọc phải đổi theo")


# ── Hàng đợi việc: params -> SDK ─────────────────────────────────────────────

class _TtsGia:
    def __init__(self):
        self.goi = []

    def create(self, **kw):
        self.goi.append(kw)
        return {"id": "job_x"}


class _ClientGia:
    def __init__(self):
        self.tts = _TtsGia()


def _hang_doi_voi_client_gia():
    from core.jobs import JobManager

    q = JobManager.__new__(JobManager)
    q._client = _ClientGia()
    return q


@pytest.mark.parametrize("params, mong", [
    ({"voice_id": "v"}, None),                         # thiếu -> không gửi
    ({"voice_id": "v", "language_code": ""}, None),    # Tự động -> không gửi
    ({"voice_id": "v", "language_code": "ja"}, "ja"),  # khách chọn -> gửi
])
def test_hang_doi_chuyen_ma_ngon_ngu_xuong_sdk(params, mong):
    from core.jobs import JobSpec
    from core.pricing import KIND_TTS

    q = _hang_doi_voi_client_gia()
    q._call_create(JobSpec(kind=KIND_TTS, content="xin chào", params=params))
    goi = q._client.tts.goi[0]
    assert goi["language_code"] == mong
