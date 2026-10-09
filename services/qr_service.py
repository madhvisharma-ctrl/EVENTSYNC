"""
EventSync Dynamic QR Service

Handles:
- Short-lived dynamic QR token generation
- QR token validation
- QR image generation
- Event QR lifecycle management

QR tokens are intentionally short-lived and are validated
server-side before an event verification can proceed.
"""

from datetime import datetime, timedelta, timezone
from io import BytesIO
import base64
import secrets

import qrcode

from database.db import execute_write, fetch_all, fetch_one
from utils.helpers import parse_datetime


QR_VALIDITY_SECONDS = 30
QR_PREFIX = "EVENTSYNC:"


def _utc_now() -> datetime:
    """
    Return the current UTC time.
    """
    return datetime.now(timezone.utc)


def _database_datetime(value: datetime) -> str:
    """
    Convert a UTC datetime to the SQLite datetime format.
    """
    return value.astimezone(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _normalize_token(token: str | None) -> str:
    """
    Normalize a token received from a QR scanner.
    """
    if not token:
        return ""

    token = str(token).strip()

    if token.startswith(QR_PREFIX):
        token = token[len(QR_PREFIX):]

    return token.strip()


def _generate_token() -> str:
    """
    Generate a cryptographically random QR token.
    """
    return secrets.token_urlsafe(32)


def get_active_qr_token(event_id: int):
    """
    Return the currently active and non-expired QR token for an event.
    """
    now = _database_datetime(_utc_now())

    return fetch_one(
        """
        SELECT
            id,
            event_id,
            token,
            generated_by,
            created_at,
            expires_at,
            is_active
        FROM qr_tokens
        WHERE event_id = ?
          AND is_active = 1
          AND expires_at > ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (event_id, now),
    )


def deactivate_event_qr_tokens(event_id: int) -> None:
    """
    Deactivate all currently active QR tokens for an event.
    """
    execute_write(
        """
        UPDATE qr_tokens
        SET is_active = 0
        WHERE event_id = ?
          AND is_active = 1
        """,
        (event_id,),
    )


def generate_qr_token(
    event_id: int,
    generated_by: int,
    validity_seconds: int = QR_VALIDITY_SECONDS,
) -> dict:
    """
    Generate a new short-lived dynamic QR token.

    Any previously active token for the same event is invalidated.
    """
    if not event_id:
        raise ValueError("Event ID is required.")

    if not generated_by:
        raise ValueError("QR generator user is required.")

    try:
        validity_seconds = int(validity_seconds)
    except (TypeError, ValueError):
        validity_seconds = QR_VALIDITY_SECONDS

    if validity_seconds < 5:
        validity_seconds = 5

    if validity_seconds > 300:
        validity_seconds = 300

    event = fetch_one(
        """
        SELECT
            id,
            event_name,
            status,
            event_date,
            start_time,
            end_time
        FROM events
        WHERE id = ?
        LIMIT 1
        """,
        (event_id,),
    )

    if event is None:
        raise ValueError("Event not found.")

    if event["status"] in {"cancelled", "completed"}:
        raise ValueError(
            "A QR code cannot be generated for this event."
        )

    generator = fetch_one(
        """
        SELECT
            id,
            role,
            is_active
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (generated_by,),
    )

    if generator is None or not generator["is_active"]:
        raise ValueError("QR generator account is unavailable.")

    # Only an event coordinator or an admin may generate the QR.
    if generator["role"] != "admin":
        coordinator = fetch_one(
            """
            SELECT id
            FROM event_coordinators
            WHERE event_id = ?
              AND user_id = ?
            LIMIT 1
            """,
            (event_id, generated_by),
        )

        if coordinator is None:
            raise ValueError(
                "Only an assigned event coordinator can generate the QR."
            )

    deactivate_event_qr_tokens(event_id)

    now = _utc_now()
    expires_at = now + timedelta(seconds=validity_seconds)

    token = _generate_token()

    token_id = execute_write(
        """
        INSERT INTO qr_tokens (
            event_id,
            token,
            generated_by,
            created_at,
            expires_at,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (
            event_id,
            token,
            generated_by,
            _database_datetime(now),
            _database_datetime(expires_at),
        ),
    )

    return {
        "id": token_id,
        "event_id": event_id,
        "token": token,
        "payload": f"{QR_PREFIX}{token}",
        "generated_by": generated_by,
        "created_at": _database_datetime(now),
        "expires_at": _database_datetime(expires_at),
        "expires_in": validity_seconds,
        "is_active": True,
    }


def get_qr_token_by_id(qr_token_id: int):
    """
    Return a QR token by database ID.
    """
    return fetch_one(
        """
        SELECT
            id,
            event_id,
            token,
            generated_by,
            created_at,
            expires_at,
            is_active
        FROM qr_tokens
        WHERE id = ?
        LIMIT 1
        """,
        (qr_token_id,),
    )


def get_qr_token(token: str):
    """
    Return a QR token record by token value.
    """
    normalized_token = _normalize_token(token)

    if not normalized_token:
        return None

    return fetch_one(
        """
        SELECT
            id,
            event_id,
            token,
            generated_by,
            created_at,
            expires_at,
            is_active
        FROM qr_tokens
        WHERE token = ?
        LIMIT 1
        """,
        (normalized_token,),
    )


def is_qr_token_valid(
    token: str,
    event_id: int | None = None,
) -> bool:
    """
    Check whether a QR token is active, belongs to the requested
    event (when provided), and has not expired.
    """
    qr_token = get_qr_token(token)

    if qr_token is None:
        return False

    if not qr_token["is_active"]:
        return False

    if event_id is not None and qr_token["event_id"] != event_id:
        return False

    expires_at = parse_datetime(qr_token["expires_at"])

    if expires_at is None:
        return False

    now = _utc_now()

    if expires_at <= now:
        execute_write(
            """
            UPDATE qr_tokens
            SET is_active = 0
            WHERE id = ?
            """,
            (qr_token["id"],),
        )
        return False

    return True


def validate_qr_token(
    token: str,
    event_id: int | None = None,
) -> dict:
    """
    Fully validate a QR token.

    Returns a structured validation result.
    """
    normalized_token = _normalize_token(token)

    if not normalized_token:
        return {
            "valid": False,
            "reason": "QR token is missing.",
            "token": None,
            "qr_token": None,
        }

    qr_token = get_qr_token(normalized_token)

    if qr_token is None:
        return {
            "valid": False,
            "reason": "QR token is invalid or not found.",
            "token": normalized_token,
            "qr_token": None,
        }

    if event_id is not None and qr_token["event_id"] != event_id:
        return {
            "valid": False,
            "reason": "QR token does not belong to this event.",
            "token": normalized_token,
            "qr_token": qr_token,
        }

    if not qr_token["is_active"]:
        return {
            "valid": False,
            "reason": "This QR token has been deactivated.",
            "token": normalized_token,
            "qr_token": qr_token,
        }

    expires_at = parse_datetime(qr_token["expires_at"])

    if expires_at is None:
        return {
            "valid": False,
            "reason": "QR token expiry information is invalid.",
            "token": normalized_token,
            "qr_token": qr_token,
        }

    now = _utc_now()

    if expires_at <= now:
        execute_write(
            """
            UPDATE qr_tokens
            SET is_active = 0
            WHERE id = ?
            """,
            (qr_token["id"],),
        )

        return {
            "valid": False,
            "reason": "QR token has expired. Please scan the current QR.",
            "token": normalized_token,
            "qr_token": qr_token,
        }

    remaining_seconds = max(
        0,
        int((expires_at - now).total_seconds()),
    )

    return {
        "valid": True,
        "reason": "QR token is valid.",
        "token": normalized_token,
        "qr_token": qr_token,
        "remaining_seconds": remaining_seconds,
    }


def generate_qr_image_bytes(payload: str) -> bytes:
    """
    Generate a PNG QR image from a payload.
    """
    if not payload:
        raise ValueError("QR payload is required.")

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )

    qr.add_data(payload)
    qr.make(fit=True)

    image = qr.make_image()

    output = BytesIO()
    image.save(output, format="PNG")

    return output.getvalue()


def generate_qr_data_uri(payload: str) -> str:
    """
    Generate a base64 PNG data URI suitable for an HTML img tag.
    """
    image_bytes = generate_qr_image_bytes(payload)
    encoded = base64.b64encode(image_bytes).decode("ascii")

    return f"data:image/png;base64,{encoded}"


def generate_qr_image_data(token: str) -> str:
    """
    Generate a QR image data URI for a raw token or QR payload.
    """
    normalized_token = _normalize_token(token)

    if not normalized_token:
        raise ValueError("QR token is required.")

    payload = f"{QR_PREFIX}{normalized_token}"

    return generate_qr_data_uri(payload)


def get_event_qr_status(event_id: int) -> dict:
    """
    Return the current QR status for an event.
    """
    qr_token = get_active_qr_token(event_id)

    if qr_token is None:
        return {
            "active": False,
            "qr_token": None,
            "remaining_seconds": 0,
        }

    expires_at = parse_datetime(qr_token["expires_at"])

    if expires_at is None:
        return {
            "active": False,
            "qr_token": qr_token,
            "remaining_seconds": 0,
        }

    remaining_seconds = max(
        0,
        int((expires_at - _utc_now()).total_seconds()),
    )

    if remaining_seconds <= 0:
        execute_write(
            """
            UPDATE qr_tokens
            SET is_active = 0
            WHERE id = ?
            """,
            (qr_token["id"],),
        )

        return {
            "active": False,
            "qr_token": qr_token,
            "remaining_seconds": 0,
        }

    return {
        "active": True,
        "qr_token": qr_token,
        "remaining_seconds": remaining_seconds,
    }


def get_event_qr_history(event_id: int):
    """
    Return QR token history for an event.
    """
    return fetch_all(
        """
        SELECT
            qt.id,
            qt.event_id,
            qt.token,
            qt.generated_by,
            qt.created_at,
            qt.expires_at,
            qt.is_active,
            u.name AS generated_by_name,
            u.role AS generated_by_role
        FROM qr_tokens qt
        LEFT JOIN users u
            ON u.id = qt.generated_by
        WHERE qt.event_id = ?
        ORDER BY qt.created_at DESC
        """,
        (event_id,),
    )


def deactivate_qr_token(qr_token_id: int) -> bool:
    """
    Deactivate one QR token.
    """
    token = get_qr_token_by_id(qr_token_id)

    if token is None:
        raise ValueError("QR token not found.")

    execute_write(
        """
        UPDATE qr_tokens
        SET is_active = 0
        WHERE id = ?
        """,
        (qr_token_id,),
    )

    return True


def cleanup_expired_tokens(event_id: int | None = None) -> int:
    """
    Deactivate expired QR tokens.

    Returns the number of affected records.
    """
    now = _database_datetime(_utc_now())

    if event_id is not None:
        row = fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM qr_tokens
            WHERE event_id = ?
              AND is_active = 1
              AND expires_at <= ?
            """,
            (event_id, now),
        )

        count = int(row["total"] or 0)

        if count:
            execute_write(
                """
                UPDATE qr_tokens
                SET is_active = 0
                WHERE event_id = ?
                  AND is_active = 1
                  AND expires_at <= ?
                """,
                (event_id, now),
            )

        return count

    row = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM qr_tokens
        WHERE is_active = 1
          AND expires_at <= ?
        """,
        (now,),
    )

    count = int(row["total"] or 0)

    if count:
        execute_write(
            """
            UPDATE qr_tokens
            SET is_active = 0
            WHERE is_active = 1
              AND expires_at <= ?
            """,
            (now,),
        )

    return count