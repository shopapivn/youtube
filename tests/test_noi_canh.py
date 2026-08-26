"""Chế độ NỐI CẢNH: ảnh N → clip N → cắt đúng thời lượng → khung cuối làm tham chiếu ảnh N+1.

Không mạng, không FFmpeg thật: mọi việc tốn tiền đi qua hàm bơm giả.
"""
import json
import os
from types import SimpleNamespace

import pytest

from core import noi_canh as nc
from core.dao_dien_auto import che_do_dao_dien
from core.kenh import Kenh


def _c(so, loc, refs=("nv1.png", "loc1.png"), giay=4.0, video="moves"):
    return {"scene_id": so, "location_used": loc, "reference_files": json.dumps(list(refs)),
            "img_prompt": "Wide shot of nv1 (nv1) at loc1\nREFERENCE IMAGES are attached, in this order:\n"
                          "- reference image 1 = nv1, the hero: a cat\n- reference image 2 = loc1, the mill: a mill\n"
                          "Every character must look EXACTLY like its reference.",
            "video_prompt": video, "duration": giay}


class TestThuan:
    def test_chuoi_theo_boi_canh(self):
        canh = [_c(1, "loc1"), _c(2, "loc1"), _c(3, ""), _c(4, "loc2"), _c(5, "loc2"), _c(6, "loc1")]
        ch = nc.chuoi_theo_boi_canh(canh)
        assert [[c["scene_id"] for c in x] for x in ch] == [[1, 2, 3], [4, 5], [6]]
        assert nc.chuoi_theo_boi_canh([]) == []

    def test_tham_chieu_va_prompt(self, tmp_path):
        for t in ("nv1.png", "loc1.png"):
            (tmp_path / t).write_bytes(b"x")
        khung = tmp_path / "k.png"; khung.write_bytes(b"k")
        c = _c(7, "loc1")
        assert [os.path.basename(p) for p in nc.tham_chieu_noi_canh(str(tmp_path), c, None)] == ["nv1.png", "loc1.png"]
        assert [os.path.basename(p) for p in nc.tham_chieu_noi_canh(str(tmp_path), c, str(khung))] == ["nv1.png", "loc1.png", "k.png"]
        p0 = nc.prompt_noi_canh(c["img_prompt"], False)
        assert p0 == c["img_prompt"]
        p1 = nc.prompt_noi_canh(c["img_prompt"], True)
        assert "reference image 2 = loc1" in p1 and "reference image 1 = nv1" in p1
        assert p1.endswith(nc.DUOI_NOI_CANH) and "NEXT moment" in p1

    def test_giay_cua_canh(self):
        assert nc.giay_cua_canh({"duration": 4.6}) == 4.6
        assert abs(nc.giay_cua_canh({"srt_start": "00:00:01,000", "srt_end": "00:00:04,500"}) - 3.5) < 1e-9
        assert nc.giay_cua_canh({}) == 0.0

    def test_cat_va_khung_lenh(self, tmp_path):
        goi = []

        def chay(lenh, **kw):
            goi.append(lenh)
            if lenh[-1].endswith(".png"):
                open(lenh[-1], "wb").write(b"png")
            return SimpleNamespace(returncode=0, stderr="")

        nc.cat_clip_theo_canh("ffmpeg", "tho.mp4", "cut.mp4", 4.6, "libx264", {"-crf": "18"}, chay=chay)
        l = goi[0]
        assert "tpad=stop_mode=clone:stop_duration=4.600" in l and "-t" in l and l[l.index("-t") + 1] == "4.600"
        assert "-an" in l and l[-1] == "cut.mp4"
        ra = nc.khung_cuoi("ffmpeg", "cut.mp4", str(tmp_path / "k" / "7.png"), chay=chay)
        assert ra.endswith("7.png") and os.path.exists(ra)
        assert "-sseof" in goi[1]

    def test_cat_hong_thi_nem_va_xoa_do(self, tmp_path):
        dich = tmp_path / "cut.mp4"; dich.write_bytes(b"do")

        def chay(lenh, **kw):
            return SimpleNamespace(returncode=1, stderr="Error x")

        with pytest.raises(RuntimeError, match="cắt clip hỏng"):
            nc.cat_clip_theo_canh("ffmpeg", "tho.mp4", str(dich), 3, chay=chay)
        assert not dich.exists()


