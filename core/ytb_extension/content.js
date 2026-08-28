// Isolated world: chuyển tiếp capture từ inject.js sang background.
window.addEventListener('message', (e) => {
  if (e.source !== window || !e.data || !e.data.__csk) return;
  try {
    chrome.runtime.sendMessage({ type: 'capture', url: e.data.url, reqBody: e.data.reqBody, resText: e.data.resText, t: e.data.t, href: location.href });
  } catch (err) {}
});
