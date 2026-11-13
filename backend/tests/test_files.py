import io
from conftest import register,login


def test_upload_download_trash_quota_and_isolation(client,csrf,monkeypatch):
    import app.services.garage_service as s3
    objects={}
    monkeypatch.setattr(s3,'upload',lambda key,stream,mime:objects.__setitem__(key,stream.read()))
    monkeypatch.setattr(s3,'delete',lambda key:objects.pop(key,None))
    monkeypatch.setattr(s3,'stream_object',lambda key:io.BytesIO(objects[key]))
    register(client,csrf,'a@example.com');login(client,csrf,'a@example.com')
    folder=client.post('/api/v1/folders',json={'name':'ABC','parent_id':'root'},headers={'X-CSRF-Token':csrf()})
    assert folder.status_code==201
    uploaded=client.post('/api/v1/files',data={'parent_id':folder.json['data']['id'],'file':(io.BytesIO(b'hello!'),'file.txt')},
                         headers={'X-CSRF-Token':csrf()})
    assert uploaded.status_code==201,uploaded.json
    file_id=uploaded.json['data']['id']
    assert client.get(f'/api/v1/files/{file_id}/download').data==b'hello!'
    assert client.get('/api/v1/dashboard/summary').json['data']['storage']['used_bytes']==6
    # B cannot see A's file.
    client.post('/api/v1/auth/logout',headers={'X-CSRF-Token':csrf()})
    register(client,csrf,'b@example.com');login(client,csrf,'b@example.com')
    assert client.get(f'/api/v1/files/{file_id}').status_code==404
    assert client.get(f'/api/v1/files/{file_id}/download').status_code==404
    client.post('/api/v1/auth/logout',headers={'X-CSRF-Token':csrf()})
    login(client,csrf,'a@example.com')
    assert client.delete(f'/api/v1/files/{file_id}',headers={'X-CSRF-Token':csrf()}).status_code==200
    assert client.get('/api/v1/dashboard/summary').json['data']['storage']['used_bytes']==6
    assert client.delete(f'/api/v1/trash/files/{file_id}',headers={'X-CSRF-Token':csrf()}).status_code==200
    assert client.get('/api/v1/dashboard/summary').json['data']['storage']['used_bytes']==0
