from typing import Type, Optional
from urllib.parse import urlparse, ParseResult
from pydantic import BaseModel, Field


class StorageSettings(BaseModel):
    url: str = Field(description="URL containing access information for the storage.")


class Storage:
    """
    Abstract base class for file storage.
    """
    _children: set[Type] = set()

    def __init_subclass__(cls) -> None:
        Storage._children.add(cls)

    @staticmethod
    def of(url: str) -> Optional['Storage']:
        """
        Creates an instance of the appropriate subclass based on the URL scheme.

        Args:
            url (str): URL containing access information.

        Returns:
            Optional[Storage]: Storage access object or None if no suitable subclass is found.
        """
        parsed = urlparse(url)
        storage_cls = next(filter(lambda s: s.accept(parsed.scheme), Storage._children), None)
        return storage_cls(parsed) if storage_cls else None

    @classmethod
    def accept(cls, scheme: str) -> bool:
        """
        Checks if the specified scheme is supported by the subclass.

        Args:
            scheme (str): URL scheme.

        Returns:
            bool: True if the scheme is supported, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement the accept method.")

    def __init__(self, url: ParseResult) -> None:
        """
        Initializes the storage instance from URL components.

        Args:
            url (ParseResult): Parsed URL components.
        """
        pass

    def exists(self, path: str) -> bool:
        """
        Checks if a file exists at the specified path.

        Args:
            path (str): File path.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement the exists method.")

    def read(self, path: str) -> bytes:
        """
        Reads the content of the specified file.

        Args:
            path (str): File path.

        Returns:
            bytes: File data.
        """
        raise NotImplementedError("Subclasses must implement the read method.")

    def write(self, path: str, data: bytes):
        """
        Writes data to the specified file.

        Args:
            path (str): File path.
            data (bytes): File data.
        """
        raise NotImplementedError("Subclasses must implement the write method.")

    def delete(self, path: str):
        """
        Deletes the specified file.

        Args:
            path (str): File path.
        """
        raise NotImplementedError("Subclasses must implement the delete method.")

    def urlize(self, path: str, **kwargs) -> str:
        """
        Generates a URL accessible to the specified file.

        Args:
            path (str): File path.

        Returns:
            str: Accessible URL for the file.
        """
        raise NotImplementedError("Subclasses must implement the urlize method.")