def _chuoi(tmp_path, lam_clip_hong=None, lam_anh_hong=None, lien_mach=False):
    anh_d = tmp_path / "5-anh"; clip_d = tmp_path / "6-clip"; tc = tmp_path / "tham-chieu"
    for d in (anh_d, clip_d, tc):
        d.mkdir(exist_ok=True)
    for t in ("nv1.png", "loc1.png"):
        (tc / t).write_bytes(b"ref")
    nhat = {"anh": [], "clip": [], "cat": [], "khung": [], "ghi": []}

    def lam_anh(c, tep, refs, prompt):
        if lam_anh_hong and c["scene_id"] in lam_anh_hong:
            raise RuntimeError("content_rejected")
        nhat["anh"].append((c["scene_id"], [os.path.basename(r) for r in refs], "NEXT moment" in prompt))
        open(tep, "wb").write(b"anh")

    def lam_clip(c, anh, tho):
        if lam_clip_hong and c["scene_id"] in lam_clip_hong:
            raise RuntimeError("clip hỏng")
        nhat["clip"].append(c["scene_id"]); open(tho, "wb").write(b"tho")

    def cat(tho, clip, giay):
        nhat["cat"].append((os.path.basename(clip), giay)); open(clip, "wb").write(b"cut")

    def trich(clip, khung):
        nhat["khung"].append(os.path.basename(khung))
        os.makedirs(os.path.dirname(khung), exist_ok=True); open(khung, "wb").write(b"khung"); return khung

    ct = nc.ChuoiNoiCanh(thu_muc_anh=str(anh_d), thu_muc_clip=str(clip_d), thu_muc_tham_chieu=str(tc),
                         lam_anh=lam_anh, lam_clip=lam_clip, cat=cat, trich_khung=trich, ghi=nhat["ghi"].append,
                         lien_mach=lien_mach)
    return ct, nhat, anh_d, clip_d


