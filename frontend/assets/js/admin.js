(() => {
  'use strict';
  if(document.body.dataset.page!=='admin')return;
  const api=window.CloudDS.api,ui=window.CloudDS.ui,$=ui.$;
  async function load(){
    try{
      const [metrics, users, plans]=await Promise.all([api.get('/admin/metrics'),api.get('/admin/users?page=1&page_size=20'),api.get('/admin/plans')]);
      $('#admin-users-count').textContent=metrics.users??metrics.total_users??'—';
      $('#admin-files-count').textContent=metrics.files??metrics.total_files??'—';
      $('#admin-storage-count').textContent=ui.fmtBytes(metrics.storage_bytes??metrics.total_storage_bytes);
      const userList=$('#admin-users');userList.replaceChildren();
      (Array.isArray(users)?users:[]).forEach(user=>{
        const item=ui.el('div','billing-entry');const heading=ui.el('strong','',user.full_name||user.email);item.append(heading,ui.el('p','',`${user.email} · ${user.role} · ${user.status}`));
        const toggle=ui.el('button','btn btn-light-outline btn-sm',user.status==='active'?'Khóa tài khoản':'Mở khóa');
        toggle.type='button';toggle.addEventListener('click',async()=>{
          if(!confirm(`Thay đổi trạng thái tài khoản ${user.email}?`))return;
          toggle.disabled=true;
          try{await api.patch(`/admin/users/${encodeURIComponent(user.id)}`,{status:user.status==='active'?'disabled':'active'});await load();}
          catch(error){ui.notice(ui.errorMessage(error),'danger','#admin-error');toggle.disabled=false;}
        });item.append(toggle);userList.append(item);
      });
      if(!userList.childElementCount)userList.append(ui.el('p','content-muted','Chưa có tài khoản.'));
      const plansList=$('#admin-plans');plansList.replaceChildren();
      (Array.isArray(plans)?plans:[]).forEach(plan=>{
        const item=ui.el('div','billing-entry');item.append(ui.el('strong','',`${plan.name} · ${ui.fmtBytes(plan.quota_bytes)} · ${ui.fmtPrice(plan.price_vnd)}`),ui.el('p','',plan.is_active?'Đang mở bán':'Đã tạm ẩn'));plansList.append(item);
      });
      if(!plansList.childElementCount)plansList.append(ui.el('p','content-muted','Chưa có gói nào.'));
    }catch(error){ui.notice(ui.errorMessage(error),'danger','#admin-error');}
  }
  (async()=>{
    const user=await ui.initWorkspace();if(!user)return;
    if(user.role!=='admin'||user.preview){$('#workspace').querySelectorAll('section,.summary-grid').forEach(node=>node.hidden=true);ui.notice('Chỉ tài khoản quản trị đã xác thực mới được truy cập trang này.','warning','#admin-error');return;}
    await load();
  })();
})();
