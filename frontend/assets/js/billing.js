(() => {
  'use strict';
  if(document.body.dataset.page!=='billing')return;
  const api=window.CloudDS.api,ui=window.CloudDS.ui,$=ui.$;
  const pagination={orders:1,invoices:1};
  async function loadList(kind){
    const id=kind==='orders'?'#orders-list':'#invoices-list', container=$(id);
    if(ui.isPreview){container.replaceChildren(ui.el('p','content-muted','Dữ liệu giao dịch sẽ hiển thị khi có backend.'));return;}
    try{
      const {data,meta}=await api.page(`/billing/${kind}?${api.qs({page:pagination[kind],page_size:10})}`);
      if(!Array.isArray(data))throw new Error('API không trả danh sách giao dịch.');
      container.replaceChildren();
      for(const item of data){
        const wrap=ui.el('div','billing-entry');
        const headline=ui.el('div','');headline.append(ui.el('strong','',item.plan_name||item.id));
        headline.append(ui.el('span','status-pill status-'+(item.status||'unknown'),item.status||'—'));
        wrap.append(headline,ui.el('p','',`${ui.fmtPrice(item.amount_vnd)} · ${ui.fmtDate(item.created_at||item.issued_at)}`));
        if(kind==='invoices'){
          const btn=ui.el('button','small-action mt-2','Xem biên nhận');btn.type='button';
          btn.addEventListener('click',async()=>{
            try{const data=await api.get(`/billing/invoices/${encodeURIComponent(item.id)}`);
              alert(`BIÊN NHẬN CLOUDDS\nMã: ${data.id}\nĐơn hàng: ${data.order_id}\nSố tiền: ${ui.fmtPrice(data.amount_vnd)}\nTrạng thái: ${data.status}\nNgày lập: ${ui.fmtDate(data.issued_at)}`);
            }catch(error){ui.notice(ui.errorMessage(error),'danger','#billing-error');}
          });wrap.append(btn);
        }
        if(kind==='orders'){
          const link=ui.el('a','subtle-link','Xem trạng thái');link.href=`payment-result.html?order_id=${encodeURIComponent(item.id)}`;wrap.append(link);
        }
        container.append(wrap);
      }
      if(!data.length)container.append(ui.el('p','content-muted',kind==='orders'?'Chưa có đơn hàng.':'Chưa có biên nhận.'));
      const pages=Math.max(1,Math.ceil((meta?.total??data.length)/10));
      const pager=$(`#${kind}-pager`);pager.hidden=pages<=1;
      $(`#${kind}-page`).textContent=`Trang ${pagination[kind]} / ${pages}`;
      $(`[data-pager="${kind}-prev"]`).disabled=pagination[kind]<=1;
      $(`[data-pager="${kind}-next"]`).disabled=pagination[kind]>=pages;
    }catch(error){container.replaceChildren(ui.el('p','content-error',ui.errorMessage(error)));}
  }
  (async()=>{
    const user=await ui.initWorkspace();if(!user)return;
    if(!user.preview){
      try{
        const s=await api.get('/billing/subscription');
        $('#billing-subscription').querySelector('p').textContent=`${s.plan?.name||s.plan_code||'—'} · ${ui.fmtBytes(s.used_bytes)} / ${ui.fmtBytes(s.quota_bytes)} · ${s.expires_at?'Hết hạn '+ui.fmtDate(s.expires_at):'Không giới hạn thời hạn'}`;
      }catch(error){ui.notice(ui.errorMessage(error),'danger','#billing-error');}
    }else $('#billing-subscription').querySelector('p').textContent='Không có giao dịch thật trong chế độ xem giao diện.';
    document.querySelectorAll('[data-pager]').forEach(btn=>btn.addEventListener('click',()=>{
      const [kind,direction]=btn.dataset.pager.split('-');pagination[kind]+=direction==='next'?1:-1;loadList(kind);
    }));
    await Promise.all([loadList('orders'),loadList('invoices')]);
  })();
})();