class TestChuoi:
    def test_noi_canh_dung_thu_tu_va_tham_chieu(self, tmp_path):
        ct, nhat, anh_d, clip_d = _chuoi(tmp_path)
        canh = [_c(1, "loc1", giay=4.6), _c(2, "loc1", giay=3.2), _c(3, "loc1", giay=5.0)]
        assert ct.chay(canh) == 3
        # cảnh 1: tham chiếu như Excel; cảnh 2, 3: nhân vật + khung trước, bỏ bối cảnh, prompt nối
        assert nhat["anh"] == [(1, ["nv1.png", "loc1.png"], False), (2, ["nv1.png", "loc1.png", "1.png"], True),
                               (3, ["nv1.png", "loc1.png", "2.png"], True)]
        assert nhat["clip"] == [1, 2, 3]
        assert nhat["cat"] == [("1.mp4", 4.6), ("2.mp4", 3.2), ("3.mp4", 5.0)]
        assert nhat["khung"] == ["1.png", "2.png", "3.png"]
        assert (clip_d / "_tho" / "1.mp4").exists() and (clip_d / "1.mp4").read_bytes() == b"cut"
        assert (clip_d / "khung" / "3.png").exists()

    def test_chay_tiep_bo_qua_phan_da_co(self, tmp_path):
        ct, nhat, anh_d, clip_d = _chuoi(tmp_path)
        canh = [_c(1, "loc1"), _c(2, "loc1")]
        (anh_d / "1.png").write_bytes(b"cu"); (clip_d / "1.mp4").write_bytes(b"cu")
        (clip_d / "khung").mkdir(); (clip_d / "khung" / "1.png").write_bytes(b"cu")
        assert ct.chay(canh) == 2
        assert [a[0] for a in nhat["anh"]] == [2] and nhat["clip"] == [2]
        assert nhat["anh"][0][1] == ["nv1.png", "loc1.png", "1.png"]           # vẫn nối từ khung cũ của cảnh 1

    def test_clip_hong_thi_noi_tu_anh(self, tmp_path):
        ct, nhat, anh_d, clip_d = _chuoi(tmp_path, lam_clip_hong={1})
        canh = [_c(1, "loc1"), _c(2, "loc1")]
        assert ct.chay(canh) == 1
        assert nhat["anh"][1][1] == ["nv1.png", "loc1.png", "1.png"]   # 1.png ở đây là ẢNH cảnh 1
        assert ct.loi == ["clip 1"] and any("khâu clip sẽ làm nốt" in d for d in nhat["ghi"])
        assert not (clip_d / "1.mp4").exists()

    def test_anh_hong_thi_chuoi_dut_va_bat_dau_lai(self, tmp_path):
        ct, nhat, anh_d, clip_d = _chuoi(tmp_path, lam_anh_hong={2})
        canh = [_c(1, "loc1"), _c(2, "loc1"), _c(3, "loc1")]
        assert ct.chay(canh) == 2
        assert [a[0] for a in nhat["anh"]] == [1, 3]
        assert nhat["anh"][1][1] == ["nv1.png", "loc1.png"] and nhat["anh"][1][2] is False   # cảnh 3 làm lại từ bối cảnh
        assert ct.loi == ["ảnh 2"]

    def test_canh_khong_co_video_prompt_thi_noi_tu_anh(self, tmp_path):
        ct, nhat, anh_d, clip_d = _chuoi(tmp_path)
        canh = [_c(1, "loc1", video=""), _c(2, "loc1")]
        assert ct.chay(canh) == 1
        assert nhat["clip"] == [2] and nhat["anh"][1][1] == ["nv1.png", "loc1.png", "1.png"]

    def test_dung_thi_dung(self, tmp_path):
        ct, nhat, anh_d, clip_d = _chuoi(tmp_path)

        class Dung(Exception):
            pass

        def kiem():
            if nhat["anh"]:
                raise Dung()

        ct.kiem_dung = kiem
        with pytest.raises(Dung):
            ct.chay([_c(1, "loc1"), _c(2, "loc1")])
        assert [a[0] for a in nhat["anh"]] == [1]

    def test_chay_cac_chuoi_song_song(self):
        goi = []
        ch = [[_c(1, "loc1"), _c(2, "loc1")], [_c(3, "loc2")], [_c(4, "loc3")]]
        assert nc.chay_cac_chuoi(ch, lambda x: (goi.append(len(x)), len(x))[1], song_song=2) == 4
        assert sorted(goi) == [1, 1, 2]


def test_noi_canh_di_duong_dao_dien_va_khau_anh_rieng():
    assert nc.la_noi_canh(Kenh(che_do_ke="noi_canh")) and not nc.la_noi_canh(Kenh(che_do_ke="tu_xay"))
    assert che_do_dao_dien(Kenh(che_do_ke="noi_canh"))
    from core import auto_khau
    bc = auto_khau.BoiCanh(goc=".", kenh=Kenh(che_do_ke="noi_canh"), goi_chat=lambda *a, **k: "")
    assert auto_khau.dung_bo_viec(bc)["anh"].__qualname__.startswith("_khau_anh_noi_canh")
    bc2 = auto_khau.BoiCanh(goc=".", kenh=Kenh(), goi_chat=lambda *a, **k: "")
    assert auto_khau.dung_bo_viec(bc2)["anh"].__qualname__.startswith("_khau_anh.")


def test_kenh_hoathinh_3d():
    from core.kenh import doc_kenh
    goc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    k = doc_kenh(goc, "hoathinh-3d")
    assert k.che_do_ke == "noi_canh" and k.do_dai_tu_do and "SHOT CONTINUITY" in k.prompt["7-canh.md"]


