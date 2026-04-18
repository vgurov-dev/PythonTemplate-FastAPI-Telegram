from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""

    def __init__(self, detail: str = None):
        super().__init__(status_code=self.status_code, detail=detail)


class NotFoundException(AppException):
    """Resource not found exception."""

    status_code = status.HTTP_404_NOT_FOUND


class AlreadyExistsException(AppException):
    """Resource already exists exception."""

    status_code = status.HTTP_409_CONFLICT


class UnauthorizedException(AppException):
    """Unauthorized exception."""

    status_code = status.HTTP_401_UNAUTHORIZED


class ForbiddenException(AppException):
    """Forbidden exception."""

    status_code = status.HTTP_403_FORBIDDEN


class ValidationException(AppException):
    """Validation error exception."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class InternalServerException(AppException):
    """Internal server error exception."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR