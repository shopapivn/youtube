"""Bo lap ke hoach hoi thoai offline cho tab Agent.

Module chi bien cau noi tieng Viet thanh de xuat co cau truc.  No khong chay tool,
khong sua workflow that va khong goi LLM; UI phai cho nguoi dung xac nhan action.

Ba luat viet o day, ca ba deu la loi da tra gia:

* **Khong bao gio tu choi mot viec Studio lam duoc.** Doi ten tab, an/hien tab
  deu di qua `core.ui_customization` — cho nay chi noi cac manh lai.
* **Cau tra loi khong duoc la ngo cut.** Moi loi dap khong lam duoc viec deu
  phai keo theo 2-3 dong khach chep lai duoc ngay. Khach cua tool nay khong biet
  code, ho khong tu doan ra phai go gi.
* **Dai tu tro lui la cach nguoi Viet noi chuyen.** *“sua tool do”*, *“cai vua
  nay”* phai nhin lai luot truoc, khong duoc coi la yeu cau moi toanh.
"""

from __future__ import annotations

import re
import unicodedata
import copy
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .ui_customization import (
    NHAN_TAB_MAC_DINH, ThayDoiGiaoDien, parse_ui_change, ten_tab_dang_co,
)


FULL_PIPELINE = (
    "research.youtube", "content.remake", "voice.shopapi", "transcribe.local",
    "prompt.workbook", "image.shopapi", "video.shopapi", "edit.ffmpeg",
)
SHORT_PIPELINE = ("research.youtube", "content.remake")
RESEARCH_PIPELINE = ("research.youtube",)
STARTER_PIPELINE = ("research.youtube", "content.remake", "voice.shopapi")

# Cong chuan giua cac tool golden. Nhieu nhanh phu (content_package -> context,
# audio/subtitles -> edit) duoc them rieng ben duoi.
MAIN_PORTS = {
    ("research.youtube", "content.remake"): ("research", "research"),
    ("content.remake", "voice.shopapi"): ("script", "script"),
    ("voice.shopapi", "transcribe.local"): ("audio", "audio"),
    ("transcribe.local", "prompt.workbook"): ("subtitles", "subtitles"),
    ("prompt.workbook", "image.shopapi"): ("scenes", "scenes"),
    ("image.shopapi", "video.shopapi"): ("images", "images"),
    ("video.shopapi", "edit.ffmpeg"): ("clips", "clips"),
}

ALIASES = {
    "research.youtube": ("research", "nghien cuu", "doi thu", "youtube"),
    "content.remake": ("content", "noi dung", "kich ban", "script"),
    "voice.shopapi": ("voice", "giong doc", "audio", "11lab"),
    "transcribe.local": ("srt", "subtitle", "phu de", "transcribe"),
    "prompt.workbook": ("excel", "workbook", "prompt table", "bang prompt"),
    "image.shopapi": ("image", "anh", "hinh"),
    "video.shopapi": ("video", "clip", "veo"),
    "edit.ffmpeg": ("edit", "dung phim", "ffmpeg", "bien tap"),
}

#: Thứ tự của mỗi tool trong dây chuyền. Dùng để lấy ĐỦ bước tiên quyết: muốn
#: ảnh thì buộc phải có kịch bản → giọng đọc → phụ đề → bảng cảnh trước đó, vì
#: cổng vào của mỗi bước lấy đúng cổng ra của bước liền trước.
_BAC = {tool_id: index for index, tool_id in enumerate(FULL_PIPELINE)}

#: Cách khách gọi tên **kết quả** họ muốn cầm trên tay.
#:
#: ═══ VÌ SAO CẦN BẢNG NÀY, KHÁC HẲN `ALIASES` ═══
#:
#: `ALIASES` để hiểu câu LỆNH (“thêm voice”, “bỏ ảnh”) — có động từ, có tên tool.
#: Khách không biết code không nói kiểu đó. Họ nói thứ họ muốn nhận: *“làm giúp
#: tao content”*, *“tao muốn có giọng đọc”*, *“cho tao cái video”*. Bộ hiểu cũ
#: đòi đúng động-từ-cộng-tên-tool nên năm lượt liền trả lời “bạn cứ nói thẳng kết
#: quả bạn muốn” mà không dựng nổi một tool nào. Đó là hỏng đúng vào việc mà cả
#: sản phẩm sinh ra để làm.
#:
#: Từ ở đây cố ý rộng và đời thường. Nhận nhầm thì khách thấy một bản đề xuất hơi
#: lệch và sửa một câu; không nhận ra gì thì khách bế tắc.
_KET_QUA = {
    "research.youtube": ("nghien cuu", "doi thu", "ngach", "research", "phan tich kenh",
                         "kenh nao dang hot", "tim ngach"),
    "content.remake": ("content", "kich ban", "noi dung", "script", "bai viet",
                       "viet bai", "viet kich ban", "y tuong", "de tai", "outline"),
    "voice.shopapi": ("giong doc", "giong noi", "long tieng", "thuyet minh", "loi binh",
                      "voice", "mp3", "audio", "doc thanh tieng", "chuyen thanh giong"),
    "transcribe.local": ("phu de", "srt", "sub", "transcribe", "bat chu", "tao sub"),
    "prompt.workbook": ("excel", "bang prompt", "workbook", "chia canh", "phan canh",
                        "prompt tung canh", "bang canh"),
    "image.shopapi": ("anh", "hinh anh", "hinh", "image", "minh hoa"),
    "video.shopapi": ("video", "clip", "veo", "seedance", "lam video"),
    "edit.ffmpeg": ("ghep video", "dung phim", "edit", "render", "bien tap",
                    "video hoan chinh", "xuat video"),
}

#: Tên hiển thị của tool khách nhận được, đặt theo KẾT QUẢ chứ không theo tên kỹ thuật.
_TEN_THEO_DICH = {
    "research.youtube": "Nghiên cứu đối thủ",
    "content.remake": "Làm content",
    "voice.shopapi": "Tạo giọng đọc",
    "transcribe.local": "Tạo phụ đề",
    "prompt.workbook": "Chia cảnh & bảng prompt",
    "image.shopapi": "Tạo ảnh",
    "video.shopapi": "Tạo video",
    "edit.ffmpeg": "Video hoàn chỉnh",
}


@dataclass(frozen=True)
class AgentAction:
    """Mot thay doi du kien; caller quyet dinh co ap dung hay khong."""

    kind: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "payload": dict(self.payload)}


@dataclass(frozen=True)
class AgentPlan:
    reply: str
    actions: Tuple[AgentAction, ...] = ()
    proposed_workflow: Optional[Mapping[str, Any]] = None
    state: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reply": self.reply,
            "actions": [action.to_dict() for action in self.actions],
            "proposed_workflow": (dict(self.proposed_workflow)
                                  if self.proposed_workflow is not None else None),
            "state": dict(self.state),
        }


