"""Ghi khuôn — tạo và sửa các mảnh khuôn từ trong tool.

`core/khuon.py` chỉ ĐỌC khuôn; `core/soan_khuon.py` là phần GHI. Phép kiểm quan
trọng nhất ở đây: một bộ vừa ghi ra phải **dựng được kênh chạy ngay** —
`kiem_kenh` im lặng. Nếu không thì trình sửa khuôn chỉ đẻ ra khuôn hỏng, tệ hơn
là bắt người dùng gõ YAML tay.

Hai luật của `core/khuon.py` phải giữ nguyên và được kiểm lại ở đây: **một khoá
một dòng** (máy chưa cài PyYAML vẫn đọc đúng) và **chặn khoá API** trước khi ghi.

Không gọi mạng, không tốn một đồng nào.
"""

from __future__ import annotations

import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kenh import (  # noqa: E402
    doc_kenh, doc_yaml, duong_kenh, kiem_kenh, liet_ke_kenh,
)
from core.khuon import (  # noqa: E402
    KHOA_VAN_HOA, KHOA_VE, THU_MUC_KHUON, LoiKhuon, dung_kenh, duong_khuon,
    liet_ke_nganh, liet_ke_van_hoa, liet_ke_ve,
)
from core.soan_khuon import (  # noqa: E402
    ghi_chien_luoc, ghi_nganh, ghi_van_hoa, ghi_ve, kiem_ma_bo, xoa_bo,
)

KHO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NGANH, VE, VAN_HOA = "tam-ly", "ao-len-than", "vi"


@pytest.fixture
def goc(tmp_path):
    """Thư mục gốc giả với khuôn thật chép vào — mỗi phép kiểm một bản riêng.

    Function-scope chứ không module-scope: các phép kiểm ở đây GHI vào khuôn,
    dùng chung một bản là chúng dẫm chân nhau.
    """
    d = str(tmp_path / "goc")
    shutil.copytree(os.path.join(KHO, "CHANNEL", THU_MUC_KHUON),
                    os.path.join(d, "CHANNEL", THU_MUC_KHUON))
    return d


@pytest.fixture
def anh(tmp_path):
    """Một tệp .png giả để làm nhân vật mẫu."""
    p = tmp_path / "nv.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"anh mau")
    return str(p)


def _ve_hop_le():
    d = {k: "x" for k in KHOA_VE}
    d["ten"] = "Nét thử"
    d["mo_ta"] = "Bộ vẽ dựng cho phép kiểm."
    return d


def _van_hoa_hop_le():
    d = {k: "x" for k in KHOA_VAN_HOA}
    d.update(ten="Tiếng thử", ngon_ngu="th",
             giong_van="Thtest voice", ky_tu_moi_phut=700, chu_bia_hoa=True)
    return d


def _nganh_hop_le():
    return dict(ten="Ngách thử", mo_ta="Ngách dựng cho phép kiểm.",
                phut_muc_tieu=8, engine="veo3", so_thumbnail=3,
                mo_hinh="claude-sonnet-5", dot_phu_de=True, am_luong_nhac=0.12)


_PROMPTS = {"2-viet.md": "Viet kich ban tu tieu de: <<TITLE>>\n",
            "7-canh.md": "Chia canh cho kich ban.\n"}


# ── Ghi xong là dựng được kênh chạy ngay ─────────────────────────────────────


class TestGhiRoiDungKenh:
    def test_ghi_ba_manh_moi_roi_dung_kenh_im_lang(self, goc, anh):
        """Đích cuối: ba bộ vừa ghi ghép lại thành kênh mà `kiem_kenh` không kêu."""
        ghi_ve(goc, "net-moi", _ve_hop_le(), anh_nv_nguon=anh)
        ghi_van_hoa(goc, "tieng-moi", _van_hoa_hop_le())
        ghi_nganh(goc, "nganh-moi", _nganh_hop_le(), _PROMPTS)

        assert any(b.ma == "net-moi" for b in liet_ke_ve(goc))
        assert any(b.ma == "tieng-moi" for b in liet_ke_van_hoa(goc))
        assert any(b.ma == "nganh-moi" for b in liet_ke_nganh(goc))

        dung_kenh(goc, "K-MOI", ma_nganh="nganh-moi", ma_ve="net-moi",
                  ma_van_hoa="tieng-moi", voice_id="giong-thu")
        assert kiem_kenh(doc_kenh(goc, "K-MOI")) == []

    def test_bo_van_hoa_moi_giu_dung_ky_tu_moi_phut(self, goc):
        d = _van_hoa_hop_le()
        d["ky_tu_moi_phut"] = 555
        ghi_van_hoa(goc, "tieng-555", d)
        dung_kenh(goc, "K-555", ma_nganh=NGANH, ma_ve=VE,
                  ma_van_hoa="tieng-555", voice_id="g")
        assert doc_kenh(goc, "K-555").ky_tu_moi_phut == 555

    def test_chien_luoc_moi_de_len_ngach(self, goc):
        ghi_chien_luoc(goc, "cl-moi",
                       dict(ten="CL thử", mo_ta="đè bước viết", can_ban_goc=False),
                       {"2-viet.md": "Loi nhac viet MOI cua chien luoc.\n"})
        dung_kenh(goc, "K-CL", ma_nganh=NGANH, ma_ve=VE, ma_van_hoa=VAN_HOA,
                  ma_chien_luoc="cl-moi", voice_id="g")
        thu = os.path.join(duong_kenh(goc, "K-CL"), "prompt", "2-viet.md")
        with open(thu, encoding="utf-8") as t:
            assert "chien luoc" in t.read()


