"""Auth DTO schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Schema for login request."""

    service_key: str = Field(..., min_length=1, description="Service secret key")
    service_name: str = Field(default="bot", description="Service name")


class RefreshRequest(BaseModel):
    """Schema for token refresh request."""

    token: str = Field(..., min_length=1, description="JWT token to refresh")


class TokenResponse(BaseModel):
    """Schema for token response."""

    token: str
    expires_at: datetime
    service: str


class TokenPayloadDTO(BaseModel):
    """Token payload DTO."""

    service: str
    exp: int
    iat: int