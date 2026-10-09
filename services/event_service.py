"""
EventSync Event Service

Handles:
- Event listing and details
- Event creation and updates
- Event registration
- Student coordinator assignment
- Teacher/student coordinator access
- Event lecture mapping
- Event status management
"""

from datetime import datetime, timezone
from typing import Any

from database.db import execute_write, fetch_all, fetch_one
from utils.helpers import clean_text, parse_datetime


EVENT_CATEGORIES = {
    "Technical",
    "Sports",
    "Cultural",
    "Placement & Career",
    "Competitions",
    "Research & Innovation",
    "College Fest",
    "Other",
}

EVENT_TYPES = {
    "Hackathon",
    "Workshop",
    "Seminar",
    "Competition",
    "Sports Meet",
    "Annual Fest",
    "Career Guidance",
    "Conference",
    "Cultural Program",
    "Technical Event",
    "Other",
}

EVENT_STATUSES = {
    "draft",
    "upcoming",
    "live",
    "completed",
    "cancelled",
}

PARTICIPATION_ROLES = {
    "participant",
    "student_coordinator",
}

COORDINATOR_ROLES = {
    "main_coordinator",
    "student_coordinator",
}


def get_all_events(include_cancelled: bool = True):
    """
    Return events ordered by date and start time.
    """
    if include_cancelled:
        return fetch_all(
            """
            SELECT
                e.id,
                e.event_name,
                e.event_category,
                e.event_type,
                e.event_date,
                e.start_time,
                e.end_time,
                e.venue,
                e.description,
                e.created_by,
                e.status,
                e.created_at,
                creator.name AS creator_name
            FROM events e
            LEFT JOIN users creator
                ON creator.id = e.created_by
            ORDER BY
                e.event_date ASC,
                e.start_time ASC,
                e.id ASC
            """
        )

    return fetch_all(
        """
        SELECT
            e.id,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            e.description,
            e.created_by,
            e.status,
            e.created_at,
            creator.name AS creator_name
        FROM events e
        LEFT JOIN users creator
            ON creator.id = e.created_by
        WHERE e.status != 'cancelled'
        ORDER BY
            e.event_date ASC,
            e.start_time ASC,
            e.id ASC
        """
    )


def get_upcoming_events():
    """
    Return events that are currently intended for student discovery.
    """
    return fetch_all(
        """
        SELECT
            e.id,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            e.description,
            e.created_by,
            e.status,
            e.created_at,
            creator.name AS creator_name
        FROM events e
        LEFT JOIN users creator
            ON creator.id = e.created_by
        WHERE e.status IN ('upcoming', 'live')
        ORDER BY
            e.event_date ASC,
            e.start_time ASC,
            e.id ASC
        """
    )


def get_live_events():
    """
    Return events currently marked as live.
    """
    return fetch_all(
        """
        SELECT
            e.id,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            e.description,
            e.created_by,
            e.status,
            e.created_at
        FROM events e
        WHERE e.status = 'live'
        ORDER BY
            e.event_date ASC,
            e.start_time ASC
        """
    )


def get_event_by_id(event_id: int):
    """
    Return one event with creator information.
    """
    return fetch_one(
        """
        SELECT
            e.id,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            e.description,
            e.created_by,
            e.status,
            e.created_at,
            creator.name AS creator_name,
            creator.email AS creator_email
        FROM events e
        LEFT JOIN users creator
            ON creator.id = e.created_by
        WHERE e.id = ?
        LIMIT 1
        """,
        (event_id,),
    )


