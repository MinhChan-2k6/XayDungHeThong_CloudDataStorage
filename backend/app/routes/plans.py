from sqlalchemy import select
from app.extensions import db
from app.models import Plan
from app.routes import api
from app.utils.errors import APIError, ok
from app.utils.validators import require_uuid


@api.get('/plans')
def list_plans():
    plans = db.session.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_vnd)).all()
    return ok([p.to_dict() for p in plans])


@api.get('/plans/<plan_id>')
def get_plan(plan_id):
    plan = db.session.get(Plan, require_uuid(plan_id))
    if not plan or not plan.is_active:
        raise APIError(404, 'RESOURCE_NOT_FOUND', 'Không tìm thấy gói dịch vụ.')
    return ok(plan.to_dict())
