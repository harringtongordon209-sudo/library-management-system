import json
from datetime import date, timedelta

import models


def test_create_borrower_without_idempotency_key(client, mock_redis):
    # No @patch needed!
    response = client.post("/api/borrowers", json={"name": "Alice"})

    assert response.status_code == 201
    assert response.json()["name"] == "Alice"

    # You can assert against the mock exactly as before
    mock_redis.get.assert_not_called()
    mock_redis.set.assert_not_called()

def test_create_borrower_with_idempotency_key_first_time(client, mock_redis):
    # First time, get returns None, set(nx=True) returns True (is_new)
    response = client.post(
        "/api/borrowers",
        json={"name": "Bob"},
        headers={"Idempotency-Key": "unique-key-123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Bob"
    assert "borrower_id" in data

    # Verify redis interactions
    mock_redis.get.assert_called_once_with("unique-key-123")
    # There should be two sets: first for 'processing' and second for the final response
    assert mock_redis.set.call_count == 2
    first, second = mock_redis.set.call_args_list
    assert first.args == ("unique-key-123", "processing")
    assert first.kwargs == {"nx": True, "ex": 3600}
    assert second.args[0] == "unique-key-123"
    assert json.loads(second.args[1]) == data
    assert second.kwargs == {"ex": 86400}

def test_create_borrower_idempotent_cached_response(client, mock_redis):
    # Cached response returned from Redis
    cached_data = '{"borrower_id": "b-123", "name": "Charlie"}'
    mock_redis.get.return_value = cached_data

    response = client.post(
        "/api/borrowers",
        json={"name": "Charlie"},
        headers={"Idempotency-Key": "existing-key"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["borrower_id"] == "b-123"
    assert data["name"] == "Charlie"

    mock_redis.get.assert_called_once_with("existing-key")
    mock_redis.set.assert_not_called()

def test_create_borrower_currently_processing(client, mock_redis):
    # Override the default mock behavior for this specific test
    mock_redis.get.return_value = "processing"

    response = client.post(
        "/api/borrowers",
        json={"name": "Charlie"},
        headers={"Idempotency-Key": "processing-key"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Request is currently processing"
    mock_redis.get.assert_called_once_with("processing-key")

def test_create_borrower_concurrent_race(client, mock_redis):
    # get returns None, but set(nx=True) returns False (someone else acquired it concurrently)
    mock_redis.get.return_value = None
    mock_redis.set.return_value = False

    response = client.post(
        "/api/borrowers",
        json={"name": "Dave"},
        headers={"Idempotency-Key": "race-key"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Request is currently processing"


def test_delete_borrower_success(client, mock_redis):
    create_response = client.post("/api/borrowers", json={"name": "Eve"})
    borrower_id = create_response.json()["borrower_id"]

    delete_response = client.delete(f"/api/borrowers/{borrower_id}")

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = client.get("/api/borrowers")
    assert all(b["borrower_id"] != borrower_id for b in get_response.json())


def test_delete_borrower_not_found(client, mock_redis):
    response = client.delete("/api/borrowers/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"] == "Borrower does not exist!"


def test_delete_borrower_with_checkout_history(client, db_session, mock_redis):
    create_response = client.post("/api/borrowers", json={"name": "Frank"})
    borrower_id = create_response.json()["borrower_id"]

    checkout_record = models.CheckoutRecord(
        item_serial_no="test-serial-001",
        borrower_id=borrower_id,
        check_out_date=date.today(),
        due_date=date.today() + timedelta(days=7),
    )
    db_session.add(checkout_record)
    db_session.commit()

    response = client.delete(f"/api/borrowers/{borrower_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Cannot delete borrower with existing checkout records"

# ---------------------------------------------------------------------------
# Additional coverage: list/filter, validation, checkout, checkin, records
# ---------------------------------------------------------------------------
import pytest


def _make_borrower(db_session, name="Zed"):
    borrower = models.Borrower(name=name)
    db_session.add(borrower)
    db_session.commit()
    return borrower


def _make_item(db_session, serial_no="item-001", title_name="Dune"):
    title = models.Title(name=title_name)
    db_session.add(title)
    db_session.commit()
    book = models.Book(title_id=title.title_id, author="Herbert", number_of_pages=500)
    db_session.add(book)
    db_session.commit()
    item = models.LibraryItem(serial_no=serial_no, format_id=book.format_id)
    db_session.add(item)
    db_session.commit()
    return item


def _make_checkout(db_session, borrower, item, return_date=None):
    record = models.CheckoutRecord(
        item_serial_no=item.serial_no,
        borrower_id=borrower.borrower_id,
        check_out_date=date.today(),
        due_date=date.today() + timedelta(days=7),
        return_date=return_date,
    )
    db_session.add(record)
    db_session.commit()
    return record


# ---- POST /api/borrowers validation ---------------------------------------

def test_create_borrower_missing_name(client, mock_redis):
    response = client.post("/api/borrowers", json={})
    assert response.status_code == 422


def test_create_borrower_invalid_name_type(client, mock_redis):
    response = client.post("/api/borrowers", json={"name": ["not", "a", "string"]})
    assert response.status_code == 422


# ---- GET /api/borrowers ---------------------------------------------------

def test_get_all_borrowers_empty(client):
    response = client.get("/api/borrowers")
    assert response.status_code == 200
    assert response.json() == []


def test_get_all_borrowers_returns_all(client, db_session):
    _make_borrower(db_session, "Ann")
    _make_borrower(db_session, "Ben")

    response = client.get("/api/borrowers")
    assert response.status_code == 200
    assert sorted(b["name"] for b in response.json()) == ["Ann", "Ben"]


def test_get_all_borrowers_name_filter_case_insensitive_partial(client, db_session):
    _make_borrower(db_session, "Alice Smith")
    _make_borrower(db_session, "Bob Jones")

    response = client.get("/api/borrowers", params={"name": "ALIC"})
    assert response.status_code == 200
    assert [b["name"] for b in response.json()] == ["Alice Smith"]


def test_get_all_borrowers_name_filter_no_match(client, db_session):
    _make_borrower(db_session, "Alice")

    response = client.get("/api/borrowers", params={"name": "zzz"})
    assert response.status_code == 200
    assert response.json() == []


# ---- POST /api/borrowers/{id}/checkoutRecords -----------------------------

def test_checkout_item_success(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    item = _make_item(db_session, "item-001", "Dune")

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": "item-001"}},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["startDate"] == date.today().isoformat()
    assert data["dueDate"] == (date.today() + timedelta(days=7)).isoformat()
    assert data["returnDate"] is None
    assert data["item"] == {"id": item.format_id, "name": "Dune", "barcode": "item-001"}
    assert "checkout_id" in data
    mock_redis.get.assert_not_called()


def test_checkout_item_borrower_not_found(client, db_session, mock_redis):
    _make_item(db_session)

    response = client.post(
        "/api/borrowers/nope/checkoutRecords",
        json={"item": {"id": "item-001"}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Borrower does not exist!"


def test_checkout_item_not_found(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": "missing-item"}},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


def test_checkout_item_already_checked_out(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    other = _make_borrower(db_session, "Other")
    item = _make_item(db_session)
    _make_checkout(db_session, other, item)

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": item.serial_no}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Item is already checked out!"


def test_checkout_item_again_after_return(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    item = _make_item(db_session)
    _make_checkout(db_session, borrower, item, return_date=date.today())

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": item.serial_no}},
    )

    assert response.status_code == 201


@pytest.mark.parametrize("body", [{}, {"item": {}}, {"item": "item-001"}])
def test_checkout_item_invalid_body(client, db_session, mock_redis, body):
    borrower = _make_borrower(db_session)

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords", json=body
    )

    assert response.status_code == 422


def test_checkout_item_idempotency_first_time(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    _make_item(db_session)

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": "item-001"}},
        headers={"Idempotency-Key": "checkout-key"},
    )

    assert response.status_code == 201
    mock_redis.get.assert_called_once_with("checkout-key")
    assert mock_redis.set.call_count == 2
    first, second = mock_redis.set.call_args_list
    assert first.args == ("checkout-key", "processing")
    assert first.kwargs == {"nx": True, "ex": 3600}
    assert second.args[0] == "checkout-key"
    # response_model adds returnDate=None after the router caches the dict
    expected = {k: v for k, v in response.json().items() if k != "returnDate"}
    assert json.loads(second.args[1]) == expected
    assert second.kwargs == {"ex": 86400}


def test_checkout_item_idempotent_cached_response(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    cached = (
        '{"checkout_id": "c-1", "startDate": "2025-01-01", "dueDate": "2025-01-08", '
        '"item": {"id": "f-1", "name": "Cached", "barcode": "item-001"}}'
    )
    mock_redis.get.return_value = cached

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": "item-001"}},
        headers={"Idempotency-Key": "checkout-key"},
    )

    assert response.status_code == 201
    assert response.json()["checkout_id"] == "c-1"
    mock_redis.set.assert_not_called()
    assert db_session.query(models.CheckoutRecord).count() == 0


def test_checkout_item_currently_processing(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    mock_redis.get.return_value = "processing"

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": "item-001"}},
        headers={"Idempotency-Key": "checkout-key"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Request is processing"


def test_checkout_item_concurrent_race(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    mock_redis.get.return_value = None
    mock_redis.set.return_value = False

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": "item-001"}},
        headers={"Idempotency-Key": "checkout-race"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Request is processing"


# ---- PATCH /api/borrowers/{id}/checkoutRecords/{checkout_id} --------------

def test_checkin_item_success(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    item = _make_item(db_session, "item-001", "Dune")
    record = _make_checkout(db_session, borrower, item)

    response = client.patch(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords/{record.checkout_id}"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["checkout_id"] == record.checkout_id
    assert data["returnDate"] == date.today().isoformat()
    assert data["item"]["name"] == "Dune"
    assert data["item"]["barcode"] == "item-001"

    db_session.refresh(record)
    assert record.return_date == date.today()


def test_checkin_item_record_not_found(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)

    response = client.patch(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords/nope"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Checkout Record not found"


def test_checkin_item_wrong_borrower(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    other = _make_borrower(db_session, "Other")
    item = _make_item(db_session)
    record = _make_checkout(db_session, borrower, item)

    response = client.patch(
        f"/api/borrowers/{other.borrower_id}/checkoutRecords/{record.checkout_id}"
    )

    assert response.status_code == 404
    db_session.refresh(record)
    assert record.return_date is None


def test_checkin_item_already_checked_in(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    item = _make_item(db_session)
    record = _make_checkout(
        db_session, borrower, item, return_date=date.today() - timedelta(days=1)
    )

    response = client.patch(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords/{record.checkout_id}"
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "This Item has already been checked in"
    db_session.refresh(record)
    assert record.return_date == date.today() - timedelta(days=1)


# ---- GET /api/borrowers/{id}/checkoutRecords ------------------------------

def test_get_checkout_records_borrower_not_found(client, mock_redis):
    response = client.get("/api/borrowers/nope/checkoutRecords")

    assert response.status_code == 400
    assert response.json()["detail"] == "Borrower does not exist!"


def test_get_checkout_records_empty(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)

    response = client.get(f"/api/borrowers/{borrower.borrower_id}/checkoutRecords")

    assert response.status_code == 200
    assert response.json() == []


def test_get_checkout_records_only_active_for_borrower(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    other = _make_borrower(db_session, "Other")
    active_item = _make_item(db_session, "item-active", "Active Title")
    returned_item = _make_item(db_session, "item-returned", "Returned Title")
    other_item = _make_item(db_session, "item-other", "Other Title")
    active = _make_checkout(db_session, borrower, active_item)
    _make_checkout(db_session, borrower, returned_item, return_date=date.today())
    _make_checkout(db_session, other, other_item)

    response = client.get(f"/api/borrowers/{borrower.borrower_id}/checkoutRecords")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["checkout_id"] == active.checkout_id
    assert data[0]["returnDate"] is None
    assert data[0]["item"]["name"] == "Active Title"
    assert data[0]["item"]["barcode"] == "item-active"


# ---- DELETE edge case -----------------------------------------------------

def test_delete_borrower_with_returned_checkout_history(client, db_session, mock_redis):
    # Router blocks deletion on ANY checkout record, including returned ones
    borrower = _make_borrower(db_session)
    item = _make_item(db_session)
    _make_checkout(db_session, borrower, item, return_date=date.today())

    response = client.delete(f"/api/borrowers/{borrower.borrower_id}")

    assert response.status_code == 409


# ---- idempotency key release on failure -------------------------------------

def _boom(*args, **kwargs):
    raise RuntimeError("db down")


def test_create_borrower_releases_key_when_commit_fails(client, db_session, mock_redis, monkeypatch):
    monkeypatch.setattr(db_session, "commit", _boom)

    with pytest.raises(RuntimeError):
        client.post(
            "/api/borrowers",
            json={"name": "Dana"},
            headers={"Idempotency-Key": "fail-key"},
        )

    mock_redis.delete.assert_called_once_with("fail-key")
    # only the 'processing' reservation was written, never a final response
    mock_redis.set.assert_called_once_with("fail-key", "processing", nx=True, ex=3600)


def test_create_borrower_without_key_does_not_touch_redis_on_failure(client, db_session, mock_redis, monkeypatch):
    monkeypatch.setattr(db_session, "commit", _boom)

    with pytest.raises(RuntimeError):
        client.post("/api/borrowers", json={"name": "Dana"})

    mock_redis.delete.assert_not_called()


def test_create_borrower_success_does_not_release_key(client, mock_redis):
    response = client.post(
        "/api/borrowers", json={"name": "Eve"}, headers={"Idempotency-Key": "ok-key"}
    )

    assert response.status_code == 201
    mock_redis.delete.assert_not_called()


def test_create_borrower_processing_conflict_does_not_release_key(client, mock_redis):
    # the other in-flight request owns the reservation, so we must not delete it
    mock_redis.get.return_value = "processing"

    response = client.post(
        "/api/borrowers", json={"name": "Eve"}, headers={"Idempotency-Key": "busy-key"}
    )

    assert response.status_code == 409
    mock_redis.delete.assert_not_called()


def test_create_borrower_lock_not_acquired_does_not_release_key(client, mock_redis):
    mock_redis.set.return_value = None  # lost the nx race

    response = client.post(
        "/api/borrowers", json={"name": "Eve"}, headers={"Idempotency-Key": "race-key"}
    )

    assert response.status_code == 409
    mock_redis.delete.assert_not_called()


def test_checkout_borrower_not_found_releases_key(client, db_session, mock_redis):
    _make_item(db_session)

    response = client.post(
        "/api/borrowers/missing/checkoutRecords",
        json={"item": {"id": "item-001"}},
        headers={"Idempotency-Key": "k-borrower"},
    )

    assert response.status_code == 400
    mock_redis.delete.assert_called_once_with("k-borrower")


def test_checkout_item_already_checked_out_releases_key(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)
    item = _make_item(db_session)
    _make_checkout(db_session, borrower, item)

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": "item-001"}},
        headers={"Idempotency-Key": "k-taken"},
    )

    assert response.status_code == 400
    mock_redis.delete.assert_called_once_with("k-taken")


def test_checkout_item_not_found_releases_key(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": "nope"}},
        headers={"Idempotency-Key": "k-noitem"},
    )

    assert response.status_code == 404
    mock_redis.delete.assert_called_once_with("k-noitem")


def test_checkout_releases_key_when_commit_fails(client, db_session, mock_redis, monkeypatch):
    borrower = _make_borrower(db_session)
    _make_item(db_session)
    monkeypatch.setattr(db_session, "commit", _boom)

    with pytest.raises(RuntimeError):
        client.post(
            f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
            json={"item": {"id": "item-001"}},
            headers={"Idempotency-Key": "k-commit"},
        )

    mock_redis.delete.assert_called_once_with("k-commit")


def test_checkout_failure_without_key_does_not_touch_redis(client, db_session, mock_redis):
    borrower = _make_borrower(db_session)

    response = client.post(
        f"/api/borrowers/{borrower.borrower_id}/checkoutRecords",
        json={"item": {"id": "nope"}},
    )

    assert response.status_code == 404
    mock_redis.delete.assert_not_called()


def test_checkout_retry_with_same_key_succeeds_after_failure(client, db_session, mock_redis):
    # simulate redis state: the failed attempt must leave nothing behind for the retry to trip over
    store = {}
    mock_redis.get.side_effect = lambda k: store.get(k)
    mock_redis.set.side_effect = lambda k, v, nx=False, ex=None: (
        False if nx and k in store else store.update({k: v}) or True
    )
    mock_redis.delete.side_effect = lambda k: store.pop(k, None)

    borrower = _make_borrower(db_session)
    headers = {"Idempotency-Key": "retry-key"}
    url = f"/api/borrowers/{borrower.borrower_id}/checkoutRecords"

    first = client.post(url, json={"item": {"id": "item-001"}}, headers=headers)
    assert first.status_code == 404
    assert "retry-key" not in store

    _make_item(db_session)
    second = client.post(url, json={"item": {"id": "item-001"}}, headers=headers)
    assert second.status_code == 201