def validate_event_data(
    event_name: str,
    event_category: str,
    event_type: str,
    event_date: str,
    start_time: str,
    end_time: str,
    venue: str,
    status: str = "upcoming",
) -> dict[str, str]:
    """
    Validate and normalize event form data.
    """
    event_name = clean_text(event_name)
    event_category = clean_text(event_category)
    event_type = clean_text(event_type)
    event_date = clean_text(event_date)
    start_time = clean_text(start_time)
    end_time = clean_text(end_time)
    venue = clean_text(venue)
    status = clean_text(status).lower()

    if not event_name:
        raise ValueError("Event name is required.")

    if len(event_name) < 3:
        raise ValueError("Event name must contain at least 3 characters.")

    if event_category not in EVENT_CATEGORIES:
        raise ValueError("Please select a valid event category.")

    if event_type not in EVENT_TYPES:
        raise ValueError("Please select a valid event type.")

    if not event_date:
        raise ValueError("Event date is required.")

    if not start_time:
        raise ValueError("Event start time is required.")

    if not end_time:
        raise ValueError("Event end time is required.")

    if not venue:
        raise ValueError("Event venue is required.")

    if status not in EVENT_STATUSES:
        raise ValueError("Please select a valid event status.")

    try:
        datetime.strptime(event_date, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("Invalid event date.") from error

    try:
        start = datetime.strptime(start_time, "%H:%M")
        end = datetime.strptime(end_time, "%H:%M")
    except ValueError as error:
        raise ValueError("Invalid event time.") from error

    if end <= start:
        raise ValueError("Event end time must be after start time.")

    return {
        "event_name": event_name,
        "event_category": event_category,
        "event_type": event_type,
        "event_date": event_date,
        "start_time": start_time,
        "end_time": end_time,
        "venue": venue,
        "status": status,
    }


def create_event(
    event_name: str,
    event_category: str,
    event_type: str,
    event_date: str,
    start_time: str,
    end_time: str,
    venue: str,
    description: str,
    created_by: int,
    status: str = "upcoming",
) -> int:
    """
    Create a new event.
    """
    data = validate_event_data(
        event_name=event_name,
        event_category=event_category,
        event_type=event_type,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        venue=venue,
        status=status,
    )

    if not created_by:
        raise ValueError("Event creator is required.")

    creator = fetch_one(
        """
        SELECT id
        FROM users
        WHERE id = ?
          AND is_active = 1
        LIMIT 1
        """,
        (created_by,),
    )

    if creator is None:
        raise ValueError("Event creator does not exist.")

    return execute_write(
        """
        INSERT INTO events (
            event_name,
            event_category,
            event_type,
            event_date,
            start_time,
            end_time,
            venue,
            description,
            created_by,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["event_name"],
            data["event_category"],
            data["event_type"],
            data["event_date"],
            data["start_time"],
            data["end_time"],
            data["venue"],
            clean_text(description),
            created_by,
            data["status"],
        ),
    )


def update_event(
    event_id: int,
    event_name: str,
    event_category: str,
    event_type: str,
    event_date: str,
    start_time: str,
    end_time: str,
    venue: str,
    description: str,
    status: str,
) -> bool:
    """
    Update an existing event.
    """
    existing_event = get_event_by_id(event_id)

    if existing_event is None:
        raise ValueError("Event not found.")

    data = validate_event_data(
        event_name=event_name,
        event_category=event_category,
        event_type=event_type,
        event_date=event_date,
        start_time=start_time,
        end_time=end_time,
        venue=venue,
        status=status,
    )

    execute_write(
        """
        UPDATE events
        SET
            event_name = ?,
            event_category = ?,
            event_type = ?,
            event_date = ?,
            start_time = ?,
            end_time = ?,
            venue = ?,
            description = ?,
            status = ?
        WHERE id = ?
        """,
        (
            data["event_name"],
            data["event_category"],
            data["event_type"],
            data["event_date"],
            data["start_time"],
            data["end_time"],
            data["venue"],
            clean_text(description),
            data["status"],
            event_id,
        ),
    )

    return True


def update_event_status(event_id: int, status: str) -> bool:
    """
    Change only an event's status.
    """
    status = clean_text(status).lower()

    if status not in EVENT_STATUSES:
        raise ValueError("Invalid event status.")

    event = get_event_by_id(event_id)

    if event is None:
        raise ValueError("Event not found.")

    execute_write(
        """
        UPDATE events
        SET status = ?
        WHERE id = ?
        """,
        (status, event_id),
    )

    return True


def delete_event(event_id: int) -> bool:
    """
    Soft-delete an event by marking it cancelled.

    Related registrations and verification history are preserved.
    """
    event = get_event_by_id(event_id)

    if event is None:
        raise ValueError("Event not found.")

    execute_write(
        """
        UPDATE events
        SET status = 'cancelled'
        WHERE id = ?
        """,
        (event_id,),
    )

    return True


def get_event_coordinators(event_id: int):
    """
    Return all coordinators assigned to an event.
    """
    return fetch_all(
        """
        SELECT
            ec.id,
            ec.event_id,
            ec.user_id,
            ec.coordinator_role,
            ec.assigned_at,
            u.name AS user_name,
            u.email AS user_email,
            u.role AS user_role,
            u.roll_no,
            d.code AS department_code
        FROM event_coordinators ec
        JOIN users u
            ON u.id = ec.user_id
        LEFT JOIN departments d
            ON d.id = u.department_id
        WHERE ec.event_id = ?
        ORDER BY
            CASE
                WHEN ec.coordinator_role = 'main_coordinator' THEN 1
                ELSE 2
            END,
            u.name ASC
        """,
        (event_id,),
    )


def get_main_coordinators(event_id: int):
    """
    Return teacher/main coordinators for an event.
    """
    return fetch_all(
        """
        SELECT
            ec.id,
            ec.event_id,
            ec.user_id,
            ec.coordinator_role,
            u.name,
            u.email,
            u.role
        FROM event_coordinators ec
        JOIN users u
            ON u.id = ec.user_id
        WHERE ec.event_id = ?
          AND ec.coordinator_role = 'main_coordinator'
          AND u.is_active = 1
        ORDER BY u.name ASC
        """,
        (event_id,),
    )


def get_student_coordinators(event_id: int):
    """
    Return student coordinators for an event.
    """
    return fetch_all(
        """
        SELECT
            ec.id,
            ec.event_id,
            ec.user_id,
            ec.coordinator_role,
            ec.assigned_at,
            u.name,
            u.email,
            u.roll_no,
            u.department_id,
            u.semester,
            u.section
        FROM event_coordinators ec
        JOIN users u
            ON u.id = ec.user_id
        WHERE ec.event_id = ?
          AND ec.coordinator_role = 'student_coordinator'
          AND u.is_active = 1
        ORDER BY u.name ASC
        """,
        (event_id,),
    )


def is_event_coordinator(user_id: int, event_id: int) -> bool:
    """
    Check whether a user is assigned to an event as coordinator.
    """
    row = fetch_one(
        """
        SELECT id
        FROM event_coordinators
        WHERE event_id = ?
          AND user_id = ?
        LIMIT 1
        """,
        (event_id, user_id),
    )

    return row is not None


def is_main_coordinator(user_id: int, event_id: int) -> bool:
    """
    Check whether a user is the main/teacher coordinator.
    """
    row = fetch_one(
        """
        SELECT id
        FROM event_coordinators
        WHERE event_id = ?
          AND user_id = ?
          AND coordinator_role = 'main_coordinator'
        LIMIT 1
        """,
        (event_id, user_id),
    )

    return row is not None


def is_student_coordinator(user_id: int, event_id: int) -> bool:
    """
    Check whether a user is a student coordinator.
    """
    row = fetch_one(
        """
        SELECT id
        FROM event_coordinators
        WHERE event_id = ?
          AND user_id = ?
          AND coordinator_role = 'student_coordinator'
        LIMIT 1
        """,
        (event_id, user_id),
    )

    return row is not None


def assign_event_coordinator(
    event_id: int,
    user_id: int,
    coordinator_role: str,
) -> int:
    """
    Assign a teacher or student as an event coordinator.
    """
    coordinator_role = clean_text(coordinator_role).lower()

    if coordinator_role not in COORDINATOR_ROLES:
        raise ValueError("Invalid coordinator role.")

    event = get_event_by_id(event_id)

    if event is None:
        raise ValueError("Event not found.")

    user = fetch_one(
        """
        SELECT
            id,
            role,
            is_active
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (user_id,),
    )

    if user is None or not user["is_active"]:
        raise ValueError("User not found or inactive.")

    if coordinator_role == "main_coordinator":
        if user["role"] != "teacher":
            raise ValueError(
                "Only teachers can be main event coordinators."
            )

    if coordinator_role == "student_coordinator":
        if user["role"] != "student":
            raise ValueError(
                "Only students can be student coordinators."
            )

    existing = fetch_one(
        """
        SELECT id
        FROM event_coordinators
        WHERE event_id = ?
          AND user_id = ?
        LIMIT 1
        """,
        (event_id, user_id),
    )

    if existing is not None:
        execute_write(
            """
            UPDATE event_coordinators
            SET coordinator_role = ?
            WHERE id = ?
            """,
            (coordinator_role, existing["id"]),
        )
        return existing["id"]

    return execute_write(
        """
        INSERT INTO event_coordinators (
            event_id,
            user_id,
            coordinator_role
        )
        VALUES (?, ?, ?)
        """,
        (
            event_id,
            user_id,
            coordinator_role,
        ),
    )


def remove_event_coordinator(event_id: int, user_id: int) -> bool:
    """
    Remove a user's coordinator assignment.
    """
    execute_write(
        """
        DELETE FROM event_coordinators
        WHERE event_id = ?
          AND user_id = ?
        """,
        (event_id, user_id),
    )

    return True


def get_event_registrations(event_id: int):
    """
    Return all students registered for an event.
    """
    return fetch_all(
        """
        SELECT
            er.id,
            er.event_id,
            er.student_id,
            er.participation_role,
            er.status,
            er.registered_at,
            u.name AS student_name,
            u.email AS student_email,
            u.roll_no,
            u.department_id,
            u.semester,
            u.section,
            d.code AS department_code,
            d.name AS department_name
        FROM event_registrations er
        JOIN users u
            ON u.id = er.student_id
        LEFT JOIN departments d
            ON d.id = u.department_id
        WHERE er.event_id = ?
        ORDER BY
            er.registered_at DESC,
            u.name ASC
        """,
        (event_id,),
    )


def get_student_event_registrations(student_id: int):
    """
    Return all events registered by a student.
    """
    return fetch_all(
        """
        SELECT
            er.id,
            er.event_id,
            er.student_id,
            er.participation_role,
            er.status AS registration_status,
            er.registered_at,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            e.description,
            e.status AS event_status
        FROM event_registrations er
        JOIN events e
            ON e.id = er.event_id
        WHERE er.student_id = ?
        ORDER BY
            e.event_date DESC,
            e.start_time DESC
        """,
        (student_id,),
    )

def get_event_registration(event_id: int, student_id: int):
    """Return one student's registration for an event."""
    return fetch_one(
        """
        SELECT *
        FROM event_registrations
        WHERE event_id = ? AND student_id = ?
        """,
        (event_id, student_id),
    )
def is_student_registered(student_id: int, event_id: int) -> bool:
    """
    Check whether a student has an active registration for an event.
    """
    row = fetch_one(
        """
        SELECT id
        FROM event_registrations
        WHERE event_id = ?
          AND student_id = ?
          AND status != 'cancelled'
        LIMIT 1
        """,
        (event_id, student_id),
    )

    return row is not None


def get_student_registration(student_id: int, event_id: int):
    """
    Return one student's registration for an event.
    """
    return fetch_one(
        """
        SELECT
            er.id,
            er.event_id,
            er.student_id,
            er.participation_role,
            er.status,
            er.registered_at
        FROM event_registrations er
        WHERE er.event_id = ?
          AND er.student_id = ?
        LIMIT 1
        """,
        (event_id, student_id),
    )


def register_student_for_event(
    event_id: int,
    student_id: int,
    participation_role: str = "participant",
) -> dict[str, Any]:
    """
    Register a student for an event.

    If the student chooses student_coordinator, the same
    operation also creates an event_coordinators assignment.
    """
    participation_role = clean_text(participation_role).lower()

    if participation_role not in PARTICIPATION_ROLES:
        raise ValueError("Invalid participation role.")

    event = get_event_by_id(event_id)

    if event is None:
        raise ValueError("Event not found.")

    if event["status"] in {"cancelled", "completed"}:
        raise ValueError(
            "Registration is closed for this event."
        )

    student = fetch_one(
        """
        SELECT
            id,
            role,
            is_active
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (student_id,),
    )

    if student is None:
        raise ValueError("Student account not found.")

    if student["role"] != "student":
        raise ValueError("Only students can register for events.")

    if not student["is_active"]:
        raise ValueError("This student account is inactive.")

    existing = get_student_registration(
        student_id=student_id,
        event_id=event_id,
    )

    if existing is not None:
        if existing["status"] == "cancelled":
            execute_write(
                """
                UPDATE event_registrations
                SET
                    participation_role = ?,
                    status = 'registered',
                    registered_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    participation_role,
                    existing["id"],
                ),
            )

            registration_id = existing["id"]
        else:
            if (
                existing["participation_role"]
                != participation_role
            ):
                execute_write(
                    """
                    UPDATE event_registrations
                    SET participation_role = ?
                    WHERE id = ?
                    """,
                    (
                        participation_role,
                        existing["id"],
                    ),
                )

            registration_id = existing["id"]
    else:
        registration_id = execute_write(
            """
            INSERT INTO event_registrations (
                event_id,
                student_id,
                participation_role,
                status
            )
            VALUES (?, ?, ?, 'registered')
            """,
            (
                event_id,
                student_id,
                participation_role,
            ),
        )

    coordinator_id = None

    if participation_role == "student_coordinator":
        coordinator_id = assign_event_coordinator(
            event_id=event_id,
            user_id=student_id,
            coordinator_role="student_coordinator",
        )

    return {
        "success": True,
        "registration_id": registration_id,
        "coordinator_id": coordinator_id,
        "participation_role": participation_role,
        "message": (
            "Registered as student coordinator."
            if participation_role == "student_coordinator"
            else "Event registration successful."
        ),
    }


