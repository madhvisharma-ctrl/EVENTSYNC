"""
EventSync Common Helper Functions

Shared utility functions used throughout the application.
"""

from datetime import datetime, timezone
from pathlib import Path
import base64
import re
import uuid


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = STATIC_DIR / "uploads"
FACE_UPLOAD_DIR = UPLOADS_DIR / "faces"


def utc_now() -> datetime:
    """
    Return the current UTC datetime as a timezone-aware datetime.
    """
    return datetime.now(timezone.utc)


def utc_now_string() -> str:
    """
    Return the current UTC time in SQLite-friendly format.
    """
    return utc_now().strftime("%Y-%m-%d %H:%M:%S")


def datetime_to_string(value: datetime | None) -> str | None:
    """
    Convert a datetime object into a standard database string.
    """
    if value is None:
        return None

    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)

    return value.strftime("%Y-%m-%d %H:%M:%S")


def parse_datetime(value: str | None) -> datetime | None:
    """
    Parse common EventSync datetime formats.

    Returns a timezone-aware UTC datetime.
    """
    if not value:
        return None

    value = str(value).strip()

    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    )

    for date_format in formats:
        try:
            parsed = datetime.strptime(value, date_format)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def ensure_upload_directories() -> None:
    """
    Create required upload directories if they do not exist.
    """
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    FACE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str | None) -> str:
    """
    Convert a filename into a safe filesystem filename.
    """
    if not filename:
        return "file"

    filename = Path(filename).name
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    filename = filename.strip("._")

    return filename or "file"


def generate_unique_filename(
    extension: str = ".jpg",
    prefix: str = "file",
) -> str:
    """
    Generate a unique safe filename.
    """
    extension = str(extension or "").strip()

    if extension and not extension.startswith("."):
        extension = f".{extension}"

    extension = extension.lower()

    return f"{prefix}_{uuid.uuid4().hex}{extension}"


def save_base64_image(
    image_data: str,
    output_directory: Path | str,
    prefix: str = "image",
) -> str:
    """
    Decode and save a base64-encoded image.

    Returns the saved filename.

    Supported input examples:
        data:image/jpeg;base64,...
        data:image/png;base64,...
        raw_base64_string
    """
    if not image_data:
        raise ValueError("Image data is required.")

    if not isinstance(image_data, str):
        raise ValueError("Image data must be a string.")

    image_data = image_data.strip()

    extension = ".jpg"

    if image_data.startswith("data:"):
        match = re.match(
            r"^data:image/([a-zA-Z0-9.+-]+);base64,(.*)$",
            image_data,
            flags=re.DOTALL,
        )

        if not match:
            raise ValueError("Invalid base64 image format.")

        image_type = match.group(1).lower()
        image_data = match.group(2)

        extension_map = {
            "jpeg": ".jpg",
            "jpg": ".jpg",
            "png": ".png",
            "webp": ".webp",
        }

        extension = extension_map.get(image_type, ".jpg")

    try:
        image_bytes = base64.b64decode(
            image_data,
            validate=True,
        )
    except Exception as error:
        raise ValueError("Invalid base64 image data.") from error

    if not image_bytes:
        raise ValueError("The image data is empty.")

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    filename = generate_unique_filename(
        extension=extension,
        prefix=prefix,
    )

    output_path = output_directory / filename
    output_path.write_bytes(image_bytes)

    return filename


def save_face_image(image_data: str) -> str:
    """
    Save a student's face image inside the EventSync face upload directory.

    Returns a relative path suitable for storing in the database.
    """
    ensure_upload_directories()

    filename = save_base64_image(
        image_data=image_data,
        output_directory=FACE_UPLOAD_DIR,
        prefix="face",
    )

    return f"uploads/faces/{filename}"


def get_absolute_static_path(relative_path: str | None) -> Path | None:
    """
    Convert a path stored relative to static/ into an absolute path.
    """
    if not relative_path:
        return None

    cleaned_path = str(relative_path).replace("\\", "/").lstrip("/")

    return STATIC_DIR / Path(cleaned_path)


def normalize_email(email: str | None) -> str:
    """
    Normalize an email address for storage and comparison.
    """
    return str(email or "").strip().lower()


def is_valid_email(email: str | None) -> bool:
    """
    Perform basic email validation.
    """
    if not email:
        return False

    email = normalize_email(email)

    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    return bool(re.match(pattern, email))


def normalize_roll_number(roll_no: str | None) -> str:
    """
    Normalize a student roll number.
    """
    return str(roll_no or "").strip().upper()


def clean_text(value: str | None) -> str:
    """
    Safely trim a text value.
    """
    return str(value or "").strip()


def parse_int(value, default: int | None = None) -> int | None:
    """
    Safely convert a value to integer.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_datetime(
    value: str | datetime | None,
    output_format: str = "%d %b %Y, %I:%M %p",
) -> str:
    """
    Format a stored datetime for display.
    """
    if value is None:
        return "-"

    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_datetime(str(value))

    if parsed is None:
        return str(value)

    return parsed.strftime(output_format)


def format_date(
    value: str | datetime | None,
    output_format: str = "%d %b %Y",
) -> str:
    """
    Format a date for display.
    """
    if value is None:
        return "-"

    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = parse_datetime(str(value))

    if parsed is None:
        try:
            parsed = datetime.strptime(str(value), "%Y-%m-%d")
        except ValueError:
            return str(value)

    return parsed.strftime(output_format)


def format_time(value: str | None) -> str:
    """
    Convert HH:MM or HH:MM:SS into a 12-hour display format.
    """
    if not value:
        return "-"

    value = str(value).strip()

    for input_format in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(value, input_format)
            return parsed.strftime("%I:%M %p")
        except ValueError:
            continue

    return value


def is_safe_uuid(value: str | None) -> bool:
    """
    Validate a UUID-like string.
    """
    if not value:
        return False

    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False