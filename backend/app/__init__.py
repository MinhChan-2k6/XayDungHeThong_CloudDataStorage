from pathlib import Path
from flask import Flask, send_from_directory
from app.config import Config
from app.extensions import db, migrate
from app.utils.errors import register_errors
from app.utils.security import verify_csrf


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get('SECRET_KEY'):
        raise RuntimeError('SECRET_KEY is required; configure backend/.env')
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        raise RuntimeError('DATABASE_URL is required; configure backend/.env')
    if not app.config.get('TESTING') and (len(app.config['SECRET_KEY']) < 32 or 'REPLACE' in app.config['SECRET_KEY']):
        raise RuntimeError('Choose a random 32+-character SECRET_KEY')
    db.init_app(app)
    migrate.init_app(app, db)
    from app import models  # noqa: F401  -- register tables for migrations
    from app.routes import register_routes
    register_routes(app)
    register_errors(app)
    app.before_request(verify_csrf)
    from app.database_seed import seed_plans, promote_admin
    app.cli.add_command(seed_plans)
    app.cli.add_command(promote_admin)
    if app.config['SERVE_FRONTEND']:
        frontend = Path(__file__).resolve().parents[2] / 'frontend'
        @app.get('/')
        @app.get('/index.html')
        def home():
            return send_from_directory(frontend, 'index.html')
        @app.get('/pages/<path:filename>')
        def page(filename):
            return send_from_directory(frontend / 'pages', filename)
        @app.get('/assets/<path:filename>')
        def assets(filename):
            return send_from_directory(frontend / 'assets', filename)

    @app.after_request
    def secure_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Cache-Control'] = 'no-store' if response.mimetype == 'application/json' else response.headers.get('Cache-Control', 'no-store')
        return response
    return app
