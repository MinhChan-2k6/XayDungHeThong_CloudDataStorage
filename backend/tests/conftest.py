import pytest
from app import create_app
from app.extensions import db
from app.models import Plan


@pytest.fixture()
def app(tmp_path):
    flask_app = create_app({
        'TESTING': True,
        'SECRET_KEY':'test-only-unsafe',
        'SQLALCHEMY_DATABASE_URI':f'sqlite:///{tmp_path / "test.db"}',
        'SESSION_COOKIE_SECURE':False,
    })
    with flask_app.app_context():
        db.create_all()
        db.session.add_all([
            Plan(code='free',name='Free',quota_bytes=500*1024*1024,price_vnd=0,duration_days=None),
            Plan(code='basic',name='Basic',quota_bytes=2*1024**3,price_vnd=10000,duration_days=30),
            Plan(code='vip',name='VIP',quota_bytes=5*1024**3,price_vnd=20000,duration_days=30),
        ])
        db.session.commit()
    yield flask_app
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def csrf(client):
    def token():
        return client.get('/api/v1/auth/csrf').json['data']['csrf_token']
    return token


def register(client, csrf, email, pwd='Password123', name='Cloud User'):
    return client.post('/api/v1/auth/register',json={'full_name':name,'email':email,'password':pwd},
                       headers={'X-CSRF-Token':csrf()})


def login(client,csrf,email,pwd='Password123'):
    result=client.post('/api/v1/auth/login',json={'email':email,'password':pwd},
                       headers={'X-CSRF-Token':csrf()})
    csrf()  # new session CSRF after successful login
    return result
