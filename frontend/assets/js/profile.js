(() => {
  'use strict';
  if(document.body.dataset.page!=='profile')return;
  const api=window.CloudDS.api,ui=window.CloudDS.ui,$=ui.$;
  (async()=>{
    const user=await ui.initWorkspace();if(!user)return;
    $('#profile-name').value=user.preview?'':(user.full_name||'');$('#profile-email').value=user.preview?'':(user.email||'');$('#profile-role').value=user.role||'—';
    if(user.preview){document.querySelectorAll('#profile-form input, #password-form input, #profile-form button, #password-form button').forEach(input=>input.disabled=true);return;}
    $('#profile-form').addEventListener('submit',async ev=>{
      ev.preventDefault();const msg=$('#profile-message');msg.textContent='Đang lưu…';
      try{const result=await api.patch('/users/me',{full_name:$('#profile-name').value.trim()});
        msg.className='small mb-3 text-success';msg.textContent='Đã lưu thông tin tài khoản.';
        if($('#workspace-status'))$('#workspace-status').textContent=result.full_name||$('#profile-name').value;
      }catch(error){msg.className='small mb-3 text-danger';msg.textContent=ui.errorMessage(error);}
    });
    $('#password-form').addEventListener('submit',async ev=>{
      ev.preventDefault();const old=$('#current-password').value,one=$('#new-password').value,two=$('#confirm-password').value,msg=$('#password-message');
      if(one!==two){msg.className='small mb-3 text-danger';msg.textContent='Mật khẩu nhập lại không khớp.';return;}
      if(one.length<8){msg.className='small mb-3 text-danger';msg.textContent='Mật khẩu mới phải có ít nhất 8 ký tự.';return;}
      msg.textContent='Đang cập nhật…';
      try{await api.post('/users/me/change-password',{current_password:old,new_password:one});
        $('#password-form').reset();msg.className='small mb-3 text-success';msg.textContent='Đổi mật khẩu thành công.';
      }catch(error){msg.className='small mb-3 text-danger';msg.textContent=ui.errorMessage(error);}
    });
  })();
})();