def cancel_event_registration(
    event_id: int,
    student_id: int,
) -> bool:
    """
    Cancel a student's event registration.

    Student coordinator assignment is removed as well.
    """
    registration = get_student_registration(
        student_id=student_id,
        event_id=event_id,
    )

    if registration is None:
        raise ValueError("Event registration not found.")

    execute_write(
        """
        UPDATE event_registrations
        SET status = 'cancelled'
        WHERE id = ?
        """,
        (registration["id"],),
    )

    execute_write(
        """
        DELETE FROM event_coordinators
        WHERE event_id = ?
          AND user_id = ?
          AND coordinator_role = 'student_coordinator'
        """,
        (event_id, student_id),
    )

    return True


def mark_registration_attended(
    event_id: int,
    student_id: int,
) -> bool:
    """
    Mark a registered student as attended.

    This is separate from academic lecture attendance.
    """
    registration = get_student_registration(
        student_id=student_id,
        event_id=event_id,
    )

    if registration is None:
        raise ValueError("Event registration not found.")

    if registration["status"] == "cancelled":
        raise ValueError("Cancelled registration cannot be attended.")

    execute_write(
        """
        UPDATE event_registrations
        SET status = 'attended'
        WHERE id = ?
        """,
        (registration["id"],),
    )

    return True


