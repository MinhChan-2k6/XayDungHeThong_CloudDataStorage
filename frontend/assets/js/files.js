/** Files + trash real operations over /api/v1; no fake local Blob data. */
(() => {
  'use strict';
  const app = window.CloudDS, api=app.api, ui=app.ui, $=ui.$;
  const PAGE_SIZE = 20;
  const query=new URLSearchParams(location.search);
  const isTrash=document.body.dataset.page==='trash';
  if (!['files','trash'].includes(document.body.dataset.page)) return;
  let parentId=query.get('parent_id') || 'root';
  let term=(query.get('search') || '').trim();
  let page=1;
  let state={files:[],folders:[],total:0};
  let modalAction=null;
  function showError(message, selector=isTrash?'#trash-error':'#file-error') {
    ui.notice(message,'danger',selector);
  }
  function button(label, iconName, action, danger=false) {
    const b=ui.el('button',`small-action${danger?' danger':''}`);
    b.type='button'; b.title=label; b.setAttribute('aria-label',label); b.append(ui.svg(iconName),ui.el('span','',label));
    b.addEventListener('click',action); return b;
  }
  function row(item,kind) {
    const row=ui.el('div','storage-row'); const left=ui.el('div','storage-row-main');
    const mark=ui.el('span','file-badge '+(kind==='folder'?'folder':item.mime_type?.startsWith('image/')?'image':'document')); mark.append(ui.svg(kind==='folder'?'folder':item.mime_type?.startsWith('image/')?'image':'file'));
    const names=ui.el('div','storage-file-info'); const name=kind==='folder'?ui.el('a','storage-name',item.name):ui.el('strong','storage-name',item.name);
    if(kind==='folder') name.href=`files.html?parent_id=${encodeURIComponent(item.id)}`;
    const detail=isTrash?'Đã xóa '+ui.fmtDate(item.deleted_at):kind==='folder'?'Thư mục':`${ui.fmtBytes(item.size_bytes)} · ${ui.fmtDate(item.updated_at||item.created_at)}`;
    names.append(name,ui.el('span','storage-subtitle',detail));left.append(mark,names);row.append(left);
    const actions=ui.el('div','storage-actions');
    if(isTrash){
      actions.append(button('Khôi phục','clock',()=>restore(item,kind)),button('Xóa vĩnh viễn','trash',()=>destroy(item,kind),true));
    }else{
      if(kind==='file') actions.append(button('Tải xuống','download',()=>perform(()=>api.download(`/files/${encodeURIComponent(item.id)}/download`,item.name),'Đã gửi yêu cầu tải xuống.')));
      if(kind==='file') actions.append(button('Thông tin','info',()=>showFileInfo(item)));
      actions.append(button('Đổi tên','more',()=>openNameDialog(item,kind)),button('Di chuyển','folder',()=>openMoveDialog(item,kind)),button('Xóa','trash',()=>deleteItem(item,kind),true));
    }
    row.append(actions);return row;
  }
  async function perform(callback, message) {
    try { await callback(); if(message) ui.toast(message); }
    catch(error) {showError(ui.errorMessage(error));}
  }
  async function loadFiles() {
    $('#file-error').hidden=true;
    const list=$('#file-list'); list.replaceChildren(ui.el('p','content-muted','Đang tải danh sách…'));
    if(term) {
      $('#files-title').textContent=`Tệp tìm thấy: “${term}”`;
    } else $('#files-title').textContent=parentId==='root'?'Tệp và thư mục ở gốc':'Nội dung thư mục';
    if (ui.isPreview) {
      list.replaceChildren(ui.el('p','content-muted','Danh sách tệp sẽ được lấy từ MySQL/Garage thông qua Flask API.'));
      $('#empty-state').hidden=true;return;
    }
    const sort=$('#sort').value.split(':');
    const args=term?{search:term,page,page_size:PAGE_SIZE,sort:sort[0],order:sort[1]}:{parent_id:parentId,page,page_size:PAGE_SIZE,sort:sort[0],order:sort[1]};
    try{
      const filesPromise=api.page(`/files?${api.qs(args)}`);
      const foldersPromise=app.folders.list(parentId);
      const [response,folders]=await Promise.all([filesPromise,foldersPromise]);
      if(!Array.isArray(response.data) || !Array.isArray(folders)) throw new Error('API danh sách không trả dữ liệu theo hợp đồng.');
      state={files:response.data,folders:term?folders.filter(f=>f.name.toLocaleLowerCase('vi').includes(term.toLocaleLowerCase('vi'))):folders,total:response.meta?.total??response.data.length};
      list.replaceChildren();
      if(!term || page===1) state.folders.forEach(folder=>list.append(row(folder,'folder')));
      state.files.forEach(file=>list.append(row(file,'file')));
      const count=state.files.length + ((!term||page===1)?state.folders.length:0);
      $('#result-count').textContent=`${count} mục`;
      $('#empty-state').hidden=count>0;
      const pages=Math.max(1,Math.ceil(state.total/PAGE_SIZE));
      $('#files-pagination').hidden=pages<=1;
      $('#page-indicator').textContent=`Trang ${page} / ${pages}`;
      $('#page-prev').disabled=page<=1;$('#page-next').disabled=page>=pages;
      $('#file-error').hidden=true;
    }catch(error){list.replaceChildren(); showError(ui.errorMessage(error));}
  }
  async function emptyTrash(){
    if(!confirm('Xóa VĨNH VIỄN mọi tệp và thư mục trong thùng rác? Không thể khôi phục dữ liệu.')) return;
    const button=$('#empty-trash');button.disabled=true;
    try{
      // No /trash/empty API in the contract: use existing individual DELETE endpoints.
      for(let batch=0;batch<100;batch++){
        const data=await api.get('/trash?page=1&page_size=100');
        if(!Array.isArray(data) || data.length===0) break;
        for(const item of data){
          const kind=item.type==='folder'?'folders':'files';
          await api.delete(`/trash/${kind}/${encodeURIComponent(item.id)}`);
        }
        if(data.length<100) break;
      }
      page=1;await loadTrash();await ui.refreshQuota();ui.toast('Đã xử lý dọn thùng rác.');
    }catch(error){showError(ui.errorMessage(error));}
    finally{button.disabled=false;}
  }
  async function loadTrash(){
    const list=$('#trash-list'); list.replaceChildren(ui.el('p','content-muted','Đang tải thùng rác…'));
    if(ui.isPreview){list.replaceChildren(ui.el('p','content-muted','Thùng rác sẽ hiển thị khi kết nối backend.'));return;}
    try{
      const response=await api.page(`/trash?${api.qs({page,page_size:PAGE_SIZE})}`);
      if(!Array.isArray(response.data)) throw new Error('API thùng rác không trả về danh sách.');
      list.replaceChildren();response.data.forEach(item=>list.append(row(item,item.type==='folder'?'folder':'file')));
      $('#trash-empty').hidden=response.data.length>0;
      const total=response.meta?.total??response.data.length, pages=Math.max(1,Math.ceil(total/PAGE_SIZE));
      $('#trash-pagination').hidden=pages<=1;$('#trash-page').textContent=`Trang ${page} / ${pages}`;
      $('#trash-prev').disabled=page<=1; $('#trash-next').disabled=page>=pages;
    }catch(error){list.replaceChildren();showError(ui.errorMessage(error));}
  }
  // Breadcrumb is resolved server-side: the list API returns only immediate children,
  // so traversing every directory from the browser would be slow and incomplete.
  async function loadBreadcrumb() {
    const container = $('#folder-breadcrumb');
    if (!container) return null;
    let loadError = null;
    container.setAttribute('role', 'navigation');
    container.setAttribute('aria-label', 'Đường dẫn thư mục');
    const parts = [{ id: 'root', name: 'Tệp của tôi' }];
    try {
      if (parentId !== 'root' && ui.isPreview) {
        throw new Error('Chế độ xem trước không có dữ liệu thư mục.');
      }
      if (parentId !== 'root') {
        const ancestors = await api.get(`/folders/${encodeURIComponent(parentId)}/breadcrumb`);
        if (!Array.isArray(ancestors) || !ancestors.length || ancestors.at(-1)?.id !== parentId) {
          throw new Error('Máy chủ chưa trả về đường dẫn thư mục hợp lệ.');
        }
        const visited = new Set(['root']);
        for (const item of ancestors) {
          if (typeof item.id !== 'string' || typeof item.name !== 'string' || !item.name.trim() || visited.has(item.id)) {
            throw new Error('Đường dẫn thư mục không hợp lệ.');
          }
          visited.add(item.id);
          parts.push({ id: item.id, name: item.name });
        }
      }
      container.replaceChildren();
      parts.forEach((item, index) => {
        if (index) container.append(ui.el('span', 'breadcrumb-divider', '/'));
        const link = ui.el('a', '', item.name);
        link.href = item.id === 'root' ? 'files.html' : `files.html?parent_id=${encodeURIComponent(item.id)}`;
        if (index === parts.length - 1 && !term) link.setAttribute('aria-current', 'page');
        container.append(link);
      });
      if (term) {
        container.append(ui.el('span', 'breadcrumb-divider', '/'), ui.el('span', '', 'Kết quả tìm kiếm'));
      }
    } catch (error) {
      // Never pretend we know the folder path if ownership, deletion or lookup fails.
      container.replaceChildren();
      const root = ui.el('a', '', 'Tệp của tôi'); root.href = 'files.html';
      container.append(root, ui.el('span', 'breadcrumb-divider', '/'),
        ui.el('span', 'breadcrumb-error', 'Không thể tải đường dẫn thư mục'));
      loadError = 'Không thể tải đường dẫn thư mục: ' + ui.errorMessage(error);
    } finally {
      container.setAttribute('data-breadcrumb-ready', 'true');
    }
    return loadError;
  }
  const reload=()=>isTrash?loadTrash():loadFiles();
  async function showFileInfo(item){
    try {
      const detail=await api.get(`/files/${encodeURIComponent(item.id)}`);
      alert(`THÔNG TIN TỆP\nTên: ${detail.name}\nDung lượng: ${ui.fmtBytes(detail.size_bytes)}\nLoại: ${detail.mime_type||'Không rõ'}\nTải lên: ${ui.fmtDate(detail.created_at)}\nCập nhật: ${ui.fmtDate(detail.updated_at)}`);
    }catch(error){showError(ui.errorMessage(error));}
  }
  async function deleteItem(item,kind){
    if(!confirm(`Chuyển ${kind==='folder'?'thư mục':'tệp'} “${item.name}” vào thùng rác?`))return;
    await perform(async()=>{await api.delete(`/${kind==='folder'?'folders':'files'}/${encodeURIComponent(item.id)}`);await reload();await ui.refreshQuota();},'Đã chuyển vào thùng rác.');
  }
  async function restore(item,kind){
    await perform(async()=>{await api.post(`/trash/${kind==='folder'?'folders':'files'}/${encodeURIComponent(item.id)}/restore`,{});await reload();},'Đã khôi phục mục đã xóa.');
  }
  async function destroy(item,kind){
    if(!confirm(`XÓA VĨNH VIỄN “${item.name}”? Hành động này không thể hoàn tác.`))return;
    await perform(async()=>{await api.delete(`/trash/${kind==='folder'?'folders':'files'}/${encodeURIComponent(item.id)}`);await reload();await ui.refreshQuota();},'Đã xóa vĩnh viễn.');
  }
  function showModal(title,label,initial,action){
    modalAction=action;
    $('#item-modal-title').textContent=title;$('#item-name-label').textContent=label;
    const input=$('#item-name');input.value=initial;input.hidden=false;input.required=true;
    $('#item-modal-error').textContent='';$('#item-modal').classList.add('is-visible');
    $('#item-modal').setAttribute('aria-hidden','false');setTimeout(()=>input.focus(),20);
  }
  function closeModal(){
    $('#item-modal').classList.remove('is-visible');$('#item-modal').setAttribute('aria-hidden','true');
    const select=$('#destination-select');if(select)select.remove();
    $('#item-name').hidden=false;
  }
  function openNameDialog(item,kind){
    showModal('Đổi tên '+(kind==='folder'?'thư mục':'tệp'),'Tên mới',item.name,async name=>{
      await api.patch(`/${kind==='folder'?'folders':'files'}/${encodeURIComponent(item.id)}`,{name});
      await reload();ui.toast('Đã đổi tên.');
    });
  }
  async function openMoveDialog(item,kind){
    if(ui.isPreview)return;
    showModal('Di chuyển '+(kind==='folder'?'thư mục':'tệp'),'Thư mục đích','',async value=>{
      await api.patch(`/${kind==='folder'?'folders':'files'}/${encodeURIComponent(item.id)}`,{parent_id:value});
      await reload();ui.toast('Đã di chuyển.');
    });
    const input=$('#item-name');input.hidden=true;input.required=false;
    const select=ui.el('select','form-select');select.id='destination-select';select.setAttribute('aria-label','Chọn thư mục đích');input.after(select);
    const chosen=ui.el('option','', 'Đang tải thư mục…');chosen.value=''; select.append(chosen);select.disabled=true;
    try{
      const result=await app.folders.destinations();
      if(!$('#item-modal').classList.contains('is-visible'))return;
      select.replaceChildren(...result.filter(d=>d.id!==item.id).map(d=>{const opt=ui.el('option','',d.label);opt.value=d.id;return opt;}));select.disabled=false;
    }catch(error){$('#item-modal-error').textContent=ui.errorMessage(error);}
  }
  async function createFolder(){
    showModal('Tạo thư mục mới','Tên thư mục','',async name=>{
      await app.folders.create(name,parentId);await reload();ui.toast('Đã tạo thư mục.');
    });
  }
  async function uploadSelected(files){
    if (!files?.length || ui.isPreview) return;
    const status=$('#upload-status');status.hidden=false; const button=$('#upload-button');button.disabled=true;
    let count=0;
    try{
      for(const file of [...files]){
        status.textContent=`Đang tải ${count+1}/${files.length}: ${file.name}`;
        const form=new FormData();form.append('file',file,file.name);form.append('parent_id',parentId);
        try {await api.upload('/files',form);count++;}
        catch(error){showError(`Tệp “${file.name}”: ${ui.errorMessage(error)}`);break;}
      }
      status.textContent=`Đã tải thành công ${count}/${files.length} tệp.`;
      if(count){await reload();await ui.refreshQuota();ui.toast('Đã tải tệp lên CloudDS.');}
    }finally{button.disabled=false;}
  }
  (async()=>{
    const user=await ui.initWorkspace();if(!user)return;
    if(isTrash){
      if(user.preview)$('#empty-trash').disabled=true;
      $('#empty-trash').addEventListener('click',emptyTrash);
      ['trash-prev','trash-next'].forEach(id=>$('#'+id).addEventListener('click',()=>{page+=id==='trash-next'?1:-1;loadTrash();}));
      await loadTrash();return;
    }
    $('#sort').addEventListener('change',()=>{page=1;loadFiles();});
    $('#page-prev').addEventListener('click',()=>{page=Math.max(1,page-1);loadFiles();});
    $('#page-next').addEventListener('click',()=>{page++;loadFiles();});
    $('#create-folder').addEventListener('click',()=>{if(!ui.isPreview)createFolder();});
    $('#upload-button').addEventListener('click',()=>{if(!ui.isPreview)$('#upload-input').click();});
    $('#upload-input').addEventListener('change',ev=>{uploadSelected(ev.target.files);ev.target.value='';});
    if(query.has('upload') && !ui.isPreview)$('#upload-input').click();
    const zone=$('#files-zone');
    zone.addEventListener('dragover',event=>{if(ui.isPreview)return;event.preventDefault();zone.classList.add('drag-over');});
    zone.addEventListener('dragleave',()=>zone.classList.remove('drag-over'));
    zone.addEventListener('drop',event=>{if(ui.isPreview)return;event.preventDefault();zone.classList.remove('drag-over');uploadSelected(event.dataTransfer.files);});
    $('#item-cancel').addEventListener('click',closeModal);$('#item-modal-x').addEventListener('click',closeModal);
    $('#item-modal').addEventListener('click',ev=>{if(ev.target.id==='item-modal')closeModal();});
    document.addEventListener('keydown',ev=>{if(ev.key==='Escape')closeModal();});
    $('#item-form').addEventListener('submit',async ev=>{
      ev.preventDefault();if(!modalAction)return;
      const value=($('#destination-select')?.value??$('#item-name').value).trim();
      if(!value){$('#item-modal-error').textContent='Vui lòng nhập/chọn thông tin hợp lệ.';return;}
      const submit=$('#item-confirm');submit.disabled=true;
      try{await modalAction(value);closeModal();}
      catch(error){$('#item-modal-error').textContent=ui.errorMessage(error);}
      finally{submit.disabled=false;}
    });
    if(term){$('#file-error').hidden=true;$('#page-subtitle').textContent='Tìm toàn bộ tệp theo tên; thư mục được lọc trong vị trí đang mở.';}
    if(user.preview){$('#create-folder').disabled=true;$('#upload-button').disabled=true;}
    const breadcrumbError = await loadBreadcrumb();
    await loadFiles();
    if (breadcrumbError && $('#file-error').hidden) showError(breadcrumbError);
  })();
})();
