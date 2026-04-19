"""Domain exceptions."""


class DomainError(Exception):
    """Base domain exception."""
    pass


class UserNotFoundError(DomainError):
    """User not found."""
    pass


class TokenExpiredError(DomainError):
    """Token expired."""
    pass


class TokenInvalidError(DomainError):
    """Token invalid."""
    pass