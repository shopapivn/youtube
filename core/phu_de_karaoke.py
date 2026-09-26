"""Lớp phủ kiểu kênh drama: phụ đề karaoke + dải đen mờ + nhân vật tách nền + sóng âm.

Chủ dự án, 25/09/2026, chỉ vào một video mẫu (`Downloads/phụ đề.PNG`): *"nó có
ảnh nhân vật chính đã cắt nền ở bên trái với chiều cao tầm đó; nó có phụ đề có
khung đen mờ ở dưới sát đáy - text nằm giữa và theo kiểu karaoke; có hiệu ứng
sóng âm"*. Và: *"txt của content sẽ là chuẩn nhất còn thời gian thì lấy ở srt"*.

═══ CHỮ LẤY TỪ KỊCH BẢN, MỐC LẤY TỪ GIỌNG ĐỌC ═══

Không phải làm thêm bước nào: khâu phụ đề (`core/phu_de.tao_phu_de`) vốn đã ép
chữ kịch bản lên mốc máy nghe, từng ký tự. Nó ghi thêm mốc TỪNG TỪ ra
`3-phu-de-tu.json`; karaoke tô đúng từ đang đọc theo đó. Lượt cũ không có tệp ấy
thì rải mốc câu cho từng từ theo độ dài chữ — vẫn đúng chữ, chỉ kém chính xác.

═══ Ô TÍM SAU TỪ ĐANG ĐỌC — HAI LỚP CHỮ CHỒNG KHÍT ═══

`\\k` của ASS (cách AFFILIATE làm) chỉ đổi MÀU chữ, không vẽ được ô. Ở đây mỗi
nhóm chữ có hai lớp cùng nội dung, cùng kiểu chữ nên chồng khít từng điểm ảnh:

    lớp 0  cả nhóm chữ trắng, suốt thời gian của nhóm
    lớp 1  mỗi từ một sự kiện: chỉ từ đang đọc hiện (các từ khác trong suốt),
           kiểu `BorderStyle=3` — libass vẽ ô nền màu viền quanh chữ hiện

═══ SÓNG ÂM THẬT, VẼ BẰNG TAY ═══

Bản đầu dùng `showwaves` của FFmpeg — chủ dự án xem demo: *"cái sóng âm đang
không đẹp"*. Nó chỉ vẽ được nét thô. Nay `ve_song_am` tự phân tích giọng đọc
(FFT từng khung) và vẽ một dải vạch BO TRÒN đối xứng: giữa là âm trầm, hai bên
âm cao, hai đầu mờ dần; vạch lên nhanh hạ mượt như visualizer của CapCut.

Nhanh nhờ vẽ sẵn: mỗi mức cao một vạch khử răng cưa, mỗi khung chỉ còn ghép
bằng numpy (~0,3 ms thay vì 7,6 ms vẽ thẳng — video 60 phút là vài chục giây
thay vì mười bốn phút). Ra một video XÁM trắng-trên-đen (vài MB); lúc dựng độ
sáng thành độ trong suốt (`alphamerge`).

═══ NHÂN VẬT TÁCH NỀN BẰNG PILLOW ═══

Ảnh tham chiếu nhân vật của dây chuyền đạo diễn là ảnh toàn thân trên nền trắng
trơn. Loang từ mép ảnh những điểm gần màu nền là ra mặt nạ — không cần `rembg`
(~170 MB mô hình) hay gọi API. Nền không trơn (loang không ra) thì bỏ nhân vật,
vẫn dựng video, và nói ra.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "MAU_O", "NhomChu", "nhom_chu", "viet_ass", "tach_nen", "loc_lop_phu",
    "font_cho", "THU_MUC_FONT",
]

#: Thư mục font đóng gói kèm tool (Montserrat ExtraBold, OFL).
THU_MUC_FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "assets", "fonts")

#: Màu ô sau từ đang đọc — tím của video mẫu. Dạng "#RRGGBB".
MAU_O = "#7B2FF7"

#: Một nhóm chữ trên màn hình tối đa ngần này ký tự (≈ hai dòng như mẫu).
TRAN_KY_TU_NHOM = 30
#: Ngừng giữa hai từ quá ngần này giây thì sang nhóm mới.
NGUONG_NGUNG = 0.6

NhomChu = Tuple[float, float, List[Tuple[str, float, float]]]

_KET_CAU = tuple(".!?。！？…")


def font_cho(ngon_ngu: str) -> str:
    """Font theo tiếng. Chữ Latinh/Việt dùng font đóng gói; CJK/Hàn dùng font sẵn
    của Windows (Montserrat không có chữ Hàn)."""
    ma = (ngon_ngu or "").lower()[:2]
    return {"ko": "Malgun Gothic", "ja": "Yu Gothic", "zh": "Microsoft YaHei",
            "th": "Leelawadee UI"}.get(ma, "Montserrat ExtraBold")


def _rai_tu(chu: str, t0: float, t1: float) -> List[Tuple[str, float, float]]:
    """Không có mốc từng từ: rải khoảng của câu cho từng từ theo độ dài chữ."""
    tu = chu.split()
    if not tu:
        return []
    tong = float(sum(len(x) for x in tu)) or 1.0
    ra, t = [], t0
    for x in tu:
        d = (t1 - t0) * len(x) / tong
        ra.append((x, round(t, 3), round(t + d, 3)))
        t += d
    return ra


def nhom_chu(cau: Sequence[Dict], tran: int = TRAN_KY_TU_NHOM) -> List[NhomChu]:
    """Gom từ thành nhóm hiện cùng lúc trên màn hình.

    `cau`: `[{"bat_dau", "ket_thuc", "chu", "tu": [[từ, t0, t1], …]}]` — đúng
    dạng `3-phu-de-tu.json`, hoặc câu SRT không có "tu". Nhóm mới khi quá `tran`
    ký tự, khi hết câu (dấu chấm/hỏi/than), hoặc khi người đọc ngừng lâu.
    Nhóm kéo dài tới lúc nhóm sau bắt đầu (không nháy trống giữa hai nhóm liền).
    """
    tu: List[Tuple[str, float, float]] = []
    for c in cau:
        cua_cau = [(str(x[0]), float(x[1]), float(x[2])) for x in (c.get("tu") or [])]
        tu.extend(cua_cau or _rai_tu(str(c.get("chu") or ""), float(c["bat_dau"]),
                                     float(c["ket_thuc"])))
    # Tầng 1: cắt thành "câu nói" — ở dấu hết câu, hoặc chỗ người đọc ngừng lâu.
    cau_noi: List[List[Tuple[str, float, float]]] = []
    dem: List[Tuple[str, float, float]] = []
    for w in tu:
        if dem and w[1] - dem[-1][2] > NGUONG_NGUNG:
            cau_noi.append(dem)
            dem = []
        dem.append(w)
        if w[0].endswith(_KET_CAU):
            cau_noi.append(dem)
            dem = []
    if dem:
        cau_noi.append(dem)
    # Tầng 2: câu dài thì chia ĐỀU thành số nhóm ít nhất — không để thừa một
    # từ lẻ loi cuối câu (đo 25/09/2026: "TRAI." đứng một mình trên màn hình).
    nhom: List[List[Tuple[str, float, float]]] = []
    for c in cau_noi:
        dai = len(" ".join(x[0] for x in c))
        so = max(1, -(-dai // max(1, tran)))
        dich = dai / float(so)
        dem = []
        for w in c:
            dem.append(w)
            if so > 1 and len(" ".join(x[0] for x in dem)) >= dich:
                nhom.append(dem)
                dem = []
                so -= 1
        if dem:
            nhom.append(dem)
    ra: List[NhomChu] = []
    for k, n in enumerate(nhom):
        dau = n[0][1]
        cuoi = n[-1][2] + 0.25
        if k + 1 < len(nhom):
            sau = nhom[k + 1][0][1]
            # Ngừng dưới 2 giây (hết câu, dấu --- ) thì giữ chữ tới nhóm sau —
            # tắt rồi bật lại trong 1,5 giây là nháy mắt (đo demo 25/09/2026).
            cuoi = sau if sau - n[-1][2] < 2.0 else n[-1][2] + 0.25
        ra.append((dau, max(cuoi, dau + 0.2), n))
    return ra


def _gio(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    return "{0}:{1:02d}:{2:02d}.{3:02d}".format(cs // 360000, cs // 6000 % 60,
                                                cs // 100 % 60, cs % 100)


def _mau_ass(hex_rgb: str, alpha: int = 0) -> str:
    h = hex_rgb.lstrip("#")
    return "&H{0:02X}{1}{2}{3}".format(alpha, h[4:6], h[2:4], h[0:2]).upper()


def _sach(tu: str) -> str:
    return tu.replace("{", "(").replace("}", ")").replace("\\", "/")


def viet_ass(duong: str, nhom: Sequence[NhomChu], rong: int, cao: int, *,
             font: str = "Montserrat ExtraBold", le_trai: int = 0, le_phai: int = 0,
             le_duoi: int = 0, co_chu: int = 0, mau_o: str = MAU_O,
             in_hoa: bool = True) -> str:
    """Ghi tệp .ass karaoke. Trả đường dẫn. Xem ghi chú đầu tệp về hai lớp chữ."""
    co_chu = co_chu or int(round(cao * 0.068))
    le_trai = le_trai or int(rong * 0.06)
    le_phai = le_phai or int(rong * 0.06)
    # Một dòng chữ nằm giữa dải đen (dải từ 64% tới đáy), hai dòng thì dâng lên.
    le_duoi = le_duoi or int(cao * 0.13)
    dem_o = max(4, co_chu // 7)
    tieu_de = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: {r}\nPlayResY: {c}\n"
        "WrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Chu,{f},{s},&H00FFFFFF,&H00FFFFFF,&H64000000,&H96000000,1,0,0,0,100,100,"
        "1,0,1,2,2,2,{l},{p},{d},1\n"
        "Style: O,{f},{s},&H00FFFFFF,&H00FFFFFF,{o},{o},1,0,0,0,100,100,"
        "1,0,3,{b},0,2,{l},{p},{d},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n").format(r=rong, c=cao, f=font, s=co_chu, l=le_trai, p=le_phai,
                                 d=le_duoi, o=_mau_ass(mau_o), b=dem_o)
    dong: List[str] = [tieu_de]
    for dau, cuoi, tu in nhom:
        chu = [_sach(w[0].upper() if in_hoa else w[0]) for w in tu]
        dong.append("Dialogue: 0,{0},{1},Chu,,0,0,0,,{2}\n".format(
            _gio(dau), _gio(cuoi), " ".join(chu)))
        for i, w in enumerate(tu):
            a = max(dau, w[1])
            b = tu[i + 1][1] if i + 1 < len(tu) else cuoi
            b = min(max(b, a + 0.05), cuoi)
            # Dấu cách luôn trong suốt — không thì ô tím lấn sang khoảng trống
            # bên cạnh từ (đo 25/09/2026).
            phan = []
            for j, x in enumerate(chu):
                if j:
                    phan.append("{\\alpha&HFF&\\3a&HFF&\\4a&HFF&} ")
                an = "00" if j == i else "FF"
                phan.append("{{\\alpha&H{0}&\\3a&H{0}&\\4a&H{0}&}}{1}".format(an, x))
            dong.append("Dialogue: 1,{0},{1},O,,0,0,0,,{2}\n".format(
                _gio(a), _gio(b), "".join(phan)))
    tam = duong + ".tmp"
    with open(tam, "w", encoding="utf-8-sig") as tep:
        tep.write("".join(dong))
    os.replace(tam, duong)
    return duong


def tach_nen(vao: str, ra: str, cao_px: int, phan_tren: float = 0.74,
             nguong: int = 38, rong_toi_da: int = 0) -> Optional[Tuple[int, int]]:
    """Tách nhân vật khỏi nền trơn, cắt lấy `phan_tren` phía trên (đầu → đùi, như
    mẫu), phóng cao `cao_px`, ghi PNG trong suốt. Trả `(rộng, cao)` hoặc None.

    Nền = màu trung bình bốn góc. Loang từ mọi điểm mép ảnh gần màu nền (sai
    khác ≤ `nguong`) — chỉ vùng NỐI với mép mới là nền, nên áo trắng giữa người
    không bị khoét. Mép mặt nạ làm mềm 1,5 điểm ảnh cho khỏi răng cưa.
    """
    from PIL import Image, ImageChops, ImageDraw, ImageFilter  # noqa: PLC0415

    anh = Image.open(vao).convert("RGB")
    w, h = anh.size
    # Nền = màu HAI GÓC TRÊN. Ảnh người kể nửa thân có thân áo chạm hai góc
    # dưới — đòi bốn góc cùng màu là loại oan (đo 26/09/2026: ảnh Daniel mặc
    # vest bị bỏ). Hai góc dưới chỉ được tính khi chúng cũng là nền.
    tren = [anh.getpixel(p) for p in ((2, 2), (w - 3, 2))]
    if max(abs(tren[0][k] - tren[1][k]) for k in range(3)) > 40:
        return None                      # hai góc trên khác màu nhau — nền không trơn
    goc = tren + [c for c in (anh.getpixel((2, h - 3)), anh.getpixel((w - 3, h - 3)))
                  if max(abs(c[k] - tren[0][k]) for k in range(3)) <= 40]
    nen = tuple(sum(c[k] for c in goc) // len(goc) for k in range(3))
    loang = anh.copy()
    dau = (255, 0, 255) if nen != (255, 0, 255) else (0, 255, 0)
    buoc = max(8, min(w, h) // 60)

    def loang_tu(x: int, y: int) -> None:
        # Chỉ loang từ điểm mép CÙNG MÀU NỀN. Ảnh người kể nửa thân có áo chạm
        # mép dưới: loang từ điểm nằm trên áo là khoét mất cả thân áo.
        p = loang.getpixel((x, y))
        if p != dau and max(abs(p[k] - nen[k]) for k in range(3)) <= nguong:
            ImageDraw.floodfill(loang, (x, y), dau, thresh=nguong)

    for x in range(0, w, buoc):
        for y in (0, h - 1):
            loang_tu(x, y)
    for y in range(0, h, buoc):
        for x in (0, w - 1):
            loang_tu(x, y)
    khac = ImageChops.difference(loang, Image.new("RGB", (w, h), dau)).convert("L")
    mat_na = khac.point(lambda v: 255 if v > 0 else 0)
    mat_na = mat_na.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.5))
    hop = mat_na.getbbox()
    if not hop or (hop[2] - hop[0]) * (hop[3] - hop[1]) < 0.02 * w * h:
        return None
    x0, y0, x1, y1 = hop
    y1 = y0 + int((y1 - y0) * max(0.3, min(1.0, phan_tren)))
    nguoi = anh.convert("RGBA")
    nguoi.putalpha(mat_na)
    nguoi = nguoi.crop((x0, y0, x1, y1))
    if rong_toi_da and nguoi.size[0] * cao_px / float(nguoi.size[1]) > rong_toi_da:
        # Ảnh nửa thân rộng (tay đưa ra khi kể) — thu nhỏ theo bề ngang để
        # chừa chỗ cho chữ, không để người chiếm nửa khung.
        cao_px = max(2, int(rong_toi_da * nguoi.size[1] / float(nguoi.size[0]))) // 2 * 2
    ti = cao_px / float(nguoi.size[1])
    nguoi = nguoi.resize((max(2, int(nguoi.size[0] * ti)) // 2 * 2, cao_px), Image.LANCZOS)
    nguoi.save(ra)
    return nguoi.size


def _nang_luong(ffmpeg: str, mp3: str, fps: float, so_dai: int):
    """Mức từng dải tần theo từng khung hình: mảng `[số khung, so_dai]` trong [0, 1].

    Giải mã giọng đọc về mono 16 kHz, FFT cửa sổ 64 ms quanh mỗi khung, gom
    vào `so_dai` dải chia theo thang log 90 Hz–6 kHz. Mỗi dải chuẩn hoá theo
    CHÍNH NÓ (bách phân vị 20 → 97): giọng nói dồn năng lượng ở dải thấp, không
    chuẩn hoá riêng thì các vạch âm cao đứng im cả video.
    """
    import subprocess  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    from .chuyen_dong_anh import _co_tien_trinh  # noqa: PLC0415

    sr = 16000
    ra = subprocess.run([ffmpeg, "-v", "error", "-i", mp3, "-ac", "1", "-ar", str(sr),
                         "-f", "s16le", "-"], stdout=subprocess.PIPE, check=True,
                        creationflags=_co_tien_trinh())
    tieng = np.frombuffer(ra.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    cua = 1024
    so_khung = max(1, int(len(tieng) / sr * fps))
    tieng = np.pad(tieng, (cua, cua))
    han = np.hanning(cua).astype(np.float32)
    tan = np.fft.rfftfreq(cua, 1.0 / sr)
    bien = np.geomspace(90, 6000, so_dai + 1)
    chi_so = [np.where((tan >= a) & (tan < b))[0] for a, b in zip(bien, bien[1:])]
    chi_so = [c if len(c) else np.array([int(np.argmin(abs(tan - a)))])
              for c, a in zip(chi_so, bien)]
    muc = np.zeros((so_khung, so_dai), dtype=np.float32)
    for dau in range(0, so_khung, 2000):
        k = np.arange(dau, min(so_khung, dau + 2000))
        tam = (k / fps * sr).astype(np.int64) + cua // 2
        cat = tieng[tam[:, None] + np.arange(cua)[None, :]] * han
        pho = np.abs(np.fft.rfft(cat, axis=1))
        for j, c in enumerate(chi_so):
            muc[k, j] = 20 * np.log10(pho[:, c].mean(axis=1) + 1e-6)
    thap = np.percentile(muc, 20, axis=0)
    cao = np.percentile(muc, 97, axis=0)
    return np.clip((muc - thap) / np.maximum(cao - thap, 1e-3), 0.0, 1.0)


def ve_song_am(ffmpeg: str, mp3: str, dich: str, rong: int, cao: int, fps: float,
               so_vach: int = 56, dung=None) -> str:
    """Vẽ dải sóng âm theo giọng đọc ra video XÁM (trắng trên đen). Trả `dich`.

    Vạch đối xứng qua giữa (giữa = âm trầm), lên nhanh / hạ mượt, hai đầu mờ
    dần, bo tròn và khử răng cưa. Xem ghi chú đầu tệp.
    """
    import subprocess  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415
    from PIL import Image, ImageDraw  # noqa: PLC0415

    from .chuyen_dong_anh import _co_tien_trinh  # noqa: PLC0415

    rong, cao = rong // 2 * 2, cao // 2 * 2
    nua = so_vach // 2
    muc = _nang_luong(ffmpeg, mp3, fps, nua)
    buoc = rong / float(so_vach)
    ngang = max(2, int(round(buoc * 0.55)))
    x = [int(round(i * buoc + (buoc - ngang) / 2)) for i in range(so_vach)]
    # Mức hiện của vạch i: nửa trái đảo ngược nửa phải, giữa là dải thấp nhất.
    thu_tu = list(range(nua - 1, -1, -1)) + list(range(nua))
    mo = np.array([0.35 + 0.65 * (1 - abs((i + 0.5) / so_vach * 2 - 1)) ** 0.8
                   for i in range(so_vach)], dtype=np.float32)
    # Dáng chung: cao ở giữa, thấp dần về hai đầu. Không có nó thì dải vạch
    # đều như một khối chữ nhật (demo 25/09/2026).
    dang = np.array([0.30 + 0.70 * np.sin(np.pi * (i + 0.5) / so_vach)
                     for i in range(so_vach)], dtype=np.float32)
    # Vẽ sẵn: mỗi mức cao một vạch bo tròn, vẽ to gấp 4 rồi thu nhỏ = khử răng cưa.
    so_muc = 48
    mau: List = []
    for m in range(so_muc):
        h = max(ngang, (0.12 + 0.88 * m / (so_muc - 1)) * cao)
        to = Image.new("L", (ngang * 4, cao * 4), 0)
        ImageDraw.Draw(to).rounded_rectangle(
            (0, (cao - h) * 2, ngang * 4 - 1, (cao + h) * 2), radius=ngang * 2, fill=255)
        mau.append(np.asarray(to.resize((ngang, cao), Image.LANCZOS), dtype=np.float32))
    tam = dich + ".tmp.mp4"
    tt = subprocess.Popen(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
         "-pix_fmt", "gray", "-s", "{0}x{1}".format(rong, cao), "-r", "{0:g}".format(fps),
         "-i", "-", "-c:v", "libx264", "-preset", "fast", "-crf", "12",
         "-pix_fmt", "yuv420p", tam],
        stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=_co_tien_trinh())
    try:
        hien = np.zeros(nua, dtype=np.float32)
        for k in range(len(muc)):
            if dung is not None and k % 500 == 0:
                dung()
            v = muc[k]
            # Lên nhanh, hạ mượt — vạch không giật xuống theo từng âm tiết.
            hien = np.where(v > hien, hien + (v - hien) * 0.65, hien * 0.86 + v * 0.14)
            khung = np.zeros((cao, rong), dtype=np.float32)
            for i in range(so_vach):
                m = int(hien[thu_tu[i]] * dang[i] * (so_muc - 1) + 0.5)
                khung[:, x[i]:x[i] + ngang] = mau[m] * mo[i]
            tt.stdin.write(khung.clip(0, 255).astype(np.uint8).tobytes())
        tt.stdin.close()
        loi = tt.stderr.read().decode("utf-8", "replace")
        if tt.wait() != 0:
            raise RuntimeError("không vẽ được sóng âm: {0}".format(loi[-300:]))
    except BaseException:
        tt.kill()
        try:
            os.remove(tam)
        except OSError:
            pass
        raise
    os.replace(tam, dich)
    return dich


def _duong_loc(p: str) -> str:
    """Đường dẫn nằm trong chuỗi lọc FFmpeg: gạch xuôi, thoát dấu hai chấm và nháy."""
    return os.path.abspath(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def loc_lop_phu(rong: int, cao: int, fps: float, ass: str, *, song: str = "",
                nv: str = "", nv_rong: int = 0, nv_cao: int = 0, nv_x: int = 0,
                song_x: int = 0, song_rong: int = 0, song_cao: int = 0,
                vao: str = "nen", ra: str = "out") -> str:
    """Chuỗi lọc: dải đen mờ → nhân vật → sóng âm → phụ đề karaoke.

    Nhận nhãn `[vao]` (khung đã đúng cỡ `rong`×`cao`), trả nhãn `[ra]`. Nhân vật
    đứng TRÊN dải đen (như mẫu: tay người không bị phủ tối), chữ nằm trên cùng.
    """
    phan = ["[{0}]drawbox=x=0:y=ih*0.64:w=iw:h=ih*0.36:color=black@0.55:t=fill[d]".format(vao)]
    nhan = "d"
    if nv and nv_cao:
        phan.append("movie='{0}',format=rgba[nv]".format(_duong_loc(nv)))
        phan.append("[{0}][nv]overlay=x={1}:y={2}:format=auto[dn]".format(
            nhan, nv_x, cao - nv_cao))
        nhan = "dn"
    if song and song_rong and song_cao:
        # Video sóng âm xám (`ve_song_am`): độ sáng thành độ trong suốt của một
        # lớp trắng — nét bo tròn khử răng cưa giữ nguyên.
        phan.append("movie='{0}',format=gray[sa]".format(_duong_loc(song)))
        phan.append("color=c=white:s={0}x{1}:r={2:g}[sw]".format(song_rong, song_cao, fps))
        phan.append("[sw][sa]alphamerge[song]")
        phan.append("[{0}][song]overlay=x={1}:y={2}:eof_action=pass:format=auto[ds]".format(
            nhan, song_x, cao - song_cao - int(cao * 0.025)))
        nhan = "ds"
    phan.append("[{0}]subtitles='{1}':fontsdir='{2}'[{3}]".format(
        nhan, _duong_loc(ass), _duong_loc(THU_MUC_FONT), ra))
    return ";".join(phan)
