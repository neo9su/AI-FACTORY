import pytest
from fastapi import status

from app.main import storage, storage_lock, CODE_LENGTH


def test_shorten_url_success(client):
    response = client.post("/shorten", json={"long_url": "https://example.com"})
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "short_code" in data
    assert len(data["short_code"]) == CODE_LENGTH
    assert data["short_code"].isalnum()


def test_shorten_url_invalid_url(client):
    response = client.post("/shorten", json={"long_url": "not-a-valid-url"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_shorten_url_too_long(client):
    long_url = "https://example.com/" + "a" * 2048  # total > 2048
    response = client.post("/shorten", json={"long_url": long_url})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_redirect_success(client):
    # First create a short code
    create_resp = client.post("/shorten", json={"long_url": "https://example.com"})
    code = create_resp.json()["short_code"]

    # Then redirect
    response = client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == status.HTTP_302_FOUND
    assert response.headers["location"] == "https://example.com/"


def test_redirect_not_found(client):
    response = client.get("/nonexist", follow_redirects=False)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_stats_success(client):
    create_resp = client.post("/shorten", json={"long_url": "https://example.com"})
    code = create_resp.json()["short_code"]

    # Access the short URL a couple times
    client.get(f"/{code}")
    client.get(f"/{code}")

    stats_resp = client.get(f"/stats/{code}")
    assert stats_resp.status_code == status.HTTP_200_OK
    data = stats_resp.json()
    assert data["original_url"] == "https://example.com/"
    assert data["click_count"] == 2


def test_stats_not_found(client):
    response = client.get("/stats/nonexist")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_shorten_url_missing_field(client):
    response = client.post("/shorten", json={})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_shorten_url_empty_string(client):
    response = client.post("/shorten", json={"long_url": ""})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_concurrent_shorten(client):
    """Test that multiple short codes are unique."""
    codes = set()
    for _ in range(50):
        resp = client.post("/shorten", json={"long_url": "https://example.com"})
        assert resp.status_code == status.HTTP_201_CREATED
        code = resp.json()["short_code"]
        assert code not in codes
        codes.add(code)
    assert len(codes) == 50


def test_redirect_increments_click_count(client):
    create_resp = client.post("/shorten", json={"long_url": "https://example.com"})
    code = create_resp.json()["short_code"]

    # First click
    client.get(f"/{code}")
    stats = client.get(f"/stats/{code}").json()
    assert stats["click_count"] == 1

    # Second click
    client.get(f"/{code}")
    stats = client.get(f"/stats/{code}").json()
    assert stats["click_count"] == 2
