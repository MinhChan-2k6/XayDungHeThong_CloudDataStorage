import uuid
from datetime import datetime, timezone
from app.extensions import db
from sqlalchemy.dialects import mysql

# Preserve the exact MySQL 8 numeric/time types defined in the approved ERD.
POS_BIG = db.BigInteger().with_variant(mysql.BIGINT(unsigned=True), 'mysql')
POS_INT = db.Integer().with_variant(mysql.INTEGER(unsigned=True), 'mysql')
DATETIME6 = db.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql')
from app.utils.validators import iso


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uid():
    return str(uuid.uuid4())


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.CHAR(36), primary_key=True, default=uid)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(16), nullable=False, default='user')
    status = db.Column(db.String(16), nullable=False, default='active')
    created_at = db.Column(DATETIME6, nullable=False, default=utcnow)
    updated_at = db.Column(DATETIME6, nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (db.UniqueConstraint('email', name='uq_users_email'),)
    def to_dict(self):
        return dict(id=self.id, full_name=self.full_name, email=self.email, role=self.role,
                    status=self.status, created_at=iso(self.created_at))
