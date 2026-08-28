"""Kênh `openstory`: bản đối chứng của `story-3d`, chỉ khác đúng `7-canh.md`.

Kênh này sinh ra để TRẢ LỜI MỘT CÂU HỎI: lối viết lời nhắc của OpenStory
(`THAM-KHAO/openstory`, đọc 26/08/2026 — bóc tách ở `THAM-KHAO/OPENSTORY-BOC-TACH.md`)
có cho ảnh đẹp hơn lối đang dùng không.

Câu trả lời chỉ dùng được khi hai kênh khác nhau ĐÚNG MỘT THỨ. Nên bài kiểm này
canh hai chuyện:

1. bảy tệp lời nhắc còn lại phải trùng `story-3d` **từng byte** — ai sửa một
   trong hai bên mà quên bên kia thì phép so hỏng, và hỏng lặng lẽ;
2. `7-canh.md` mới vẫn giữ đủ hợp đồng dữ liệu của dây chuyền (khối PACING,
   các chỗ trống, khoá JSON) — lời nhắc hay đến mấy mà thiếu `<<SRT>>` thì
   khâu chia cảnh không chạy.
"""
import os

from core.chia_canh import nhip_tu_khuon
from core.dao_dien_auto import che_do_dao_dien, khuon_du_cho_dao_dien
from core.kenh import doc_kenh, kiem_kenh
from core.noi_canh import la_noi_canh

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Bảy tệp phải trùng kênh đối chứng từng byte — xem docstring.
TEP_PHAI_TRUNG = ("1-tieu-de.md", "2-viet.md", "2b-cham.md", "3-sua.md",
                  "6-seo.md", "8-thumbnail.md", "9-nhac.md")


def _canh() -> str:
    with open(os.path.join(GOC, "CHANNEL", "openstory", "prompt", "7-canh.md"),
              encoding="utf-8") as t:
        return t.read()


def test_kenh_chay_duoc_va_dung_che_do():
    k = doc_kenh(GOC, "openstory")
    assert kiem_kenh(k) == []
    assert k.ngon_ngu == "vi" and k.engine == "veo3"
    assert k.che_do_ke == "tu_xay" and che_do_dao_dien(k) and not la_noi_canh(k)
    assert k.do_dai_tu_do


def test_chi_khac_story_3d_dung_mot_tep():
    """Đổi hai thứ một lúc thì không biết thứ nào làm nên khác biệt."""
    doi = doc_kenh(GOC, "openstory")
    goc = doc_kenh(GOC, "story-3d")
    for ten in TEP_PHAI_TRUNG:
        assert doi.prompt[ten] == goc.prompt[ten], \
            "{0} đã lệch story-3d — phép so không còn một biến".format(ten)
    assert doi.prompt["7-canh.md"] != goc.prompt["7-canh.md"]
    for khoa in ("style", "voice_id", "ngon_ngu", "ky_tu_moi_phut", "engine",
                 "che_do_ke"):
        assert getattr(doi, khoa) == getattr(goc, khoa), khoa


def test_hop_dong_du_lieu_cua_khau_chia_canh():
    chu = _canh()
    assert nhip_tu_khuon(chu) == (3.0, 8.0)
    assert khuon_du_cho_dao_dien(chu)
    for cho in ("<<SRT>>", "<<CLIP_SEC>>", "<<MIN_SEC>>", "<<MAX_SEC>>",
                "<<KHUC_THU>>", "<<TONG_KHUC>>", "<<LA_KHUC_DAU>>",
                "<<TY_LE_KHUNG>>", "<<CAST_STYLE>>", "<<DIRECTOR_PLAN>>",
                "<<CONTEXT>>"):
        assert cho in chu, cho
    for khoa in ("srt_from", "srt_to", "img_prompt", "video_prompt",
                 "narration_vi", "characters_used", "location_used",
                 "primary_subject", "primary_action", "visual_anchor",
                 "must_not_show"):
        assert '"{0}"'.format(khoa) in chu, khoa


def test_mang_du_luat_cua_openstory():
    """Năm luật là lý do kênh này tồn tại — mất luật nào là mất phép so."""
    chu = _canh().lower()
    # ảnh tham chiếu lo nhận dạng, chữ lo thế giới
    assert "60%" in chu and "reference image" in chu
    # khung đầu có thế năng
    # 28/08: viết lại mục 3 — giữ ý "khung đầu phải mang chuyển động",
    # thêm yêu cầu hành động ĐANG diễn ra. Cụm cũ "potential energy"
    # không còn; kiểm bằng cụm mới.
    assert "starting frame" in chu and "weight already shifted" in chu
    # một cảnh = một cú máy, và clip chỉ một cú máy
    assert "one continuous camera take" in chu
    assert "exactly one camera move" in chu and "never stack" in chu
    # clip không nhắc lại thứ ảnh đã có
    assert "never repeat what the picture already shows" in chu
    # cấm chữ hô hào và thông số máy trong lời nhắc clip
    for tu in ("epic", "masterpiece", "24fps"):
        assert tu in chu, tu
    # tiếng: nền + tiếng động, cấm nhạc và cấm lời thoại (đã có giọng đọc riêng)
    assert "ambient:" in chu and "sfx:" in chu
    assert "no music" in chu and "no speech" in chu


