(() => {
  'use strict';
  const app = window.CloudDS, ui = app.ui;
  const { $, el, svg, fmtBytes, fmtDate } = ui;
  (async () => {
    const user = await ui.initWorkspace(); if (!user) return;
    if (user.preview) {
      $('#greeting').textContent = 'Đây là bố cục giao diện, chưa có dữ liệu máy chủ.';
      $('#recent-files').replaceChildren(el('p','content-muted','Tệp sẽ được hiển thị khi backend cung cấp dữ liệu.'));
      return;
    }
    $('#greeting').textContent = `Xin chào ${user.full_name || user.email}! Không gian CloudDS của bạn đang sẵn sàng.`;
    try {
      const data = await ui.refreshQuota();
      $('#summary-used').textContent = fmtBytes(data.storage?.used_bytes);
      $('#summary-total').textContent = fmtBytes(data.storage?.quota_bytes);
      $('#summary-files').textContent = data.counts?.files ?? '—';
      $('#summary-folders').textContent = data.counts?.folders ?? '—';
    } catch (error) { ui.notice(ui.errorMessage(error)); }
    try {
      const files = await app.api.get('/files?parent_id=root&page=1&page_size=5&sort=created_at&order=desc');
      const list = $('#recent-files'); list.replaceChildren();
      if (!Array.isArray(files) || !files.length) { list.append(el('p','content-muted','Chưa có tệp ở thư mục gốc. Hãy mở “Tệp của tôi” để tải lên.')); return; }
      const table = el('table','file-table'); const thead=el('thead'); const hr=el('tr');
      ['Tên tệp','Ngày tải','Dung lượng'].forEach(k=>hr.append(el('th','',k))); thead.append(hr);
      const body = el('tbody'); files.forEach(file=>{
        const tr = el('tr'), td = el('td'); const link = el('a','file-name'); link.href = `files.html?parent_id=${encodeURIComponent(file.parent_id||'root')}`;
        link.append(svg('file'),el('strong','',file.name)); td.append(link); tr.append(td,el('td','',fmtDate(file.created_at)),el('td','',fmtBytes(file.size_bytes))); body.append(tr);
      }); table.append(thead,body); list.append(table);
    } catch (error) { $('#recent-files').replaceChildren(el('p','content-error',ui.errorMessage(error))); }
  })();
})();
