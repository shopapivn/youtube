"""Nền giao diện: dựng lại các lớp `customtkinter` bằng **tkinter thường**.

**Vì sao có file này.** customtkinter vẽ mỗi widget bằng một canvas riêng để bo
góc. Hệ quả là cửa sổ Studio có 546 widget trong đó **164 là canvas**, và Windows
phải vẽ lại từng cái mỗi khi khách kéo cửa sổ. Đo trên cùng một nội dung 96 dòng:

===================  ==========  ================
bộ vẽ                 số widget   mỗi bước kéo
===================  ==========  ================
tkinter thường        193         10,0 ms
customtkinter         385         22,7 ms
===================  ==========  ================

Chủ dự án kéo thử hai cửa sổ cạnh nhau và xác nhận đúng như số đo: tkinter thường
mượt, customtkinter giật. Bỏ bo góc **không** cứu được (đo: 29,7 → 43,7 ms) vì
chi phí nằm ở bản thân cái canvas, không ở góc.

**Vì sao làm thành lớp nền chứ không sửa từng tab.** Code giao diện có 11.000
dòng ở 14 file. Đổi hết là 14.000 chỗ có thể sai. Ở đây ta giữ **nguyên si** tên
lớp và tên tham số của customtkinter, nên mỗi file chỉ đổi đúng một dòng import.
Muốn quay lại cũng chỉ đổi lại một dòng.

**Quy ước dịch tham số** (customtkinter → tkinter):

======================  ==========================================
customtkinter            tkinter
======================  ==========================================
``fg_color``             ``bg`` (``"transparent"`` → nền của cha)
``text_color``           ``fg``
``border_width``         ``highlightthickness``
``border_color``         ``highlightbackground``
``corner_radius``        bỏ — tkinter không bo góc được
``hover_color``          bỏ
======================  ==========================================

customtkinter đo `width`/`height` bằng **điểm ảnh**, còn tkinter đo widget có chữ
bằng **số ký tự / số dòng**. Nên với nhãn, nút, ô nhập… ta quy đổi qua bề rộng
thật của phông (:func:`_so_ky_tu`); truyền thẳng là ô rộng gấp bảy lần.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Any, Dict, Optional, Tuple

__all__ = [
    "CTk", "CTkToplevel", "CTkFrame", "CTkLabel", "CTkButton", "CTkEntry",
    "CTkTextbox", "CTkOptionMenu", "CTkComboBox", "CTkSegmentedButton",
    "CTkScrollableFrame",
    "CTkCheckBox", "CTkProgressBar", "CTkSlider", "CTkImage", "CTkCanvas",
    "StringVar", "IntVar", "DoubleVar", "BooleanVar",
    "set_appearance_mode", "set_default_color_theme", "set_widget_scaling",
]

StringVar = tk.StringVar
IntVar = tk.IntVar
DoubleVar = tk.DoubleVar
BooleanVar = tk.BooleanVar
CTkCanvas = tk.Canvas

#: Màu lấy từ `ui/theme.py` — nơi duy nhất được phép định nghĩa màu.
#:
#: Bản đầu của file này gõ cứng `#ffffff` cho ô nhập và ô soạn thảo. Tool đang
#: dùng tông TỐI, nên mọi ô nhập loè ra trắng giữa nền navy — đúng thứ mà dòng
#: đầu `theme.py` cấm: "Không hardcode mã màu ở chỗ khác".
from . import theme  # noqa: E402

_NEN_LUI = theme.CARD
_NEN_O_NHAP = theme.CARD_ALT
_CHU = theme.TEXT
_CHU_MO = theme.TEXT_MUTED
_VIEN = theme.BORDER

#: Tham số riêng của customtkinter, không có tương đương ở tkinter. Nuốt im lặng
#: là có chủ đích: chúng chỉ ảnh hưởng thẩm mỹ, còn ném lỗi thì khách mất tool.
_BO_QUA = frozenset({
    "corner_radius", "hover_color", "hover", "text_color_disabled",
    "border_spacing", "background_corner_colors", "round_width_to_even_numbers",
    "round_height_to_even_numbers", "scrollbar_button_color",
    "scrollbar_button_hover_color", "label_fg_color", "label_text_color",
    "progress_color", "button_hover_color", "dropdown_hover_color",
    "dropdown_fg_color", "dropdown_text_color", "dropdown_font",
    "selected_color", "selected_hover_color", "unselected_color",
    "unselected_hover_color", "checkmark_color", "checkbox_width",
    "checkbox_height", "dynamic_resizing", "orientation", "determinate_speed",
    "indeterminate_speed", "number_of_steps", "button_length",
    "button_color", "button_hover_color", "placeholder_text_color",
    "text_color_disabled", "fg_color_disabled", "border_color_disabled",
    "scrollbar_fg_color", "corner_radius_top", "corner_radius_bottom",
    "segmented_button_fg_color", "segmented_button_selected_color",
    "segmented_button_selected_hover_color", "segmented_button_unselected_color",
    "segmented_button_unselected_hover_color", "text_color_hover",
    "activate_scrollbars", "label_anchor", "overwrite_preferred_drawing_method",
})


def set_appearance_mode(_mode: str) -> None:
    """Không làm gì — nền này chỉ có một bảng màu, do `ui/theme.py` quyết định."""


def set_default_color_theme(_name: str) -> None:
    """Không làm gì — xem :func:`set_appearance_mode`."""


def set_widget_scaling(_value: float) -> None:
    """Không làm gì — Windows đã tự lo phần phóng to."""


# ── Dịch tham số ─────────────────────────────────────────────────────────────


def _mau(value: Any) -> Optional[str]:
    """customtkinter cho phép `("màu sáng", "màu tối")`; ta chỉ dùng màu sáng."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return str(value[0]) if value else None
    return str(value)