def get_event_lecture_mappings(event_id: int):
    """
    Return lectures mapped to an event.
    """
    return fetch_all(
        """
        SELECT
            elm.id,
            elm.event_id,
            elm.lecture_id,
            elm.mapped_at,
            l.lecture_date,
            l.start_time,
            l.end_time,
            l.room,
            l.semester,
            l.section,
            s.subject_code,
            s.subject_name,
            u.name AS teacher_name,
            d.code AS department_code
        FROM event_lecture_mapping elm
        JOIN lectures l
            ON l.id = elm.lecture_id
        JOIN subjects s
            ON s.id = l.subject_id
        JOIN users u
            ON u.id = l.teacher_id
        LEFT JOIN departments d
            ON d.id = l.department_id
        WHERE elm.event_id = ?
        ORDER BY
            l.lecture_date ASC,
            l.start_time ASC
        """,
        (event_id,),
    )


def get_lecture_mapped_events(lecture_id: int):
    """
    Return events mapped to a lecture.
    """
    return fetch_all(
        """
        SELECT
            elm.id,
            elm.event_id,
            elm.lecture_id,
            elm.mapped_at,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            e.status
        FROM event_lecture_mapping elm
        JOIN events e
            ON e.id = elm.event_id
        WHERE elm.lecture_id = ?
        ORDER BY
            e.event_date ASC,
            e.start_time ASC
        """,
        (lecture_id,),
    )


