from flask import session
from app.routes import api
from app.extensions import db
from app.services.auth_service import register, authenticate
from app.utils.errors import ok
from app.utils.security import current_user, csrf_token, login_required
from app.utils.validators import json_object


@api.get('/auth/csrf')
def csrf():
    return ok({'csrf_token': csrf_token()})


@api.post('/auth/register')
def signup():
    user = register(json_object())
    return ok({'user': user.to_dict()}, 201)


@api.post('/auth/login')
def signin():
    user = authenticate(json_object())
    session.clear()
    session.permanent = True
    session['user_id'] = user.id
    return ok({'user': user.to_dict()})


@api.post('/auth/logout')
@login_required
def logout():
    session.clear()
    return ok({'message': 'Đã đăng xuất.'})


@api.get('/auth/me')
@login_required
def me():
    return ok({'user': current_user().to_dict()})
