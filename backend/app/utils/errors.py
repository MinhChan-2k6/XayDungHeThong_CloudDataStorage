from flask import jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def ok(data, status=200, meta=None):
    response = {'success': True, 'data': data}
    if meta is not None:
        response['meta'] = meta
    return jsonify(response), status


def fail(error):
    item = {'code': error.code, 'message': error.message}
    if error.details is not None:
        item['details'] = error.details
    return jsonify({'success': False, 'error': item}), error.status


def register_errors(app):
    @app.errorhandler(APIError)
    def api_error(e):
        return fail(e)

    @app.errorhandler(413)
    def too_large(e):
        return fail(APIError(413, 'FILE_TOO_LARGE', 'Tệp vượt giới hạn 100 MB.'))

    @app.errorhandler(HTTPException)
    def http_error(e):
        return fail(APIError(e.code or 500, 'HTTP_ERROR', e.description or 'Yêu cầu không hợp lệ.'))

    @app.errorhandler(Exception)
    def unhandled(e):
        # Stack trace is logged server-side only.
        app.logger.exception('Unhandled API exception')
        return fail(APIError(500, 'INTERNAL_ERROR', 'Máy chủ gặp lỗi.'))
