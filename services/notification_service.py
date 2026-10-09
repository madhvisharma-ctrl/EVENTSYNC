"""
EventSync Notification Service

Handles:
- Student verification notifications
- Event-related notifications
- Teacher notification inbox
- Read/unread notification state
- Notification counts
"""

from datetime import datetime, timezone
from typing import Any

from database.db import execute_write, fetch_all, fetch_one
from utils.helpers import clean_text


NOTIFICATION_TYPES = {
    "event_verification",
    "event_registration",
    "event_update",
    "general",
}


def _utc_now_string() -> str:
    """
    Return current UTC time in SQLite-friendly format.
    """
    return datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def create_notification(
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "general",
    event_id: int | None = None,
    student_id: int | None = None,
) -> int:
    """
    Create a notification for a user.

    Returns:
        Newly created notification ID.
    """
    title = clean_text(title)
    message = clean_text(message)
    notification_type = clean_text(
        notification_type
    ).lower()

    if not user_id:
        raise ValueError("User ID is required.")

    if not title:
        raise ValueError("Notification title is required.")

    if not message:
        raise ValueError("Notification message is required.")

    if notification_type not in NOTIFICATION_TYPES:
        notification_type = "general"

    return execute_write(
        """
        INSERT INTO notifications (
            user_id,
            event_id,
            student_id,
            title,
            message,
            notification_type,
            is_read,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """,
        (
            user_id,
            event_id,
            student_id,
            title,
            message,
            notification_type,
            _utc_now_string(),
        ),
    )


def get_notification_by_id(
    notification_id: int,
    user_id: int | None = None,
):
    """
    Return a notification by ID.

    If user_id is supplied, the notification must belong
    to that user.
    """
    if user_id is None:
        return fetch_one(
            """
            SELECT
                n.id,
                n.user_id,
                n.event_id,
                n.student_id,
                n.title,
                n.message,
                n.notification_type,
                n.is_read,
                n.created_at,
                e.event_name,
                e.event_category,
                e.event_date,
                e.start_time,
                e.end_time,
                e.venue,
                s.name AS student_name,
                s.email AS student_email,
                s.roll_no AS student_roll_no
            FROM notifications n
            LEFT JOIN events e
                ON e.id = n.event_id
            LEFT JOIN users s
                ON s.id = n.student_id
            WHERE n.id = ?
            LIMIT 1
            """,
            (notification_id,),
        )

    return fetch_one(
        """
        SELECT
            n.id,
            n.user_id,
            n.event_id,
            n.student_id,
            n.title,
            n.message,
            n.notification_type,
            n.is_read,
            n.created_at,
            e.event_name,
            e.event_category,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            s.name AS student_name,
            s.email AS student_email,
            s.roll_no AS student_roll_no
        FROM notifications n
        LEFT JOIN events e
            ON e.id = n.event_id
        LEFT JOIN users s
            ON s.id = n.student_id
        WHERE n.id = ?
          AND n.user_id = ?
        LIMIT 1
        """,
        (
            notification_id,
            user_id,
        ),
    )


def get_user_notifications(
    user_id: int,
    unread_only: bool = False,
    limit: int = 100,
):
    """
    Return notifications belonging to a user.
    """
    if not user_id:
        return []

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100

    limit = max(1, min(limit, 500))

    if unread_only:
        return fetch_all(
            """
            SELECT
                n.id,
                n.user_id,
                n.event_id,
                n.student_id,
                n.title,
                n.message,
                n.notification_type,
                n.is_read,
                n.created_at,
                e.event_name,
                e.event_category,
                e.event_date,
                e.start_time,
                e.end_time,
                e.venue,
                s.name AS student_name,
                s.email AS student_email,
                s.roll_no AS student_roll_no
            FROM notifications n
            LEFT JOIN events e
                ON e.id = n.event_id
            LEFT JOIN users s
                ON s.id = n.student_id
            WHERE n.user_id = ?
              AND n.is_read = 0
            ORDER BY n.created_at DESC, n.id DESC
            LIMIT ?
            """,
            (
                user_id,
                limit,
            ),
        )

    return fetch_all(
        """
        SELECT
            n.id,
            n.user_id,
            n.event_id,
            n.student_id,
            n.title,
            n.message,
            n.notification_type,
            n.is_read,
            n.created_at,
            e.event_name,
            e.event_category,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            s.name AS student_name,
            s.email AS student_email,
            s.roll_no AS student_roll_no
        FROM notifications n
        LEFT JOIN events e
            ON e.id = n.event_id
        LEFT JOIN users s
            ON s.id = n.student_id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC, n.id DESC
        LIMIT ?
        """,
        (
            user_id,
            limit,
        ),
    )


