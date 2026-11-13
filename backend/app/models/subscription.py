from app.extensions import db
from app.models.user import uid, utcnow, POS_BIG, POS_INT, DATETIME6
from app.utils.validators import iso


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    id = db.Column(db.CHAR(36), primary_key=True, default=uid)
    user_id = db.Column(db.CHAR(36), db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    plan_id = db.Column(db.CHAR(36), db.ForeignKey('plans.id', ondelete='RESTRICT'), nullable=False)
    order_id = db.Column(db.CHAR(36), nullable=True)
    quota_bytes = db.Column(POS_BIG, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='active')
    # MySQL has no partial UNIQUE; inactive rows generate NULL and do not conflict.
    active_user_id = db.Column(db.CHAR(36), db.Computed("CASE WHEN status = 'active' THEN user_id ELSE NULL END", persisted=True))
    started_at = db.Column(DATETIME6, nullable=False, default=utcnow)
    expires_at = db.Column(DATETIME6)
    ended_at = db.Column(DATETIME6)
    created_at = db.Column(DATETIME6, nullable=False, default=utcnow)
    __table_args__ = (
        db.UniqueConstraint('order_id', name='uq_subscriptions_order_id'),
        db.UniqueConstraint('active_user_id', name='uq_subscriptions_active_user_id'),
        db.ForeignKeyConstraint(['user_id','order_id'],['orders.user_id','orders.id'],name='fk_subscription_owner_order',ondelete='RESTRICT'),
        db.Index('ix_subscription_user_status_exp', 'user_id','status','expires_at'),
    )
    def to_dict(self, plan, used):
        return dict(plan={'id':plan.id,'code':plan.code,'name':plan.name}, status=self.status,
                    quota_bytes=self.quota_bytes, used_bytes=used, started_at=iso(self.started_at),
                    expires_at=iso(self.expires_at))
