from sqlalchemy import select
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models import User, StorageUsage, Plan, Subscription
from app.models.user import utcnow
from app.utils.errors import APIError
from app.utils.validators import email_address, password_check, safe_name


def register(data):
    full_name = safe_name(data.get('full_name'), max_len=100)
    if len(full_name) < 2:
        raise APIError(422, 'INVALID_FIELD', 'Họ và tên cần ít nhất 2 ký tự.')
    email = email_address(data.get('email'))
    password = password_check(data.get('password'))
    if db.session.scalar(select(User.id).where(User.email == email)):
        raise APIError(409, 'EMAIL_ALREADY_EXISTS', 'Địa chỉ email đã được sử dụng.')
    free = db.session.scalar(select(Plan).where(Plan.code == 'free', Plan.is_active.is_(True)))
    if not free:
        raise APIError(503, 'SERVICE_UNAVAILABLE', 'Gói Free chưa được khởi tạo.')
    user = User(full_name=full_name, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.flush()
    db.session.add(StorageUsage(user_id=user.id, used_bytes=0, reserved_bytes=0))
    db.session.add(Subscription(user_id=user.id, plan_id=free.id, quota_bytes=free.quota_bytes,
                                status='active', started_at=utcnow()))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Unique email constraint handles concurrent registration attempts.
        if db.session.scalar(select(User.id).where(User.email == email)):
            raise APIError(409, 'EMAIL_ALREADY_EXISTS', 'Địa chỉ email đã được sử dụng.')
        raise
    return user


def authenticate(data):
    email = email_address(data.get('email'))
    pwd = data.get('password')
    if not isinstance(pwd, str):
        raise APIError(401, 'INVALID_CREDENTIALS', 'Thông tin đăng nhập không chính xác.')
    user = db.session.scalar(select(User).where(User.email == email))
    if user is None or not check_password_hash(user.password_hash, pwd) or user.status != 'active':
        raise APIError(401, 'INVALID_CREDENTIALS', 'Thông tin đăng nhập không chính xác.')
    return user
