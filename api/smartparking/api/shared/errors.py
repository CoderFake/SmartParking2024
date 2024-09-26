from collections.abc import Callable
from configparser import ConfigParser
from dataclasses import field
from dataclasses import dataclass as builtin_dataclass
import logging
from typing import Any, Literal, Union, Optional, NoReturn, cast
from typing_extensions import Self
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler as default_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from pydantic import ValidationError, Field
from pydantic.dataclasses import dataclass
from pydantic_core import ErrorDetails
from smartparking.model.errors import Errorneous
from .i18n import I18N


#----------------------------------------------------------------
# Response types
#----------------------------------------------------------------
@dataclass
class ErrorResponse:
    """
    Common response structure for errors.
    """
    code: str = Field(description="Error code.")
    message: str = Field(description="Error message.")
    args: list[Any] = Field(default_factory=list, description="Arguments for formatting the error message.")
    kwargs: dict[str, Any] = Field(default_factory=dict, description="Keyword arguments for formatting the error message.")
    detail: Any = Field(default=None, description="Detailed information.")

    def localize(self, formatter: Callable[[str], str | None]) -> Self:
        """
        Modify the error message using localization.

        Args:
            formatter: A function that retrieves the message format from the error code.
        Returns:
            This instance after localization.
        """
        fmt = formatter(self.code)
        if fmt:
            self.message = fmt.format(*self.args or [], **self.kwargs or {})
        return self


@dataclass
class ValidationDetail:
    """
    Detailed information for each field in a validation error.
    """
    loc: list[str | int] = Field(description="Path to the field where the error occurred.")
    type: str = Field(description="Type of the error.")
    message: str = Field(description="Error message.")
    kwargs: dict[str, Any] = Field(description="Keyword arguments for formatting the error message.")

    @classmethod
    def from_error(cls, err: ErrorDetails) -> Self:
        """
        Create an instance from a Pydantic validation error detail object.

        Args:
            err (ErrorDetails): The error detail from Pydantic.
        Returns:
            ValidationDetail: An instance containing the error details.
        """
        return ValidationDetail(
            loc=list(err["loc"]),
            type=err["type"],
            message=err["msg"],
            kwargs=cast(dict[str, Any], err["ctx"]) if "ctx" in err else {},
        )


@dataclass
class ValidationErrorResponse(ErrorResponse):
    """
    Response structure for validation errors.
    """
    code: Literal['validation_error'] = Field(description="Error code.")
    detail: list[ValidationDetail] = Field(default_factory=list, description="List of validation errors.")

    def localize(self, formatter: Callable[[str], str | None]) -> Self:
        super().localize(formatter)
        for err in self.detail:
            fmt = formatter(err.type)
            if fmt:
                err.message = fmt.format(**err.kwargs or {})
        return self


#----------------------------------------------------------------
# Application errors
#----------------------------------------------------------------
@builtin_dataclass
class HTTPApplicationError(Exception):
    """
    Errors generated within the application.
    """
    status: int
    error: ErrorResponse
    cause: Exception | None = None


def abort(status: int, cause: Any = None, code: Optional[str] = None, message: Optional[str] = None, *args, **kwargs) -> NoReturn:
    """
    Raise an error from the application.

    Args:
        status: HTTP status code.
        cause: The underlying cause of the error, such as an exception object.
        code: Error code. Defaults to 'unexpected' if not provided.
        message: Error message. Defaults to 'Internal server error' if not provided.
    """
    if isinstance(cause, Errorneous):
        raise HTTPApplicationError(
            status=status,
            error=ErrorResponse(
                code=(code or cause.key).lower(),
                message=message or cause.message,
                args=(list(cause.args) if cause.args else []) + list(args),
                kwargs=(cause.kwargs or {}) | kwargs,
                detail=None,
            ),
            cause=cause.detail if isinstance(cause.detail, Exception) else None
        )
    else:
        raise HTTPApplicationError(
            status=status,
            error=ErrorResponse(
                code=(code or "unexpected").lower(),
                message=message or (cause and str(cause)) or "Internal server error",
                args=list(args),
                kwargs=kwargs,
            )
        )


