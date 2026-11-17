/* Cloud Portal: 9 server + dang nhap Keycloak + kho tai lieu MinIO */
(function () {
  'use strict';

  const API = '/api';
  const H = location.hostname;
  const PROTO = location.protocol === 'https:' ? 'https:' : 'http:';
  const $ = (id) => document.getElementById(id);

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));

  const fmtSize = (n) => {
    if (n == null) return '';
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(0) + ' KB';
    return (n / 1024 / 1024).toFixed(1) + ' MB';
  };

  const protoUrl = (port, path) =>
    `${PROTO}//${H}${Number(port) === 80 ? '' : ':' + port}${path || '/'}`;

  /* ---------------- toast ---------------- */
  function toast(msg, kind, code) {
    const box = $('toasts');
    if (!box) return;
    const el = document.createElement('div');
    el.className = 'toast' + (kind === 'err' ? ' err' : '');
    el.innerHTML = esc(msg) + (code ? `<code>${esc(code)}</code>` : '');
    box.appendChild(el);
    setTimeout(() => el.remove(), kind === 'err' ? 9000 : 5200);
  }

  async function getJSON(url, opts) {
    const res = await fetch(url, Object.assign({ cache: 'no-store' }, opts));
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.error || 'HTTP ' + res.status);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  /* ---------------- dang nhap ---------------- */
  let ME = { authenticated: false, is_admin: false, username: '', roles: [] };

  function renderAuth() {
    const box = $('authArea');
    if (!box) return;
    if (ME.authenticated) {
      box.innerHTML = `
        <span class="who"><span class="dot up"></span>${esc(ME.username)}</span>
        <span class="role ${ME.is_admin ? 'admin' : ''}">${ME.is_admin ? 'admin' : 'viewer'}</span>
        <button class="link-btn" id="logoutBtn" type="button">Đăng xuất</button>`;
      $('logoutBtn').onclick = logout;
    } else {
      const next = encodeURIComponent(location.pathname + location.hash);
      box.innerHTML = `<a class="login-btn" href="/api/session/login?next=${next}">Đăng nhập</a>`;
    }
    renderStorageRole();
  }

  async function loadMe() {
    try {
      ME = await getJSON(API + '/session/me');
    } catch (e) {
      ME = { authenticated: false, is_admin: false, username: '', roles: [] };
    }
    renderAuth();
    renderUploadZone();
    return ME;
  }

  async function logout() {
    try {
      const d = await getJSON(API + '/session/logout', { method: 'POST' });
      location.href = d.logout_url || '/';
    } catch (e) {
      location.href = '/';
    }
  }

  /* ---------------- 9 server ---------------- */
  let services = [];

  function svcCard(s) {
    const dot = `<span class="dot ${s.status === 'up' ? 'up' : 'down'}"></span>`;
    const portTag = `<span class="port">:${s.port}</span>`;
    const meta = `<p class="meta">${esc(s.container)}<br>${esc(s.detail)}</p>`;
    if (s.has_ui) {
      const href = protoUrl(s.open_port, s.open_path);
      return `<a class="svc-card ${s.status === 'up' ? '' : 'is-down'}"
                 href="${esc(href)}" target="_blank" rel="noopener"
                 title="Mở ${esc(s.name)} trong tab mới">
        <div class="row1">${dot}<h3>${esc(s.name)}</h3><span class="open-mark">↗</span></div>
        ${meta}${portTag}
      </a>`;
    }
    return `<div class="svc-card is-off ${s.status === 'up' ? '' : 'is-down'}"
                 data-hint="${esc(s.hint || '')}" role="button" tabindex="0">
      <div class="row1">${dot}<h3>${esc(s.name)}</h3><span class="open-mark">i</span></div>
      ${meta}${portTag}
    </div>`;
  }

  function renderServices() {
    const grid = $('svcGrid');
    if (!grid) return;
    grid.innerHTML = services.map(svcCard).join('');
    grid.querySelectorAll('[data-hint]').forEach((el) => {
      const show = () => toast(services.find((x) => x.hint === el.dataset.hint)?.name +
        ' không có giao diện web.', 'info', el.dataset.hint);
      el.addEventListener('click', show);
      el.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); show(); } });
    });
  }

  async function loadServices() {
    const btn = $('svcRefresh');
    if (btn) btn.disabled = true;
    try {
      const d = await getJSON(API + '/services');
      services = d.services;
      renderServices();
      const sum = $('svcSummary');
      if (sum) {
        sum.innerHTML = `<span class="${d.up === d.count ? '' : 'down'}">${d.up}/${d.count}</span> đang chạy · cập nhật ${esc(d.checked_at)}`;
      }
    } catch (e) {
      const sum = $('svcSummary');
      if (sum) sum.textContent = 'Không tải được trạng thái: ' + e.message;
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  /* ---------------- kho tai lieu ---------------- */
  let docs = { images: [], documents: [] };

  function renderStorageRole() {
    const el = $('storageRole');
    if (!el) return;
    el.textContent = ME.authenticated
      ? (ME.is_admin ? 'Bạn là admin — được upload và xoá.' : 'Bạn là viewer — chỉ xem và tải.')
      : 'Đăng nhập admin để upload hoặc xoá.';
  }

  function renderUploadZone() {
    const zone = $('uploadZone');
    if (!zone) return;
    zone.classList.toggle('locked', !ME.is_admin);
  }

  function renderFiles() {
    const imgBox = $('imgList');
    const pdfBox = $('pdfList');

    if (imgBox) {
      imgBox.innerHTML = docs.images.length ? docs.images.map((f) => `
        <div class="file-item">
          <img src="${esc(f.url)}" alt="" loading="lazy">
          <div class="file-info"><b>${esc(f.name)}</b><span>${fmtSize(f.size)} · ${esc(f.last_modified)}</span></div>
          <div class="file-actions">
            <a class="mini-btn" href="${esc(f.url)}" target="_blank" rel="noopener">Xem</a>
            ${ME.is_admin ? `<button class="mini-btn danger" data-del="images" data-name="${esc(f.name)}" type="button">Xoá</button>` : ''}
          </div>
        </div>`).join('') : '<div class="file-empty">Chưa có ảnh nào.</div>';
    }

    if (pdfBox) {
      pdfBox.innerHTML = docs.documents.length ? docs.documents.map((f) => `
        <div class="file-item">
          <div class="file-thumb">PDF</div>
          <div class="file-info"><b>${esc(f.name.replace(/^[0-9a-f]{8}_/, ''))}</b><span>${fmtSize(f.size)} · ${esc(f.last_modified)}</span></div>
          <div class="file-actions">
            <a class="mini-btn" href="${API}/files/documents/${encodeURIComponent(f.name)}/download">Tải</a>
            ${ME.is_admin ? `<button class="mini-btn danger" data-del="documents" data-name="${esc(f.name)}" type="button">Xoá</button>` : ''}
          </div>
        </div>`).join('') : '<div class="file-empty">Chưa có tài liệu PDF.</div>';
    }
  }

  async function loadFiles() {
    try {
      const [a, b] = await Promise.all([
        getJSON(API + '/files/images'),
        getJSON(API + '/files/documents'),
      ]);
      docs.images = a.files || [];
      docs.documents = b.files || [];
    } catch (e) {
      docs = { images: [], documents: [] };
      toast('Không tải được kho tài liệu: ' + e.message, 'err');
    }
    renderFiles();
  }

  async function uploadFile(file) {
    if (!file) return;
    if (!ME.is_admin) {
      toast('Cần đăng nhập tài khoản admin để upload.', 'err');
      return;
    }
    const fd = new FormData();
    fd.append('file', file);
    try {
      await getJSON(API + '/files/upload', { method: 'POST', body: fd });
      toast('Đã upload: ' + file.name);
      await loadFiles();
    } catch (e) {
      if (e.status === 401) toast('Chưa đăng nhập — hãy đăng nhập admin.', 'err');
      else if (e.status === 403) toast('Chỉ admin được upload.', 'err');
      else toast('Upload lỗi: ' + e.message, 'err');
    }
  }

  function wireStorage() {
    const zone = $('uploadZone');
    const input = $('fileInput');
    if (!zone || !input) return;

    zone.addEventListener('click', () => input.click());
    input.addEventListener('change', () => { uploadFile(input.files[0]); input.value = ''; });
    ['dragenter', 'dragover'].forEach((ev) => zone.addEventListener(ev, (e) => {
      e.preventDefault(); zone.classList.add('drag');
    }));
    ['dragleave', 'drop'].forEach((ev) => zone.addEventListener(ev, (e) => {
      e.preventDefault(); zone.classList.remove('drag');
    }));
    zone.addEventListener('drop', (e) => uploadFile(e.dataTransfer.files[0]));

    document.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-del]');
      if (!btn) return;
      if (!confirm('Xoá file "' + btn.dataset.name + '"?')) return;
      try {
        await getJSON(`${API}/files/${btn.dataset.del}/${encodeURIComponent(btn.dataset.name)}`,
          { method: 'DELETE' });
        toast('Đã xoá file.');
        await loadFiles();
      } catch (err) {
        toast(err.status === 403 ? 'Chỉ admin được xoá.' : 'Xoá lỗi: ' + err.message, 'err');
      }
    });
  }

  /* ---------------- khoi dong ---------------- */
  async function boot() {
    wireStorage();
    const btn = $('svcRefresh');
    if (btn) btn.onclick = loadServices;

    await loadMe();
    await Promise.all([loadServices(), loadFiles()]);

    setInterval(loadServices, 15000);

    const q = new URLSearchParams(location.search);
    if (q.get('login') === 'ok') toast('Đăng nhập thành công.');
    if (q.get('login') === 'error') toast('Đăng nhập thất bại, thử lại.', 'err');
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
