"""All secrets and deployment-specific values come from the environment."""
import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')


def get_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', '')
    SERVE_FRONTEND = get_bool('SERVE_FRONTEND', False)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', '')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 1800}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = get_bool('COOKIE_SECURE', False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE + 1024 * 1024
    GARAGE_ENDPOINT = os.getenv('GARAGE_ENDPOINT', '')
    GARAGE_REGION = os.getenv('GARAGE_REGION', 'garage')
    GARAGE_BUCKET = os.getenv('GARAGE_BUCKET', '')
    GARAGE_ACCESS_KEY = os.getenv('GARAGE_ACCESS_KEY', '')
    GARAGE_SECRET_KEY = os.getenv('GARAGE_SECRET_KEY', '')
    VNPAY_TMN_CODE = os.getenv('VNPAY_TMN_CODE', '')
    VNPAY_HASH_SECRET = os.getenv('VNPAY_HASH_SECRET', '')
    VNPAY_PAYMENT_URL = os.getenv('VNPAY_PAYMENT_URL', 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html')
    VNPAY_RETURN_URL = os.getenv('VNPAY_RETURN_URL', '')
    # Only explicitly allow testing support through application test configuration.
