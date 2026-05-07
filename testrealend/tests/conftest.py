import pytest
import os

# Set test environment before importing app
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret-key'

from app import create_app
from extension.extension import db as _db


@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 60  # 1 minute for tests
    yield app


@pytest.fixture(scope='function')
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    """Create a fresh database for each test."""
    with app.app_context():
        yield _db


@pytest.fixture
def auth_headers(client):
    """Get authenticated headers by logging in as admin."""
    response = client.post('/api/login', json={
        'username': 'admin1',
        'password': 'admin123',
        'role': 'admin'
    })
    if response.status_code == 200:
        data = response.get_json()
        return {'Authorization': f'Bearer {data["access_token"]}'}
    return {}


@pytest.fixture
def employee_headers(client):
    """Get authenticated headers by logging in as employee."""
    response = client.post('/api/login', json={
        'username': 'employee1',
        'password': 'emp123',
        'role': 'employee'
    })
    if response.status_code == 200:
        data = response.get_json()
        return {'Authorization': f'Bearer {data["access_token"]}'}
    return {}
