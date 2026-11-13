from sqlalchemy import select
from flask import request
from app.extensions import db
from app.models import Folder
from app.models.user import utcnow
from app.routes import api
from app.services.file_service import (user_lock, folder_for_user, check_duplicate, move_folder)
from app.utils.errors import APIError,ok
from app.utils.security import current_user,login_required
from app.utils.validators import json_object, parent_id, safe_name, require_uuid


@api.get('/folders')
@login_required
def list_folders():
    user_id=current_user().id
    target=parent_id(request.args.get('parent_id','root'))
    folder_for_user(user_id,target)
    rows=db.session.scalars(select(Folder).where(Folder.user_id==user_id,
                        Folder.parent_id==target,Folder.deleted_at.is_(None)).order_by(Folder.name.asc())).all()
    return ok([r.to_dict() for r in rows])


@api.post('/folders')
@login_required
def create_folder():
    user_id=current_user().id
    data=json_object()
    name=safe_name(data.get('name'))
    parent=parent_id(data.get('parent_id','root'))
    user_lock(user_id)
    folder_for_user(user_id,parent)
    check_duplicate(Folder,user_id,parent,name)
    record=Folder(user_id=user_id,parent_id=parent,name=name)
    db.session.add(record)
    db.session.commit()
    return ok(record.to_dict(),201)


@api.patch('/folders/<folder_id>')
@login_required
def edit_folder(folder_id):
    user_id=current_user().id
    data=json_object()
    if not any(k in data for k in ('name','parent_id')):
        raise APIError(422,'INVALID_FIELD','Cần tên hoặc thư mục đích.')
    user_lock(user_id)
    record=folder_for_user(user_id,require_uuid(folder_id))
    target=parent_id(data['parent_id']) if 'parent_id' in data else record.parent_id
    name=safe_name(data['name']) if 'name' in data else record.name
    if target != record.parent_id:
        move_folder(user_id,record,target)
    check_duplicate(Folder,user_id,target,name,record.id)
    record.name=name
    db.session.commit()
    return ok(record.to_dict())


@api.delete('/folders/<folder_id>')
@login_required
def trash_folder(folder_id):
    user_id=current_user().id
    user_lock(user_id)
    record=folder_for_user(user_id,require_uuid(folder_id))
    record.deleted_at=utcnow()
    db.session.commit()
    return ok({'id':record.id,'trashed':True})


@api.get('/folders/<folder_id>/breadcrumb')
@login_required
def folder_breadcrumb(folder_id):
    """Return root-to-current ancestor names for an owned, active folder.

    The UI must not crawl the entire folder tree to reconstruct a path.
    This read-only endpoint does not change any schema or folder metadata.
    """
    user_id = current_user().id
    current_id = require_uuid(folder_id)
    ancestors = []
    seen = set()
    while current_id:
        if current_id in seen:
            raise APIError(404, 'RESOURCE_NOT_FOUND', 'Đường dẫn thư mục không hợp lệ.')
        seen.add(current_id)
        folder = db.session.scalar(select(Folder).where(
            Folder.id == current_id,
            Folder.user_id == user_id,
            Folder.deleted_at.is_(None)
        ))
        if folder is None:
            raise APIError(404, 'RESOURCE_NOT_FOUND', 'Không tìm thấy thư mục.')
        ancestors.append({'id': folder.id, 'name': folder.name})
        current_id = folder.parent_id
    ancestors.reverse()
    return ok(ancestors)
