from sqlalchemy import select,func
from app.extensions import db
from app.models import User,File,Plan,StorageUsage
from app.routes import api
from app.utils.errors import APIError,ok
from app.utils.security import admin_required,current_user
from app.utils.validators import json_object, pagination, require_uuid


def plan_payload(data, current=None):
    code=data.get('code',current.code if current else None)
    name=data.get('name',current.name if current else None)
    quota=data.get('quota_bytes',current.quota_bytes if current else None)
    price=data.get('price_vnd',current.price_vnd if current else None)
    duration=data.get('duration_days',current.duration_days if current else None)
    active=data.get('is_active',current.is_active if current else True)
    if not isinstance(code,str) or not code.isascii() or not code.islower() or not code.replace('_','').isalnum() or len(code)>32:
        raise APIError(422,'INVALID_FIELD','Mã gói không hợp lệ.')
    if not isinstance(name,str) or not name.strip() or len(name)>80:
        raise APIError(422,'INVALID_FIELD','Tên gói không hợp lệ.')
    if type(quota) is not int or quota<=0 or type(price) is not int or price<0:
        raise APIError(422,'INVALID_FIELD','Giá hoặc dung lượng không hợp lệ.')
    if type(active) is not bool or ((duration is None) != (price==0)) or (duration is not None and (type(duration) is not int or duration<=0)):
        raise APIError(422,'INVALID_FIELD','Thời hạn gói không hợp lệ.')
    return dict(code=code,name=name.strip(),quota_bytes=quota,price_vnd=price,duration_days=duration,is_active=active)


@api.get('/admin/users')
@admin_required
def users():
    page,size=pagination()
    rows=db.session.scalars(select(User).order_by(User.created_at.desc()).offset((page-1)*size).limit(size)).all()
    return ok([row.to_dict() for row in rows],meta={'page':page,'page_size':size,
                 'total':db.session.scalar(select(func.count()).select_from(User))})


@api.patch('/admin/users/<user_id>')
@admin_required
def patch_user(user_id):
    user=db.session.get(User,require_uuid(user_id))
    if not user:
        raise APIError(404,'RESOURCE_NOT_FOUND','Không tìm thấy người dùng.')
    if user.id==current_user().id:
        raise APIError(409,'INVALID_STATE','Không thể tự khóa tài khoản của mình.')
    status=json_object().get('status')
    if status not in ('active','disabled'):
        raise APIError(422,'INVALID_FIELD','Trạng thái không hợp lệ.')
    user.status=status
    db.session.commit()
    return ok(user.to_dict())


@api.get('/admin/plans')
@admin_required
def plans():
    return ok([p.to_dict() for p in db.session.scalars(select(Plan).order_by(Plan.price_vnd)).all()])


@api.post('/admin/plans')
@admin_required
def add_plan():
    data=plan_payload(json_object())
    if db.session.scalar(select(Plan.id).where(Plan.code==data['code'])):
        raise APIError(409,'DUPLICATE_NAME','Mã gói đã tồn tại.')
    plan=Plan(**data)
    db.session.add(plan)
    db.session.commit()
    return ok(plan.to_dict(),201)


@api.patch('/admin/plans/<plan_id>')
@admin_required
def update_plan(plan_id):
    plan=db.session.get(Plan,require_uuid(plan_id))
    if not plan:
        raise APIError(404,'RESOURCE_NOT_FOUND','Không tìm thấy gói.')
    data=json_object()
    if plan.code=='free' and (('code' in data and data['code'] != 'free') or 'price_vnd' in data or 'duration_days' in data or data.get('is_active') is False):
        raise APIError(409,'INVALID_STATE','Gói Free phải miễn phí và luôn có sẵn.')
    values=plan_payload(data,plan)
    if db.session.scalar(select(Plan.id).where(Plan.code==values['code'],Plan.id!=plan.id)):
        raise APIError(409,'DUPLICATE_NAME','Mã gói đã tồn tại.')
    for k,v in values.items():
        setattr(plan,k,v)
    db.session.commit()
    return ok(plan.to_dict())


@api.get('/admin/metrics')
@admin_required
def metrics():
    return ok({'users':db.session.scalar(select(func.count()).select_from(User)),
               'files':db.session.scalar(select(func.count()).select_from(File).where(File.storage_state=='ready')),
               'storage_bytes':db.session.scalar(select(func.coalesce(func.sum(StorageUsage.used_bytes),0)))})