def _nen_cua(widget: Any) -> str:
    """Màu nền của một widget bất kỳ, kể cả widget customtkinter còn sót lại."""
    for doc in (lambda: widget.cget("bg"), lambda: _mau(widget.cget("fg_color"))):
        try:
            value = doc()
        except Exception:  # noqa: BLE001 - widget không có thuộc tính đó
            continue
        if value and value != "transparent":
            return str(value)
    return _NEN_LUI


def _so_ky_tu(font: Any, pixels: Any, widget: Any) -> Optional[int]:
    """Quy bề rộng điểm ảnh thành số ký tự, theo phông thật đang dùng.

    Trả `None` khi không đo được, để nơi gọi bỏ hẳn tham số thay vì đoán bừa —
    ô rộng sai còn đỡ hơn ô rộng gấp bảy lần.
    """
    try:
        pixels = int(pixels)
    except (TypeError, ValueError):
        return None
    if pixels <= 0:
        return None
    try:
        do = tkfont.Font(root=widget, font=font) if font else tkfont.nametofont("TkDefaultFont")
        rong = max(1, do.measure("0"))
    except Exception:  # noqa: BLE001 - chưa có root hoặc phông lạ
        rong = 7
    return max(1, int(round(pixels / float(rong))))


def _so_dong(font: Any, pixels: Any, widget: Any) -> Optional[int]:
    try:
        pixels = int(pixels)
    except (TypeError, ValueError):
        return None
    if pixels <= 0:
        return None
    try:
        do = tkfont.Font(root=widget, font=font) if font else tkfont.nametofont("TkDefaultFont")
        cao = max(1, do.metrics("linespace"))
    except Exception:  # noqa: BLE001
        cao = 16
    return max(1, int(round(pixels / float(cao))))


def _dich(kwargs: Dict[str, Any], master: Any, *, doi_co_chu: bool,
          widget: Any = None) -> Dict[str, Any]:
    """Đổi tham số kiểu customtkinter sang tham số tkinter.

    `doi_co_chu`: widget này đo `width`/`height` bằng ký tự (nhãn, nút, ô nhập)
    hay bằng điểm ảnh (khung, thanh tiến độ).
    """
    ra: Dict[str, Any] = {}
    font = kwargs.get("font")
    for ten, gia_tri in kwargs.items():
        if ten in _BO_QUA:
            continue
        if ten == "fg_color":
            mau = _mau(gia_tri)
            ra["bg"] = _nen_cua(master) if mau in (None, "transparent") else mau
        elif ten == "bg_color":
            continue
        elif ten == "text_color":
            mau = _mau(gia_tri)
            if mau and mau != "transparent":
                ra["fg"] = mau
        elif ten == "border_color":
            mau = _mau(gia_tri)
            if mau:
                ra["highlightbackground"] = mau
                ra["highlightcolor"] = mau
        elif ten == "border_width":
            ra["highlightthickness"] = int(gia_tri or 0)
        elif ten in ("width", "height") and doi_co_chu:
            doi = _so_ky_tu if ten == "width" else _so_dong
            quy = doi(font, gia_tri, widget)
            if quy is not None:
                ra[ten] = quy
        elif ten == "placeholder_text":
            continue  # xử lý riêng ở CTkEntry
        else:
            ra[ten] = gia_tri
    return ra


