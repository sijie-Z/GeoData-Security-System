import os

# Resolve the project root (parent of this config file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "test")


class Config:
    """Base configuration. All sensitive values must be set via environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-key-replace-in-production")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-jwt-key-replace-in-production")

    # File storage
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", os.path.join(DATA_DIR, "upload_folder"))
    WATERMARK_FOLDER = os.environ.get("WATERMARK_FOLDER", os.path.join(DATA_DIR, "watermark_folder"))
    EXTRACTED_FOLDER = os.environ.get("EXTRACTED_FOLDER", os.path.join(DATA_DIR, "extracted_folder"))
    # v3 personalized delivery artifacts (one <uuid>/ subfolder per delivery)
    DELIVERY_FOLDER = os.environ.get("DELIVERY_FOLDER", os.path.join(WATERMARK_FOLDER, "deliveries"))

    # Database (MySQL for business data, PostgreSQL for spatial data)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "mysql+mysqldb://root:root@127.0.0.1/esri_test?connect_timeout=5"
    )
    SQLALCHEMY_BINDS = {
        "mysql_db": os.environ.get("MYSQL_URI", "mysql+mysqldb://root:root@127.0.0.1/esri_test?connect_timeout=5"),
        "postgres_db": os.environ.get(
            "POSTGRES_URI", "postgresql://postgres:root@127.0.0.1/esri_test?connect_timeout=5"
        ),
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLAlchemy engine options — prevent stale connections and connection drops
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", "10")),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "20")),
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "3600")),  # Recycle connections every hour
        "pool_pre_ping": True,  # Verify connections before use (prevents MySQL "server has gone away")
        "connect_args": {
            "connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "10")),
        },
    }

    # JWT
    JWT_ACCESS_TOKEN_EXPIRES = 7200  # 2 hours in seconds
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days in seconds
    JWT_BLOCKLIST_ENABLED = True
    # Identity is a dict throughout this codebase (get_jwt_identity() returns a dict).
    # Flask-JWT-Extended >= 4.7 defaults JWT_VERIFY_SUB to True; combined with PyJWT
    # >= 2.10 that rejects dict identities ("Subject must be a string"), so every
    # authenticated request 401s on a fresh install. Disable the check to keep the
    # existing dict contract (stringifying identity would be an auth-wide rewrite).
    JWT_VERIFY_SUB = False

    # Rate limiter — uses Redis for multi-worker consistency (falls back to memory)
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", os.environ.get("REDIS_URL", "memory://"))
    RATELIMIT_STRATEGY = "fixed-window"

    # CORS — broader origins for development, configurable for production
    CORS_ORIGINS = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5174,http://localhost:5173,http://localhost:5175,http://localhost:5176,http://localhost:5177",
    ).split(",")

    # Redis
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Cache TTL (seconds)
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get("CACHE_DEFAULT_TIMEOUT", "300"))
    CACHE_DASHBOARD_TIMEOUT = int(os.environ.get("CACHE_DASHBOARD_TIMEOUT", "120"))

    # GeoServer
    GEOSERVER_URL = os.environ.get("GEOSERVER_URL", "http://localhost:8080/geoserver")
    GEOSERVER_USER = os.environ.get("GEOSERVER_USER", "admin")
    GEOSERVER_PASSWORD = os.environ.get("GEOSERVER_PASSWORD", "geoserver")
    GEOSERVER_WORKSPACE = os.environ.get("GEOSERVER_WORKSPACE", "test")


class DevelopmentConfig(Config):
    DEBUG = True

    def __init__(self):
        super().__init__()
        insecure = {"dev-only-key-replace-in-production", "dev-only-jwt-key-replace-in-production"}
        if self.SECRET_KEY in insecure or self.JWT_SECRET_KEY in insecure:
            import logging

            logging.warning("Using insecure dev keys — set SECRET_KEY and JWT_SECRET_KEY env vars for production")


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        super().__init__()
        insecure = {"dev-only-key-replace-in-production", "dev-only-jwt-key-replace-in-production"}
        if self.SECRET_KEY in insecure or self.JWT_SECRET_KEY in insecure:
            raise RuntimeError("Production requires SECRET_KEY and JWT_SECRET_KEY environment variables")


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    # Tests must stay hermetic: point the default engine at SQLite too, so a
    # query whose bind cannot be resolved (e.g. aggregate Selects without a
    # mapped entity) lands on the same test DB instead of the default MySQL
    # URI, which fails wherever no MySQL is running (CI containers).
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"
    # The base engine options carry MySQL-only connect_args, which sqlite3.connect()
    # rejects; keep the pooling settings and drop the connect_args for SQLite.
    SQLALCHEMY_ENGINE_OPTIONS = {**Config.SQLALCHEMY_ENGINE_OPTIONS, "connect_args": {}}
    SQLALCHEMY_BINDS = {
        "mysql_db": "sqlite:///test.db",
        "postgres_db": "sqlite:///test.db",
    }
    JWT_ACCESS_TOKEN_EXPIRES = 60
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    if env == "testing":
        return TestingConfig
    return ProductionConfig if env == "production" else DevelopmentConfig
