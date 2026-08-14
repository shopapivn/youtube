"""Tab **Prompt Visuals**: file giọng đọc → phụ đề → prompt từng cảnh → Excel.

Chủ dự án, 14/08/2026: *"từ mp3 voice ra srt rồi sau đó chạy ra các prompt trong
excel"*, làm theo `D:\\VE3_SUITE`.

Cột của file Excel sinh ra **trùng tên với bảng của VE3_SUITE** (`scenes`,
`characters`, `director_plan`, `thumbnail`), nên mở thẳng bằng VE3 được.

Phần nghĩ nằm ở `core/prompt_visuals.py` (thuần tuý, test được) và ở hai tool
trong `tool-catalog/`. Tệp này chỉ dựng nút, hỏi cho rõ trước khi tiêu tiền, và
đổ kết quả ra màn hình.

LƯU Ý: bước viết prompt **tiêu ví ShopAPI**. Nên trang này nói giá bằng lời trước khi
chạy, và không bao giờ tự chạy khi mở tab.
"""

from __future__ import annotations

import os
import threading
from typing import List, Optional

from PyQt5.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QProgressBar,
    QVBoxLayout, QWidget,
)

from core.prompt_visuals import (
    ENGINE, MA_MODEL_NGHE, MO_HINH, NGON_NGU, cau_thieu_gi, dung_workflow,
)

from . import theme
from .widgets import (
    ChonThuMuc, HangXuongDong, mo_thu_muc, nhan, nut_chinh, nut_phu, the,
    tieu_de_trang,
)

__all__ = ["TrangPromptVisuals"]

#: Đuôi file giọng đọc nhận vào.
DUOI_TIENG = ("*.mp3", "*.wav", "*.m4a", "*.aac", "*.flac", "*.ogg")