class _Nen:
    """Phần dùng chung: dịch tham số ở cả lúc dựng lẫn lúc `configure`."""

    _DOI_CO_CHU = False

    def _chuan(self, kwargs: Dict[str, Any], master: Any) -> Dict[str, Any]:
        return _dich(kwargs, master, doi_co_chu=self._DOI_CO_CHU, widget=self)

    def configure(self, **kwargs):  # noqa: D102
        return super().configure(**_dich(kwargs, self.master,
                                         doi_co_chu=self._DOI_CO_CHU, widget=self))

    config = configure

    def cget(self, key: str):  # noqa: D102
        doi = {"fg_color": "bg", "text_color": "fg", "border_color": "highlightbackground",
               "border_width": "highlightthickness"}
        if key == "corner_radius":
            return 0
        return super().cget(doi.get(key, key))


# ── Cửa sổ ───────────────────────────────────────────────────────────────────


def _dat_phong_mac_dinh(widget) -> None:
    """Đổi phông mặc định của Tk sang phông trong `ui/theme.py`.

    Widget nào không khai báo `font` sẽ dùng `TkDefaultFont` — trên Windows đó là
    Tahoma cỡ 9, nét thô, giãn dòng chật. Đặt lại một lần ở đây thì mọi hộp thoại,
    menu chuột phải và widget lỡ quên khai báo đều theo cùng một bộ chữ.
    """
    ten_phong, co = theme.FONT_FAMILY, theme.FONT_BODY[1]
    for ten in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
                "TkIconFont", "TkTooltipFont"):
        try:
            tkfont.nametofont(ten, root=widget).configure(family=ten_phong, size=co)
        except Exception:  # noqa: BLE001 — phông thiếu thì Tk tự lùi về mặc định
            pass
    try:
        tkfont.nametofont("TkFixedFont", root=widget).configure(
            family=theme.FONT_MONO_FAMILY, size=theme.FONT_MONO[1])
    except Exception:  # noqa: BLE001
        pass


def _nhuom_ttk(widget) -> None:
    """Kéo các widget `ttk` về đúng tông của `ui/theme.py`.

    `ttk.Combobox`, thanh cuộn và thanh tiến độ mặc định lấy màu của hệ điều
    hành — trắng sáng. Giữa nền tối của tool chúng loè ra như lỗi hiển thị. `ttk`
    không nhận `bg`/`fg` như widget thường, bắt buộc phải đi qua `Style`.
    """
    try:
        style = ttk.Style(widget)
        try:
            style.theme_use("clam")   # theme duy nhất cho đổi màu triệt để
        except tk.TclError:
            pass
        style.configure("TCombobox", fieldbackground=_NEN_O_NHAP, background=_NEN_O_NHAP,
                        foreground=_CHU, arrowcolor=_CHU, bordercolor=_VIEN,
                        lightcolor=_VIEN, darkcolor=_VIEN, selectbackground=theme.ACCENT,
                        selectforeground=_CHU, padding=4)
        style.map("TCombobox",
                  fieldbackground=[("readonly", _NEN_O_NHAP)],
                  foreground=[("readonly", _CHU)],
                  bordercolor=[("focus", theme.ACCENT)])
        widget.option_add("*TCombobox*Listbox.background", _NEN_O_NHAP)
        widget.option_add("*TCombobox*Listbox.foreground", _CHU)
        widget.option_add("*TCombobox*Listbox.selectBackground", theme.ACCENT)
        widget.option_add("*TCombobox*Listbox.selectForeground", _CHU)
        style.configure("Vertical.TScrollbar", background=theme.CARD_ALT,
                        troughcolor=theme.CARD, bordercolor=theme.CARD,
                        arrowcolor=_CHU_MO, relief="flat")
        style.map("Vertical.TScrollbar", background=[("active", theme.HOVER)])
        style.configure("TProgressbar", background=theme.ACCENT,
                        troughcolor=theme.BORDER, bordercolor=theme.BORDER,
                        lightcolor=theme.ACCENT, darkcolor=theme.ACCENT)
    except Exception:  # noqa: BLE001 — màu sai xấu hơn, nhưng không được làm chết tool
        pass


class CTk(_Nen, tk.Tk):
    """Cửa sổ gốc."""

    def __init__(self, **kwargs):
        tk.Tk.__init__(self)
        _dat_phong_mac_dinh(self)
        _nhuom_ttk(self)
        if kwargs:
            self.configure(**kwargs)


class CTkToplevel(_Nen, tk.Toplevel):
    """Cửa sổ phụ."""

    def __init__(self, master=None, **kwargs):
        tk.Toplevel.__init__(self, master)
        if kwargs:
            self.configure(**kwargs)