def test_phong_ngua_bo_loc_ngay_tu_luc_viet():
    """OpenStory chữa sau khi bị từ chối; ở đây tránh ngay từ lúc viết prompt."""
    chu = _canh().lower()
    for tu in ("anthropomorphic", "sly", "body horror", "copyrighted character"):
        assert tu in chu, tu


def test_moi_nguoi_trong_khung_phai_co_anh():
    """Nhân vật không ai kê tên thì không có ảnh, và máy bịa ra con khác.

    Đo bởi phiên kho-github-77 trên phim hoathinh-3d/0002 (27/08/2026): cảnh 5
    ghi "nv2 and siblings" → bầy dê bốn chân không mặc gì; cảnh 7 ghi "the
    disguised wolf" → sói đội mũ trùm áo trắng; cảnh 8 chỉ hở một cái chân sói
    mà không kê tên → chân trắng toát trong khi sói xám than. Luật chép sang
    đây vì bệnh không thuộc riêng kênh nào.
    """
    chu = _canh().lower()
    assert "even one" in chu and "only half seen" in chu
    assert "the siblings" in chu and "the rest of them" in chu
    assert "disguise" in chu
    # 28/08: BỎ trần "tối đa hai nhân vật". Bảng đo dựng nên nó bị nhiễu —
    # cảnh nhiều ảnh cũng là cảnh nhiều nhân vật, nên nó đo độ khó của bố cục
    # chứ không đo số ảnh. Hạ trần đẩy người bệnh ra khỏi cảnh của chính mình
    # (phim 0007 cảnh 4). Xem ghi chú ở `TOI_DA_NV_THAM_CHIEU`.
    assert "at most two characters" not in chu
    assert "carries their own reference" in chu


def test_moi_noi_goi_tao_clip_deu_truyen_co_ghim_khung_dau():
    """Kênh khai `khung_dau: true` mà một nhánh quên truyền là cờ chết lặng.

    Đo 27/08/2026: phim openstory/0002 bật cờ, nhưng khung đầu clip lệch trung
    bình 37,6/255 so với chính tấm ảnh gửi vào (0/30 clip trùng khít). Làm lại
    đúng một clip có cờ: lệch 3,5. Nguyên nhân: hai trong ba nơi gọi `_lam_clip`
    không truyền `khung_dau`, chỉ đường nối cảnh truyền.
    """
    import re

    with open(os.path.join(GOC, "core", "auto_khau.py"), encoding="utf-8") as t:
        chu = t.read()
    goi = re.findall(r"_lam_clip\((?:[^()]|\([^()]*\))*\)", chu)
    goi = [g for g in goi if not g.startswith("_lam_clip(bc: ")]
    assert len(goi) >= 3, "đổi số nơi gọi thì sửa bài kiểm này"
    thieu = [g for g in goi if "khung_dau" not in g]
    assert not thieu, "nơi gọi quên cờ ghim khung đầu: {0}".format(thieu)


def test_luat_ai_dang_noi():
    """Câu thoại thì người NÓI là chủ thể, câu phản ứng thì người NGHE.

    Kênh `hoathinh-3d` có luật này từ trước; bản viết lại theo lối OpenStory
    của kênh này làm mất nó. Chủ dự án xem phim 0004: *"lúc nhân vật nói
    chuyện với thầy lang thì đang bị ngược là thầy lang nói"*.
    """
    chu = _canh().lower()
    assert "belongs to the speaker" in chu and "belongs to the listener" in chu
    assert "primary_subject" in chu


def test_hanh_dong_phai_DANG_dien_ra():
    """"Sắp sửa" không đủ — trẻ con phải gọi tên được hành động trong ảnh.

    Đo 27/08/2026 (phim 0005 cảnh 9): lời kể "mèo nhảy tót lên thúng", ảnh ra
    con mèo ĐỨNG CẠNH cái thúng trên đất.
    """
    chu = _canh().lower()
    assert "already happening" in chu or "underway" in chu
    assert "in the air" in chu and "not a cat standing beside" in chu


def test_nhan_vat_bi_che_khuat_van_phai_co_moc_nhan_dang():
    """Nhân vật nằm trùm chăn, quay lưng, chìm nước thì máy không có gì để bám.

    Đo 27/08/2026 (phim 0005 cảnh 5): bà nằm ốm chỉ hở đầu → vẽ thành một ông
    già hói mặc nâu, mà bộ chấm vẫn cho 4/5 vì nhân vật KIA khớp ảnh gốc.
    """
    chu = _canh().lower()
    assert "lying, covered or turned away" in chu
    assert "feature that still identifies" in chu   # câu xuống dòng sau "ONE"
    assert "anchor, not a description" in chu   # câu xuống dòng sau "One"


