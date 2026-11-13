/** Shared UI for public home and authenticated workspace. */
(() => {
  'use strict';
  const app = window.CloudDS = window.CloudDS || {};
  const $ = (selector, base = document) => base.querySelector(selector);
  const el = (tag, className, text) => {
    const node = document.createElement(tag); if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text); return node;
  };
  const fmtBytes = bytes => {
    if (!Number.isFinite(Number(bytes)) || Number(bytes) < 0) return '—';
    const size = Number(bytes); if (size < 1024) return `${size} B`;
    const unit = Math.min(Math.floor(Math.log(size) / Math.log(1024)), 4);
    return `${(size / Math.pow(1024, unit)).toLocaleString('vi-VN', { maximumFractionDigits: 1 })} ${['B','KB','MB','GB','TB'][unit]}`;
  };
  const fmtPrice = value => Number.isFinite(Number(value)) ? Number(value).toLocaleString('vi-VN') + 'đ' : '—';
  const fmtDate = value => {
    if (!value) return '—'; const d = new Date(value); return Number.isNaN(d.getTime()) ? '—' : new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(d);
  };
  const svg = name => { const s = document.createElementNS('http://www.w3.org/2000/svg','svg'); s.setAttribute('class','icon'); s.setAttribute('aria-hidden','true'); const u = document.createElementNS('http://www.w3.org/2000/svg','use'); u.setAttribute('href',`#icon-${name}`); s.append(u); return s; };
  const isPreview = new URLSearchParams(window.location.search).get('preview') === '1';
  function notice(message, type = 'danger', selector = '#global-notice') {
    const output = $(selector); if (!output) return;
    output.textContent = message; output.className = `alert alert-${type}`; output.hidden = !message;
  }
  function toast(message) {
    const node = $('#toast'); if (!node) { notice(message); return; }
    $('#toast-message').textContent = message; node.hidden = false;
    clearTimeout(toast.timeout); toast.timeout = setTimeout(() => { node.hidden = true; }, 5000);
  }
  function errorMessage(error) { return error?.message || 'Không thể hoàn tất thao tác. Vui lòng thử lại.'; }
  function updateQuota(storage = {}, planName = '—') {
    const used = Number(storage.used_bytes) || 0, quota = Number(storage.quota_bytes) || 0;
    const pct = quota > 0 ? Math.min(100, used / quota * 100) : 0;
    const meter = $('#quota-meter'); if (meter) meter.setAttribute('aria-valuenow', String(Math.round(pct)));
    if ($('#quota-bar')) $('#quota-bar').style.width = `${pct}%`;
    if ($('#quota-label')) $('#quota-label').textContent = quota ? `${fmtBytes(used)} / ${fmtBytes(quota)} đã dùng` : 'Chưa có thông tin dung lượng';
    if ($('#plan-name')) $('#plan-name').textContent = (planName || 'Gói đang dùng').toLocaleUpperCase('vi-VN');
    if ($('#plan-quota')) $('#plan-quota').textContent = fmtBytes(quota);
    // Reveal the whole sidebar quota block only AFTER all real API values are set.
    $('.sidebar-storage')?.setAttribute('data-quota-state', 'ready');
  }
  async function refreshQuota() {
    const summary = await app.api.get('/dashboard/summary');
    updateQuota(summary.storage, summary.subscription?.plan_name || summary.subscription?.plan_code);
    return summary;
  }
  async function initWorkspace() {
    if (!document.body.classList.contains('drive-page')) return null;
    const menu = $('#menu-toggle'), sidebar = $('#sidebar'), backdrop = $('#sidebar-backdrop');
    const closeMenu = () => { sidebar.classList.remove('is-open'); backdrop.hidden = true; menu?.setAttribute('aria-expanded','false'); };
    menu?.addEventListener('click', () => { const open = sidebar.classList.toggle('is-open'); backdrop.hidden = !open; menu.setAttribute('aria-expanded', String(open)); });
    backdrop?.addEventListener('click', closeMenu);
    document.addEventListener('keydown', ev => { if (ev.key === 'Escape') closeMenu(); if (ev.key === '/' && !['INPUT','TEXTAREA'].includes(document.activeElement.tagName)) { ev.preventDefault(); $('#global-search')?.focus(); } });
    $('#global-search-form')?.addEventListener('submit', ev => {
      ev.preventDefault(); const query = $('#global-search')?.value.trim();
      window.location.href = 'files.html' + (query ? `?search=${encodeURIComponent(query)}` : '');
    });
    const search = new URLSearchParams(window.location.search).get('search');
    if (search && $('#global-search')) $('#global-search').value = search;
    if (isPreview) {
      notice('Đang xem giao diện thử nghiệm. Chưa có tài khoản thật hoặc dữ liệu trên máy chủ; các thao tác lưu và thanh toán không hoạt động trong chế độ này.', 'warning');
      if ($('#workspace-status')) $('#workspace-status').textContent = 'XEM GIAO DIỆN';
      if ($('#account')) $('#account').textContent = 'DS';
      // Preview intentionally has no real subscription or storage data.
      $('#logout')?.setAttribute('disabled','true');
      return { id: 'preview', full_name: 'Khách xem trước', role: 'user', preview: true };
    }
    try {
      const data = await app.api.get('/auth/me');
      const user = data?.user || data;
      if (!user?.id) throw new Error('API /auth/me thiếu dữ liệu tài khoản.');
      if ($('#workspace-status')) $('#workspace-status').textContent = user.full_name || user.email || '';
      if ($('#account')) $('#account').textContent = (user.full_name || user.email || '?').trim().split(/\s+/).slice(-2).map(w=>w[0]?.toUpperCase() || '').join('');
      // Admin navigation stays hidden in HTML until the server confirms role=admin.
      const adminLink = $('[data-nav="admin"]');
      if (adminLink) adminLink.hidden = user.role !== 'admin';
      try { await refreshQuota(); } catch (error) {
        // Do not show the placeholder or a fabricated Free plan when quota fails.
        const section = $('.sidebar-storage');
        if (section?.getAttribute('data-quota-state') !== 'ready') {
          if ($('#quota-label')) $('#quota-label').textContent = 'Không tải được thông tin dung lượng';
          if ($('#plan-name')) $('#plan-name').textContent = '—';
          if ($('#plan-quota')) $('#plan-quota').textContent = '—';
          section?.setAttribute('data-quota-state', 'error');
        }
        notice('Không thể tải thông tin dung lượng: ' + errorMessage(error));
      }
      return user;
    } catch (error) {
      if (error.status === 401) { const next = new URL(window.location.href).pathname.split('/').pop(); window.location.replace(`login.html?next=${encodeURIComponent(next)}`); return null; }
      notice('Không thể kiểm tra phiên đăng nhập: ' + errorMessage(error) + ' Hãy thử tải lại trang.', 'danger');
      return null;
    }
  }
  // Homepage: preserve old animations, mobile navigation, but never fabricate API responses.
  if (document.querySelector('.site-header')) {
    const nav = $('#main-navigation'), toggle = $('.menu-toggle');
    const closeMenu = () => { nav?.classList.remove('is-open'); toggle?.setAttribute('aria-expanded','false'); };
    toggle?.addEventListener('click', () => { const open=nav.classList.toggle('is-open'); toggle.setAttribute('aria-expanded',String(open)); });
    nav?.addEventListener('click', ev => { if (ev.target.closest('a')) closeMenu(); });
    document.addEventListener('click', ev => { if (!ev.target.closest('.site-header')) closeMenu(); });
    const reveal = document.querySelectorAll('.reveal');
    if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      const observer = new IntersectionObserver(entries => { entries.forEach(item => { if (item.isIntersecting) { item.target.classList.add('is-visible'); observer.unobserve(item.target); } }); }, { threshold: 0.07 });
      reveal.forEach(node => { node.classList.add('is-pending'); observer.observe(node); });
    }
  }
  if ($('#logout')) $('#logout').addEventListener('click', async () => {
    if (isPreview) return;
    try { await app.api.post('/auth/logout',{}); app.api.clearCsrf(); window.location.replace('login.html'); }
    catch (error) { toast(errorMessage(error)); }
  });
  app.ui = Object.freeze({ $, el, svg, notice, toast, errorMessage, fmtBytes, fmtDate, fmtPrice, refreshQuota, updateQuota, isPreview, initWorkspace });
})();
