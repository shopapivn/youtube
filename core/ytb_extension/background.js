// Chỉ số kênh — thu thập analytics YouTube Studio.
//
// NGUYÊN TẮC: MỘT TAB LÀM VIỆC DUY NHẤT, đổi link lần lượt.
// Không mở/đóng tab liên tục (từng gây rò rỉ tab → Chrome hết RAM → tắt),
// không bao giờ đụng tới tab người dùng đang mở.
//
// Mỗi link: đổi URL → tải lại một lần (Studio hay hỏng khi vào thẳng link sâu)
//           → chờ dữ liệu ngừng về → sang link kế tiếp. Xong thì để tab ở about:blank.

// Để trống = lưu thẳng vào thư mục Tải xuống của máy (bản dành cho người dùng thường).
// Điền địa chỉ máy chủ nhận nếu bạn có dựng một cái.
const HOST_MAC_DINH = '';
// Mốc chụp (giờ sau đăng). 72–120h là giai đoạn YouTube quyết định có mở rộng phân phối
// hay không (video 1 bùng impressions đúng ở 72–117h) — thiếu mốc ở đó là mù đúng chỗ cần nhìn.
const MOC = [24, 48, 72, 96, 120, 168, 336, 672];
const captures = {};          // tabId -> {count, last}
const lanTay = {};            // "videoId|endpoint" -> lần ghi cuối từ tab người dùng (chống rác)
let nhanHienTai = null;       // {videoId, label} của lượt đang chạy
let tabLamViec = null;
let dangChay = false;
let logs = [];
let endpoints = {};
let giuThuc = null;
const TRANG_NGHI = chrome.runtime.getURL('nghi.html');

// ---------------------------------------------------------------- tiện ích
const cho = (ms) => new Promise(r => setTimeout(r, ms));
const pad = (n) => String(n).padStart(2, '0');
const stamp = (d = new Date()) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
const log = (m) => { logs.unshift(`${new Date().toLocaleTimeString()} ${m}`); logs = logs.slice(0, 200); chrome.storage.local.set({ logs }); };
const st = async (k, mac = {}) => (await chrome.storage.local.get(k))[k] ?? mac;
const luu = (k, v) => chrome.storage.local.set({ [k]: v });
const b64 = (s) => btoa(unescape(encodeURIComponent(s)));

// service worker MV3 hay bị ngủ giữa chừng → giữ thức trong lúc làm việc
const batGiuThuc = () => { if (!giuThuc) giuThuc = setInterval(() => chrome.runtime.getPlatformInfo(() => {}), 20000); };
const tatGiuThuc = () => { if (giuThuc) { clearInterval(giuThuc); giuThuc = null; } };

