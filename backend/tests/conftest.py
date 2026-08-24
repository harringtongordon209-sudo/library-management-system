import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch
from main import app
from database import get_db
import models

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    models.Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    models.Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function", autouse=True)
def mock_redis():
    """
    Mocks the redis_client used in the routers.
    Yields the mock object so tests can configure return values or assert calls.
    """
    # Make sure this string matches the exact import path in your app
    with patch("routers.borrowers.redis_client") as mocked_client:
        # Optional: Set default behaviors that apply to most tests
        mocked_client.get.return_value = None
        mocked_client.set.return_value = True

        # Yield hands the mock over to the test function
        yield mocked_client