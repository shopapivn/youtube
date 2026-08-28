// Script của trang nghỉ. PHẢI để file riêng — extension MV3 chặn script viết thẳng trong HTML.
function nap() {
  chrome.runtime.sendMessage({ type: 'trang_thai' }, (t) => {
    if (!t) return;
    const $ = (id) => document.getElementById(id);
    // Ba trạng thái, không phải hai: lưu vào máy (bình thường), có máy chủ và tới được,
    // có máy chủ mà không tới được (mới là hỏng).
    $('host').innerHTML = t.luu_may
      ? '<span class="ok">✓ lưu vào máy này</span> Thư mục Tải xuống / ' + (t.thu_muc || 'chi-so-youtube')
      : (t.hostOk
        ? '<span class="ok">✓ kết nối</span> ' + t.host
        : '<span class="bad">✗ không tới được</span> ' + t.host + ' — dữ liệu sẽ lưu vào Tải xuống');
    $('kenh').textContent = t.kenh || '(chưa nhận diện — mở trang Nội dung của Studio một lần)';
    const daChup = t.daChup || {};
    const vs = Object.entries(t.videos || {}).sort((a, b) => b[1].ngay_dang_ms - a[1].ngay_dang_ms);
    $('video').innerHTML = vs.length
      ? vs.map(([id, v]) => `<div>${id} · ${Math.round((Date.now() - v.ngay_dang_ms) / 36e5)}h · đã chụp [${(daChup[id] || []).join(', ') || '—'}]</div>`).join('')
      : '<span class="bad">chưa thấy video nào</span>';
    const snap = (t.lich || []).filter(l => l.name.startsWith('snap')).sort((a, b) => a.when - b.when)[0];
    $('ke').textContent = snap
      ? `${snap.name.split('|')[1]} — mốc ${snap.name.split('|')[2]}h — ${new Date(snap.when).toLocaleString()}`
      : 'không còn mốc nào (mọi mốc đã chụp xong)';
    const nk = t.logs || [];
    const xong = nk.find(l => l.includes('xong '));
    $('lanchup').innerHTML = xong
      ? '<span class="ok">✓ ' + xong + '</span>'
      : '<span class="bad">chưa chụp lần nào từ khi cài</span>';
    $('cuoi').textContent = nk[0] || '(chưa có)';
    $('nk').textContent = nk.slice(0, 12).join('\n');
  });
}
nap();
setInterval(nap, 5000);

// Nút kiểm tra thủ công. Lưu ý: chính tab này sẽ được dùng để mở trang analytics,
// nên trang sẽ đổi rồi quay lại — kết quả xem ở dòng "Lần chụp gần nhất".
document.getElementById('chup').addEventListener('click', () => {
  document.getElementById('tt').textContent = 'đang chụp… tab sẽ mở trang analytics rồi tự quay lại đây (~1 phút)';
  document.getElementById('chup').disabled = true;
  chrome.runtime.sendMessage({ type: 'quet_ngay' });
});