from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db
import models

# 1. Configure the in-memory SQLite database
# The :memory: path means "do not save this to a file, just keep it in RAM"
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Keeps the in-memory DB alive for the duration of the test
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Tell SQLAlchemy to create your tables (Titles, Formats, etc.) in this fake database
models.Base.metadata.create_all(bind=engine)

# 3. Create the function that will replace your normal 'get_db'
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. OVERRIDE THE DEPENDENCY!
# This tells FastAPI: "Whenever a route asks for get_db, run override_get_db instead."
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_get_all_titles_with_mock_data():
    # --- SETUP: Inject mock data into the fake database ---
    db = TestingSessionLocal()

    mock_title = models.Title(
        name="The Mocked Matrix",
        description="A book that only exists in memory.",
        genre="Sci-Fi"
    )
    db.add(mock_title)
    db.commit()
    db.refresh(mock_title)
    db.close()

    # --- EXECUTE: Hit the endpoint ---
    # The client will use our overridden DB, meaning it only sees "The Mocked Matrix"
    response = client.get("/api/titles")

    # --- ASSERT: Verify the API returned our mock data ---
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1  # Ensure only our one fake book is there
    assert data[0]["name"] == "The Mocked Matrix"
    assert "title_id" in data[0]
    assert "genre" not in data[0]
    assert "description" not in data[0]

