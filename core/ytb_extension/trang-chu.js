// Trang chủ YouTube của phiên kênh: THU NHỎ → LƯỚT TỚI ĐÁY → TẢI LẠI VÀI LƯỢT → GOM HẾT LINK → gửi về tool.
//
// Chủ dự án, 05/09/2026: *"cách cào đơn giản chỉ là mở trang chủ và thu nhỏ để lấy hết link
// về, sau đó chuyển cho bên tool — tool sẽ làm các việc phía sau… cứ lướt kéo xuống cuối thì
// video mới hiện"* và *"quét trang chủ có thể làm một lượt 2–3 lần, mỗi lần load trang chủ
// có thể ra dữ liệu mới"*.
//
// Đúng, và nó sửa các chỗ yếu của bản trước:
//   · v2.4 chỉ gom LINK KÊNH, không video, không tên → về trạm là nối thẳng vào hộp thư không
//     lọc được gì. Hai kênh 雑学 lọt vào sổ đối thủ (150 dòng) đi đúng đường này.
//   · v2.4 cuộn đúng 6 màn rồi thôi (~40–80 video). Trang chủ nạp thêm vô hạn khi kéo tới đáy;
//     thu nhỏ trang thì mỗi lần nạp được nhiều hơn. Đo thật 05/09: một lượt 422 video.
//   · v2.6.0 vớ được tiêu đề chỉ 3% (12/422): thẻ video thường để tiêu đề ở `aria-label` hoặc
//     ở phần tử con `#video-title`, không ở `title`. Sửa cả hai.
//   · Mỗi lần TẢI LẠI trang chủ YouTube xếp một bộ đề xuất khác → gom qua vài lượt (giữ trong
//     sessionStorage, sống qua reload), gửi MỘT gói khi xong.
//
// Trình duyệt KHÔNG phân tích gì. Tool ở nhà có yt-dlp tra tên kênh, tag, tuổi, view, rồi lọc và
// cào. Bám DOM càng ít càng ít hỏng: thứ bắt buộc duy nhất là `a[href]`.
(() => {
  if (location.hostname !== 'www.youtube.com') return;
  if (location.pathname !== '/') return;   // chỉ trang chủ — không đụng trang xem

  const SO_LUOT_TAI = 3;          // tải lại trang chủ bao nhiêu lượt — mỗi lượt một bộ đề xuất khác
  const MAX_LAN_CUON = 60;        // trần cuộn mỗi lượt: không treo mãi
  const DUNG_SAU_KHONG_MOI = 5;   // 5 lần cuộn liền không có link mới = đã tới đáy thật
  const NGHI_MS = 1800;           // đủ cho YouTube nạp trang kế
  const KHO = 'tc_v26';           // khoá sessionStorage (mất khi đóng tab — đúng ý: mỗi lần mở là một lượt quét)

  const goi = (msg) => { try { chrome.runtime.sendMessage(msg); } catch (e) {} };
  const docKho = () => { try { return JSON.parse(sessionStorage.getItem(KHO) || '{}'); } catch (e) { return {}; } };
  const ghiKho = (o) => { try { sessionStorage.setItem(KHO, JSON.stringify(o)); } catch (e) {} };

  const kho = docKho();
  const luot = (kho.luot || 0) + 1;
  const video = new Map(Object.entries(kho.video || {}));   // mã → {…} gom qua các lượt
  const kenh = new Set(kho.kenh || []);

  // Kệ (shelf) mà thẻ đang nằm trong — "急上昇" / "Đang thịnh hành" / "Shorts"… có thì tốt.
  const keCua = (el) => {
    const shelf = el.closest('ytd-rich-shelf-renderer, ytd-rich-section-renderer, ytd-reel-shelf-renderer');
    if (!shelf) return '';
    const t = shelf.querySelector('#title, #title-text, h2');
    return (t && t.textContent || '').trim().slice(0, 60);
  };
  const tieuDeCua = (a, the) => {
    // Thứ tự theo tần suất gặp thật: aria-label của link tiêu đề → title → chữ trong #video-title.
    const al = a.getAttribute('aria-label') || '';
    if ((a.id === 'video-title-link' || a.id === 'video-title') && al) return al;
    const tt = a.getAttribute('title') || '';
    if (tt) return tt;
    const vt = the && the.querySelector('#video-title, yt-formatted-string#video-title, h3');
    return (vt && (vt.getAttribute('title') || vt.textContent) || '').trim();
  };

  const gom = () => {
    let moi = 0;
    document.querySelectorAll('a[href]').forEach((a) => {
      const href = a.getAttribute('href') || '';
      let m = href.match(/^\/watch\?v=([\w-]{11})/) || href.match(/^\/shorts\/([\w-]{11})/);
      if (m) {
        const ma = m[1];
        const short = href.startsWith('/shorts/');
        const the = a.closest('ytd-rich-item-renderer, ytd-rich-grid-media, ytd-video-renderer, ytd-compact-video-renderer, ytd-grid-video-renderer, ytm-shorts-lockup-view-model');
        let v = video.get(ma);
        if (!v) { v = { ma, tieu_de: '', link_kenh: '', ten_kenh: '', ke: '', vi_tri: video.size + 1, luot, short }; video.set(ma, v); moi++; }
        if (!v.tieu_de) { const t = tieuDeCua(a, the); if (t) v.tieu_de = t.slice(0, 200); }
        if (!v.link_kenh && the) {
          const k = the.querySelector('a[href^="/@"], a[href^="/channel/UC"]');
          if (k) {
            const mk = (k.getAttribute('href') || '').match(/^\/(@[\w.\-]+|channel\/UC[\w\-]+)/);
            if (mk) { v.link_kenh = 'https://www.youtube.com/' + mk[1]; v.ten_kenh = (k.textContent || '').trim().slice(0, 80); }
          }
        }
        if (!v.ke && the) v.ke = keCua(the);
        return;
      }
      m = href.match(/^\/(@[\w.\-]+|channel\/UC[\w\-]+)/);
      if (m) kenh.add('https://www.youtube.com/' + m[1]);
    });
    return moi;
  };

  let lan = 0, khongMoi = 0;
  goi({ type: 'zoom', muc: 0.5 });                 // thu nhỏ để mỗi lần nạp được nhiều thẻ hơn
  const dong_ho = setInterval(() => {
    lan += 1;
    const moi = gom();
    khongMoi = moi ? 0 : khongMoi + 1;
    window.scrollTo(0, document.documentElement.scrollHeight);   // kéo thẳng tới đáy → nạp trang kế
    if (lan < MAX_LAN_CUON && khongMoi < DUNG_SAU_KHONG_MOI) return;
    clearInterval(dong_ho);
    gom();                                          // vét lần cuối sau lượt nạp chót

    // Gửi NGAY phần mới của lượt này — không gom tới cuối. Agent máy ảo chỉ chờ ~90 giây rồi có thể
    // đóng Chrome; ba lượt cần 2–5 phút. Gửi theo lượt thì Chrome chết ở lượt 2 vẫn còn lượt 1 ở
    // trạm. Mỗi video/kênh đi đúng MỘT lần trong cả đợt (kho sessionStorage nhớ cái đã gửi).
    const moi_video = [...video.values()].filter(v => v.luot === luot);
    const da_gui = new Set(kho.kenh_da_gui || []);
    const trong_video = new Set(moi_video.map(v => v.link_kenh).filter(Boolean));
    const danh_sach = [...trong_video, ...[...kenh].filter(k => !trong_video.has(k))].filter(k => !da_gui.has(k));
    if (moi_video.length || danh_sach.length) {
      goi({ type: 'trang_chu', video: moi_video, danh_sach, href: location.href,
            so_lan_cuon: lan, luot, so_luot_tai: SO_LUOT_TAI });
    }
    danh_sach.forEach(k => da_gui.add(k));

    if (luot < SO_LUOT_TAI) {
      // Chưa đủ lượt: cất vào sessionStorage rồi TẢI LẠI — trang chủ mới sẽ xếp bộ đề xuất khác,
      // và script này chạy lại từ đầu với kho đã gom (để không gửi trùng).
      ghiKho({ luot, video: Object.fromEntries(video), kenh: [...kenh], kenh_da_gui: [...da_gui] });
      window.scrollTo(0, 0);
      setTimeout(() => location.reload(), 1200);
      return;
    }
    try { sessionStorage.removeItem(KHO); } catch (e) {}
    goi({ type: 'zoom', muc: 1 });
    window.scrollTo(0, 0);
  }, NGHI_MS);
})();
