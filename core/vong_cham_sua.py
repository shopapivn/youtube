"""Vòng CHẤM TOÀN BÀI → VÁ (vài bản) → CHẤM SO — chọn lọc, không thêm luật.

═══ VÌ SAO CÓ TỆP NÀY (09/09/2026) ═══

Template remake sống bằng hai thứ: lời nhắc ngắn có một mục tiêu rõ, và làm vài
bản rồi chọn. Chủ dự án: *"prompt càng đơn giản càng mở và có mục tiêu chính thì
AI càng làm tốt… làm nhiều chọn ra cái hay — bộ chấm và sửa chưa có logic đó"*.

Đo trên lượt TL4-T7/0012: bộ chấm nhìn đúng chỗ (tự bắt ý 1 ở 29%, câu trì hoãn,
thiếu câu hỏi), nhưng ĐƯỜNG ỐNG làm bài dở đi ở ba khớp:

1. Bản ghép cuối (hook mới + thân) chưa bao giờ được chấm như MỘT bài — hook mới
   cắt mất nghịch lý + thuyết Savanna mà chính bộ chấm bảo giữ.
2. Bộ chấm chỉ có kịch bản gốc; không biết người xem gốc thích câu nào (248 bình
   luận), không biết kênh đã đo được gì về giữ chân.
3. Mã vứt bản sửa vì độ dài (×1,27 > 1,25) trước khi bộ chấm kịp so.

Vòng ở đây chữa đúng ba khớp ấy và không thêm luật nào vào lời nhắc viết:

    CHẤM TOÀN BÀI (bản đồ rớt so với gốc, có bình luận gốc + số thật của kênh)
        → "giữ" thì dừng
        → "sửa" thì VÁ `so_ban_va` bản, cùng một lời chê
        → CHẤM SO [bản cũ, các bản vá] — cùng bộ chấm, cùng dữ liệu
        → chọn bản cũ: đếm "không hơn"; chọn bản vá: nhận
    lặp tối đa `so_vong`; dừng khi 2 vòng liền không hơn.

Mã chỉ chặn MỘT thứ: bản vá viết lại từ đầu (trùng chữ với bản trước dưới
`GIU_CHU_VA`) hoặc dài/ngắn dị dạng. Hay/dở là việc của bộ chấm — cửa thật là
bộ chấm so hai bản cạnh nhau, rào chắn số là cửa giả.

Bản đồ rớt của bản cuối được trả về để nơi gọi ghi ra đĩa: sau giờ 85, khi
Studio có đường giữ chân thật, đặt hai thứ cạnh nhau là cách duy nhất để bộ chấm
được sửa bởi khán giả thật thay vì bởi gu của model.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .goi_van_ban import loc_json
from .viet_nhieu_ban import _thay, nhan_ban, trung_nguyen_van

__all__ = ["KHUON_CHAM_TOAN_BAI", "KHUON_VA_TOAN_BAI", "GIU_CHU_VA",
           "DAI_VA_MIN", "DAI_VA_MAX", "khoi_binh_luan", "cham_toan_bai",
           "vong_cham_sua", "so_voi_that", "ban_do_json"]

#: Khuôn mặc định khi kênh không có `prompt/2g-cham-toan-bai.md`. Ô:
#: `<<SO_BAN>>`, `<<PHUT>>`, `<<COMPETITOR_TRANSCRIPT>>`, `<<BINH_LUAN_GOC>>`,
#: `<<SU_THAT_KENH>>`, `<<CAC_BAN>>`.
KHUON_CHAM_TOAN_BAI = (
    "Dưới đây là kịch bản đã viral (bản gốc) và <<SO_BAN>> bản của tôi (đánh dấu "
    "A, B, C…), cùng bình luận người xem dưới bản gốc và số giữ chân đã đo trên "
    "kênh tôi.\n\nMục đích duy nhất: kịch bản HAY — hay tới mức khán giả nói "
    "<<NGON_NGU>> xem HẾT. YouTube đo cái hay bằng đúng việc ấy.\n\n"
    "Hình dung người xem gốc đang xem từng bản (khoảng <<PHUT>> phút). Vẽ bản đồ "
    "rớt: chia bài thành 6–8 đoạn, mỗi đoạn chiếm từ bao nhiêu tới bao nhiêu % bài, "
    "tới cuối đoạn còn lại bao nhiêu % người xem so với lúc bắt đầu, vì sao. Bản "
    "của tôi có giữ được thứ người xem gốc nhớ không. Chọn MỘT bản; chỉ có một bản "
    "thì trả lời giữ hay sửa.\n\n"
    "Trả về DUY NHẤT một JSON:\n"
    "{\"chon\": \"A\", \"ban_do_rot\": {\"A\": [{\"doan\": \"\", \"tu_pct\": 0, "
    "\"den_pct\": 12, \"con_lai\": 70, \"vi_sao\": \"\"}]}, \"cho_kem_nhat\": \"\", "
    "\"mat_gi_cua_goc\": \"\", \"giu_hay_sua\": \"giữ hoặc sửa\"}\n\n"
    "bản gốc:\n\n<<COMPETITOR_TRANSCRIPT>>\n\n"
    "bình luận dưới bản gốc:\n\n<<BINH_LUAN_GOC>>\n\n"
    "số giữ chân đã đo trên kênh tôi:\n\n<<SU_THAT_KENH>>\n\n<<CAC_BAN>>")

#: Khuôn vá mặc định. Ô: `<<CHO_KEM>>`, `<<MAT_GI>>`, `<<NGON_NGU>>`,
#: `<<COMPETITOR_TRANSCRIPT>>`, `<<DRAFT>>`.
KHUON_VA_TOAN_BAI = (
    "Kịch bản dưới đây đã ghép xong. Bộ chấm nói:\n- chỗ kém nhất: <<CHO_KEM>>\n"
    "- thứ của bản gốc bị mất mà người xem nhớ: <<MAT_GI>>\n\n"
    "Sửa đúng chỗ đó để kịch bản hay hơn — hay tới mức khán giả nói <<NGON_NGU>> "
    "xem hết — lấy chất liệu từ bản gốc "
    "nếu cần; chỗ khác giữ nguyên. Viết bằng <<NGON_NGU>>. Trả về NGUYÊN VĂN toàn "
    "bộ kịch bản sau khi sửa, không nhận xét.\n\n"
    "bản gốc:\n\n<<COMPETITOR_TRANSCRIPT>>\n\nkịch bản cần sửa:\n\n<<DRAFT>>")

#: Bản vá trùng chữ với bản trước dưới mức này là viết lại từ đầu — bỏ. Đây là
#: rào chắn DUY NHẤT bằng mã; độ dài không chặn (bước nắn độ dài đứng sau).
GIU_CHU_VA = 0.5
#: Chỉ bắt bản dị dạng (rỗng một nửa, hoặc phình gần gấp đôi).
DAI_VA_MIN, DAI_VA_MAX = 0.6, 1.6


#: Khối bình luận đưa cho bộ chấm: đủ để biết người xem nhớ gì, không dài tới
#: mức loãng bài chấm. Chủ dự án 09/09/2026: "giới hạn để nó đảm bảo kết quả ok".
BINH_LUAN_TOI_DA, BINH_LUAN_DAI = 20, 200


def khoi_binh_luan(binh_luan: Sequence[Tuple[int, str]],
                   toi_da: int = BINH_LUAN_TOI_DA) -> str:
    """Bình luận `(like, chữ)` → khối chữ cho lời nhắc; rỗng nếu không có gì."""
    dong: List[str] = []
    for like, chu in list(binh_luan or []):
        chu = " ".join(str(chu or "").split())
        if chu:
            dong.append("({0}) {1}".format(int(like or 0), chu[:BINH_LUAN_DAI]))
        if len(dong) >= toi_da:
            break
    return "\n".join(dong)


def _ten_ban(i: int, ten_ban: Optional[Sequence[str]]) -> str:
    if ten_ban and i < len(ten_ban):
        return str(ten_ban[i])
    return "bản " + nhan_ban(i)


def cham_toan_bai(goi: Callable[[str], str], cac_ban: Sequence[str], goc: str, *,
                  khuon: str = "", chung: Optional[Dict[str, Any]] = None,
                  ghi: Optional[Callable[[str], None]] = None,
                  ten_ban: Optional[Sequence[str]] = None,
                  ) -> Tuple[int, Dict[str, Any]]:
    """Chấm `cac_ban` như những bài trọn vẹn. Trả `(chỉ số bản chọn, JSON bộ chấm)`.

    Chấm hỏng (gọi lỗi, JSON lỗi, chọn chữ lạ) → chọn bản đầu (bản đang có) và
    JSON mang khoá `loi`. Không bao giờ ném — vòng chấm không được làm vỡ bài.
    """
    o = dict(chung or {})
    o.update({
        "SO_BAN": len(cac_ban),
        "CAC_BAN": "\n\n".join("=== BẢN {0} ===\n{1}".format(nhan_ban(i), b)
                               for i, b in enumerate(cac_ban)),
        "COMPETITOR_TRANSCRIPT": goc or "",
    })
    o.setdefault("BINH_LUAN_GOC", "(không có)")
    o.setdefault("SU_THAT_KENH", "(chưa có)")
    o.setdefault("PHUT", "?")
    o.setdefault("NGON_NGU", "tiếng của kênh")
    try:
        tra = goi(_thay(khuon.strip() or KHUON_CHAM_TOAN_BAI, o))
        ket = loc_json(tra)
        if not isinstance(ket, dict):
            raise ValueError("bộ chấm không trả JSON dạng đối tượng")
    except Exception as loi:  # noqa: BLE001 — chấm hỏng thì giữ bản đang có
        if ghi is not None:
            ghi("  (chấm toàn bài hỏng: {0} — giữ bản đang có)".format(str(loi)[:90]))
        return 0, {"loi": str(loi)[:200]}
    chu = str(ket.get("chon") or "").strip().upper()[:1]
    i = ord(chu) - 65 if chu else 0
    if not (0 <= i < len(cac_ban)):
        i = 0
    if ghi is not None:
        ghi("  chấm toàn bài: chọn {0} · {1} · kém nhất: {2}".format(
            _ten_ban(i, ten_ban), str(ket.get("giu_hay_sua") or "?").strip(),
            str(ket.get("cho_kem_nhat") or "").strip()[:140]))
    return i, ket


def _muon_sua(ket: Dict[str, Any]) -> bool:
    q = str(ket.get("giu_hay_sua") or "").strip().lower()
    if "giữ" in q or q.startswith("giu") or q in ("keep", "giu"):
        return False
    return bool(str(ket.get("cho_kem_nhat") or "").strip())


def _ban_do(ket: Dict[str, Any], i: int) -> Any:
    bd = ket.get("ban_do_rot")
    if isinstance(bd, dict):
        return bd.get(nhan_ban(i)) or bd.get(str(i)) or bd
    return bd


def vong_cham_sua(goi_cham: Callable[[str], str], goi_va: Callable[[str], str],
                  ban: str, goc: str, *,
                  khuon_cham: str = "", khuon_va: str = "",
                  chung: Optional[Dict[str, Any]] = None,
                  so_vong: int = 3, so_ban_va: int = 2,
                  ghi: Optional[Callable[[str], None]] = None,
                  don: Optional[Callable[[str], str]] = None,
                  luu: Optional[Callable[[str, str], None]] = None,
                  ) -> Tuple[str, str, Any]:
    """Chấm toàn bài → vá vài bản → chấm so, tối đa `so_vong` vòng.

    Trả `(bản cuối, biên bản, bản đồ rớt của bản cuối)`. Hỏng ở đâu cũng trả
    về bản đang có. `don` dọn chữ AI trả về (lời dẫn, ghi chú); `luu(tên, chữ)`
    để nơi gọi ghi từng bản vá ra đĩa.
    """
    def noi(dong: str) -> None:
        if ghi is not None:
            ghi(dong)

    o = dict(chung or {})
    o["COMPETITOR_TRANSCRIPT"] = goc or ""   # lời nhắc vá cũng cần bản gốc để lấy chất liệu
    o.setdefault("NGON_NGU", "tiếng của kênh")
    bien_ban: List[str] = []
    ban_do_cuoi: Any = None
    khong_hon = 0
    hien = (ban or "").strip()
    if not hien:
        return ban, "bài rỗng, không chấm", None

    for vong in range(1, max(0, int(so_vong or 0)) + 1):
        noi("  vòng chấm-sửa {0}/{1}…".format(vong, so_vong))
        _i, ket = cham_toan_bai(goi_cham, [hien], goc, khuon=khuon_cham, chung=o,
                                ghi=ghi, ten_ban=("bản đang có",))
        if "loi" in ket:
            bien_ban.append("vòng {0}: chấm hỏng — {1}".format(vong, ket["loi"]))
            break
        ban_do_cuoi = _ban_do(ket, 0) or ban_do_cuoi
        bien_ban.append("vòng {0}: {1} · kém nhất: {2} · mất của gốc: {3}".format(
            vong, str(ket.get("giu_hay_sua") or "?").strip(),
            str(ket.get("cho_kem_nhat") or "").strip()[:300],
            str(ket.get("mat_gi_cua_goc") or "").strip()[:300]))
        if not _muon_sua(ket):
            bien_ban.append("  → bộ chấm nói giữ, dừng.")
            break

        # ── VÁ vài bản, cùng một lời chê — làm nhiều rồi chọn, không sửa một lần rồi tin
        loi_nhac = _thay(khuon_va.strip() or KHUON_VA_TOAN_BAI, dict(
            o, CHO_KEM=str(ket.get("cho_kem_nhat") or "").strip() or "(không ghi)",
            MAT_GI=str(ket.get("mat_gi_cua_goc") or "").strip() or "(không mất)",
            DRAFT=hien))
        va: List[str] = []
        for j in range(max(1, int(so_ban_va or 1))):
            try:
                chu = (goi_va(loi_nhac) or "").strip()
            except Exception as loi:  # noqa: BLE001 — một bản vá hỏng không làm vỡ vòng
                noi("  (bản vá {0} hỏng: {1})".format(nhan_ban(j), str(loi)[:80]))
                continue
            if don is not None:
                chu = (don(chu) or "").strip()
            if not chu:
                continue
            ti_le = len(chu) / max(1, len(hien))
            giu_chu = trung_nguyen_van(chu, hien)
            if giu_chu < GIU_CHU_VA or not (DAI_VA_MIN <= ti_le <= DAI_VA_MAX):
                noi("  (bỏ bản vá {0}: trùng chữ {1:.0%}, dài x{2:.2f} — viết lại từ đầu)"
                    .format(nhan_ban(j), giu_chu, ti_le))
                bien_ban.append("  bỏ bản vá {0}: trùng chữ {1:.0%}, dài x{2:.2f}".format(
                    nhan_ban(j), giu_chu, ti_le))
                continue
            va.append(chu)
            if luu is not None:
                luu("vong{0}-va{1}".format(vong, nhan_ban(j)), chu)
        if not va:
            bien_ban.append("  → không bản vá nào dùng được, giữ bản đang có.")
            break

        # ── CHẤM SO: bản cũ đứng đầu, các bản vá theo sau — cùng bộ chấm, cùng dữ liệu
        ten = ["bản cũ"] + ["bản vá " + nhan_ban(j) for j in range(len(va))]
        i_hon, ket_so = cham_toan_bai(goi_cham, [hien] + va, goc, khuon=khuon_cham,
                                      chung=o, ghi=ghi, ten_ban=ten)
        if "loi" in ket_so:
            bien_ban.append("  chấm so hỏng — giữ bản cũ.")
            break
        if i_hon == 0:
            khong_hon += 1
            bien_ban.append("  → bộ chấm vẫn thích bản cũ ({0} vòng liền).".format(khong_hon))
            if khong_hon >= 2:
                bien_ban.append("  → hai vòng không hơn, dừng.")
                break
            continue
        khong_hon = 0
        hien = va[i_hon - 1]
        ban_do_cuoi = _ban_do(ket_so, i_hon) or ban_do_cuoi
        bien_ban.append("  → nhận {0} ({1} ký tự).".format(ten[i_hon], len(hien)))
        if luu is not None:
            luu("vong{0}-chon".format(vong), hien)

    return hien, "\n".join(bien_ban), ban_do_cuoi


def so_voi_that(ban_do: Any, retention: Sequence[float]) -> List[str]:
    """Đặt bản đồ rớt bộ chấm ĐOÁN cạnh đường giữ chân THẬT của Studio.

    `retention` là dãy % người còn lại theo % độ dài video (Studio trả ~100
    điểm, `chi_so_ytb.BanGhi.retention`). Mỗi đoạn của bản đồ có `den_pct` →
    lấy điểm thật tại đó. Trả về các dòng sẵn để dán vào
    `nghien-cuu/su-that-cham.txt` — đây là cách bộ chấm được khán giả thật sửa.
    Thiếu dữ liệu (không có `den_pct`, retention rỗng) thì trả `[]`.
    """
    r = list(retention or [])
    if not r or not isinstance(ban_do, list):
        return []
    ra: List[str] = []
    for doan in ban_do:
        if not isinstance(doan, dict):
            continue
        try:
            den = float(doan.get("den_pct"))
            doan_du = float(doan.get("con_lai"))
        except (TypeError, ValueError):
            continue
        i = min(len(r) - 1, max(0, int(round(den / 100.0 * (len(r) - 1)))))
        that = float(r[i])
        lech = that - doan_du
        ra.append("- {0} (tới {1:.0f}% bài): bộ chấm đoán còn {2:.0f}% người, thật {3:.0f}% ({4:+.0f})"
                  .format(str(doan.get("doan") or "?")[:40], den, doan_du, that, lech))
    return ra


def ban_do_json(ban_do: Any) -> str:
    """Bản đồ rớt → chuỗi JSON để ghi cạnh lượt (so với đường giữ chân thật sau này)."""
    try:
        return json.dumps(ban_do, ensure_ascii=False, indent=1)
    except Exception:  # noqa: BLE001
        return str(ban_do)