# ── Sửa (ghi đè) một bộ đang có ──────────────────────────────────────────────


class TestGhiDe:
    def test_sua_bo_ve_khong_dua_anh_thi_giu_anh_cu(self, goc):
        """Sửa mô tả bộ vẽ có sẵn mà không chọn ảnh mới → ảnh cũ còn nguyên."""
        cu = open(duong_khuon(goc, "ve", VE, "nv1.png"), "rb").read()
        d = _ve_hop_le()
        d["ten"] = "Áo len than — sửa"
        ghi_ve(goc, VE, d)  # không truyền anh_nv_nguon
        moi = open(duong_khuon(goc, "ve", VE, "nv1.png"), "rb").read()
        assert moi == cu
        assert any(b.nhan == "Áo len than — sửa" for b in liet_ke_ve(goc))


# ── Chặn trước khi hỏng ──────────────────────────────────────────────────────


class TestChan:
    def test_thieu_khoa_ve_thi_loi(self, goc, anh):
        d = _ve_hop_le()
        del d["palette"]
        with pytest.raises(LoiKhuon):
            ghi_ve(goc, "net-thieu", d, anh_nv_nguon=anh)
        assert not any(b.ma == "net-thieu" for b in liet_ke_ve(goc))

    def test_bo_ve_moi_khong_co_anh_thi_loi(self, goc):
        with pytest.raises(LoiKhuon):
            ghi_ve(goc, "net-khong-anh", _ve_hop_le())

    def test_ky_tu_moi_phut_khong_duong_thi_loi(self, goc):
        d = _van_hoa_hop_le()
        d["ky_tu_moi_phut"] = 0
        with pytest.raises(LoiKhuon):
            ghi_van_hoa(goc, "tieng-0", d)

    def test_nganh_thieu_loi_nhac_bat_buoc_thi_loi(self, goc):
        with pytest.raises(LoiKhuon):
            ghi_nganh(goc, "nganh-thieu", _nganh_hop_le(),
                      {"2-viet.md": "chi co mot buoc\n"})  # thiếu 7-canh.md

    def test_chien_luoc_khong_co_loi_nhac_thi_loi(self, goc):
        with pytest.raises(LoiKhuon):
            ghi_chien_luoc(goc, "cl-rong",
                           dict(ten="rỗng", mo_ta="x", can_ban_goc=False), {})

    def test_loi_nhac_ten_la_bi_chan(self, goc):
        with pytest.raises(LoiKhuon):
            ghi_nganh(goc, "nganh-tenla", _nganh_hop_le(),
                      {"2-viet.md": "a", "7-canh.md": "b", "linh-tinh.md": "c"})

    @pytest.mark.parametrize("ma", ["a/b", "a:b", 'a"b', "_an", ".an", "  "])
    def test_ma_bo_khong_hop_le(self, ma):
        assert kiem_ma_bo(ma)


# ── Khoá API không được lọt vào khuôn ────────────────────────────────────────


class TestKhoaApi:
    def test_khoa_trong_gia_tri_yaml_bi_chan(self, goc, anh):
        d = _ve_hop_le()
        d["image_style"] = "sk-abcdefghijklmnopqrstuvwxyz0123"
        with pytest.raises(LoiKhuon) as e:
            ghi_ve(goc, "net-khoa", d, anh_nv_nguon=anh)
        assert "khoá" in str(e.value).lower()
        assert not os.path.exists(duong_khuon(goc, "ve", "net-khoa"))

    def test_khoa_giau_trong_loi_nhac_bi_chan(self, goc):
        pr = dict(_PROMPTS)
        pr["7-canh.md"] = "AIzaSyA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q\n"
        with pytest.raises(LoiKhuon):
            ghi_nganh(goc, "nganh-khoa", _nganh_hop_le(), pr)
        assert not os.path.exists(duong_khuon(goc, "nganh", "nganh-khoa"))