def map_event_to_lecture(
    event_id: int,
    lecture_id: int,
) -> int:
    """
    Map an academic lecture to an event.
    """
    event = get_event_by_id(event_id)

    if event is None:
        raise ValueError("Event not found.")

    lecture = fetch_one(
        """
        SELECT
            id,
            teacher_id,
            subject_id,
            lecture_date,
            start_time,
            end_time
        FROM lectures
        WHERE id = ?
          AND is_active = 1
        LIMIT 1
        """,
        (lecture_id,),
    )

    if lecture is None:
        raise ValueError("Lecture not found.")

    existing = fetch_one(
        """
        SELECT id
        FROM event_lecture_mapping
        WHERE event_id = ?
          AND lecture_id = ?
        LIMIT 1
        """,
        (event_id, lecture_id),
    )

    if existing is not None:
        return existing["id"]

    return execute_write(
        """
        INSERT INTO event_lecture_mapping (
            event_id,
            lecture_id
        )
        VALUES (?, ?)
        """,
        (
            event_id,
            lecture_id,
        ),
    )


def unmap_event_from_lecture(
    event_id: int,
    lecture_id: int,
) -> bool:
    """
    Remove an event-to-lecture mapping.
    """
    execute_write(
        """
        DELETE FROM event_lecture_mapping
        WHERE event_id = ?
          AND lecture_id = ?
        """,
        (event_id, lecture_id),
    )

    return True