def test_khong_viet_nhan_vat_thanh_mot_cai_xac_vo_danh():
    """Trần 2 nhân vật đẩy người thứ ba thành "a blanketed figure" — và người
    vô danh thì được vẽ thành người lạ.

    Đo 28/08/2026 (phim 0007 cảnh 4): "thầy lang tới xem bệnh" gắn ảnh thầy
    lang + cậu bé, còn BÀ — nhân vật cả cảnh nói về — bị viết thành "a small
    blanketed figure resting out of focus" và ra một người tóc đen lạ hoắc.
    """
    chu = _canh().lower()
    assert "the one who acts and the one acted upon" in chu
    assert "never write a story character as an unnamed body" in chu
    assert "blanketed figure" in chu
    assert "keep them out of the frame entirely" in chu


def test_cam_khung_qua_vai_va_khung_chu_quan():
    """Khung qua vai đặt một cái lưng vô danh vào chỗ to nhất của khung hình.

    Ảnh tham chiếu là chân dung nhìn thẳng. Chỗ nào camera không thấy mặt thì
    máy không có gì để khớp, và nó bịa ra người lạ ngay tại chỗ ấy.

    Đo 28/08/2026 (phim 0008 cảnh 7): "Over-the-shoulder shot from just behind
    nv1's shoulder… looking across to nv4" → cậu bé BIẾN MẤT khỏi ảnh, giữa nhà
    mọc ra một người đàn bà trung niên không có trong truyện, thầy lang còn lại
    cái lưng xanh. Chấm 2/5, vẽ lại bốn lượt, lượt nào cũng hỏng y hệt — lỗi ở
    KHUNG HÌNH nên vẽ lại bao nhiêu lần cũng vô ích.
    """
    chu = _canh()
    assert "**No over-the-shoulder shot, and no POV shot.**" in chu
    assert "Two-shot of" in chu
    # và không còn mời gọi hai lối khung ấy trong bảng chọn cỡ máy
    bang = chu[chu.find("## 6."):chu.find("## 7.")]
    assert "`Over-the-shoulder shot of" not in bang and "`POV of" not in bang


def test_hai_nhan_vat_cung_loai_thi_moi_nguoi_mot_moc():
    """Hai người già trong một khung: máy xoá một người, vẽ người kia hai lần.

    Đo 28/08/2026 (phim 0008 cảnh 7): thầy lang (ông già râu trắng, áo chàm,
    khăn đóng đen) và bà (bà già búi bạc, áo nâu) cùng một phòng. Lời nhắc gọi
    thầy lang KHÔNG kèm mốc nào, còn bà thì có mốc "búi tóc bạc trên chiếu" —
    ảnh ra là **bà đứng ở chỗ thầy lang**, áo nâu y hệt, không có thầy lang.
    """
    chu = _canh()
    assert "## 3c." in chu
    assert "the machine sees several" in chu.lower()
    assert "One feature each." in chu
    # và không được biến thành lời tả ngoại hình — luật 1 vẫn cai
    assert "One feature, never a portrait" in chu


def test_tu_the_phai_kem_LY_DO():
    """Ba người một cái giường: máy tự chọn ai nằm, trừ khi câu nói rõ vì sao.

    Đo 28/08/2026 (phim 0008 cảnh 7, lượt hai): mọi nhân vật khớp ảnh tham
    chiếu, bộ chấm cho 4/5 — nhưng **bà đứng nói còn cậu bé nằm ngủ trên chõng
    bệnh**, ngược hẳn truyện. Ảnh qua được mọi cửa nhận dạng mà vẫn kể sai:
    bộ chấm nhìn mặt, không nhìn vai.
    """
    chu = _canh()
    assert "## 3d." in chu
    assert "say WHY they are in it" in chu
    assert "no two characters" in chu and "share a posture phrase" in chu


def test_vi_du_trong_loi_nhac_khong_duoc_chay_sang_phim_moi():
    """Mọi luật ở đây đều kèm phép đo trên phim CŨ — kèm tên nhân vật phim ấy.

    Kênh này để làm **nhiều** truyện cổ tích, không phải một. Lời nhắc nhắc
    "the cat", "the healer", "the grandmother", "the basket-boat" hàng chục
    lần; không rào lại thì truyện Thạch Sanh cũng mọc ra một con mèo.
    """
    chu = _canh()
    assert "## 0. THE EXAMPLES BELOW ARE NOT YOUR STORY" in chu
    assert "None of that belongs in the film you are writing now" in chu
    assert "The rules are general. The examples are not." in chu
    # Phải đứng TRƯỚC mọi ví dụ, không thì đọc xong mới được dặn.
    assert chu.index("## 0.") < chu.index("## 1. Identity comes from")
