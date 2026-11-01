import models
from datetime import date, timedelta

# formats.py imports redis_client but never uses it, so no redis patching is needed
# and there is no Idempotency-Key support to assert on.


def _make_format(db_session, cls=models.Book, **kwargs):
    title = models.Title(name="Dune", genre="Sci-Fi")
    db_session.add(title)
    db_session.commit()
    fmt = cls(title_id=title.title_id, **kwargs)
    db_session.add(fmt)
    db_session.commit()
    return fmt


def _make_item(db_session, serial_no, format_id):
    item = models.LibraryItem(serial_no=serial_no, format_id=format_id)
    db_session.add(item)
    db_session.commit()
    return item


def _checkout(db_session, serial_no, returned=False):
    borrower = models.Borrower(name="Alice")
    db_session.add(borrower)
    db_session.commit()
    record = models.CheckoutRecord(
        item_serial_no=serial_no,
        borrower_id=borrower.borrower_id,
        check_out_date=date.today(),
        due_date=date.today() + timedelta(days=7),
        return_date=date.today() if returned else None,
    )
    db_session.add(record)
    db_session.commit()
    return record


# ---- GET /api/formats/{format_id}/items -----------------------------------

def test_get_format_items_success(client, db_session, mock_redis):
    fmt = _make_format(db_session, author="Herbert", number_of_pages=500)
    _make_item(db_session, "serial-001", fmt.format_id)
    _make_item(db_session, "serial-002", fmt.format_id)

    response = client.get(f"/api/formats/{fmt.format_id}/items")

    assert response.status_code == 200
    data = response.json()
    assert data["format_id"] == fmt.format_id
    assert sorted(data["items"]) == ["serial-001", "serial-002"]

    # Router does not use redis
    mock_redis.get.assert_not_called()
    mock_redis.set.assert_not_called()


def test_get_format_items_not_found(client):
    response = client.get("/api/formats/does-not-exist/items")

    assert response.status_code == 404
    assert response.json()["detail"] == "Format not found"


def test_get_format_items_empty_when_no_items(client, db_session):
    fmt = _make_format(db_session, author="Herbert", number_of_pages=500)

    response = client.get(f"/api/formats/{fmt.format_id}/items")

    assert response.status_code == 200
    assert response.json() == {"format_id": fmt.format_id, "items": []}


def test_get_format_items_excludes_checked_out(client, db_session):
    fmt = _make_format(db_session, author="Herbert", number_of_pages=500)
    _make_item(db_session, "serial-001", fmt.format_id)
    _make_item(db_session, "serial-002", fmt.format_id)
    _checkout(db_session, "serial-001")

    response = client.get(f"/api/formats/{fmt.format_id}/items")

    assert response.status_code == 200
    assert response.json()["items"] == ["serial-002"]


def test_get_format_items_includes_returned_items(client, db_session):
    fmt = _make_format(db_session, author="Herbert", number_of_pages=500)
    _make_item(db_session, "serial-001", fmt.format_id)
    _checkout(db_session, "serial-001", returned=True)

    response = client.get(f"/api/formats/{fmt.format_id}/items")

    assert response.status_code == 200
    assert response.json()["items"] == ["serial-001"]


def test_get_format_items_all_checked_out(client, db_session):
    fmt = _make_format(db_session, author="Herbert", number_of_pages=500)
    _make_item(db_session, "serial-001", fmt.format_id)
    _checkout(db_session, "serial-001")

    response = client.get(f"/api/formats/{fmt.format_id}/items")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_get_format_items_only_returns_items_for_requested_format(client, db_session):
    book = _make_format(db_session, author="Herbert", number_of_pages=500)
    movie = _make_format(db_session, cls=models.Movie, director="Villeneuve", runtime=155)
    _make_item(db_session, "book-001", book.format_id)
    _make_item(db_session, "movie-001", movie.format_id)

    book_response = client.get(f"/api/formats/{book.format_id}/items")
    movie_response = client.get(f"/api/formats/{movie.format_id}/items")

    assert book_response.json()["items"] == ["book-001"]
    assert movie_response.json()["items"] == ["movie-001"]


def test_get_format_items_checkout_of_other_format_does_not_affect(client, db_session):
    book = _make_format(db_session, author="Herbert", number_of_pages=500)
    movie = _make_format(db_session, cls=models.Movie, director="Villeneuve", runtime=155)
    _make_item(db_session, "book-001", book.format_id)
    _make_item(db_session, "movie-001", movie.format_id)
    _checkout(db_session, "movie-001")

    response = client.get(f"/api/formats/{book.format_id}/items")

    assert response.json()["items"] == ["book-001"]


def test_get_format_items_works_for_each_format_type(client, db_session):
    audiobook = _make_format(db_session, cls=models.Audiobook, narrator="Brick", runtime=1200)
    _make_item(db_session, "audio-001", audiobook.format_id)

    response = client.get(f"/api/formats/{audiobook.format_id}/items")

    assert response.status_code == 200
    assert response.json()["items"] == ["audio-001"]


def test_get_format_items_rejects_non_get_methods(client, db_session):
    fmt = _make_format(db_session, author="Herbert", number_of_pages=500)

    assert client.post(f"/api/formats/{fmt.format_id}/items").status_code == 405
    assert client.delete(f"/api/formats/{fmt.format_id}/items").status_code == 405