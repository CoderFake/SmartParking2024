from enum import Enum, auto
from typing import Any, Optional


def dauto(doc: str = ""):
    """
    Helper function to create enum members with automatic values and documentation.

    Args:
        doc (str): Documentation string for the enum member.

    Returns:
        tuple: A tuple containing an auto-generated value and the documentation string.
    """
    return auto(), doc


class Errorneous:
    """
    Base class for defining custom errors within the application.
    """

    def __init__(self, value, doc: Optional[str] = None) -> None:
        """
        Initialize the Errorneous instance.

        Args:
            value: The value associated with the error.
            doc (Optional[str]): Documentation string for the error.
        """
        self._doc = doc or ""

    @property
    def doc(self) -> str:
        """
        Get the documentation string of the error.

        Returns:
            str: The documentation string.
        """
        return self._doc

    @property
    def value(self) -> Any:
        """
        Get the value associated with the error.

        Returns:
            Any: The error value.
        """
        return self

    @property
    def detail(self) -> Any:
        """
        Get detailed information about the error.

        Returns:
            Any: Detailed error information.
        """
        return None

    @property
    def key(self) -> str:
        """
        Get the key/name of the error.

        Returns:
            str: The error key/name.
        """
        return self.name  # type: ignore

    @property
    def message(self) -> str:
        """
        Get the default error message.

        Returns:
            str: The error message.
        """
        return f"Service operation failed by {self.name}"  # type: ignore

    @property
    def args(self) -> tuple:
        """
        Get the positional arguments for the error message.

        Returns:
            tuple: Positional arguments.
        """
        return ()

    @property
    def kwargs(self) -> dict[str, Any]:
        """
        Get the keyword arguments for the error message.

        Returns:
            dict[str, Any]: Keyword arguments.
        """
        return {}

    def was(self, *candidates) -> bool:
        """
        Check if the error matches any of the provided candidate errors.

        Args:
            candidates: Candidate error instances to compare against.

        Returns:
            bool: True if the error matches any candidate, False otherwise.
        """
        return any(map(lambda c: c is self.value, candidates))

    def on(
        self,
        __detail: Any = None,
        __message: Optional[str] = None,
        /,
        *args,
        **kwargs
    ) -> 'DetailedErroneous':
        """
        Create a DetailedErroneous instance with additional details.

        Args:
            __detail (Any): Detailed information about the error.
            __message (Optional[str]): Custom error message.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments for message formatting.

        Returns:
            DetailedErroneous: An instance with detailed error information.
        """
        return DetailedErroneous(self, __detail, __message, *args, **kwargs)


class DetailedErroneous(Errorneous):
    """
    Extended error class that includes detailed information.
    """

    def __init__(
        self,
        base: Errorneous,
        __detail: Any = None,
        __message: Optional[str] = None,
        /,
        *args,
        **kwargs
    ) -> None:
        """
        Initialize the DetailedErroneous instance.

        Args:
            base (Errorneous): The base error instance.
            __detail (Any): Detailed information about the error.
            __message (Optional[str]): Custom error message.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments for message formatting.
        """
        super().__init__(None)
        self._base = base
        self._detail = __detail
        self._message = __message
        self._args = args
        self._kwargs = kwargs

    @property
    def doc(self) -> str:
        """
        Get the documentation string from the base error.

        Returns:
            str: The documentation string.
        """
        return self._base.doc

    @property
    def value(self) -> Any:
        """
        Get the value from the base error.

        Returns:
            Any: The error value.
        """
        return self._base.value

    @property
    def detail(self) -> Any:
        """
        Get the detailed information about the error.

        Returns:
            Any: Detailed error information.
        """
        return self._detail

    @property
    def key(self) -> str:
        """
        Get the key/name from the base error.

        Returns:
            str: The error key/name.
        """
        return self._base.key

    @property
    def message(self) -> str:
        """
        Get the customized error message if provided, otherwise the detail as string.

        Returns:
            str: The error message.
        """
        return (self._message and self._message.format(*self._args, **self._kwargs)) or str(
            self._detail
        )

    @property
    def args(self) -> tuple:
        """
        Get the positional arguments for the error message.

        Returns:
            tuple: Positional arguments.
        """
        return self._args

    @property
    def kwargs(self) -> dict[str, Any]:
        """
        Get the keyword arguments for the error message.

        Returns:
            dict[str, Any]: Keyword arguments.
        """
        return self._kwargs


class Errors(Errorneous, Enum):
    """
    Enumeration of predefined application errors.
    """

    #------------------------------------------------------------
    # Service Errors
    #------------------------------------------------------------
    # Common
    IO_ERROR = dauto("Input/output error.")

    # Account
    UNAUTHORIZED = dauto("Authentication failed.")
    NOT_SIGNED_UP = dauto("Sign-up is required.")

    # Data
    DATA_NOT_FOUND = dauto("Data does not exist.")
    INVALID_IMAGE_FORMAT = dauto("Invalid image format.")

    # Validations
    INVALID_CONTENT_TYPE = dauto("Invalid Content-Type.")
    INVALID_MULTIPART = dauto("Invalid multipart format.")
