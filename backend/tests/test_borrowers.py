
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
    mock_redis.set.assert_any_call("unique-key-123", "processing", nx=True, ex=3600)

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