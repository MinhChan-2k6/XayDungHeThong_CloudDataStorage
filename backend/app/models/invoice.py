from app.extensions import db
from app.models.user import uid, utcnow, POS_BIG, POS_INT, DATETIME6
from app.utils.validators import iso


class Invoice(db.Model):
    __tablename__ = 'invoices'
    id = db.Column(db.CHAR(36), primary_key=True, default=uid)
    order_id = db.Column(db.CHAR(36), db.ForeignKey('orders.id', ondelete='RESTRICT'), nullable=False)
    invoice_no = db.Column(db.String(40), nullable=False)
    amount_vnd = db.Column(POS_BIG, nullable=False)
    status = db.Column(db.String(16), nullable=False, default='issued')
    issued_at = db.Column(DATETIME6, nullable=False, default=utcnow)
    __table_args__ = (db.UniqueConstraint('order_id', name='uq_invoices_order_id'),
                      db.UniqueConstraint('invoice_no', name='uq_invoices_invoice_no'))
    def to_dict(self):
        return dict(id=self.id, order_id=self.order_id, amount_vnd=self.amount_vnd,
                    status=self.status, issued_at=iso(self.issued_at))
