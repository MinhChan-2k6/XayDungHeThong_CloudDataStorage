from app.extensions import db
from app.models.user import uid, utcnow, POS_BIG, POS_INT, DATETIME6
from app.utils.validators import iso


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.CHAR(36), primary_key=True, default=uid)
    user_id = db.Column(db.CHAR(36), db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    plan_id = db.Column(db.CHAR(36), db.ForeignKey('plans.id', ondelete='RESTRICT'), nullable=False)
    order_code = db.Column(db.String(40), nullable=False)
    amount_vnd = db.Column(POS_BIG, nullable=False)
    quota_bytes = db.Column(POS_BIG, nullable=False)
    duration_days = db.Column(POS_INT, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='pending')
    created_at = db.Column(DATETIME6, nullable=False, default=utcnow)
    updated_at = db.Column(DATETIME6, nullable=False, default=utcnow, onupdate=utcnow)
    paid_at = db.Column(DATETIME6)
    __table_args__ = (db.UniqueConstraint('order_code',name='uq_orders_order_code'),
                      db.UniqueConstraint('user_id','id',name='uq_order_user_id'),
                      db.Index('ix_order_user_created','user_id','created_at'))
    def to_dict(self, plan_name=None):
        return dict(id=self.id, plan_id=self.plan_id, plan_name=plan_name, amount_vnd=self.amount_vnd,
                    status=self.status, created_at=iso(self.created_at), paid_at=iso(self.paid_at))