def get_unread_notification_count(user_id: int) -> int:
    """
    Return the unread notification count for a user.
    """
    if not user_id:
        return 0

    row = fetch_one(
        """
        SELECT COUNT(*) AS unread_count
        FROM notifications
        WHERE user_id = ?
          AND is_read = 0
        """,
        (user_id,),
    )

    if row is None:
        return 0

    return int(row["unread_count"] or 0)


def get_notification_count(user_id: int) -> int:
    """
    Return total notification count for a user.
    """
    if not user_id:
        return 0

    row = fetch_one(
        """
        SELECT COUNT(*) AS notification_count
        FROM notifications
        WHERE user_id = ?
        """,
        (user_id,),
    )

    if row is None:
        return 0

    return int(row["notification_count"] or 0)


def mark_notification_read(
    notification_id: int,
    user_id: int,
) -> bool:
    """
    Mark one notification as read.

    Returns:
        True if a notification was updated.
    """
    if not notification_id or not user_id:
        return False

    notification = get_notification_by_id(
        notification_id,
        user_id,
    )

    if notification is None:
        return False

    execute_write(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE id = ?
          AND user_id = ?
        """,
        (
            notification_id,
            user_id,
        ),
    )

    return True


def mark_notification_unread(
    notification_id: int,
    user_id: int,
) -> bool:
    """
    Mark one notification as unread.
    """
    if not notification_id or not user_id:
        return False

    notification = get_notification_by_id(
        notification_id,
        user_id,
    )

    if notification is None:
        return False

    execute_write(
        """
        UPDATE notifications
        SET is_read = 0
        WHERE id = ?
          AND user_id = ?
        """,
        (
            notification_id,
            user_id,
        ),
    )

    return True


def mark_all_notifications_read(user_id: int) -> int:
    """
    Mark all notifications belonging to a user as read.

    Returns:
        Number of notifications changed.
    """
    if not user_id:
        return 0

    unread_before = get_unread_notification_count(
        user_id
    )

    if unread_before == 0:
        return 0

    execute_write(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
          AND is_read = 0
        """,
        (user_id,),
    )

    return unread_before


def delete_notification(
    notification_id: int,
    user_id: int,
) -> bool:
    """
    Delete one notification belonging to a user.
    """
    if not notification_id or not user_id:
        return False

    notification = get_notification_by_id(
        notification_id,
        user_id,
    )

    if notification is None:
        return False

    execute_write(
        """
        DELETE FROM notifications
        WHERE id = ?
          AND user_id = ?
        """,
        (
            notification_id,
            user_id,
        ),
    )

    return True


def create_event_verification_notification(
    teacher_id: int,
    student_id: int,
    event_id: int,
    student_name: str,
    roll_no: str,
    verification_time: str | None = None,
) -> int:
    """
    Notify a teacher when a student successfully verifies
    event presence.

    This is the primary notification used by the event
    verification workflow.
    """
    student_name = clean_text(student_name)
    roll_no = clean_text(roll_no)

    if not verification_time:
        verification_time = _utc_now_string()

    event = fetch_one(
        """
        SELECT
            id,
            event_name,
            event_category,
            venue
        FROM events
        WHERE id = ?
        LIMIT 1
        """,
        (event_id,),
    )

    if event is None:
        raise ValueError("Event not found.")

    event_name = event["event_name"]

    title = "Event Presence Verified"

    message = (
        f"{student_name} ({roll_no}) verified presence "
        f"for {event_name}. "
        f"QR verified, face verified, "
        f"time: {verification_time}."
    )

    return create_notification(
        user_id=teacher_id,
        event_id=event_id,
        student_id=student_id,
        title=title,
        message=message,
        notification_type="event_verification",
    )


