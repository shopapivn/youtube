"""Bộ công cụ Agent được phép gọi — mắt và tay của nó trên máy khách.

═══ VÌ SAO CÓ FILE NÀY ═══

Chủ dự án, 12/08/2026: *"tao đang dùng vs code claude code extension thì tao code
tool rất ok, tao muốn khách tao cũng được trải nghiệm như vậy"*.

Thứ làm Claude Code khác hẳn một khung chat **không phải mô hình**, mà là vòng
lặp công cụ: gọi công cụ → đọc kết quả → nghĩ → gọi tiếp. Agent cũ của Studio bắn
một phát duy nhất và bắt mô hình trả về một JSON, nên nó luôn phải **đoán**. File
này là bộ công cụ để nó **biết**.

═══ QUYỀN ═══

Chủ dự án đã chốt: *"nó có toàn quyền, quyền cao nhất"*. Nên đọc và ghi file
không bị giới hạn theo thư mục.

Ba giới hạn còn lại **không phải hàng rào quyền**, mà là giới hạn kỹ thuật, và
mỗi cái đều có lý do đo được:

* `TRAN_DOC` — đọc một file 40MB vào ngữ cảnh thì vừa vỡ giới hạn mô hình, vừa
  tính tiền cho thứ không ai đọc.
* `TRAN_LIET_KE` — thư mục kết quả của người làm lâu năm có hàng nghìn file.
* **Không có công cụ xoá.** Không phải vì thiếu quyền: vì không việc nào trong
  luồng dựng tool cần xoá, mà xoá nhầm thì không có thùng rác để lấy lại. Agent
  cần dọn thì bảo khách — họ xoá bằng File Explorer, thấy tận mắt thứ mình xoá.

═══ MỌI VIỆC ĐỀU KỂ LẠI ═══

Mỗi lời gọi trả về một dòng `ke_lai` bằng tiếng người, để khung chat hiện được
*"đã đọc thư mục ket-qua/giong-noi — 128 file"*. Agent làm gì trên máy khách thì
khách phải nhìn thấy, không phải tin.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional

from .kho_cua_khach import quet_kho, tom_tat_kho
from .mau_kich_ban import liet_ke as liet_ke_mau, luu as luu_mau
from .chuoi_buoc import Buoc
from .skill_rieng import SkillRiengError, liet_ke_rieng, luu_skill

__all__ = ["CongCu", "KetQuaGoi", "BoCongCu", "MO_TA_CONG_CU", "TRAN_DOC",
           "TRAN_LIET_KE"]

#: Trần ký tự khi đọc một file vào ngữ cảnh.
TRAN_DOC = 60_000

#: Trần số mục khi liệt kê một thư mục.
TRAN_LIET_KE = 300

MA_HOA = ("utf-8-sig", "utf-8", "cp1258", "latin-1")


@dataclass
class KetQuaGoi:
    """Kết quả một lời gọi công cụ.

    `noi_dung` gửi lại cho mô hình; `ke_lai` hiện cho khách đọc. Hai thứ khác
    nhau: mô hình cần dữ liệu, khách cần biết chuyện gì vừa xảy ra trên máy mình.
    """

    noi_dung: str
    ke_lai: str
    hong: bool = False


@dataclass
class CongCu:
    ten: str
    mo_ta: str
    tham_so: Mapping[str, Any]
    chay: Callable[..., KetQuaGoi]


def _doc_chu(duong_dan: str) -> Optional[str]:
    for ma in MA_HOA:
        try:
            with open(duong_dan, "r", encoding=ma) as tep:
                return tep.read()
        except (UnicodeDecodeError, OSError):
            continue
    return None


class BoCongCu:
    """Bộ công cụ gắn với một bản cài. Giữ nhật ký để giao diện kể lại."""

    def __init__(self, base_dir: str, giao_dien: Any = None):
        """`giao_dien` là tay của agent trên thanh bên, do tầng UI đưa vào.

        Lõi không import Qt, nên nó không tự đổi được tên tab. Tầng UI truyền vào
        một vật có `doi_ten_tab(ten_cu, ten_moi)`, `an_tab(ten)`, `hien_tab(ten)`,
        `danh_sach_tab()`. Không truyền thì ba công cụ đó **không được khai báo** —
        thà thiếu công cụ còn hơn khai một công cụ gọi vào là hỏng.
        """
        self.base_dir = os.path.abspath(base_dir)
        self.giao_dien = giao_dien
        self.nhat_ky: List[str] = []
        self.da_tao: List[str] = []

    # ── Mắt ──────────────────────────────────────────────────────────────────

    def xem_thu_muc(self, duong_dan: str = "") -> KetQuaGoi:
        goc = self._that(duong_dan)
        if not os.path.isdir(goc):
            return KetQuaGoi("Không có thư mục: {0}".format(goc),
                             "tìm thư mục {0} — không có".format(duong_dan or "."),
                             hong=True)
        try:
            ten = sorted(os.listdir(goc))
        except OSError as loi:
            return KetQuaGoi("Không đọc được: {0}".format(loi),
                             "đọc thư mục {0} — hỏng".format(duong_dan), hong=True)
        dong, thua = [], max(0, len(ten) - TRAN_LIET_KE)
        for t in ten[:TRAN_LIET_KE]:
            duong = os.path.join(goc, t)
            if os.path.isdir(duong):
                dong.append("{0}/".format(t))
            else:
                try:
                    dong.append("{0}  ({1} byte)".format(t, os.path.getsize(duong)))
                except OSError:
                    dong.append(t)
        if thua:
            dong.append("… còn {0} mục nữa".format(thua))
        return KetQuaGoi("\n".join(dong) or "(thư mục trống)",
                         "xem thư mục {0} — {1} mục".format(duong_dan or ".", len(ten)))

    def doc_file(self, duong_dan: str) -> KetQuaGoi:
        that = self._that(duong_dan)
        chu = _doc_chu(that)
        if chu is None:
            return KetQuaGoi("Không đọc được file: {0}".format(that),
                             "đọc {0} — không đọc được".format(duong_dan), hong=True)
        cat = len(chu) > TRAN_DOC
        if cat:
            chu = chu[:TRAN_DOC] + "\n\n[… đã cắt bớt cho vừa ngữ cảnh …]"
        return KetQuaGoi(chu, "đọc {0} — {1} ký tự{2}".format(
            duong_dan, len(chu), " (đã cắt)" if cat else ""))

    def kho_cua_khach(self) -> KetQuaGoi:
        """Ảnh chụp gọn về việc khách đang làm — rẻ hơn tự đi liệt kê từng thư mục."""
        chu = tom_tat_kho(quet_kho(self.base_dir))
        return KetQuaGoi(chu, "xem qua công việc của khách")

    # ── Tay ──────────────────────────────────────────────────────────────────

    def ghi_file(self, duong_dan: str, noi_dung: str) -> KetQuaGoi:
        that = self._that(duong_dan)
        try:
            thu_muc = os.path.dirname(that)
            if thu_muc:
                os.makedirs(thu_muc, exist_ok=True)
            with open(that, "w", encoding="utf-8") as tep:
                tep.write(noi_dung)
        except OSError as loi:
            return KetQuaGoi("Không ghi được: {0}".format(loi),
                             "ghi {0} — hỏng".format(duong_dan), hong=True)
        self.da_tao.append(that)
        return KetQuaGoi("Đã ghi {0} ký tự vào {1}".format(len(noi_dung), that),
                         "ghi {0} — {1} ký tự".format(duong_dan, len(noi_dung)))

    def tao_skill(self, ten: str, prompt: str, mo_ta: str = "",
                  nhan_dau_vao: str = "Nội dung", goi_y: str = "") -> KetQuaGoi:
        """Đẻ ra một Skill — việc lẻ, hiện ngay trong tab Skill."""
        try:
            duong = luu_skill(self.base_dir, ten, prompt, mo_ta=mo_ta,
                              nhan_dau_vao=nhan_dau_vao, goi_y=goi_y)
        except SkillRiengError as loi:
            return KetQuaGoi("Skill chưa dùng được: {0}".format(loi),
                             "tạo Skill “{0}” — chưa được".format(ten), hong=True)
        self.da_tao.append(duong)
        return KetQuaGoi(
            "Đã tạo Skill “{0}”. Nó nằm trong tab Skill, khách bấm chạy được ngay."
            .format(ten),
            "tạo Skill “{0}”".format(ten))

    def tao_template(self, ten: str, cac_prompt: List[str]) -> KetQuaGoi:
        """Đẻ ra một template nhiều bước cho tab Viết kịch bản."""
        buoc = [Buoc("Prompt {0}".format(i + 1), str(p))
                for i, p in enumerate(cac_prompt or []) if str(p).strip()]
        if not buoc:
            return KetQuaGoi("Template phải có ít nhất một prompt.",
                             "tạo template “{0}” — chưa được".format(ten), hong=True)
        try:
            duong = luu_mau(self.base_dir, ten, buoc)
        except OSError as loi:
            return KetQuaGoi("Không lưu được: {0}".format(loi),
                             "tạo template “{0}” — hỏng".format(ten), hong=True)
        self.da_tao.append(duong)
        return KetQuaGoi(
            "Đã tạo template “{0}” gồm {1} prompt, nằm ở tab Viết kịch bản → Template."
            .format(ten, len(buoc)),
            "tạo template “{0}” ({1} prompt)".format(ten, len(buoc)))

    def dang_co_gi(self) -> KetQuaGoi:
        """Skill và template khách đã có — để agent đừng đẻ trùng cái đã có."""
        skill = [s.ten for s in liet_ke_rieng(self.base_dir)]
        mau = [m.ten for m in liet_ke_mau(self.base_dir) if not m.di_kem]
        chu = json.dumps({"skill_cua_khach": skill, "template_cua_khach": mau},
                         ensure_ascii=False)
        return KetQuaGoi(chu, "xem lại Skill và template khách đã có")

    # ── Tay trên thanh bên ───────────────────────────────────────────────────

    def danh_sach_tab(self) -> KetQuaGoi:
        bang = self.giao_dien.danh_sach_tab()
        return KetQuaGoi(json.dumps(bang, ensure_ascii=False), "xem danh sách tab")

    def doi_ten_tab(self, ten_cu: str, ten_moi: str) -> KetQuaGoi:
        ok, ly_do = self.giao_dien.doi_ten_tab(ten_cu, ten_moi)
        return KetQuaGoi(ly_do, "đổi tên tab “{0}” → “{1}”".format(ten_cu, ten_moi),
                         hong=not ok)

    def an_tab(self, ten: str) -> KetQuaGoi:
        ok, ly_do = self.giao_dien.an_tab(ten)
        return KetQuaGoi(ly_do, "ẩn tab “{0}”".format(ten), hong=not ok)

    def hien_tab(self, ten: str) -> KetQuaGoi:
        ok, ly_do = self.giao_dien.hien_tab(ten)
        return KetQuaGoi(ly_do, "hiện lại tab “{0}”".format(ten), hong=not ok)

    # ── Hạ tầng ──────────────────────────────────────────────────────────────

    def _that(self, duong_dan: str) -> str:
        """Đường dẫn tương đối tính từ thư mục cài; đường tuyệt đối giữ nguyên.

        Chủ dự án đã chốt agent có toàn quyền, nên **không chặn** đường dẫn ra
        ngoài thư mục cài. Đổi lại mọi lời gọi đều được kể lại kèm đường dẫn thật
        — khách nhìn thấy agent chạm vào đâu.
        """
        duong_dan = (duong_dan or "").strip()
        if not duong_dan:
            return self.base_dir
        if os.path.isabs(duong_dan):
            return os.path.abspath(duong_dan)
        return os.path.abspath(os.path.join(self.base_dir, duong_dan))

    def bang(self) -> Dict[str, CongCu]:
        cong_cu = list(self._cong_cu_chung())
        if self.giao_dien is not None:
            cong_cu += list(self._cong_cu_giao_dien())
        return {c.ten: c for c in cong_cu}

    def _cong_cu_giao_dien(self):
        return (
            CongCu("danh_sach_tab",
                   "Xem các tab đang có trên thanh bên và tên hiện tại của chúng.",
                   {"type": "object", "properties": {}}, self.danh_sach_tab),
            CongCu("doi_ten_tab", "Đổi tên một tab trên thanh bên.",
                   {"type": "object", "properties": {
                       "ten_cu": {"type": "string", "description": "Tên tab đang hiện."},
                       "ten_moi": {"type": "string"}},
                    "required": ["ten_cu", "ten_moi"]}, self.doi_ten_tab),
            CongCu("an_tab", "Ẩn một tab khỏi thanh bên.",
                   {"type": "object", "properties": {"ten": {"type": "string"}},
                    "required": ["ten"]}, self.an_tab),
            CongCu("hien_tab", "Hiện lại một tab đã ẩn.",
                   {"type": "object", "properties": {"ten": {"type": "string"}},
                    "required": ["ten"]}, self.hien_tab),
        )

    def _cong_cu_chung(self):
        return (
            CongCu("xem_thu_muc", "Liệt kê file trong một thư mục của khách.",
                   {"type": "object", "properties": {
                       "duong_dan": {"type": "string",
                                     "description": "Tương đối với thư mục cài, "
                                                    "để trống là thư mục gốc."}}},
                   self.xem_thu_muc),
            CongCu("doc_file", "Đọc nội dung một file chữ (.txt, .srt, .json…).",
                   {"type": "object", "properties": {
                       "duong_dan": {"type": "string"}},
                    "required": ["duong_dan"]},
                   self.doc_file),
            CongCu("kho_cua_khach",
                   "Tóm tắt công việc khách đã làm: đã tạo bao nhiêu giọng đọc, "
                   "ảnh, video; dùng tab nào nhiều; có template gì.",
                   {"type": "object", "properties": {}}, self.kho_cua_khach),
            CongCu("dang_co_gi",
                   "Liệt kê Skill và template khách đã có, để không tạo trùng.",
                   {"type": "object", "properties": {}}, self.dang_co_gi),
            CongCu("ghi_file", "Ghi nội dung ra một file trên máy khách.",
                   {"type": "object", "properties": {
                       "duong_dan": {"type": "string"},
                       "noi_dung": {"type": "string"}},
                    "required": ["duong_dan", "noi_dung"]},
                   self.ghi_file),
            CongCu("tao_skill",
                   "Tạo một Skill mới cho khách — một việc lẻ: đưa vào một thứ, "
                   "nhận về một thứ. Hiện ngay trong tab Skill.",
                   {"type": "object", "properties": {
                       "ten": {"type": "string", "description": "Tên ngắn, tối đa 48 ký tự."},
                       "prompt": {"type": "string",
                                  "description": "Lời nhắc. BẮT BUỘC chứa {0} — "
                                                 "chỗ chèn nội dung khách nhập."},
                       "mo_ta": {"type": "string"},
                       "nhan_dau_vao": {"type": "string",
                                        "description": "Nhãn ô nhập, ví dụ “Kịch bản cần chấm”."},
                       "goi_y": {"type": "string", "description": "Chữ mờ trong ô nhập."}},
                    "required": ["ten", "prompt"]},
                   self.tao_skill),
            CongCu("tao_template",
                   "Tạo template nhiều prompt nối nhau cho tab Viết kịch bản. "
                   "Kết quả prompt trước là đầu vào prompt sau.",
                   {"type": "object", "properties": {
                       "ten": {"type": "string"},
                       "cac_prompt": {"type": "array", "items": {"type": "string"}}},
                    "required": ["ten", "cac_prompt"]},
                   self.tao_template),
        )


def MO_TA_CONG_CU(bo: BoCongCu) -> List[Dict[str, Any]]:  # noqa: N802 — tên hằng
    """Khai báo công cụ theo dạng `tools` của API — gửi kèm mỗi lượt gọi."""
    return [{"type": "function",
             "function": {"name": c.ten, "description": c.mo_ta,
                          "parameters": dict(c.tham_so)}}
            for c in bo.bang().values()]
