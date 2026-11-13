from app.extensions import db
from app.models.user import uid, utcnow, POS_BIG, POS_INT, DATETIME6


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.CHAR(36), primary_key=True, default=uid)
    order_id = db.Column(db.CHAR(36), db.ForeignKey('orders.id', ondelete='RESTRICT'), nullable=False, index=True)
    provider = db.Column(db.String(16), nullable=False, default='vnpay')
    txn_ref = db.Column(db.String(64), nullable=False)
    provider_txn_no = db.Column(db.String(64))
    amount_vnd = db.Column(POS_BIG, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='pending')
    response_code = db.Column(db.String(16))
    created_at = db.Column(DATETIME6, nullable=False, default=utcnow)
    updated_at = db.Column(DATETIME6, nullable=False, default=utcnow, onupdate=utcnow)
    paid_at = db.Column(DATETIME6)
    __table_args__ = (
        db.UniqueConstraint('txn_ref', name='uq_payments_txn_ref'),
        db.UniqueConstraint('provider_txn_no', name='uq_payments_provider_txn_no'),db.Index('ix_payment_order_created','order_id','created_at'),)
