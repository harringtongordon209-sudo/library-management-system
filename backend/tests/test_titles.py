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

# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------
import pytest
from unittest.mock import patch


@pytest.fixture
def titles_redis():
    # conftest's autouse mock only patches routers.borrowers, so patch titles separately
    with patch("routers.titles.redis_client") as mocked_client:
        mocked_client.get.return_value = None
        mocked_client.set.return_value = True
        yield mocked_client


def _make_title(db_session, name="Dune", genre="Sci-Fi", description="Desert planet"):
    title = models.Title(name=name, genre=genre, description=description)
    db_session.add(title)
    db_session.commit()
    return title


# ---- GET /api/titles ------------------------------------------------------

def test_get_all_titles_empty(client):
    response = client.get("/api/titles")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_titles_name_filter_case_insensitive_partial(client, db_session):
    _make_title(db_session, name="The Matrix")
    _make_title(db_session, name="Dune")

    response = client.get("/api/titles", params={"name": "matr"})
    assert response.status_code == 200
    data = response.json()
    assert [t["name"] for t in data] == ["The Matrix"]


def test_get_all_titles_name_filter_no_match(client, db_session):
    _make_title(db_session, name="Dune")
    response = client.get("/api/titles", params={"name": "zzz"})
    assert response.status_code == 200
    assert response.json() == []


# ---- POST /api/titles -----------------------------------------------------

