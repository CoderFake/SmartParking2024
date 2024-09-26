import asyncio
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
import json
import logging
import sys
from uuid import uuid4
from types import ModuleType
from typing import Any, Callable, Optional, Union, Awaitable, Generic, Protocol, TypeVar, TYPE_CHECKING, Dict
from typing_extensions import Self
import fitz  # PyMuPDF library for PDF processing
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from smartparking.ext.firebase.base import FirebaseAuth, FirebaseAdmin, FirebaseAuthSettings
from smartparking.ext.storage.base import Storage
from smartparking.config import ApplicationSettings


class Closeable(Protocol):
    async def close(self, exc: Optional[Exception]) -> None:
        ...


T = TypeVar('T', bound=Closeable)


@dataclass
class Resources:
    db: AsyncEngine
    storage: Storage
    firebase: Union[FirebaseAuth, FirebaseAdmin]
    logger: logging.Logger

    def open(self) -> 'ResourceSession':
        return ResourceSession(
            id=str(uuid4()),
            db=async_sessionmaker(self.db, expire_on_commit=False)(),
            storage=self.storage,
            firebase=self.firebase,
            logger=self.logger,
        )


@dataclass
class ResourceSession(Closeable):
    id: str
    db: AsyncSession
    storage: Storage
    firebase: Union[FirebaseAuth, FirebaseAdmin]
    logger: logging.Logger

    @property
    def tx(self) -> AsyncSession:
        if not self.db.sync_session.in_transaction:
            self.db.sync_session.begin()
        return self.db

    _status: bool = field(init=False)

    def __post_init__(self):
        self._status = True

    def fail(self) -> None:
        self._status = False

    async def close(self, exc: Optional[Exception]) -> None:
        """
        Close the resource session, committing or rolling back the transaction based on the status.

        Args:
            exc (Optional[Exception]): The exception that occurred, if any.
        """
        status = self._status and exc is None

        # Close resources. Only the DB session requires cleanup operations.
        try:
            if self.db.in_transaction():
                if status:
                    self.logger.debug(f"Committing transaction: {self.id}")
                    await self.db.commit()
                else:
                    self.logger.debug(f"Rolling back transaction: {self.id}")
                    await self.db.rollback()
        except Exception as e:
            self.logger.warning("Exception occurred while closing transaction.", exc_info=e)
        finally:
            await self.db.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.close(exc_value)

    @property
    def auth(self) -> FirebaseAuth:
        """
        Retrieve the FirebaseAuth instance from the FirebaseAdmin if applicable.

        Returns:
            FirebaseAuth: The Firebase authentication instance.
        """
        return self.firebase if isinstance(self.firebase, FirebaseAuth) else self.firebase.auth


_context = ContextVar[ResourceSession]('_context')


async def configure(settings: ApplicationSettings, logger: logging.Logger) -> tuple[Resources, Callable]:
    """
    Configure the application resources, including the database engine, storage, and Firebase services.

    Args:
        settings (ApplicationSettings): The application settings.
        logger (logging.Logger): The logger instance.

    Returns:
        tuple[Resources, Callable]: A tuple containing the Resources instance and a session-calling function.
    """
    # Create the asynchronous database engine
    engine = create_async_engine(
        settings.db.dsn,
        echo_pool=settings.db.echo_pool and "debug",
    )
    if settings.db.echo:
        engine.echo = True

    # Initialize storage based on the provided URL
    import smartparking.ext.storage.local
    import smartparking.ext.storage.s3
    storage = Storage.of(settings.storage.url)
    if storage is None:
        raise ValueError(f"Invalid URL for storage: {settings.storage.url}")

    # Initialize Firebase services
    firebase = FirebaseAuth(settings.firebase) if isinstance(settings.firebase,
                                                             FirebaseAuthSettings) else FirebaseAdmin(settings.firebase)

    resources = Resources(
        db=engine,
        storage=storage,
        firebase=firebase,
        logger=logger,
    )

    async def call_session(next: Callable[[ResourceSession], Awaitable[Any]]) -> Callable[
        [ResourceSession], Awaitable[Any]]:
        """
        Middleware to handle resource sessions within a context.

        Args:
            next (Callable[[ResourceSession], Awaitable[Any]]): The next callable in the middleware chain.

        Returns:
            Callable[[ResourceSession], Awaitable[Any]]: The wrapped callable.
        """
        session = resources.open()
        token = _context.set(session)
        async with session:
            try:
                return await next(session)
            except:
                session.fail()
                raise
            finally:
                _context.reset(token)

    return resources, call_session


@dataclass
class ContextualResources:
    """
    Context manager for handling resource sessions, supporting both synchronous and asynchronous contexts.
    """
    cxt: ContextVar[ResourceSession]
    resources: Resources
    event_loop: Optional[asyncio.AbstractEventLoop]
    token: Optional[Token] = field(default=None, init=False)

    @classmethod
    def of(cls, resources: Resources, event_loop: Optional[asyncio.AbstractEventLoop] = None) -> 'ContextualResources':
        """
        Factory method to create an instance of ContextualResources.

        Args:
            resources (Resources): The application resources.
            event_loop (Optional[asyncio.AbstractEventLoop]): The event loop, if any.

        Returns:
            ContextualResources: The instantiated ContextualResources.
        """
        return cls(_context, resources, event_loop)

    def __enter__(self) -> ResourceSession:
        session = self.resources.open()
        self.token = self.cxt.set(session)
        return session

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        value = self.cxt.get()
        try:
            async def close():
                await value.close(exc_value)

            if self.event_loop:
                self.event_loop.run_until_complete(close())
            else:
                asyncio.run(close())
        finally:
            if self.token is not None:
                self.cxt.reset(self.token)

    async def __aenter__(self) -> ResourceSession:
        session = self.resources.open()
        self.token = self.cxt.set(session)
        return session

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        value = self.cxt.get()
        try:
            await value.close(exc_value)
        finally:
            if self.token is not None:
                self.cxt.reset(self.token)


class ContextAccessor(Generic[T]):
    """
    Accessor for retrieving context variables.
    """

    def __init__(self, cxt: ContextVar[T]) -> None:
        self.cxt = cxt

    def __getattr__(self, name: str) -> Any:
        return getattr(self.cxt.get(), name)


class Module(ModuleType):
    """
    Module accessor.
    """
    accessor = ContextAccessor[ResourceSession](_context)

    @property
    def context(self) -> ResourceSession:
        return Module.accessor  # type: ignore


sys.modules[__name__].__class__ = Module
if TYPE_CHECKING:
    context: ResourceSession
