from io import BytesIO
from urllib.parse import parse_qs, ParseResult
from typing import Optional
from .base import Storage

try:
    import boto3
    from botocore.exceptions import ClientError
    import logging

    logger = logging.getLogger(__name__)

    class S3Storage(Storage):
        """
        Storage class for Amazon S3.

        Corresponds to URLs with the `s3` scheme.
        """

        @classmethod
        def accept(cls, scheme: str) -> bool:
            """
            Determines if the provided scheme is supported by this storage class.

            Args:
                scheme (str): The URL scheme.

            Returns:
                bool: True if the scheme is 's3', False otherwise.
            """
            return scheme.lower() == 's3'

        def __init__(self, url: ParseResult) -> None:
            """
            Initializes the S3Storage instance from URL components.

            Args:
                url (ParseResult): Parsed URL components.
            """
            super().__init__(url)
            query_params = parse_qs(url.query)

            access_key = query_params.get('access_key', [None])[0]
            secret_key = query_params.get('secret', [None])[0]

            # Initialize S3 client with Signature Version 4
            if access_key and secret_key:
                self.client = boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=url.netloc,
                    config=boto3.session.Config(signature_version='s3v4')
                )
            else:
                self.client = boto3.client(
                    's3',
                    region_name=url.netloc,
                    config=boto3.session.Config(signature_version='s3v4')
                )

            self.bucket = url.path.lstrip('/')
            logger.debug(f"Initialized S3Storage with bucket: {self.bucket}")

        def exists(self, path: str) -> bool:
            """
            Checks if a file exists at the specified path in the S3 bucket.

            Args:
                path (str): The file path.

            Returns:
                bool: True if the file exists, False otherwise.
            """
            try:
                self.client.head_object(Bucket=self.bucket, Key=path)
                logger.debug(f"File exists: {path}")
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    logger.debug(f"File does not exist: {path}")
                    return False
                else:
                    logger.error(f"Error checking existence of {path}: {e}")
                    raise

        def read(self, path: str) -> bytes:
            """
            Reads the content of the specified file from the S3 bucket.

            Args:
                path (str): The file path.

            Returns:
                bytes: The file data.

            Raises:
                FileNotFoundError: If the file does not exist.
                IOError: If an I/O error occurs.
            """
            try:
                response = self.client.get_object(Bucket=self.bucket, Key=path)
                data = response['Body'].read()
                logger.info(f"Read {len(data)} bytes from {path}")
                return data
            except self.client.exceptions.NoSuchKey:
                logger.error(f"File not found: {path}")
                raise FileNotFoundError(f"The file {path} does not exist in bucket {self.bucket}.")
            except ClientError as e:
                logger.error(f"Error reading file {path}: {e}")
                raise IOError(f"An error occurred while reading the file {path}: {e}")

        def write(self, path: str, data: bytes, public: bool = False) -> int:
            """
            Writes data to the specified file in the S3 bucket.

            Args:
                path (str): The file path.
                data (bytes): The data to write.
                public (bool): Whether to make the file publicly accessible (default: False).

            Returns:
                int: The number of bytes written.

            Raises:
                IOError: If an I/O error occurs.
            """
            try:
                extra_args = {}
                if public:
                    extra_args['ACL'] = 'public-read'

                self.client.put_object(
                    Bucket=self.bucket,
                    Key=path,
                    Body=data,
                    **extra_args
                )
                bytes_written = len(data)
                logger.info(f"Wrote {bytes_written} bytes to {path} with public={public}")
                return bytes_written
            except ClientError as e:
                logger.error(f"Error writing to file {path}: {e}")
                raise IOError(f"An error occurred while writing to the file {path}: {e}")

        def delete(self, path: str) -> None:
            """
            Deletes the specified file from the S3 bucket.

            Args:
                path (str): The file path.

            Raises:
                FileNotFoundError: If the file does not exist.
                IOError: If an I/O error occurs.
            """
            try:
                self.client.delete_object(Bucket=self.bucket, Key=path)
                logger.info(f"Deleted file at {path}")
            except self.client.exceptions.NoSuchKey:
                logger.error(f"File not found for deletion: {path}")
                raise FileNotFoundError(f"The file {path} does not exist in bucket {self.bucket}.")
            except ClientError as e:
                logger.error(f"Error deleting file {path}: {e}")
                raise IOError(f"An error occurred while deleting the file {path}: {e}")

        def urlize(self, path: str, public: bool = False, expiration: int = 3600, **kwargs) -> str:
            """
            Generates an accessible URL for the specified file.

            If the `public` parameter is True, returns the public URL.
            Otherwise, returns a presigned URL with the specified expiration.

            Args:
                path (str): The file path.
                public (bool): Whether to return a public URL (default: False).
                expiration (int): Time in seconds for the presigned URL to remain valid.

            Returns:
                str: The accessible URL for the file.
            """
            try:
                if public:
                    url = f"https://{self.bucket}.s3.{self.client.meta.region_name}.amazonaws.com/{path}"
                    logger.debug(f"Generated public URL for {path}: {url}")
                    return url
                else:
                    url = self.client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': self.bucket, 'Key': path},
                        ExpiresIn=expiration,
                        **kwargs
                    )
                    logger.debug(f"Generated presigned URL for {path}: {url}")
                    return url
            except ClientError as e:
                logger.error(f"Error generating URL for {path}: {e}")
                raise

except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("boto3 is not installed. S3Storage will not be available.")