def test_create_title_success(client, db_session):
    response = client.post(
        "/api/titles",
        json={"name": "Neuromancer", "description": "Cyberpunk", "genre": "Sci-Fi"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Neuromancer"
    assert data["description"] == "Cyberpunk"
    assert data["genre"] == "Sci-Fi"
    assert data["title_id"]
    assert db_session.query(models.Title).count() == 1


def test_create_title_optional_fields_omitted(client):
    response = client.post("/api/titles", json={"name": "Minimal"})
    assert response.status_code == 201
    assert response.json()["description"] is None
    assert response.json()["genre"] is None


def test_create_title_duplicate_name(client, db_session):
    _make_title(db_session, name="Dune")
    response = client.post("/api/titles", json={"name": "Dune"})
    assert response.status_code == 400
    assert response.json()["detail"] == "That title already exists"
    assert db_session.query(models.Title).count() == 1


def test_create_title_missing_name(client):
    response = client.post("/api/titles", json={"genre": "Sci-Fi"})
    assert response.status_code == 422


def test_create_title_with_idempotency_key_first_time(client, titles_redis):
    response = client.post(
        "/api/titles", json={"name": "Keyed"}, headers={"Idempotency-Key": "k-1"}
    )
    assert response.status_code == 201
    titles_redis.get.assert_called_once_with("k-1")
    assert titles_redis.set.call_count == 2
    titles_redis.set.assert_any_call("k-1", "processing", nx=True, ex=3600)


def test_create_title_idempotent_cached_response(client, db_session, titles_redis):
    titles_redis.get.return_value = (
        '{"title_id": "t-1", "name": "Cached", "description": null, "genre": null}'
    )
    response = client.post(
        "/api/titles", json={"name": "Cached"}, headers={"Idempotency-Key": "k-2"}
    )
    assert response.status_code == 201
    assert response.json()["title_id"] == "t-1"
    assert db_session.query(models.Title).count() == 0
    titles_redis.set.assert_not_called()


def test_create_title_idempotency_processing_conflict(client, db_session, titles_redis):
    titles_redis.get.return_value = "processing"
    response = client.post(
        "/api/titles", json={"name": "Busy"}, headers={"Idempotency-Key": "k-3"}
    )
    assert response.status_code == 409
    assert db_session.query(models.Title).count() == 0


def test_create_title_idempotency_lock_not_acquired(client, db_session, titles_redis):
    titles_redis.set.return_value = None  # nx set fails: someone else won the race
    response = client.post(
        "/api/titles", json={"name": "Race"}, headers={"Idempotency-Key": "k-4"}
    )
    assert response.status_code == 409
    assert db_session.query(models.Title).count() == 0


# ---- POST /api/titles/{id}/book | Movie | Audiobook ------------------------

def test_create_book_copies_success(client, db_session):
    title = _make_title(db_session)
    response = client.post(
        f"/api/titles/{title.title_id}/book",
        json={"author": "Frank Herbert", "number_of_pages": 412, "number_of_copies": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title_id"] == title.title_id
    assert data["author"] == "Frank Herbert"
    assert data["number_of_pages"] == 412
    assert len(data["created_serial_numbers"]) == 3
    assert len(set(data["created_serial_numbers"])) == 3

    assert db_session.query(models.Book).count() == 1
    items = db_session.query(models.LibraryItem).filter_by(format_id=data["format_id"]).all()
    assert {i.serial_no for i in items} == set(data["created_serial_numbers"])


def test_create_book_copies_zero_copies(client, db_session):
    title = _make_title(db_session)
    response = client.post(
        f"/api/titles/{title.title_id}/book",
        json={"author": "A", "number_of_pages": 10, "number_of_copies": 0},
    )
    assert response.status_code == 200
    assert response.json()["created_serial_numbers"] == []
    assert db_session.query(models.LibraryItem).count() == 0


def test_create_book_copies_title_not_found(client):
    response = client.post(
        "/api/titles/missing/book",
        json={"author": "A", "number_of_pages": 10, "number_of_copies": 1},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Title not found"


def test_create_book_copies_validation_error(client, db_session):
    title = _make_title(db_session)
    response = client.post(
        f"/api/titles/{title.title_id}/book", json={"author": "A"}
    )
    assert response.status_code == 422


def test_create_book_copies_non_integer_pages(client, db_session):
    title = _make_title(db_session)
    response = client.post(
        f"/api/titles/{title.title_id}/book",
        json={"author": "A", "number_of_pages": "many", "number_of_copies": 1},
    )
    assert response.status_code == 422


def test_create_book_copies_idempotent_cached_response(client, db_session, titles_redis):
    title = _make_title(db_session)
    titles_redis.get.return_value = (
        '{"title_id": "t", "format_id": "f", "author": "A", "number_of_pages": 1,'
        ' "created_serial_numbers": ["s1"]}'
    )
    response = client.post(
        f"/api/titles/{title.title_id}/book",
        json={"author": "A", "number_of_pages": 1, "number_of_copies": 1},
        headers={"Idempotency-Key": "book-k"},
    )
    assert response.status_code == 200
    assert response.json()["created_serial_numbers"] == ["s1"]
    assert db_session.query(models.Book).count() == 0


def test_create_book_copies_idempotency_first_time_caches_result(client, db_session, titles_redis):
    title = _make_title(db_session)
    response = client.post(
        f"/api/titles/{title.title_id}/book",
        json={"author": "A", "number_of_pages": 1, "number_of_copies": 1},
        headers={"Idempotency-Key": "book-k2"},
    )
    assert response.status_code == 200
    assert titles_redis.set.call_count == 2
    final_call = titles_redis.set.call_args_list[-1]
    assert final_call.args[0] == "book-k2"
    assert final_call.kwargs["ex"] == 86400


def test_create_book_copies_idempotency_processing_conflict(client, db_session, titles_redis):
    title = _make_title(db_session)
    titles_redis.get.return_value = "processing"
    response = client.post(
        f"/api/titles/{title.title_id}/book",
        json={"author": "A", "number_of_pages": 1, "number_of_copies": 1},
        headers={"Idempotency-Key": "book-k3"},
    )
    assert response.status_code == 409


def test_create_movie_copies_success(client, db_session):
    title = _make_title(db_session)
    response = client.post(
        f"/api/titles/{title.title_id}/Movie",
        json={"director": "Villeneuve", "runtime": 155, "number_of_copies": 2},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["director"] == "Villeneuve"
    assert data["runtime"] == 155
    assert len(data["created_serial_numbers"]) == 2
    assert db_session.query(models.Movie).count() == 1
    assert db_session.query(models.LibraryItem).count() == 2


def test_create_movie_copies_title_not_found(client):
    response = client.post(
        "/api/titles/missing/Movie",
        json={"director": "D", "runtime": 90, "number_of_copies": 1},
    )
    assert response.status_code == 404


def test_create_movie_copies_validation_error(client, db_session):
    title = _make_title(db_session)
    response = client.post(
        f"/api/titles/{title.title_id}/Movie", json={"director": "D"}
    )
    assert response.status_code == 422


def test_create_movie_copies_idempotent_cached_response(client, db_session, titles_redis):
    title = _make_title(db_session)
    titles_redis.get.return_value = (
        '{"title_id": "t", "format_id": "f", "director": "D", "runtime": 1,'
        ' "created_serial_numbers": []}'
    )
    response = client.post(
        f"/api/titles/{title.title_id}/Movie",
        json={"director": "D", "runtime": 1, "number_of_copies": 1},
        headers={"Idempotency-Key": "movie-k"},
    )
    assert response.status_code == 200
    assert response.json()["format_id"] == "f"
    assert db_session.query(models.Movie).count() == 0


def test_create_audiobook_copies_success(client, db_session):
    title = _make_title(db_session)
    response = client.post(
        f"/api/titles/{title.title_id}/Audiobook",
        json={"narrator": "Scott Brick", "runtime": 1300, "number_of_copies": 4},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["narrator"] == "Scott Brick"
    assert data["runtime"] == 1300
    assert len(data["created_serial_numbers"]) == 4
    assert db_session.query(models.Audiobook).count() == 1
    assert db_session.query(models.LibraryItem).count() == 4


def test_create_audiobook_copies_title_not_found(client):
    response = client.post(
        "/api/titles/missing/Audiobook",
        json={"narrator": "N", "runtime": 10, "number_of_copies": 1},
    )
    assert response.status_code == 404


def test_create_audiobook_copies_validation_error(client, db_session):
    title = _make_title(db_session)
    response = client.post(
        f"/api/titles/{title.title_id}/Audiobook", json={"narrator": "N"}
    )
    assert response.status_code == 422


def test_create_audiobook_copies_idempotent_cached_response(client, db_session, titles_redis):
    title = _make_title(db_session)
    titles_redis.get.return_value = (
        '{"title_id": "t", "format_id": "f", "narrator": "N", "runtime": 1,'
        ' "created_serial_numbers": []}'
    )
    response = client.post(
        f"/api/titles/{title.title_id}/Audiobook",
        json={"narrator": "N", "runtime": 1, "number_of_copies": 1},
        headers={"Idempotency-Key": "ab-k"},
    )
    assert response.status_code == 200
    assert response.json()["narrator"] == "N"
    assert db_session.query(models.Audiobook).count() == 0


# ---- GET /api/titles/{id} -------------------------------------------------

def test_get_title_detail_not_found(client):
    response = client.get("/api/titles/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Title not found"


def test_get_title_detail_no_formats(client, db_session):
    title = _make_title(db_session)
    response = client.get(f"/api/titles/{title.title_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Dune"
    assert data["description"] == "Desert planet"
    assert data["genre"] == "Sci-Fi"
    assert data["formats"] == []


def test_get_title_detail_with_format_counts(client, db_session):
    title = _make_title(db_session)
    client.post(
        f"/api/titles/{title.title_id}/book",
        json={"author": "A", "number_of_pages": 1, "number_of_copies": 3},
    )
    client.post(
        f"/api/titles/{title.title_id}/Movie",
        json={"director": "D", "runtime": 1, "number_of_copies": 2},
    )
    response = client.get(f"/api/titles/{title.title_id}")
    assert response.status_code == 200
    counts = {f["format"]: f["count"] for f in response.json()["formats"]}
    assert counts == {"book": 3, "movie": 2}


def test_get_title_detail_format_with_zero_copies_omitted(client, db_session):
    # The query uses an inner join on LibraryItem, so zero-copy formats are not listed
    title = _make_title(db_session)
    client.post(
        f"/api/titles/{title.title_id}/book",
        json={"author": "A", "number_of_pages": 1, "number_of_copies": 0},
    )
    response = client.get(f"/api/titles/{title.title_id}")
    assert response.json()["formats"] == []


# ---- GET /api/titles/{id}/formats -----------------------------------------

def test_get_title_formats_not_found(client):
    response = client.get("/api/titles/missing/formats")
    assert response.status_code == 404
    assert response.json()["detail"] == "Title not found"


def test_get_title_formats_empty(client, db_session):
    title = _make_title(db_session)
    response = client.get(f"/api/titles/{title.title_id}/formats")
    assert response.status_code == 200
    assert response.json() == {
        "title_id": title.title_id,
        "name": "Dune",
        "format_types": [],
    }


def test_get_title_formats_lists_all_formats(client, db_session):
    title = _make_title(db_session)
    book = client.post(
        f"/api/titles/{title.title_id}/book",
        json={"author": "A", "number_of_pages": 1, "number_of_copies": 1},
    ).json()
    audio = client.post(
        f"/api/titles/{title.title_id}/Audiobook",
        json={"narrator": "N", "runtime": 1, "number_of_copies": 0},
    ).json()
    response = client.get(f"/api/titles/{title.title_id}/formats")
    assert response.status_code == 200
    formats = {f["format_id"]: f["format_type"] for f in response.json()["format_types"]}
    assert formats == {book["format_id"]: "book", audio["format_id"]: "audiobook"}


# ---- idempotency key release on failure -------------------------------------

def _boom(*args, **kwargs):
    raise RuntimeError("db down")


def test_create_title_duplicate_releases_key(client, db_session, titles_redis):
    _make_title(db_session, name="Dune")

    response = client.post(
        "/api/titles", json={"name": "Dune"}, headers={"Idempotency-Key": "dup-key"}
    )

    assert response.status_code == 400
    titles_redis.delete.assert_called_once_with("dup-key")


def test_create_title_releases_key_when_commit_fails(client, db_session, titles_redis, monkeypatch):
    monkeypatch.setattr(db_session, "commit", _boom)

    with pytest.raises(RuntimeError):
        client.post(
            "/api/titles", json={"name": "Fail"}, headers={"Idempotency-Key": "fail-key"}
        )

    titles_redis.delete.assert_called_once_with("fail-key")


def test_create_title_failure_without_key_does_not_touch_redis(client, db_session, titles_redis):
    _make_title(db_session, name="Dune")

    response = client.post("/api/titles", json={"name": "Dune"})

    assert response.status_code == 400
    titles_redis.delete.assert_not_called()


def test_create_title_success_does_not_release_key(client, titles_redis):
    response = client.post(
        "/api/titles", json={"name": "Fine"}, headers={"Idempotency-Key": "ok-key"}
    )

    assert response.status_code == 201
    titles_redis.delete.assert_not_called()


def test_create_title_processing_conflict_does_not_release_key(client, titles_redis):
    # the other in-flight request owns the reservation, so we must not delete it
    titles_redis.get.return_value = "processing"

    response = client.post(
        "/api/titles", json={"name": "Busy"}, headers={"Idempotency-Key": "busy-key"}
    )

    assert response.status_code == 409
    titles_redis.delete.assert_not_called()


def test_create_title_lock_not_acquired_does_not_release_key(client, titles_redis):
    titles_redis.set.return_value = None  # lost the nx race

    response = client.post(
        "/api/titles", json={"name": "Race"}, headers={"Idempotency-Key": "race-key"}
    )

    assert response.status_code == 409
    titles_redis.delete.assert_not_called()


@pytest.mark.parametrize("path, body", [
    ("book", {"author": "A", "number_of_pages": 1, "number_of_copies": 1}),
    ("Movie", {"director": "D", "runtime": 90, "number_of_copies": 1}),
    ("Audiobook", {"narrator": "N", "runtime": 90, "number_of_copies": 1}),
])
def test_create_copies_title_not_found_releases_key(client, titles_redis, path, body):
    response = client.post(
        f"/api/titles/missing/{path}", json=body, headers={"Idempotency-Key": "k-missing"}
    )

    assert response.status_code == 404
    titles_redis.delete.assert_called_once_with("k-missing")


@pytest.mark.parametrize("path, body", [
    ("book", {"author": "A", "number_of_pages": 1, "number_of_copies": 1}),
    ("Movie", {"director": "D", "runtime": 90, "number_of_copies": 1}),
    ("Audiobook", {"narrator": "N", "runtime": 90, "number_of_copies": 1}),
])
def test_create_copies_releases_key_when_commit_fails(
    client, db_session, titles_redis, monkeypatch, path, body
):
    title = _make_title(db_session)
    monkeypatch.setattr(db_session, "commit", _boom)

    with pytest.raises(RuntimeError):
        client.post(
            f"/api/titles/{title.title_id}/{path}",
            json=body,
            headers={"Idempotency-Key": "k-commit"},
        )

    titles_redis.delete.assert_called_once_with("k-commit")


@pytest.mark.parametrize("path, body", [
    ("book", {"author": "A", "number_of_pages": 1, "number_of_copies": 1}),
    ("Movie", {"director": "D", "runtime": 90, "number_of_copies": 1}),
    ("Audiobook", {"narrator": "N", "runtime": 90, "number_of_copies": 1}),
])
def test_create_copies_success_does_not_release_key(client, db_session, titles_redis, path, body):
    title = _make_title(db_session)

    response = client.post(
        f"/api/titles/{title.title_id}/{path}",
        json=body,
        headers={"Idempotency-Key": "k-ok"},
    )

    assert response.status_code == 200
    titles_redis.delete.assert_not_called()


def test_create_book_copies_failure_without_key_does_not_touch_redis(client, titles_redis):
    response = client.post(
        "/api/titles/missing/book",
        json={"author": "A", "number_of_pages": 1, "number_of_copies": 1},
    )

    assert response.status_code == 404
    titles_redis.delete.assert_not_called()
