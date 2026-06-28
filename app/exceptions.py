from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Base class for HTTP-agnostic domain errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    """Raised when a requested resource does not exist (or is soft-deleted)."""


class ConflictError(DomainError):
    """Raised when an operation violates a uniqueness/business constraint."""


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain exceptions to HTTP responses. Called once from main.py."""

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(ConflictError)
    async def _conflict(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.message})
