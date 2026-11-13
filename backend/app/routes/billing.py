from sqlalchemy import select, func
from app.extensions import db
from app.models import Order, Plan, Invoice
from app.routes import api
from app.services.billing_service import new_order, order_for_user, subscription_for_user
from app.utils.errors import APIError, ok
from app.utils.security import current_user, login_required
from app.utils.validators import json_object, pagination, require_uuid


@api.get('/billing/subscription')
@login_required
def subscription():
    return ok(subscription_for_user(current_user().id))


@api.post('/billing/orders')
@login_required
def buy_plan():
    data = json_object()
    order = new_order(current_user().id, data.get('plan_id'))
    return ok(order.to_dict(), 201)


@api.get('/billing/orders')
@login_required
def orders():
    user_id = current_user().id
    page, size = pagination()
    q = select(Order).where(Order.user_id == user_id)
    count = db.session.scalar(select(func.count()).select_from(Order).where(Order.user_id == user_id))
    rows = db.session.scalars(q.order_by(Order.created_at.desc()).offset((page-1)*size).limit(size)).all()
    return ok([row.to_dict(db.session.get(Plan, row.plan_id).name) for row in rows], meta={'page':page,'page_size':size,'total':count})


@api.get('/billing/orders/<order_id>')
@login_required
def get_order(order_id):
    row = order_for_user(current_user().id, order_id)
    return ok(row.to_dict(db.session.get(Plan, row.plan_id).name))


@api.get('/billing/invoices')
@login_required
def invoices():
    user_id = current_user().id
    page, size = pagination()
    q = select(Invoice).join(Order, Invoice.order_id == Order.id).where(Order.user_id == user_id)
    count = db.session.scalar(select(func.count()).select_from(Invoice).join(Order, Invoice.order_id==Order.id).where(Order.user_id == user_id))
    rows = db.session.scalars(q.order_by(Invoice.issued_at.desc()).offset((page-1)*size).limit(size)).all()
    return ok([r.to_dict() for r in rows], meta={'page':page,'page_size':size,'total':count})


@api.get('/billing/invoices/<invoice_id>')
@login_required
def invoice_detail(invoice_id):
    row = db.session.scalar(select(Invoice).join(Order, Invoice.order_id == Order.id).where(
        Invoice.id == require_uuid(invoice_id), Order.user_id == current_user().id))
    if not row:
        raise APIError(404, 'RESOURCE_NOT_FOUND', 'Không tìm thấy biên nhận.')
    return ok(row.to_dict())
