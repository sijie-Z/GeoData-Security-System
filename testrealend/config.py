import os

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
    JWT_ACCESS_TOKEN_EXPIRES = 7200  # 2 hours in seconds
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days in seconds
    JWT_BLOCKLIST_ENABLED = True

    # Rate limiter
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_STRATEGY = 'fixed-window'

    # CORS
    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS', 'http://localhost:5174,http://localhost:5173'
    ).split(',')

    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # Cache TTL (seconds)
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_DEFAULT_TIMEOUT', '300'))
    CACHE_DASHBOARD_TIMEOUT = int(os.environ.get('CACHE_DASHBOARD_TIMEOUT', '120'))


class DevelopmentConfig(Config):
    DEBUG = True

    def __init__(self):
        super().__init__()
        insecure = {'dev-only-key-replace-in-production', 'dev-only-jwt-key-replace-in-production'}
        if self.SECRET_KEY in insecure or self.JWT_SECRET_KEY in insecure:
            import logging
            logging.warning("Using insecure dev keys — set SECRET_KEY and JWT_SECRET_KEY env vars for production")


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        super().__init__()
        insecure = {'dev-only-key-replace-in-production', 'dev-only-jwt-key-replace-in-production'}
        if self.SECRET_KEY in insecure or self.JWT_SECRET_KEY in insecure:
            raise RuntimeError("Production requires SECRET_KEY and JWT_SECRET_KEY environment variables")


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_BINDS = {
        'mysql_db': 'sqlite:///test.db',
        'postgres_db': 'sqlite:///test.db',
    }
    JWT_ACCESS_TOKEN_EXPIRES = 60
    RATELIMIT_ENABLED = False


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    if env == 'testing':
        return TestingConfig
    return ProductionConfig if env == 'production' else DevelopmentConfig
