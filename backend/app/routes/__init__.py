from flask import Blueprint

api = Blueprint('api', __name__, url_prefix='/api/v1')


def register_routes(app):
    from app.routes import auth, users, files, folders, plans, billing, payments, admin, health  # noqa: F401
    app.register_blueprint(api)
