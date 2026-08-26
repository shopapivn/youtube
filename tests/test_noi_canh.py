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


class TestNeoLai:
    def test_bo_cum_co_khung(self):
        assert nc.bo_cum_co_khung("Medium shot of nv1 (nv1) waving at loc1, warm light") == "nv1 (nv1) waving at loc1, warm light"
        assert nc.bo_cum_co_khung("Over-the-shoulder shot from behind nv2 toward nv1, she laughs") == "nv2 toward nv1, she laughs"
        assert nc.bo_cum_co_khung("The kids hide under the table") == "The kids hide under the table"

    def test_prompt_neo_lai(self):
        goc = "Close-up of nv1 (nv1) smiling at loc1" + chr(10) + "REFERENCE IMAGES are attached, in this order:" + chr(10) + "- reference image 1 = nv1, the hero: a cat"
        p = nc.prompt_neo_lai(goc)
        assert p.startswith("nv1 (nv1) smiling") and "REFERENCE IMAGES" in p and p.endswith(nc.DUOI_NEO_LAI)
        assert "NEXT moment" not in p

    def test_neo_lai_sau_toi_da_noi_tiep(self, tmp_path):
        ct, nhat, anh_d, clip_d = _chuoi(tmp_path, lien_mach=True)
        canh = [_c(i, "loc1", refs=("nv1.png", "loc1.png")) for i in range(1, 7)]
        assert ct.chay(canh) == 6
        # 1: ảnh mới; 2, 3: diễn tiếp; 4: neo lại (ảnh mới, cùng bố cục); 5, 6: diễn tiếp
        assert [a[0] for a in nhat["anh"]] == [1, 4]
        assert any("neo lại" in d for d in nhat["ghi"]) and sum("diễn tiếp" in d for d in nhat["ghi"]) == 4
        assert nhat["anh"][1][1] == ["nv1.png", "loc1.png", "3.png"]


def test_engine_giu_khung_dau():
    assert nc.engine_giu_khung_dau("seedance") and not nc.engine_giu_khung_dau("veo3") and not nc.engine_giu_khung_dau("")


class TestGiuKhungDau:
    def test_theo_engine_hoac_co_khung_dau(self):
        from types import SimpleNamespace as NS
        assert nc.giu_khung_dau(NS(engine="seedance", khung_dau=False))
        assert not nc.giu_khung_dau(NS(engine="veo3", khung_dau=False))
        assert nc.giu_khung_dau(NS(engine="veo3", khung_dau=True))
        assert not nc.giu_khung_dau(NS(engine="veo3"))


def _cu_may(tmp_path, lam_anh_hong=None, lam_clip_hong=None):
    anh_d = tmp_path / "5-anh"; clip_d = tmp_path / "6-clip"; tc = tmp_path / "tham-chieu"
    for d in (anh_d, clip_d, tc):
        d.mkdir(exist_ok=True)
    for x in ("nv1.png", "loc1.png"):
        (tc / x).write_bytes(b"ref")
    nhat = {"anh": [], "clip": [], "cat": [], "noi": [], "khung": [], "ghi": []}

    def lam_anh(c, tep, refs, prompt):
        if lam_anh_hong and len(nhat["anh"]) + 1 in lam_anh_hong:
            raise RuntimeError("content_rejected")
        nhat["anh"].append((os.path.basename(tep), [os.path.basename(r) for r in refs], prompt[:40]))
        open(tep, "wb").write(b"anh")

    def lam_clip(c, anh, tho, anh_cuoi=None):
        if lam_clip_hong and len(nhat["clip"]) + 1 in lam_clip_hong:
            raise RuntimeError("clip hỏng")
        nhat["clip"].append((os.path.basename(tho), c["video_prompt"], os.path.basename(anh),
                             os.path.basename(anh_cuoi) if anh_cuoi else None))
        open(tho, "wb").write(b"tho")

    def cat_tu(nguon, dich, bat_dau, giay):
        nhat["cat"].append((os.path.basename(dich), round(bat_dau, 2), round(giay, 2))); open(dich, "wb").write(b"cut")

    def noi(nguon, dich):
        nhat["noi"].append([os.path.basename(x) for x in nguon]); open(dich, "wb").write(b"take")

    def trich(clip, khung):
        nhat["khung"].append(os.path.basename(khung)); open(khung, "wb").write(b"khung"); return khung

    ct = nc.CuMayDai(thu_muc_anh=str(anh_d), thu_muc_clip=str(clip_d), thu_muc_tham_chieu=str(tc),
                     lam_anh=lam_anh, lam_clip=lam_clip, cat=lambda *a: None, trich_khung=trich,
                     ghi=nhat["ghi"].append, cat_tu=cat_tu, noi_clip=noi)
    return ct, nhat, anh_d, clip_d


