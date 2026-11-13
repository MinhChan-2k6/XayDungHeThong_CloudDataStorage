"""VNPAY PAY 2.1.0 Sandbox: HMAC-SHA512, only IPN may change entitlements."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from flask import current_app
from sqlalchemy import select
from app.extensions import db
from app.models import Order, Payment
from app.services.billing_service import activate_after_payment
from app.utils.errors import APIError

TZ = timezone(timedelta(hours=7))  # Vietnam UTC+7, no daylight saving


def _ready():
    cfg = current_app.config
    if not all(cfg.get(k) for k in ('VNPAY_TMN_CODE','VNPAY_HASH_SECRET','VNPAY_RETURN_URL','VNPAY_PAYMENT_URL')):
        raise APIError(503, 'SERVICE_UNAVAILABLE', 'VNPay Sandbox chưa được cấu hình.')
    if not cfg['VNPAY_RETURN_URL'].startswith('https://') and not cfg.get('TESTING'):
        raise APIError(503, 'SERVICE_UNAVAILABLE', 'VNPay Return URL phải dùng HTTPS.')
    return cfg


def sign(params, secret):
    """Canonical PHP urlencode-compatible form, sorted, excluding only checksum fields."""
    data = {k: str(v) for k, v in params.items() if k.startswith('vnp_') and k not in ('vnp_SecureHash','vnp_SecureHashType') and v is not None}
    canonical = urlencode(sorted(data.items()))
    return hmac.new(secret.encode('utf-8'), canonical.encode('utf-8'), hashlib.sha512).hexdigest()


def verify(params):
    secret = _ready()['VNPAY_HASH_SECRET']
    expected = params.get('vnp_SecureHash', '')
    if not isinstance(expected, str) or len(expected) != 128:
        return False
    if any(not k.startswith('vnp_') for k in params.keys()):
        return False
    return hmac.compare_digest(sign(params, secret), expected.lower())


def create_checkout(user_id, order, ip):
    cfg = _ready()
    if order.user_id != user_id or order.status != 'pending':
        raise APIError(409, 'INVALID_STATE', 'Đơn hàng không ở trạng thái chờ thanh toán.')
    payment = Payment(order_id=order.id, provider='vnpay', txn_ref=secrets.token_hex(16).upper(),
                      amount_vnd=order.amount_vnd, status='pending')
    db.session.add(payment)
    db.session.commit()
    now = datetime.now(TZ)
    values = {
        'vnp_Version':'2.1.0','vnp_Command':'pay','vnp_TmnCode':cfg['VNPAY_TMN_CODE'],
        'vnp_Amount':str(order.amount_vnd * 100),'vnp_CurrCode':'VND',
        'vnp_TxnRef':payment.txn_ref,'vnp_OrderInfo':'CloudDS '+order.order_code,
        'vnp_OrderType':'other','vnp_Locale':'vn','vnp_ReturnUrl':cfg['VNPAY_RETURN_URL'],
        'vnp_IpAddr':ip or '127.0.0.1',
        'vnp_CreateDate':now.strftime('%Y%m%d%H%M%S'),
        'vnp_ExpireDate':(now + timedelta(minutes=15)).strftime('%Y%m%d%H%M%S'),
    }
    sig = sign(values, cfg['VNPAY_HASH_SECRET'])
    query = urlencode(sorted(values.items())) + '&vnp_SecureHash=' + sig
    return cfg['VNPAY_PAYMENT_URL'] + ('&' if '?' in cfg['VNPAY_PAYMENT_URL'] else '?') + query


def process_ipn(params):
    """Return VNPay's RspCode/Message, NEVER a CloudDS API envelope."""
    if not verify(params):
        return {'RspCode':'97','Message':'Invalid Checksum'}
    if params.get('vnp_TmnCode') != current_app.config['VNPAY_TMN_CODE']:
        return {'RspCode':'97','Message':'Invalid Merchant'}
    ref = params.get('vnp_TxnRef', '')
    payment = db.session.scalar(select(Payment).where(Payment.txn_ref == ref))
    if not payment:
        return {'RspCode':'01','Message':'Order Not Found'}
    # Lock the order, then re-read its related payment in the transaction.
    order = db.session.scalar(select(Order).where(Order.id == payment.order_id).with_for_update())
    if not order:
        return {'RspCode':'01','Message':'Order Not Found'}
    payment = db.session.scalar(select(Payment).where(Payment.id == payment.id).with_for_update())
    try:
        received = int(params.get('vnp_Amount', ''))
    except ValueError:
        return {'RspCode':'04','Message':'Invalid Amount'}
    if received != order.amount_vnd * 100 or payment.amount_vnd != order.amount_vnd:
        return {'RspCode':'04','Message':'Invalid Amount'}
    if order.status == 'paid' or payment.status != 'pending':
        return {'RspCode':'02','Message':'Order already confirmed'}
    if order.status != 'pending':
        return {'RspCode':'02','Message':'Order not pending'}
    status = params.get('vnp_TransactionStatus', '')
    response_code = params.get('vnp_ResponseCode', '')
    if not status or not response_code or not params.get('vnp_TransactionNo'):
        return {'RspCode':'99','Message':'Incomplete transaction'}
    txn_no = params['vnp_TransactionNo']
    if status == '00' and response_code == '00':
        other = db.session.scalar(select(Payment.id).where(Payment.provider_txn_no == txn_no, Payment.id != payment.id))
        if other:
            return {'RspCode':'02','Message':'Transaction already recorded'}
        payment.status = 'paid'
        from app.models.user import utcnow
        payment.paid_at = utcnow()
        payment.provider_txn_no = txn_no
        payment.response_code = response_code
        activate_after_payment(order)
    else:
        payment.status = 'failed'
        payment.response_code = response_code
        payment.provider_txn_no = txn_no
        # The order stays pending, permitting a fresh valid checkout attempt.
    db.session.commit()
    return {'RspCode':'00','Message':'Confirm Success'}
