"""Bộ cài VPS: dữ liệu kênh THẬT phải vào trước khi giải nén mã.

`tool.zip` mang bản KHUÔN MẪU của kênh mẫu (vd TL4-T7). Giải nén trước thì
thư mục kênh khuôn mẫu có mặt, `dat_kenh` thấy "đã có" và bỏ qua dữ liệu thật
(18/09/2026: suýt mất 860 MB chỉ số/nghiên cứu của TL4-T7 khi đóng gói thật).
"""

import importlib.util
import os
import zipfile

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _nap_bo_cai():
    spec = importlib.util.spec_from_file_location(
        "cai_dat_vps_thu_tu", os.path.join(GOC, "vm", "cai_dat_vps.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_du_lieu_kenh_that_thang_khuon_mau_trong_zip(tmp_path, monkeypatch):
    m = _nap_bo_cai()
    goi = tmp_path / "vm" / "goi-vps"
    (goi / "kenh" / "TL4-T7" / "chi-so").mkdir(parents=True)
    (goi / "kenh" / "TL4-T7" / "chi-so" / "that.csv").write_text("so that", encoding="utf-8")
    (goi / "kenh" / "TL4-T7" / "kenh.yaml").write_text("ma: TL4-T7  # THAT\n", encoding="utf-8")
    with zipfile.ZipFile(goi / "tool.zip", "w") as zf:
        zf.writestr("CHANNEL/TL4-T7/kenh.yaml", "ma: TL4-T7  # KHUON MAU\n")
        zf.writestr("core/x.py", "X = 1\n")
    mytool = tmp_path / "MyTool"

    monkeypatch.setattr(m, "GOC", str(tmp_path / "vm"))
    monkeypatch.setattr(m, "GOI_VPS", str(goi))
    monkeypatch.setattr(m, "MYTOOL", str(mytool))
    monkeypatch.setattr(m, "bao_dam_python", lambda **k: "python")
    monkeypatch.setattr(m, "cai_thu_vien", lambda *a, **k: {})
    monkeypatch.setattr(m, "cam_loi_tat_vps", lambda *a, **k: True)
    monkeypatch.setattr(m, "khoi_dong_mytool", lambda *a, **k: True)

    m.cai(bao=lambda _d: None)

    kenh = mytool / "CHANNEL" / "TL4-T7"
    assert (kenh / "chi-so" / "that.csv").is_file()
    assert "THAT" in (kenh / "kenh.yaml").read_text(encoding="utf-8")
    assert (mytool / "core" / "x.py").is_file()
