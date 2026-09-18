"""Thẩm định Công thức V7 bằng AI (`core/cong_thuc_v7_ai.py`) — AI giả, không gọi mạng, không tốn tiền.

Chủ dự án, 18/09/2026: *"bản chất tool có API mà sao không kết hợp để số liệu chuẩn"*. AI chỉ thay bốn phán
đoán mà từ khoá làm kém (cụm, dạng, tệp tuổi, trùng đề tài); số đo giữ nguyên. Bộ test chốt:

- chỉ gửi nhóm đầu bảng, lô 20, nhớ kết quả, bấm lại không gọi lại;
- lô hỏng không giết cả lượt;
- kết quả AI thật sự đổi điểm: trùng đề tài bị trừ, nhắm người lớn tuổi bị loại, "cách làm" mất điểm khuôn;
- kênh đăng thêm video / đổi danh sách cụm thì phải hỏi lại;
- kênh còn thiếu trong sổ lấy đúng từ bảng đề xuất, không trùng hộp thư.
"""

from __future__ import annotations

import io
import json
import os
import re

import pytest

from core import cong_thuc_v7 as v7
from core import cong_thuc_v7_ai as ai
from core import doi_thu_kenh as so

from test_cong_thuc_v7 import (  # noqa: E402 — thư mục tests/ nằm sẵn trong sys.path
    A, BAY_GIO, C, KENH, W1, W2, _ghi, _raw_join, dung_kenh,
)

T = "trungV7xxxx"    # cùng luận điểm với V7 đã đăng
OLD = "lonTuoi0001"  # nhắm người lớn tuổi nhưng không có chữ khoá tuổi nào


def _them_ung_vien(goc):
    cot, hang = so.doc_bang(goc, KENH)
    for ma, kenh, td, view, tang, dai in (
            (T, "強者が隠す真実", "【脳科学】「これ」を一人でやれる人は高IQの可能性があります", "66000", "3000", "20:29"),
            (OLD, "お金の心理", "お金に困らない人が人生の最終章で静かにしていること", "150000", "2500", "18:00")):
        d = dict.fromkeys(cot, "")
        d.update({"Kênh": kenh, "Tiêu đề video": td, "Link video": "https://www.youtube.com/watch?v=" + ma,
                  "View": view, so.COT_TANG: tang, "Thời lượng": dai})
        hang.append([d[c] for c in cot])
    so.luu_bang(goc, KENH, cot, hang)


class AIGia:
    """Trả lời như AI thật: đọc các dòng "n. tiêu đề", phán theo nội dung tiêu đề."""

    def __init__(self, hong_lan=()):
        self.lan = 0
        self.gui = []
        self.hong_lan = set(hong_lan)

    def phan(self, td):
        m = {"cum": "moi", "dang": "chan-dung", "tep": "chung", "trung": 0, "trung_voi": "", "ly_do": "ok"}
        if "物欲" in td or "金持ち" in td or "お金" in td or "掃除" in td:
            m["cum"] = "vat-chat"
        if "IQ" in td or "知能" in td:
            m["cum"] = "tri-tue"
        if "方法" in td:
            m["dang"] = "cach-lam"
        if "高IQ" in td:
            m.update(trung=85, trung_voi=W2)
        if "最終章" in td:
            m["tep"] = "lon-tuoi"
        return m

    def __call__(self, client, tin_nhan, **kw):
        self.lan += 1
        if self.lan in self.hong_lan:
            raise RuntimeError("máy chủ trả rỗng")
        dong = re.findall(r"^(\d+)\. (.*)$", tin_nhan[-1]["content"], re.M)
        self.gui.extend(td for _n, td in dong)
        return "```json\n" + json.dumps({n: self.phan(td) for n, td in dong}, ensure_ascii=False) + "\n```"


@pytest.fixture
def kenh(tmp_path):
    goc = dung_kenh(tmp_path)
    _them_ung_vien(goc)
    return goc


def _cham(goc):
    return v7.cham(goc, KENH, bay_gio=BAY_GIO)


