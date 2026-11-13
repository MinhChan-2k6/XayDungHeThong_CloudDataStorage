import mimetypes
import uuid
from urllib.parse import quote
from flask import request, Response, stream_with_context
from sqlalchemy import select, func
from app.extensions import db
from app.models import File, Folder
from app.models.user import utcnow
from app.routes import api
from app.services import garage_service
from app.services.file_service import (file_for_user, folder_for_user, folder_is_trashed,
                                       check_duplicate, user_lock, hard_delete_file,
                                       hard_delete_folder, trash_view, descendants)
from app.services.quota_service import reserve, release, lock_usage
from app.utils.errors import APIError, ok
from app.utils.security import current_user, login_required
from app.utils.validators import json_object, pagination, parent_id, require_uuid, safe_name, iso


@api.get('/files')
@login_required
def list_files():
    user_id = current_user().id
    term = request.args.get('search','').strip()
    q = select(File).where(File.user_id == user_id, File.deleted_at.is_(None), File.storage_state == 'ready')
    if term:
        if len(term) > 255:
            raise APIError(422, 'INVALID_FIELD', 'Từ khóa quá dài.')
        q = q.where(File.name.ilike('%' + term.replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%', escape='!'))
        rows = db.session.scalars(q).all()
        rows = [f for f in rows if not f.folder_id or not folder_is_trashed(db.session.get(Folder, f.folder_id))]
        sort = request.args.get('sort','created_at')
        if sort not in ('created_at','updated_at','name','size_bytes'):
            sort='created_at'
        reverse=request.args.get('order','desc')!='asc'
        rows.sort(key=lambda f:getattr(f,sort),reverse=reverse)
        page,size=pagination()
        total=len(rows)
        return ok([f.to_dict() for f in rows[(page-1)*size:page*size]], meta={'page':page,'page_size':size,'total':total})
    target=parent_id(request.args.get('parent_id','root'))
    folder_for_user(user_id,target)
    q=q.where(File.folder_id == target)
    page,size=pagination()
    count=db.session.scalar(select(func.count()).select_from(q.subquery()))
    sort=request.args.get('sort','created_at')
    if sort not in ('created_at','updated_at','name','size_bytes'):
        raise APIError(422,'INVALID_FIELD','Trường sắp xếp không hợp lệ.')
    order=request.args.get('order','desc')
    if order not in ('asc','desc'):
        raise APIError(422,'INVALID_FIELD','Thứ tự sắp xếp không hợp lệ.')
    column=getattr(File,sort)
    q=q.order_by(column.desc() if order=='desc' else column.asc(), File.id)
    rows=db.session.scalars(q.offset((page-1)*size).limit(size)).all()
    return ok([f.to_dict() for f in rows],meta={'page':page,'page_size':size,'total':count})


@api.post('/files')
@login_required
def upload_file():
    user_id=current_user().id
    file=request.files.get('file')
    if file is None or not file.filename:
        raise APIError(422,'INVALID_FIELD','Vui lòng chọn tệp.')
    name=safe_name(file.filename)
    folder_id=parent_id(request.form.get('parent_id','root'))
    try:
        stream=file.stream
        stream.seek(0,2)
        size=stream.tell()
        stream.seek(0)
    except (OSError,AttributeError):
        raise APIError(422,'INVALID_FIELD','Không đọc được dung lượng tệp.')
    from flask import current_app
    if size>current_app.config['MAX_FILE_SIZE']:
        raise APIError(413,'FILE_TOO_LARGE','Tệp vượt giới hạn 100 MB.')
    if size<0:
        raise APIError(422,'INVALID_FIELD','Dung lượng tệp không hợp lệ.')
    user_lock(user_id)
    folder_for_user(user_id,folder_id)
    check_duplicate(File,user_id,folder_id,name)
    reserve(user_id,size)
    key=f'users/{user_id}/{uuid.uuid4().hex}'
    mime=(file.mimetype or mimetypes.guess_type(name)[0] or 'application/octet-stream')[:255]
    try:
        garage_service.upload(key,stream,mime)
        user_lock(user_id)
        folder_for_user(user_id,folder_id)
        check_duplicate(File,user_id,folder_id,name)
        record=File(user_id=user_id,folder_id=folder_id,name=name,object_key=key,
                    size_bytes=size,mime_type=mime,storage_state='ready')
        usage=lock_usage(user_id)
        usage.reserved_bytes-=size
        usage.used_bytes+=size
        db.session.add(record)
        db.session.flush()
        result = record.to_dict()
        db.session.commit()
    except Exception:
        db.session.rollback()
        try:
            garage_service.delete(key)
        except APIError:
            # A reconciliation job must clean any orphan key if deletion fails.
            current_app.logger.error('Garage orphan cleanup needed for object %s',key)
        try:
            release(user_id,size)
        except Exception:
            current_app.logger.exception('Quota reservation cleanup failed')
        raise
    return ok(result,201)


@api.get('/files/<file_id>')
@login_required
def file_detail(file_id):
    record=file_for_user(current_user().id,require_uuid(file_id))
    return ok(record.to_dict())


@api.get('/files/<file_id>/download')
@login_required
def download_file(file_id):
    record=file_for_user(current_user().id,require_uuid(file_id))
    body=garage_service.stream_object(record.object_key)
    def chunks():
        try:
            while True:
                chunk=body.read(1024*256)
                if not chunk:
                    break
                yield chunk
        finally:
            body.close()
    disposition="attachment; filename=download; filename*=UTF-8''"+quote(record.name,safe='')
    resp=Response(stream_with_context(chunks()),mimetype='application/octet-stream')
    resp.headers['Content-Disposition']=disposition
    resp.headers['Content-Length']=str(record.size_bytes)
    resp.headers['Cache-Control']='private, no-store'
    return resp


@api.patch('/files/<file_id>')
@login_required
def update_file(file_id):
    user_id=current_user().id
    data=json_object()
    if not any(k in data for k in ('name','parent_id')):
        raise APIError(422,'INVALID_FIELD','Cần tên hoặc thư mục đích.')
    user_lock(user_id)
    record=file_for_user(user_id,require_uuid(file_id))
    name=safe_name(data['name']) if 'name' in data else record.name
    target=parent_id(data['parent_id']) if 'parent_id' in data else record.folder_id
    folder_for_user(user_id,target)
    check_duplicate(File,user_id,target,name,record.id)
    record.name=name
    record.folder_id=target
    db.session.commit()
    return ok(record.to_dict())


@api.delete('/files/<file_id>')
@login_required
def trash_file(file_id):
    user_id=current_user().id
    user_lock(user_id)
    record=file_for_user(user_id,require_uuid(file_id))
    record.deleted_at=utcnow()
    db.session.commit()
    return ok({'id':record.id,'trashed':True})


@api.get('/trash')
@login_required
def list_trash():
    page,size=pagination()
    rows=trash_view(current_user().id)
    rows.sort(key=lambda v:v['deleted_at'],reverse=True)
    total=len(rows)
    items=[{'type':item['type'],'id':item['id'],'name':item['name'],'deleted_at':iso(item['deleted_at'])} for item in rows[(page-1)*size:page*size]]
    return ok(items,meta={'page':page,'page_size':size,'total':total})


@api.post('/trash/<kind>/<item_id>/restore')
@login_required
def restore_trash(kind,item_id):
    user_id=current_user().id
    if kind not in ('files','folders'):
        raise APIError(404,'RESOURCE_NOT_FOUND','Không tìm thấy dữ liệu.')
    data=json_object()
    user_lock(user_id)
    fid=require_uuid(item_id)
    target_overridden='parent_id' in data
    target=parent_id(data.get('parent_id','root')) if target_overridden else None
    if kind=='files':
        record=file_for_user(user_id,fid,allow_deleted=True)
        if record.deleted_at is None:
            raise APIError(409,'INVALID_STATE','Tệp chưa nằm trong thùng rác.')
        if not target_overridden:
            target=record.folder_id
            if target and folder_is_trashed(db.session.get(Folder,target)):
                target=None
        folder_for_user(user_id,target)
        check_duplicate(File,user_id,target,record.name,record.id)
        record.folder_id=target
        record.deleted_at=None
        record.storage_state='ready'
        db.session.commit()
        return ok(record.to_dict())
    record=folder_for_user(user_id,fid,allow_deleted=True)
    if record.deleted_at is None:
        raise APIError(409,'INVALID_STATE','Thư mục chưa nằm trong thùng rác.')
    if not target_overridden:
        target=record.parent_id
        if target and folder_is_trashed(db.session.get(Folder,target)):
            target=None
    folder_for_user(user_id,target)
    if target == record.id or target in {r.id for r in descendants(record,user_id)}:
        raise APIError(409,'INVALID_STATE','Không thể khôi phục vào thư mục con.')
    check_duplicate(Folder,user_id,target,record.name,record.id)
    record.parent_id=target
    record.deleted_at=None
    db.session.commit()
    return ok(record.to_dict())


@api.delete('/trash/<kind>/<item_id>')
@login_required
def remove_permanently(kind,item_id):
    user_id=current_user().id
    if kind not in ('files','folders'):
        raise APIError(404,'RESOURCE_NOT_FOUND','Không tìm thấy dữ liệu.')
    fid=require_uuid(item_id)
    if kind=='files':
        record=file_for_user(user_id,fid,allow_deleted=True)
        if record.deleted_at is None:
            raise APIError(409,'INVALID_STATE','Chỉ xóa vĩnh viễn tệp trong thùng rác.')
        hard_delete_file(user_id,record)
    else:
        record=folder_for_user(user_id,fid,allow_deleted=True)
        if record.deleted_at is None:
            raise APIError(409,'INVALID_STATE','Chỉ xóa vĩnh viễn thư mục trong thùng rác.')
        hard_delete_folder(user_id,record)
    return ok({'id':fid,'permanently_deleted':True})
