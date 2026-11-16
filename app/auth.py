import logging
from typing import Callable, List, Optional
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import get_settings
from app.models.user import AuthenticatedUser, UserRole

logger = logging.getLogger("entry_ai")

# HTTPBearer security scheme (auto_error=False allows returning custom JSON errors)
security = HTTPBearer(auto_error=False)


def decode_jwt_token(token: str) -> dict:
    """Decodes and validates a JWT token against the shared JWT_SECRET."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="הטוקן פג תוקף (Token has expired)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"טוקן לא תקין (Invalid token: {err})",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> AuthenticatedUser:
    """FastAPI dependency to extract and validate the authenticated user from the Bearer token."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="נדרש טוקן אימות (Authentication token required)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = decode_jwt_token(token)

    user_id = payload.get("userId") or payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="הטוקן אינו מכיל מזהה משתמש (Token missing user ID)",
        )

    role_str = payload.get("role")
    try:
        user_role = UserRole(role_str) if role_str else UserRole.SCANNER
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"תפקיד משתמש לא חוקי: {role_str}",
        )

    return AuthenticatedUser(
        user_id=str(user_id),
        role=user_role,
        username=payload.get("username"),
        email=payload.get("email"),
    )


def require_role(allowed_roles: List[UserRole]) -> Callable:
    """Returns a dependency ensuring the user holds one of the specified roles."""
    async def role_checker(user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            logger.warning(
                f"Unauthorized access attempt by user {user.user_id} with role '{user.role}' "
                f"(requires one of: {[r.value for r in allowed_roles]})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="אין לך הרשאה לבצע פעולה זו (Forbidden: Insufficient permissions)",
            )
        return user

    return role_checker


# Convenient pre-configured role dependencies
require_superadmin = require_role([UserRole.SUPERADMIN])
require_admin = require_role([UserRole.SUPERADMIN, UserRole.ADMIN])
require_scanner = require_role([UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.SCANNER])
