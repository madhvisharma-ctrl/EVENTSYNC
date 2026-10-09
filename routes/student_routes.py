from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database.db import fetch_all, fetch_one

from services import auth_service
from services import event_service

from utils.decorators import student_required


# ============================================================
# BLUEPRINT
# ============================================================

student_bp = Blueprint(
    "student",
    __name__,
    url_prefix="/student",
)


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@student_bp.route("/")
@student_bp.route("/dashboard")
@student_required
def dashboard():
    """
    Main student dashboard.

    Shows:
        - Registered events
        - Verified events
        - Upcoming/live events
        - Notifications
        - Coordinator assignments
        - Academic attendance summary
    """
    student_id = session["user_id"]

    student = auth_service.get_user_by_id(student_id)

    if not student:
        session.clear()
        flash(
            "Student account could not be found. Please log in again.",
            "danger",
        )
        return redirect(url_for("auth.login"))

    registered_events = (
        event_service.get_student_registered_events(
            student_id
        )
    )

    coordinator_events = (
        event_service.get_student_coordinator_events(
            student_id
        )
    )

    upcoming_events = event_service.get_upcoming_events()

    live_events = event_service.get_live_events()

    # --------------------------------------------------------
    # Event verification history
    # --------------------------------------------------------

    verified_events = fetch_all(
        """
        SELECT
            ev.id,
            ev.event_id,
            ev.student_id,
            ev.qr_verified,
            ev.face_verified,
            ev.verification_status,
            ev.confidence,
            ev.verified_at,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue
        FROM event_verifications ev
        JOIN events e
            ON e.id = ev.event_id
        WHERE ev.student_id = ?
          AND ev.verification_status = 'verified'
        ORDER BY ev.verified_at DESC
        """,
        (student_id,),
    )

    # --------------------------------------------------------
    # Notifications
    # --------------------------------------------------------

    notifications = fetch_all(
        """
        SELECT
            n.id,
            n.event_id,
            n.student_id,
            n.title,
            n.message,
            n.notification_type,
            n.is_read,
            n.created_at,
            e.event_name
        FROM notifications n
        LEFT JOIN events e
            ON e.id = n.event_id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
        LIMIT 10
        """,
        (student_id,),
    )

    unread_notification_count = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM notifications
        WHERE user_id = ?
          AND is_read = 0
        """,
        (student_id,),
    )

    unread_notification_count = int(
        unread_notification_count["count"]
        if unread_notification_count
        else 0
    )

    # --------------------------------------------------------
    # Academic attendance summary
    # --------------------------------------------------------

    attendance_summary = fetch_one(
        """
        SELECT
            COUNT(*) AS total_classes,
            SUM(
                CASE
                    WHEN attendance_status = 'present'
                    THEN 1 ELSE 0
                END
            ) AS present_count,
            SUM(
                CASE
                    WHEN attendance_status = 'absent'
                    THEN 1 ELSE 0
                END
            ) AS absent_count,
            SUM(
                CASE
                    WHEN attendance_status = 'late'
                    THEN 1 ELSE 0
                END
            ) AS late_count
        FROM attendance
        WHERE student_id = ?
        """,
        (student_id,),
    )

    total_classes = int(
        attendance_summary["total_classes"] or 0
    )

    present_count = int(
        attendance_summary["present_count"] or 0
    )

    absent_count = int(
        attendance_summary["absent_count"] or 0
    )

    late_count = int(
        attendance_summary["late_count"] or 0
    )

    attended_count = (
        present_count + late_count
    )

    attendance_percentage = (
        round(
            attended_count / total_classes * 100,
            2,
        )
        if total_classes
        else 0
    )

    attendance_summary = {
        "total_classes": total_classes,
        "present_count": present_count,
        "absent_count": absent_count,
        "late_count": late_count,
        "attended_count": attended_count,
        "attendance_percentage": attendance_percentage,
    }

    return render_template(
        "student/dashboard.html",
        student=student,
        registered_events=registered_events,
        verified_events=verified_events,
        upcoming_events=upcoming_events,
        live_events=live_events,
        coordinator_events=coordinator_events,
        notifications=notifications,
        unread_notification_count=unread_notification_count,
        attendance_summary=attendance_summary,
    )


# ============================================================
# ALL EVENTS
# ============================================================

@student_bp.route("/events")
@student_required
def events():
    """
    Show all available events to the student.
    """
    student_id = session["user_id"]

    events = event_service.get_all_events()

    registered_event_ids = set()

    for event in events:
        registration = event_service.get_event_registration(
            event_id=event["id"],
            student_id=student_id,
        )

        if registration:
            registered_event_ids.add(
                event["id"]
            )

    return render_template(
        "student/events.html",
        events=events,
        registered_event_ids=registered_event_ids,
    )


# ============================================================
# EVENT DETAILS
# ============================================================

@student_bp.route("/events/<int:event_id>")
@student_required
def event_details(event_id):
    """
    Show details of one event.
    """
    student_id = session["user_id"]

    event = event_service.get_event_by_id(
        event_id
    )

    if not event:
        flash(
            "Event not found.",
            "danger",
        )
        return redirect(
            url_for("student.events")
        )

    registration = (
        event_service.get_event_registration(
            event_id=event_id,
            student_id=student_id,
        )
    )

    coordinators = (
        event_service.get_event_coordinators(
            event_id
        )
    )

    return render_template(
        "student/event_details.html",
        event=event,
        registration=registration,
        coordinators=coordinators,
    )


# ============================================================
# REGISTER FOR EVENT
# ============================================================

@student_bp.route(
    "/events/<int:event_id>/register",
    methods=["POST"],
)
@student_required
def register_event(event_id):
    """
    Register the logged-in student for an event.

    Participation role:
        participant
        student_coordinator

    Selecting student_coordinator also creates the corresponding
    event coordinator assignment through the event service.
    """
    student_id = session["user_id"]

    participation_role = (
        request.form.get(
            "participation_role",
            "participant",
        )
        .strip()
        .lower()
    )

    if participation_role not in {
        "participant",
        "student_coordinator",
    }:
        participation_role = "participant"

    event = event_service.get_event_by_id(
        event_id
    )

    if not event:
        flash(
            "Event not found.",
            "danger",
        )
        return redirect(
            url_for("student.events")
        )

    result = event_service.register_student_for_event(
        event_id=event_id,
        student_id=student_id,
        participation_role=participation_role,
    )

    if result.get("success"):
        flash(
            result.get(
                "message",
                "Successfully registered for the event.",
            ),
            "success",
        )
    else:
        flash(
            result.get(
                "message",
                "Unable to register for this event.",
            ),
            "danger",
        )

    return redirect(
        url_for(
            "student.event_details",
            event_id=event_id,
        )
    )


# ============================================================
# CANCEL EVENT REGISTRATION
# ============================================================

@student_bp.route(
    "/events/<int:event_id>/cancel",
    methods=["POST"],
)
@student_required
def cancel_event(event_id):
    """
    Cancel the student's event registration.
    """
    student_id = session["user_id"]

    result = event_service.cancel_event_registration(
        event_id=event_id,
        student_id=student_id,
    )

    if result.get("success"):
        flash(
            result.get(
                "message",
                "Event registration cancelled.",
            ),
            "success",
        )
    else:
        flash(
            result.get(
                "message",
                "Unable to cancel registration.",
            ),
            "danger",
        )

    return redirect(
        url_for(
            "student.event_details",
            event_id=event_id,
        )
    )


# ============================================================
# MY EVENTS
# ============================================================

@student_bp.route("/my-events")
@student_required
def my_events():
    """
    Show the student's registered events.
    """
    student_id = session["user_id"]

    registered_events = (
        event_service.get_student_registered_events(
            student_id
        )
    )

    verified_events = fetch_all(
        """
        SELECT
            ev.id AS verification_id,
            ev.event_id,
            ev.verification_status,
            ev.qr_verified,
            ev.face_verified,
            ev.confidence,
            ev.verified_at,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue
        FROM event_verifications ev
        JOIN events e
            ON e.id = ev.event_id
        WHERE ev.student_id = ?
          AND ev.verification_status = 'verified'
        ORDER BY ev.verified_at DESC
        """,
        (student_id,),
    )

    return render_template(
        "student/my_events.html",
        registered_events=registered_events,
        verified_events=verified_events,
    )


# ============================================================
# EVENT VERIFICATION PAGE
# ============================================================

@student_bp.route(
    "/events/<int:event_id>/verify"
)
@student_required
def verify_event(event_id):
    """
    Open the live QR + face verification screen.

    The actual verification is handled by
    verification_routes.py.
    """
    student_id = session["user_id"]

    event = event_service.get_event_by_id(
        event_id
    )

    if not event:
        flash(
            "Event not found.",
            "danger",
        )
        return redirect(
            url_for("student.events")
        )

    registration = (
        event_service.get_event_registration(
            event_id=event_id,
            student_id=student_id,
        )
    )

    if not registration:
        flash(
            "You must register for this event before verification.",
            "warning",
        )
        return redirect(
            url_for(
                "student.event_details",
                event_id=event_id,
            )
        )

    return render_template(
        "student/verify_event.html",
        event=event,
        registration=registration,
    )


# ============================================================
# VERIFICATION RESULT
# ============================================================

@student_bp.route(
    "/events/<int:event_id>/verification-result"
)
@student_required
def verification_result(event_id):
    """
    Show the latest verification result for the student.
    """
    student_id = session["user_id"]

    event = event_service.get_event_by_id(
        event_id
    )

    if not event:
        flash(
            "Event not found.",
            "danger",
        )
        return redirect(
            url_for("student.events")
        )

    verification = fetch_one(
        """
        SELECT
            ev.id,
            ev.event_id,
            ev.student_id,
            ev.qr_verified,
            ev.face_verified,
            ev.verification_status,
            ev.confidence,
            ev.verified_at,
            ev.created_at,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue
        FROM event_verifications ev
        JOIN events e
            ON e.id = ev.event_id
        WHERE ev.event_id = ?
          AND ev.student_id = ?
        ORDER BY ev.created_at DESC
        LIMIT 1
        """,
        (
            event_id,
            student_id,
        ),
    )

    return render_template(
        "student/verification_result.html",
        event=event,
        verification=verification,
    )


# ============================================================
# STUDENT COORDINATOR WORKSPACE
# ============================================================

@student_bp.route("/coordinator")
@student_required
def coordinator():
    """
    Student coordinator workspace.

    A normal participant can access the route, but will simply
    see events for which they have the student coordinator role.
    """
    student_id = session["user_id"]

    coordinator_events = (
        event_service.get_student_coordinator_events(
            student_id
        )
    )

    event_data = []

    for event in coordinator_events:
        statistics = (
            event_service.get_event_statistics(
                event["id"]
            )
        )

        event_data.append(
            {
                "event": event,
                "statistics": statistics,
            }
        )

    return render_template(
        "student/coordinator.html",
        coordinator_events=coordinator_events,
        event_data=event_data,
    )


# ============================================================
# STUDENT PROFILE
# ============================================================



# ============================================================
# STUDENT — VERIFICATION HISTORY
# ============================================================

@student_bp.route("/verification-history")
@student_required
def verification_history():
    """Show the logged-in student's event verification history."""
    student_id = session["user_id"]
    verifications = fetch_all(
        """
        SELECT
            ev.id,
            ev.event_id,
            ev.qr_verified,
            ev.face_verified,
            ev.verification_status,
            ev.confidence,
            ev.verified_at,
            e.event_name,
            e.event_date,
            e.start_time,
            e.end_time,
            e.venue
        FROM event_verifications ev
        JOIN events e ON e.id = ev.event_id
        WHERE ev.student_id = ?
        ORDER BY ev.verified_at DESC
        """,
        (student_id,),
    )
    return render_template(
        "student/verification_history.html",
        verifications=verifications,
    )