class TestCuMayDai:
    def test_chia_doan(self):
        canh = [_c(1, "loc1", giay=4.6), _c(2, "loc1", giay=3.2), _c(3, "loc1", giay=5.0)]
        d = nc.chia_doan(canh)
        assert [x["k"] for x in d] == [0, 1] and abs(d[0]["giay"] - 6.4) < 1e-6
        assert [c["scene_id"] for c in d[0]["canh"]] == [1, 2] and [c["scene_id"] for c in d[1]["canh"]] == [2, 3]
        assert len(nc.chia_doan([_c(1, "loc1", giay=8.0)])) == 1
        assert len(nc.chia_doan([_c(1, "loc1", giay=8.1)])) == 2

    def test_hanh_dong_clip_bo_khoa_va_tach_duoi(self):
        v = ("IDENTITY LOCK, highest priority for the entire clip: every character stays exactly; nothing is added. "
             "Only pose, gesture, expression and camera move. nv1 waves at nv2, slow pan, smooth 3D animated motion, no text")
        hd, duoi = nc.hanh_dong_clip(v)
        assert hd == "nv1 waves at nv2, slow pan" and duoi.startswith(", smooth 3D animated motion")
        assert nc.hanh_dong_clip("just moves") == ("just moves", "")

    def test_prompt_doan(self):
        d = {"canh": [_c(1, "loc1", video="Medium shot of nv1 waving, smooth 3D animated motion, no text"),
                      _c(2, "loc1", video="Close-up of nv1 laughing, smooth 3D animated motion, no text")]}
        p = nc.prompt_doan(d, False)
        assert p.startswith(nc.DAU_CLIP_KHUNG_DAU) and "Medium shot of nv1 waving Then: nv1 laughing, smooth 3D" in p
        assert p.count("no text") == 1
        assert nc.prompt_doan(d, True).startswith(nc.DAU_CLIP_NOI_TIEP_DAI + "nv1 waving")

    def test_moi_loi_nhac_clip_deu_khoa_nhan_dang_co_va_nen(self):
        for dau in (nc.DAU_CLIP_KHUNG_DAU, nc.DAU_CLIP_NOI_TIEP_DAI):
            assert dau.startswith("IDENTITY LOCK")
            assert "SIZE relative to" in dau and "nobody grows" in dau
            assert "no stripes" in dau and "background" in dau
        # đoạn diễn tiếp: máy ĐỨNG YÊN (bốn đoạn trôi nhẹ cộng lại thành zoom)
        assert "locked off" in nc.DAU_CLIP_NOI_TIEP_DAI and "does not move" in nc.DAU_CLIP_NOI_TIEP_DAI
        assert "SIZE relative to" not in "" and "nobody changes size" in nc.DUOI_KHUNG_CUOI
        assert "camera has NOT moved" in nc.DUOI_KHUNG_CUOI

    def test_bo_chi_dao_may(self):
        assert nc.bo_chi_dao_may("framed over nv2's shoulder, nv1 recoils sharply, camera eases in slightly") == "nv1 recoils sharply"
        assert nc.bo_chi_dao_may("nv2 rises onto two legs, one paw stroking its whiskers, camera tilts upward following it") ==             "nv2 rises onto two legs, one paw stroking its whiskers"
        assert nc.bo_chi_dao_may("Close-up of nv2 bowing, no camera move") == "nv2 bowing"
        assert nc.bo_chi_dao_may("nv1 laughs") == "nv1 laughs"

    def test_mot_cu_may_hai_doan_roi_cat_tung_canh(self, tmp_path):
        ct, nhat, anh_d, clip_d = _cu_may(tmp_path)
        canh = [_c(1, "loc1", giay=4.6), _c(2, "loc1", giay=3.2), _c(3, "loc1", giay=5.0)]
        assert ct.chay(canh) == 3
        # 12,8 s -> 2 đoạn; 3 khung: mở cú máy, cuối đoạn 0 (= đầu đoạn 1), cuối đoạn 1
        assert [x[0] for x in nhat["anh"]] == ["1.png", "1-1.png", "1-2.png"]
        assert nhat["anh"][0] == ("1.png", ["nv1.png", "loc1.png"], nc.prompt_noi_canh(canh[0]["img_prompt"], False)[:40])
        # khung cuối vẽ kèm CHÍNH khung đầu của đoạn, lời nhắc "cùng cú máy"
        assert nhat["anh"][1][1] == ["nv1.png", "loc1.png", "1.png"]
        assert nhat["anh"][2][1] == ["nv1.png", "loc1.png", "1-1.png"]
        assert nhat["anh"][1][2] == nc.prompt_khung_cuoi(canh[1]["img_prompt"])[:40]
        # clip ghim hai đầu
        assert [(x[0], x[2], x[3]) for x in nhat["clip"]] == [
            ("1-0.mp4", "1.png", "1-1.png"), ("1-1.mp4", "1-1.png", "1-2.png")]
        assert nhat["clip"][0][1].startswith(nc.DAU_CLIP_KHUNG_DAU) and nhat["clip"][1][1].startswith(nc.DAU_CLIP_NOI_TIEP_DAI)
        assert nhat["cat"] == [("1-0-cat.mp4", 0.0, 6.4), ("1-1-cat.mp4", 0.0, 6.4),
                               ("1.mp4", 0.0, 4.6), ("2.mp4", 4.6, 3.2), ("3.mp4", 7.8, 5.0)]
        assert nhat["noi"] == [["1-0-cat.mp4", "1-1-cat.mp4"]] and (clip_d / "_doan" / "1.mp4").exists()
        # chạy lại: không làm gì thêm
        n = {k: len(v) for k, v in nhat.items() if k != "ghi"}
        assert ct.chay(canh) == 3 and {k: len(v) for k, v in nhat.items() if k != "ghi"} == n

    def test_moi_doan_deu_co_hai_khung(self, tmp_path):
        """Khung cuối đoạn k CHÍNH LÀ khung đầu đoạn k+1 — vẽ một lần, dùng hai lần."""
        ct, nhat, anh_d, clip_d = _cu_may(tmp_path)
        canh = [_c(i, "loc1", giay=8.0) for i in range(1, 5)]   # 32 s -> 4 đoạn
        assert ct.chay(canh) == 4
        assert [a[0] for a in nhat["anh"]] == ["1.png", "1-1.png", "1-2.png", "1-3.png", "1-4.png"]
        assert [(x[2], x[3]) for x in nhat["clip"]] == [
            ("1.png", "1-1.png"), ("1-1.png", "1-2.png"), ("1-2.png", "1-3.png"), ("1-3.png", "1-4.png")]
        assert nhat["clip"][0][1].startswith(nc.DAU_CLIP_KHUNG_DAU)
        assert all(x[1].startswith(nc.DAU_CLIP_NOI_TIEP_DAI) for x in nhat["clip"][1:])

    def test_clip_hong_giua_chung_thi_cat_phan_da_co(self, tmp_path):
        ct, nhat, anh_d, clip_d = _cu_may(tmp_path, lam_clip_hong={2})
        canh = [_c(1, "loc1", giay=6.0), _c(2, "loc1", giay=6.0), _c(3, "loc1", giay=4.0)]   # 16 s → 2 đoạn × 8
        assert ct.chay(canh) == 1
        assert ct.loi == ["clip đoạn 1-1"] and nhat["noi"] == [["1-0-cat.mp4"]]
        assert [x[0] for x in nhat["cat"]] == ["1-0-cat.mp4", "1.mp4"]

    def test_anh_khung_cuoi_hong_thi_dung_chuoi(self, tmp_path):
        ct, nhat, anh_d, clip_d = _cu_may(tmp_path, lam_anh_hong={2})
        canh = [_c(1, "loc1", giay=6.0), _c(2, "loc1", giay=6.0)]
        assert ct.chay(canh) == 0
        assert ct.loi == ["ảnh đoạn 1-0"] and nhat["clip"] == []