# ── Khung và chữ ─────────────────────────────────────────────────────────────


class CTkFrame(_Nen, tk.Frame):
    """Khung phẳng. Đây là lớp bỏ được nhiều canvas nhất — 148 chỗ dùng."""

    def __init__(self, master=None, **kwargs):
        kwargs.setdefault("fg_color", _nen_cua(master))
        ra = _dich(kwargs, master, doi_co_chu=False)
        ra.setdefault("highlightthickness", 0)
        tk.Frame.__init__(self, master, **ra)


class CTkLabel(_Nen, tk.Label):
    _DOI_CO_CHU = True

    def __init__(self, master=None, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        ra = _dich(kwargs, master, doi_co_chu=True)
        ra.setdefault("highlightthickness", 0)
        ra.setdefault("bd", 0)
        tk.Label.__init__(self, master, **ra)


class CTkButton(_Nen, tk.Button):
    _DOI_CO_CHU = True

    def __init__(self, master=None, **kwargs):
        mau_nen = _mau(kwargs.get("fg_color"))
        kwargs.setdefault("text_color", "#ffffff" if mau_nen and mau_nen != "transparent" else None)
        ra = _dich(kwargs, master, doi_co_chu=True)
        ra.setdefault("relief", "flat")
        ra.setdefault("bd", 0)
        ra.setdefault("cursor", "hand2")
        ra.setdefault("padx", 12)
        ra.setdefault("pady", 6)
        ra.setdefault("highlightthickness", 0)
        ra.setdefault("activeforeground", ra.get("fg", _CHU))
        # Nút không có nền riêng thì lấy nền của cha, để không lòi ô xám của hệ điều hành.
        ra.setdefault("bg", _nen_cua(master))
        ra.setdefault("activebackground", ra["bg"])
        ra.setdefault("disabledforeground", _CHU_MO)
        tk.Button.__init__(self, master, **ra)
        self._nen_that = ra["bg"]
        if str(ra.get("state", "normal")) == "disabled":
            self._doi_theo_trang_thai("disabled")

    def configure(self, **kwargs):  # noqa: D102
        trang_thai = kwargs.get("state")
        ket = _Nen.configure(self, **kwargs)
        if "fg_color" in kwargs:
            self._nen_that = _mau(kwargs["fg_color"]) or self._nen_that
        if trang_thai is not None:
            self._doi_theo_trang_thai(str(trang_thai))
        return ket

    config = configure

    def _doi_theo_trang_thai(self, trang_thai: str) -> None:
        """Nút tắt phải TRÔNG như đã tắt, không chỉ mờ chữ.

        `tk.Button` không đổi nền khi `state="disabled"`. Nút chính vẫn xanh đậm
        y như lúc bấm được, chỉ chữ nhạt đi — khách bấm mãi không thấy gì và
        tưởng tool hỏng. Nên ở đây nền cũng phải xám đi theo.
        """
        if trang_thai != "disabled":
            nen = self._nen_that
        elif str(self._nen_that).lower() in (theme.CARD.lower(), theme.CARD_ALT.lower()):
            # Nút kiểu viền: nền đã nhạt sẵn, tô xám đặc lại thành NẶNG hơn cả nút
            # bấm được bên cạnh. Chỉ để chữ mờ đi là đủ hiểu.
            nen = self._nen_that
        else:
            nen = theme.BORDER
        try:
            tk.Button.configure(self, bg=nen, activebackground=nen)
        except Exception:  # noqa: BLE001 — widget đã bị huỷ
            pass


class CTkCheckBox(_Nen, tk.Checkbutton):
    _DOI_CO_CHU = True

    def __init__(self, master=None, **kwargs):
        kwargs.setdefault("fg_color", _nen_cua(master))
        ra = _dich(kwargs, master, doi_co_chu=True)
        ra.setdefault("highlightthickness", 0)
        ra.setdefault("bd", 0)
        ra.setdefault("anchor", "w")
        ra.setdefault("activebackground", ra.get("bg", _nen_cua(master)))
        tk.Checkbutton.__init__(self, master, **ra)

    def select(self):  # noqa: D102
        tk.Checkbutton.select(self)

    def deselect(self):  # noqa: D102
        tk.Checkbutton.deselect(self)

    def get(self) -> int:
        """customtkinter trả 0/1; tkinter không có `get` nên dựng lại ở đây."""
        variable = self.cget("variable")
        if not variable:
            return 0
        try:
            return int(self.tk.globalgetvar(variable))
        except Exception:  # noqa: BLE001
            return 0


# ── Ô nhập ───────────────────────────────────────────────────────────────────


class CTkEntry(_Nen, tk.Entry):
    _DOI_CO_CHU = True

    def __init__(self, master=None, **kwargs):
        goi_y = kwargs.pop("placeholder_text", "")
        kwargs.setdefault("fg_color", _NEN_O_NHAP)
        kwargs.setdefault("text_color", _CHU)
        ra = _dich(kwargs, master, doi_co_chu=True)
        ra.setdefault("relief", "flat")
        ra.setdefault("highlightthickness", 1)
        ra.setdefault("highlightbackground", _VIEN)
        ra.setdefault("highlightcolor", theme.ACCENT)
        ra.setdefault("bd", 0)
        ra.setdefault("selectbackground", theme.DARK_CARD)
        ra.setdefault("selectforeground", _CHU)
        ra.setdefault("insertbackground", _CHU)   # con trỏ nhấp nháy phải nhìn thấy
        ra.pop("height", None)  # tkinter không đặt được chiều cao ô nhập
        tk.Entry.__init__(self, master, **ra)
        self._goi_y = str(goi_y or "")
        self._mau_chu = ra.get("fg", _CHU)
        if self._goi_y:
            self._hien_goi_y()
            self.bind("<FocusIn>", self._vao, add="+")
            self.bind("<FocusOut>", self._ra, add="+")

    # tkinter không có chữ gợi ý sẵn trong ô, nên dựng lại bằng hai sự kiện.
    def _hien_goi_y(self) -> None:
        self._dang_goi_y = True
        tk.Entry.insert(self, 0, self._goi_y)
        tk.Entry.configure(self, fg="#98a2b3")

    def _vao(self, _event=None) -> None:
        if getattr(self, "_dang_goi_y", False):
            tk.Entry.delete(self, 0, "end")
            tk.Entry.configure(self, fg=self._mau_chu)
            self._dang_goi_y = False

    def _ra(self, _event=None) -> None:
        if not tk.Entry.get(self):
            self._hien_goi_y()

    def get(self) -> str:
        if getattr(self, "_dang_goi_y", False):
            return ""
        return tk.Entry.get(self)

    def insert(self, index, string):  # noqa: D102
        self._vao()
        return tk.Entry.insert(self, index, string)

    def delete(self, first, last=None):  # noqa: D102
        self._vao()
        return tk.Entry.delete(self, first, last)


class CTkTextbox(_Nen, tk.Text):
    _DOI_CO_CHU = True

    def __init__(self, master=None, **kwargs):
        kwargs.setdefault("fg_color", _NEN_O_NHAP)
        kwargs.setdefault("text_color", _CHU)
        ra = _dich(kwargs, master, doi_co_chu=True)
        ra.setdefault("relief", "flat")
        ra.setdefault("bd", 0)
        ra.setdefault("highlightthickness", 1)
        ra.setdefault("highlightbackground", _VIEN)
        ra.setdefault("highlightcolor", _VIEN)
        ra.setdefault("insertbackground", _CHU)
        ra.setdefault("selectbackground", theme.DARK_CARD)
        ra.setdefault("selectforeground", _CHU)
        ra.setdefault("wrap", "word")
        ra.setdefault("padx", 8)
        ra.setdefault("pady", 6)
        tk.Text.__init__(self, master, **ra)


# ── Chọn trong danh sách ─────────────────────────────────────────────────────


class CTkOptionMenu(_Nen, ttk.Combobox):
    _DOI_CO_CHU = True

    def __init__(self, master=None, **kwargs):
        lenh = kwargs.pop("command", None)
        bien = kwargs.pop("variable", None) or tk.StringVar(master=master)
        values = list(kwargs.pop("values", []) or [])
        ra = _dich(kwargs, master, doi_co_chu=True)
        for bo in ("bg", "fg", "highlightthickness", "highlightbackground",
                   "highlightcolor", "height", "anchor", "relief", "bd", "cursor"):
            ra.pop(bo, None)   # ttk không nhận các tuỳ chọn của tk thường
        # `state` phải được RÚT RA trước, không được để lọt vào `**ra`: nó cũng
        # là tham số cố định ngay dưới, và `ttk.Combobox` sẽ ném
        # `TypeError: got multiple values for keyword argument 'state'`.
        #
        # Đây không phải lỗi thẩm mỹ: nó nổ ngay lúc dựng khu Đăng nhập hàng
        # loạt, tức là CẢ tab Vận hành không mở lên được — mà ShopAPI Ops thì
        # dựng đúng tab đó lúc khởi động, nên cả tool "bấm vào không lên gì cả".
        # Giữ nguyện vọng của nơi gọi thay vì vứt đi: `CTkComboBox` đọc lại ở
        # dưới để biết ô này cho gõ tay hay chỉ được chọn.
        self._trang_thai_xin = ra.pop("state", None)
        ttk.Combobox.__init__(self, master, textvariable=bien, values=values,
                              state="readonly", **ra)
        self._bien = bien
        if values:
            bien.set(values[0])
        if lenh is not None:
            self.bind("<<ComboboxSelected>>", lambda _e: lenh(self._bien.get()), add="+")

    def set(self, value) -> None:  # noqa: D102
        self._bien.set(value)

    def get(self):  # noqa: D102
        return self._bien.get()

    def configure(self, **kwargs):  # noqa: D102
        if "values" in kwargs:
            ttk.Combobox.configure(self, values=list(kwargs.pop("values") or []))
        if "state" in kwargs:
            state = kwargs.pop("state")
            ttk.Combobox.configure(self, state="readonly" if state == "normal" else state)
        kwargs.pop("fg_color", None)
        kwargs.pop("text_color", None)
        kwargs.pop("font", None)
        return ttk.Combobox.configure(self, **kwargs) if kwargs else None

    config = configure


class CTkComboBox(CTkOptionMenu):
    """Như :class:`CTkOptionMenu` nhưng khách gõ tay được."""

    def __init__(self, master=None, **kwargs):
        CTkOptionMenu.__init__(self, master, **kwargs)
        # Mặc định cho gõ tay, NHƯNG nơi gọi xin `state="readonly"` thì phải
        # được tôn trọng: ô chọn tài khoản ở khu Đăng nhập hàng loạt cố ý không
        # cho gõ, vì một email gõ sai ở đó sẽ mở Chrome bằng nhầm hồ sơ.
        ttk.Combobox.configure(self, state=self._trang_thai_xin or "normal")


class CTkSegmentedButton(_Nen, tk.Frame):
    """Dãy nút chọn một — dựng bằng `Radiobutton` phẳng."""

    def __init__(self, master=None, **kwargs):
        lenh = kwargs.pop("command", None)
        bien = kwargs.pop("variable", None) or tk.StringVar(master=master)
        values = list(kwargs.pop("values", []) or [])
        font = kwargs.get("font")
        nen = _nen_cua(master)
        tk.Frame.__init__(self, master, bg=nen, highlightthickness=0)
        self._bien = bien
        self._lenh = lenh
        self._nut = {}
        for value in values:
            nut = tk.Radiobutton(
                self, text=str(value), value=value, variable=bien, font=font,
                indicatoron=0, relief="flat", bd=1, padx=10, pady=3, cursor="hand2",
                bg=theme.CARD_ALT, fg=_CHU, selectcolor=theme.ACCENT,
                activebackground=theme.HOVER, highlightthickness=0,
                command=self._chon,
            )
            nut.pack(side="left", padx=1)
            self._nut[value] = nut
        if values and not bien.get():
            bien.set(values[0])

    def _chon(self) -> None:
        if self._lenh is not None:
            self._lenh(self._bien.get())

    def set(self, value) -> None:  # noqa: D102
        self._bien.set(value)

    def get(self):  # noqa: D102
        return self._bien.get()

    def configure(self, **kwargs):  # noqa: D102
        if "values" in kwargs:
            kwargs.pop("values")  # danh sách cố định sau khi dựng
        if "state" in kwargs:
            state = kwargs.pop("state")
            for nut in self._nut.values():
                nut.configure(state=state)
        return None

    config = configure


# ── Thanh trượt và thanh tiến độ ─────────────────────────────────────────────


#: Độ dày thanh trượt, điểm ảnh. Đủ để bấm trúng, không chiếm chỗ.
_DAY_THANH_TRUOT = 16


class CTkSlider(_Nen, tk.Scale):
    """Thanh trượt.

    ═══ BẪY ĐÃ DÍNH ═══

    Hai thư viện hiểu `width` NGƯỢC NHAU:

    * customtkinter: `width` = **chiều dài** thanh trượt
    * tkinter `Scale`: `width` = **độ dày** (bề ngang của rãnh)

    Truyền thẳng `width=220` sang tkinter cho ra một khối xám dày 220 điểm ảnh
    chắn hết tab Giọng nói, đẩy nút "Tạo giọng nói" ra ngoài màn hình. Nên ở đây
    `width` phải đổi thành `length`, và độ dày do ta đặt.
    """

    def __init__(self, master=None, **kwargs):
        kwargs.pop("number_of_steps", None)
        lenh = kwargs.pop("command", None)
        dai = kwargs.pop("width", None)
        kwargs.pop("height", None)          # tkinter không đặt được, xem docstring
        nen = _nen_cua(master)
        ra = _dich(kwargs, master, doi_co_chu=False)
        if dai:
            ra["length"] = int(dai)
        ra["width"] = _DAY_THANH_TRUOT
        ra.setdefault("orient", "horizontal")
        ra.setdefault("showvalue", 0)
        # Núm trượt lấy màu `bg` của widget. Để `bg` bằng nền thẻ là núm trắng
        # nằm trên rãnh trắng — nhìn ảnh chụp chỉ thấy hai vạch xám rời nhau,
        # không biết đang kéo cái gì. Nên núm phải là màu nhấn.
        ra.setdefault("bg", theme.ACCENT)
        ra.setdefault("activebackground", theme.ACCENT_DARK)
        ra.setdefault("troughcolor", theme.BORDER)
        ra.setdefault("sliderrelief", "flat")
        ra.setdefault("sliderlength", 18)
        ra.setdefault("highlightthickness", 0)
        ra.setdefault("highlightbackground", nen)
        ra.setdefault("bd", 0)
        ra.setdefault("resolution", 0.01)
        if lenh is not None:
            ra["command"] = lambda value: lenh(float(value))
        tk.Scale.__init__(self, master, **ra)


class CTkProgressBar(_Nen, ttk.Progressbar):
    def __init__(self, master=None, **kwargs):
        che_do = kwargs.pop("mode", "determinate")
        ra = {}
        if "width" in kwargs:
            ra["length"] = kwargs["width"]
        if "orientation" in kwargs:
            ra["orient"] = kwargs["orientation"]
        ttk.Progressbar.__init__(self, master, mode=che_do, maximum=1.0, **ra)

    def set(self, value: float) -> None:
        """customtkinter dùng thang 0–1; ta giữ nguyên bằng `maximum=1.0`."""
        try:
            self["value"] = max(0.0, min(1.0, float(value)))
        except Exception:  # noqa: BLE001
            pass

    def get(self) -> float:  # noqa: D102
        try:
            return float(self["value"])
        except Exception:  # noqa: BLE001
            return 0.0

    def configure(self, **kwargs):  # noqa: D102
        if "mode" in kwargs:
            ttk.Progressbar.configure(self, mode=kwargs.pop("mode"))
        for bo in ("fg_color", "progress_color", "corner_radius", "height", "width", "font"):
            kwargs.pop(bo, None)
        return ttk.Progressbar.configure(self, **kwargs) if kwargs else None

    config = configure

    def start(self, interval=None):  # noqa: D102
        try:
            ttk.Progressbar.start(self, interval or 50)
        except Exception:  # noqa: BLE001
            pass

    def stop(self):  # noqa: D102
        try:
            ttk.Progressbar.stop(self)
        except Exception:  # noqa: BLE001
            pass


# ── Khung cuộn ───────────────────────────────────────────────────────────────


class CTkScrollableFrame(tk.Frame):
    """Khung cuộn được.

    Điểm khác quan trọng so với customtkinter: nó gắn bánh xe chuột **cục bộ**
    thay vì `bind_all` toàn ứng dụng. Bản của customtkinter cộng dồn tay nghe
    vào phạm vi toàn cục và **không gỡ khi widget bị huỷ** — đo được 39 tay nghe
    còn lại sau khi đã huỷ hết khung.

    `_parent_canvas` giữ nguyên tên vì code hiện có gọi tới nó để cuộn xuống đáy.
    """

    def __init__(self, master=None, **kwargs):
        nen = _mau(kwargs.pop("fg_color", None)) or _nen_cua(master)
        if nen == "transparent":
            nen = _nen_cua(master)
        for bo in ("corner_radius", "border_width", "border_color", "label_text",
                   "scrollbar_button_color", "scrollbar_button_hover_color", "orientation"):
            kwargs.pop(bo, None)
        rong = kwargs.pop("width", None)
        cao = kwargs.pop("height", None)
        tk.Frame.__init__(self, master, bg=nen, highlightthickness=0,
                          **{k: v for k, v in kwargs.items() if k in ("bg",)})
        if rong:
            self.configure(width=rong)
        if cao:
            self.configure(height=cao)
        self._parent_canvas = tk.Canvas(self, bg=nen, highlightthickness=0, bd=0,
                                        relief="flat", takefocus=0)
        self._thanh = ttk.Scrollbar(self, orient="vertical", command=self._parent_canvas.yview)
        self._parent_canvas.configure(yscrollcommand=self._thanh.set)
        self._thanh.pack(side="right", fill="y")
        self._parent_canvas.pack(side="left", fill="both", expand=True)
        self._ruot = tk.Frame(self._parent_canvas, bg=nen, highlightthickness=0)
        self._cua = self._parent_canvas.create_window((0, 0), window=self._ruot, anchor="nw")
        self._ruot.bind("<Configure>", self._ruot_doi)
        self._parent_canvas.bind("<Configure>", self._canvas_doi)
        # Cục bộ, và gỡ theo widget — không rò ra phạm vi toàn ứng dụng.
        for muc in (self._parent_canvas, self._ruot):
            muc.bind("<MouseWheel>", self._lan, add="+")
        self._ruot.bind("<Enter>", lambda _e: self._parent_canvas.focus_set(), add="+")

    def _ruot_doi(self, _event=None) -> None:
        """Cập nhật vùng cuộn — chỉ khi thật sự đổi, và không cho gọi lồng nhau.

        ═══ VÌ SAO CẦN CẢ HAI LỚP CHẶN ═══

        Đặt lại vùng cuộn làm widget đổi kích thước, mà đổi kích thước lại bắn
        `<Configure>` gọi ngược vào đây. Tệ hơn: nhãn có `wraplength` xuống dòng
        lại khi bề rộng đổi, nên chiều cao đổi theo, nên vùng cuộn đổi tiếp — hai
        trạng thái thay nhau vô tận. So giá trị KHÔNG đủ chặn vòng hai nhịp đó;
        `tkinter.update()` không bao giờ trả về và cửa sổ treo cứng ngay lúc mở.
        """
        if getattr(self, "_dang_chinh", False):
            return
        self._dang_chinh = True
        try:
            khung = self._parent_canvas.bbox("all")
            if khung != getattr(self, "_khung_cu", None):
                self._khung_cu = khung
                self._parent_canvas.configure(scrollregion=khung)
        finally:
            self._dang_chinh = False

    def _canvas_doi(self, event) -> None:
        if getattr(self, "_dang_chinh", False):
            return
        if event.width == getattr(self, "_rong_cu", None):
            return
        self._dang_chinh = True
        try:
            self._rong_cu = event.width
            self._parent_canvas.itemconfigure(self._cua, width=event.width)
        finally:
            self._dang_chinh = False

    def _lan(self, event) -> None:
        if self._parent_canvas.yview() == (0.0, 1.0):
            return  # không có gì để cuộn thì đừng nuốt sự kiện
        self._parent_canvas.yview_scroll(-int(event.delta / 120), "units")

    # Widget con phải nằm trong khung ruột, không nằm thẳng trong `self`.
    @property
    def _khung_con(self) -> tk.Frame:
        return self._ruot

    def winfo_children(self):  # noqa: D102
        return self._ruot.winfo_children()


def _con_vao_ruot(cls):
    """Cho `CTkScrollableFrame(...)` nhận widget con vào khung ruột.

    Code hiện có viết `ctk.CTkLabel(khung_cuon, ...)` — tức là truyền chính khung
    cuộn làm cha. Với customtkinter điều đó hợp lệ vì nó tự chuyển tiếp. Ở đây ta
    làm y hệt bằng cách trả khung ruột ra khi ai đó dùng khung cuộn làm cha.
    """
    goc = cls.__init__

    def __init__(self, master=None, **kwargs):
        if isinstance(master, CTkScrollableFrame):
            master = master._ruot
        goc(self, master, **kwargs)

    cls.__init__ = __init__
    return cls


for _lop in (CTkFrame, CTkLabel, CTkButton, CTkEntry, CTkTextbox, CTkCheckBox,
             CTkOptionMenu, CTkComboBox, CTkSegmentedButton, CTkSlider,
             CTkProgressBar, CTkScrollableFrame):
    _con_vao_ruot(_lop)


# ── Ảnh ──────────────────────────────────────────────────────────────────────


class CTkImage:
    """Bọc ảnh Pillow cho hợp API customtkinter, trả về `PhotoImage` thật."""

    def __init__(self, light_image=None, dark_image=None, size=None, **_kwargs):
        from PIL import ImageTk

        anh = light_image or dark_image
        if size and anh is not None:
            try:
                from PIL import Image

                anh = anh.resize(tuple(int(v) for v in size), Image.LANCZOS)
            except Exception:  # noqa: BLE001 - ảnh lạ thì giữ nguyên cỡ
                pass
        self._anh = ImageTk.PhotoImage(anh) if anh is not None else None

    def __str__(self) -> str:
        return str(self._anh) if self._anh is not None else ""
