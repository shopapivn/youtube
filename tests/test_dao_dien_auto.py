"""Tab Tự động nối dây chuyền đạo diễn của Prompt Visuals khi kênh khai `che_do_ke`.

Không gọi mạng: hàm AI chia cảnh và hàm tạo ảnh đều được bơm giả.
"""
import json
import os
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from core import dao_dien_auto as dd
from core.auto_khau import _hop_cho_canh, _viet_xlsx
from core.kenh import Kenh, doc_kenh


def _bc(tmp_path, che_do="tu_xay", anh_nv=None):
    nhat_ky = []
    kenh = SimpleNamespace(ma="story-3d", che_do_ke=che_do, engine="veo3", mo_hinh="claude-sonnet-5",
                           style={"default_character_prompt": "a cat"}, anh_nv=anh_nv or [])
    return SimpleNamespace(goc=str(tmp_path), kenh=kenh, client=object(), ghi=nhat_ky.append,
                           _nhat_ky=nhat_ky)


def _luot(tmp_path, srt=True):
    d = tmp_path / "0001"
    d.mkdir(exist_ok=True)
    if srt:
        (d / "3-phu-de.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nxin chào\n", encoding="utf-8")
    (d / "1-kich-ban.txt").write_text("Ngày xưa có một con mèo.", encoding="utf-8")
    return SimpleNamespace(thu_muc=str(d), ma_luot="0001", ma_kenh="story-3d")


MAN = {
    "scenes": [{"scene_id": 1, "img_prompt": "cat by the mill", "video_prompt": "cat blinks",
                "srt_start": "00:00:00,000", "srt_end": "00:00:02,000",
                "reference_files": json.dumps(["nv1.png", "loc1.png"])}],
    "characters": [{"id": "nv1", "name": "Cat", "role": "hero", "english_prompt": "a grey cat",
                    "sheet_prompt": "portrait of a grey cat"},
                   {"id": "nv2", "name": "King", "role": "king", "sheet_prompt": "portrait of a king"}],
    "locations": [{"id": "loc1", "name": "Mill", "english_prompt": "an old mill",
                   "sheet_prompt": "an old mill at eye level"}],
    "director_plan": [{"scene_id": 1, "location": "loc1"}],
}


class TestKenh:
    def test_doc_che_do_ke_tu_yaml(self, tmp_path):
        d = tmp_path / "CHANNEL" / "x"
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text("ma: x\nten: X\nche_do_ke: tu_xay\n", encoding="utf-8")
        assert doc_kenh(str(tmp_path), "x").che_do_ke == "tu_xay"

    def test_kenh_khong_khai_thi_rong(self, tmp_path):
        d = tmp_path / "CHANNEL" / "y"
        d.mkdir(parents=True)
        (d / "kenh.yaml").write_text("ma: y\n", encoding="utf-8")
        assert doc_kenh(str(tmp_path), "y").che_do_ke == ""
        assert not dd.che_do_dao_dien(doc_kenh(str(tmp_path), "y"))

    def test_che_do_dao_dien(self):
        assert dd.che_do_dao_dien(Kenh(che_do_ke="tu_xay"))
        assert dd.che_do_dao_dien(Kenh(che_do_ke="nhan_vat_va_boi_canh"))
        assert not dd.che_do_dao_dien(Kenh(che_do_ke="mot_nhan_vat"))
        assert not dd.che_do_dao_dien(Kenh())


