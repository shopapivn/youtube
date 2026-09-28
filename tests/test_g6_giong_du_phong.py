"""GÓI G6 — giọng dự phòng cho khâu đọc (`core/tu_choi_noi_dung.py` mục 2.5).

Thiết kế: `docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md`. Năm bài kiểm bắt buộc của
gói (mục 3.1, dòng G6):

1. giọng khoá + có giọng dự phòng → mọi đoạn đọc bằng giọng mới, đoạn cũ (đã
   đọc bằng giọng bị khoá) vào `_lam-lai/`.
2. giọng khoá, không có giọng dự phòng và tool không tự chọn được → HỎNG với
   đúng câu rõ.
3. đoạn bị chặn nội dung → CHỈ đoạn đó được viết lại, `1-kich-ban.txt` cập
   nhật đúng đoạn ấy.
4. sổ cấp kênh: lượt SAU của cùng kênh dùng ngay giọng dự phòng đã biết,
   không phải mất một lượt gửi hỏng rồi mới tìm ra.
5. kênh không khai `giong_du_phong` → tool tự chọn giọng cùng ngôn ngữ + cùng
   giới người kể, từ danh sách giọng tool đang có (`shopapi.VOICE_CATALOG` +
   `voice_id` của các kênh khác trong `CHANNEL/`).

Không gọi mạng: `bc.client` là đồ giả, và `_tai_ket_qua_mot_lan` / `_noi_mp3`
/ `_doi_cao_do_giong` / `_lam_sach_ket_qua` bị vá để khỏi cần FFmpeg hay HTTP
thật — cùng nếp với `tests/test_tai_ket_qua_kien_nhan.py`.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from core import auto_khau as ak
from core.auto import LuotChay, TrangThaiKhau
from core.kenh import Kenh


# ── Đồ giả dùng chung ────────────────────────────────────────────────────────


class _TtsGia:
    """Máy chủ ShopAPI giả: `create()` hỏng CHO ĐÚNG các `voice_id` bị khoá."""

    def __init__(self, giong_khoa=()):
        self.goi = []
        self.giong_khoa = set(giong_khoa)
        self.tts = self
        self.jobs = self

    def create(self, **kw):
        self.goi.append(kw)
        if kw.get("voice_id") in self.giong_khoa:
            from shopapi import InvalidRequestError

            raise InvalidRequestError(
                message="Giọng đọc “x” cần gói trả phí (voice "
                        "subscription required) hoặc không tồn tại.",
                code="invalid_request")
        return {"id": "job_{0}".format(len(self.goi)), "status": "succeeded",
                "outputs": [{"url": "http://x/a.mp3"}]}

    def retrieve(self, ma):  # pragma: no cover - job xong ngay lúc tạo
        raise AssertionError("không nên polling: job trả succeeded ngay")


def _bc(tmp_path, kenh: Kenh, giong_khoa=(), goi_chat=None) -> ak.BoiCanh:
    dong = []
    client = _TtsGia(giong_khoa=giong_khoa)
    return ak.BoiCanh(
        goc=str(tmp_path), kenh=kenh,
        goi_chat=goi_chat or (lambda *a, **k: ""),
        client=client, on_log=dong.append, ngu=lambda s: None,
        ffmpeg="",
    ), dong, client


def _kenh(**kw) -> Kenh:
    mac_dinh = dict(ma="k1", ten="Kênh test", ngon_ngu="vi", voice_id="giong-goc",
                    giong_du_phong="", gioi_nguoi_ke="", mo_hinh="claude-sonnet-5",
                    giay_nghi_phan=0.0)
    mac_dinh.update(kw)
    return Kenh(**mac_dinh)


def _luot(tmp_path, kich_ban: str) -> LuotChay:
    thu_muc = os.path.join(str(tmp_path), "PROJECTS", "AUTO", "k1", "0001")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "1-kich-ban.txt"), "w", encoding="utf-8") as tep:
        tep.write(kich_ban)
    return LuotChay(ma_kenh="k1", ma_luot="0001", thu_muc=thu_muc)


@pytest.fixture(autouse=True)
def _vo_hieu_hoa_duong_ffmpeg(monkeypatch):
    """Không cần FFmpeg thật: vá phần tải + nối/đổi cao độ/dọn tệp cuối khâu."""
    def tai_gia(bc, goi, chi_so, dich):
        with open(dich, "wb") as tep:
            tep.write(b"ID3fake-mp3")
        return dich

    monkeypatch.setattr(ak, "_tai_ket_qua_mot_lan", tai_gia)
    monkeypatch.setattr(ak, "_tim_ffmpeg", lambda: "")
    monkeypatch.setattr(ak, "_noi_mp3", lambda bc, manh, dich, nghi=None: (
        open(dich, "wb").write(b"ID3fake-mp3-noi")))
    monkeypatch.setattr(ak, "_doi_cao_do_giong", lambda bc, mp3: False)
    monkeypatch.setattr(ak, "_lam_sach_ket_qua", lambda bc, *tep: None)
    yield


# ── 1) giọng khoá + CÓ giọng dự phòng: đổi cả khâu, đoạn cũ vào _lam-lai ────


def test_giong_khoa_co_du_phong_doi_ca_khau_va_don_doan_cu(tmp_path):
    kenh = _kenh(voice_id="giong-goc", giong_du_phong="giong-du-phong")
    bc, dong, client = _bc(tmp_path, kenh, giong_khoa={"giong-goc"})
    luot = _luot(tmp_path, "Đoạn một ngắn để đọc thử.\n---\nĐoạn hai cũng ngắn.")

    # Mô phỏng "Chạy tiếp": đoạn 1 đã đọc XONG bằng giọng gốc ở một lượt
    # trước (tệp đã nằm sẵn trên đĩa) — đoạn 2 mới hỏng vì giọng bị khoá.
    thu_muc_doan = os.path.join(luot.thu_muc, "2-doan")
    os.makedirs(thu_muc_doan, exist_ok=True)
    with open(os.path.join(thu_muc_doan, "001.mp3"), "wb") as tep:
        tep.write(b"ID3-doan-1-giong-cu")

    lam = ak._khau_giong_doc(bc)
    ket = lam(luot, TrangThaiKhau(ma="giong_doc"))

    assert ket["so_doan"] == 2
    # Đoạn 1 (giọng cũ) đã bị đưa vào _lam-lai/, KHÔNG còn nằm ở chỗ cũ.
    kho_lam_lai = os.path.join(thu_muc_doan, "_lam-lai")
    assert os.path.isdir(kho_lam_lai)
    assert len(os.listdir(kho_lam_lai)) == 1
    # Không có lượt gọi nào XONG bằng giọng gốc — mọi lượt "giong-goc" đều
    # hỏng (đúng nghĩa "bị khoá"); các lượt còn lại phải là giọng dự phòng.
    goi_thanh_cong = [g for g in client.goi if g.get("voice_id") != "giong-goc"]
    assert goi_thanh_cong, "phải có lượt gọi bằng giọng dự phòng"
    assert all(g["voice_id"] == "giong-du-phong" for g in goi_thanh_cong)
    assert os.path.exists(os.path.join(thu_muc_doan, "001.mp3"))
    assert os.path.exists(os.path.join(thu_muc_doan, "002.mp3"))
    assert any("đổi CẢ KHÂU sang giọng dự phòng" in d for d in dong)


# ── 2) giọng khoá, KHÔNG có giọng dự phòng, KHÔNG tự chọn được → HỎNG rõ ────


def test_giong_khoa_khong_du_phong_khong_tu_chon_duoc_thi_HONG_ro(tmp_path):
    kenh = _kenh(voice_id="giong-goc", giong_du_phong="", ngon_ngu="ja")
    bc, dong, client = _bc(tmp_path, kenh, giong_khoa={"giong-goc"})
    # goc KHÔNG có thư mục CHANNEL/ nào khác → tự chọn cũng ra rỗng.
    luot = _luot(tmp_path, "Một đoạn ngắn để đọc thử giọng.")

    with pytest.raises(RuntimeError) as loi:
        lam = ak._khau_giong_doc(bc)
        lam(luot, TrangThaiKhau(ma="giong_doc"))

    cau = str(loi.value)
    assert "giong-goc" in cau
    assert "khoá" in cau or "trả phí" in cau
    assert "Cài đặt kênh" in cau


# ── 3) đoạn bị chặn nội dung: CHỈ đoạn đó viết lại, kịch bản cập nhật ───────


def test_doan_bi_chan_noi_dung_chi_doan_do_duoc_viet_lai(tmp_path):
    kenh = _kenh(voice_id="giong-goc")
    doan_cam = "Câu văn bị bộ lọc nội dung từ chối vì mô tả bạo lực."
    doan_lanh = "Một buổi sáng yên bình ở ngôi làng nhỏ."
    kich_ban = doan_cam + "\n---\n" + doan_lanh

    goi_ai = {"n": 0}

    def goi_chat(loi_nhac, **kw):
        goi_ai["n"] += 1
        return "Một buổi sáng căng thẳng nhưng không đổ máu."

    class _TtsChanNoiDung(_TtsGia):
        def create(self, **kw):
            self.goi.append(kw)
            if kw.get("text", "").strip() == doan_cam:
                from shopapi import ContentRejectedError

                raise ContentRejectedError(
                    message="Nội dung bạn gửi vi phạm quy định sử dụng nên đã "
                            "bị từ chối. Bạn KHÔNG bị trừ tiền.",
                    code="content_rejected")
            return {"id": "job_{0}".format(len(self.goi)), "status": "succeeded",
                    "outputs": [{"url": "http://x/a.mp3"}]}

    client = _TtsChanNoiDung()
    bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=goi_chat,
                    client=client, on_log=[].append, ngu=lambda s: None, ffmpeg="")
    luot = _luot(tmp_path, kich_ban)

    lam = ak._khau_giong_doc(bc)
    ket = lam(luot, TrangThaiKhau(ma="giong_doc"))

    assert ket["so_doan"] == 2
    assert goi_ai["n"] == 1, "chỉ đoạn bị chặn mới gọi AI viết lại"
    # 1-kich-ban.txt phải mang câu ĐÃ viết lại, đoạn lành giữ nguyên.
    kich_ban_moi = open(os.path.join(luot.thu_muc, "1-kich-ban.txt"),
                        encoding="utf-8").read()
    assert "Một buổi sáng căng thẳng nhưng không đổ máu." in kich_ban_moi
    assert doan_cam not in kich_ban_moi
    assert doan_lanh in kich_ban_moi
    # Không đoạn nào bị coi là "giọng bị khoá" — cả hai file đều ra.
    assert os.path.exists(os.path.join(luot.thu_muc, "2-doan", "001.mp3"))
    assert os.path.exists(os.path.join(luot.thu_muc, "2-doan", "002.mp3"))


# ── RÀ SOÁT 28/09/2026: KHÔNG sửa 1-kich-ban.txt GIỮA khâu — tệp phụ
# `2-doan/thay-the.json` + `2-doan/van-ban-bam.json`, áp một lần lúc xong ──


def _tts_chan_mot_cau(doan_cam: str, cau_thay: str):
    class _TtsChanNoiDung(_TtsGia):
        def create(self, **kw):
            self.goi.append(kw)
            if kw.get("text", "").strip() == doan_cam:
                from shopapi import ContentRejectedError

                raise ContentRejectedError(
                    message="Nội dung bạn gửi vi phạm quy định sử dụng nên đã "
                            "bị từ chối. Bạn KHÔNG bị trừ tiền.",
                    code="content_rejected")
            return {"id": "job_{0}".format(len(self.goi)), "status": "succeeded",
                    "outputs": [{"url": "http://x/a.mp3"}]}

    return _TtsChanNoiDung()


class TestKhongSuaKichBanGiuaKhau:
    def test_thay_the_ghi_vao_tep_phu_khong_dung_kich_ban_giua_khau(self, tmp_path, monkeypatch):
        """Chặn NGAY TRƯỚC lúc nối mp3 cuối — tại thời điểm đó, mọi mảnh mp3
        đã xong nhưng `_khau_giong_doc` CHƯA `return`. `1-kich-ban.txt` phải
        đã được áp ĐÚNG MỘT LẦN rồi (đặt trước `_noi_mp3`, không phải giữa
        vòng đọc từng đoạn)."""
        kenh = _kenh(voice_id="giong-goc")
        doan_cam = "Câu văn bị bộ lọc nội dung từ chối vì mô tả bạo lực."
        doan_lanh = "Một buổi sáng yên bình ở ngôi làng nhỏ."
        kich_ban = doan_cam + "\n---\n" + doan_lanh
        cau_thay = "Một buổi sáng căng thẳng nhưng không đổ máu."

        client = _tts_chan_mot_cau(doan_cam, cau_thay)
        bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh,
                        goi_chat=lambda *a, **k: cau_thay,
                        client=client, on_log=[].append, ngu=lambda s: None, ffmpeg="")
        luot = _luot(tmp_path, kich_ban)

        def noi_hong(*a, **k):
            raise RuntimeError("mô phỏng ngắt máy giữa lúc nối mp3")

        monkeypatch.setattr(ak, "_noi_mp3", noi_hong)
        with pytest.raises(RuntimeError, match="mô phỏng ngắt máy"):
            ak._khau_giong_doc(bc)(luot, TrangThaiKhau(ma="giong_doc"))

        # `1-kich-ban.txt` đã được áp — không phải "sửa giữa khâu" theo nghĩa
        # cũ (ghi ngay khi MỘT đoạn xong), mà là áp ĐỦ tất cả thay thế MỘT
        # LẦN sau khi mọi mảnh mp3 đã có, trước khi nối — xem thân bài kiểm.
        kich_ban_sau = open(os.path.join(luot.thu_muc, "1-kich-ban.txt"),
                            encoding="utf-8").read()
        assert doan_cam not in kich_ban_sau
        assert cau_thay in kich_ban_sau

        # Tệp phụ ghi lại đúng thay thế, độc lập với 1-kich-ban.txt.
        thay_the = json.load(open(
            os.path.join(luot.thu_muc, "2-doan", ak.TEP_THAY_THE_DOAN),
            encoding="utf-8"))
        assert thay_the["1"]["doan_moi"] == cau_thay
        assert os.path.exists(os.path.join(luot.thu_muc, "2-doan", "001.mp3"))
        assert os.path.exists(os.path.join(luot.thu_muc, "2-doan", "002.mp3"))

    def test_chay_tiep_sau_khi_ngat_giua_noi_mp3_khong_doc_lai_khong_lech(
            self, tmp_path, monkeypatch):
        """"Chạy tiếp" sau ca ngắt máy ở bài trên: không gọi thêm TTS nào (cả
        hai mảnh mp3 được TÁI SỬ DỤNG đúng nhờ băm văn bản khớp — kể cả mảnh
        đã viết lại, dù `1-kich-ban.txt` giờ mang bản ĐÃ SỬA), và khâu hoàn
        tất bình thường ở lần chạy thứ hai."""
        kenh = _kenh(voice_id="giong-goc")
        doan_cam = "Câu văn bị bộ lọc nội dung từ chối vì mô tả bạo lực."
        doan_lanh = "Một buổi sáng yên bình ở ngôi làng nhỏ."
        kich_ban = doan_cam + "\n---\n" + doan_lanh
        cau_thay = "Một buổi sáng căng thẳng nhưng không đổ máu."

        client = _tts_chan_mot_cau(doan_cam, cau_thay)
        bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh,
                        goi_chat=lambda *a, **k: cau_thay,
                        client=client, on_log=[].append, ngu=lambda s: None, ffmpeg="")
        luot = _luot(tmp_path, kich_ban)

        monkeypatch.setattr(ak, "_noi_mp3", lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("mô phỏng ngắt máy giữa lúc nối mp3")))
        with pytest.raises(RuntimeError, match="mô phỏng ngắt máy"):
            ak._khau_giong_doc(bc)(luot, TrangThaiKhau(ma="giong_doc"))
        so_lan_goi_truoc = len(client.goi)

        def noi_that(bc_, manh, dich, nghi=None):
            with open(dich, "wb") as tep:
                tep.write(b"ID3fake-mp3-noi")

        monkeypatch.setattr(ak, "_noi_mp3", noi_that)
        ket = ak._khau_giong_doc(bc)(luot, TrangThaiKhau(ma="giong_doc"))

        assert ket["so_doan"] == 2
        assert len(client.goi) == so_lan_goi_truoc, (
            "cả hai mảnh mp3 phải được TÁI SỬ DỤNG nguyên vẹn ở lần chạy "
            "tiếp — không gọi thêm TTS nào, và không đâm lại đúng vân tay "
            "GỐC đã bị chặn nội dung")
        assert os.path.exists(os.path.join(luot.thu_muc, "2-giong-doc.mp3"))

    def test_ap_thay_the_bo_qua_muc_bam_khong_khop(self, tmp_path):
        """`_ap_thay_the_vao_kich_ban` không tin mù tệp phụ — băm lệch (tệp
        `thay-the.json` bị sửa tay/hỏng) thì BỎ QUA đúng mục đó, không đoán."""
        thu_muc = str(tmp_path)
        thu_muc_doan = os.path.join(thu_muc, "2-doan")
        os.makedirs(thu_muc_doan, exist_ok=True)
        with open(os.path.join(thu_muc, "1-kich-ban.txt"), "w", encoding="utf-8") as tep:
            tep.write("Câu gốc chưa đổi.")
        with open(os.path.join(thu_muc_doan, ak.TEP_THAY_THE_DOAN), "w",
                  encoding="utf-8") as tep:
            json.dump({"1": {"doan_cu": "Câu gốc chưa đổi.", "doan_moi": "Câu đã sửa.",
                             "bam_cu": "bam-sai-be-be"}}, tep)

        luot = LuotChay(ma_kenh="k1", ma_luot="0001", thu_muc=thu_muc)
        da_ap = ak._ap_thay_the_vao_kich_ban(luot, thu_muc_doan)

        assert da_ap == 0
        assert open(os.path.join(thu_muc, "1-kich-ban.txt"),
                    encoding="utf-8").read() == "Câu gốc chưa đổi."

    def test_bam_van_ban_khop_va_khong_khop(self, tmp_path):
        thu_muc_doan = str(tmp_path)
        ak._ghi_bam_van_ban_doan(thu_muc_doan, 1, "văn bản A")
        assert ak._bam_van_ban_khop(thu_muc_doan, 1, "văn bản A") is True
        assert ak._bam_van_ban_khop(thu_muc_doan, 1, "văn bản KHÁC") is False
        # Chưa có tệp băm (đoạn 2 chưa từng ghi) → coi như không kiểm được,
        # tin mp3 hiện có như nết cũ.
        assert ak._bam_van_ban_khop(thu_muc_doan, 2, "bất kỳ") is True


# ── RÀ SOÁT 28/09/2026: `_viet_lai_doan_doc` không nuốt HẾT TIỀN, không để
# lời TỪ CHỐI của chính AI viết lại lọt thành "bản đã sửa" ─────────────────


# ── RÀ SOÁT 28/09/2026: "văn bản quá dài" chia ĐÔI THẬT theo câu, thay vì
# viết lại ±10% (viết lại giữ nguyên độ dài không giải quyết được gì) ───────


_DOAN_DAI = (
    "Một câu chuyện dài kể về hành trình của cô gái nhỏ. "
    "Cô đi qua những cánh đồng lúa chín vàng mỗi buổi sáng sớm. "
    "Trên đường cô gặp rất nhiều người bạn tốt bụng và thân thiện. "
    "Họ cùng nhau chia sẻ những câu chuyện vui buồn của cuộc sống. "
    "Cuối ngày cô trở về nhà với trái tim tràn đầy niềm vui thật sự."
)


class _TtsQuaDai(_TtsGia):
    """Máy chủ giả: từ chối MỌI lượt gọi dài hơn `tran_ky_tu` bằng câu có
    "quá dài" — mô phỏng trần THẬT của cổng thấp hơn ước lượng cục bộ
    (`CHU_MOI_LUOT_DOC`) của tool, nên dù đã tiền-chia đoạn vẫn có thể dính."""

    def __init__(self, tran_ky_tu: int):
        super().__init__()
        self.tran_ky_tu = tran_ky_tu

    def create(self, **kw):
        self.goi.append(kw)
        text = kw.get("text", "")
        if len(text) > self.tran_ky_tu:
            from shopapi import InvalidRequestError

            raise InvalidRequestError(
                message="Văn bản quá dài cho một lượt đọc (text too long).",
                code="invalid_request")
        return {"id": "job_{0}".format(len(self.goi)), "status": "succeeded",
                "outputs": [{"url": "http://x/a.mp3"}]}


class TestVanBanQuaDaiChiaDoi:
    def test_qua_dai_chia_doi_theo_cau_khong_doi_loi_doc(self, tmp_path):
        kenh = _kenh(voice_id="giong-goc")
        client = _TtsQuaDai(tran_ky_tu=len(_DOAN_DAI) // 2 + 40)
        bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=lambda *a, **k: "",
                        client=client, on_log=[].append, ngu=lambda s: None, ffmpeg="")
        luot = _luot(tmp_path, _DOAN_DAI)

        lam = ak._khau_giong_doc(bc)
        ket = lam(luot, TrangThaiKhau(ma="giong_doc"))

        assert ket["so_doan"] == 1, "vẫn đúng MỘT đoạn — chỉ khác cách GỬI"
        # Ba lượt gọi: 1 lần đủ dài bị từ chối, 2 lần cho hai nửa.
        van_ban_da_goi = [g["text"] for g in client.goi]
        assert van_ban_da_goi[0] == _DOAN_DAI
        assert len(van_ban_da_goi) == 3
        for nua in van_ban_da_goi[1:]:
            assert len(nua) <= client.tran_ky_tu
        # Hai nửa ghép lại (bỏ khoảng trắng thừa ở mép) đúng bằng bản gốc —
        # lời đọc không đổi một chữ.
        ghep = (van_ban_da_goi[1].strip() + " " + van_ban_da_goi[2].strip())
        assert ghep.replace("  ", " ") == _DOAN_DAI

        # KHÔNG được coi là "viết lại nội dung" — 1-kich-ban.txt giữ NGUYÊN,
        # không có tệp thay-the.json nào ghi cho đoạn này.
        kich_ban_sau = open(os.path.join(luot.thu_muc, "1-kich-ban.txt"),
                            encoding="utf-8").read()
        assert _DOAN_DAI in kich_ban_sau
        duong_thay_the = os.path.join(luot.thu_muc, "2-doan", ak.TEP_THAY_THE_DOAN)
        assert not os.path.exists(duong_thay_the) or not json.load(
            open(duong_thay_the, encoding="utf-8"))
        assert os.path.exists(os.path.join(luot.thu_muc, "2-doan", "001.mp3"))

    def test_khong_tach_duoc_thi_giu_loi_goc(self, tmp_path):
        """Một 'đoạn' không có lấy một dấu câu/khoảng trắng nào để chia (ca
        cực đoan) — không chia đôi được thì phải giữ NGUYÊN lỗi gốc, không
        đoán bừa hay lặp vô hạn."""
        kenh = _kenh(voice_id="giong-goc")
        doan_lien = "a" * 300  # không dấu câu, không khoảng trắng
        client = _TtsQuaDai(tran_ky_tu=100)
        bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=lambda *a, **k: "",
                        client=client, on_log=[].append, ngu=lambda s: None, ffmpeg="")
        luot = _luot(tmp_path, doan_lien)

        with pytest.raises(Exception, match="quá dài|too long"):
            ak._khau_giong_doc(bc)(luot, TrangThaiKhau(ma="giong_doc"))


class TestVietLaiDoanDocRaSoat:
    def test_loi_het_tien_di_xuyen_khong_bi_nuot(self, tmp_path):
        kenh = _kenh(voice_id="giong-goc")
        luot = _luot(tmp_path, "kịch bản không quan trọng ở bài này")

        def goi_chat(*a, **k):
            raise RuntimeError("Ví hết tiền, vui lòng nạp thêm để tiếp tục.")

        bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=goi_chat,
                        client=None, on_log=[].append, ngu=lambda s: None, ffmpeg="")

        with pytest.raises(RuntimeError, match="hết tiền"):
            ak._viet_lai_doan_doc(bc, luot, 1, "Đoạn gốc cần viết lại.", "content_rejected")

    def test_cancelled_di_xuyen_khong_bi_nuot(self, tmp_path):
        from core.auto import Cancelled

        kenh = _kenh(voice_id="giong-goc")
        luot = _luot(tmp_path, "kịch bản không quan trọng ở bài này")

        def goi_chat(*a, **k):
            raise Cancelled()

        bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=goi_chat,
                        client=None, on_log=[].append, ngu=lambda s: None, ffmpeg="")

        with pytest.raises(Cancelled):
            ak._viet_lai_doan_doc(bc, luot, 1, "Đoạn gốc cần viết lại.", "content_rejected")

    def test_loi_ai_thoang_qua_khac_van_bi_nuot_tra_rong(self, tmp_path):
        """Đối chứng: lỗi AI THƯỜNG (không phải hết tiền/Dừng) vẫn phải bị
        nuốt thành chuỗi rỗng như cũ — không được đổi hành vi cho ca này."""
        kenh = _kenh(voice_id="giong-goc")
        luot = _luot(tmp_path, "kịch bản không quan trọng ở bài này")

        def goi_chat(*a, **k):
            raise RuntimeError("máy chủ AI tạm gián đoạn")

        bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=goi_chat,
                        client=None, on_log=[].append, ngu=lambda s: None, ffmpeg="")

        ra = ak._viet_lai_doan_doc(bc, luot, 1, "Đoạn gốc cần viết lại.", "content_rejected")
        assert ra == ""

    def test_ai_tu_choi_viet_lai_khong_duoc_coi_la_da_sua(self, tmp_path):
        """Chính AI được nhờ viết lại đoạn cũng TỪ CHỐI — câu từ chối đó
        (dài hơn sàn "quá ngắn") không được coi là bản đã sửa, để không bị
        đọc thành giọng nói / ghi đè vào 1-kich-ban.txt."""
        kenh = _kenh(voice_id="giong-goc")
        luot = _luot(tmp_path, "kịch bản không quan trọng ở bài này")
        # Một đoạn ĐỌC thật thường dài cỡ vài trăm ký tự (một khúc TTS) — dài
        # hơn hẳn một câu từ chối ngắn của AI, nên tỉ lệ 30% của `la_cau_tu_
        # choi` mới có ý nghĩa. Đoạn quá ngắn thì câu từ chối có thể còn DÀI
        # HƠN cả 30% đoạn gốc, và phép so tỉ lệ không bắt được — đây không
        # phải điều bài kiểm này đang đo.
        doan_goc = ("Một đoạn văn kể chuyện khá dài, đủ để mô phỏng đúng một "
                    "khúc đọc thật trong khâu giọng đọc của tool. ") * 6

        def goi_chat(*a, **k):
            return ("Tôi không thể viết lại đoạn này vì nó vẫn mô tả nội dung "
                    "vi phạm chính sách dù đã cố diễn đạt gián tiếp hơn.")

        bc = ak.BoiCanh(goc=str(tmp_path), kenh=kenh, goi_chat=goi_chat,
                        client=None, on_log=[].append, ngu=lambda s: None, ffmpeg="")

        ra = ak._viet_lai_doan_doc(bc, luot, 1, doan_goc, "content_rejected")
        assert ra == ""


# ── 4) sổ cấp kênh: lượt SAU dùng ngay giọng dự phòng đã biết ───────────────


def test_luot_sau_cua_kenh_dung_ngay_giong_du_phong_da_biet(tmp_path):
    kenh = _kenh(voice_id="giong-goc", giong_du_phong="giong-du-phong")

    # Lượt 0001: giọng gốc bị khoá, tool tự đổi và ghi sổ cấp kênh.
    bc1, _dong1, client1 = _bc(tmp_path, kenh, giong_khoa={"giong-goc"})
    luot1 = _luot(tmp_path, "Đoạn ngắn cho lượt một.")
    ak._khau_giong_doc(bc1)(luot1, TrangThaiKhau(ma="giong_doc"))

    duong_so_kenh = os.path.join(str(tmp_path), "PROJECTS", "AUTO", "k1",
                                 ak.TEP_SO_KENH_GIONG)
    assert os.path.isfile(duong_so_kenh)
    so = json.load(open(duong_so_kenh, encoding="utf-8"))
    # RÀ SOÁT 28/09/2026: dòng sổ giờ có HẠN (`HAN_NGAY_GIONG_THAY_THE`), nên
    # không còn là chuỗi trần — câu báo "voice subscription required" khớp
    # `_CUM_KHOA_GOI_RO_RANG` ("trả phí"/"subscription"), ghi CHỐT ngay.
    assert so["giong_thay_the"]["giong-goc"]["giong_moi"] == "giong-du-phong"
    assert so["giong_thay_the"]["giong-goc"]["luc"] > 0

    # Lượt 0002 (kênh y hệt, vẫn khai voice_id="giong-goc"): phải dùng NGAY
    # giọng dự phòng — KHÔNG có lượt gọi nào bằng "giong-goc" nữa.
    bc2, dong2, client2 = _bc(tmp_path, kenh, giong_khoa={"giong-goc"})
    luot2_thu_muc = os.path.join(str(tmp_path), "PROJECTS", "AUTO", "k1", "0002")
    os.makedirs(luot2_thu_muc, exist_ok=True)
    with open(os.path.join(luot2_thu_muc, "1-kich-ban.txt"), "w",
              encoding="utf-8") as tep:
        tep.write("Đoạn ngắn cho lượt hai.")
    luot2 = LuotChay(ma_kenh="k1", ma_luot="0002", thu_muc=luot2_thu_muc)

    ak._khau_giong_doc(bc2)(luot2, TrangThaiKhau(ma="giong_doc"))

    ma_giong_da_goi = {g["voice_id"] for g in client2.goi}
    assert ma_giong_da_goi == {"giong-du-phong"}
    assert any("đã biết bị khoá ở lượt trước" in d for d in dong2)


# ── RÀ SOÁT 28/09/2026: sổ kênh có HẠN + chỉ chốt khi đủ chắc ───────────────
#
# Trước bản vá, MỘT lần "invalid_request" bất kỳ (kể cả câu mơ hồ như "voice
# not found" — có thể chỉ là gõ nhầm mã hay máy chủ đang đồng bộ danh mục)
# đã ghi sổ CẤP KÊNH VĨNH VIỄN. Giờ: câu RÕ RÀNG ("trả phí"/"subscription")
# vẫn chốt ngay; câu MƠ HỒ cần THẤY LẠI ở một lượt khác mới chốt; và mọi dòng
# đã chốt đều có HẠN (`HAN_NGAY_GIONG_THAY_THE` ngày).


class _TtsGiaKhongRo:
    """Máy chủ giả: lỗi giọng nhưng câu KHÔNG chứa "trả phí"/"subscription" —
    mô phỏng ca "voice not found" mơ hồ, có thể chỉ là trục trặc thoáng qua."""

    def __init__(self, giong_khoa=()):
        self.goi = []
        self.giong_khoa = set(giong_khoa)
        self.tts = self
        self.jobs = self

    def create(self, **kw):
        self.goi.append(kw)
        if kw.get("voice_id") in self.giong_khoa:
            from shopapi import InvalidRequestError

            raise InvalidRequestError(
                message="Giọng đọc voice_id không tồn tại.",
                code="invalid_request")
        return {"id": "job_{0}".format(len(self.goi)), "status": "succeeded",
                "outputs": [{"url": "http://x/a.mp3"}]}

    def retrieve(self, ma):  # pragma: no cover - job xong ngay lúc tạo
        raise AssertionError("không nên polling: job trả succeeded ngay")


def _bc_khong_ro(tmp_path, kenh: Kenh, giong_khoa=()) -> ak.BoiCanh:
    dong = []
    client = _TtsGiaKhongRo(giong_khoa=giong_khoa)
    return ak.BoiCanh(
        goc=str(tmp_path), kenh=kenh,
        goi_chat=lambda *a, **k: "",
        client=client, on_log=dong.append, ngu=lambda s: None,
        ffmpeg="",
    ), dong, client


def _luot_so(tmp_path, ma_luot: str, kich_ban: str) -> LuotChay:
    thu_muc = os.path.join(str(tmp_path), "PROJECTS", "AUTO", "k1", ma_luot)
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "1-kich-ban.txt"), "w", encoding="utf-8") as tep:
        tep.write(kich_ban)
    return LuotChay(ma_kenh="k1", ma_luot=ma_luot, thu_muc=thu_muc)


class TestSoKenhCanThayLaiTruocKhiChot:
    def test_mot_lan_cau_mo_ho_chua_du_de_chot_so(self, tmp_path):
        kenh = _kenh(voice_id="giong-goc", giong_du_phong="giong-du-phong")
        duong_so_kenh = os.path.join(str(tmp_path), "PROJECTS", "AUTO", "k1",
                                     ak.TEP_SO_KENH_GIONG)

        bc1, dong1, client1 = _bc_khong_ro(tmp_path, kenh, giong_khoa={"giong-goc"})
        luot1 = _luot_so(tmp_path, "0001", "Đoạn ngắn cho lượt một.")
        ak._khau_giong_doc(bc1)(luot1, TrangThaiKhau(ma="giong_doc"))

        so = json.load(open(duong_so_kenh, encoding="utf-8"))
        assert "giong-goc" not in (so.get("giong_thay_the") or {}), (
            "một lần 'không tồn tại' mơ hồ CHƯA đủ chắc để ghi sổ vĩnh viễn")
        assert so["cho_xac_nhan"]["giong-goc"]["giong_moi"] == "giong-du-phong"
        assert any("CHƯA ghi sổ kênh" in d for d in dong1)

        # Lượt 2 (kênh y hệt): CHƯA có shortcut — phải thử lại "giong-goc"
        # trước, đúng nết cũ, vì sổ chưa CHỐT.
        bc2, dong2, client2 = _bc_khong_ro(tmp_path, kenh, giong_khoa={"giong-goc"})
        luot2 = _luot_so(tmp_path, "0002", "Đoạn ngắn cho lượt hai.")
        ak._khau_giong_doc(bc2)(luot2, TrangThaiKhau(ma="giong_doc"))

        ma_giong_da_goi2 = {g["voice_id"] for g in client2.goi}
        assert "giong-goc" in ma_giong_da_goi2, (
            "chưa chốt sổ thì lượt sau vẫn phải thử lại giọng gốc trước")

        # Đúng cặp giọng này đã THẤY LẠI ở một lượt khác — giờ mới chốt.
        so2 = json.load(open(duong_so_kenh, encoding="utf-8"))
        assert so2["giong_thay_the"]["giong-goc"]["giong_moi"] == "giong-du-phong"

        # Lượt 3: giờ có shortcut, giống hệt ca "rõ ràng".
        bc3, dong3, client3 = _bc_khong_ro(tmp_path, kenh, giong_khoa={"giong-goc"})
        luot3 = _luot_so(tmp_path, "0003", "Đoạn ngắn cho lượt ba.")
        ak._khau_giong_doc(bc3)(luot3, TrangThaiKhau(ma="giong_doc"))

        ma_giong_da_goi3 = {g["voice_id"] for g in client3.goi}
        assert ma_giong_da_goi3 == {"giong-du-phong"}
        assert any("đã biết bị khoá ở lượt trước" in d for d in dong3)


class TestHanSoKenhGiongThayThe:
    def test_doc_tra_rong_khi_da_het_han(self, tmp_path):
        duong = os.path.join(str(tmp_path), ak.TEP_SO_KENH_GIONG)
        qua_han = time.time() - (ak.HAN_NGAY_GIONG_THAY_THE + 1) * 86400
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump({"giong_thay_the": {"giong-goc": {
                "giong_moi": "giong-cu-da-het-han", "luc": qua_han}}}, tep)
        assert ak._doc_giong_thay_the_kenh(duong, "giong-goc") == "", (
            "dòng đã QUÁ HẠN không được dùng nữa — khâu phải tự thử lại "
            "giọng gốc, biết đâu chủ giọng đã mở lại gói")

    def test_doc_tra_gia_tri_khi_con_han(self, tmp_path):
        duong = os.path.join(str(tmp_path), ak.TEP_SO_KENH_GIONG)
        con_han = time.time() - 1 * 86400
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump({"giong_thay_the": {"giong-goc": {
                "giong_moi": "giong-du-phong", "luc": con_han}}}, tep)
        assert ak._doc_giong_thay_the_kenh(duong, "giong-goc") == "giong-du-phong"

    def test_dong_so_kieu_cu_chuoi_tran_van_doc_duoc(self, tmp_path):
        """Sổ ghi TRƯỚC bản vá 28/09/2026 (chuỗi trần, không hạn) — vẫn đọc
        được, không vô hiệu hoá hàng loạt ngay lúc nâng cấp."""
        duong = os.path.join(str(tmp_path), ak.TEP_SO_KENH_GIONG)
        with open(duong, "w", encoding="utf-8") as tep:
            json.dump({"giong_thay_the": {"giong-goc": "giong-du-phong"}}, tep)
        assert ak._doc_giong_thay_the_kenh(duong, "giong-goc") == "giong-du-phong"


# ── 5) tự chọn giọng cùng ngôn ngữ + giới khi kênh không khai ───────────────


def _viet_kenh_yaml(goc: str, ma: str, ngon_ngu: str, voice_id: str,
                    gioi_nguoi_ke: str = "") -> None:
    thu_muc = os.path.join(goc, "CHANNEL", ma)
    os.makedirs(thu_muc, exist_ok=True)
    dong = ['ma: "{0}"'.format(ma), 'ngon_ngu: "{0}"'.format(ngon_ngu),
            'voice_id: "{0}"'.format(voice_id)]
    if gioi_nguoi_ke:
        dong.append('gioi_nguoi_ke: "{0}"'.format(gioi_nguoi_ke))
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write("\n".join(dong) + "\n")


class TestTuChonGiongDuPhong:
    def test_chon_giong_cung_ngon_ngu_va_gioi_tu_kenh_khac(self, tmp_path):
        goc = str(tmp_path)
        _viet_kenh_yaml(goc, "kenh-han-nu", "ko", "giong-han-nu", "nu")
        _viet_kenh_yaml(goc, "kenh-han-nam", "ko", "giong-han-nam", "nam")
        _viet_kenh_yaml(goc, "kenh-nhat", "ja", "giong-nhat", "")

        chon = ak._chon_giong_du_phong_tu_dong(goc, "ko", "nam")
        assert chon == "giong-han-nam"

    def test_khong_khai_gioi_thi_khong_doan_bua_gioi_cua_ung_vien(self, tmp_path):
        goc = str(tmp_path)
        # Kênh tiếng Hàn duy nhất KHÔNG khai giới — không được coi là khớp
        # khi đang cần đúng giới "nam".
        _viet_kenh_yaml(goc, "kenh-han", "ko", "giong-han", "")

        chon = ak._chon_giong_du_phong_tu_dong(goc, "ko", "nam")
        assert chon == ""

    def test_khong_co_ung_vien_hop_thi_tra_rong(self, tmp_path):
        goc = str(tmp_path)
        _viet_kenh_yaml(goc, "kenh-nhat", "ja", "giong-nhat", "nam")
        assert ak._chon_giong_du_phong_tu_dong(goc, "ko", "nam") == ""

    def test_loai_tru_giong_da_thu(self, tmp_path):
        goc = str(tmp_path)
        _viet_kenh_yaml(goc, "kenh-han-a", "ko", "giong-a", "nu")
        _viet_kenh_yaml(goc, "kenh-han-b", "ko", "giong-b", "nu")
        chon = ak._chon_giong_du_phong_tu_dong(
            goc, "ko", "nu", giong_loai_tru=["giong-a"])
        assert chon == "giong-b"

    def test_tieng_viet_uu_tien_VOICE_CATALOG_cua_sdk(self, tmp_path):
        from shopapi import VOICE_CATALOG

        goc = str(tmp_path)
        # Không có kênh nào khác trong CHANNEL/ — chỉ còn nguồn SDK.
        chon = ak._chon_giong_du_phong_tu_dong(goc, "vi", "nu")
        ma_nu = {g["id"] for g in VOICE_CATALOG if g.get("gender") == "female"}
        assert chon in ma_nu

    def test_khong_gioi_thi_khong_doan_khi_ung_vien_cung_khong_khai_gioi(self, tmp_path):
        """RÀ SOÁT 28/09/2026: kênh CẦN giọng dự phòng không khai giới người
        kể, và ứng viên duy nhất CŨNG không khai giới — hai cái không biết
        cộng lại không phải bằng chứng, không được đoán bừa. Trước bản vá,
        "không giới thì chỉ cần đúng ngôn ngữ" trả thẳng "giong-han", có thể
        ra một giọng khác hẳn giới người kể thật của kênh."""
        goc = str(tmp_path)
        _viet_kenh_yaml(goc, "kenh-han", "ko", "giong-han", "")
        assert ak._chon_giong_du_phong_tu_dong(goc, "ko", "") == ""

    def test_khong_gioi_van_nhan_ung_vien_da_khai_ro_gioi_cua_no(self, tmp_path):
        """Không biết giới CỦA KÊNH ĐANG CẦN, nhưng ứng viên (một kênh KHÁC,
        cùng ngôn ngữ) đã khai rõ giới người kể của CHÍNH NÓ — ứng viên có
        nguồn gốc rõ ràng, không phải đoán mù, nên được chấp nhận."""
        goc = str(tmp_path)
        _viet_kenh_yaml(goc, "kenh-han", "ko", "giong-han", "nam")
        assert ak._chon_giong_du_phong_tu_dong(goc, "ko", "") == "giong-han"

    def test_khong_gioi_thi_khong_dung_VOICE_CATALOG_dau_danh_muc(self, tmp_path):
        """RÀ SOÁT 28/09/2026: kênh tiếng Việt không khai giới — không được
        lấy giọng ĐẦU DANH MỤC `VOICE_CATALOG` bất kể giới. Không có kênh
        nào khác trong tool để đối chiếu → phải trả rỗng, không đoán."""
        goc = str(tmp_path)
        assert ak._chon_giong_du_phong_tu_dong(goc, "vi", "") == ""


# ── Kenh.giong_du_phong: khoá mới trong lược đồ (không đụng CHANNEL/*.yaml) ──


def test_kenh_co_khoa_giong_du_phong_va_doc_duoc_tu_yaml(tmp_path):
    from core.kenh import doc_kenh

    goc = str(tmp_path)
    thu_muc = os.path.join(goc, "CHANNEL", "kx")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write('ma: "kx"\nvoice_id: "a"\ngiong_du_phong: "b"\n')
    k = doc_kenh(goc, "kx")
    assert k.giong_du_phong == "b"


def test_kenh_khong_khai_giong_du_phong_mac_dinh_rong(tmp_path):
    from core.kenh import doc_kenh

    goc = str(tmp_path)
    thu_muc = os.path.join(goc, "CHANNEL", "ky")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "kenh.yaml"), "w", encoding="utf-8") as tep:
        tep.write('ma: "ky"\nvoice_id: "a"\n')
    k = doc_kenh(goc, "ky")
    assert k.giong_du_phong == ""


def test_khong_dung_CHANNEL_yaml_co_san(tmp_path):
    """Yêu cầu bắt buộc: KHÔNG sửa các `CHANNEL/*.yaml` có sẵn của kho —
    `git status` không được thấy tệp nào dưới `CHANNEL/` bị đổi bởi bài kiểm
    này (bài kiểm này chỉ dùng `tmp_path`, không đụng `CHANNEL/` thật)."""
    goc_that = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    duong = os.path.join(goc_that, "CHANNEL", "story-dien-anh-han", "kenh.yaml")
    truoc = open(duong, encoding="utf-8").read()
    assert "giong_du_phong" not in truoc, (
        "kênh mẫu có sẵn không được tự thêm khoá mới — chỉ thêm vào lược đồ")


# ── UI: ô chọn giọng dự phòng trong Cài đặt kênh (đọc nguồn, không dựng Qt) ──


class TestUiCaiDatKenh:
    def test_trang_giong_co_o_chon_giong_du_phong(self):
        import inspect

        import ui_qt.kenh as uk

        ma = inspect.getsource(uk.HopKenh._trang_giong)
        assert "_o_giong_du_phong" in ma
        assert "QLineEdit" in ma

    def test_giong_du_phong_duoc_ghi_xuong_yaml(self):
        import inspect

        import ui_qt.kenh as uk

        ma = inspect.getsource(uk.HopKenh._ghi_de_kenh_yaml)
        assert '"giong_du_phong"' in ma

    def test_giong_du_phong_duoc_nap_lai_khi_sua_kenh(self):
        import inspect

        import ui_qt.kenh as uk

        ma = inspect.getsource(uk.HopKenh._dung_sua)
        assert "_o_giong_du_phong.setText(self._kenh.giong_du_phong)" in ma

    def test_huong_dan_co_nhac_giong_du_phong(self):
        from ui_qt.huong_dan import HUONG_DAN

        chu = " ".join(HUONG_DAN["quan-ly-kenh"].get("luu_y", []))
        assert "Giọng dự phòng" in chu or "giọng dự phòng" in chu

    # ── RÀ SOÁT 28/09/2026: hiện + gỡ giọng thay thế đang dùng ──────────────

    def test_trang_giong_co_nhan_va_nut_bo_giong_thay_the(self):
        import inspect

        import ui_qt.kenh as uk

        ma = inspect.getsource(uk.HopKenh._trang_giong)
        assert "_o_giong_thay_the_hien_tai" in ma
        assert "_nut_bo_giong_thay_the" in ma
        assert "Bỏ giọng thay thế" in ma

    def test_dung_sua_goi_cap_nhat_giong_thay_the(self):
        import inspect

        import ui_qt.kenh as uk

        ma = inspect.getsource(uk.HopKenh._dung_sua)
        assert "_cap_nhat_giong_thay_the_hien_tai()" in ma

    def test_cap_nhat_giong_thay_the_doc_dung_so_cap_kenh(self):
        import inspect

        import ui_qt.kenh as uk

        ma = inspect.getsource(uk.HopKenh._cap_nhat_giong_thay_the_hien_tai)
        assert "_doc_giong_thay_the_kenh" in ma
        assert "self._kenh.voice_id" in ma

    def test_bo_giong_thay_the_xoa_dung_khoa_khong_dung_kenh_yaml(self):
        import inspect

        import ui_qt.kenh as uk

        ma = inspect.getsource(uk.HopKenh._bo_giong_thay_the)
        assert "giong_thay_the" in ma
        assert "ghi_json" in ma
        assert "_ghi_de_kenh_yaml" not in ma
        assert "_cap_nhat_giong_thay_the_hien_tai()" in ma
