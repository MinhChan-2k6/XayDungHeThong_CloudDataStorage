from sqlalchemy import text
from app.extensions import db
from app.routes import api
from app.utils.errors import ok, APIError


@api.get('/health')
def health():
    try:
        db.session.execute(text('SELECT 1'))
        return ok({'status':'ok'})
    except Exception:
        raise APIError(503, 'SERVICE_UNAVAILABLE', 'Database chưa sẵn sàng.')
