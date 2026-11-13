/** Public plan list and authenticated upgrade flow; price/quota are never hardcoded. */
(() => {
  'use strict';
  const app = window.CloudDS, ui = app.ui;
  const $ = selector => document.querySelector(selector);
  function makePlan(plan, currentCode, inDashboard) {
    const col = ui.el('div', inDashboard ? 'col-md-4' : 'col-lg-4 col-md-6');
    const card = ui.el('article', `plan-card${plan.code==='basic'?' featured':''} h-100`);
    const label = ui.el('div','plan-label'); label.append(ui.el('h3','plan-name',plan.name || plan.code),ui.el('span','plan-tag',plan.code === 'free' ? 'MIỄN PHÍ' : 'LƯU TRỮ ĐÁM MÂY'));
    card.append(label, ui.el('p','plan-description','Dữ liệu được bảo vệ trong không gian riêng của tài khoản.'));
    const cap = ui.el('div','plan-capacity'); cap.append(ui.el('strong','',ui.fmtBytes(plan.quota_bytes))); card.append(cap);
    const price = ui.el('div','plan-price',ui.fmtPrice(plan.price_vnd)); price.append(ui.el('span','price-period',plan.price_vnd===0 ? ' / miễn phí' : plan.duration_days ? ` / ${plan.duration_days} ngày` : '')); card.append(price);
    const divider=ui.el('div','plan-divider'); card.append(divider);
    const items=ui.el('ul','check-list'); ['Tải tệp lên và tải xuống','Thư mục cá nhân','Theo dõi dung lượng sử dụng'].forEach(value=>{const li=ui.el('li'); li.append(ui.el('span','text-success','✓'),ui.el('span','',value)); items.append(li);}); card.append(items);
    if (inDashboard) {
      const button = ui.el('button', 'btn btn-brand mt-3 w-100', currentCode===plan.code?'Đang sử dụng':plan.code==='free'?'Gói mặc định':'Chọn gói');
      button.type = 'button'; button.disabled = currentCode===plan.code || plan.code==='free' || ui.isPreview;
      button.addEventListener('click',async()=>{
        if (!confirm(`Tạo đơn hàng nâng cấp lên gói ${plan.name}?`)) return;
        button.disabled=true; const former=button.textContent; button.textContent='Đang tạo đơn…';
        try { const order=await app.api.post('/billing/orders',{plan_id:plan.id}); if (!order?.id) throw new Error('API không trả mã đơn hàng.'); location.href=`checkout.html?order_id=${encodeURIComponent(order.id)}`; }
        catch(error){ ui.notice(ui.errorMessage(error),'danger','#plan-message'); button.disabled=false; button.textContent=former; }
      }); card.append(button);
    } else {
      const link = ui.el('a','btn btn-brand mt-3 w-100',plan.code==='free'?'Tạo tài khoản miễn phí':'Xem gói dịch vụ');
      link.href = plan.code==='free' ? 'pages/register.html' : 'pages/plans.html'; card.append(link);
    }
    col.append(card); return col;
  }
  function placeholderPlans(root, isDashboard = false) {
    root.replaceChildren();
    for(const code of ['Free','Basic','Pro']) {
      const col=ui.el('div',isDashboard?'col-lg-4 col-md-6':'col-md-4');
      const card=ui.el('article','plan-card h-100');
      card.append(ui.el('h3','plan-name',code),ui.el('p','plan-description','Thông tin giá và dung lượng được lấy từ máy chủ.'),ui.el('div','plan-capacity','—'),ui.el('p','content-muted','Chưa có dữ liệu gói dịch vụ.'));
      col.append(card);root.append(col);
    }
  }
  async function loadHome() {
    const root = $('#home-plans'); if (!root) return;
    try {
      const list = await app.api.get('/plans');
      if (!Array.isArray(list)) throw new Error('Danh sách gói từ API không hợp lệ.');
      root.replaceChildren(...list.filter(p=>p.is_active!==false).map(p=>makePlan(p,null,false)));
      if (!root.childElementCount) root.append(ui.el('p','content-muted','Chưa có gói lưu trữ nào đang được mở bán.'));
    } catch(error) {
      placeholderPlans(root);
      const note=ui.el('div','col-12 plan-notice','Giá và hạn mức chưa khả dụng do API chưa kết nối.'); root.prepend(note);
    }
  }
  async function loadPage() {
    if (document.body.dataset.page!=='plans') return;
    const user = await ui.initWorkspace(); if (!user) return;
    let code = null;
    if (!user.preview) {
      try {
        const subscription = await app.api.get('/billing/subscription');
        code=subscription.plan?.code || subscription.plan_code;
        $('#current-plan').querySelector('p').textContent=`${subscription.plan?.name || code || '—'} · ${ui.fmtBytes(subscription.used_bytes)} / ${ui.fmtBytes(subscription.quota_bytes)} · ${subscription.expires_at ? 'Hết hạn '+ui.fmtDate(subscription.expires_at):'Không giới hạn thời hạn'}`;
      } catch(error) {ui.notice(ui.errorMessage(error),'danger','#plan-message');}
    } else $('#current-plan').querySelector('p').textContent='Chỉ xem giao diện. Không thể đặt mua khi chưa có backend.';
    try {
      const list = user.preview ? [] : await app.api.get('/plans');
      if (!Array.isArray(list)) throw new Error('API không trả mảng gói.');
      $('#plan-grid').replaceChildren(...list.filter(p=>p.is_active!==false).map(p=>makePlan(p,code,true)));
      if (!list.length) placeholderPlans($('#plan-grid'),true);
    } catch(error) { ui.notice(ui.errorMessage(error),'danger','#plan-message'); placeholderPlans($('#plan-grid'),true); }
  }
  loadHome(); loadPage();
})();