const NHIEU = /log_event|\/att\/|\/ars\/|feedback|notification|get_survey|google_hats|security\/|promotions|communications|check_creator_bulk|generate_204|ptracking|\/api\/stats|play\.google|gstatic|fonts\./;
const tenEp = (u) => { try { const x = new URL(u); return (x.host.replace('studio.youtube.com', '') + x.pathname.replace('/youtubei/v1/', '')).replace(/^\//, '').slice(0, 80); } catch (e) { return u.slice(0, 80); } };
const ghiEp = (path, luuDuoc) => { const e = (endpoints[path] = endpoints[path] || { thay: 0, luu: 0 }); luuDuoc ? e.luu++ : e.thay++; chrome.storage.local.set({ endpoints }); };
chrome.webRequest.onCompleted.addListener((d) => { if (!NHIEU.test(d.url)) ghiEp(tenEp(d.url), false); },
  { urls: ['<all_urls>'], types: ['xmlhttprequest'] });

// ---------------------------------------------------------------- tab làm việc (chỉ MỘT)
// Chỉ dùng lại tab nếu nó đúng là tab làm việc của mình (about:blank hoặc Studio).
// Sau khi Chrome khởi động lại, id tab được cấp lại từ đầu nên id cũ có thể trỏ vào tab khác
// của người dùng — điều hướng nhầm sẽ cướp tab đang xem.
async function tabHopLe(id) {
  try {
    const t = await chrome.tabs.get(id);
    const u = t.url || t.pendingUrl || '';
    return u === 'about:blank' || u.startsWith(TRANG_NGHI) || u.startsWith('https://studio.youtube.com/');
  } catch (e) { return false; }
}

// Đóng tab, nhưng KHÔNG BAO GIỜ đóng tab cuối cùng của cửa sổ (đóng nó = Chrome thoát).
async function dongAnToan(id) {
  try {
    const t = await chrome.tabs.get(id);
    const cung = await chrome.tabs.query({ windowId: t.windowId });
    if (cung.length <= 1) { try { await chrome.tabs.update(id, { url: TRANG_NGHI }); } catch (e) {} return; }
    await chrome.tabs.remove(id);
  } catch (e) {}
}

// Tab làm việc được neo theo TRANG NGHỈ (url), không theo id — id đổi khi Chrome/service worker khởi động lại.
// Đồng thời dọn tab analytics còn kẹt từ lượt trước (chỉ tab KHÔNG ai đang xem).
async function layTab() {
  if (tabLamViec != null && await tabHopLe(tabLamViec)) return tabLamViec;
  // Service worker MV3 ngủ giữa chừng làm mất biến nhớ. Đọc lại id đã ghi xuống đĩa trước khi
  // nghĩ tới chuyện mở tab mới — nếu không, mỗi lần worker ngủ lại đẻ thêm một tab Studio.
  const daLuu = await st('tab_lam_viec', null);
  if (daLuu != null && await tabHopLe(daLuu)) { tabLamViec = daLuu; return daLuu; }
  try {
    const nghiTabs = await chrome.tabs.query({ url: TRANG_NGHI + '*' });
    if (nghiTabs.length) {
      await datTab(nghiTabs[0].id);
      for (const t of nghiTabs.slice(1)) await dongAnToan(t.id);
      return tabLamViec;
    }
  } catch (e) {}
  try {
    // Bắt MỌI tab Studio đang nền, không chỉ analytics/*: lượt bị ngắt giữa chừng để tab kẹt
    // ở /videos/upload, và truy vấn cũ không khớp nên tab đó nằm lại vĩnh viễn.
    const ket = await chrome.tabs.query({ url: 'https://studio.youtube.com/*', active: false });
    if (ket.length) {
      await datTab(ket[0].id);
      for (const t of ket.slice(1)) await dongAnToan(t.id);
      if (ket.length > 1) log(`gộp ${ket.length} tab Studio kẹt về 1`);
      return tabLamViec;
    }
  } catch (e) {}
  const t = await chrome.tabs.create({ url: TRANG_NGHI, active: false });
  await datTab(t.id);
  return t.id;
}

async function datTab(id) {
  tabLamViec = id;
  await luu('tab_lam_viec', id);
}

// Đổi link MỘT lần. Chỉ tải lại khi sau 9 giây vẫn chưa có dữ liệu nào (Studio render hỏng).
async function moLink(tabId, url, nhan) {
  nhanHienTai = nhan;
  captures[tabId] = { count: 0, last: 0 };
  try { await chrome.tabs.update(tabId, { url, active: true }); } catch (e) { return 0; }
  const batDau = Date.now();
  let daTaiLai = false;
  while (Date.now() - batDau < 30000) {
    await cho(500);
    const c = captures[tabId] || { count: 0, last: 0 };
    if (c.count > 0 && Date.now() - c.last > 4000) break;          // dữ liệu đã ngừng về → xong
    if (!daTaiLai && c.count === 0 && Date.now() - batDau > 9000) { // chưa có gì → tải lại đúng 1 lần
      daTaiLai = true;
      log('trang chưa có dữ liệu → tải lại');
      try { await chrome.tabs.reload(tabId, { bypassCache: true }); } catch (e) {}
    }
  }
  return (captures[tabId] || {}).count || 0;
}

// Bấm nút "Xuất → .csv" của chính Studio (mọi ngôn ngữ đều có chữ .csv).
async function xuatCSV(tabId) {
  try {
    const r = await chrome.scripting.executeScript({ target: { tabId }, func: async () => {
      const cho = (ms) => new Promise(r => setTimeout(r, ms));
      const moiNode = () => { const ra = []; const sau = (root) => { for (const e of root.querySelectorAll('*')) { ra.push(e); if (e.shadowRoot) sau(e.shadowRoot); } }; sau(document); return ra; };
      const btn = moiNode().find(e => e.id === 'export-button');
      if (!btn) return 'không thấy nút xuất';
      btn.click();
      // Menu của Studio mở CHẬM hơn 1,2 giây (đo trực tiếp: 1,2s chưa có gì, 2s đã đủ 9 mục),
      // nên chờ một khoảng cứng rồi bỏ cuộc là hỏng — nhật ký đầy "không thấy mục csv" trong khi
      // menu vẫn mở ra bình thường ngay sau đó. Chờ tới khi menu thật sự hiện.
      // Mục cần bấm mang tên đầy đủ theo ngôn ngữ giao diện, ví dụ tiếng Việt:
      // "Giá trị được phân tách bằng dấu phẩy (.csv)" — mọi ngôn ngữ đều có phần "(.csv)".
      let csv = null;
      for (let i = 0; i < 20 && !csv; i++) {
        await cho(500);
        const items = moiNode().filter(e => (e.tagName === 'TP-YT-PAPER-ITEM' || e.getAttribute('role') === 'menuitem') && e.offsetParent !== null);
        csv = items.find(e => /\.csv/i.test(e.innerText || ''));
      }
      if (!csv) { document.body.click(); return 'không thấy mục csv'; }
      csv.click(); return 'đã bấm csv';
    } });
    return r && r[0] && r[0].result;
  } catch (e) { return 'lỗi: ' + e.message; }
}

// ---------------------------------------------------------------- nhận capture
function duyet(o, f) { if (o && typeof o === 'object') { f(o); for (const k in o) duyet(o[k], f); } }

async function nhanDienVideo(res, ep) {
  // CHỈ nhận video của kênh mình: trang "chế độ nâng cao" cũng tra tiêu đề video NGUỒN ĐỀ XUẤT
  // (kênh người khác) — nhận nhầm sẽ mở analytics video không sở hữu và Studio báo lỗi.
  const kenh = await st('kenh', '');
  const tuDanhSach = /list_creator_videos/.test(ep || '');
  const videos = await st('videos', {});
  const cuaMinh = new Set();
  let moi = 0;
  duyet(res, (d) => {
    const id = d.videoId;
    if (typeof id !== 'string' || !/^[\w-]{11}$/.test(id)) return;
    const ts = Number(d.timePublishedSeconds || d.publishedTimestamp || d.timeCreatedSeconds || 0);
    if (!ts) return;
    const ch = d.channelId || (d.metadata && d.metadata.channelId) || '';
    if (kenh ? ch !== kenh : !(tuDanhSach && !ch)) return;
    cuaMinh.add(id);
    const v = videos[id] || {};
    if (!videos[id]) moi++;
    videos[id] = {
      tieu_de: d.title || v.tieu_de || '',
      ngay_dang_ms: ts * 1000,
      dai_giay: Number(d.lengthSeconds || v.dai_giay || 0),
      kenh: ch || kenh,
      phat_hien: v.phat_hien || Date.now(),
    };
  });
  if (kenh && tuDanhSach && cuaMinh.size) {
    for (const id of Object.keys(videos)) {
      if (!cuaMinh.has(id)) {
        delete videos[id];
        await chrome.alarms.clear(`ngay|${id}`);
        for (const h of MOC) await chrome.alarms.clear(`snap|${id}|${h}`);
        log(`bỏ video lạ ${id}`);
      }
    }
  }
  await luu('videos', videos);
  if (moi) { log(`thấy ${moi} video mới (tổng ${Object.keys(videos).length})`); await datLich(); }
}

async function luuCapture(msg, sender) {
  const tabId = sender.tab && sender.tab.id;
  const ch = (msg.href.match(/\/channel\/(UC[\w-]+)/) || [])[1];
  if (ch) { const cu = await st('kenh', ''); if (cu !== ch) { await luu('kenh', ch); log(`kênh: ${ch}`); } }
  const kenh = (await st('ma_kenh', '')) || (await st('kenh', '')) || 'kenh';
  const vid = (msg.href.match(/\/video\/([\w-]{11})\//) || [])[1] || 'kenh';
  const tab = (msg.href.match(/\/(tab-[a-z_]+)/) || [])[1] || 'tab';
  const ep = tenEp(msg.url).replace(/[^\w.-]+/g, '-').replace(/^-|-$/g, '') || 'ep';
  const laLuotChup = tabId === tabLamViec && nhanHienTai;
  const lb = laLuotChup ? nhanHienTai.label : `tay-${stamp().slice(0, 8)}`;

  // Tab Studio người dùng để mở vẫn tự gọi lại API (thẻ "Hoạt động mới nhất" làm mới mỗi 10 giây).
  // Không chặn hẳn — bản chụp tình cờ đó từng là nguồn số duy nhất của một mốc — nhưng mỗi
  // (video, endpoint) chỉ giữ 1 lần / 5 phút, nếu không một tab mở qua đêm sinh hàng trăm MB rác.
  if (!laLuotChup) {
    const k = `${vid}|${ep}`;
    if (Date.now() - (lanTay[k] || 0) < 300000) return;
    lanTay[k] = Date.now();
  }

  let req = null, res = null;
  try { req = msg.reqBody ? JSON.parse(msg.reqBody) : null; } catch (e) {}
  try { res = JSON.parse(msg.resText); } catch (e) { res = { _raw: msg.resText }; }
  if (/creator_videos|get_video/.test(ep)) nhanDienVideo(res, ep).catch(() => {});

  const c = (captures[tabId] = captures[tabId] || { count: 0, last: 0 });
  c.count += 1; c.last = Date.now();
  const ten = `${stamp()}_${tab}_${ep}_${c.count}.json`;
  const goi = { captured_at: new Date().toISOString(), href: msg.href, url: msg.url, request: req, response: res };
  await luuGoi(kenh, vid, lb, ten, goi, msg.resText.length);
  ghiEp(tenEp(msg.url), true);
}

// Lưu một gói: có địa chỉ máy chủ thì gửi về đó, không thì ghi thẳng vào thư mục Tải xuống.
// Bản dành cho người dùng thường KHÔNG cấu hình máy chủ — extension Chrome chỉ được phép ghi
// vào Tải xuống, nên đó là chỗ dữ liệu nằm, và công cụ sẽ đọc từ đúng chỗ ấy.
async function luuGoi(kenh, vid, nhan, ten, goi, cỡ = 0, im = false) {
  const host = await st('host', '');
  if (host) {
    try {
      const r = await fetch(host + '/capture', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kenh, id: vid, label: nhan, ten, goi }) });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      if (!im) log(`→host ${vid}/${nhan} ${ten.slice(0, 28)} (${Math.round(cỡ / 1024)} KB)`);
      return true;
    } catch (e) { log(`máy chủ lỗi (${e.message}) → lưu vào Tải xuống`); }
  }
  try {
    const thu_muc = await st('thu_muc', 'chi-so-youtube');
    await chrome.downloads.download({ url: 'data:application/json;base64,' + b64(JSON.stringify(goi)),
      filename: `${thu_muc}/${kenh}/${vid}/${nhan}/${ten}`, conflictAction: 'uniquify', saveAs: false });
    if (!im) log(`↓ đã lưu ${vid}/${nhan} (${Math.round(cỡ / 1024)} KB)`);
    return true;
  } catch (e) { log(`LỖI lưu: ${e.message}`); return false; }
}

// ---------------------------------------------------------------- các lượt chụp
const CHI_SO = 't_metrics=VIDEO_THUMBNAIL_IMPRESSIONS&t_metrics=VIDEO_THUMBNAIL_IMPRESSIONS_VTR&t_metrics=EXTERNAL_VIEWS&t_metrics=AVERAGE_WATCH_TIME&t_metrics=EXTERNAL_WATCH_TIME';
const kho = (id, chieu, them = '') =>
  `https://studio.youtube.com/video/${id}/analytics/tab-reach_viewers/period-default/explore?entity_type=VIDEO&entity_id=${id}${them}&time_period=lifetime&explore_type=TABLE_AND_CHART&metric=EXTERNAL_VIEWS&granularity=DAY&${CHI_SO}&dimension=${chieu}&o_column=VIDEO_THUMBNAIL_IMPRESSIONS&o_direction=ANALYTICS_ORDER_DIRECTION_DESC`;
// Sắp theo IMPRESSIONS, không phải views. Bảng tải dần khi cuộn và Xuất→.csv chỉ lấy phần đã tải,
// nên thứ tự quyết định phần nào lọt vào file. Sắp theo views thì phần đầu là mấy chục nguồn có
// view, còn impressions lại nằm rải ở hàng trăm nguồn 0-view phía sau: video 2 xuất ra 40 nguồn
// mà chỉ phủ 5,7% tổng impressions. Sắp theo impressions thì dù chỉ lấy được phần đầu, đó cũng
// là phần chiếm nhiều impressions nhất — độ phủ cao nhất có thể với cùng số dòng.

// [url, có xuất CSV không]
// [url, có xuất CSV không]
const LINK_VIDEO = (id) => [
  [`https://studio.youtube.com/video/${id}/analytics/tab-overview/period-since_publish`, false],
  [kho(id, 'TRAFFIC_SOURCE_DETAIL', '&ddr_dimension=TRAFFIC_SOURCE_TYPE&ddr_value=YT_RELATED'), true],  // pool đề xuất
  [kho(id, 'COUNTRY'), true],                                                                            // vùng đầy đủ
];

async function nghi(tabId) {
  nhanHienTai = null;
  try { await chrome.tabs.update(tabId, { url: TRANG_NGHI, active: false }); } catch (e) {}
}

async function chupVideo(videoId, label, ep = false) {
  const kenh = await st('kenh', '');
  const v = (await st('videos', {}))[videoId];
  // Cùng một mốc từng bị chụp 2–3 lần trong vài phút (lịch chồng lên thao tác tay, hoặc bấm
  // "Chụp ngay" nhiều lần): mỗi lượt mất gần một phút và chỉ ghi đè lên chính nó. Đã chụp mốc
  // nào thì thôi mốc đó, trừ khi người dùng chủ động ép chụp lại.
  if (!ep && ((await st('daChup', {}))[videoId] || []).includes(label)) {
    log(`bỏ qua ${videoId} [${label}]: đã chụp mốc này rồi`);
    return 0;
  }
  if (!v || (kenh && v.kenh && v.kenh !== kenh)) {
    log(`bỏ ${videoId}: không thuộc kênh`);
    const videos = await st('videos', {}); delete videos[videoId]; await luu('videos', videos);
    return 0;
  }
  while (dangChay) await cho(3000);
  dangChay = true; batGiuThuc();
  try {
    const tabId = await layTab();
    log(`chụp ${videoId} [${label}]`);
    let tong = 0;
    for (const [url, canCSV] of LINK_VIDEO(videoId)) {
      tong += await moLink(tabId, url, { videoId, label });
      if (canCSV) { log(`xuất csv: ${await xuatCSV(tabId)}`); await cho(4000); }
    }
    await nghi(tabId);
    const gio = v.ngay_dang_ms ? Math.round((Date.now() - v.ngay_dang_ms) / 36e5) : null;
    const xong = { kenh: (await st('ma_kenh', '')) || kenh || 'kenh', id: videoId, label,
      tieu_de: v.tieu_de || '', thoi_luong: v.dai_giay || null, gio,
      ngay_dang: v.ngay_dang_ms ? new Date(v.ngay_dang_ms).toISOString() : null };
    const host = await st('host', '');
    if (host) {
      try {
        await fetch(host + '/done', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(xong) });
      } catch (e) {}
    } else {
      // Không có máy chủ nhận: mấy thông tin này (tiêu đề, thời lượng, mốc giờ) không nằm
      // trong gói nào của Studio, nên phải ghi thành một tệp riêng — thiếu nó thì bản chụp
      // vẫn đọc được nhưng không biết là của video nào, dài bao nhiêu, ở mốc mấy giờ.
      await luuGoi(xong.kenh, videoId, label, '_thong-tin.json', xong, 0, true);
    }
    const daChup = await st('daChup', {});
    (daChup[videoId] = daChup[videoId] || []).push(label);
    await luu('daChup', daChup);
    log(`xong ${videoId} [${label}]: ${tong} gói`);
    return tong;
  } finally { dangChay = false; tatGiuThuc(); }
}

async function chupKenh() {
  const ch = await st('kenh', '');
  if (!ch) return;
  while (dangChay) await cho(3000);
  dangChay = true; batGiuThuc();
  try {
    const tabId = await layTab();
    const label = `kenh-${stamp().slice(0, 8)}`;
    log(`chụp kênh ${ch}`);
    for (const tab of ['tab-overview', 'tab-content', 'tab-build_audience']) {
      await moLink(tabId, `https://studio.youtube.com/channel/${ch}/analytics/${tab}/period-default`, { videoId: 'kenh', label });
    }
    await nghi(tabId);
  } finally { dangChay = false; tatGiuThuc(); }
}

async function khamPha() {
  while (dangChay) await cho(3000);
  dangChay = true; batGiuThuc();
  try {
    const tabId = await layTab();
    let ch = await st('kenh', '');
    if (!ch) {
      // Chưa biết mã kênh (máy mới, hoặc vừa xoá bộ nhớ): mở trang gốc để Studio tự chuyển hướng
      // sang /channel/<UC…>. Mã kênh trước đây CHỈ được nhặt từ href của các gói bắt được — nhưng
      // trang gốc gần như không gọi API nào, nên không có gói, nên không bao giờ có mã kênh, và
      // khamPha lặp lại mãi trang gốc: "trang chưa có dữ liệu → tải lại → chưa thấy video".
      // Đọc thẳng từ URL của tab sau khi chuyển hướng.
      log('chưa biết kênh — mở Studio để nhận diện');
      await moLink(tabId, 'https://studio.youtube.com/', null);
      for (let i = 0; i < 15 && !ch; i++) {
        try { ch = ((await chrome.tabs.get(tabId)).url.match(/\/channel\/(UC[\w-]+)/) || [])[1] || ''; } catch (e) {}
        if (!ch) await cho(1000);
      }
      if (ch) { await luu('kenh', ch); log(`kênh: ${ch}`); }
    }
    if (!ch) { await nghi(tabId); return; }
    log('tìm video từ trang Nội dung');
    await moLink(tabId, `https://studio.youtube.com/channel/${ch}/videos/upload`, null);
    await nghi(tabId);
  } finally { dangChay = false; tatGiuThuc(); }
}

// ---------------------------------------------------------------- lịch
let lanKhamPha = 0;
async function datLich() {
  const videos = await st('videos', {});
  if (!Object.keys(videos).length) {
    if (Date.now() - lanKhamPha > 60000) {
      lanKhamPha = Date.now();
      await khamPha();
      if (Object.keys(await st('videos', {})).length) return datLich();
      log('chưa thấy video — kiểm tra đã đăng nhập Studio đúng kênh chưa');
    }
    return;
  }
  const daChup = await st('daChup', {});
  const co = new Set((await chrome.alarms.getAll()).map(a => a.name));
  let n = 0;
  for (const [id, v] of Object.entries(videos)) {
    const tuoi = (Date.now() - v.ngay_dang_ms) / 36e5;
    for (const h of MOC) {
      if (tuoi > 24 * 35) break;
      const ten = `snap|${id}|${h}`;
      if (co.has(ten) || (daChup[id] || []).includes(`${h}h`)) continue;
      const khi = v.ngay_dang_ms + h * 36e5;
      if (khi > Date.now()) { await chrome.alarms.create(ten, { when: khi }); co.add(ten); n++; }
    }
    if (!(daChup[id] || []).length && !co.has(`ngay|${id}`)) {
      await chrome.alarms.create(`ngay|${id}`, { when: Date.now() + 5000 });
      co.add(`ngay|${id}`);
    }
  }
  if (!co.has('kham-pha')) await chrome.alarms.create('kham-pha', { periodInMinutes: 720 });
  if (!co.has('tu-kiem')) await chrome.alarms.create('tu-kiem', { periodInMinutes: 30 });
  if (!co.has('kenh')) await chrome.alarms.create('kenh', { when: Date.now() + 6 * 3600e3, periodInMinutes: 7 * 24 * 60 });
  if (n) log(`đặt thêm ${n} lịch`);
}

chrome.alarms.onAlarm.addListener(async (a) => {
  const [k, id, h] = a.name.split('|');
  if (k === 'snap') await chupVideo(id, `${h}h`);
  else if (k === 'ngay') {
    const v = (await st('videos', {}))[id];
    await chupVideo(id, `${v ? Math.round((Date.now() - v.ngay_dang_ms) / 36e5) : 0}h`);
  } else if (k === 'kham-pha') await khamPha();
  else if (k === 'kenh') await chupKenh();
  else if (k === 'tu-kiem') await datLich();
});

chrome.runtime.onInstalled.addListener(async () => {
  const v = chrome.runtime.getManifest().version;
  const cu = await st('phien_ban', '');
  if (cu !== v) {
    await chrome.alarms.clearAll();
    await luu('videos', {});
    await luu('phien_ban', v);
    log(`nâng cấp ${cu || '—'} → ${v}`);
  }
  datLich();
});
chrome.runtime.onStartup.addListener(() => datLich());

// ---------------------------------------------------------------- popup
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  (async () => {
    if (msg.type === 'capture') { await luuCapture(msg, sender); reply({ ok: true }); }
    else if (msg.type === 'trang_thai') {
      let hostOk = false;
      const host = await st('host', HOST_MAC_DINH);
      // Không có địa chỉ máy chủ là chuyện BÌNH THƯỜNG, không phải hỏng: dữ liệu ghi thẳng
      // vào thư mục Tải xuống. Trạng thái phải nói đúng thế, chứ hiện "✗ không tới được"
      // sẽ làm người dùng tưởng hỏng và đi sửa một thứ vốn không cần có.
      if (host) { try { hostOk = (await fetch(host + '/')).ok; } catch (e) {} }
      reply({ host, hostOk, luu_may: !host, thu_muc: await st('thu_muc', 'chi-so-youtube'),
        kenh: await st('kenh', ''), ma_kenh: await st('ma_kenh', ''),
        videos: await st('videos', {}), daChup: await st('daChup', {}),
        lich: (await chrome.alarms.getAll()).map(a => ({ name: a.name, when: a.scheduledTime })),
        endpoints, logs: logs.slice(0, 30) });
    }
    else if (msg.type === 'cau_hinh') {
      await luu('host', msg.host || '');
      await luu('ma_kenh', msg.ma_kenh || '');
      if (msg.thu_muc !== undefined) await luu('thu_muc', msg.thu_muc || 'chi-so-youtube');
      reply({ ok: true });
    }
    else if (msg.type === 'quet_ngay') {
      if (!Object.keys(await st('videos', {})).length) await khamPha();
      const videos = await st('videos', {});
      for (const id of (msg.ids && msg.ids.length ? msg.ids : Object.keys(videos))) {
        const v = videos[id];
        // Bấm nút là chủ động muốn chụp lại → cho ép, kể cả mốc đã có.
        await chupVideo(id, `${v ? Math.round((Date.now() - v.ngay_dang_ms) / 36e5) : 0}h`, true);
      }
      reply({ ok: true });
    }
    else if (msg.type === 'kham_pha') { khamPha(); reply({ ok: true }); }
    else if (msg.type === 'chup_kenh') { chupKenh(); reply({ ok: true }); }
    else if (msg.type === 'xoa_lich') {
      await chrome.alarms.clearAll(); await luu('daChup', {});
      log('xoá lịch sử chụp, đặt lại lịch');
      if (!Object.keys(await st('videos', {})).length) { lanKhamPha = 0; await khamPha(); }
      await datLich(); reply({ ok: true });
    }
    else reply({});
  })();
  return true;
});
