/** Folder endpoint wrapper; all ownership and cycle checks must also run in Flask. */
(() => {
  'use strict';
  const api=window.CloudDS.api;
  const base='/folders';
  const endpoint=id=>`${base}/${encodeURIComponent(id)}`;
  window.CloudDS.folders=Object.freeze({
    list: parent => api.get(`${base}?parent_id=${encodeURIComponent(parent||'root')}`),
    create: (name, parent='root') => api.post(base,{ name, parent_id: parent }),
    rename: (id, name) => api.patch(endpoint(id),{ name }),
    move: (id, parent) => api.patch(endpoint(id),{ parent_id: parent }),
    trash: id => api.delete(endpoint(id)),
    // Collect existing folders from GET /folders?parent_id=... (no uncontracted API).
    async destinations(maxDepth=7) {
      const result=[{id:'root',label:'Không gian gốc'}];
      const visited=new Set(['root']);
      async function visit(parent, prefix, depth) {
        if(depth>maxDepth || result.length>500) return;
        const children=await api.get(`${base}?parent_id=${encodeURIComponent(parent)}`);
        if(!Array.isArray(children)) throw new Error('Dữ liệu thư mục chưa hợp lệ.');
        for (const folder of children) {
          if(!folder.id || visited.has(folder.id)) continue;
          visited.add(folder.id);
          result.push({id:folder.id,label:prefix+folder.name});
          await visit(folder.id,prefix+folder.name+' / ',depth+1);
        }
      }
      await visit('root','',1);
      return result;
    }
  });
})();
