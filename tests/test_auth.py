import time
import pytest
import jwt
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from app.config import get_settings
from app.models.user import AuthenticatedUser, UserRole
from app.auth import get_current_user, require_admin, require_scanner, decode_jwt_token
from app.database import run_readonly_aggregate

settings = get_settings()

# Create a test app with protected endpoints
test_app = FastAPI()
test_router = APIRouter(prefix="/test")


@test_router.get("/admin-only")
async def admin_route(user: AuthenticatedUser = Depends(require_admin)):
    return {"message": "Admin access granted", "user_id": user.user_id, "role": user.role}


@test_router.get("/scanner-allowed")
async def scanner_route(user: AuthenticatedUser = Depends(require_scanner)):
    return {"message": "Scanner access granted", "user_id": user.user_id, "role": user.role}


test_app.include_router(test_router)
client = TestClient(test_app)


def create_token(user_id: str, role: str, expires_in: int = 3600, secret: str = settings.jwt_secret) -> str:
    now = int(time.time())
    payload = {
        "userId": user_id,
        "role": role,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_admin_can_access_admin_route():
    token = create_token("admin_123", UserRole.ADMIN.value)
    response = client.get("/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Admin access granted"
    assert data["role"] == "admin"


def test_superadmin_can_access_admin_route():
    token = create_token("super_123", UserRole.SUPERADMIN.value)
    response = client.get("/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "superadmin"


def test_scanner_is_forbidden_from_admin_route():
    token = create_token("scanner_123", UserRole.SCANNER.value)
    response = client.get("/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert "אין לך הרשאה" in response.json()["detail"]


def test_scanner_can_access_scanner_route():
    token = create_token("scanner_123", UserRole.SCANNER.value)
    response = client.get("/test/scanner-allowed", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "scanner"


def test_missing_token_returns_401():
    response = client.get("/test/admin-only")
    assert response.status_code == 401
    assert "נדרש טוקן" in response.json()["detail"]


def test_expired_token_returns_401():
    token = create_token("admin_123", UserRole.ADMIN.value, expires_in=-10)
    response = client.get("/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "פג תוקף" in response.json()["detail"]


def test_wrong_secret_returns_401():
    token = create_token("admin_123", UserRole.ADMIN.value, secret="wrong-secret-key-12345")
    response = client.get("/test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "טוקן לא תקין" in response.json()["detail"]


@pytest.mark.asyncio
async def test_readonly_aggregate_blocks_write_stages():
    # Attempting to use $out or $merge must raise ValueError
    with pytest.raises(ValueError, match="Forbidden pipeline stage"):
        await run_readonly_aggregate(
            collection_name="entries",
            pipeline=[{"$match": {}}, {"$out": "malicious_collection"}],
        )

    with pytest.raises(ValueError, match="Forbidden pipeline stage"):
        await run_readonly_aggregate(
            collection_name="entries",
            pipeline=[{"$match": {}}, {"$merge": {"into": "entries"}}],
        )


@pytest.mark.asyncio
async def test_readonly_aggregate_blocks_unauthorized_collections():
    with pytest.raises(ValueError, match="not in allowed read-only collections"):
        await run_readonly_aggregate(
            collection_name="system.users",
            pipeline=[{"$match": {}}],
        )
