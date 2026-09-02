// Chạy trong MAIN world của studio.youtube.com: vá fetch/XHR để chép lại request+response
// của các endpoint analytics mà Studio tự gọi. KHÔNG tự gửi request nào.
(() => {
  const TINH = /\.(js|css|png|jpe?g|gif|svg|woff2?|ttf|ico|mp4|webm|webp|m3u8)(\?|$)/i;
  const NHIEU = /log_event|\/att\/|\/ars\/|feedback|notification|get_survey|google_hats|security\/|promotions|communications|check_creator_bulk|generate_204|\/ptracking|\/api\/stats|play\.google|gstatic|fonts\./;
  // đã hiệu chỉnh 26/08: analytics của Studio = youtubei/v1/yta_web/{get_screen,get_cards,join}; danh sách video = creator/{get,list}_creator_videos
  // 02/09: thêm get_channel_dashboard — trang tổng quan Studio gọi nó ngay khi mở, mang
  // chỉ số cấp KÊNH (48h/28 ngày, video đang gánh kênh); trước đây "thấy 2 / lưu 0".
  const MATCH = /youtubei\/v1\/(yta_web\/(get_screen|get_cards|join|csv_export)|creator\/((get|list)_creator_videos|get_video|get_channel_dashboard))/;
  // Thẻ "Hoạt động mới nhất" của trang tổng quan tự gọi lại get_cards mỗi 10 giây và KHÔNG chứa
  // chỉ số nào ta cần (không có keyMetricCardConfig). Một tab để mở qua đêm từng sinh 409 gói /
  // 45 MB toàn thứ này. Bỏ ngay tại nguồn.
  const RAC = (reqBody) => {
    if (!reqBody) return false;
    return reqBody.indexOf('latestActivityCardConfig') >= 0 && reqBody.indexOf('keyMetricCardConfig') < 0;
  };
  const send = (url, reqBody, resText) => {
    if (RAC(reqBody)) return;
    try { window.postMessage({ __csk: true, url, reqBody, resText, t: Date.now() }, '*'); } catch (e) {}
  };
  const of = window.fetch;
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    const res = await of.apply(this, arguments);
    if (MATCH.test(url)) {
      try {
        const body = init && typeof init.body === 'string' ? init.body : null;
        res.clone().text().then(t => send(url, body, t)).catch(() => {});
      } catch (e) {}
    }
    return res;
  };
  const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, url) { this.__csk_url = String(url || ''); return oo.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (body) {
    if (MATCH.test(this.__csk_url)) {
      this.addEventListener('load', () => {
        try {
          let txt;
          const rt = this.responseType;
          if (rt === '' || rt === 'text') txt = this.responseText;
          else if (rt === 'json') txt = JSON.stringify(this.response);
          else if (rt === 'arraybuffer') txt = new TextDecoder().decode(this.response);
          else if (rt === 'blob') { this.response.text().then(t => send(this.__csk_url, typeof body === 'string' ? body : null, t)); return; }
          if (txt) send(this.__csk_url, typeof body === 'string' ? body : null, txt);
        } catch (e) {}
      });
    }
    return os.apply(this, arguments);
  };
})();