def plan_message(message: str, catalog: Any, workflow: Optional[Mapping[str, Any]] = None,
                 state: Optional[Mapping[str, Any]] = None, *,
                 history: Sequence[Mapping[str, str]] = (),
                 tabs: Optional[Mapping[str, str]] = None) -> AgentPlan:
    """Hieu mot tap lenh nho, an toan va co tinh quyet dinh.

    ``catalog`` chap nhan mapping id -> manifest, iterable manifest, hoac iterable dict.
    Workflow de xuat luon la ban sao moi; ham khong sua input cua caller.

    ``history`` la lich su hoi thoai (co the chua ca cau dang xu ly) — dung de
    hieu cau noi tro lui. ``tabs`` la bang *khoa tab -> nhan dang hien* cua vo
    giao dien dang chay; khong truyen thi lay bang mac dinh cua ban Qt.
    """
    original = (message or "").strip()
    text = _plain(original)
    new_state = dict(state or {})
    ids = _catalog_ids(catalog)
    stage = str(new_state.get("onboarding_stage") or "")

    # Chinh giao dien dat TRUOC moi nhanh khac. No la viec Studio lam chac chan
    # duoc, khong phu thuoc catalog, mang hay giai doan onboarding — de no roi
    # xuong duoi la de no bi mot nhanh khac nuot mat roi tra ve cau tu choi.
    giao_dien = _ke_hoach_giao_dien(original, tabs, new_state)
    if giao_dien is not None:
        return giao_dien

    tro_lui = _ke_hoach_tro_lui(original, text, catalog, workflow, new_state, history, tabs, ids)
    if tro_lui is not None:
        return tro_lui

    name = _assistant_name(original, text) or (_simple_name(original) if stage == "name" else None)
    if name:
        new_state.update({"assistant_name": name, "onboarding_stage": "goal",
                          "onboarding_complete": False})
        action = AgentAction("set_assistant_name", {"name": name})
        return AgentPlan(("Được, từ giờ tôi là {0}. Bạn muốn tool này giúp làm việc gì?\n\n"
                          "Nếu chưa biết bắt đầu ở đâu, có thể chọn:\n"
                          "1. Nghiên cứu đối thủ\n2. Làm content\n3. Tạo giọng đọc\n\n"
                          "Ta làm tốt từng tool con trước; khi ổn, bạn chỉ cần bảo tôi nối chúng lại.").format(name),
                         (action,), None, new_state)

    post_run = _post_run_step(original, text, workflow, new_state)
    if post_run is not None:
        return post_run

    onboarding = _onboarding_step(original, text, ids, new_state)
    if onboarding is not None:
        return onboarding

    requested = None
    if _has(text, "day du", "toan bo", "tron quy trinh", "tron bo", "tu dau den cuoi",
            "full", "tu a den z", "a-z", "end to end", "all tool") and _has(
            text, "pipeline", "quy trinh", "youtube", "day chuyen", "tool"):
        requested = FULL_PIPELINE
    elif _has(text, "nghien cuu content voice", "research content voice",
              "nghien cuu den voice", "research den voice"):
        requested = STARTER_PIPELINE
    elif _has(text, "research va content", "nghien cuu va content",
              "nghien cuu content", "research content"):
        requested = SHORT_PIPELINE
    elif _has(text, "chi nghien cuu", "tool nghien cuu", "pipeline nghien cuu",
              "research only"):
        requested = RESEARCH_PIPELINE
    if requested is not None:
        missing = [tool_id for tool_id in requested if tool_id not in ids]
        available = [tool_id for tool_id in requested if tool_id in ids]
        proposed = _new_workflow(
            available,
            "YouTube đầy đủ" if requested == FULL_PIPELINE else
            ("Nghiên cứu đến voice" if requested == STARTER_PIPELINE else
             ("Nghiên cứu và content" if requested == SHORT_PIPELINE else "Nghiên cứu YouTube")),
        )
        action = AgentAction("replace_workflow", {"workflow": proposed})
        suffix = ""
        if missing:
            suffix = " Chưa thể thêm: {0}.".format(", ".join(missing))
        return AgentPlan("Đã dựng bản đề xuất gồm {0} bước.{1}".format(len(available), suffix),
                         (action,), proposed, new_state)

    configured = _configuration_change(text, original, workflow)
    if configured is not None:
        proposed, changes = configured
        return AgentPlan("Đã tạo đề xuất cấu hình: {0}.".format(", ".join(changes)),
                         (AgentAction("configure_workflow", {"changes": changes}),), proposed, new_state)

    operation = _operation(text)
    tool_id = _resolve_alias(text, ids)
    if operation and tool_id:
        proposed = _copy_workflow(workflow)
        changed = _change_tool(proposed, operation, tool_id)
        if not changed:
            return AgentPlan(_no_change_reply(operation, tool_id, tabs), (), proposed, new_state)
        action = AgentAction(operation + "_tool", {"tool_id": tool_id})
        verbs = {"add": "thêm", "remove": "bỏ", "disable": "tắt", "enable": "bật"}
        return AgentPlan("Đã tạo đề xuất {0} {1}.".format(verbs[operation], tool_id),
                         (action,), proposed, new_state)

    # Khách gọi tên KẾT QUẢ muốn có ("làm giúp tao content", "thêm bước tạo ảnh
    # và video"). Dựng đủ dây chuyền tới đó, kể cả khi câu không có động từ nào.
    dich = _dich_xa_nhat(text, ids)
    if dich is not None:
        return _dung_toi_dich(dich, ids, new_state)

    if operation:
        return AgentPlan(_cau_khong_lam_duoc(
            "Tôi chưa rõ bạn muốn đổi phần nào. Hãy nói tên kết quả — ví dụ "
            "“thêm giọng đọc”, “bỏ phần ảnh”, “tắt bước video”.", tabs),
            (), _copy_workflow(workflow), new_state)
    return AgentPlan(_moi_chon_dich(tabs), (),
                     _copy_workflow(workflow) if workflow is not None else None, new_state)


#: Các `AgentAction` chạm vào giao diện chứ không chạm vào workflow.
#:
#: Trang Qt nhìn đúng tập này để biết hành động nào nó phải tự tay làm; lõi chỉ
#: mô tả, không có quyền vẽ.
HANH_DONG_GIAO_DIEN = ("rename_tab", "hide_tab", "show_tab")

#: Đại từ trỏ lui: “sửa tool **đó**”, “cái vừa nãy”, “làm tiếp đi”.
#:
#: Dò trên câu **CÒN DẤU**, không dò trên bản bỏ dấu như phần còn lại của module.
#: Bỏ dấu xong thì “đó/đấy/đầy/này/nãy” dồn hết về `do`/`day`/`nay`, và câu
#: *“pipeline youtube đầy đủ”* bị nhận nhầm là câu trỏ lui — mất luôn đường dựng
#: dây chuyền đầy đủ. Vài cụm không dấu vẫn giữ lại vì chúng không thể lẫn với
#: từ nào khác.
_TU_TRO_LUI = ("đó", "đấy", "này", "nãy", "kia",
               "vừa nói", "vừa nãy", "vừa rồi", "vừa xong", "ban nãy", "lúc nãy",
               "ở trên", "như vậy", "như thế",
               "làm tiếp", "tiếp đi", "tiếp tục",
               "vua noi", "vua nay", "vua roi", "vua xong", "ban nay", "luc nay",
               "lam tiep", "tiep di", "tiep tuc")

