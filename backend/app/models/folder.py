from app.extensions import db
from app.models.user import uid, utcnow, POS_BIG, POS_INT, DATETIME6
from app.utils.validators import iso


class Folder(db.Model):
    __tablename__ = 'folders'
    id = db.Column(db.CHAR(36), primary_key=True, default=uid)
    user_id = db.Column(db.CHAR(36), db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    parent_id = db.Column(db.CHAR(36), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    deleted_at = db.Column(DATETIME6)
    # Technical generated columns: enforce unique active name per parent, including root.
    active_parent = db.Column(db.CHAR(36), db.Computed("CASE WHEN deleted_at IS NULL THEN COALESCE(parent_id, 'root') ELSE NULL END", persisted=True))
    active_name = db.Column(db.String(255), db.Computed("CASE WHEN deleted_at IS NULL THEN LOWER(name) ELSE NULL END", persisted=True))
    created_at = db.Column(DATETIME6, nullable=False, default=utcnow)
    updated_at = db.Column(DATETIME6, nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'id', name='uq_folder_owner_id'),
        db.UniqueConstraint('user_id', 'active_parent', 'active_name', name='uq_folder_active_name'),
        db.ForeignKeyConstraint(['user_id', 'parent_id'], ['folders.user_id','folders.id'], name='fk_folder_owner_parent', ondelete='RESTRICT'),
        db.Index('ix_folder_owner_parent_deleted', 'user_id','parent_id','deleted_at'),
    )
    def to_dict(self):
        return dict(id=self.id, name=self.name, parent_id=self.parent_id or 'root',
                    created_at=iso(self.created_at), updated_at=iso(self.updated_at))