# ── Máy chưa cài PyYAML vẫn đọc đúng ─────────────────────────────────────────


class TestMayKhongCoPyYAML:
    """Tệp khuôn ghi ra phải đọc y hệt bằng cả hai bộ đọc YAML.

    Giống `TestMayKhongCoPyYAML` của `test_khuon.py`, nhưng cho tệp KHUÔN do
    `soan_khuon` ghi (ve.yaml, van-hoa.yaml) chứ không phải kenh.yaml.
    """

    def test_hai_bo_doc_cho_cung_ket_qua(self, goc, anh):
        from core.kenh import _yaml_toi_gian

        ghi_ve(goc, "net-yaml", _ve_hop_le(), anh_nv_nguon=anh)
        ghi_van_hoa(goc, "tieng-yaml", _van_hoa_hop_le())
        for duong in (duong_khuon(goc, "ve", "net-yaml", "ve.yaml"),
                      duong_khuon(goc, "van-hoa", "tieng-yaml.yaml")):
            day_du = doc_yaml(duong)
            with open(duong, encoding="utf-8") as tep:
                du_phong = _yaml_toi_gian(tep.read())
            lech = [k for k in day_du if str(day_du[k]) != str(du_phong.get(k))]
            assert not lech, "{0} lệch ở {1}".format(duong, lech)

    def test_moi_khoa_gon_trong_mot_dong(self, goc):
        ghi_van_hoa(goc, "tieng-dong", _van_hoa_hop_le())
        duong = duong_khuon(goc, "van-hoa", "tieng-dong.yaml")
        with open(duong, encoding="utf-8") as tep:
            dong = [d for d in tep.read().splitlines()
                    if d.strip() and not d.lstrip().startswith("#")]
        assert all(":" in d and not d.startswith((" ", "\t")) for d in dong)


# ── Hỏng giữa chừng không để lại khuôn nửa vời ───────────────────────────────


class TestKhongDeLaiNuaVoi:
    def test_hong_khi_ghi_de_thi_giu_ban_cu(self, goc, monkeypatch):
        """Đĩa đầy giữa lúc ghi đè bộ vẽ → bản cũ còn nguyên, không sót rác."""
        import core.soan_khuon as m

        cu = open(duong_khuon(goc, "ve", VE, "ve.yaml"), "rb").read()

        def gay(*a, **kw):
            raise OSError("đĩa đầy")

        monkeypatch.setattr(m.shutil, "copy2", gay)
        d = _ve_hop_le()
        d["ten"] = "Không bao giờ ghi được"
        with pytest.raises(LoiKhuon):
            ghi_ve(goc, VE, d)
        assert open(duong_khuon(goc, "ve", VE, "ve.yaml"), "rb").read() == cu
        assert not os.path.exists(duong_khuon(goc, "ve", "_soan-" + VE))
        assert not os.path.exists(duong_khuon(goc, "ve", "_cu-" + VE))


# ── Xoá bộ ───────────────────────────────────────────────────────────────────


class TestXoaBo:
    def test_xoa_mot_bo_ve(self, goc):
        xoa_bo(goc, "ve", "phan-bang-den")
        assert not any(b.ma == "phan-bang-den" for b in liet_ke_ve(goc))

    def test_khong_xoa_duoc_bo_bat_buoc_cuoi_cung(self, goc):
        """Ngách chỉ có một (`tam-ly`) — xoá nó thì không dựng được kênh nào."""
        with pytest.raises(LoiKhuon):
            xoa_bo(goc, "nganh", NGANH)
        assert any(b.ma == NGANH for b in liet_ke_nganh(goc))

    def test_xoa_bo_khong_pha_kenh_da_tao(self, goc):
        """Kênh tự chứa từ lúc dựng — xoá khuôn xong kênh vẫn chạy được."""
        dung_kenh(goc, "K-GIU", ma_nganh=NGANH, ma_ve="phan-bang-den",
                  ma_van_hoa=VAN_HOA, voice_id="g")
        xoa_bo(goc, "ve", "phan-bang-den")
        assert "K-GIU" in liet_ke_kenh(goc)
        assert kiem_kenh(doc_kenh(goc, "K-GIU")) == []



