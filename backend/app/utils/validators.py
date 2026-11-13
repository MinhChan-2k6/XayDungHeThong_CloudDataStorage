import re
import uuid
from flask import request
from app.utils.errors import APIError


def json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError(400, 'VALIDATION_ERROR', 'Cần dữ liệu JSON dạng đối tượng.')
    return data


def require_uuid(raw):
    try:
        value = str(uuid.UUID(str(raw)))
    except (ValueError, TypeError, AttributeError):
        raise APIError(404, 'RESOURCE_NOT_FOUND', 'Không tìm thấy dữ liệu.')
    return value


def parent_id(raw):
    if raw in ('root', None, ''):
        return None
    return require_uuid(raw)


def safe_name(raw, *, max_len=255):
    if not isinstance(raw, str):
        raise APIError(422, 'INVALID_FIELD', 'Tên không hợp lệ.')
    value = raw.strip()
    if not value or len(value) > max_len or any(ord(c) < 32 for c in value) or '/' in value or '\\' in value:
        raise APIError(422, 'INVALID_FIELD', 'Tên không hợp lệ (1–255 ký tự, không chứa dấu / hoặc \\).')
    if value in ('.', '..'):
        raise APIError(422, 'INVALID_FIELD', 'Tên không hợp lệ.')
    return value


def pagination():
    try:
        page = int(request.args.get('page', '1'))
        size = int(request.args.get('page_size', '20'))
        if page < 1 or not 1 <= size <= 100:
            raise ValueError()
    except ValueError:
        raise APIError(422, 'INVALID_FIELD', 'Tham số phân trang không hợp lệ.')
    return page, size


def email_address(raw):
    if not isinstance(raw, str):
        raise APIError(422, 'INVALID_FIELD', 'Email không hợp lệ.')
    value = raw.strip().lower()
    if len(value) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]{2,}', value):
        raise APIError(422, 'INVALID_FIELD', 'Email không hợp lệ.')
    return value


def password_check(raw):
    if not isinstance(raw, str) or not 8 <= len(raw) <= 128 or not any(c.isalpha() for c in raw) or not any(c.isdigit() for c in raw):
        raise APIError(422, 'INVALID_FIELD', 'Mật khẩu từ 8 đến 128 ký tự, có ít nhất một chữ và một số.')
    return raw


def iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ') if dt else None