@student_bp.route("/profile")
@student_required
def profile():
    """
    Show the student's profile.
    """
    student_id = session["user_id"]

    student = auth_service.get_user_by_id(
        student_id
    )

    if not student:
        session.clear()
        flash(
            "Student account could not be found.",
            "danger",
        )
        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "student/dashboard.html",
        student=student,
        profile_view=True,
    )


# ============================================================
# MARK EVENT ATTENDED
# ============================================================

@student_bp.route(
    "/events/<int:event_id>/mark-attended",
    methods=["POST"],
)
@student_required
def mark_event_attended(event_id):
    """
    Manual event attendance action.

    This is separate from academic lecture attendance.
    """
    student_id = session["user_id"]

    registration = (
        event_service.get_event_registration(
            event_id=event_id,
            student_id=student_id,
        )
    )

    if not registration:
        flash(
            "You are not registered for this event.",
            "warning",
        )
        return redirect(
            url_for(
                "student.event_details",
                event_id=event_id,
            )
        )

    result = event_service.mark_registration_attended(
        event_id=event_id,
        student_id=student_id,
    )

    if result.get("success"):
        flash(
            result.get(
                "message",
                "Event attendance updated.",
            ),
            "success",
        )
    else:
        flash(
            result.get(
                "message",
                "Unable to update event attendance.",
            ),
            "danger",
        )

    return redirect(
        url_for(
            "student.event_details",
            event_id=event_id,
        )
    )