class TestChayDaoDien:
    def test_goi_handle_va_ghi_dan(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        nhan = {}

        def handle(req):
            nhan.update(req)
            return {"scenes": {"json": MAN}}

        canh, man = dd.chay_dao_dien(bc, luot, handle=handle)
        assert [c["scene_id"] for c in canh] == [1]
        assert man["characters"][1]["id"] == "nv2"
        # Đầu vào đúng dạng run.py mong: {"path": ...}
        assert nhan["inputs"]["subtitles"]["path"].endswith("3-phu-de.srt")
        assert os.path.isfile(nhan["inputs"]["context"]["path"])
        with open(nhan["inputs"]["context"]["path"], encoding="utf-8") as f:
            ctx = json.load(f)
        assert "con mèo" in json.dumps(ctx, ensure_ascii=False)
        # Không tốn lượt ảnh bìa / nhạc — tab Tự động có khâu riêng.
        assert nhan["config"]["thumbnail"] is False and nhan["config"]["nhac"] is False
        assert nhan["config"]["che_do_ke"] == "tu_xay"
        assert nhan["workspace"] == luot.thu_muc
        with open(os.path.join(luot.thu_muc, dd.TEP_DAN), encoding="utf-8") as f:
            dan = json.load(f)
        assert [c["id"] for c in dan["characters"]] == ["nv1", "nv2"]
        assert dan["locations"][0]["id"] == "loc1"

    def test_khong_canh_thi_nem(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        with pytest.raises(RuntimeError):
            dd.chay_dao_dien(bc, luot, handle=lambda r: {"scenes": {"json": {"scenes": []}}})

    def test_thieu_phu_de_thi_nem(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path, srt=False)
        with pytest.raises(RuntimeError):
            dd.chay_dao_dien(bc, luot, handle=lambda r: MAN)

    def test_nhan_vat_co_dinh_dua_nv1_vao_boi_canh(self, tmp_path):
        bc, luot = _bc(tmp_path, che_do="nhan_vat_va_boi_canh"), _luot(tmp_path)
        nhan = {}

        def handle(req):
            nhan.update(req)
            return {"scenes": {"json": MAN}}

        dd.chay_dao_dien(bc, luot, handle=handle)
        with open(nhan["inputs"]["context"]["path"], encoding="utf-8") as f:
            ctx = json.dumps(json.load(f))
        assert "nv1.png" in ctx and "a cat" in ctx


class TestTaoThamChieu:
    def test_tao_thieu_bo_qua_da_co_va_chep_co_dinh(self, tmp_path):
        nv1 = tmp_path / "nv1.png"
        nv1.write_bytes(b"PNG-kenh")
        bc, luot = _bc(tmp_path, anh_nv=[str(nv1)]), _luot(tmp_path)
        tc = tmp_path / "0001" / dd.THU_MUC_THAM_CHIEU
        tc.mkdir()
        (tc / "loc1.png").write_bytes(b"da co")
        man = json.loads(json.dumps(MAN))
        man["characters"][0]["co_dinh"] = True
        goi = []

        def tao_anh(ma_id, prompt, dich):
            goi.append((ma_id, prompt))
            if ma_id == "nv2":
                raise RuntimeError("content_rejected")
            with open(dich, "wb") as f:
                f.write(b"x")

        thieu = dd.tao_tham_chieu(bc, luot, man, tao_anh=tao_anh)
        assert thieu == ["nv2"]
        assert goi == [("nv2", "portrait of a king")]        # loc1 đã có, nv1 cố định → chép
        assert (tc / "nv1.png").read_bytes() == b"PNG-kenh"
        assert (tc / "loc1.png").read_bytes() == b"da co"
        assert any("nv2" in d and "KHÔNG" in d for d in bc._nhat_ky)

    def test_khong_co_gi_de_tao(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)

        def khong_goi(*a):
            pytest.fail("không được gọi")

        assert dd.tao_tham_chieu(bc, luot, {"characters": [], "locations": []}, tao_anh=khong_goi) == []


class TestThamChieuTheoCanh:
    def test_duong_tham_chieu_canh(self, tmp_path):
        luot = _luot(tmp_path)
        tc = tmp_path / "0001" / dd.THU_MUC_THAM_CHIEU
        tc.mkdir()
        (tc / "nv1.png").write_bytes(b"x")
        c = {"reference_files": json.dumps(["nv1.png", "loc9.png"])}
        assert [os.path.basename(p) for p in dd.duong_tham_chieu_canh(luot, c)] == ["nv1.png"]
        assert dd.duong_tham_chieu_canh(luot, {"reference_files": "nv1.png, loc9.png"}) == \
            dd.duong_tham_chieu_canh(luot, c)
        assert dd.duong_tham_chieu_canh(luot, {}) == []

    def test_hop_cho_canh(self, tmp_path, monkeypatch):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        tc = tmp_path / "0001" / dd.THU_MUC_THAM_CHIEU
        tc.mkdir()
        (tc / "nv1.png").write_bytes(b"x")
        hop_cu = object()
        c = {"reference_files": json.dumps(["nv1.png"])}
        # Kênh không khai → hộp cũ y nguyên (TL4-T7 không đổi gì).
        bc.kenh.che_do_ke = ""
        assert _hop_cho_canh(bc, luot, c, hop_cu) is hop_cu
        bc.kenh.che_do_ke = "tu_xay"
        hop = _hop_cho_canh(bc, luot, c, hop_cu)
        assert isinstance(hop, dd.ThamChieuCanh)
        goi = []

        def tai_len_gia(client, p):
            goi.append(p)
            return "https://u/" + os.path.basename(p)

        monkeypatch.setattr("core.anh_len.tai_len", tai_len_gia)
        assert hop.lay() == ["https://u/nv1.png"]
        assert hop.lay() == ["https://u/nv1.png"] and len(goi) == 1     # nhớ, không tải lại
        assert _hop_cho_canh(bc, luot, {"reference_files": "[]"}, hop_cu).lay() == []


class TestXlsxCoDan:
    def test_sheet_nhan_vat_va_boi_canh(self, tmp_path):
        k = SimpleNamespace(style={"default_character_prompt": "a cat", "reference_lock": ""})
        duong = str(tmp_path / "4-canh.xlsx")
        canh = [dict(MAN["scenes"][0]), {"scene_id": 2, "img_prompt": "mill", "video_prompt": "wind",
                                         "srt_start": "0", "srt_end": "1", "reference_files": ""}]
        _viet_xlsx(duong, canh, k, ke_hoach=MAN["director_plan"], dan=MAN["characters"],
                   boi_canh=MAN["locations"])
        wb = load_workbook(duong)
        nv = wb["characters"]
        ids = [nv.cell(h, 1).value for h in range(2, nv.max_row + 1)]
        assert ids == ["nv1", "nv2"]
        dau = [nv.cell(1, c).value for c in range(1, nv.max_column + 1)]
        assert nv.cell(3, dau.index("image_file") + 1).value == "nv2.png"
        assert nv.cell(3, dau.index("sheet_prompt") + 1).value == "portrait of a king"
        lo = wb["locations"]
        assert lo.cell(2, 1).value == "loc1" and lo.cell(2, 6).value == "loc1.png"
        assert "story_map" in wb.sheetnames
        ws = wb.worksheets[0]
        dau = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        cot = dau.index("reference_files") + 1
        assert json.loads(ws.cell(2, cot).value) == ["nv1.png", "loc1.png"]
        assert not (ws.cell(3, cot).value or "")           # cảnh không khai → để trống, KHÔNG ép nv1

    def test_duong_cu_van_mac_dinh_nv1(self, tmp_path):
        k = SimpleNamespace(style={"default_character_prompt": "a cat", "reference_lock": ""})
        duong = str(tmp_path / "4-canh.xlsx")
        _viet_xlsx(duong, [{"scene_id": 1, "img_prompt": "x", "video_prompt": "y",
                            "srt_start": "0", "srt_end": "1"}], k)
        wb = load_workbook(duong)
        nv = wb["characters"]
        assert nv.cell(2, 1).value == "nv1" and "locations" not in wb.sheetnames
        ws = wb.worksheets[0]
        dau = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
        assert json.loads(ws.cell(2, dau.index("reference_files") + 1).value) == ["nv1.png"]


class TestThietKeLai:
    def test_tu_choi_hai_lan_thi_thiet_ke_lai_va_tao_lai(self, tmp_path):
        from core.prompt_visuals import DUOI_CHAN_DUNG
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = json.loads(json.dumps(MAN))
        lock = "REFERENCE IMAGES are attached, in this order:\n- reference image 1 = nv1, the hero: a grey cat with a feathered hat\n"
        man["characters"] = [
            {"id": "nv1", "name": "Cat", "role": "hero", "english_prompt": "a grey cat with a feathered hat",
             "sheet_prompt": "a grey cat with a feathered hat" + DUOI_CHAN_DUNG + " Style: 3D"},
            {"id": "nv1b", "name": "Cat", "role": "hero",
             "english_prompt": "a grey cat with a feathered hat; outfit at this stage: boots",
             "sheet_prompt": "a grey cat with a feathered hat; outfit at this stage: boots" + DUOI_CHAN_DUNG + " Style: 3D"},
        ]
        canh = [{"scene_id": 1, "img_prompt": "cat by the mill\n" + lock, "video_prompt": "x",
                 "reference_files": json.dumps(["nv1.png"])}]
        goi = []

        def tao_anh(ma_id, prompt, dich):
            goi.append((ma_id, prompt[:40]))
            if "feathered" in prompt:
                raise RuntimeError("content_rejected")
            with open(dich, "wb") as f:
                f.write(b"png")

        def goi_ai(loi_nhac):
            assert "feathered hat" in loi_nhac and "REJECTING" in loi_nhac
            return '{"english_prompt": "a grey cat wearing a small red beret"}'

        thieu = dd.tao_tham_chieu(bc, luot, man, canh=canh, tao_anh=tao_anh, goi_ai=goi_ai)
        assert thieu == []
        # Cả hai giai đoạn tạo lại bằng thiết kế mới, giai đoạn b giữ đồ riêng.
        tc = tmp_path / "0001" / dd.THU_MUC_THAM_CHIEU
        assert (tc / "nv1.png").exists() and (tc / "nv1b.png").exists()
        assert man["characters"][1]["english_prompt"] == "a grey cat wearing a small red beret; outfit at this stage: boots"
        assert man["characters"][0]["sheet_prompt"].endswith(" Style: 3D")
        # Khối khoá trong cảnh đổi theo, và đã ghi ra đĩa.
        assert "small red beret" in canh[0]["img_prompt"] and "feathered" not in canh[0]["img_prompt"]
        with open(os.path.join(luot.thu_muc, "4-canh.json"), encoding="utf-8") as f:
            assert "small red beret" in json.load(f)[0]["img_prompt"]
        with open(os.path.join(luot.thu_muc, dd.TEP_DAN), encoding="utf-8") as f:
            assert "beret" in json.load(f)["characters"][0]["english_prompt"]

    def test_thiet_ke_lai_hong_thi_van_bao_thieu(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = json.loads(json.dumps(MAN))

        def tao_anh(ma_id, prompt, dich):
            raise RuntimeError("content_rejected")

        thieu = dd.tao_tham_chieu(bc, luot, man, canh=[], tao_anh=tao_anh, goi_ai=lambda l: "không có json")
        assert sorted(thieu) == ["loc1", "nv1", "nv2"]
        assert any("KHÔNG tạo được" in d for d in bc._nhat_ky)


    def test_giai_doan_bi_chan_thi_doi_ca_bo_do_cua_giai_doan(self, tmp_path):
        from core.prompt_visuals import DUOI_CHAN_DUNG
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = json.loads(json.dumps(MAN))
        man["characters"] = [
            {"id": "nv1", "role": "hero", "english_prompt": "a yellow cat",
             "sheet_prompt": "a yellow cat" + DUOI_CHAN_DUNG + " Style: 3D"},
            {"id": "nv1b", "role": "hero",
             "english_prompt": "a yellow cat; outfit at this stage: a feathered hat and boots",
             "sheet_prompt": "a yellow cat; outfit at this stage: a feathered hat and boots" + DUOI_CHAN_DUNG + " Style: 3D"},
        ]
        lock = "REFERENCE IMAGES are attached, in this order:" + chr(10) + \
            "- reference image 1 = nv1b, the hero: a yellow cat; outfit at this stage: a feathered hat and boots" + chr(10)
        canh = [{"scene_id": 20, "img_prompt": "cat walks" + chr(10) + lock, "video_prompt": "x",
                 "reference_files": json.dumps(["nv1b.png"])}]
        (tmp_path / "0001" / dd.THU_MUC_THAM_CHIEU).mkdir()
        (tmp_path / "0001" / dd.THU_MUC_THAM_CHIEU / "nv1.png").write_bytes(b"cu")
        hoi = []

        def tao_anh(ma_id, prompt, dich):
            if "feathered" in prompt:
                raise RuntimeError("content_rejected")
            with open(dich, "wb") as f:
                f.write(b"png")

        def goi_ai(loi_nhac):
            hoi.append(loi_nhac)
            return '{"english_prompt": "a yellow cat with green eyes", "outfit": "plain brown boots and a small red scarf"}'

        thieu = dd.tao_tham_chieu(bc, luot, man, canh=canh, tao_anh=tao_anh, goi_ai=goi_ai)
        assert thieu == []
        assert "feathered hat and boots" in hoi[0] and '"outfit"' in hoi[0]     # AI biết đồ cũ của giai đoạn
        nv1, nv1b = man["characters"]
        assert nv1["english_prompt"] == "a yellow cat with green eyes"
        assert nv1b["english_prompt"] == "a yellow cat with green eyes; outfit at this stage: plain brown boots and a small red scarf"
        assert nv1b["sheet_prompt"].endswith(" Style: 3D") and "feathered" not in nv1b["sheet_prompt"]
        assert "plain brown boots" in canh[0]["img_prompt"] and "feathered" not in canh[0]["img_prompt"]
        tc = tmp_path / "0001" / dd.THU_MUC_THAM_CHIEU
        assert (tc / "nv1b.png").read_bytes() == b"png" and (tc / "nv1.png").read_bytes() == b"png"
        assert (tc / "nv1.png.cu").read_bytes() == b"cu"


class TestSuaCanhTheoDoMoi:
    def test_chi_sua_canh_co_nhan_vat_va_ta_do_cu(self):
        lock = chr(10) + "REFERENCE IMAGES are attached, in this order:" + chr(10) + "- reference image 1 = nv1b, the hero: cat"
        canh = [
            {"scene_id": 5, "reference_files": json.dumps(["nv1b.png"]),
             "img_prompt": "nv1b tips its wide-brim hat, boots mid-step" + lock, "video_prompt": "the hat brim lifts"},
            {"scene_id": 6, "reference_files": json.dumps(["nv1b.png"]),
             "img_prompt": "nv1b waves happily" + lock, "video_prompt": "waves"},
            {"scene_id": 7, "reference_files": json.dumps(["nv8.png"]),
             "img_prompt": "a guard in tall boots" + lock, "video_prompt": "x"},
        ]
        hoi = []

        def goi_ai(loi_nhac):
            hoi.append(loi_nhac)
            return json.dumps({"5": {"img": "nv1b touches its red beret, vest mid-step", "video": "the beret tilts"}})

        n = dd.sua_canh_theo_do_moi(canh, "nv1b", "a wide-brim felt hat with a feather, leather boots and a cloth sack",
                                     "a small red beret and a little brown vest", goi_ai)
        assert n == 1 and len(hoi) == 1
        assert '"5"' in hoi[0] and '"6"' not in hoi[0] and '"7"' not in hoi[0]   # chỉ cảnh có nv1b và tả đồ cũ
        assert canh[0]["img_prompt"].startswith("nv1b touches its red beret") and "REFERENCE IMAGES" in canh[0]["img_prompt"]
        assert canh[0]["video_prompt"] == "the beret tilts"
        assert canh[2]["img_prompt"].startswith("a guard in tall boots")          # cảnh khác không đụng

    def test_khong_co_canh_nao_thi_khong_goi_ai(self):
        def goi_ai(l):
            pytest.fail("không được gọi")

        assert dd.sua_canh_theo_do_moi([{"scene_id": 1, "reference_files": "[]", "img_prompt": "x"}],
                                        "nv1b", "boots", "vest", goi_ai) == 0


class TestSoiChanDung:
    def test_chan_dung_thieu_vuong_mien_thi_ve_lai_va_giu_ban_hon(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv5", "role": "the king", "english_prompt": "a jolly old king with a golden crown and red robe",
                               "sheet_prompt": "portrait of the king"}], "locations": []}
        goi = []

        def tao_anh(ma_id, prompt, dich):
            goi.append(prompt)
            with open(dich, "wb") as f:
                f.write(b"lan%d" % len(goi))

        def cham(anh, mo_ta, vai):
            assert vai == "the king" and "crown" in mo_ta
            return (3, "golden crown, royal robe") if open(anh, "rb").read() == b"lan1" else (5, "")

        assert dd.tao_tham_chieu(bc, luot, man, tao_anh=tao_anh, cham=cham) == []
        assert len(goi) == 2 and "MUST clearly show: golden crown, royal robe" in goi[1]
        tc = tmp_path / "0001" / dd.THU_MUC_THAM_CHIEU
        assert (tc / "nv5.png").read_bytes() == b"lan2"           # bản vẽ lại tốt hơn được dùng
        assert (tc / "nv5.png.lan1.png").exists()
        assert any("3/5" in d for d in bc._nhat_ky)

    def test_ban_ve_lai_khong_hon_thi_giu_tam_dau(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"characters": [{"id": "nv5", "role": "the king", "english_prompt": "a king", "sheet_prompt": "p"}],
               "locations": [{"id": "loc1", "sheet_prompt": "a hall"}]}
        n = {"k": 0}

        def tao_anh(ma_id, prompt, dich):
            n["k"] += 1
            with open(dich, "wb") as f:
                f.write(b"x")

        cham_goi = []

        def cham(anh, mo_ta, vai):
            cham_goi.append(vai)
            return (3, "crown")

        assert dd.tao_tham_chieu(bc, luot, man, tao_anh=tao_anh, cham=cham) == []
        assert n["k"] == 3                           # nv5 hai lần, loc1 một lần (bối cảnh không chấm)
        assert cham_goi == ["the king", "the king"]
        tc = tmp_path / "0001" / dd.THU_MUC_THAM_CHIEU
        assert (tc / "nv5.png").exists() and not (tc / "nv5.png.lan2.png").exists()


class TestKhoaLanChay:
    def test_run_id_doi_khi_phu_de_doi(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        nhan = []

        def handle(req):
            nhan.append(req["run_id"])
            return {"scenes": {"json": MAN}}

        dd.chay_dao_dien(bc, luot, handle=handle)
        (tmp_path / "0001" / "3-phu-de.srt").write_text("1\n00:00:00,000 --> 00:00:02,000\nkhac\n", encoding="utf-8")
        dd.chay_dao_dien(bc, luot, handle=handle)
        assert nhan[0].startswith("story-3d-0001-") and nhan[0] != nhan[1]

    def test_khong_dan_nhan_vat_thi_nem(self, tmp_path):
        bc, luot = _bc(tmp_path), _luot(tmp_path)
        man = {"scenes": MAN["scenes"], "characters": [], "locations": []}
        with pytest.raises(RuntimeError, match="dàn nhân vật"):
            dd.chay_dao_dien(bc, luot, handle=lambda r: {"scenes": {"json": man}})