def notify_event_coordinators(
    event_id: int,
    student_id: int,
    student_name: str,
    roll_no: str,
    verification_time: str | None = None,
) -> list[int]:
    """
    Notify all assigned teacher coordinators for an event
    after successful student verification.

    Returns:
        List of created notification IDs.
    """
    coordinators = fetch_all(
        """
        SELECT
            ec.user_id,
            u.name,
            u.role
        FROM event_coordinators ec
        INNER JOIN users u
            ON u.id = ec.user_id
        WHERE ec.event_id = ?
          AND u.is_active = 1
        ORDER BY
            CASE
                WHEN ec.coordinator_role = 'main_coordinator'
                THEN 0
                ELSE 1
            END,
            u.name ASC
        """,
        (event_id,),
    )

    notification_ids = []

    for coordinator in coordinators:
        notification_id = create_event_verification_notification(
            teacher_id=coordinator["user_id"],
            student_id=student_id,
            event_id=event_id,
            student_name=student_name,
            roll_no=roll_no,
            verification_time=verification_time,
        )

        notification_ids.append(notification_id)

    return notification_ids


def create_event_registration_notification(
    user_id: int,
    event_id: int,
    event_name: str,
    participation_role: str,
) -> int:
    """
    Create a confirmation notification after event registration.
    """
    event_name = clean_text(event_name)
    participation_role = clean_text(
        participation_role
    ).replace("_", " ").title()

    title = "Event Registration Confirmed"

    message = (
        f"You are registered for {event_name} "
        f"as {participation_role}."
    )

    return create_notification(
        user_id=user_id,
        event_id=event_id,
        title=title,
        message=message,
        notification_type="event_registration",
    )


def create_event_update_notification(
    user_id: int,
    event_id: int,
    event_name: str,
    message: str,
) -> int:
    """
    Notify a user about an event update.
    """
    event_name = clean_text(event_name)
    message = clean_text(message)

    title = f"Event Update: {event_name}"

    return create_notification(
        user_id=user_id,
        event_id=event_id,
        title=title,
        message=message,
        notification_type="event_update",
    )


def get_event_verification_notifications(
    user_id: int,
    limit: int = 100,
):
    """
    Return only successful event-verification notifications
    for a specific user.
    """
    if not user_id:
        return []

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100

    limit = max(1, min(limit, 500))

    return fetch_all(
        """
        SELECT
            n.id,
            n.user_id,
            n.event_id,
            n.student_id,
            n.title,
            n.message,
            n.notification_type,
            n.is_read,
            n.created_at,
            e.event_name,
            e.event_category,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            s.name AS student_name,
            s.email AS student_email,
            s.roll_no AS student_roll_no
        FROM notifications n
        LEFT JOIN events e
            ON e.id = n.event_id
        LEFT JOIN users s
            ON s.id = n.student_id
        WHERE n.user_id = ?
          AND n.notification_type = 'event_verification'
        ORDER BY n.created_at DESC, n.id DESC
        LIMIT ?
        """,
        (
            user_id,
            limit,
        ),
    )


def get_recent_notifications(
    user_id: int,
    limit: int = 5,
):
    """
    Return a small set of recent notifications for dashboard cards.
    """
    return get_user_notifications(
        user_id=user_id,
        unread_only=False,
        limit=limit,
    )


def get_notification_summary(
    user_id: int,
) -> dict[str, Any]:
    """
    Return dashboard-friendly notification statistics.
    """
    total = get_notification_count(user_id)
    unread = get_unread_notification_count(user_id)

    return {
        "total": total,
        "unread": unread,
        "read": max(0, total - unread),
    }