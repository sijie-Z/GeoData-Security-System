import logging
import os
import secrets

# Resolve the project root (parent of this config file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "test")


def _resolve_secret(name):
    """Return ``(value, from_env)``; an unset secret gets a random per-process value.

    The old public defaults (``dev-only-key-replace-in-production``) let anyone
    forge session cookies / JWTs on a deployment that forgot to configure the
    environment.  Generating a throwaway key keeps local development working
    (tokens simply die on restart) while removing the known-secret footgun.
    """
    value = os.environ.get(name)
    if value:
        return value, True
    return secrets.token_hex(32), False


_SECRET_KEY_VALUE, _SECRET_KEY_FROM_ENV = _resolve_secret("SECRET_KEY")
_JWT_SECRET_KEY_VALUE, _JWT_SECRET_KEY_FROM_ENV = _resolve_secret("JWT_SECRET_KEY")
_SECRETS_FROM_ENV = _SECRET_KEY_FROM_ENV and _JWT_SECRET_KEY_FROM_ENV
_APP_ENV = os.environ.get("FLASK_ENV", "development")

if not _SECRETS_FROM_ENV and _APP_ENV not in ("testing", "production"):
    logging.getLogger(__name__).warning(
        "SECRET_KEY/JWT_SECRET_KEY 未通过环境变量配置：本次启动已生成临时随机密钥，"
        "重启后所有已签发的会话/令牌都会失效。本地开发可接受；生产环境必须设置这两个变量。"
    )


class Config:
    """Base configuration. All sensitive values must be set via environment variables."""

    SECRET_KEY = _SECRET_KEY_VALUE
    JWT_SECRET_KEY = _JWT_SECRET_KEY_VALUE

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

    # EVM anchor (Sepolia testnet) — empty EVM_CONTRACT_ADDRESS = provider not configured.
    # The private key is NOT a config value: it lives in instance/keys/evm_sepolia.key
    # (git-ignored) and is read via evidence/evm.py.
    EVM_RPC_URL = os.environ.get("EVM_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com")
    EVM_CHAIN_ID = int(os.environ.get("EVM_CHAIN_ID", "11155111"))
    EVM_CONTRACT_ADDRESS = os.environ.get("EVM_CONTRACT_ADDRESS", "")
    EVM_ANCHOR_ENABLED = os.environ.get("EVM_ANCHOR_ENABLED", "auto")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        super().__init__()
        if not _SECRETS_FROM_ENV:
            raise RuntimeError("Production requires SECRET_KEY and JWT_SECRET_KEY environment variables")


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    # Deterministic fallback keeps tests hermetic when no env vars are set;
    # conftest.py sets explicit test keys, so this only covers other runners.
    SECRET_KEY = os.environ.get("SECRET_KEY") or "test-secret-key"
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or "test-jwt-secret-key"
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
    if env == "production":
        # ``from_object`` never instantiates the class, so ProductionConfig's
        # __init__ guard alone would not fire here — enforce it explicitly.
        if not _SECRETS_FROM_ENV:
            raise RuntimeError("Production requires SECRET_KEY and JWT_SECRET_KEY environment variables")
        return ProductionConfig
    return DevelopmentConfig