#: Trần độ dài của một câu trỏ lui. “sửa tool đó”, “vẫn cái đó”, “làm tiếp đi”
#: đều rất ngắn; câu dài hơn thường đã tự mang đủ nội dung của nó.
_TRAN_TU_TRO_LUI = 6

#: Giai đoạn mà Studio đang tự hỏi khách một câu có sẵn.
#:
#: Đang giữa những giai đoạn này thì “như vậy đi” là **câu trả lời cho câu hỏi
#: vừa rồi**, không phải câu trỏ lui — cướp nó là làm hỏng mạch onboarding.
_GIAI_DOAN_TU_DO = ("", "active", "complete")


def _ke_hoach_giao_dien(original: str, tabs: Optional[Mapping[str, str]],
                        state: Dict[str, Any]) -> Optional[AgentPlan]:
    """Đổi tên / ẩn / hiện tab — việc Studio làm được, nên không bao giờ được từ chối.

    Lời đáp viết ở thể đã-xong vì nơi gọi áp dụng hành động **ngay trước khi**
    vẽ câu trả lời (xem `ui_qt/trang_agent.py::_nhan_tra_loi`); áp không được thì
    chính nó nối thêm dòng báo hỏng.
    """
    thay_doi = parse_ui_change(original, tabs)
    if thay_doi is None:
        return None
    if not thay_doi.lam_duoc:
        return AgentPlan(_khong_ro_tab(thay_doi, tabs), (), None, state)
    if thay_doi.kieu == "doi_ten":
        loi = "Xong — tab “{0}” từ giờ tên là “{1}”.".format(
            thay_doi.old_label, thay_doi.new_label)
        hanh_dong = AgentAction("rename_tab", {"key": thay_doi.key,
                                               "label": thay_doi.new_label,
                                               "old_label": thay_doi.old_label})
    elif thay_doi.kieu == "an":
        loi = ("Đã ẩn tab “{0}” khỏi thanh bên. Muốn lấy lại chỉ cần nói "
               "“hiện tab {0}”.".format(thay_doi.old_label))
        hanh_dong = AgentAction("hide_tab", {"key": thay_doi.key,
                                             "label": thay_doi.old_label})
    else:
        loi = "Đã hiện lại tab “{0}” trên thanh bên.".format(thay_doi.old_label)
        hanh_dong = AgentAction("show_tab", {"key": thay_doi.key,
                                             "label": thay_doi.old_label})
    return AgentPlan(loi + "\n\n" + _con_lam_duoc(tabs, (thay_doi.key,)),
                     (hanh_dong,), None, state)


def _ke_hoach_tro_lui(original: str, text: str, catalog: Any,
                      workflow: Optional[Mapping[str, Any]], state: Dict[str, Any],
                      history: Sequence[Mapping[str, str]],
                      tabs: Optional[Mapping[str, str]], ids: set) -> Optional[AgentPlan]:
    """Câu nối ngắn trỏ về lượt trước: *“sửa tool đó”*, *“cái vừa nãy”*.

    Coi những câu này là yêu cầu mới toanh là bắt khách nhắc lại nguyên văn thứ
    họ vừa nói — không ai nói chuyện kiểu đó, và đúng chỗ này Agent đã trả lời
    trật hai lượt liền.
    """
    if str(state.get("onboarding_stage") or "") not in _GIAI_DOAN_TU_DO:
        return None
    if not _cau_tro_lui(original, ids):
        return None
    neo = _neo_truoc(history, text, ids)
    if neo is None:
        return AgentPlan(_cau_khong_lam_duoc(
            "Tôi chưa rõ “{0}” đang trỏ về việc nào — trước đó mình chưa nói tới "
            "thứ nào cả.".format(original), tabs), (), None, state)
    truoc = parse_ui_change(neo, tabs)
    if truoc is not None:
        # Không làm lại y nguyên việc cũ: đổi tên hai lần cùng một tên là thay
        # đổi ngầm sau lưng khách. Nêu thẳng các nước đi tiếp cho đúng tab đó.
        return AgentPlan(_moi_sua_tab(truoc, tabs), (), None, state)
    tiep = plan_message(neo, catalog, workflow, state, tabs=tabs)
    return AgentPlan("Bạn đang nói tới “{0}”.\n\n{1}".format(neo, tiep.reply),
                     tiep.actions, tiep.proposed_workflow, tiep.state)


def _cau_tro_lui(original: str, ids: set) -> bool:
    """Câu ngắn, có đại từ trỏ lui, và **tự nó không nêu nổi việc nào**.

    >>> _cau_tro_lui("sửa tool đó", set())
    True
    >>> _cau_tro_lui("làm tiếp đi", set())
    True
    >>> _cau_tro_lui("pipeline youtube đầy đủ", set())
    False
    >>> _cau_tro_lui("tao muốn có giọng đọc", {"voice.shopapi"})
    False
    """
    cau = (original or "").strip().lower()
    if not cau or len(cau.split()) > _TRAN_TU_TRO_LUI:
        return False
    if not any(re.search(r"(?<!\w)" + re.escape(tu) + r"(?!\w)", cau) for tu in _TU_TRO_LUI):
        return False
    return _dich_xa_nhat(_plain(cau), ids) is None


def _neo_truoc(history: Sequence[Mapping[str, str]], text: str,
               ids: set) -> Optional[str]:
    """Câu của khách mà “đó” đang trỏ về: lượt gần nhất tự nó có nội dung.

    Bỏ qua chính câu đang xử lý — trang Qt đưa lịch sử **đã gồm** câu vừa gõ.
    """
    for muc in reversed(list(history or ())):
        if not isinstance(muc, Mapping) or muc.get("role") != "user":
            continue
        noi_dung = str(muc.get("content") or "").strip()
        if not noi_dung or _plain(noi_dung) == text or _cau_tro_lui(noi_dung, ids):
            continue
        return noi_dung
    return None


def neo_giao_dien(message: str, history: Sequence[Mapping[str, str]] = (),
                  tabs: Optional[Mapping[str, str]] = None) -> Optional[ThayDoiGiaoDien]:
    """Câu trỏ lui mà thứ nó trỏ về là một việc giao diện.

    `core.agent_service` hỏi hàm này để **không giao câu đó cho mô hình**: việc
    giao diện thì Studio làm chắc chắn được, còn mô hình thì đoán — và nó đã
    đoán sai đúng theo hướng tệ nhất, trả lời *“mình không chỉnh sửa giao diện
    hay tab ví/tài khoản của ứng dụng được”*.
    """
    if not _cau_tro_lui(message, set()):
        return None
    neo = _neo_truoc(history, _plain(message or ""), set())
    return parse_ui_change(neo, tabs) if neo else None


