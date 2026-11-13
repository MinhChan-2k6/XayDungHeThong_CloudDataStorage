from conftest import register,login


def test_register_login_logout_and_csrf(client,csrf):
    res=register(client,csrf,'test@example.com')
    assert res.status_code==201
    assert 'password_hash' not in str(res.json)
    assert register(client,csrf,'test@example.com').status_code==409
    assert client.post('/api/v1/auth/login',json={'email':'test@example.com','password':'Password123'}).status_code==403
    assert login(client,csrf,'test@example.com').status_code==200
    assert client.get('/api/v1/auth/me').json['data']['user']['email']=='test@example.com'
    assert client.post('/api/v1/auth/logout',headers={'X-CSRF-Token':csrf()}).status_code==200
    assert client.get('/api/v1/auth/me').status_code==401


def test_plan_seed_and_quota(client,csrf):
    res=client.get('/api/v1/plans').json['data']
    assert [(p['code'],p['price_vnd']) for p in res]==[('free',0),('basic',10000),('vip',20000)]
    register(client,csrf,'free@example.com');login(client,csrf,'free@example.com')
    result=client.get('/api/v1/dashboard/summary').json['data']
    assert result['storage']['quota_bytes']==500*1024*1024