def test_duoi_noi_canh_khong_noi_doi(tmp_path):
    goc = "Wide shot of nv1 (nv1) at loc1. Style: 3D"
    p1 = nc.prompt_noi_canh(goc, True)
    p2 = nc.prompt_noi_canh(p1, True)            # nối lần hai từ bản đã có đuôi
    assert p1 == p2 and p1.count("NEXT moment") == 1
    assert nc.bo_duoi_noi_canh(p1) == goc and nc.bo_duoi_noi_canh(goc) == goc


def test_prompt_dai_thi_rut_khoi_khoa_va_duoi_ngan():
    lock = chr(10).join("- reference image %d = nv%d, the hero: " % (i, i) + "x" * 1300 for i in range(1, 5))
    goc = "Wide shot of nv1 (nv1)" + chr(10) + "REFERENCE IMAGES are attached, in this order:" + chr(10) + lock
    assert len(goc) > nc.TRAN_PROMPT
    p = nc.prompt_noi_canh(goc, True)
    assert len(p) <= 5000 and p.endswith(nc.DUOI_NOI_CANH_NGAN) and "reference image 4 = nv4" in p
    assert nc.bo_duoi_noi_canh(nc.prompt_noi_canh("ngan (nv1)", True)) == "ngan (nv1)"


class TestLienMach:
    def test_noi_tiep_khong_cat(self):
        a = _c(1, "loc1", refs=("nv1.png", "nv2.png", "loc1.png"))
        assert nc.noi_tiep_khong_cat(a, _c(2, "loc1", refs=("nv1.png", "loc1.png")))         # nv1 ⊆ {nv1,nv2}
        assert not nc.noi_tiep_khong_cat(a, _c(3, "loc1", refs=("nv1.png", "nv4.png", "loc1.png")))   # nv4 mới vào
        assert not nc.noi_tiep_khong_cat(None, _c(4, "loc1"))
        assert not nc.noi_tiep_khong_cat(a, _c(5, "loc1", refs=("loc1.png",)))              # cảnh không người: ảnh mới

    def test_bat_dau_cat(self):
        assert nc.bat_dau_cat(4.0, 8.0) == nc.BO_DAU_CLIP
        assert nc.bat_dau_cat(7.9, 8.0) == 0.1 - 1e-16 or abs(nc.bat_dau_cat(7.9, 8.0) - 0.1) < 1e-9
        assert nc.bat_dau_cat(8.0, 8.0) == 0.0

    def test_cat_co_ss(self):
        goi = []
        nc.cat_clip_theo_canh("ffmpeg", "tho.mp4", "cut.mp4", 4.0, chay=lambda l, **k: (goi.append(l), SimpleNamespace(returncode=0, stderr=""))[1], bat_dau=0.35)
        l = goi[0]
        assert l[l.index("-ss") + 1] == "0.350" and l.index("-ss") < l.index("-i")

    def test_chuoi_dien_tiep_khong_tao_anh_moi(self, tmp_path):
        ct, nhat, anh_d, clip_d = _chuoi(tmp_path, lien_mach=True)
        canh = [_c(1, "loc1", refs=("nv1.png", "loc1.png")), _c(2, "loc1", refs=("nv1.png", "loc1.png")),
                _c(3, "loc1", refs=("nv1.png", "nv4.png", "loc1.png"))]
        (tmp_path / "tham-chieu" / "nv4.png").write_bytes(b"ref")
        assert ct.chay(canh) == 3
        # cảnh 2 diễn tiếp: không gọi lam_anh, ảnh 2 = khung cuối 1; cảnh 3 có nv4 mới → ảnh mới
        assert [a[0] for a in nhat["anh"]] == [1, 3]
        assert (anh_d / "2.png").read_bytes() == b"khung"
        assert nhat["clip"] == [1, 2, 3] and any("diễn tiếp" in d for d in nhat["ghi"])
        assert nhat["anh"][1][1] == ["nv1.png", "nv4.png", "loc1.png", "2.png"]
