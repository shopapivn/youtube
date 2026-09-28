"""Bài kiểm gói G5: bọc chuỗi 6 nấc của `tao_tham_chieu` bằng sổ (`SoCuu`).

docs/THIET-KE-XU-LY-TU-CHOI-NOI-DUNG.md, mục 2.5 (chuỗi cứu ảnh tham chiếu) +
mục 3.1 (bảng gói G5). Ba điều bắt buộc, không gọi mạng:

1. Bấm Dừng (`Cancelled`) hoặc hết tiền giữa lúc tạo tham chiếu — kể cả giữa
   chuỗi 6 nấc — phải đi XUYÊN QUA: không chạy nấc sau, không gọi
   `_bo_id_khoi_canh`.
2. Mỗi nấc đã chạy có đúng một dòng `[CỨU]`.
3. Nhân vật có ảnh tham chiếu bị từ chối được ghi `nguy_co: mat_that` vào sổ
   `tu-choi.json` của lượt — để khâu ảnh/khâu clip (gói G3/G4) đọc lại.
"""
from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from core import dao_dien_auto as dd
from core.auto import Cancelled
from core.prompt_visuals import DUOI_CHAN_DUNG


def _bc(tmp_path):
    nhat_ky = []
    kenh = SimpleNamespace(ma="story-3d", che_do_ke="tu_xay", engine="veo3",
                           mo_hinh="claude-sonnet-5", style={}, anh_nv=[])
    return SimpleNamespace(goc=str(tmp_path), kenh=kenh, client=object(),
                           ghi=nhat_ky.append, _nhat_ky=nhat_ky)


def _luot(tmp_path):
    return SimpleNamespace(thu_muc=str(tmp_path / "0001"), ma_luot="0001", ma_kenh="story-3d")


def _doc_so(luot):
    with open(os.path.join(luot.thu_muc, "tu-choi.json"), encoding="utf-8") as f:
        return json.load(f)


class TestHuyVaHetTienDiXuyen:
    def test_cancelled_o_lan_dau_khong_chay_thiet_ke_lai(self, tmp_path, monkeypatch):
        """Bấm Dừng ngay khi đang vẽ (chưa kịp vào chuỗi cứu) — không được
        chạy thiết kế lại lẫn `_bo_id_khoi_canh`."""
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv1", "sheet_prompt": "a cat"}], "locations": []}

        goi_thiet_ke = []
        monkeypatch.setattr(dd, "_thiet_ke_lai_va_tao_lai",
                            lambda *a, **k: goi_thiet_ke.append(1) or False)
        goi_bo_id = []
        monkeypatch.setattr(dd, "_bo_id_khoi_canh", lambda *a, **k: goi_bo_id.append(1))

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            raise Cancelled()

        with pytest.raises(Cancelled):
            dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh, goi_ai=lambda l: "x")
        assert goi_thiet_ke == [], "bấm Dừng rồi thì không được chạy thiết kế lại"
        assert goi_bo_id == [], "bấm Dừng rồi thì không được bỏ id khỏi cảnh"

    def test_cancelled_giua_chuoi_6_nac_khong_chay_nac_sau(self, tmp_path, monkeypatch):
        """Nhân vật đã bị từ chối lần đầu (vào chuỗi cứu) — Dừng xảy ra NGAY ở
        nấc 1 (thiết kế lại) — không được chạy nấc 2 trở đi."""
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv1", "sheet_prompt": "a cat"}], "locations": []}

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            raise RuntimeError("content_rejected")

        def thiet_ke_lai_huy(*a, **k):
            raise Cancelled()

        monkeypatch.setattr(dd, "_thiet_ke_lai_va_tao_lai", thiet_ke_lai_huy)
        goi_nac2 = []
        monkeypatch.setattr(dd, "_muon_anh_giai_doan", lambda *a, **k: goi_nac2.append(1) or False)
        goi_bo_id = []
        monkeypatch.setattr(dd, "_bo_id_khoi_canh", lambda *a, **k: goi_bo_id.append(1))

        with pytest.raises(Cancelled):
            dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh, goi_ai=lambda l: "x")
        assert goi_nac2 == [], "Dừng ở nấc 1 thì nấc 2 không được chạy"
        assert goi_bo_id == []

    def test_het_tien_o_lan_dau_di_xuyen_khong_bo_id(self, tmp_path, monkeypatch):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv1", "sheet_prompt": "a cat"}], "locations": []}
        goi_bo_id = []
        monkeypatch.setattr(dd, "_bo_id_khoi_canh", lambda *a, **k: goi_bo_id.append(1))

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            raise RuntimeError("hết tiền")

        with pytest.raises(RuntimeError, match="hết tiền"):
            dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh, goi_ai=lambda l: "x")
        assert goi_bo_id == []
        assert not any("KHÔNG tạo được" in x for x in bc._nhat_ky), \
            "hết tiền không phải 'không tạo được vì nội dung'"

    def test_het_tien_giua_mot_nac_di_xuyen(self, tmp_path, monkeypatch):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv1", "sheet_prompt": "a cat"}], "locations": []}

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            raise RuntimeError("content_rejected")

        def het_tien(*a, **k):
            raise RuntimeError("không đủ số dư")

        monkeypatch.setattr(dd, "_thiet_ke_lai_va_tao_lai", het_tien)
        goi_nac2 = []
        monkeypatch.setattr(dd, "_muon_anh_giai_doan", lambda *a, **k: goi_nac2.append(1) or False)

        with pytest.raises(RuntimeError, match="không đủ số dư"):
            dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh, goi_ai=lambda l: "x")
        assert goi_nac2 == []