def test_uoc_luot_va_chi_gui_mot_lan(kenh):
    kq = _cham(kenh)
    so_tieu_de, luot = ai.uoc_luot(kenh, KENH, kq)
    assert so_tieu_de > 0 and luot == -(-len([v for v in kq.video_minh if v.tieu_de]) // 20) + 1
    goi = AIGia()
    assert ai.tham_dinh(object(), kenh, KENH, kq, goi=goi) == so_tieu_de
    assert goi.lan == luot
    kq2 = _cham(kenh)
    assert ai.uoc_luot(kenh, KENH, kq2) == (0, 0), "đã nhớ thì không tốn lượt nào nữa"
    goi2 = AIGia()
    assert ai.tham_dinh(object(), kenh, KENH, kq2, goi=goi2) == 0 and goi2.lan == 0


def test_ket_qua_ai_doi_diem_that(kenh):
    truoc = {d.ma: d for d in _cham(kenh).ung_vien}
    assert truoc[T].trung == 0 and OLD in truoc
    ai.tham_dinh(object(), kenh, KENH, _cham(kenh), goi=AIGia())
    kq = _cham(kenh)
    sau = {d.ma: d for d in kq.ung_vien}
    loai = {d.ma: d.bi_loai for d in kq.bi_loai}
    # trùng đề tài với V7 → trừ 20 và có lý do
    assert sau[T].nguon_danh_gia == v7.NGUON_AI and sau[T].trung == 85
    assert sau[T].diem <= truoc[T].diem - 20 + 1
    assert any("trùng đề tài" in x for x in sau[T].ly_do)
    # nhắm người lớn tuổi mà không có chữ khoá → AI loại
    assert loai.get(OLD) == "AI: nhắm người lớn tuổi"
    # "cách làm" mất điểm khuôn dạng
    assert sau[C].dang == "cach-lam" and sau[C].diem_khuon <= 5
    # số đo không đổi
    assert sau[A].view == truoc[A].view and sau[A].diem_pool == truoc[A].diem_pool
    assert kq.ung_vien[0].ma == A


def test_lo_hong_khong_giet_ca_luot(kenh, monkeypatch):
    monkeypatch.setattr(ai, "SO_MOI_LO", 2)
    kq = _cham(kenh)
    goi = AIGia(hong_lan={1})
    nhan = ai.tham_dinh(object(), kenh, KENH, kq, goi=goi, on_log=lambda _d: None)
    so_tieu_de, _ = ai.uoc_luot(kenh, KENH, kq)
    assert nhan > 0 and so_tieu_de == 2, "lô hỏng để lại đúng 2 tiêu đề chưa thẩm định, lô khác vẫn ghi"


def test_dang_them_video_thi_hoi_lai_ung_vien(kenh):
    ai.tham_dinh(object(), kenh, KENH, _cham(kenh), goi=AIGia())
    moi = os.path.join(kenh, "CHANNEL", KENH, "chi-so", "newVIDEO001")
    _ghi(os.path.join(moi, "13h", "_thong-tin.json"),
         json.dumps({"tieu_de": "新しい動画", "ngay_dang": "2026-09-17T01:00:00.000Z"}))
    _ghi(os.path.join(moi, "13h", "tong-quan.json"), json.dumps({"impressions": 100}))
    kq = _cham(kenh)
    minh, ung = ai.can_tham_dinh(kenh, KENH, kq.ung_vien, kq.video_minh, kq.cau_hinh)
    assert [m for m, _t in minh] == ["newVIDEO001"], "video mình cũ vẫn nhớ, chỉ video mới cần gửi"
    assert ung, "ứng viên phải so trùng lại với video vừa đăng"
    assert all(d.nguon_danh_gia == v7.NGUON_TU_KHOA for d in kq.ung_vien), "chưa so lại thì không dùng kết quả cũ"


def test_doi_danh_sach_cum_thi_ket_qua_cu_het_hieu_luc(kenh):
    ai.tham_dinh(object(), kenh, KENH, _cham(kenh), goi=AIGia())
    ch, duong = v7.nap_cau_hinh(kenh, KENH)
    ch["cum"]["suc-khoe"] = {"ten": "Sức khoẻ", "tu": ["健康"]}
    with io.open(duong, "w", encoding="utf-8") as tep:
        json.dump(ch, tep, ensure_ascii=False)
    assert ai.uoc_luot(kenh, KENH, _cham(kenh))[0] > 0


def test_ai_tra_loi_sai_dang_thi_bo_qua_khong_doan(kenh):
    kq = _cham(kenh)
    nhan = ai.tham_dinh(object(), kenh, KENH, kq, goi=lambda *a, **k: "xin lỗi, tôi không hiểu", on_log=lambda _d: None)
    assert nhan == 0 and v7.doc_bo_nho(kenh, KENH, kq.cau_hinh) == {}


def test_doc_ket_qua_chuan_hoa_gia_tri_la():
    ch = v7.CAU_HINH_MAC_DINH
    ra = ai._doc_ket_qua('{"1": {"cum": "khong-co", "dang": "x", "tep": "y", "trung": "120", "trung_voi": "la"},'
                         ' "9": {"cum": "tri-tue"}}', 2, ch, [W1])
    assert ra == {0: {"cum": "moi", "dang": "khac", "tep": "chung", "trung": 0, "trung_voi": "", "ly_do": ""}}


def test_de_bai_co_cum_video_minh_va_dinh_nghia(kenh):
    kq = _cham(kenh)
    de = ai.de_bai(kq.cau_hinh, kq.video_minh, "người 25–45 sống lệch nhịp")
    assert "vat-chat" in de and W1 in de and "lon-tuoi" in de and "người 25–45" in de


# ── MỘT NÚT chạy luôn V7 ─────────────────────────────────────────────────────

def test_mot_nut_cham_v7_co_ai_va_bao_cao(kenh):
    """18/09/2026: *"chạy một nút thì mọi thứ sau khi xong v7 cũng phải có số liệu đủ và chuẩn"*."""
    from core import mot_nut

    bc = mot_nut.BaoCao()
    nhat_ky = []
    goi = AIGia()
    mot_nut._cham_v7(kenh, KENH, bc, object(), goi, nhat_ky.append)
    assert goi.lan > 0 and bc.v7["ai"] > 0
    assert bc.v7["lam_ngay"] >= 1 and bc.v7["top"][0].startswith("【雑学】昔より物欲が減った人の心理")
    assert "V7: Làm ngay" in bc.tom_tat()
    assert os.path.isfile(os.path.join(so.thu_muc_nghien_cuu(kenh, KENH), "v7-tham-dinh.json"))
    goi2 = AIGia()
    mot_nut._cham_v7(kenh, KENH, mot_nut.BaoCao(), object(), goi2, nhat_ky.append)
    assert goi2.lan == 0, "lượt MỘT NÚT hôm sau không trả tiền lại cho tiêu đề đã thẩm định"


def test_mot_nut_khong_vi_thi_khong_goi_ai(kenh):
    from core import mot_nut

    bc = mot_nut.BaoCao()
    mot_nut._cham_v7(kenh, KENH, bc, None, None, lambda _d: None)
    assert "ai" not in bc.v7 and bc.v7["top"]


# ── kênh còn thiếu ───────────────────────────────────────────────────────────

def test_kenh_con_thieu_va_hop_thu(kenh):
    tm = v7.thu_muc_chi_so(kenh, KENH)
    raw = _raw_join(W1, [(A, 50, 9.0, 8, 400000, "昔より物欲が減った人の心理"),
                         ("newMONEY001", 40, 10.0, 7, 380000, "お金持ちが絶対にしない習慣"),
                         ("newMONEY002", 30, 9.0, 3, 380000, "貧乏な人がやりがちなこと"),
                         ("newOLD00001", 60, 9.0, 9, 380000, "60代でお金に困らない人"),
                         ("newNEWS0001", 60, 9.0, 9, 380000, "ニュース速報")],
                    kenh_id={A: "UCdaTheoDoi", "newMONEY001": "UCmoi111", "newMONEY002": "UCmoi111",
                             "newOLD00001": "UCgia", "newNEWS0001": "UCtin"})
    _ghi(os.path.join(tm, W1, "tay-20260917", "raw", "x_reach_viewers_join_1.json"), json.dumps(raw))
    ra = v7.kenh_con_thieu(kenh, KENH, bay_gio=BAY_GIO)
    assert [(link, xem) for link, xem, _td in ra] == [("https://www.youtube.com/channel/UCmoi111", 10.0)], ra
    assert v7.them_vao_hop_thu(kenh, KENH, [r[0] for r in ra]) == 1
    assert v7.them_vao_hop_thu(kenh, KENH, [r[0] for r in ra]) == 0, "đã có trong hộp thư thì không thêm dòng"
    assert so.doc_ban_dua(kenh, KENH) == [], "kênh máy tìm không được ghi như kênh khách tự đưa"
