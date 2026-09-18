"""Đóng gói tool cho VPS (`core/goi_vps.py`) và bộ cài phía VPS
(`vm/cai_dat_vps.py`) — bước E của `vm/KE-HOACH-5-KENH.md`.

Không gọi mạng, không gọi API thật. `vm/cai_dat_vps.py` không phải gói Python
(vm/ không có `__init__.py`) nên nạp bằng `importlib` như các bài kiểm
`vm/agent.py` khác (`tests/test_vm_agent.py::_nap_agent`).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from threading import Event

import pytest

GOC = Path(__file__).resolve().parent.parent


def _nap_cai_dat_vps():
    spec = importlib.util.spec_from_file_location(
        "vm_cai_dat_vps", GOC / "vm" / "cai_dat_vps.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Dựng một "tool giả" tối thiểu để đóng gói ────────────────────────────────


def _dung_tool_gia(goc: Path) -> None:
    (goc / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    (goc / "core").mkdir()
    (goc / "core" / "mock.py").write_text("print('ma tool')\n", encoding="utf-8")
    (goc / "secrets.json").write_text('{"khoa": "bi-mat"}', encoding="utf-8")
    (goc / "config.json").write_text('{"rieng": "cua may"}', encoding="utf-8")
    (goc / "workspace").mkdir()
    (goc / "workspace" / "rac.txt").write_text("rac", encoding="utf-8")

    # Kênh KHUÔN MẪU — phải vào tool.zip (mau_cua_tool: true).
    khuon = goc / "CHANNEL" / "KHUON1"
    khuon.mkdir(parents=True)
    (khuon / "kenh.yaml").write_text("ma: KHUON1\nmau_cua_tool: true\n",
                                     encoding="utf-8")

    # Kênh THẬT — dữ liệu kinh doanh, KHÔNG được vào tool.zip, chỉ vào kenh/.
    that = goc / "CHANNEL" / "TL4-T7"
    that.mkdir(parents=True)
    (that / "kenh.yaml").write_text("ma: TL4-T7\nten: Kenh that\n",
                                    encoding="utf-8")
    (that / "chi-so").mkdir()
    (that / "chi-so" / "tong-quan.json").write_text('{"view": 123}',
                                                     encoding="utf-8")


def _goi(goc: Path, **kwargs):
    from core.goi_vps import dong_goi_vps

    nhat_ky = []
    ket = dong_goi_vps(str(goc), on_log=nhat_ky.append, **kwargs)
    return ket, nhat_ky


# ── core.goi_vps.dong_goi_vps ────────────────────────────────────────────────


class TestDongGoiVPS:
    def test_thieu_kenh_thi_bao_loi_ro(self, tmp_path):
        from core.goi_vps import dong_goi_vps

        _dung_tool_gia(tmp_path)
        with pytest.raises(ValueError):
            dong_goi_vps(str(tmp_path), kenh_mang_theo=[])

    def test_tool_zip_giu_ma_loai_bi_mat_va_kenh_khong_phai_khuon(self, tmp_path):
        _dung_tool_gia(tmp_path)
        ket, _log = _goi(tmp_path, kenh_mang_theo=["TL4-T7"])

        duong_zip = tmp_path / "vm" / "goi-vps" / "tool.zip"
        assert duong_zip.is_file()
        with zipfile.ZipFile(duong_zip) as zf:
            ten = set(zf.namelist())

        assert "core/mock.py" in ten
        assert "VERSION" in ten
        assert "CHANNEL/KHUON1/kenh.yaml" in ten, "kênh khuôn mẫu phải vào tool.zip"
        assert "secrets.json" not in ten
        assert "config.json" not in ten
        assert not any(t.startswith("workspace/") for t in ten)
        assert not any(t.startswith("vm/") for t in ten), "vm/ tự gói, không lặp vào tool.zip"
        assert not any(t.startswith("CHANNEL/TL4-T7/") for t in ten), \
            "kênh THẬT không phải khuôn mẫu — dữ liệu đi qua kenh/, không qua tool.zip"

    def test_du_lieu_kenh_that_duoc_chep_day_du_rieng(self, tmp_path):
        _dung_tool_gia(tmp_path)
        ket, _log = _goi(tmp_path, kenh_mang_theo=["TL4-T7"])

        dich = tmp_path / "vm" / "goi-vps" / "kenh" / "TL4-T7"
        assert (dich / "kenh.yaml").is_file()
        assert (dich / "chi-so" / "tong-quan.json").is_file(), \
            "chi-so/ bị .gitignore chặn khỏi tool.zip nhưng PHẢI có trong kenh/"

    def test_manifest_va_config_vps(self, tmp_path):
        goc = _gia(tmp_path)
        ket, _log = _goi(goc, kenh_mang_theo=["TL4-T7", "KHUON1"])

        manifest = ket["manifest"]
        assert manifest["phien_ban"] == "9.9.9"
        assert manifest["kenh"] == ["TL4-T7", "KHUON1"]
        assert manifest["tool_zip"]["sha256"]
        assert manifest["tool_zip"]["bytes"] > 0

        duong_manifest = goc / "vm" / "goi-vps" / "vps-manifest.json"
        assert json.loads(duong_manifest.read_text(encoding="utf-8")) == manifest

        cau_hinh = json.loads((goc / "vm" / "config.json").read_text(encoding="utf-8"))
        assert cau_hinh["tram"] == "http://127.0.0.1:8765"
        assert cau_hinh["cac_kenh"] == ["TL4-T7", "KHUON1"]
        assert cau_hinh["che_do_phien"] is True
        assert cau_hinh["kenh"] == "TL4-T7"
        assert cau_hinh["NGUON"] == "tool", "vẫn giữ các khoá cũ của dong_goi_vm"

    def test_khong_co_ffmpeg_whisper_thi_bao_that_khong_nem_loi(self, tmp_path, monkeypatch):
        # Cô lập khỏi bộ đệm HuggingFace THẬT của máy đang chạy test — máy
        # phát triển có thể đã tải sẵn bộ nghe cho việc khác.
        monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hf-rong"))
        # Cùng lý do: máy phát triển có FFmpeg thật (PATH hoặc imageio-ffmpeg)
        # — giả lập máy trắng để bài kiểm không phụ thuộc máy đang chạy nó.
        import core.dung_video as dung_video_mod

        monkeypatch.setattr(dung_video_mod, "tim_ffmpeg", lambda _goc="": "")
        goc = _gia(tmp_path)
        ket, log = _goi(goc, kenh_mang_theo=["TL4-T7"])
        assert ket["manifest"]["whisper"]["co"] is False
        assert ket["manifest"]["ffmpeg"]["co"] is False
        assert any("chua" in d.lower() or "chưa" in d.lower() for d in log)

    def test_thu_muc_vm_tuy_chinh_khong_dung_vao_vm_that(self, tmp_path):
        """`thu_muc_vm` cho phép nhắm output ra khỏi `<goc>/vm` thật — dùng để
        đo trên máy thật mà không tạo gói trong `vm/` đang chạy."""
        goc = _gia(tmp_path)
        rieng = tmp_path / "noi-khac"
        ket, _log = _goi(goc, kenh_mang_theo=["TL4-T7"], thu_muc_vm=str(rieng))
        assert (rieng / "goi-vps" / "tool.zip").is_file()
        assert not (goc / "vm" / "goi-vps").exists()

    def test_huy_truoc_khi_bat_dau_thi_khong_lam_gi(self, tmp_path):
        goc = _gia(tmp_path)
        huy = Event()
        huy.set()
        from core.goi_vps import dong_goi_vps

        ket = dong_goi_vps(str(goc), kenh_mang_theo=["TL4-T7"], cancel=huy)
        assert ket == {"huy": True}
        assert not (goc / "vm" / "goi-vps" / "tool.zip").exists()


def _gia(tmp_path) -> Path:
    goc = tmp_path / "tool"
    goc.mkdir()
    _dung_tool_gia(goc)
    return goc


# ── vm/cai_dat_vps.py — giải nén, dữ liệu kênh, thư viện, whisper/ffmpeg ─────


class TestGiaiNenToolZip:
    def _tep_zip(self, tmp_path) -> Path:
        duong = tmp_path / "tool.zip"
        with zipfile.ZipFile(duong, "w") as zf:
            zf.writestr("core/a.py", "print(1)\n")
            zf.writestr("VERSION", "1.2.3\n")
            zf.writestr("CHANNEL/K1/kenh.yaml", "ma: K1\n")
            zf.writestr("config.json", "khong bao gio that su co trong zip")
        return duong

    def test_lan_dau_ghi_het(self, tmp_path):
        mod = _nap_cai_dat_vps()
        duong_zip = self._tep_zip(tmp_path)
        mytool = tmp_path / "MyTool"
        ket = mod.giai_nen_tool_zip(str(duong_zip), str(mytool))
        assert (mytool / "core" / "a.py").is_file()
        assert (mytool / "VERSION").read_text() == "1.2.3\n"
        assert (mytool / "CHANNEL" / "K1" / "kenh.yaml").is_file()
        assert (mytool / "config.json").is_file()
        assert ket == {"ghi": 4, "giu": 0}, "lần đầu MyTool trống — ghi hết, không có gì để giữ"

    def test_lan_sau_khong_de_du_lieu_da_co(self, tmp_path):
        mod = _nap_cai_dat_vps()
        duong_zip = self._tep_zip(tmp_path)
        mytool = tmp_path / "MyTool"
        mytool.mkdir()
        (mytool / "config.json").write_text('{"that": true}', encoding="utf-8")
        (mytool / "CHANNEL" / "K1").mkdir(parents=True)
        (mytool / "CHANNEL" / "K1" / "kenh.yaml").write_text(
            "ma: K1\nda_chinh_tay: true\n", encoding="utf-8")

        ket = mod.giai_nen_tool_zip(str(duong_zip), str(mytool))

        assert json.loads((mytool / "config.json").read_text(encoding="utf-8")) == {"that": True}, \
            "config.json thật (nếu có) không bao giờ bị đè"
        assert "da_chinh_tay" in (mytool / "CHANNEL" / "K1" / "kenh.yaml").read_text(encoding="utf-8"), \
            "kênh đã có trên VPS thì GIỮ NGUYÊN, không đè bằng bản mẫu"
        assert (mytool / "core" / "a.py").is_file(), "mã vẫn phải được ghi/đè"
        assert ket == {"ghi": 2, "giu": 2}


class TestDatKenh:
    def test_chi_chep_khi_chua_co(self, tmp_path):
        mod = _nap_cai_dat_vps()
        goi = tmp_path / "goi-vps"
        (goi / "kenh" / "TL4-T7").mkdir(parents=True)
        (goi / "kenh" / "TL4-T7" / "kenh.yaml").write_text("ma: TL4-T7\n",
                                                            encoding="utf-8")
        mytool = tmp_path / "MyTool"

        ket1 = mod.dat_kenh(str(goi), str(mytool))
        assert ket1["TL4-T7"] == "moi"
        assert (mytool / "CHANNEL" / "TL4-T7" / "kenh.yaml").is_file()

        # Kênh trên VPS đổi khác đi sau khi cài lần đầu — lần sau KHÔNG đụng.
        (mytool / "CHANNEL" / "TL4-T7" / "moi.txt").write_text("da doi", encoding="utf-8")
        ket2 = mod.dat_kenh(str(goi), str(mytool))
        assert ket2["TL4-T7"] == "giu_nguyen"
        assert (mytool / "CHANNEL" / "TL4-T7" / "moi.txt").is_file()


class TestCaiThuVien:
    def test_goi_dung_python_va_tung_tep_yeu_cau(self, tmp_path):
        mod = _nap_cai_dat_vps()
        mytool = tmp_path / "MyTool"
        mytool.mkdir()
        (mytool / "requirements.txt").write_text("a\n", encoding="utf-8")
        vm_dir = tmp_path / "vm"
        vm_dir.mkdir()
        (vm_dir / "requirements-vm.txt").write_text("b\n", encoding="utf-8")

        goi = []

        def chay_gia(lenh):
            goi.append(list(lenh))
            return 0, ""

        ket = mod.cai_thu_vien("PYTHON.EXE", str(mytool), str(vm_dir), chay=chay_gia)
        assert ket["MyTool"]["ok"] is True
        assert ket["vm"]["ok"] is True
        assert ket["MyTool (builder)"]["ok"] is True  # tệp không tồn tại nhưng TUỲ CHỌN — không tính là hỏng
        duong_da_goi = {tuple(l) for l in goi}
        assert ("PYTHON.EXE", "-m", "pip", "install", "-q", "-r",
                str(mytool / "requirements.txt")) in duong_da_goi
        assert ("PYTHON.EXE", "-m", "pip", "install", "-q", "-r",
                str(vm_dir / "requirements-vm.txt")) in duong_da_goi

    def test_thu_lai_toi_ba_lan_roi_bao_that(self, tmp_path):
        mod = _nap_cai_dat_vps()
        mytool = tmp_path / "MyTool"
        mytool.mkdir()
        (mytool / "requirements.txt").write_text("a\n", encoding="utf-8")

        so_lan = {"n": 0}

        def chay_gia(_lenh):
            so_lan["n"] += 1
            return 1, "loi mang"

        ket = mod.cai_thu_vien("PY", str(mytool), str(tmp_path / "khong-co-vm"),
                               chay=chay_gia)
        assert ket["MyTool"]["ok"] is False
        assert "loi mang" in ket["MyTool"]["loi"]
        assert so_lan["n"] == 3, "phải thử đúng 3 lần trước khi bỏ cuộc"


class TestWhisperFfmpeg:
    def test_whisper_dat_lan_dau_khong_de_lan_sau(self, tmp_path):
        mod = _nap_cai_dat_vps()
        goi = tmp_path / "goi-vps"
        nguon = goi / "whisper"
        nguon.mkdir(parents=True)
        (nguon / "model.bin").write_text("gia", encoding="utf-8")
        mytool = tmp_path / "MyTool"

        ket1 = mod.dat_whisper(str(goi), str(mytool))
        assert ket1 == {"co": True, "moi": True,
                        "duong": str(mytool / "models" / mod.TEN_MODEL_WHISPER)}
        assert (mytool / "models" / mod.TEN_MODEL_WHISPER / "model.bin").is_file()

        ket2 = mod.dat_whisper(str(goi), str(mytool))
        assert ket2["moi"] is False

    def test_khong_mang_theo_whisper_thi_bao_that(self, tmp_path):
        mod = _nap_cai_dat_vps()
        ket = mod.dat_whisper(str(tmp_path / "goi-vps"), str(tmp_path / "MyTool"))
        assert ket == {"co": False}

    def test_ffmpeg_giu_cau_truc_bin_de_tim_ffmpeg_da_tai_thay(self, tmp_path):
        mod = _nap_cai_dat_vps()
        goi = tmp_path / "goi-vps"
        (goi / "ffmpeg" / "ffmpeg-7.1" / "bin").mkdir(parents=True)
        (goi / "ffmpeg" / "ffmpeg-7.1" / "bin" / "ffmpeg.exe").write_text("gia", encoding="utf-8")
        mytool = tmp_path / "MyTool"

        ket = mod.dat_ffmpeg(str(goi), str(mytool))
        assert ket["co"] is True and ket["moi"] is True
        duong_exe = mytool / "runtime" / "ffmpeg-7.1" / "bin" / "ffmpeg.exe"
        assert duong_exe.is_file()

        # `core.dung_video.tim_ffmpeg` phải TỰ THẤY được đường này.
        sys.path.insert(0, str(GOC))
        from core.ffmpeg_goi_san import tim_ffmpeg_da_tai
        assert tim_ffmpeg_da_tai(str(mytool)) == str(duong_exe)

        ket2 = mod.dat_ffmpeg(str(goi), str(mytool))
        assert ket2["moi"] is False


class TestMocVaTram:
    def test_ghi_vps_json(self, tmp_path):
        mod = _nap_cai_dat_vps()
        mytool = tmp_path / "MyTool"
        mytool.mkdir()
        duong = mod.ghi_vps_json(str(mytool), str(tmp_path / "vm"))
        du_lieu = json.loads(Path(duong).read_text(encoding="utf-8"))
        assert du_lieu["vm_dir"] == str((tmp_path / "vm").resolve()) or \
            os.path.normcase(du_lieu["vm_dir"]) == os.path.normcase(str(tmp_path / "vm"))
        assert du_lieu["tao_luc"] > 0

    def test_bao_dam_tram_loopback_sua_khi_lech(self, tmp_path):
        mod = _nap_cai_dat_vps()
        vm_dir = tmp_path / "vm"
        vm_dir.mkdir()
        (vm_dir / "config.json").write_text(
            json.dumps({"tram": "http://may-nha:8765", "kenh": "X"}), encoding="utf-8")
        cai = mod.bao_dam_tram_loopback(str(vm_dir))
        assert cai["tram"] == mod.TRAM_VPS
        assert cai["che_do_phien"] is True
        tren_dia = json.loads((vm_dir / "config.json").read_text(encoding="utf-8"))
        assert tren_dia["tram"] == mod.TRAM_VPS
        assert tren_dia["kenh"] == "X", "khoá khác không bị mất"

    def test_bao_dam_tram_loopback_dung_neu_da_dung(self, tmp_path):
        mod = _nap_cai_dat_vps()
        vm_dir = tmp_path / "vm"
        vm_dir.mkdir()
        duong = vm_dir / "config.json"
        duong.write_text(json.dumps({"tram": mod.TRAM_VPS, "che_do_phien": True}),
                         encoding="utf-8")
        mtime_truoc = duong.stat().st_mtime_ns
        mod.bao_dam_tram_loopback(str(vm_dir))
        assert duong.stat().st_mtime_ns == mtime_truoc, "đã đúng thì không ghi lại"


class TestHoSoPhatTrien:
    def test_chep_claude_local_luon_de_tao_nhat_ky_chi_lan_dau(self, tmp_path):
        mod = _nap_cai_dat_vps()
        vm_dir = tmp_path / "vm"
        vm_dir.mkdir()
        (vm_dir / "VPS-CLAUDE.md").write_text("ban 1", encoding="utf-8")
        mytool = tmp_path / "MyTool"
        mytool.mkdir()
        (mytool / "NHAT-KY-PHAT-TRIEN.md").write_text("nhat ky rieng cua toi",
                                                       encoding="utf-8")

        mod.dat_ho_so_phat_trien(str(vm_dir), str(mytool))
        assert (mytool / "CLAUDE.local.md").read_text(encoding="utf-8") == "ban 1"
        assert (mytool / "NHAT-KY-PHAT-TRIEN.md").read_text(encoding="utf-8") == \
            "nhat ky rieng cua toi", "nhật ký CỦA CHỦ không bao giờ bị đè"
        assert (mytool / "workspace" / "ban-va").is_dir()

        (vm_dir / "VPS-CLAUDE.md").write_text("ban 2", encoding="utf-8")
        mod.dat_ho_so_phat_trien(str(vm_dir), str(mytool))
        assert (mytool / "CLAUDE.local.md").read_text(encoding="utf-8") == "ban 2", \
            "CLAUDE.local.md LUON duoc cap nhat theo ban moi nhat"


class TestLoiTatVaMoTool:
    def test_cam_loi_tat_goi_powershell_don_doi_cu(self, tmp_path):
        mod = _nap_cai_dat_vps()
        mytool = tmp_path / "MyTool"
        (mytool / "ui_qt").mkdir(parents=True)
        (mytool / "CHAY-GON.vbs").write_text("' gia", encoding="utf-8")

        goi = []

        def chay_gia(lenh):
            goi.append(list(lenh))
            return 0, ""

        ok = mod.cam_loi_tat_vps(str(mytool), chay=chay_gia)
        assert ok is True
        ma_lenh = " ".join(goi[0])
        assert "MyTool VM.lnk" in ma_lenh
        assert "shopapi-vm-agent.bat" in ma_lenh
        assert "MyTool VPS.lnk" in ma_lenh

    def test_khong_co_chay_gon_thi_bao_that_khong_nem_loi(self, tmp_path):
        mod = _nap_cai_dat_vps()
        assert mod.cam_loi_tat_vps(str(tmp_path / "khong-ton-tai")) is False

    def test_khoi_dong_mytool_truyen_whisper_model_dir(self, tmp_path):
        mod = _nap_cai_dat_vps()
        mytool = tmp_path / "MyTool"
        mytool.mkdir()
        (mytool / "CHAY-GON.vbs").write_text("' gia", encoding="utf-8")

        goi = []
        ok = mod.khoi_dong_mytool(
            str(mytool), whisper_dir=str(tmp_path / "models" / "x"),
            chay_popen=lambda lenh, env: goi.append((list(lenh), dict(env))))
        assert ok is True
        lenh, env = goi[0]
        assert lenh[0] == "wscript.exe"
        assert env["WHISPER_MODEL_DIR"] == str(tmp_path / "models" / "x")


class TestBaoDamPython:
    def test_python_dang_dung_tu_choi_windowsapps(self, tmp_path, monkeypatch):
        mod = _nap_cai_dat_vps()
        gia = tmp_path / "WindowsApps" / "python.exe"
        gia.parent.mkdir(parents=True)
        gia.write_text("gia", encoding="utf-8")
        monkeypatch.setattr(mod.sys, "executable", str(gia))
        assert mod.python_dang_dung() == ""

    def test_python_dang_dung_binh_thuong_thi_dung_luon(self, monkeypatch):
        mod = _nap_cai_dat_vps()
        assert mod.python_dang_dung() == sys.executable

    def test_khong_co_python_thi_tai_va_cai(self, tmp_path, monkeypatch):
        mod = _nap_cai_dat_vps()
        monkeypatch.setattr(mod.sys, "executable",
                            str(tmp_path / "WindowsApps" / "python.exe"))
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
        monkeypatch.setenv("TEMP", str(tmp_path / "temp"))

        goi_chay = []

        def chay_gia(lenh):
            goi_chay.append(list(lenh))
            if lenh[0] in ("py", "python"):
                return 1, ""  # chưa có gì trên máy
            # lệnh cài .exe: giả lập kết quả — cũng tạo luôn python.exe đích
            duong_cai = Path(tmp_path / "local" / "Programs" / "Python" / "Python311")
            duong_cai.mkdir(parents=True, exist_ok=True)
            (duong_cai / "python.exe").write_text("gia", encoding="utf-8")
            return 0, ""

        ra = mod.bao_dam_python(chay=chay_gia, tai=lambda _url: b"noi dung gia")
        assert ra.endswith("python.exe")
        assert os.path.isfile(ra)
        # Đã thử "py -3" và "python" trước khi tải.
        lenh_dau = [l[0] for l in goi_chay]
        assert "py" in lenh_dau or "python" in lenh_dau


# ── vm/CAI-DAT-VM.bat: chọn nhánh đúng khi có/không có goi-vps/ ─────────────


@pytest.mark.skipif(sys.platform != "win32", reason="chỉ chạy .bat trên Windows")
class TestChonNhanhBat:
    def _chay_bat(self, tmp_path, **tep) -> str:
        import shutil

        duong_bat = tmp_path / "CAI-DAT-VM.bat"
        shutil.copyfile(GOC / "vm" / "CAI-DAT-VM.bat", duong_bat)
        for ten, noi_dung in tep.items():
            duong = tmp_path / ten
            duong.parent.mkdir(parents=True, exist_ok=True)
            duong.write_text(noi_dung, encoding="utf-8")
        ket = subprocess.run(
            [str(duong_bat)], cwd=str(tmp_path), input="", capture_output=True,
            text=True, timeout=60)
        return ket.stdout

    def test_co_goi_vps_thi_goi_cai_dat_vps(self, tmp_path):
        ra = self._chay_bat(
            tmp_path,
            **{
                "goi-vps/tool.zip": "gia",
                "cai_dat_vps.py": "print('DA_VAO_CAI_DAT_VPS')",
                "requirements-vm.txt": "",
            })
        assert "DA_VAO_CAI_DAT_VPS" in ra

    def test_khong_co_goi_vps_thi_di_duong_cu(self, tmp_path):
        ra = self._chay_bat(
            tmp_path,
            **{
                "cai_dat_vm.py": "print('DA_VAO_CAI_DAT_VM_CU')",
                "requirements-vm.txt": "",
            })
        assert "DA_VAO_CAI_DAT_VM_CU" in ra


def test_gitignore_chan_goi_vps_va_claude_local():
    """`vm/goi-vps/` (nặng, dữ liệu kênh thật) và `CLAUDE.local.md` (VPS tự
    sinh từ `vm/VPS-CLAUDE.md`) không bao giờ lên kho công khai."""
    noi_dung = (GOC / ".gitignore").read_text(encoding="utf-8")
    assert "vm/goi-vps/" in noi_dung
    assert "CLAUDE.local.md" in noi_dung