class TrangPromptVisuals(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._files: List[str] = []
        self._huy: Optional[threading.Event] = None
        self._da_xong: List[str] = []
        self._thu_muc_da_xuat = ""

        doc = QVBoxLayout(self)
        doc.setContentsMargins(24, 20, 24, 20)
        doc.setSpacing(14)
        doc.addWidget(tieu_de_trang(
            "Prompt Visuals",
            "Giọng đọc → phụ đề → prompt từng cảnh → file Excel."))
        doc.addWidget(self._the_nhap())
        doc.addWidget(self._the_chay())
        doc.addStretch(1)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setFixedHeight(120)
        self._log.setStyleSheet(
            "background:{0}; border:1px solid {1}; border-radius:8px;"
            " color:{2}; font-size:12px;".format(theme.THE_MO, theme.VIEN,
                                                 theme.CHU_MO))
        doc.addWidget(self._log)
        self._ve_trang_thai()

    # ── Dựng giao diện ───────────────────────────────────────────────────────

    def _the_nhap(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(10)
        v.addWidget(nhan("1. Chọn file giọng đọc", "h2"))

        hang = HangXuongDong()
        hang.addWidget(nut_phu("Chọn file…", self._chon_file, rong=150))
        hang.addWidget(nut_phu("Bỏ danh sách", self._bo_file, rong=150))
        v.addLayout(hang)

        self._nhan_file = nhan("Chưa chọn file nào.", "phu")
        self._nhan_file.setWordWrap(True)
        self._nhan_file.setMinimumWidth(1)
        v.addWidget(self._nhan_file)

        v.addWidget(nhan("2. Cắt cảnh và viết prompt theo", "h2"))
        chon = HangXuongDong()
        self._engine = self._o_chon(ENGINE, chon, "Engine dựng video")
        self._mo_hinh = self._o_chon(MO_HINH, chon, "Mô hình viết prompt")
        self._ngon_ngu = self._o_chon(NGON_NGU, chon, "Tiếng trong file")
        v.addLayout(chon)
        return khung

    def _o_chon(self, muc, hang, mach: str) -> QComboBox:
        o = QComboBox()
        for ma, ten in muc:
            o.addItem(ten, ma)
        o.setToolTip(mach)
        o.setMinimumWidth(1)
        hang.addWidget(o)
        return o

    def _the_chay(self) -> QWidget:
        khung = the()
        v = QVBoxLayout(khung)
        v.setContentsMargins(18, 16, 18, 18)
        v.setSpacing(10)
        v.addWidget(nhan("3. Chạy", "h2"))

        # Nói giá TRƯỚC nút bấm, không phải sau. Bước nghe chạy trên máy nên
        # miễn phí; bước viết prompt gọi AI nên tiêu ví — người bấm phải biết
        # trước cái nào là cái nào.
        v.addWidget(self._chu_phu(
            "Bước nghe chạy trên máy bạn, miễn phí. Bước viết prompt gọi AI nên "
            "có tiêu ví ShopAPI — mỗi 20 cảnh một lượt gọi."))

        self._canh_bao = self._chu_phu("")
        self._canh_bao.setStyleSheet("color:{0};".format(theme.VANG))
        self._canh_bao.hide()
        v.addWidget(self._canh_bao)

        hang = HangXuongDong()
        self._nut_chay = nut_chinh("Tạo prompt", self._chay)
        self._nut_chay.setFixedWidth(200)
        hang.addWidget(self._nut_chay)
        self._nut_dung = nut_phu("Dừng", self._dung, rong=96)
        self._nut_dung.setEnabled(False)
        hang.addWidget(self._nut_dung)
        self._nut_tai = nut_phu("Tải bộ nghe", self._tai_model, rong=160)
        self._nut_tai.setToolTip(
            "Tải bộ nghe tiếng ({0}) về máy — khoảng 0,5 GB, chỉ một lần. "
            "Không tiêu ví ShopAPI.".format(MA_MODEL_NGHE))
        hang.addWidget(self._nut_tai)
        self._nut_mo = nut_phu("Mở kết quả",
                               lambda: mo_thu_muc(self._thu_muc_da_xuat),
                               rong=150)
        self._nut_mo.setEnabled(False)
        hang.addWidget(self._nut_mo)
        v.addLayout(hang)

        self._thanh = QProgressBar()
        self._thanh.setRange(0, 100)
        self._thanh.setValue(0)
        self._thanh.setTextVisible(True)
        v.addWidget(self._thanh)

        self._thu_muc = ChonThuMuc(self._app.default_output_dir("prompt-visuals"))
        v.addWidget(self._thu_muc)
        return khung

    @staticmethod
    def _chu_phu(chu: str) -> QLabel:
        nh = nhan(chu, "phu")
        nh.setWordWrap(True)
        nh.setMinimumWidth(1)
        return nh

    # ── Trạng thái máy ───────────────────────────────────────────────────────

    def _dich_vu(self):
        """`BuilderService` gắn với ví của người dùng.

        Dựng mới mỗi lần hỏi chứ không giữ sẵn: người dùng có thể vừa đăng nhập
        ở tab Tài khoản xong, mà bản giữ sẵn thì vẫn ôm cái khoá rỗng cũ.
        """
        from core.builder_service import BuilderService  # noqa: PLC0415

        def bi_mat():
            return {"SHOPAPI_API_KEY": (self._app.config.api_key or "").strip(),
                    "SHOPAPI_BASE_URL": self._app.config.base_url or ""}

        return BuilderService(self._app.base_dir, shopapi_secret=bi_mat)

    def _ve_trang_thai(self) -> None:
        """Hỏi máy còn thiếu gì, rồi nói ra bằng tiếng người."""
        try:
            dv = self._dich_vu()
            wf = dung_workflow("kiem-tra", ma_chay="prompt-visuals-kiemtra")
            thieu = cau_thieu_gi(dv.readiness(wf).issues)
        except Exception as loi:  # noqa: BLE001 — dò hỏng không được chặn tab
            thieu = ["Chưa dò được máy: {0}".format(loi)]
        if thieu:
            self._canh_bao.setText("Chưa chạy được:\n• " + "\n• ".join(thieu))
            self._canh_bao.show()
        else:
            self._canh_bao.hide()
        self._nut_tai.setVisible(any(MA_MODEL_NGHE in c for c in thieu))
        self._nut_chay.setEnabled(not thieu and bool(self._files))

    def showEvent(self, su_kien):  # noqa: N802 — tên do Qt quy định
        """Dò lại mỗi lần mở tab: người dùng có thể vừa tải bộ nghe hoặc vừa
        đăng nhập ở tab khác."""
        super().showEvent(su_kien)
        self._ve_trang_thai()

    # ── Chọn file ────────────────────────────────────────────────────────────

    def _chon_file(self) -> None:
        duong, _ = QFileDialog.getOpenFileNames(
            self, "Chọn file giọng đọc", "",
            "Âm thanh ({0});;Tất cả (*.*)".format(" ".join(DUOI_TIENG)))
        if not duong:
            return
        for d in duong:
            if d not in self._files:
                self._files.append(d)
        self._ve_danh_sach()

    def _bo_file(self) -> None:
        self._files = []
        self._ve_danh_sach()

    def _ve_danh_sach(self) -> None:
        if not self._files:
            self._nhan_file.setText("Chưa chọn file nào.")
        else:
            ten = [os.path.basename(d) for d in self._files]
            self._nhan_file.setText("{0} file: {1}".format(
                len(ten), ", ".join(ten[:6]) + ("…" if len(ten) > 6 else "")))
        self._ve_trang_thai()

    # ── Chạy ─────────────────────────────────────────────────────────────────

    def _chay(self) -> None:
        if not self._files:
            self._app.show_message("Chưa có file",
                                   "Bấm “Chọn file…” để chọn file giọng đọc.")
            return
        engine = self._engine.currentData()
        mo_hinh = self._mo_hinh.currentData()
        ngon_ngu = self._ngon_ngu.currentData()
        files = list(self._files)

        self._huy = threading.Event()
        huy = self._huy
        self._nut_chay.setEnabled(False)
        self._nut_dung.setEnabled(True)
        self._da_xong = []
        self._thanh.setValue(0)
        self._ghi("Bắt đầu — {0} file.".format(len(files)))

        def viec() -> List[str]:
            return self._chay_nen(files, engine, mo_hinh, ngon_ngu, huy)

        self._app.run_bg(viec, on_ok=self._xong, on_err=self._hong)

    def _chay_nen(self, files, engine, mo_hinh, ngon_ngu, huy) -> List[str]:
        """LUỒNG NỀN. Không chạm widget — mọi câu chữ đi qua `_ghi_nen`."""
        from core.artifacts import LocalArtifactStore  # noqa: PLC0415
        from core.workflow_runner import CancellationToken  # noqa: PLC0415

        dv = self._dich_vu()
        ra: List[str] = []
        for thu_tu, duong in enumerate(files, start=1):
            if huy.is_set():
                self._ghi_nen("Đã dừng — xong {0}/{1} file.".format(
                    len(ra), len(files)))
                break
            ten = os.path.basename(duong)
            self._ghi_nen("[{0}/{1}] {2}".format(thu_tu, len(files), ten))
            try:
                # Nạp file vào kho artifact của Studio: runner chỉ làm việc với
                # mã artifact, không nhận đường dẫn trần.
                kho: LocalArtifactStore = dv.artifacts
                ma = kho.put_file(duong, kind="audio",
                                  schema="narration-audio.v1")
                ma_chay = "pv-" + _ma_an_toan(ten) or "pv-chay"
                wf = dung_workflow(_ma_artifact(ma), engine=engine,
                                   mo_hinh=mo_hinh, ngon_ngu=ngon_ngu,
                                   ma_chay=ma_chay)
                huy_token = CancellationToken()
                if huy.is_set():
                    break

                def bao(su_kien, _ten=ten):
                    loi_nhan = getattr(su_kien, "message", "") or ""
                    tien = getattr(su_kien, "progress", None)
                    if loi_nhan:
                        self._ghi_nen("    " + str(loi_nhan))
                    if isinstance(tien, (int, float)):
                        self._tien_nen(float(tien))

                trang_thai = dv.run(
                    wf,
                    approved_permissions=("workspace.read", "workspace.write",
                                          "compute.local", "network.shopapi",
                                          "secret.shopapi"),
                    cancellation=huy_token, on_event=bao)
                duong_xlsx = self._tim_workbook(dv, trang_thai)
                if duong_xlsx:
                    dich = self._chep_ra(duong_xlsx, ten)
                    ra.append(dich)
                    self._ghi_nen("  xong: đã tạo {0}".format(os.path.basename(dich)))
                else:
                    self._ghi_nen("  không được: chạy xong nhưng không thấy file Excel đâu")
            except Exception as loi:  # noqa: BLE001 — một file hỏng không giết lượt
                self._ghi_nen("  không được: {0}".format(str(loi)[:200]))
        return ra

    @staticmethod
    def _tim_workbook(dv, trang_thai) -> str:
        """Lấy đường dẫn file Excel từ artifact mà bước prompt trả về."""
        nut = getattr(trang_thai, "nodes", {}) or {}
        buoc = nut.get("prompt")
        if buoc is None or getattr(buoc, "status", "") != "succeeded":
            return ""
        ma = (getattr(buoc, "outputs", {}) or {}).get("workbook")
        if not ma:
            return ""
        try:
            return str(dv.artifacts.path(ma if isinstance(ma, str) else ma[0]))
        except Exception:  # noqa: BLE001
            return ""

    def _chep_ra(self, nguon: str, ten_tieng: str) -> str:
        """Chép file Excel ra thư mục người dùng chọn, tên theo file giọng đọc.

        Để nguyên trong kho artifact thì tên là một chuỗi băm — mở ra không biết
        của file nào.
        """
        import shutil  # noqa: PLC0415

        thu_muc = self._thu_muc.value
        os.makedirs(thu_muc, exist_ok=True)
        goc = os.path.splitext(os.path.basename(ten_tieng))[0]
        dich = os.path.join(thu_muc, "{0} - prompts.xlsx".format(goc))
        shutil.copyfile(nguon, dich)
        self._thu_muc_da_xuat = thu_muc
        return dich

    def _dung(self) -> None:
        if self._huy is not None:
            self._huy.set()
        self._ghi("Đã yêu cầu dừng…")

    def _xong(self, ds: List[str]) -> None:
        self._da_xong = list(ds)
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._nut_mo.setEnabled(bool(ds))
        self._thanh.setValue(100 if ds else 0)
        if ds:
            self._ghi("Xong: {0} file Excel. Mở bằng VE3 hoặc Excel đều được."
                      .format(len(ds)))
            self._app.show_message(
                "Đã tạo prompt",
                "{0} file Excel nằm trong:\n{1}\n\nCác sheet đặt tên đúng kiểu "
                "VE3 (scenes, characters…) nên mở thẳng bằng VE3_SUITE được."
                .format(len(ds), self._thu_muc_da_xuat))
        else:
            self._ghi("Không tạo được file nào — xem nhật ký ở trên.")

    def _hong(self, loi: BaseException) -> None:
        self._nut_chay.setEnabled(True)
        self._nut_dung.setEnabled(False)
        self._app.show_error(loi)

    # ── Tải bộ nghe ──────────────────────────────────────────────────────────

    def _tai_model(self) -> None:
        """Tải model nghe. Miễn phí, nhưng nặng — nên hỏi trước."""
        from core.model_installer import ALLOWED_MODELS  # noqa: PLC0415

        self._nut_tai.setEnabled(False)
        self._ghi("Đang tải bộ nghe ({0}) — khoảng 0,5 GB, chỉ một lần…"
                  .format(MA_MODEL_NGHE))

        goc = self._app.base_dir
        repo = ALLOWED_MODELS.get(MA_MODEL_NGHE, "")

        def viec():
            from pathlib import Path  # noqa: PLC0415

            from core.model_installer import install  # noqa: PLC0415

            return str(install(Path(goc), MA_MODEL_NGHE, repo))

        def ok(duong):
            self._nut_tai.setEnabled(True)
            self._ghi("Đã tải xong bộ nghe: {0}".format(duong))
            self._ve_trang_thai()

        def hong(loi):
            self._nut_tai.setEnabled(True)
            self._ghi("Tải bộ nghe hỏng: {0}".format(loi))
            self._app.show_error(loi)

        self._app.run_bg(viec, on_ok=ok, on_err=hong)

    # ── Nhật ký ──────────────────────────────────────────────────────────────

    def _ghi(self, dong: str) -> None:
        self._log.appendPlainText(dong)

    def _ghi_nen(self, dong: str) -> None:
        self._app.goi_tren_luong_ve(lambda: self._ghi(dong))

    def _tien_nen(self, phan: float) -> None:
        gia_tri = max(0, min(100, int(round(phan * 100))))
        self._app.goi_tren_luong_ve(lambda: self._thanh.setValue(gia_tri))

    def doi_du_an(self, _ten: str) -> None:
        self._thu_muc.dat(self._app.default_output_dir("prompt-visuals"))


def _ma_artifact(gia_tri) -> str:
    """`put_file` trả về `Artifact` hoặc chuỗi tuỳ bản — nhận cả hai."""
    return str(getattr(gia_tri, "artifact_id", "") or gia_tri)


def _ma_an_toan(ten: str) -> str:
    """Đổi tên file thành mã workflow hợp lệ (chỉ chữ, số, `.`, `_`, `-`).

    Mã này cũng là tên tệp điểm dừng, nên mỗi file giọng đọc một mã riêng —
    dùng chung là file sau đè điểm dừng của file trước.
    """
    goc = os.path.splitext(os.path.basename(ten))[0]
    ra = "".join(c if (c.isalnum() or c in "._-") else "-" for c in goc)
    return ra.strip("-.") or "chay"
