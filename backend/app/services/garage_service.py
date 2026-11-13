"""Private S3-compatible Garage object store; bucket/key never exposed to browsers."""
from functools import lru_cache
import boto3
from botocore.client import Config as BotocoreConfig
from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app
from app.utils.errors import APIError


def client():
    conf = current_app.config
    needed = ('GARAGE_ENDPOINT', 'GARAGE_BUCKET', 'GARAGE_ACCESS_KEY', 'GARAGE_SECRET_KEY')
    if any(not conf.get(key) for key in needed):
        raise APIError(503, 'SERVICE_UNAVAILABLE', 'Garage chưa được cấu hình.')
    return boto3.client('s3', endpoint_url=conf['GARAGE_ENDPOINT'], region_name=conf['GARAGE_REGION'],
                        aws_access_key_id=conf['GARAGE_ACCESS_KEY'], aws_secret_access_key=conf['GARAGE_SECRET_KEY'],
                        config=BotocoreConfig(signature_version='s3v4', s3={'addressing_style':'path'},
                                              retries={'max_attempts':3,'mode':'standard'}))


def upload(key, stream, mime):
    try:
        client().upload_fileobj(stream, current_app.config['GARAGE_BUCKET'], key,
                                ExtraArgs={'ContentType': mime})
    except (BotoCoreError, ClientError, OSError) as exc:
        current_app.logger.warning('Garage upload error: %s', type(exc).__name__)
        raise APIError(503, 'SERVICE_UNAVAILABLE', 'Không thể lưu tệp lên Garage.') from exc


def stream_object(key):
    try:
        return client().get_object(Bucket=current_app.config['GARAGE_BUCKET'], Key=key)['Body']
    except (BotoCoreError, ClientError, OSError) as exc:
        current_app.logger.warning('Garage download error: %s', type(exc).__name__)
        raise APIError(503, 'SERVICE_UNAVAILABLE', 'Không thể tải tệp từ Garage.') from exc


def delete(key):
    try:
        client().delete_object(Bucket=current_app.config['GARAGE_BUCKET'], Key=key)
    except (BotoCoreError, ClientError, OSError) as exc:
        current_app.logger.warning('Garage delete error: %s', type(exc).__name__)
        raise APIError(503, 'SERVICE_UNAVAILABLE', 'Không thể xóa tệp khỏi Garage.') from exc
