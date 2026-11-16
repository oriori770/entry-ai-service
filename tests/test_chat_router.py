import time
import pytest
import jwt
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import app
from app.models.user import UserRole

client = TestClient(app)
settings = get_settings()


def create_token(user_id: str, role: str, expires_in: int = 3600) -> str:
    now = int(time.time())
    payload = {
        "userId": user_id,
        "role": role,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def test_admin_chat_response():
    token = create_token("admin_001", UserRole.ADMIN.value)
    payload = {
        "messages": [{"role": "user", "content": "מה שלומך ומה היכולות שלך?"}],
        "stream": False,
    }
    response = client.post(
        "/api/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    assert "מנהל" in data["reply"]


def test_admin_event_proposal_flow():
    token = create_token("admin_001", UserRole.ADMIN.value)
    payload = {
        "messages": [{"role": "user", "content": "צור לי אירוע חדש בשם כנס שנתי"}],
        "stream": False,
    }
    response = client.post(
        "/api/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action_proposals"] is not None
    assert len(data["action_proposals"]) > 0
    proposal = data["action_proposals"][0]
    assert proposal["type"] == "create_event"
    assert "name" in proposal["payload"]


def test_scanner_chat_response():
    token = create_token("scanner_001", UserRole.SCANNER.value)
    payload = {
        "messages": [{"role": "user", "content": "שלום, אני צריך עזרה במשמרת"}],
        "stream": False,
    }
    response = client.post(
        "/api/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert "סדרן" in data["reply"]


def test_scanner_bola_rejection_on_financial_questions():
    token = create_token("scanner_001", UserRole.SCANNER.value)
    payload = {
        "messages": [{"role": "user", "content": "כמה כסף והכנסות נכנסו באירוע האחרון?"}],
        "stream": False,
    }
    response = client.post(
        "/api/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    # Must be strictly rejected with Hebrew permission error
    assert "אין לך הרשאה" in data["reply"]
    assert data["action_proposals"] is None


def test_unauthenticated_chat_returns_401():
    payload = {
        "messages": [{"role": "user", "content": "שלום"}],
    }
    response = client.post("/api/ai/chat", json=payload)
    assert response.status_code == 401


def test_streaming_chat_mode():
    token = create_token("admin_001", UserRole.ADMIN.value)
    payload = {
        "messages": [{"role": "user", "content": "היי"}],
        "stream": True,
    }
    response = client.post(
        "/api/ai/chat",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    text = response.text
    assert "data:" in text
    assert "done" in text
