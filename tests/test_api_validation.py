from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_invalid_ticket_body_returns_400() -> None:
    response = client.post(
        "/api/tickets",
        json={
            "event_id": "not-a-uuid",
            "first_name": "",
            "last_name": "Ivanov",
            "email": "not-an-email",
            "seat": "",
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert "detail" in body
    assert isinstance(body["detail"], list)
    assert body["detail"]


def test_unknown_route_still_returns_404() -> None:
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
