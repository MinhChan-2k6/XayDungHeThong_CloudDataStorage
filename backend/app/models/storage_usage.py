from app.extensions import db
from app.models.user import utcnow, POS_BIG, DATETIME6


class StorageUsage(db.Model):
    __tablename__ = 'storage_usage'
    user_id = db.Column(db.CHAR(36), db.ForeignKey('users.id', ondelete='RESTRICT'), primary_key=True)
    used_bytes = db.Column(POS_BIG, nullable=False, default=0)
    reserved_bytes = db.Column(POS_BIG, nullable=False, default=0)
    updated_at = db.Column(DATETIME6, nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        db.CheckConstraint('used_bytes >= 0', name='ck_storage_used_positive'),
        db.CheckConstraint('reserved_bytes >= 0', name='ck_storage_reserved_positive'),
    )
