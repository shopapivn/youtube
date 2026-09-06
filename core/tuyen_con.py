"""**Tệp khán giả → tuyến con** — nhận diện bằng từ khoá, không cần AI.

Chủ dự án, 06/09/2026: *"các tuyến mày đang phân không giống kiểu tao làm theo tệp khán giả… lúc trước
tao phân có 3: NGƯỜI SỐNG LỆCH NHỊP SỐ ĐÔNG · NGƯỜI BỊ ĐÁNH GIÁ THẤP HƠN NĂNG LỰC THẬT · NGƯỜI TÒ MÒ XEM
MÌNH LÀ KIỂU NGƯỜI NÀO… trong tệp lệch nhịp có các tuyến con: người thích ở một mình, người không dùng
mạng xã hội, người không thích thể thao…"*

Hai tầng:
  * **Tệp** (mã trong `nghien-cuu/tuyen.csv`, cột "Tuyến / Kênh" của sổ content) — AI + luật cứng gán.
  * **Chủ đề** (tuyến con, cột "Chủ đề") — nhận diện bằng từ khoá ở đây. Mỗi chủ đề thuộc đúng một
    tệp, nên nhận ra chủ đề là suy được tệp: dòng nào máy nhận ra thì điền cả hai (khi ô tệp trống),
    AI chỉ còn phải xem phần máy không nhận ra. Phân loại vì thế ổn định, lặp lại được, và đọc được
    lý do ("vì tiêu đề có SNS").

Thứ tự ưu tiên khi một tiêu đề dính nhiều nhóm: từ loại trừ (雑学…) → mốc tuổi (tệp trung niên) →
chủ đề của tệp lệch nhịp → cảnh giác → đánh giá thấp → tò mò. Đúng PHÂN XỬ trong tuyen.csv: "cùng nói
phòng bừa: xin được phép bừa → lệch nhịp; xin cách dọn / bừa vì tuổi → trung niên".
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from .phan_tuyen import DAU_MOC_TUOI, MA_LECH_NHIP, MA_TRUNG_NIEN, _dinh_tu_loai_tru

__all__ = ["CHU_DE", "MA_THAP", "MA_TO_MO", "MA_CANH_GIAC", "nhan_dien", "dien_chu_de", "ten_chu_de"]

MA_THAP = "nguoi-bi-danh-gia-thap-hon-nang-luc-that"
MA_TO_MO = "nguoi-to-mo-xem-minh-la-kieu-nguoi-nao"
MA_CANH_GIAC = "nguoi-canh-giac-ke-doc-hai"

#: (mã chủ đề, tên hiện, regex tiếng Nhật) — theo thứ tự ưu tiên trong từng tệp.
CHU_DE: Dict[str, List[Tuple[str, str, "re.Pattern[str]"]]] = {
    MA_LECH_NHIP: [
        ("khong-sns", "không dùng mạng xã hội", re.compile("SNS|インスタ|投稿しない|投稿をしない|投稿もしない|既読")),
        ("khong-the-thao", "không hứng thú thể thao / trào lưu", re.compile(
            "スポーツ|ワールドカップ|野球に興味|流行に|ブランドに興味|熱狂できない|夢中になれない|興味がない人|興味が持てない|興味のない人")),
        ("o-nha", "thích ở nhà, không ra ngoài", re.compile(
            "家にいたい|家から出|外に出ない|出かけない|家が好き|家にいる|家を愛|休日に予定|予定を入れない|遠出")),
        ("it-ban", "ít bạn, giữ khoảng cách", re.compile(
            "友達が少な|友人が少な|友達がいな|人付き合い|人間関係から距離|疎遠|群れない|群れる|連絡を絶|縁を切|付き合わない|合わせない")),
        ("noi-mot-minh", "hay nói một mình", re.compile("独り言|ひとりごと")),
        ("dam-dong-met", "mệt khi ở đám đông", re.compile("人混み|飲み会|誰といても|大勢|集まり|雑談が苦手|複数人|会話が苦手|人といると疲れ")),
        ("phong-bua", "phòng bừa (xin được phép)", re.compile("部屋が汚|散らか")),
        ("mot-minh", "thích ở một mình", re.compile(
            "一人が好き|1人が好き|ひとりが好き|一人の時間|1人の時間|ひとり時間|一人時間|一人でいる|一人でいても|一人で|1人で|ひとりで|孤独を好|孤独を選|孤独が好|ソロ|ぼっち|静かな人|口数が少な|無口|話さない人|内向")),
    ],
    MA_CANH_GIAC: [
        ("ke-doc-hai", "nhận diện người độc hại", re.compile(
            "性格が悪い|ずるい|テイカー|嫉妬|攻撃してくる|無礼|話が通じない|非を認めない|関わってはいけない|見下す|マウント|操る|支配|裏切|毒親|危険な人|やばい人|悪口|敵が多い|離れるべき人|距離を置くべき")),
    ],
    MA_THAP: [
        ("hoc-van-iq", "học vấn, IQ không đo được", re.compile("学歴|IQ|知能|高知能|頭がいい人|頭のいい人|頭の良い人|賢い人|地頭|天才")),
        ("no-luc", "cố gắng không được đền đáp", re.compile("努力|報われ|評価され|認められ|軽く扱われ|尊重され|大器晩成|遅咲き|突然成長|花開く")),
        ("tai-nang-an", "tài năng bị ẩn", re.compile("隠された才能|隠れた才能|才能|能力が高い|ずば抜け|優秀|センス")),
    ],
    MA_TO_MO: [
        ("dong-vat", "thói quen vô hại: thú cưng", re.compile("猫|犬|動物|ペット")),
        ("thoi-quen-vat", "thói quen vô hại khác", re.compile(
            "早起き|朝型|夜型|財布|同じ映画|会釈|コーヒー|紅茶|読書が好き|散歩|手書き|左利き|血液型|植物|園芸|庭いじり|バイク|登山|道を聞かれ|自分で直す|料理が好き|お菓子作り|音楽が好き|文字|字が|ゲームが好き")),
    ],
}

#: Tệp trung niên: chủ đề theo mốc tuổi / dọn nhà (luật cứng đã đưa mốc tuổi về tệp này).
CHU_DE_TRUNG_NIEN: List[Tuple[str, str, "re.Pattern[str]"]] = [
    ("don-nha", "dọn nhà, bỏ bớt đồ", re.compile("片付け|捨て|断捨離|掃除|物が多い|ミニマ|もったいな|整理|家事")),
    ("tri-nho", "trí nhớ, não già", re.compile("物忘れ|認知症|脳の老化|記憶力|海馬|脳年齢")),
    ("tuoi-tac", "tuổi tác là nhân vật chính", re.compile("|".join(re.escape(m) for m in DAU_MOC_TUOI if m) + "|人生後半|昭和|1970|1974|老い|老け")),
]

_TU_KHOA_TRUNG_NIEN = re.compile("片付け|捨て|断捨離|掃除|物が多い|ミニマ|もったいな|家事卒業|物忘れ|認知症|脳の老化|海馬|人生後半|昭和|1970|1974|老い|老け")


def ten_chu_de(ma: str) -> str:
    for ds in list(CHU_DE.values()) + [CHU_DE_TRUNG_NIEN]:
        for m, ten, _rx in ds:
            if m == ma:
                return ten
    return ma


def nhan_dien(tieu_de: str, kenh_nguon: str = "") -> Optional[Tuple[str, str]]:
    """`(mã tệp, mã chủ đề)` cho một tiêu đề, hoặc `None` khi không nhận ra (để AI / để trống)."""
    td = (tieu_de or "").strip()
    if not td or _dinh_tu_loai_tru(td):
        return None
    if any(m in td for m in DAU_MOC_TUOI) or _TU_KHOA_TRUNG_NIEN.search(td):
        # "phòng bừa" xin được phép bừa là lệch nhịp — chỉ khi KHÔNG có mốc tuổi/cách dọn.
        for m, _ten, rx in CHU_DE_TRUNG_NIEN:
            if rx.search(td):
                return MA_TRUNG_NIEN, m
        return MA_TRUNG_NIEN, "tuoi-tac"
    # Tò mò xét TRƯỚC đánh giá thấp: "道を聞かれる人の才能" là thói quen vô hại (tò mò), chữ 才能 chỉ là khuôn.
    for tep in (MA_LECH_NHIP, MA_CANH_GIAC, MA_TO_MO, MA_THAP):
        for m, _ten, rx in CHU_DE[tep]:
            if rx.search(td):
                return tep, m
    return None


def dien_chu_de(goc: str, kenh: str, *, tep_dang_mo: Optional[Sequence[str]] = None) -> Dict[str, int]:
    """Điền cột "Chủ đề" cho mọi dòng content nhận ra được; điền cả "Tuyến / Kênh" khi ô ấy TRỐNG.

    Không đè nhãn tệp đã có (AI/người đặt) — chỉ thêm chủ đề cho nó. Dòng đã có tệp mà máy nhận ra
    chủ đề của TỆP KHÁC thì chủ đề để trống (không cãi nhau với nhãn). `tep_dang_mo`: chỉ điền tệp
    trong danh sách này (mặc định: mọi tệp máy biết). Trả {"chu_de": n, "tep_moi": n, "xem": n}.
    """
    from . import doi_thu_kenh as so  # noqa: PLC0415

    cot, hang = so.doc_bang(goc, kenh)
    o = {c: i for i, c in enumerate(cot)}
    i_td, i_t, i_cd, i_k = o.get("Tiêu đề video"), o.get(so.COT_TUYEN), o.get(so.COT_CHU_DE), o.get("Kênh")
    dem = {"chu_de": 0, "tep_moi": 0, "xem": 0}
    if i_td is None or i_t is None or i_cd is None:
        return dem
    cho_phep = set(tep_dang_mo) if tep_dang_mo else None
    doi = False
    for d in hang:
        while len(d) < len(cot):
            d.append("")
        td = str(d[i_td]).strip()
        if not td:
            continue
        dem["xem"] += 1
        kq = nhan_dien(td, str(d[i_k]) if i_k is not None else "")
        if kq is None:
            continue
        tep, cd = kq
        if cho_phep is not None and tep not in cho_phep:
            continue
        nhan = str(d[i_t]).strip()
        if not nhan:
            d[i_t] = tep
            dem["tep_moi"] += 1
            doi = True
            nhan = tep
        if nhan == tep and str(d[i_cd]).strip() != cd:
            d[i_cd] = cd
            dem["chu_de"] += 1
            doi = True
    if doi:
        so.luu_bang(goc, kenh, cot, hang)
    return dem
