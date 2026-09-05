"""Quét content đối thủ không cần giao diện — cùng đường với nút "Quét đối thủ": gộp sổ, nuôi danh bạ, ghi mốc.

Dựng dữ liệu bằng `lay_du_lieu(thu_thap=giả)` của core — đi qua đúng khâu phân tích thật, chỉ thay
lời gọi mạng. Không yt-dlp, không Qt.
"""

import functools
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import danh_ba_doi_thu as db  # noqa: E402
from core import doi_thu_kenh as so  # noqa: E402
from core import quet_doi_thu as qdt  # noqa: E402
from core.doi_thu import lay_du_lieu  # noqa: E402
from core.youtube import Channel, Video  # noqa: E402

KENH = "TL4-T7"
LINK = "https://www.youtube.com/@zure"


def _kenh(views=(1000, 1000, 9000)):
    vids = [Video(video_id="zure%02d" % i, title="tiêu đề %d 一人が好きな人" % i,
                  url="https://www.youtube.com/watch?v=zure%02d" % i, views=v, duration_s=570,
                  upload_date="2026-09-0%d" % (i + 1), channel_name="ズレは才能")
            for i, v in enumerate(views)]
    return Channel(input_url=LINK, name="ズレは才能【心の仕組み】", channel_url=LINK, subscribers=7700, videos=vids)


def _lay(views=(1000, 1000, 9000)):
    def thu_thap(inputs, **kw):
        return [_kenh(views)], []
    return functools.partial(lay_du_lieu, thu_thap=thu_thap)


def _goc(tmp_path):
    (tmp_path / "CHANNEL" / KENH / "nghien-cuu").mkdir(parents=True)
    return str(tmp_path)


def test_quet_gop_so_nuoi_danh_ba_va_ghi_moc(tmp_path):
    goc = _goc(tmp_path)
    nhat_ky = []
    dem = qdt.quet(goc, KENH, [LINK], lang="ja", lay=_lay(), on_log=nhat_ky.append)
    assert dem == {"kenh": 1, "video": 3, "dong_truoc": 0, "dong_sau": 3}
    cot, hang = so.doc_bang(goc, KENH)
    o = {c: i for i, c in enumerate(cot)}
    assert sorted(h[o["Link video"]][-6:] for h in hang) == ["zure00", "zure01", "zure02"]
    assert {h[o["Kênh"]] for h in hang} == {"ズレは才能【心の仕組み】"}
    c2, h2 = db.doc(goc, KENH)
    o2 = db.chi_so_cot(list(c2))
    assert len(h2) == 1 and h2[0][o2["Subs"]] == "7700" and h2[0][o2["View TV"]] == "1000"
    assert h2[0][o2["Dài TV"]] == "9:30" and h2[0][o2["Trạng thái"]] == db.THEO_DOI
    assert so.doc_cai(goc, KENH).get("quet_luc"), "phải ghi mốc quét để lượt sau tính Tăng/ngày"
    assert any("3 video" in m for m in nhat_ky)


def test_luot_hai_khong_nhan_dong_va_co_tang_ngay(tmp_path):
    goc = _goc(tmp_path)
    qdt.quet(goc, KENH, [LINK], lang="ja", lay=_lay((1000, 1000, 9000)))
    so.luu_cai(goc, KENH, quet_luc=time.time() - 2 * 86400)     # giả là quét cách đây 2 ngày
    dem = qdt.quet(goc, KENH, [LINK], lang="ja", lay=_lay((1000, 1000, 15000)))
    assert dem["dong_truoc"] == 3 and dem["dong_sau"] == 3, "cùng link phải GỘP, không nhân dòng"
    cot, hang = so.doc_bang(goc, KENH)
    o = {c: i for i, c in enumerate(cot)}
    dong = next(h for h in hang if h[o["Link video"]].endswith("zure02"))
    assert dong[o["View"]] == "15000" and dong[o["View lần trước"]] == "9000"
    assert dong[o["Tăng/ngày"]].strip(), "lượt hai phải ra Tăng/ngày — thước NHANH của bộ chấm"


def test_khong_co_link_thi_khong_dung_so(tmp_path):
    goc = _goc(tmp_path)
    assert qdt.quet(goc, KENH, [], lay=_lay()) == {"kenh": 0, "video": 0, "dong_truoc": 0, "dong_sau": 0}
    assert not os.path.exists(os.path.join(goc, "CHANNEL", KENH, "nghien-cuu", "content.csv"))
