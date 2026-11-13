"""Idempotent seed. Run: flask --app wsgi seed-plans"""
import click
from flask.cli import with_appcontext
from sqlalchemy import select
from app.extensions import db
from app.models import Plan


@click.command('seed-plans')
@with_appcontext
def seed_plans():
    plans = (
        ('free','Free',500*1024*1024,0,None),
        ('basic','Basic',2*1024*1024*1024,10000,30),
        ('vip','VIP',5*1024*1024*1024,20000,30),
    )
    for code,name,quota,price,days in plans:
        existing=db.session.scalar(select(Plan).where(Plan.code==code))
        if not existing:
            db.session.add(Plan(code=code,name=name,quota_bytes=quota,price_vnd=price,
                                duration_days=days,is_active=True))
    db.session.commit()
    click.echo('Default plans are present (existing data left unchanged).')


@click.command('promote-admin')
@click.argument('email')
@with_appcontext
def promote_admin(email):
    """Explicit administrative action; signup never grants administrator rights."""
    from app.models import User
    user = db.session.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise click.ClickException('User not found.')
    user.role = 'admin'
    db.session.commit()
    click.echo('Admin role assigned to ' + user.email)
