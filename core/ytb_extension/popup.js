const $ = (s) => document.querySelector(s);
const send = (m) => new Promise(r => chrome.runtime.sendMessage(m, r));

async function nap() {
  const t = await send({ type: 'trang_thai' });
  if (!t) return;
  if (document.activeElement !== $('#host')) $('#host').value = t.host;
  if (document.activeElement !== $('#ma_kenh')) $('#ma_kenh').value = t.ma_kenh;
  // Bỏ trống ô máy chủ là cách dùng BÌNH THƯỜNG — dữ liệu ghi vào thư mục Tải xuống.
  $('#host_tt').innerHTML = t.luu_may
    ? '<span class="ok">✓ lưu vào máy này</span> — Tải xuống / ' + (t.thu_muc || 'chi-so-youtube')
    : (t.hostOk ? '<span class="ok">✓ kết nối</span>' : '<span class="bad">✗ không tới được → lưu vào Tải xuống</span>');
  $('#kenh').textContent = t.kenh || '(chưa nhận diện — mở Studio)';
  const vs = Object.entries(t.videos).sort((a, b) => b[1].ngay_dang_ms - a[1].ngay_dang_ms);
  $('#videos').textContent = vs.length ? vs.map(([id, v]) => `${id}  ${Math.round((Date.now() - v.ngay_dang_ms) / 36e5)}h  [${(t.daChup[id] || []).join(',')}]  ${(v.tieu_de || '').slice(0, 30)}`).join('\n') : '(chưa có — mở trang Nội dung của Studio)';
  $('#lich').textContent = t.lich.length ? t.lich.filter(l => l.name.startsWith('snap')).map(l => `${l.name.split('|')[1]}@${l.name.split('|')[2]}h ${new Date(l.when).toLocaleString()}`).join(' · ') || 'chỉ có khám phá định kỳ' : 'chưa có';
  $('#ep').textContent = Object.entries(t.endpoints || {}).map(([k, v]) => `${k}: ${v.thay} / ${v.luu}`).join('\n') || '(chưa thấy gì)';
  $('#log').textContent = (t.logs || []).join('\n');
}

$('#luu').onclick = async () => { await send({ type: 'cau_hinh', host: $('#host').value.trim(), ma_kenh: $('#ma_kenh').value.trim() }); nap(); };
$('#kham').onclick = async () => { await send({ type: 'kham_pha' }); setTimeout(nap, 1500); };
$('#quet').onclick = async () => { await send({ type: 'quet_ngay' }); setTimeout(nap, 1500); };
$('#kenhbtn').onclick = async () => { await send({ type: 'chup_kenh' }); setTimeout(nap, 1500); };
$('#xoa').onclick = async () => { await send({ type: 'xoa_lich' }); nap(); };
nap();
setInterval(nap, 3000);
