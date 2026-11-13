"""Initial CloudDS schema: nine tables matching docs/03-database-erd.md.

Revision ID: 0001_initial
Revises: None

This revision deliberately freezes the column definitions rather than calling
metadata.create_all(), so future model edits cannot change historical migrations.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


# MySQL uses unsigned numeric types; SQLite uses equivalent signed types in tests.
BIG = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), 'mysql')
UINT = sa.Integer().with_variant(mysql.INTEGER(unsigned=True), 'mysql')
DT = sa.DateTime().with_variant(mysql.DATETIME(fsp=6), 'mysql')


def upgrade():
    op.create_table('users',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('full_name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('created_at', DT, nullable=False),
        sa.Column('updated_at', DT, nullable=False),
        sa.UniqueConstraint('email', name='uq_users_email'),
    )

    op.create_table('plans',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('code', sa.String(32), nullable=False),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('quota_bytes', BIG, nullable=False),
        sa.Column('price_vnd', BIG, nullable=False),
        sa.Column('duration_days', UINT),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', DT, nullable=False),
        sa.Column('updated_at', DT, nullable=False),
        sa.UniqueConstraint('code', name='uq_plans_code'),
        sa.CheckConstraint('quota_bytes >= 0', name='ck_plan_quota_positive'),
        sa.CheckConstraint('price_vnd >= 0', name='ck_plan_price_positive'),
    )

    op.create_table('storage_usage',
        sa.Column('user_id', sa.CHAR(36), primary_key=True),
        sa.Column('used_bytes', BIG, nullable=False),
        sa.Column('reserved_bytes', BIG, nullable=False),
        sa.Column('updated_at', DT, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.CheckConstraint('used_bytes >= 0', name='ck_storage_used_positive'),
        sa.CheckConstraint('reserved_bytes >= 0', name='ck_storage_reserved_positive'),
    )

    op.create_table('folders',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('parent_id', sa.CHAR(36)),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('deleted_at', DT),
        sa.Column('active_parent', sa.CHAR(36), sa.Computed(
            "CASE WHEN deleted_at IS NULL THEN COALESCE(parent_id, 'root') ELSE NULL END", persisted=True)),
        sa.Column('active_name', sa.String(255), sa.Computed(
            'CASE WHEN deleted_at IS NULL THEN LOWER(name) ELSE NULL END', persisted=True)),
        sa.Column('created_at', DT, nullable=False),
        sa.Column('updated_at', DT, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('user_id','id', name='uq_folder_owner_id'),
        sa.ForeignKeyConstraint(['user_id','parent_id'], ['folders.user_id','folders.id'],
                                name='fk_folder_owner_parent', ondelete='RESTRICT'),
        sa.UniqueConstraint('user_id','active_parent','active_name', name='uq_folder_active_name'),
    )
    op.create_index('ix_folders_user_id', 'folders', ['user_id'])
    op.create_index('ix_folder_owner_parent_deleted', 'folders', ['user_id','parent_id','deleted_at'])

    op.create_table('files',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('folder_id', sa.CHAR(36)),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('object_key', sa.String(512), nullable=False),
        sa.Column('size_bytes', BIG, nullable=False),
        sa.Column('mime_type', sa.String(255), nullable=False),
        sa.Column('storage_state', sa.String(16), nullable=False),
        sa.Column('deleted_at', DT),
        sa.Column('active_parent', sa.CHAR(36), sa.Computed(
            "CASE WHEN deleted_at IS NULL THEN COALESCE(folder_id, 'root') ELSE NULL END", persisted=True)),
        sa.Column('active_name', sa.String(255), sa.Computed(
            'CASE WHEN deleted_at IS NULL THEN LOWER(name) ELSE NULL END', persisted=True)),
        sa.Column('created_at', DT, nullable=False),
        sa.Column('updated_at', DT, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id','folder_id'], ['folders.user_id','folders.id'],
                                name='fk_file_owner_folder', ondelete='RESTRICT'),
        sa.UniqueConstraint('object_key', name='uq_files_object_key'),
        sa.UniqueConstraint('user_id','active_parent','active_name', name='uq_file_active_name'),
        sa.CheckConstraint('size_bytes >= 0', name='ck_file_size_positive'),
    )
    op.create_index('ix_files_user_id','files',['user_id'])
    op.create_index('ix_file_owner_folder_deleted','files',['user_id','folder_id','deleted_at'])

    op.create_table('orders',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('plan_id', sa.CHAR(36), nullable=False),
        sa.Column('order_code', sa.String(40), nullable=False),
        sa.Column('amount_vnd', BIG, nullable=False),
        sa.Column('quota_bytes', BIG, nullable=False),
        sa.Column('duration_days', UINT, nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('created_at', DT, nullable=False),
        sa.Column('updated_at', DT, nullable=False),
        sa.Column('paid_at', DT),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('user_id','id',name='uq_order_user_id'),
        sa.UniqueConstraint('order_code',name='uq_orders_order_code'),
    )
    op.create_index('ix_orders_user_id','orders',['user_id'])
    op.create_index('ix_order_user_created','orders',['user_id','created_at'])

    op.create_table('subscriptions',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('plan_id', sa.CHAR(36), nullable=False),
        sa.Column('order_id', sa.CHAR(36)),
        sa.Column('quota_bytes', BIG, nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('active_user_id', sa.CHAR(36), sa.Computed(
            "CASE WHEN status = 'active' THEN user_id ELSE NULL END", persisted=True)),
        sa.Column('started_at', DT, nullable=False),
        sa.Column('expires_at', DT),
        sa.Column('ended_at', DT),
        sa.Column('created_at', DT, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id','order_id'], ['orders.user_id','orders.id'],
                                name='fk_subscription_owner_order', ondelete='RESTRICT'),
        sa.UniqueConstraint('order_id',name='uq_subscriptions_order_id'),
        sa.UniqueConstraint('active_user_id',name='uq_subscriptions_active_user_id'),
    )
    op.create_index('ix_subscriptions_user_id','subscriptions',['user_id'])
    op.create_index('ix_subscription_user_status_exp','subscriptions',['user_id','status','expires_at'])

    op.create_table('payments',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('order_id', sa.CHAR(36), nullable=False),
        sa.Column('provider', sa.String(16), nullable=False),
        sa.Column('txn_ref', sa.String(64), nullable=False),
        sa.Column('provider_txn_no', sa.String(64)),
        sa.Column('amount_vnd', BIG, nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('response_code', sa.String(16)),
        sa.Column('created_at', DT, nullable=False),
        sa.Column('updated_at', DT, nullable=False),
        sa.Column('paid_at', DT),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('txn_ref',name='uq_payments_txn_ref'),
        sa.UniqueConstraint('provider_txn_no',name='uq_payments_provider_txn_no'),
    )
    op.create_index('ix_payments_order_id','payments',['order_id'])
    op.create_index('ix_payment_order_created','payments',['order_id','created_at'])

    op.create_table('invoices',
        sa.Column('id', sa.CHAR(36), primary_key=True),
        sa.Column('order_id', sa.CHAR(36), nullable=False),
        sa.Column('invoice_no', sa.String(40), nullable=False),
        sa.Column('amount_vnd', BIG, nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('issued_at', DT, nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('order_id',name='uq_invoices_order_id'),
        sa.UniqueConstraint('invoice_no',name='uq_invoices_invoice_no'),
    )


def downgrade():
    op.drop_table('invoices')
    op.drop_table('payments')
    op.drop_table('subscriptions')
    op.drop_table('orders')
    op.drop_table('files')
    op.drop_table('folders')
    op.drop_table('storage_usage')
    op.drop_table('plans')
    op.drop_table('users')