def _tab_lam_vi_du(tabs: Optional[Mapping[str, str]] = None,
                   tru: Iterable[str] = ()) -> Tuple[str, ...]:
    """Nhãn tab dùng làm ví dụ trong lời gợi ý.

    Loại tab Agent ra: nó **không ẩn được** (ẩn đi là khách mất chính chỗ ra
    lệnh để bật lại), nên mời khách “ẩn tab Agent” là mời họ vào một câu báo lỗi.
    """
    bang = dict(tabs or NHAN_TAB_MAC_DINH)
    bo = set(tru) | {"agent"}
    ten = tuple(str(nhan) for khoa, nhan in bang.items()
                if khoa not in bo and str(nhan).strip())
    return ten or (NHAN_TAB_MAC_DINH["wallet"],)


def _goi_y_lam_duoc(tabs: Optional[Mapping[str, str]] = None) -> Tuple[str, ...]:
    """Ba dòng khách chép lại được nguyên văn, trong đó có một việc giao diện.

    Có một ví dụ giao diện là cố ý: khách không đoán được là Agent đổi tên tab
    được, mà đó lại đúng thứ họ hay xin đầu tiên.
    """
    return ("• “làm content” — tôi dựng tool viết kịch bản",
            "• “tạo giọng đọc” — tôi dựng tool cho ra file MP3",
            "• “đổi tên tab {0} thành Tài khoản” — tôi đổi tên tab ngay".format(
                _tab_lam_vi_du(tabs)[-1]))


def _cau_khong_lam_duoc(ly_do: str, tabs: Optional[Mapping[str, str]] = None) -> str:
    """Câu đáp khi chưa làm được việc — **luôn** kèm việc làm được ngay.

    “Bạn muốn mình giúp gì về workflow YouTube không?” là ngõ cụt: khách không
    biết code thì không biết trả lời gì, và họ đứng lại đúng ở đó.
    """
    return ly_do + "\n\nMấy việc này tôi làm được ngay — chép nguyên một dòng rồi gửi:\n" + \
        "\n".join(_goi_y_lam_duoc(tabs))


def _con_lam_duoc(tabs: Optional[Mapping[str, str]] = None,
                  tru: Iterable[str] = ()) -> str:
    ten = _tab_lam_vi_du(tabs, tru)
    khac = ten[1] if len(ten) > 1 else ten[0]
    return ("Cần sửa nữa thì cứ nói tiếp:\n"
            "• “ẩn tab {0}” — giấu bớt tab bạn không dùng\n"
            "• “đổi tên tab {1} thành Tab của tôi” — đổi tiếp tab khác\n"
            "• “làm content” — tôi quay lại dựng tool cho bạn").format(ten[0], khac)


def _khong_ro_tab(thay_doi: ThayDoiGiaoDien,
                  tabs: Optional[Mapping[str, str]]) -> str:
    if not thay_doi.key:
        return _cau_khong_lam_duoc(
            "Tôi không thấy tab nào tên “{0}”. Các tab đang có: {1}.".format(
                thay_doi.old_label, ", ".join(ten_tab_dang_co(tabs))), tabs)
    return _cau_khong_lam_duoc(
        "Tên mới cho tab “{0}” chưa dùng được — cần từ 1 đến 40 ký tự.".format(
            thay_doi.old_label), tabs)


def _moi_sua_tab(thay_doi: ThayDoiGiaoDien,
                 tabs: Optional[Mapping[str, str]]) -> str:
    """Nói rõ “đó” là tab nào, rồi bày sẵn các nước đi tiếp cho đúng tab ấy."""
    ten = thay_doi.new_label or thay_doi.old_label
    dong = ["Bạn đang nói tới tab “{0}”. Tab đó tôi sửa được ngay — nói một "
            "trong mấy câu này:".format(ten),
            "• “đổi tên tab {0} thành Tài khoản của tôi” — đổi lại tên".format(ten)]
    if thay_doi.key != "agent":
        dong.append("• “ẩn tab {0}” — giấu khỏi thanh bên".format(ten))
    dong.append("• “hiện tab {0}” — bày lại tab đã ẩn".format(
        _tab_lam_vi_du(tabs, (thay_doi.key,))[0]))
    return "\n".join(dong)


def _dich_xa_nhat(text: str, ids: set) -> Optional[str]:
    """Kết quả XA NHẤT trong dây chuyền mà khách vừa nhắc tới.

    Lấy xa nhất chứ không lấy cái đầu tiên: *“thêm bước tạo ảnh và video”* nghĩa
    là khách muốn đi tới video, và ảnh là bước nằm trên đường đó. Bộ hiểu cũ gặp
    hai tên một lúc thì trả về `None` và bỏ cuộc — đúng câu khách hay nói nhất.
    """
    xa = None
    for tool_id, tu_khoa in _KET_QUA.items():
        if tool_id not in ids:
            continue
        if any(_khop_tron_tu(text, tu) for tu in tu_khoa):
            if xa is None or _BAC.get(tool_id, -1) > _BAC.get(xa, -1):
                xa = tool_id
    return xa


def _khop_tron_tu(text: str, tu_khoa: str) -> bool:
    """Khớp theo **ranh giới từ**, không khớp chuỗi con.

    Bỏ dấu xong thì “ảnh” và “cảnh” đều còn `anh`/`canh`, nên tìm chuỗi con làm
    câu *“chia cảnh”* bị hiểu thành *“tạo ảnh”* — khách xin bảng cảnh mà nhận về
    dây chuyền dài hơn, tốn thêm tiền ảnh. Cùng cái bẫy với “nhanh”, “thành”,
    “danh sách”.

    >>> _khop_tron_tu("chia canh", "anh")
    False
    >>> _khop_tron_tu("tao anh minh hoa", "anh")
    True
    >>> _khop_tron_tu("tao giong doc", "giong doc")
    True
    """
    return re.search(r"(?<![0-9a-z])" + re.escape(_plain(tu_khoa)) + r"(?![0-9a-z])",
                     text) is not None


def _dung_toi_dich(dich: str, ids: set, state: Dict[str, Any]) -> AgentPlan:
    """Dựng dây chuyền ngắn nhất **thật sự chạy được** để ra kết quả `dich`.

    Kèm đủ bước tiên quyết, vì cổng vào của mỗi bước lấy đúng cổng ra của bước
    liền trước — thiếu một mắt là workflow không hợp lệ và khách nhận lỗi thay
    vì nhận sản phẩm.
    """
    can = [tool_id for tool_id in FULL_PIPELINE[: _BAC[dich] + 1] if tool_id in ids]
    ten = _TEN_THEO_DICH.get(dich, "Tool của tôi")
    proposed = _new_workflow(can, ten)
    proposed["workflow_id"] = _personal_tool_id(state)
    state.update({"personal_tool_id": proposed["workflow_id"], "personal_tool_name": ten,
                  "onboarding_complete": True, "onboarding_stage": "active"})
    if len(can) == 1:
        loi = "Tôi dựng cho bạn tool “{0}”. Bấm Áp dụng rồi chạy thử.".format(ten)
    else:
        truoc = " → ".join(_TEN_THEO_DICH.get(t, t) for t in can[:-1])
        loi = ("Tôi dựng cho bạn tool “{0}” gồm {1} bước: {2} → {0}.\n\n"
               "Các bước đầu là bắt buộc — bước sau cần đúng thứ bước trước làm ra. "
               "Bấm Áp dụng rồi chạy thử.").format(ten, len(can), truoc)
    return AgentPlan(loi, (AgentAction("replace_workflow", {"workflow": proposed}),),
                     proposed, state)


