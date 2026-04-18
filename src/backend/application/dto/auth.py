"""Auth DTO schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Schema for login request."""

    service_key: Optional[str] = None
    service_name: Optional[str] = "bot"


class RefreshRequest(BaseModel):
    """Schema for token refresh request."""

    token: str


class TokenResponse(BaseModel):
    """Schema for token response."""

    token: str
    expires_at: datetime
    service: str