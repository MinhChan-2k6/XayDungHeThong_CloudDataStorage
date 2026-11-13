from app.extensions import db
from app.models.user import uid, utcnow, POS_BIG, POS_INT, DATETIME6


class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.CHAR(36), primary_key=True, default=uid)
    code = db.Column(db.String(32), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    quota_bytes = db.Column(POS_BIG, nullable=False)
    price_vnd = db.Column(POS_BIG, nullable=False)
    duration_days = db.Column(POS_INT)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(DATETIME6, nullable=False, default=utcnow)
    updated_at = db.Column(DATETIME6, nullable=False, default=utcnow, onupdate=utcnow)
    __table_args__ = (
        db.UniqueConstraint('code', name='uq_plans_code'),
        db.CheckConstraint('quota_bytes >= 0', name='ck_plan_quota_positive'),
        db.CheckConstraint('price_vnd >= 0', name='ck_plan_price_positive'),
    )
    def to_dict(self):
        return dict(id=self.id, code=self.code, name=self.name, quota_bytes=self.quota_bytes,
                    price_vnd=self.price_vnd, duration_days=self.duration_days, is_active=self.is_active)