def abort_with(status: int, code: Optional[str] = None, message: Optional[str] = None) -> Callable[[Any], NoReturn]:
    """
    Get a function that calls `abort` with the provided parameters when given an error object.

    Args:
        status: HTTP status code.
        code: Error code. Defaults to 'unexpected' if not provided.
        message: Error message. Defaults to 'Internal server error' if not provided.
    Returns:
        A function that takes an error object and raises an application error.
    """
    def inner(cause: Any = None):
        abort(status, cause, code, message)
    return inner


def errorModel(*errors: Union[Errorneous, tuple[str, str], Any], model_index: list[int] = [0]) -> type:
    """
    Generate a type that outputs the given errors as a table in the documentation.

    Args:
        errors: A list of error objects.
    Returns:
        A type that encapsulates the given errors.
    """
    def table(*errors) -> str:
        if not errors:
            return ""

        def row(e) -> str:
            if isinstance(e, Errorneous):
                return f"|`{e.name.lower()}`|{e.doc}|"  # type: ignore
            elif isinstance(e, tuple):
                return f"|`{e[0]}`|{e[1] if len(e) > 1 else ''}|"
            else:
                return f"|`{str(e)}`||"

        rows = '\n'.join(row(e) for e in errors)

        return f"""

| code | description |
| :--- | :--- |
{rows}
"""

    # Class name must be unique because Pydantic maps types by their names.
    # Class definition syntax does not work maybe because the dataclass is wrapped by Pydantic model type.
    model = type(
        f"ErrorResponse_{model_index[0]}",
        (ErrorResponse,),
        dict(code=field(metadata=dict(description="Error code." + table(*errors)))),
    )
    model.__annotations__["code"] = str
    model = dataclass(model)
    model_index[0] += 1
    return model


#----------------------------------------------------------------
# Activation
#----------------------------------------------------------------
def setup_handlers(
    app: FastAPI,
    msg: Union[str, list[str], None],
    logger: logging.Logger,
):
    """
    Set up error handlers.

    Args:
        app: The FastAPI application.
        msg: Path(s) to the message file(s) in `ConfigParser` format.
        logger: Logger for error output.
    """
    # Localization
    messages = ConfigParser()
    if msg:
        messages.read(msg)
    available_langs = messages.sections()

    def formatter(req: Request) -> Callable[[str], str | None]:
        def format(code: str) -> str | None:
            i18n = I18N(req.headers.getlist("Accept-Language"))
            lang = i18n.lookup(available_langs)
            section = messages[lang.value if lang else 'DEFAULT']
            return section[code] if code in section else None
        return format

    # Handlers
    # Exceptions raised from FastAPI.
    @app.exception_handler(HTTPException)
    async def http_exception_handler(req: Request, exc: HTTPException):
        if exc.status_code == 401:
            return await default_handler(req, exc)
        logger.warning("Unexpected exception was thrown.", exc_info=exc)
        err = ErrorResponse(
            code="unexpected",
            message=str(exc.detail)
        )
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(err.localize(formatter(req))))

    # Validation errors
    @app.exception_handler(ValidationError)
    async def request_validation_handler(req: Request, exc: ValidationError):
        err = ValidationErrorResponse(
            code="validation_error",
            message=f"Validations failed on {len(exc.errors())} fields.",
            detail=[ValidationDetail.from_error(e) for e in exc.errors()],
        )
        return JSONResponse(status_code=422, content=jsonable_encoder(err.localize(formatter(req))))

    # Validation error caused by invalid response data. Detail should not be responded to client.
    @app.exception_handler(RequestValidationError)
    async def response_validation_handler(req: Request, exc: RequestValidationError):
        logger.warning("Invalid response data raised an error.", exc_info=exc)
        err = ErrorResponse(code="unexpected", message="Internal server error.")
        return JSONResponse(status_code=500, content=jsonable_encoder(err.localize(formatter(req))))

    # Application error.
    @app.exception_handler(HTTPApplicationError)
    async def application_error_handler(req: Request, exc: HTTPApplicationError):
        if exc.cause:
            logger.warning("Unexpected exception was thrown.", exc_info=exc.cause)
        return JSONResponse(status_code=exc.status, content=jsonable_encoder(exc.error.localize(formatter(req))))
