from sqlalchemy import select, func, or_
from werkzeug.security import check_password_hash, generate_password_hash
from app.extensions import db
from app.models import File, Folder, Plan, StorageUsage
from app.services.file_service import folder_is_trashed
from app.routes import api
from app.services.quota_service import ensure_subscription
from app.utils.errors import APIError, ok
from app.utils.security import current_user, login_required
from app.utils.validators import json_object, safe_name, password_check, iso


@api.patch('/users/me')
@login_required
def update_profile():
    data = json_object()
    name = safe_name(data.get('full_name'), max_len=100)
    if len(name) < 2:
        raise APIError(422, 'INVALID_FIELD', 'Họ tên ít nhất 2 ký tự.')
    user = current_user()
    user.full_name = name
    db.session.commit()
    return ok(user.to_dict())


@api.post('/users/me/change-password')
@login_required
def change_password():
    data = json_object()
    user = current_user()
    if not isinstance(data.get('current_password'), str) or not check_password_hash(user.password_hash, data['current_password']):
        raise APIError(403, 'INVALID_CREDENTIALS', 'Mật khẩu hiện tại không đúng.')
    password = password_check(data.get('new_password'))
    if check_password_hash(user.password_hash, password):
        raise APIError(422, 'INVALID_FIELD', 'Mật khẩu mới phải khác mật khẩu cũ.')
    user.password_hash = generate_password_hash(password)
    db.session.commit()
    return ok({'message': 'Đã đổi mật khẩu.'})


@api.get('/dashboard/summary')
@login_required
def summary():
    user_id = current_user().id
    subscription = ensure_subscription(user_id)
    usage = db.session.get(StorageUsage, user_id)
    plan = db.session.get(Plan, subscription.plan_id)
    folder_rows = db.session.scalars(select(Folder).where(Folder.user_id == user_id)).all()
    hidden = {folder.id for folder in folder_rows if folder_is_trashed(folder)}
    folders = len(folder_rows) - len(hidden)
    files = db.session.scalar(select(func.count()).select_from(File).where(
        File.user_id == user_id, File.deleted_at.is_(None), File.storage_state == 'ready',
        or_(File.folder_id.is_(None), ~File.folder_id.in_(hidden)) if hidden else File.id.is_not(None)))
    result = {'storage':{'used_bytes':usage.used_bytes,'quota_bytes':subscription.quota_bytes,
                         'remaining_bytes':max(0, subscription.quota_bytes - usage.used_bytes - usage.reserved_bytes)},
              'counts':{'files':files,'folders':folders},
              'subscription':{'plan_code':plan.code,'plan_name':plan.name,'expires_at':iso(subscription.expires_at)}}
    db.session.commit()
    return ok(result)
