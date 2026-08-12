"""Trang Agent (Qt) — bản chuyển của `ui/tab_agent.py`.

Đây là cửa trước của cả sản phẩm: khách nói việc muốn làm bằng lời thường, Agent
dựng Tool của họ từ các tool con.

Ba luật giữ nguyên từ bản tkinter, cả ba đều là lỗi đã trả giá:

* **Chỉ vẽ 30 bong bóng gần nhất**, dù phiên nhớ 200 tin. Hai nhu cầu khác nhau:
  mô hình cần ngữ cảnh, mắt người cần đọc được. Vẽ cả 200 là cuộn mất nửa giây
  mỗi nhịp.
* **Không hiện tiền ở đây** — chuyện tiền gom về trang Ví & Tài khoản.
* **Mọi thay đổi đều là ĐỀ XUẤT**, khách bấm duyệt mới thành thật.

Bộ hiểu offline (`core.agent_planner`) là **sàn**: khách chưa nạp tiền, mất mạng,
hay mô hình lỗi đều rơi xuống đây, và nó vẫn phải dựng được tool.

Trang này còn là **tay của Agent trên thanh bên**: đổi tên tab, ẩn/hiện tab do
`core.ui_customization` hiểu và `core.ui_profile` nhớ, nhưng chỉ chỗ này mới
chạm được vào widget thật.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtCore import QPoint, QRect, QSize, Qt
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLayout, QLineEdit, QPlainTextEdit, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from core.agent_planner import HANH_DONG_GIAO_DIEN, plan_message
from core.agent_service import respond, shopapi_completer
from core.agent_session import load_agent_session, save_agent_session
from core.noi_tool import noi_them_tool
from core.tool_contract import ToolContractError, load_catalog, load_manifest
from core.tool_proposals import ToolProposalStore, activate_declarative
from core.ui_profile import load_hidden_tabs, load_tab_labels, save_hidden_tab, save_tab_label

from . import theme
from .widgets import HangXuongDong, nhan, nut_chinh, nut_phu, the, tieu_de_trang

__all__ = ["TrangAgent"]

#: Số bong bóng được VẼ. Không liên quan số tin được NHỚ — xem docstring module.
_MAX_BONG_BONG = 30

#: Bề rộng cột “Tool của tôi”.
#:
#: Cửa sổ hẹp nhất là 1000px (`ui_qt/app.py::setMinimumSize`), trừ thanh bên
#: 240px và lề trang còn chưa tới 700px cho hai cột. Cột phải từng để 320px mà
#: **không đóng khung**, nên nút bên trong tự đẩy nó rộng thêm và cả cột trôi ra
#: ngoài mép phải: khách nhìn thấy nút “✓ Tạo Tool của tôi” bị cắt mất một nửa.
#:
#: 320px là bề rộng nhỏ nhất mà hai nút dưới cột còn đủ chỗ cho **cả câu chữ**;
#: hẹp hơn là nút bắt đầu phải cắt chữ bằng “…”.
_RONG_COT_PHAI = 320


#: Gợi ý bấm nhanh. Chữ phải NGẮN — chip dài bị layout cắt cụt, khách đọc ra
#: "m giúp tao conte" thì thà đừng có.
GOI_Y = ("Làm content", "Tạo giọng đọc", "Tạo ảnh", "Làm video")


def _ep_vao_cot(nut, rong: int = _RONG_COT_PHAI) -> None:
    """Ép một nút nằm trọn trong cột: cắt chữ bằng “…” chứ không tràn ra ngoài.

    Chặn bề rộng tối đa là phần bắt buộc — Qt lấy `max(sizeHint, minimumSizeHint)`
    làm bề rộng tối thiểu của nút, nên một nhãn dài đủ sức đẩy rộng cả cột. Đo
    chữ hoãn tới lúc trang hiện ra vì bảng kiểu QSS (nút chính cỡ 15px) chỉ được
    áp lúc widget được polish, đo sớm hơn là đo bằng phông sai.
    """
    nut.setMaximumWidth(rong)
    nut.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    # Nhãn gốc giữ trong một thuộc tính riêng, không mượn tooltip: tooltip là
    # chỗ nói thêm cho khách, mượn nó thì lần đo sau lấy nhầm câu chú thích làm
    # nhãn nút.
    day_du = nut.property("nhan_day_du") or nut.text()
    nut.setProperty("nhan_day_du", day_du)
    if nut.text() != day_du:
        nut.setText(day_du)  # đo lại từ chữ gốc, không đo chồng lên chữ đã cắt
    thua = nut.sizeHint().width() - rong
    if thua <= 0:
        return
    # Lấy phần thừa từ chính `sizeHint` nên không phải đoán lề trong nút — mỗi
    # kiểu nút một mức lề khác nhau, đoán sai là cắt chữ khi vẫn còn chỗ.
    do = nut.fontMetrics()
    rong_chu = (do.horizontalAdvance(day_du) if hasattr(do, "horizontalAdvance")
                else do.width(day_du))
    if not nut.toolTip():
        nut.setToolTip(day_du)
    nut.setText(do.elidedText(day_du, Qt.ElideRight, max(rong_chu - thua, 32)))


class BongBong(QFrame):
    def __init__(self, vai: str, noi_dung: str):
        super().__init__()
        khach = vai == "user"
        # Chọn theo objectName, KHÔNG theo `QFrame`: `QLabel` là lớp con của
        # `QFrame`, nên `QFrame {...}` vẽ viền quanh cả từng dòng chữ bên trong —
        # bong bóng thành một chồng hộp lồng nhau.
        self.setObjectName("bubble")
        self.setStyleSheet(
            "#bubble {{ background: {0}; border: 1px solid {1}; border-radius: 12px; }}".format(
                theme.NHAN_NHAT if khach else theme.THE, theme.VIEN))
        doc = QVBoxLayout(self)
        doc.setContentsMargins(14, 10, 14, 12)
        doc.setSpacing(4)
        doc.addWidget(nhan("Bạn" if khach else "Agent", "muted"))
        chu = nhan(noi_dung)
        chu.setTextInteractionFlags(Qt.TextSelectableByMouse)
        doc.addWidget(chu)


class TrangAgent(QWidget):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self._ho_so_ui = Path(app.base_dir) / "workspace" / "ui-profile.json"
        self._phien_path = Path(app.base_dir) / "workspace" / "agent-session.json"
        self._phien = load_agent_session(self._phien_path)
        self._phien.state.update({"onboarding_complete": True, "onboarding_stage": "active"})
        self._cho_duyet: Optional[Dict[str, Any]] = None
        self._tool_cho_duyet = None
        self._bong: List[BongBong] = []
        self._kho_de_xuat = ToolProposalStore(
            Path(app.base_dir) / "workspace" / "tool-proposals")
        self._catalog = self._nap_catalog()

        ngang = QHBoxLayout(self)
        ngang.setContentsMargins(24, 20, 24, 20)
        ngang.setSpacing(14)

        # ── Cột trái: hội thoại ──────────────────────────────────────────────
        trai = QVBoxLayout()
        trai.setSpacing(12)
        trai.addWidget(tieu_de_trang(
            # Tiêu đề là TÊN, không phải một câu. Câu dài 714px ở đây từng ép bề
            # rộng tối thiểu của cả trang lên 1168px — tràn hẳn ra ngoài mép.
            "🤖  Agent xây tool",
            "Nói điều bạn muốn, tôi xây giúp. Mỗi tab là một tool con."))
        self._cuon = QScrollArea()
        self._cuon.setWidgetResizable(True)
        trong = QWidget()
        self._chat = QVBoxLayout(trong)
        self._chat.setContentsMargins(2, 2, 8, 2)
        self._chat.setSpacing(8)
        self._chat.addStretch(1)
        self._cuon.setWidget(trong)
        trai.addWidget(self._cuon, 1)

        goi_y = HangXuongDong()
        for cau in GOI_Y:
            goi_y.addWidget(nut_phu(cau, lambda c=cau: self._gui(c.lower())))
        trai.addLayout(goi_y)

        hang = QHBoxLayout()
        self._o_nhap = QLineEdit()
        self._o_nhap.setPlaceholderText("Ví dụ: tôi muốn làm kênh YouTube về tâm lý")
        self._o_nhap.returnPressed.connect(lambda: self._gui())
        hang.addWidget(self._o_nhap, 1)
        self._nut_gui = nut_chinh("Gửi", lambda: self._gui())
        self._nut_gui.setFixedWidth(110)
        hang.addWidget(self._nut_gui)
        trai.addLayout(hang)
        ngang.addLayout(trai, 1)

        # ── Cột phải: Tool của tôi ───────────────────────────────────────────
        #
        # Cả cột nằm trong MỘT widget có bề rộng cố định. Trước đây cột chỉ là
        # một `QVBoxLayout` với vài widget con tự đặt bề rộng: widget nào rộng
        # hơn thì kéo cả cột rộng theo, và ở cửa sổ nhỏ nhất nó tràn khỏi mép.
        self._cot_phai = QWidget()
        self._cot_phai.setFixedWidth(_RONG_COT_PHAI)
        phai = QVBoxLayout(self._cot_phai)
        phai.setContentsMargins(0, 0, 0, 0)
        phai.setSpacing(10)
        phai.addWidget(nhan("Tool của tôi", "h2"))
        self._tom_tat = QPlainTextEdit()
        self._tom_tat.setReadOnly(True)
        self._tom_tat.setMinimumHeight(240)
        phai.addWidget(self._tom_tat)
        # Nhãn nút phải nằm gọn trong 320px. Nhãn cũ “✓  Thêm tool mới vào bộ
        # tool” cần tới 398px — chính nó kéo cả cột rộng ra và đẩy mọi thứ khỏi
        # mép phải cửa sổ. Câu hỏi xác nhận vẫn nói đủ ý khi khách bấm vào.
        self._nut_duyet = nut_chinh("✓ Tạo Tool của tôi", self._duyet)
        self._nut_duyet.setEnabled(False)
        phai.addWidget(self._nut_duyet)
        self._nut_them_tool = nut_phu("✓  Thêm tool mới", self._kich_hoat_tool)
        self._nut_them_tool.setEnabled(False)
        self._nut_them_tool.setToolTip("Thêm tool mới vào bộ tool của bạn")
        phai.addWidget(self._nut_them_tool)
        phai.addStretch(1)
        self._trang_thai = nhan("", "muted")
        phai.addWidget(self._trang_thai)
        ngang.addWidget(self._cot_phai)

        self._ve_lai_lich_su()
        self._ve_tom_tat(self._phien.workflow)
        self._ap_ho_so_giao_dien()

    def showEvent(self, su_kien) -> None:  # noqa: N802 — tên do Qt quy định
        super().showEvent(su_kien)
        for nut in (self._nut_duyet, self._nut_them_tool):
            _ep_vao_cot(nut)

    # ── Thanh bên: tay của Agent trên giao diện ──────────────────────────────

    def _nav(self) -> Tuple[tuple, ...]:
        """Danh sách trang của vỏ đang chạy: `(khoá, biểu tượng, nhãn)`.

        Đọc từ chính cửa sổ chứ không nhập hằng `TRANG`: vỏ vận hành thu hẹp
        danh sách này, mà tab nó cố ý bỏ đi thì Agent cũng không được đụng tới.
        """
        return tuple(getattr(self._app, "_nav", ()) or ())

    def _nhan_tab(self) -> Dict[str, str]:
        """Bảng *khoá tab → nhãn đang hiện*, đã tính cả tên khách vừa đổi."""
        da_doi = self._nhan_da_luu()
        return {khoa: da_doi.get(khoa, ten) for khoa, _bt, ten in self._nav()}

    def _nhan_da_luu(self) -> Dict[str, str]:
        try:
            return load_tab_labels(self._ho_so_ui)
        except OSError:
            return {}

    def _nut_tab(self, khoa: str):
        ben = getattr(self._app, "_ben", None)
        return getattr(ben, "_nut", {}).get(khoa) if ben is not None else None

    def _ve_lai_nut_tab(self, khoa: str, ten: str) -> None:
        nut = self._nut_tab(khoa)
        if nut is None:
            return
        bieu_tuong = next((bt for k, bt, _t in self._nav() if k == khoa), "")
        nut.setText("   {0}    {1}".format(bieu_tuong, ten))

    def _ap_ho_so_giao_dien(self) -> None:
        """Đặt lại tên và trạng thái ẩn của tab ngay khi mở tool.

        Chạy được ở đây vì thanh bên đã dựng xong trước các trang. Không có bước
        này thì mỗi lần khách mở lại tool là tên tab tự nhảy về mặc định — khách
        sẽ nghĩ Agent chỉ nói cho vui chứ không sửa thật.
        """
        for khoa, ten in self._nhan_da_luu().items():
            self._ve_lai_nut_tab(khoa, ten)
        try:
            an = load_hidden_tabs(self._ho_so_ui)
        except OSError:
            return
        for khoa in an:
            nut = self._nut_tab(khoa)
            if nut is not None:
                nut.setVisible(False)

    def _lam_viec_giao_dien(self, hanh_dong) -> List[str]:
        """Thi hành các `AgentAction` chạm giao diện; trả về những lời báo hỏng.

        Trả lời của Agent viết ở thể đã-xong, nên phải làm TRƯỚC khi vẽ câu trả
        lời: hỏng chỗ nào thì nói thẳng chỗ đó, không để câu “Xong” đứng một mình.
        """
        hong: List[str] = []
        for viec in hanh_dong or ():
            kieu = getattr(viec, "kind", "")
            du_lieu = dict(getattr(viec, "payload", {}) or {})
            khoa = str(du_lieu.get("key") or "")
            if kieu not in HANH_DONG_GIAO_DIEN or not khoa:
                continue
            if khoa not in {k for k, _bt, _t in self._nav()}:
                hong.append("Bản này không có tab đó nên tôi chưa đổi được gì.")
                continue
            try:
                if kieu == "rename_tab":
                    ten = save_tab_label(self._ho_so_ui, khoa, str(du_lieu.get("label") or ""))
                    self._ve_lai_nut_tab(khoa, ten)
                else:
                    an = kieu == "hide_tab"
                    save_hidden_tab(self._ho_so_ui, khoa, an)
                    nut = self._nut_tab(khoa)
                    if nut is not None:
                        nut.setVisible(not an)
                    if an:
                        # Ẩn tab đang mở là để khách nhìn vào một trang không còn
                        # lối quay lại; kéo họ về đúng chỗ vừa ra lệnh.
                        self._app.show_page("agent")
            except (OSError, ValueError) as loi:
                hong.append("Chưa đổi được giao diện: {0}".format(loi))
        return hong

    # ── Catalog ──────────────────────────────────────────────────────────────

    def _nap_catalog(self):
        goc = Path(self._app.base_dir)
        try:
            catalog = load_catalog(sorted((goc / "tool-catalog").glob("*/tool.json")))
            for duong in sorted((goc / "user-tools").glob("*/tool.json")):
                manifest = load_manifest(duong)
                catalog[manifest.tool_id] = manifest
            return catalog
        except ToolContractError:
            return {}

    # ── Hội thoại ────────────────────────────────────────────────────────────

    def _ve_lai_lich_su(self) -> None:
        """Vẽ phần đuôi lịch sử, kèm một dòng báo phần bị giấu.

        Dòng báo phải **nằm trong** trần `_MAX_BONG_BONG`, không được cộng thêm.
        Trước đây nó vẽ dòng báo rồi vẽ tiếp đủ `_MAX_BONG_BONG` bong bóng, nên
        vòng cắt trong `_them_bong` đẩy chính dòng báo ra ngay lúc vừa vẽ xong —
        khách không bao giờ thấy nó, và tưởng Agent quên sạch mọi chuyện đã nói.
        """
        tin = self._phien.messages
        an_bot = len(tin) - _MAX_BONG_BONG
        if an_bot > 0:
            self._them_bong("assistant", "… {0} tin nhắn cũ hơn vẫn nằm trong ngữ cảnh "
                                         "của Agent nhưng không hiện ở đây, để khung chat "
                                         "còn cuộn mượt.".format(an_bot))
            tin = tin[-(_MAX_BONG_BONG - 1):]
        for muc in tin:
            self._them_bong(muc["role"], muc["content"])
        if not tin:
            self._them_bong("assistant",
                            "Chào bạn! Nói việc bạn muốn làm — tôi dựng tool giúp.")

    def _them_bong(self, vai: str, noi_dung: str) -> None:
        bong = BongBong(vai, noi_dung)
        self._chat.insertWidget(self._chat.count() - 1, bong)
        self._bong.append(bong)
        while len(self._bong) > _MAX_BONG_BONG:
            cu = self._bong.pop(0)
            cu.setParent(None)
            cu.deleteLater()
        thanh = self._cuon.verticalScrollBar()
        thanh.setValue(thanh.maximum())

    def _gui(self, san: str = "") -> None:
        cau = (san or self._o_nhap.text()).strip()
        if not cau:
            return
        self._o_nhap.clear()
        self._phien.add("user", cau)
        self._them_bong("user", cau)
        self._nut_gui.setEnabled(False)
        self._trang_thai.setText("Agent đang nghĩ…")

        catalog = self._catalog
        workflow = self._phien.workflow
        trang_thai = dict(self._phien.state)
        lich_su = list(self._phien.messages)
        cau_hinh = self._app.config
        # Đọc nhãn tab TRÊN luồng vẽ rồi mới giao xuống nền: luồng nền không được
        # chạm widget, kể cả chỉ để đọc một dòng chữ.
        nhan_tab = self._nhan_tab()

        def viec():
            hoan_thanh = None
            khoa = str(getattr(cau_hinh, "api_key", "") or "")
            if khoa:
                hoan_thanh = shopapi_completer(
                    khoa, str(getattr(cau_hinh, "base_url", "") or "https://api.shopapi.vn"))
            return respond(cau, catalog, workflow=workflow, state=trang_thai,
                           history=lich_su, tabs=nhan_tab, complete=hoan_thanh)

        self._app.run_bg(viec, on_ok=self._nhan_tra_loi, on_err=self._loi_tra_loi)

    def _loi_tra_loi(self, loi: BaseException) -> None:
        """Mạng hỏng không được làm khách bế tắc — lùi về bộ hiểu offline.

        Đó chính là lý do `core.agent_planner` tồn tại: nó là sàn, không phải
        đường dự phòng cho vui.
        """
        self._nut_gui.setEnabled(True)
        cuoi = next((muc["content"] for muc in reversed(self._phien.messages)
                     if muc.get("role") == "user"), "")
        ke_hoach = plan_message(cuoi, self._catalog, self._phien.workflow,
                                self._phien.state, history=list(self._phien.messages),
                                tabs=self._nhan_tab())
        self._nhan_tra_loi(ke_hoach)

    def _nhan_tra_loi(self, tra_loi) -> None:
        self._nut_gui.setEnabled(True)
        self._trang_thai.setText("")
        loi_nhan = getattr(tra_loi, "reply", "")
        hong = self._lam_viec_giao_dien(getattr(tra_loi, "actions", ()))
        if hong:
            loi_nhan = "\n\n".join(["⚠ " + dong for dong in hong] + [loi_nhan])
        self._phien.add("assistant", loi_nhan)
        self._them_bong("assistant", loi_nhan)
        de_xuat = getattr(tra_loi, "proposed_workflow", None)
        if de_xuat:
            self._cho_duyet = dict(de_xuat)
            self._nut_duyet.setEnabled(True)
            self._ve_tom_tat(self._cho_duyet)
        tool_moi = getattr(tra_loi, "tool_proposal", None)
        if tool_moi is not None:
            self._tool_cho_duyet = tool_moi
            try:
                self._kho_de_xuat.save(tool_moi)
            except Exception:  # noqa: BLE001 — lưu nháp hỏng không chặn hội thoại
                pass
            self._nut_them_tool.setEnabled(
                tool_moi.manifest.runtime.get("kind") == "declarative")
        trang_thai_moi = getattr(tra_loi, "state", None)
        if trang_thai_moi:
            self._phien.state.update(dict(trang_thai_moi))
        self._luu_phien()

    # ── Tool của tôi ─────────────────────────────────────────────────────────

    def _ve_tom_tat(self, workflow) -> None:
        if not workflow or not workflow.get("nodes"):
            self._tom_tat.setPlainText(
                "Chưa có Tool của tôi.\n\nHãy nói việc bạn muốn làm ở ô bên trái.")
            return
        dong = ["QUY TRÌNH CỦA BẠN", ""]
        nodes = list(workflow.get("nodes", []))
        for so, node in enumerate(nodes, 1):
            manifest = self._catalog.get(node.get("tool_id"))
            ten = getattr(manifest, "name", None) or str(node.get("tool_id"))
            bat = node.get("config", {}).get("enabled", True)
            dong.append("{0}. {1}{2}".format(so, ten, "" if bat else "   [ĐÃ TẮT]"))
            if so < len(nodes):
                dong.append("   ↓")
        dong += ["", "Muốn đổi gì, cứ nói ở ô chat."]
        self._tom_tat.setPlainText("\n".join(dong))

    def _duyet(self) -> None:
        if not self._cho_duyet:
            return
        self._phien.workflow = dict(self._cho_duyet)
        self._cho_duyet = None
        self._nut_duyet.setEnabled(False)
        self._ve_tom_tat(self._phien.workflow)
        self._luu_phien()
        self._them_bong("assistant", "Đã tạo Tool của bạn. Mở tab tương ứng để chạy thử.")

    def _kich_hoat_tool(self) -> None:
        de_xuat = self._tool_cho_duyet
        if de_xuat is None:
            return
        from PyQt5.QtWidgets import QMessageBox

        dong_y = QMessageBox.question(
            self, "Thêm tool mới vào bộ tool của bạn?",
            "{0}\n\nTên tool: {1}\n\nTool này chỉ soạn chữ và gọi ShopAPI — nó không "
            "chạy được lệnh nào trên máy bạn. Thêm vào nhé?".format(
                de_xuat.summary, de_xuat.manifest.name))
        if dong_y != QMessageBox.Yes:
            return
        try:
            activate_declarative(de_xuat, Path(self._app.base_dir) / "user-tools")
        except Exception as loi:  # noqa: BLE001
            self._app.show_error(loi)
            return
        self._catalog[de_xuat.manifest.tool_id] = de_xuat.manifest
        self._tool_cho_duyet = None
        self._nut_them_tool.setEnabled(False)
        ket = noi_them_tool(self._phien.workflow, de_xuat.manifest, self._catalog)
        if ket.noi_duoc:
            self._cho_duyet = ket.workflow
            self._nut_duyet.setEnabled(True)
            self._ve_tom_tat(ket.workflow)
        self._them_bong("assistant", "Đã thêm “{0}” vào bộ tool của bạn.\n\n{1}".format(
            de_xuat.manifest.name, ket.loi_nhan))
        self._luu_phien()

    def _luu_phien(self) -> None:
        try:
            save_agent_session(self._phien_path, self._phien)
        except OSError:
            pass  # không ghi được phiên thì vẫn cho làm việc tiếp
