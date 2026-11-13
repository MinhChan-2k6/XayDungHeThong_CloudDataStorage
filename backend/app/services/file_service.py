"""Cross-user isolation, folder hierarchy, trash, and coordinated S3 deletion."""
from sqlalchemy import select
from app.extensions import db
from app.models import File, Folder, User
from app.models.user import utcnow
from app.utils.errors import APIError
from app.services import garage_service
from app.services.quota_service import lock_usage


def user_lock(user_id):
    db.session.scalar(select(User).where(User.id == user_id).with_for_update())


def folder_for_user(user_id, folder_id, *, allow_deleted=False):
    if not folder_id:
        return None
    folder = db.session.scalar(select(Folder).where(Folder.id == folder_id, Folder.user_id == user_id).with_for_update())
    if folder is None or (not allow_deleted and folder_is_trashed(folder)):
        raise APIError(404, 'RESOURCE_NOT_FOUND', 'Không tìm thấy thư mục.')
    return folder


def folder_is_trashed(folder):
    if folder.deleted_at is not None:
        return True
    visited = {folder.id}
    while folder.parent_id:
        parent = db.session.get(Folder, folder.parent_id)
        if parent is None or parent.id in visited or parent.deleted_at is not None:
            return True
        visited.add(parent.id)
        folder = parent
    return False


def file_for_user(user_id, file_id, *, allow_deleted=False):
    item = db.session.scalar(select(File).where(File.id == file_id, File.user_id == user_id).with_for_update())
    if item is None or (not allow_deleted and (item.deleted_at or item.storage_state != 'ready' or (item.folder_id and folder_is_trashed(db.session.get(Folder, item.folder_id))))):
        raise APIError(404, 'RESOURCE_NOT_FOUND', 'Không tìm thấy tệp.')
    return item


def check_duplicate(model, user_id, dest_id, name, ignore=None):
    column = File.folder_id if model is File else Folder.parent_id
    qry = select(model.id).where(model.user_id == user_id, column == dest_id,
                                 model.name == name, model.deleted_at.is_(None))
    if ignore:
        qry = qry.where(model.id != ignore)
    if db.session.scalar(qry.with_for_update()):
        raise APIError(409, 'DUPLICATE_NAME', 'Tên đã tồn tại trong thư mục này.')


def descendants(root, user_id):
    """All descendants including deleted ones, breadth-first, without recursion cycles."""
    result = []
    seen = {root.id}
    queue = [root.id]
    while queue:
        children = db.session.scalars(select(Folder).where(Folder.user_id == user_id, Folder.parent_id.in_(queue))).all()
        queue = []
        for child in children:
            if child.id not in seen:
                result.append(child)
                queue.append(child.id)
                seen.add(child.id)
    return result


def move_folder(user_id, folder, target_id):
    if target_id == folder.id or target_id in {item.id for item in descendants(folder, user_id)}:
        raise APIError(409, 'INVALID_STATE', 'Không thể di chuyển thư mục vào chính nó hoặc thư mục con.')
    folder_for_user(user_id, target_id)
    folder.parent_id = target_id


def hard_delete_file(user_id, item):
    """Garage delete is idempotent; metadata is deleted only after successful S3 delete."""
    item.storage_state = 'deleting'
    db.session.commit()
    garage_service.delete(item.object_key)
    # Serialize with upload/reservation at the user row.
    user_lock(user_id)
    row = db.session.scalar(select(File).where(File.id == item.id, File.user_id == user_id).with_for_update())
    if row:
        usage = lock_usage(user_id)
        usage.used_bytes = max(0, usage.used_bytes - row.size_bytes)
        db.session.delete(row)
    db.session.commit()


def hard_delete_folder(user_id, folder):
    children = descendants(folder, user_id)
    ids = [folder.id] + [child.id for child in children]
    file_rows = db.session.scalars(select(File).where(File.user_id == user_id, File.folder_id.in_(ids))).all()
    for item in file_rows:
        hard_delete_file(user_id, item)
    # Delete leaves first; all objects already removed. Retry is safe after failures.
    user_lock(user_id)
    for child in reversed(children):
        db.session.delete(child)
    db.session.delete(folder)
    db.session.commit()


def trash_view(user_id):
    deleted_folders = db.session.scalars(select(Folder).where(Folder.user_id == user_id, Folder.deleted_at.is_not(None))).all()
    directly_trashed = [f for f in deleted_folders if not f.parent_id or not folder_is_trashed_ancestor(f)]
    file_items = db.session.scalars(select(File).where(File.user_id == user_id, File.deleted_at.is_not(None))).all()
    direct_files = [f for f in file_items if not f.folder_id or not folder_is_trashed(db.session.get(Folder, f.folder_id))]
    data = [dict(type='folder', id=f.id, name=f.name, deleted_at=f.deleted_at) for f in directly_trashed]
    data += [dict(type='file', id=f.id, name=f.name, deleted_at=f.deleted_at) for f in direct_files]
    return data


def folder_is_trashed_ancestor(folder):
    visited = {folder.id}
    while folder.parent_id:
        parent = db.session.get(Folder, folder.parent_id)
        if parent is None or parent.id in visited:
            return True
        if parent.deleted_at is not None:
            return True
        visited.add(parent.id)
        folder = parent
    return False
