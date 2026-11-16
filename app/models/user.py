from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    SCANNER = "scanner"


class AuthenticatedUser(BaseModel):
    user_id: str = Field(..., description="Unique user identifier from JWT payload")
    role: UserRole = Field(..., description="Role of the authenticated user")
    username: Optional[str] = Field(None, description="Username if available")
    email: Optional[str] = Field(None, description="User email address if available")
