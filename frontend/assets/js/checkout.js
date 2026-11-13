/** Order confirmation and payment-result polling. Never trusts redirect params as paid status. */
(() => {
  'use strict';
  const app=window.CloudDS,api=app.api,ui=app.ui,$=ui.$;
  const params=new URLSearchParams(location.search);
  const orderId=params.get('order_id');
  async function loadOrder(){
    if(!orderId){throw new Error('Đường dẫn thiếu mã đơn hàng. Hãy chọn gói dịch vụ trước.');}
    const order=await api.get(`/billing/orders/${encodeURIComponent(orderId)}`);
    if (!order?.id) throw new Error('Máy chủ không trả thông tin đơn hàng.');
    return order;
  }
  async function checkout(user){
    const button=$('#pay-button');
    try{
      if(user.preview){$('#checkout-summary').textContent='Chế độ xem giao diện, chưa có đơn hàng.';return;}
      const order=await loadOrder();
      const content=$('#checkout-summary');content.replaceChildren();
      for(const [label,value] of [
        ['Mã đơn hàng',order.id],['Gói đã chọn',order.plan?.name||order.plan_name||order.plan_id],
        ['Số tiền',ui.fmtPrice(order.amount_vnd)],['Trạng thái',order.status],['Ngày tạo',ui.fmtDate(order.created_at)]
      ]){
        const line=ui.el('div','checkout-line');line.append(ui.el('span','',label),ui.el('strong','',value||'—'));content.append(line);
      }
      if(order.status!=='pending'){
        button.disabled=true;button.textContent=`Đơn hàng ${order.status||'không còn chờ thanh toán'}`;
        return;
      }
      button.disabled=false;
      button.addEventListener('click',async()=>{
        button.disabled=true;button.textContent='Đang kết nối VNPay…';
        try{
          const result=await api.post('/payments/vnpay/checkout',{order_id:order.id});
          const url=new URL(result.checkout_url);
          if(url.protocol!=='https:' || !/\.vnpayment\.vn$/i.test(url.hostname)) throw new Error('Backend trả về URL thanh toán VNPay không hợp lệ.');
          window.location.assign(url.href);
        }catch(error){ui.notice(ui.errorMessage(error),'danger','#checkout-error');button.disabled=false;button.textContent='Thanh toán bằng VNPay Sandbox';}
      });
    }catch(error){ui.notice(ui.errorMessage(error),'danger','#checkout-error');$('#checkout-summary').replaceChildren();}
  }
  async function paymentResult(user){
    const root=$('#payment-result-status');
    async function refresh(){
      if(user.preview){root.replaceChildren(ui.el('h2','','Không có dữ liệu thanh toán trong chế độ xem giao diện.'));return;}
      try{
        const order=await loadOrder();
        const heading=order.status==='paid'?'Thanh toán thành công':order.status==='pending'?'Đơn đang chờ xác nhận':order.status==='failed'?'Thanh toán không thành công':order.status==='cancelled'?'Đơn hàng đã hủy':'Trạng thái đơn hàng';
        root.replaceChildren(ui.el('h2','',heading),ui.el('p','',`Trạng thái ghi nhận trên server: ${order.status||'—'}. Mã đơn: ${order.id}.`));
        if(order.status==='paid') await ui.refreshQuota().catch(()=>{});
      }catch(error){root.replaceChildren(ui.el('h2','','Chưa thể kiểm tra đơn hàng'),ui.el('p','content-error',ui.errorMessage(error)));}
    }
    $('#refresh-order').addEventListener('click',refresh);
    await refresh();
  }
  (async()=>{
    if(!['checkout','payment-result'].includes(document.body.dataset.page))return;
    const user=await ui.initWorkspace();if(!user)return;
    if(document.body.dataset.page==='checkout')checkout(user);else paymentResult(user);
  })();
})();
