import io
from conftest import register,login
from app.models import StorageUsage
from app.extensions import db


def test_reject_quota_before_s3(client,csrf,monkeypatch,app):
    register(client,csrf,'a@example.com');login(client,csrf,'a@example.com')
    with app.app_context():
        usage=db.session.query(StorageUsage).first()
        usage.used_bytes=500*1024*1024
        db.session.commit()
    import app.services.garage_service as garage
    def fail_upload(*args):
        raise AssertionError('S3 should not be called when over quota')
    monkeypatch.setattr(garage,'upload',fail_upload)
    result=client.post('/api/v1/files',data={'file':(io.BytesIO(b'A'),'a.txt'),'parent_id':'root'},
                       headers={'X-CSRF-Token':csrf()})
    assert result.status_code==409 and result.json['error']['code']=='QUOTA_EXCEEDED'
