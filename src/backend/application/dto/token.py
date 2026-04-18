"""Token payload schemas."""
from pydantic import BaseModel, Field


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    service: str = Field(..., min_length=1, description="Service name")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")

    model_config = {"extra": "forbid"}