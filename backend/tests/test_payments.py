from conftest import register,login
from app.models import Plan,Order,Subscription,Payment
from app.extensions import db
from sqlalchemy import select,func
from app.services.vnpay_service import sign


def test_return_cannot_activate_and_ipn_idempotent(client,csrf,app):
    app.config.update(VNPAY_TMN_CODE='SANDBOXDEMO',VNPAY_HASH_SECRET='test-secret',
                      VNPAY_RETURN_URL='https://example.com/api/v1/payments/vnpay/return')
    register(client,csrf,'a@example.com');login(client,csrf,'a@example.com')
    plan=next(p for p in client.get('/api/v1/plans').json['data'] if p['code']=='basic')
    order=client.post('/api/v1/billing/orders',json={'plan_id':plan['id'],'amount_vnd':1},
                      headers={'X-CSRF-Token':csrf()}).json['data']
    assert order['amount_vnd']==10000
    result=client.post('/api/v1/payments/vnpay/checkout',json={'order_id':order['id']},
                       headers={'X-CSRF-Token':csrf()})
    assert result.status_code==200
    with app.app_context():
        payment=db.session.scalar(select(Payment).where(Payment.order_id==order['id']))
        ref=payment.txn_ref
    query={'vnp_TmnCode':'SANDBOXDEMO','vnp_TxnRef':ref,'vnp_Amount':'1000000',
           'vnp_ResponseCode':'00','vnp_TransactionStatus':'00','vnp_TransactionNo':'123987456'}
    query['vnp_SecureHash']=sign(query,'test-secret')
    assert client.get('/api/v1/payments/vnpay/return',query_string=query).status_code==302
    assert client.get(f"/api/v1/billing/orders/{order['id']}").json['data']['status']=='pending'
    assert client.get('/api/v1/payments/vnpay/ipn',query_string=query).json['RspCode']=='00'
    assert client.get('/api/v1/payments/vnpay/ipn',query_string=query).json['RspCode']=='02'
    assert client.get(f"/api/v1/billing/orders/{order['id']}").json['data']['status']=='paid'
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(Subscription).where(Subscription.order_id==order['id']))==1