def _moi_chon_dich(tabs: Optional[Mapping[str, str]] = None) -> str:
    """Câu hỏi lại khi chưa hiểu — luôn kèm lựa chọn cụ thể, không hỏi trống.

    “Bạn cứ nói thẳng kết quả bạn muốn” là câu hỏi trống: khách không biết code
    thì không biết tool này làm được gì để mà nói.
    """
    ten = ten_tab_dang_co(tabs)
    return ("Bạn muốn nhận thứ gì trước? Cứ gõ một dòng, ví dụ:\n\n"
            "• “nghiên cứu đối thủ” → báo cáo xem ngách còn cửa không\n"
            "• “làm content” → một kịch bản hoàn chỉnh\n"
            "• “tạo giọng đọc” → file MP3 dùng được ngay\n"
            "• “tạo ảnh” hoặc “làm video” → tôi dựng đủ các bước cần trước đó\n"
            "• “đổi tên tab {0} thành Tài khoản” → tôi sửa luôn giao diện cho bạn\n\n"
            "Bạn cũng có thể tả bằng lời thường, ví dụ “tao muốn có video kể "
            "chuyện tâm lý”.").format(ten[-1] if ten else NHAN_TAB_MAC_DINH["wallet"])


def _plain(value: str) -> str:
    value = value.replace("đ", "d").replace("Đ", "D")
    value = "".join(c for c in unicodedata.normalize("NFD", value)
                    if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", value.lower()).strip()


def _has(text: str, *needles: str) -> bool:
    return any(_plain(needle) in text for needle in needles)


def _catalog_ids(catalog: Any) -> set:
    if isinstance(catalog, Mapping):
        return set(str(key) for key in catalog)
    result = set()
    for item in catalog or ():
        if isinstance(item, Mapping):
            tool_id = item.get("tool_id")
        else:
            tool_id = getattr(item, "tool_id", None)
        if tool_id:
            result.add(str(tool_id))
    return result


def _assistant_name(original: str, text: str) -> Optional[str]:
    if not _has(text, "dat ten", "goi may la", "ten tro ly", "tro ly ten"):
        return None
    patterns = (
        r"(?:đặt tên(?: trợ lý)?(?: là)?|gọi mày là|trợ lý tên|tên trợ lý(?: là)?)\s+['\"]?([^'\".,!?]+)",
        r"(?:dat ten(?: tro ly)?(?: la)?|goi may la|tro ly ten|ten tro ly(?: la)?)\s+([^.,!?]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, original, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if 1 <= len(name) <= 40:
                return name
    return None


def _simple_name(original: str) -> Optional[str]:
    name = original.strip().strip("'\"")
    plain = _plain(name)
    if _has(plain, "pipeline", "quy trinh", "youtube", "tao tool", "lam video", "nghien cuu"):
        return None
    if 1 <= len(name) <= 40 and len(name.split()) <= 5 and "\n" not in name and not re.search(r"[\\/:*?<>|]", name):
        return name
    return None


def _onboarding_step(original: str, text: str, ids: set,
                     state: Dict[str, Any]) -> Optional[AgentPlan]:
    stage = str(state.get("onboarding_stage") or "")
    if not stage:
        return None
    if stage == "name":
        return AgentPlan("Bạn muốn đặt tên cho trợ lý là gì?", (), None, state)
    if stage == "goal":
        choice = text.strip()[:1]
        if choice == "1" or _has(text, "nghien cuu", "doi thu", "research"):
            tools = RESEARCH_PIPELINE; name = "Nghiên cứu đối thủ"
        elif choice == "2" or _has(text, "content", "noi dung", "kich ban"):
            tools = SHORT_PIPELINE; name = "Làm content"
        elif choice == "3" or _has(text, "voice", "giong", "mp3"):
            tools = STARTER_PIPELINE; name = "Tạo giọng đọc"
        elif _has(text, "day du", "full", "tron quy trinh", "a-z", "tu dau den cuoi"):
            tools = FULL_PIPELINE; name = "Sản xuất YouTube đầy đủ"
        else:
            state["channel_goal"] = original[:500]
            return AgentPlan("Tôi hiểu ý tưởng chính rồi. Kết quả đầu tiên bạn muốn cầm trên tay là gì? Ví dụ: một báo cáo đối thủ, một kịch bản, một file giọng đọc, hoặc một thay đổi cụ thể trên giao diện.", (), None, state)
        available = [tool_id for tool_id in tools if tool_id in ids]
        tool_id = _personal_tool_id(state)
        proposed = _new_workflow(available, name)
        proposed["workflow_id"] = tool_id
        state.update({"channel_goal": original[:500], "personal_tool_id": tool_id,
                      "personal_tool_name": name, "personal_tool_revision": 1,
                      "onboarding_stage": "complete", "onboarding_complete": True})
        return AgentPlan(
            "Tôi đã dựng bản đầu tiên “{0}”. Hãy xem bên phải; dùng thử riêng phần này, chưa cần nối cả dây chuyền.".format(name),
            (AgentAction("replace_workflow", {"workflow": proposed}),), proposed, state)
    if stage == "format":
        if _has(text, "short", "video doc", "9:16", "tiktok"):
            video_format = "short"
        elif _has(text, "ca hai", "both", "hon hop"):
            video_format = "both"
        elif _has(text, "dai", "video ngang", "16:9", "long"):
            video_format = "long"
        else:
            return AgentPlan("Bạn chọn giúp tôi một trong ba kiểu: video dài, Shorts dọc, hoặc cả hai.", (), None, state)
        state.update({"video_format": video_format, "onboarding_stage": "current_process"})
        return AgentPlan("Hiện tại bạn đang làm video theo những bước nào? Có thể trả lời rất ngắn, ví dụ: “tự viết content, thuê voice, edit thủ công”.", (), None, state)
    if stage == "current_process":
        state["current_process"] = original[:1000]
        state["onboarding_stage"] = "scope"
        return AgentPlan("Chọn một khung khởi đầu nhỏ; mỗi khung có một kết quả dễ kiểm tra:\n"
                         "1. Nghiên cứu đối thủ → nhận báo cáo nghiên cứu\n"
                         "2. Làm content → nhận kịch bản hoàn chỉnh\n"
                         "3. Làm giọng đọc → nhận file MP3\n"
                         "Khi phần này đạt, bạn chỉ cần nói “nối thêm bước tiếp theo”.\n"
                         "Bạn có thể thêm điều muốn tự duyệt, ví dụ: “3, tôi duyệt content”.", (), None, state)
    if stage == "scope":
        choice = text.strip()[:1]
        if choice == "1" or _has(text, "chi nghien cuu", "research only"):
            tools = RESEARCH_PIPELINE; scope = "research"
        elif choice == "2" or (_has(text, "content") and not _has(text, "voice", "video", "tron", "het")):
            tools = SHORT_PIPELINE; scope = "content"
        elif choice == "3" or (_has(text, "voice", "giong") and not _has(text, "video", "edit", "tron", "het")):
            tools = STARTER_PIPELINE; scope = "voice"
        elif choice == "4" or _has(text, "video", "edit", "tron", "het", "full"):
            tools = FULL_PIPELINE; scope = "full"
        else:
            return AgentPlan("Hãy chọn 1, 2 hoặc 3. Nếu bạn mới bắt đầu, chọn 1 để chạy quen rồi nối thêm từng bước. Nếu thật sự muốn làm hết ngay, hãy nói rõ “trọn quy trình”.", (), None, state)
        criteria = {"research": "Có báo cáo đối thủ đủ rõ để quyết định ngách",
                    "content": "Có kịch bản hoàn chỉnh đúng chủ đề và giọng kênh",
                    "voice": "Có file MP3 nghe tự nhiên và dùng được",
                    "full": "Có video hoàn chỉnh xem được"}
        state.update({"automation_scope": scope, "review_preferences": original[:700],
                      "success_criterion": criteria[scope],
                      "onboarding_stage": "constraints"})
        return AgentPlan("Khi chọn cách làm, bạn ưu tiên chất lượng, tốc độ hay tiết kiệm chi phí? Nếu có ngân sách mong muốn cho mỗi video, hãy nói luôn; không biết thì trả lời “dùng mức hợp lý”.", (), None, state)
    if stage == "constraints":
        state.update({"quality_budget_priority": original[:500], "onboarding_stage": "confirm"})
        return AgentPlan(_profile_summary(state) +
                         "\n\nTôi hiểu như vậy đã đúng chưa? Trả lời “đúng, tạo tool của tôi” để tôi dựng bản thiết kế; nếu chưa đúng, hãy nói phần cần sửa.",
                         (), None, state)
    if stage == "confirm":
        if not _has(text, "dung", "chinh xac", "ok", "tao tool", "dong y", "yes"):
            if _profile_correction(original, text, state):
                return AgentPlan(_profile_summary(state) +
                                 "\n\nTôi đã sửa hồ sơ. Nếu đúng, hãy trả lời “đúng, tạo tool của tôi”.",
                                 (), None, state)
            return AgentPlan("Tôi chưa tạo vội. Hãy nói rõ như “đổi sang video dài”, “ngân sách 100 nghìn”, hoặc trả lời “đúng, tạo tool của tôi” khi bản tóm tắt đã chính xác.", (), None, state)
        scope = str(state.get("automation_scope") or "full")
        tools = {"research": RESEARCH_PIPELINE, "content": SHORT_PIPELINE,
                 "voice": STARTER_PIPELINE}.get(scope, FULL_PIPELINE)
        available = [tool_id for tool_id in tools if tool_id in ids]
        tool_id = _personal_tool_id(state)
        proposed = _new_workflow(available, "Tool YouTube của tôi")
        proposed["workflow_id"] = tool_id
        _apply_profile(proposed, state)
        state.update({"personal_tool_id": tool_id, "personal_tool_name": proposed["name"],
                      "personal_tool_revision": 1, "onboarding_stage": "complete",
                      "onboarding_complete": True})
        reply = ("Đã dựng “{0}” phiên bản 1 gồm {1} bước theo đúng hồ sơ của bạn. "
                 "Hãy xem bản thiết kế bên phải; mọi thay đổi sau này chỉ cần nói với tôi.").format(
                     proposed["name"], len(available))
        return AgentPlan(reply, (AgentAction("replace_workflow", {"workflow": proposed}),), proposed, state)
    return None


def _post_run_step(original: str, text: str, workflow: Optional[Mapping[str, Any]],
                   state: Dict[str, Any]) -> Optional[AgentPlan]:
    stage = str(state.get("onboarding_stage") or "")
    if stage == "review_result":
        if _has(text, "dat", "tot", "on", "dung", "hai long", "ok") and not _has(
                text, "chua", "khong", "sai", "loi"):
            state.update({"onboarding_stage": "active", "last_feedback": "satisfied"})
            return AgentPlan("Tốt, tôi đã ghi nhận đây là bản đang dùng. Khi muốn tối ưu, bạn chỉ cần nói kết quả nào cần tốt hơn.", (), None, state)
        state.update({"onboarding_stage": "feedback_detail", "last_feedback": original[:1000]})
        return AgentPlan("Tôi sẽ sửa thành phiên bản mới, chưa đụng vào bản đang chạy. Điều gì chưa đúng nhất: content, giọng đọc, hình ảnh, chuyển động hay bản edit cuối?", (), None, state)
    if stage == "feedback_detail":
        state["last_feedback_detail"] = original[:1000]
        configured = _configuration_change(text, original, workflow)
        if configured is None:
            return AgentPlan("Tôi đã ghi nhận phản hồi. Hãy nói thay đổi cụ thể, ví dụ “đổi video dọc 9:16”, “dùng Seedance” hoặc “đổi giọng đọc vi_female_01”.", (), None, state)
        proposed, changes = configured
        revision = int(state.get("personal_tool_revision") or 1) + 1
        state.update({"personal_tool_revision": revision, "onboarding_stage": "revision_review"})
        return AgentPlan("Đã tạo bản sửa phiên bản {0}: {1}. Bản đang chạy chưa bị thay đổi; hãy duyệt đề xuất bên phải.".format(
            revision, ", ".join(changes)),
            (AgentAction("configure_workflow", {"changes": changes}),), proposed, state)
    if stage == "troubleshoot":
        state["last_feedback_detail"] = original[:1000]
        return AgentPlan("Tôi đã ghi nhận. Hãy bấm “Kiểm tra máy”; sau khi sửa thành phần được báo thiếu, bấm Chạy để Studio tiếp tục từ checkpoint thay vì làm lại bước đã xong.", (), None, state)
    return None


def _apply_profile(workflow: Dict[str, Any], state: Mapping[str, Any]) -> None:
    video_format = state.get("video_format")
    aspect = "9:16" if video_format == "short" else "16:9"
    for node in workflow.get("nodes", []):
        if node.get("tool_id") in ("image.shopapi", "video.shopapi"):
            node.setdefault("config", {})["aspect_ratio"] = aspect
        if node.get("tool_id") in ("content.remake", "transcribe.local") and state.get("language"):
            node.setdefault("config", {})["language"] = state["language"]


def _personal_tool_id(state: Mapping[str, Any]) -> str:
    seed = "|".join(str(state.get(key) or "") for key in (
        "channel_goal", "video_format", "automation_scope", "current_process"))
    return "personal-youtube-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]


def _profile_summary(state: Mapping[str, Any]) -> str:
    formats = {"short": "Shorts dọc", "long": "video dài ngang", "both": "cả video dài và Shorts"}
    scopes = {"research": "chỉ nghiên cứu", "content": "nghiên cứu và content",
              "voice": "đến giọng đọc", "full": "trọn quy trình đến video hoàn chỉnh"}
    return ("TÔI HIỂU TOOL CỦA BẠN NHƯ SAU:\n"
            "• Mục tiêu kênh: {0}\n"
            "• Định dạng: {1}\n"
            "• Cách bạn đang làm: {2}\n"
            "• Tự động hóa/duyệt tay: {3}\n"
            "• Ưu tiên và ngân sách: {4}\n"
            "• Khi nào coi là đạt: {5}").format(
                state.get("channel_goal") or "chưa rõ",
                formats.get(state.get("video_format"), str(state.get("video_format") or "chưa rõ")),
                state.get("current_process") or "chưa rõ",
                state.get("review_preferences") or scopes.get(state.get("automation_scope"), "chưa rõ"),
                state.get("quality_budget_priority") or "mức hợp lý",
                state.get("success_criterion") or "có sản phẩm dùng được")


def _profile_correction(original: str, text: str, state: Dict[str, Any]) -> bool:
    changed = False
    if _has(text, "short", "video doc", "9:16"):
        state["video_format"] = "short"; changed = True
    elif _has(text, "ca hai", "both"):
        state["video_format"] = "both"; changed = True
    elif _has(text, "video dai", "video ngang", "16:9"):
        state["video_format"] = "long"; changed = True
    if _has(text, "ngan sach", "chi phi", "uu tien", "chat luong", "tiet kiem", "toc do"):
        state["quality_budget_priority"] = original[:500]; changed = True
    return changed


def _operation(text: str) -> Optional[str]:
    if _has(text, "them", "chen", "add"):
        return "add"
    if _has(text, "bo", "xoa", "remove"):
        return "remove"
    if _has(text, "tat", "disable"):
        return "disable"
    if _has(text, "bat", "enable", "kich hoat"):
        return "enable"
    return None


def _resolve_alias(text: str, ids: set) -> Optional[str]:
    # ID day du la tin hieu manh nhat.
    for tool_id in sorted(ids, key=len, reverse=True):
        if _plain(tool_id) in text:
            return tool_id
    matches = []
    for tool_id, aliases in ALIASES.items():
        if tool_id in ids and any(_plain(alias) in text for alias in aliases):
            matches.append(tool_id)
    return matches[0] if len(matches) == 1 else None


def _new_workflow(tool_ids: Sequence[str], name: str) -> Dict[str, Any]:
    nodes = [{"id": "step-{0}".format(i + 1), "tool_id": tool_id,
              "inputs": ({"query": "__ASK_USER__"} if tool_id == "research.youtube" else {}),
              "config": {"enabled": True}}
             for i, tool_id in enumerate(tool_ids)]
    by_tool = {node["tool_id"]: node for node in nodes}
    edges = []
    for source, target in zip(tool_ids, tool_ids[1:]):
        ports = MAIN_PORTS.get((source, target))
        if ports:
            edges.append(_edge(by_tool[source]["id"], ports[0], by_tool[target]["id"], ports[1]))
    # Cac input phu giu du lieu giau hon va cho editor dung lai audio/SRT.
    for source, source_port, target, target_port in (
        ("content.remake", "content_package", "prompt.workbook", "context"),
        ("prompt.workbook", "scenes", "video.shopapi", "scenes"),
        ("voice.shopapi", "audio", "edit.ffmpeg", "audio"),
        ("transcribe.local", "subtitles", "edit.ffmpeg", "subtitles"),
    ):
        if source in by_tool and target in by_tool:
            edges.append(_edge(by_tool[source]["id"], source_port, by_tool[target]["id"], target_port))
    return {"workflow_id": "youtube-default", "version": "1", "name": name,
            "nodes": nodes, "edges": edges}


def _copy_workflow(workflow: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    workflow = workflow or {}
    return {
        "workflow_id": workflow.get("workflow_id", "workflow-moi"),
        "version": workflow.get("version", "1"),
        "name": workflow.get("name", "Workflow mới"),
        "nodes": copy.deepcopy(list(workflow.get("nodes", []))),
        "edges": copy.deepcopy(list(workflow.get("edges", []))),
    }


def _configuration_change(text: str, original: str,
                          workflow: Optional[Mapping[str, Any]]) -> Optional[Tuple[Dict[str, Any], List[str]]]:
    if not workflow:
        return None
    proposed = _copy_workflow(workflow)
    changes: List[str] = []

    def set_for(tool_id: str, key: str, value: Any) -> None:
        for node in proposed["nodes"]:
            if node.get("tool_id") == tool_id:
                node.setdefault("config", {})[key] = value
                changes.append("{0}.{1} = {2}".format(tool_id, key, value))

    ty_le = _ty_le_khung(text)
    if ty_le:
        set_for("image.shopapi", "aspect_ratio", ty_le)
        set_for("video.shopapi", "aspect_ratio", ty_le)
    if _has(text, "seedance"):
        set_for("video.shopapi", "engine", "seedance")
        set_for("video.shopapi", "duration", 10)
    elif _has(text, "veo3", "veo 3") and _has(text, "engine", "video", "dung"):
        set_for("video.shopapi", "engine", "veo3")
        set_for("video.shopapi", "duration", 8)
    whisper = re.search(r"(?:whisper|srt|phu de).*?\b(tiny|base|small|medium|large-v3)\b", text)
    if whisper and whisper.group(1) == "small":
        set_for("transcribe.local", "model", whisper.group(1))
    maximum = re.search(r"(?:toi da|max(?:imum)?)[^0-9]{0,12}(\d{1,3})[^\n]*(?:video|clip)", text)
    if maximum:
        set_for("research.youtube", "max_videos", int(maximum.group(1)))
    giong = _ma_giong(text, original)
    if giong:
        set_for("voice.shopapi", "voice_id", giong)
    language = re.search(r"(?:ngon ngu|language)\s+(?:la\s+)?([a-z]{2,5})\b", text)
    if language:
        set_for("content.remake", "language", language.group(1))
        set_for("transcribe.local", "language", language.group(1))
    return (proposed, changes) if changes else None


#: Từ khách dùng để nói về khung hình, thay vì gõ `9:16`.
_TU_TY_LE = (
    (("doc", "dung", "shorts", "short", "tiktok", "reels"), "9:16"),
    (("ngang", "landscape"), "16:9"),
    (("vuong", "square"), "1:1"),
)

#: Ngữ cảnh bắt buộc để một từ hướng được hiểu là khung hình.
#:
#: Không có nó thì *"đổi giọng đọc sang nam"* biến thành đổi khung hình dọc: bỏ
#: dấu xong "đọc" và "dọc" giống hệt nhau.
_NGU_CANH_TY_LE = ("video", "anh", "hinh", "khung", "ty le", "clip", "shorts", "tiktok", "reels")


def _ty_le_khung(text: str) -> Optional[str]:
    """Tỉ lệ khung khách muốn, hiểu cả khi họ không gõ con số.

    >>> _ty_le_khung("doi sang video doc")
    '9:16'
    >>> _ty_le_khung("lam anh vuong")
    '1:1'
    >>> _ty_le_khung("doi giong doc sang nam") is None
    True
    """
    so = re.search(r"(?<!\d)(16\s*:\s*9|9\s*:\s*16|1\s*:\s*1)(?!\d)", text)
    if so:
        return so.group(1).replace(" ", "")
    if not any(_khop_tron_tu(text, tu) for tu in _NGU_CANH_TY_LE):
        return None
    for tu_khoa, gia_tri in _TU_TY_LE:
        if any(_khop_tron_tu(text, tu) for tu in tu_khoa):
            return gia_tri
    return None


#: Giọng theo giới tính, dùng đúng mã trong danh mục của máy chủ.
_GIONG_THEO_GIOI = {"nam": "vi_male_01", "nu": "vi_female_01",
                    "trai": "vi_male_01", "gai": "vi_female_01"}


def _ma_giong(text: str, original: str) -> Optional[str]:
    """Mã giọng khách muốn — chỉ nhận mã THẬT, không vớ đại từ kế bên.

    Bản cũ bắt “chữ liền sau từ giọng”, nên *"đổi giọng đọc sang nam"* đặt
    `voice_id = "sang"`. Máy chủ nhận mã lạ là hỏng job, mà khách không tài nào
    đoán ra vì sao — im lặng không đổi gì còn hơn đổi thành rác.

    >>> _ma_giong("doi giong doc sang nam", "đổi giọng đọc sang nam")
    'vi_male_01'
    >>> _ma_giong("dung giong vi_female_03", "dùng giọng vi_female_03")
    'vi_female_03'
    >>> _ma_giong("doi giong doc di", "đổi giọng đọc đi") is None
    True
    """
    ro_rang = re.search(r"\b(vi_(?:male|female)_\d{2})\b", text)
    if ro_rang:
        return ro_rang.group(1)
    # Mã ElevenLabs thật: đúng 20 ký tự chữ và số.
    ngoai = re.search(r"\b([A-Za-z0-9]{20})\b", original)
    if ngoai:
        return ngoai.group(1)
    if not _khop_tron_tu(text, "giong") and not _has(text, "long tieng", "thuyet minh"):
        return None
    for tu, ma in _GIONG_THEO_GIOI.items():
        if _khop_tron_tu(text, tu):
            return ma
    return None


def _change_tool(workflow: Dict[str, Any], operation: str, tool_id: str) -> bool:
    nodes = workflow["nodes"]
    found = next((node for node in nodes if node.get("tool_id") == tool_id), None)
    if operation == "add":
        if found:
            return False
        # Một node media đứng riêng thường không chạy được. Thêm toàn bộ bước
        # tiên quyết còn thiếu rồi nối lại các cổng canonical.
        required = FULL_PIPELINE[:FULL_PIPELINE.index(tool_id) + 1] if tool_id in FULL_PIPELINE else (tool_id,)
        next_number = max([_step_number(n.get("id", "")) for n in nodes] + [0]) + 1
        for required_id in required:
            if any(node.get("tool_id") == required_id for node in nodes):
                continue
            nodes.append({"id": "step-{0}".format(next_number), "tool_id": required_id,
                          "inputs": ({"query": "__ASK_USER__"} if required_id == "research.youtube" else {}),
                          "config": {"enabled": True}})
            next_number += 1
        _sort_and_rewire(workflow)
        return True
    if not found:
        return False
    if operation == "remove":
        # Bỏ luôn các bước phụ thuộc ở phía sau. Giữ chúng lại sẽ tạo một DAG
        # nhìn có vẻ đẹp nhưng thiếu input bắt buộc và không thể áp dụng/chạy.
        remove_ids = {found.get("id")}
        changed = True
        while changed:
            changed = False
            for edge in workflow.get("edges", []):
                if edge.get("source_node") in remove_ids and edge.get("target_node") not in remove_ids:
                    remove_ids.add(edge.get("target_node")); changed = True
        workflow["nodes"] = [node for node in nodes if node.get("id") not in remove_ids]
        _sort_and_rewire(workflow)
        return True
    enabled = operation == "enable"
    config = found.setdefault("config", {})
    if bool(config.get("enabled", True)) == enabled:
        return False
    config["enabled"] = enabled
    return True


def _sort_and_rewire(workflow: Dict[str, Any]) -> None:
    rank = {tool_id: index for index, tool_id in enumerate(FULL_PIPELINE)}
    workflow["nodes"].sort(key=lambda node: (rank.get(node.get("tool_id"), len(rank)),
                                              str(node.get("id", ""))))
    by_tool = {node.get("tool_id"): node for node in workflow["nodes"]}
    edges = []
    for (source, target), (source_port, target_port) in MAIN_PORTS.items():
        if source in by_tool and target in by_tool:
            edges.append(_edge(by_tool[source]["id"], source_port, by_tool[target]["id"], target_port))
    for source, source_port, target, target_port in (
        ("content.remake", "content_package", "prompt.workbook", "context"),
        ("prompt.workbook", "scenes", "video.shopapi", "scenes"),
        ("voice.shopapi", "audio", "edit.ffmpeg", "audio"),
        ("transcribe.local", "subtitles", "edit.ffmpeg", "subtitles"),
    ):
        if source in by_tool and target in by_tool:
            edges.append(_edge(by_tool[source]["id"], source_port, by_tool[target]["id"], target_port))
    workflow["edges"] = edges


def _step_number(node_id: str) -> int:
    match = re.fullmatch(r"step-(\d+)", str(node_id))
    return int(match.group(1)) if match else 0


def _no_change_reply(operation: str, tool_id: str,
                     tabs: Optional[Mapping[str, str]] = None) -> str:
    """Không có gì để đổi — nói bằng tên khách hiểu, và vẫn mở đường đi tiếp.

    Câu cũ đọc là *“voice.shopapi đã có trong workflow.”*: vừa là mã kỹ thuật
    khách không biết, vừa hết chuyện ngay tại đó.
    """
    ten = _TEN_THEO_DICH.get(tool_id, tool_id)
    if operation == "add":
        ly_do = "“{0}” đã có sẵn trong Tool của bạn rồi.".format(ten)
    elif operation == "remove":
        ly_do = "“{0}” vốn không có trong Tool của bạn nên không có gì để bỏ.".format(ten)
    else:
        ly_do = ("“{0}” đang đúng trạng thái bạn muốn, hoặc chưa có trong Tool "
                 "của bạn.".format(ten))
    return _cau_khong_lam_duoc(ly_do, tabs)


def _edge(source_node: str, source_port: str, target_node: str, target_port: str) -> Dict[str, str]:
    return {"source_node": source_node, "source_port": source_port,
            "target_node": target_node, "target_port": target_port}
