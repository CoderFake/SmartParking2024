from dataclasses import dataclass, field
import io
from PIL import Image


@dataclass
class ImageContent:
    image: Image.Image

    @property
    def format(self) -> str:
        """
        Retrieves the image format string interpreted by PIL.

        https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
        """
        return self.image.format or ""

    @property
    def mime(self) -> str:
        """
        Retrieves the MIME type of the image.
        """
        return Image.MIME.get(self.format, 'application/octet-stream')

    @property
    def ext(self) -> str:
        """
        Retrieves the file extension of the image.
        """
        return self.format.lower()

    def bytes(self, format: str | None = None) -> bytes:
        """
        Retrieves the image data as bytes.

        Args:
            format (str | None): The format to save the image in. If None, uses the image's current format.

        Returns:
            bytes: The image data in bytes.
        """
        buf = io.BytesIO()
        self.image.save(buf, format=format or self.format)
        return buf.getvalue()


def load_image(data: bytes) -> ImageContent:
    """
    Interprets image data and loads it into an ImageContent instance.

    Args:
        data (bytes): The image data in bytes.

    Returns:
        ImageContent: The loaded image content with applied EXIF orientation.
    """
    image = Image.open(io.BytesIO(data))

    resolved = resolve_exif(image)

    return ImageContent(resolved)


def resolve_exif(img: Image.Image) -> Image.Image:
    """
    Applies rotation information contained in EXIF data to the image.

    Args:
        img (Image.Image): The PIL Image object.

    Returns:
        Image.Image: The image with EXIF orientation applied.
    """
    exif = img.getexif()
    if exif is None:
        return img

    orientation = exif.get(274, None)

    match orientation:
        case 1:
            img = img
        case 2:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        case 3:
            img = img.transpose(Image.ROTATE_180)
        case 4:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        case 5:
            img = img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
        case 6:
            img = img.transpose(Image.ROTATE_270)
        case 7:
            img = img.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
        case 8:
            img = img.transpose(Image.ROTATE_90)
        case _:
            img = img

    new_img = Image.new(img.mode, img.size)
    new_img.putdata(img.getdata())

    return new_img
