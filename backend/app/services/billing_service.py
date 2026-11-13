import secrets
from datetime import timedelta
from sqlalchemy import select
from app.extensions import db
from app.models import Plan, Subscription, Order, Invoice, StorageUsage, User
from app.models.user import utcnow
from app.services.quota_service import ensure_subscription
from app.utils.errors import APIError
from app.utils.validators import require_uuid


def new_order(user_id, plan_id):
    plan = db.session.get(Plan, require_uuid(plan_id))
    if not plan or not plan.is_active:
        raise APIError(404, 'RESOURCE_NOT_FOUND', 'Không tìm thấy gói dịch vụ.')
    if plan.price_vnd <= 0 or not plan.duration_days or plan.code == 'free':
        raise APIError(422, 'INVALID_FIELD', 'Gói miễn phí không cần thanh toán.')
    order = Order(user_id=user_id, plan_id=plan.id, order_code='CDS'+secrets.token_hex(12).upper(),
                  amount_vnd=plan.price_vnd, quota_bytes=plan.quota_bytes,
                  duration_days=plan.duration_days, status='pending')
    db.session.add(order)
    db.session.commit()
    return order


def order_for_user(user_id, order_id):
    order = db.session.scalar(select(Order).where(Order.id == require_uuid(order_id), Order.user_id == user_id))
    if not order:
        raise APIError(404, 'RESOURCE_NOT_FOUND', 'Không tìm thấy đơn hàng.')
    return order


def activate_after_payment(order):
    """Only called by a verified, successful IPN with an order row lock."""
    if order.status == 'paid':
        return
    now = utcnow()
    # Lock user and retire the previous subscription before applying paid entitlement.
    db.session.scalar(select(User).where(User.id == order.user_id).with_for_update())
    current = db.session.scalar(select(Subscription).where(
        Subscription.user_id == order.user_id, Subscription.status == 'active').with_for_update())
    if current:
        current.status = 'ended'
        current.ended_at = now
        db.session.flush()
    db.session.add(Subscription(user_id=order.user_id, plan_id=order.plan_id, order_id=order.id,
                                quota_bytes=order.quota_bytes, status='active', started_at=now,
                                expires_at=now + timedelta(days=order.duration_days)))
    order.status = 'paid'
    order.paid_at = now
    db.session.add(Invoice(order_id=order.id, invoice_no='CDSINV'+secrets.token_hex(12).upper(),
                           amount_vnd=order.amount_vnd, status='issued', issued_at=now))


def subscription_for_user(user_id):
    active = ensure_subscription(user_id)
    plan = db.session.get(Plan, active.plan_id)
    usage = db.session.get(StorageUsage, user_id)
    result = active.to_dict(plan, usage.used_bytes)
    db.session.commit()
    return result
