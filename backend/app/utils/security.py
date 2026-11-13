"""Session/cookie authentication and CSRF without storing tokens in localStorage."""
import hmac
import secrets
from functools import wraps
from flask import g, request, session
from app.extensions import db
from app.utils.errors import APIError


def current_user():
    if hasattr(g, 'cloudds_user'):
        return g.cloudds_user
    from app.models import User
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None
    if user is None or user.status != 'active':
        if user_id:
            session.clear()
        raise APIError(401, 'UNAUTHENTICATED', 'Vui lòng đăng nhập để tiếp tục.')
    g.cloudds_user = user
    return user


def login_required(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        current_user()
        return fn(*args, **kwargs)
    return inner


def admin_required(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        user = current_user()
        if user.role != 'admin':
            raise APIError(403, 'FORBIDDEN', 'Bạn không có quyền quản trị.')
        return fn(*args, **kwargs)
    return inner


def csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']


def verify_csrf():
    # HMAC signature checks protect VNPay callbacks; they are not browser cookie requests.
    if request.method in ('GET', 'HEAD', 'OPTIONS') or request.path == '/api/v1/payments/vnpay/ipn':
        return
    got = request.headers.get('X-CSRF-Token', '')
    expected = session.get('csrf_token', '')
    if not got or not expected or not hmac.compare_digest(got, expected):
        raise APIError(403, 'CSRF_INVALID', 'CSRF token không hợp lệ. Vui lòng tải lại trang.')
    # Do not mutate cookie session for every request.
    origin = request.headers.get('Origin')
    if origin:
        from urllib.parse import urlparse
        from flask import current_app
        parsed = urlparse(origin)
        if parsed.netloc != request.host:
            raise APIError(403, 'FORBIDDEN', 'Origin không hợp lệ.')
