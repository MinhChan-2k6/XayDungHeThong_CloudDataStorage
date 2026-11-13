from sqlalchemy import select
from app.extensions import db
from app.models import Plan, Subscription, StorageUsage, User
from app.models.user import utcnow
from app.utils.errors import APIError


def lock_usage(user_id):
    usage = db.session.scalar(select(StorageUsage).where(StorageUsage.user_id == user_id).with_for_update())
    if usage is None:
        raise APIError(500, 'INTERNAL_ERROR', 'Tài khoản thiếu thông tin dung lượng.')
    return usage


def ensure_subscription(user_id, *, locked=False):
    """Called within a transaction. Lock user for quota/payment serialization."""
    if not locked:
        db.session.scalar(select(User).where(User.id == user_id).with_for_update())
    active = db.session.scalar(select(Subscription).where(
        Subscription.user_id == user_id, Subscription.status == 'active').with_for_update())
    now = utcnow()
    if active is not None and (active.expires_at is None or active.expires_at > now):
        return active
    if active is not None:
        active.status = 'expired'
        active.ended_at = now
        db.session.flush()
    free = db.session.scalar(select(Plan).where(Plan.code == 'free'))
    if free is None:
        raise APIError(503, 'SERVICE_UNAVAILABLE', 'Chưa có gói Free.')
    free_sub = Subscription(user_id=user_id, plan_id=free.id, quota_bytes=free.quota_bytes,
                            status='active', started_at=now)
    db.session.add(free_sub)
    db.session.flush()
    return free_sub


def subscription_info(user_id):
    active = ensure_subscription(user_id)
    usage = lock_usage(user_id)
    plan = db.session.get(Plan, active.plan_id)
    result = active.to_dict(plan, usage.used_bytes)
    db.session.commit()  # persists expiration fallback when necessary
    return result


def reserve(user_id, size):
    # Lock order: user -> storage_usage (consistently across uploads & payment).
    db.session.scalar(select(User).where(User.id == user_id).with_for_update())
    active = ensure_subscription(user_id, locked=True)
    usage = lock_usage(user_id)
    available = max(0, active.quota_bytes - usage.used_bytes - usage.reserved_bytes)
    if size > available:
        raise APIError(409, 'QUOTA_EXCEEDED', 'Dung lượng lưu trữ không đủ.',
                       {'available_bytes': available, 'required_bytes': size})
    usage.reserved_bytes += size
    db.session.commit()


def release(user_id, size):
    usage = lock_usage(user_id)
    usage.reserved_bytes = max(0, usage.reserved_bytes - size)
    db.session.commit()


def storage_summary(user_id):
    active = ensure_subscription(user_id)
    usage = lock_usage(user_id)
    return active, usage
