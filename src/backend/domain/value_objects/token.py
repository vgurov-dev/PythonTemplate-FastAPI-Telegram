"""Token value object for domain layer."""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TokenPayload(BaseModel):
    """JWT token payload schema."""

    model_config = ConfigDict(extra="forbid")

    service: str = Field(..., min_length=1, description="Service name")
    exp: int = Field(..., description="Expiration timestamp (Unix)")
    iat: int = Field(..., description="Issued at timestamp (Unix)")

    @computed_field
    @property
    def exp_datetime(self) -> datetime:
        """Expiration time as datetime."""
        return datetime.fromtimestamp(self.exp, tz=timezone.utc)

    @computed_field
    @property
    def iat_datetime(self) -> datetime:
        """Issued at time as datetime."""
        return datetime.fromtimestamp(self.iat, tz=timezone.utc)
