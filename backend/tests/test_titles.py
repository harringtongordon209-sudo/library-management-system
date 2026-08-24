import models

def test_get_all_titles(client, db_session):
    # db_session and client are automatically provided by conftest.py
    mock_title = models.Title(name="The Mocked Matrix", genre="Sci-Fi")
    db_session.add(mock_title)
    db_session.commit()

    response = client.get("/api/titles")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1  # Ensure only our one fake book is there
    assert data[0]["name"] == "The Mocked Matrix"
    assert "title_id" in data[0]
    assert "genre" in data[0]
    assert "description" not in data[0]