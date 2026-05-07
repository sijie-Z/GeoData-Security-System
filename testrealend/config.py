import os
import sys

# Resolve the project root (parent of this config file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, 'test')


class Config:
    """Base configuration. All sensitive values must be set via environment variables."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-key-replace-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-only-jwt-key-replace-in-production')

    # File storage
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(DATA_DIR, 'upload_folder'))
    WATERMARK_FOLDER = os.environ.get('WATERMARK_FOLDER', os.path.join(DATA_DIR, 'watermark_folder'))
    EXTRACTED_FOLDER = os.environ.get('EXTRACTED_FOLDER', os.path.join(DATA_DIR, 'extracted_folder'))

    # Database (MySQL for business data, PostgreSQL for spatial data)
    SQLALCHEMY_BINDS = {
        'mysql_db': os.environ.get('MYSQL_URI', 'mysql+mysqldb://root:root@127.0.0.1/esri_test'),
        'postgres_db': os.environ.get('POSTGRES_URI', 'postgresql://postgres:root@127.0.0.1/esri_test'),
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    JWT_ACCESS_TOKEN_EXPIRES = 86400  # 24 hours in seconds
    JWT_REFRESH_TOKEN_EXPIRES = 2592000  # 30 days in seconds

    # Rate limiter
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_STRATEGY = 'fixed-window'

    # CORS
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 'http://localhost:5174,http://localhost:5173'
    ).split(',')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return ProductionConfig if env == 'production' else DevelopmentConfig