# ============================================================
# STUDENT NOTIFICATIONS
# ============================================================

@student_bp.route("/notifications")
@student_required
def notifications():
    """
    Show notifications received by the student.
    """
    student_id = session["user_id"]

    notifications = fetch_all(
        """
        SELECT
            n.id,
            n.event_id,
            n.student_id,
            n.title,
            n.message,
            n.notification_type,
            n.is_read,
            n.created_at,
            e.event_name
        FROM notifications n
        LEFT JOIN events e
            ON e.id = n.event_id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
        """,
        (student_id,),
    )

    return render_template(
        "student/dashboard.html",
        notifications=notifications,
        notification_view=True,
    )


# ============================================================
# MARK NOTIFICATION AS READ
# ============================================================

@student_bp.route(
    "/notifications/<int:notification_id>/read",
    methods=["POST"],
)
@student_required
def mark_notification_read(notification_id):
    """
    Mark one student notification as read.
    """
    student_id = session["user_id"]

    notification = fetch_one(
        """
        SELECT
            id
        FROM notifications
        WHERE id = ?
          AND user_id = ?
        LIMIT 1
        """,
        (
            notification_id,
            student_id,
        ),
    )

    if not notification:
        flash(
            "Notification not found.",
            "warning",
        )
        return redirect(
            url_for("student.notifications")
        )

    from database.db import execute_write

    execute_write(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE id = ?
          AND user_id = ?
        """,
        (
            notification_id,
            student_id,
        ),
    )

    return redirect(
        url_for("student.notifications")
    )