def get_teacher_events(teacher_id: int):
    """
    Return events where a teacher is assigned as main coordinator.
    """
    return fetch_all(
        """
        SELECT
            e.id,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            e.description,
            e.status,
            ec.coordinator_role
        FROM event_coordinators ec
        JOIN events e
            ON e.id = ec.event_id
        WHERE ec.user_id = ?
          AND ec.coordinator_role = 'main_coordinator'
        ORDER BY
            e.event_date DESC,
            e.start_time DESC
        """,
        (teacher_id,),
    )
def get_teacher_coordinator_events(teacher_id: int):
    """
    Return events where a teacher is assigned as coordinator.
    """
    return fetch_all(
        """
        SELECT
            e.id,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            e.description,
            e.status,
            ec.coordinator_role
        FROM event_coordinators ec
        JOIN events e
            ON e.id = ec.event_id
        WHERE ec.user_id = ?
          AND ec.coordinator_role = 'main_coordinator'
        ORDER BY
            e.event_date DESC,
            e.start_time DESC
        """,
        (teacher_id,),
    )


def get_student_coordinator_events(student_id: int):
    """
    Return events where a student is assigned as coordinator.
    """
    return fetch_all(
        """
        SELECT
            e.id,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue,
            e.description,
            e.status,
            ec.coordinator_role
        FROM event_coordinators ec
        JOIN events e
            ON e.id = ec.event_id
        WHERE ec.user_id = ?
          AND ec.coordinator_role = 'student_coordinator'
        ORDER BY
            e.event_date DESC,
            e.start_time DESC
        """,
        (student_id,),
    )


def get_event_statistics(event_id: int) -> dict[str, int]:
    """
    Return registration, attendance, and verification counts.
    """
    event = get_event_by_id(event_id)

    if event is None:
        raise ValueError("Event not found.")

    registrations = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM event_registrations
        WHERE event_id = ?
          AND status != 'cancelled'
        """,
        (event_id,),
    )

    attended = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM event_registrations
        WHERE event_id = ?
          AND status = 'attended'
        """,
        (event_id,),
    )

    verified = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM event_verifications
        WHERE event_id = ?
          AND verification_status = 'verified'
        """,
        (event_id,),
    )

    coordinators = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM event_coordinators
        WHERE event_id = ?
        """,
        (event_id,),
    )

    return {
        "registrations": int(registrations["total"] or 0),
        "attended": int(attended["total"] or 0),
        "verified": int(verified["total"] or 0),
        "coordinators": int(coordinators["total"] or 0),
    }


def get_event_categories() -> list[str]:
    """
    Return event categories in stable display order.
    """
    return [
        "Technical",
        "Sports",
        "Cultural",
        "Placement & Career",
        "Competitions",
        "Research & Innovation",
        "College Fest",
        "Other",
    ]


def get_event_types() -> list[str]:
    """
    Return event types in stable display order.
    """
    return [
        "Hackathon",
        "Workshop",
        "Seminar",
        "Competition",
        "Sports Meet",
        "Annual Fest",
        "Career Guidance",
        "Conference",
        "Cultural Program",
        "Technical Event",
        "Other",
    ]


def get_event_statuses() -> list[str]:
    """
    Return event statuses in stable display order.
    """
    return [
        "draft",
        "upcoming",
        "live",
        "completed",
        "cancelled",
    ]


def get_participation_roles() -> list[dict[str, str]]:
    """
    Return student participation choices for UI forms.
    """
    return [
        {
            "value": "participant",
            "label": "Participant",
            "description": "Attend the event as a participant.",
        },
        {
            "value": "student_coordinator",
            "label": "Student Coordinator",
            "description": (
                "Help coordinate the event and manage "
                "event activities."
            ),
        },
    ]


def get_event_dashboard_data(event_id: int) -> dict[str, Any] | None:
    """
    Return a complete event summary for coordinator/admin pages.
    """
    event = get_event_by_id(event_id)

    if event is None:
        return None

    return {
        "event": event,
        "coordinators": get_event_coordinators(event_id),
        "registrations": get_event_registrations(event_id),
        "lecture_mappings": get_event_lecture_mappings(event_id),
        "statistics": get_event_statistics(event_id),
    }