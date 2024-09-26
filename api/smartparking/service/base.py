from enum import Enum, auto
from functools import wraps
import inspect
from typing import Any, Optional, Callable, TypeVar, ParamSpec, Generic, Awaitable, Concatenate, cast, overload
from smartparking.model.errors import Errorneous


R = TypeVar('R')
P = ParamSpec('P')


def dauto(doc: str = ""):
    return auto(), doc


class Result(Generic[R]):
    @property
    def error(self) -> Optional[Errorneous]:
        return None

    @property
    def is_resolved(self) -> bool:
        return True

    def __enter__(self):
        return ResultGuard(self)

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def __bool__(self) -> bool:
        return True

    def get(self) -> R:
        raise NotImplementedError()

    def or_else(self, handler: Callable[[Errorneous], Any]) -> R:
        raise NotImplementedError()

    def was(self, *candidates) -> bool:
        return False

    def resolve(self) -> 'Result':
        return self


class ServiceContext:
    class Aborted(Exception):
        def __init__(self, result: Result, *args: object) -> None:
            super().__init__(*args)
            self.result = result

    class Unexpected(Errorneous, Enum):
        UNEXPECTED = auto()

    def __init__(self, catch_all=False) -> None:
        self.result: Result[Any] = Success(None)
        self.catch_all = catch_all

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is ServiceContext.Aborted:
            self.result = exc_value.result
            return True
        elif exc_type is not None and self.catch_all:
            self.result = Failure(ServiceContext.Unexpected.UNEXPECTED)
            return True

    def __le__(self, result: Result[R]) -> R:
        if result:
            self.result = result
            return result.get()
        else:
            raise ServiceContext.Aborted(result)


Maybe = R | Errorneous


def service(f: Callable[P, Awaitable[R | Errorneous]]) -> Callable[P, Awaitable[Result[R]]]:
    @wraps(f)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Result[R]:
        r = await f(*args, **kwargs)
        if isinstance(r, Errorneous):
            return Failure(r)
        else:
            return Success(cast(R, r))
    return wrapper


class ResultGuard:
    def __init__(self, result: Result) -> None:
        self.result = result

    @property
    def error(self) -> Optional[Errorneous]:
        return self.result.error

    def was(self, *candidates) -> bool:
        return self.result.was(*candidates)

    def otherwise(self) -> bool:
        self.result.resolve()
        return not bool(self.result)


class Success(Result[R]):
    def __init__(self, value: R) -> None:
        self.value = value

    def get(self) -> R:
        return self.value

    def or_else(self, handler: Callable[[Errorneous], Any]) -> R:
        return self.value


class Failure(Result):
    def __init__(self, error: Errorneous) -> None:
        self._error = error
        self._resolved = False

    @property
    def error(self) -> Optional[Errorneous]:
        return self._error

    @property
    def is_resolved(self) -> bool:
        return self._resolved

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None and not self._resolved:
            raise UnhandledErroneousException(self._error)

    def __bool__(self) -> bool:
        return False

    def get(self) -> R:
        raise UnhandledErroneousException(self._error)

    def or_else(self, handler: Callable[[Errorneous], Any]) -> R:
        return handler(self._error)

    def was(self, *candidates) -> bool:
        if self._error.was(*candidates):
            self.resolve()
            return True
        else:
            return False

    def resolve(self) -> 'Result':
        self._resolved = True
        return self


class UnhandledErroneousException(Exception):
    def __init__(self, error: Errorneous, *args: object) -> None:
        super().__init__(*args)
        self.error = error

    def __str__(self) -> str:
        return f"Unhandled error: {self.error.message}"