from urllib.parse import urlencode
from flask import request, redirect, jsonify
from sqlalchemy import select
from app.extensions import db
from app.models import Payment, Order
from app.routes import api
from app.services.billing_service import order_for_user
from app.services.vnpay_service import create_checkout, process_ipn, verify
from app.utils.errors import APIError, ok
from app.utils.security import current_user, login_required
from app.utils.validators import json_object


@api.post('/payments/vnpay/checkout')
@login_required
def checkout():
    order = order_for_user(current_user().id, json_object().get('order_id'))
    url = create_checkout(current_user().id, order, request.remote_addr)
    return ok({'order_id':order.id,'checkout_url':url})


@api.get('/payments/vnpay/return')
def payment_return():
    # Browser redirect cannot change any account balances or subscription state.
    args = request.args.to_dict()
    order_id = ''
    if verify(args):
        payment = db.session.scalar(select(Payment).where(Payment.txn_ref == args.get('vnp_TxnRef','')))
        if payment:
            order_id = payment.order_id
    query = urlencode({'order_id':order_id, 'valid_return':int(bool(order_id))})
    return redirect('/pages/payment-result.html?' + query, code=302)


@api.get('/payments/vnpay/ipn')
def ipn():
    try:
        data = process_ipn(request.args.to_dict())
        return jsonify(data), 200
    except Exception:
        db.session.rollback()
        from flask import current_app
        current_app.logger.exception('VNPay IPN failure')
        return jsonify({'RspCode':'99','Message':'Unknown error'}), 200
