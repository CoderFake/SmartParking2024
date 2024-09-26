import os
from urllib.parse import urljoin, ParseResult
from .base import StorageSettings, Storage


class LocalStorage(Storage):
    """
    Storage class representing local files.

    Corresponds to URLs with an empty scheme or the `file` scheme.
    """

    @classmethod
    def accept(cls, scheme: str) -> bool:
        """
        Determines if the provided scheme is supported by this storage class.

        Args:
            scheme (str): The URL scheme.

        Returns:
            bool: True if the scheme is empty or 'file', False otherwise.
        """
        return scheme == '' or scheme == 'file'

    def __init__(self, url: ParseResult) -> None:
        """
        Initializes the LocalStorage instance from URL components.

        Args:
            url (ParseResult): Parsed URL components.
        """
        super().__init__(url)
        self.root = url.path

    def _on(self, path: str) -> str:
        """
        Joins the root directory with the provided file path.

        Args:
            path (str): The file path.

        Returns:
            str: The absolute file path.
        """
        return os.path.join(self.root, path)

    def exists(self, path: str) -> bool:
        """
        Checks if a file exists at the specified path.

        Args:
            path (str): The file path.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        return os.path.exists(self._on(path))

    def read(self, path: str) -> bytes:
        """
        Reads the content of the specified file.

        Args:
            path (str): The file path.

        Returns:
            bytes: The file data.
        """
        path = self._on(path)
        with open(path, 'rb') as f:
            return f.read()

    def write(self, path: str, data: bytes) -> int:
        """
        Writes data to the specified file.

        Args:
            path (str): The file path.
            data (bytes): The data to write.

        Returns:
            int: The number of bytes written.
        """
        path = self._on(path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            return f.write(data)

    def delete(self, path: str) -> None:
        """
        Deletes the specified file.

        Args:
            path (str): The file path.
        """
        os.remove(self._on(path))

    def urlize(self, path: str, root: str, **kwargs) -> str:
        """
        Generates an accessible URL for the specified file.

        Args:
            path (str): The file path.
            root (str): The root URL to prepend.

        Returns:
            str: The accessible URL for the file.
        """
        return urljoin(root, path)
