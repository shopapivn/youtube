// Trang chủ YouTube: gom các KÊNH đứng sau video được đề xuất, gửi về trạm.
//
// Logic của chủ dự án (01/09/2026): trang chủ của phiên kênh là nơi YouTube
// đề xuất content cho ĐÚNG tệp khán giả ấy — "cái đuôi để nắm không phải
// content mà là đối thủ: nắm được hết đối thủ là nắm được hết content".
// Nên ở đây không lấy video; lấy CHỦ của video, đổ vào sổ đối thủ của kênh
// (trạm nhận qua POST /doi-thu, tự khử trùng lặp).
//
// Chạy MỘT LẦN mỗi lượt mở trang chủ: cuộn vài màn cho YouTube nạp thêm đề
// xuất, gom link kênh, gửi một gói duy nhất rồi thôi — không bám theo dõi,
// không lặp lại. Muốn quét lại thì mở lại trang chủ (agent trên máy ảo làm
// đúng như vậy khi nhận lệnh "quét trang chủ").
(() => {
  if (location.hostname !== 'www.youtube.com') return;
  if (location.pathname !== '/') return;   // chỉ trang chủ — không đụng trang xem

  const gom = () => {
    const ra = new Set();
    document.querySelectorAll('a[href^="/@"], a[href^="/channel/UC"]').forEach((a) => {
      const m = (a.getAttribute('href') || '').match(/^\/(@[\w.\-]+|channel\/UC[\w\-]+)/);
      if (m) ra.add('https://www.youtube.com/' + m[1]);
    });
    return [...ra];
  };

  let buoc = 0;
  const dong_ho = setInterval(() => {
    buoc += 1;
    // Cuộn để YouTube nạp thêm đề xuất — 6 màn là chừng 40–80 video.
    window.scrollBy(0, Math.round(window.innerHeight * 1.5));
    if (buoc < 6) return;
    clearInterval(dong_ho);
    const danh_sach = gom();
    if (danh_sach.length) {
      try {
        chrome.runtime.sendMessage({ type: 'doi_thu', danh_sach, href: location.href });
      } catch (e) {}
    }
    window.scrollTo(0, 0);
  }, 2500);
})();