class TestMoiNacCoDongCuu:
    def _man_soi(self):
        return {"characters": [
            {"id": "nv5", "role": "villain", "english_prompt": "a grey wolf",
             "sheet_prompt": "a grey wolf" + DUOI_CHAN_DUNG},
            {"id": "nv5b", "role": "villain", "english_prompt": "a grey wolf, white paws",
             "sheet_prompt": "a grey wolf, white paws" + DUOI_CHAN_DUNG}],
            "locations": []}

    def test_nac_hong_va_nac_xong_deu_co_dong_cuu(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = self._man_soi()

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            if ma_id == "nv5":
                raise RuntimeError("content_rejected")
            open(dich, "wb").write(b"png")

        thieu = dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh,
                                  goi_ai=lambda l: "không có json")
        assert thieu == []
        # Nấc 1 (thiết kế lại) không qua vì goi_ai không trả JSON hợp lệ.
        assert any("[CỨU] tham chiếu nv5 · thiet_ke_lai → chưa qua" in d for d in bc._nhat_ky), bc._nhat_ky
        # Nấc 2 (mượn ảnh giai đoạn anh em) cứu được.
        assert any("[CỨU] tham chiếu nv5 · muon_giai_doan → XONG" in d for d in bc._nhat_ky), bc._nhat_ky
        # Nấc 3+ không chạy nữa vì đã cứu xong ở nấc 2.
        assert not any("khong_quan_ao" in d for d in bc._nhat_ky if "[CỨU]" in d)

    def test_het_ca_6_nac_van_moi_nac_mot_dong(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv1", "role": "hero", "english_prompt": "a cat",
                               "sheet_prompt": "a cat" + DUOI_CHAN_DUNG}],
               "locations": []}

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            raise RuntimeError("content_rejected")

        thieu = dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh,
                                  goi_ai=lambda l: "không có json")
        assert thieu == ["nv1"]
        for ten_nac in ("thiet_ke_lai", "muon_giai_doan", "khong_quan_ao", "toi_gian", "muon_khuon"):
            assert any("[CỨU] tham chiếu nv1 · {0} →".format(ten_nac) in d for d in bc._nhat_ky), \
                (ten_nac, bc._nhat_ky)
        assert any("[DỪNG] tham chiếu nv1 · hết 6 nấc cứu" in d for d in bc._nhat_ky)


class TestGhiNguyCoNhanVatVaoSo:
    def test_nhan_vat_bi_tu_choi_ghi_vao_so_khong_phai_boi_canh(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv1", "sheet_prompt": "a cat"},
                              {"id": "nv2", "sheet_prompt": "a king"}],
               "locations": [{"id": "loc1", "sheet_prompt": "a mill"}]}

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            raise RuntimeError("content_rejected")

        thieu = dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh,
                                  goi_ai=lambda l: "không có json")
        assert sorted(thieu) == ["loc1", "nv1", "nv2"]

        so = _doc_so(luot)
        assert set(so["nhan_vat"]) == {"nv1", "nv2"}, "bối cảnh (loc1) không phải nhân vật"
        for ma_id in ("nv1", "nv2"):
            assert so["nhan_vat"][ma_id]["nguy_co"] == "mat_that"

    def test_canh_dung_nhan_vat_duoc_ghi_vao_nguy_co(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv1", "sheet_prompt": "a cat"}], "locations": []}
        canh = [{"scene_id": 7, "characters_used": "nv1"},
                {"scene_id": 9, "characters_used": "nv1, nv2"}]

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            raise RuntimeError("content_rejected")

        dd.tao_tham_chieu(bc, luot, man, canh=canh, tao_anh=tao_anh,
                          goi_ai=lambda l: "không có json")
        so = _doc_so(luot)
        assert so["nhan_vat"]["nv1"]["canh"] == [7, 9]

    def test_nhan_vat_duoc_cuu_van_khong_ghi_khi_khong_tung_bi_tu_choi(self, tmp_path):
        """Nhân vật vẽ được ngay lần đầu — chưa từng vào sổ `nhan_vat`."""
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv1", "sheet_prompt": "a cat"}], "locations": []}

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            open(dich, "wb").write(b"png")

        assert dd.tao_tham_chieu(bc, luot, man, tao_anh=tao_anh) == []
        assert not os.path.exists(os.path.join(luot.thu_muc, "tu-choi.json"))


class TestSoCuuDaTruyenVao:
    def test_dung_so_cuu_duoc_truyen_vao_thay_vi_tu_dung(self, tmp_path):
        """`so_cuu` truyền sẵn (đường thật của một khâu dùng chung sổ cả lượt)
        thì `tao_tham_chieu` phải dùng đúng cái đó, không tự dựng cái khác."""
        from core.tu_choi_noi_dung import SoCuu

        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv1", "sheet_prompt": "a cat"}], "locations": []}
        duong = os.path.join(luot.thu_muc, "so-rieng.json")
        so_cuu = SoCuu(duong_tep=duong, on_log=bc.ghi)

        def tao_anh(ma_id, prompt, dich, tham_chieu=None):
            raise RuntimeError("content_rejected")

        dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh,
                          goi_ai=lambda l: "không có json", so_cuu=so_cuu)
        assert os.path.isfile(duong), "phải ghi vào ĐÚNG sổ được truyền vào"
        assert not os.path.exists(os.path.join(luot.thu_muc, "tu-choi.json"))
