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
from services import attendance_service
from services import event_service

from utils.decorators import teacher_required


# ============================================================
# BLUEPRINT
# ============================================================

teacher_bp = Blueprint(
    "teacher",
    __name__,
    url_prefix="/teacher",
)


# ============================================================
# TEACHER DASHBOARD
# ============================================================

@teacher_bp.route("/")
@teacher_bp.route("/dashboard")
@teacher_required
def dashboard():
    """
    Main teacher dashboard.

    Shows:
        - Academic lectures
        - Upcoming/live event coordination assignments
        - Event verification notifications
        - Attendance information
    """
    teacher_id = session["user_id"]

    teacher = auth_service.get_user_by_id(
        teacher_id
    )

    if not teacher:
        session.clear()

        flash(
            "Teacher account could not be found. Please log in again.",
            "danger",
        )

        return redirect(
            url_for("auth.login")
        )

    # --------------------------------------------------------
    # Academic lectures
    # --------------------------------------------------------

    lectures = attendance_service.get_teacher_lectures(
        teacher_id=teacher_id
    )

    # --------------------------------------------------------
    # Event coordinator assignments
    # --------------------------------------------------------

    coordinator_events = (
        event_service.get_teacher_coordinator_events(
            teacher_id
        )
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

            e.event_name,

            u.name AS student_name,
            u.roll_no AS student_roll_no

        FROM notifications n

        LEFT JOIN events e
            ON e.id = n.event_id

        LEFT JOIN users u
            ON u.id = n.student_id

        WHERE n.user_id = ?

        ORDER BY n.created_at DESC

        LIMIT 10
        """,
        (teacher_id,),
    )

    unread_row = fetch_one(
        """
        SELECT
            COUNT(*) AS count
        FROM notifications
        WHERE user_id = ?
          AND is_read = 0
        """,
        (teacher_id,),
    )

    unread_notification_count = int(
        unread_row["count"]
        if unread_row
        else 0
    )

    # --------------------------------------------------------
    # Recently verified event students
    # --------------------------------------------------------

    verified_students = fetch_all(
        """
        SELECT
            ev.id AS verification_id,
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
            e.start_time AS event_start_time,
            e.end_time AS event_end_time,
            e.venue,

            u.name AS student_name,
            u.roll_no AS student_roll_no,
            u.email AS student_email

        FROM event_verifications ev

        JOIN events e
            ON e.id = ev.event_id

        JOIN users u
            ON u.id = ev.student_id

        WHERE ev.verification_status = 'verified'
          AND ev.qr_verified = 1
          AND ev.face_verified = 1

          AND EXISTS (
              SELECT 1
              FROM event_coordinators ec
              WHERE ec.event_id = ev.event_id
                AND ec.user_id = ?
            )

        ORDER BY ev.verified_at DESC

        LIMIT 10
        """,
        (teacher_id,),
    )

    return render_template(
        "teacher/dashboard.html",
        teacher=teacher,
        lectures=lectures,
        coordinator_events=coordinator_events,
        notifications=notifications,
        unread_notification_count=unread_notification_count,
        verified_students=verified_students,
    )


# ============================================================
# TEACHER NOTIFICATIONS
# ============================================================

@teacher_bp.route("/notifications")
@teacher_required
def notifications():
    """
    Show all notifications for the teacher.

    Event verification notifications can contain:
        - Student name
        - Roll number
        - Event name
        - QR verification
        - Face verification
        - Verification time
    """
    teacher_id = session["user_id"]

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

            e.event_name,

            u.name AS student_name,
            u.roll_no AS student_roll_no,
            u.email AS student_email

        FROM notifications n

        LEFT JOIN events e
            ON e.id = n.event_id

        LEFT JOIN users u
            ON u.id = n.student_id

        WHERE n.user_id = ?

        ORDER BY n.created_at DESC
        """,
        (teacher_id,),
    )

    return render_template(
        "teacher/notifications.html",
        notifications=notifications,
    )


# ============================================================
# MARK NOTIFICATION AS READ
# ============================================================

@teacher_bp.route(
    "/notifications/<int:notification_id>/read",
    methods=["POST"],
)
@teacher_required
def mark_notification_read(notification_id):
    """
    Mark one teacher notification as read.
    """
    teacher_id = session["user_id"]

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
            teacher_id,
        ),
    )

    if not notification:
        flash(
            "Notification not found.",
            "warning",
        )

        return redirect(
            url_for("teacher.notifications")
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
            teacher_id,
        ),
    )

    return redirect(
        url_for("teacher.notifications")
    )


# ============================================================
# MARK ALL NOTIFICATIONS AS READ
# ============================================================

@teacher_bp.route(
    "/notifications/read-all",
    methods=["POST"],
)
@teacher_required
def mark_all_notifications_read():
    """
    Mark all teacher notifications as read.
    """
    teacher_id = session["user_id"]

    from database.db import execute_write

    execute_write(
        """
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
        """,
        (teacher_id,),
    )

    flash(
        "All notifications marked as read.",
        "success",
    )

    return redirect(
        url_for("teacher.notifications")
    )


# ============================================================
# VERIFIED EVENT STUDENTS
# ============================================================

@teacher_bp.route("/verified-students")
@teacher_required
def verified_students():
    """
    Show students whose event presence was successfully
    verified for events coordinated by this teacher.
    """
    teacher_id = session["user_id"]

    students = fetch_all(
        """
        SELECT
            ev.id AS verification_id,
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
            e.start_time AS event_start_time,
            e.end_time AS event_end_time,
            e.venue,

            u.name AS student_name,
            u.roll_no AS student_roll_no,
            u.email AS student_email,
            d.code AS department_code,
            d.name AS department_name,
            u.semester,
            u.section

        FROM event_verifications ev

        JOIN events e
            ON e.id = ev.event_id

        JOIN users u
            ON u.id = ev.student_id

        LEFT JOIN departments d
            ON d.id = u.department_id

        JOIN event_coordinators ec
            ON ec.event_id = ev.event_id
            AND ec.user_id = ?

        WHERE ev.verification_status = 'verified'
          AND ev.qr_verified = 1
          AND ev.face_verified = 1

        ORDER BY
            ev.verified_at DESC,
            u.roll_no ASC,
            u.name ASC
        """,
        (teacher_id,),
    )

    return render_template(
        "teacher/verified_students.html",
        verified_students=students,
    )


# ============================================================
# EVENT COORDINATOR WORKSPACE
# ============================================================

@teacher_bp.route("/coordinator")
@teacher_required
def coordinator():
    """
    Teacher event coordinator workspace.

    This is separate from the teacher's academic lecture
    responsibilities.
    """
    teacher_id = session["user_id"]

    coordinator_events = (
        event_service.get_teacher_coordinator_events(
            teacher_id
        )
    )

    event_data = []

    for event in coordinator_events:
        statistics = (
            event_service.get_event_statistics(
                event["id"]
            )
        )

        registrations = (
            event_service.get_event_registrations(
                event["id"]
            )
        )

        event_data.append(
            {
                "event": event,
                "statistics": statistics,
                "registrations": registrations,
            }
        )

    return render_template(
        "teacher/coordinator.html",
        coordinator_events=coordinator_events,
        event_data=event_data,
    )


# ============================================================
# EVENT REGISTRATIONS
# ============================================================

@teacher_bp.route(
    "/coordinator/event/<int:event_id>/registrations"
)
@teacher_required
def event_registrations(event_id):
    """
    Show students registered for an event coordinated
    by the logged-in teacher.
    """
    teacher_id = session["user_id"]

    if not event_service.is_event_coordinator(
        event_id=event_id,
        user_id=teacher_id,
    ):
        flash(
            "You are not assigned as coordinator for this event.",
            "danger",
        )

        return redirect(
            url_for("teacher.coordinator")
        )

    event = event_service.get_event_by_id(
        event_id
    )

    if not event:
        flash(
            "Event not found.",
            "danger",
        )

        return redirect(
            url_for("teacher.coordinator")
        )

    registrations = (
        event_service.get_event_registrations(
            event_id
        )
    )

    return render_template(
        "teacher/coordinator.html",
        event=event,
        registrations=registrations,
        coordinator_view=True,
    )


# ============================================================
# EVENT ATTENDANCE
# ============================================================

@teacher_bp.route(
    "/coordinator/event/<int:event_id>/attendance",
    methods=["POST"],
)
@teacher_required
def mark_event_attendance(event_id):
    """
    Manually update event-registration attendance.

    This is event attendance only.

    It NEVER updates the academic attendance table.
    """
    teacher_id = session["user_id"]

    if not event_service.is_event_coordinator(
        event_id=event_id,
        user_id=teacher_id,
    ):
        flash(
            "You are not assigned as coordinator for this event.",
            "danger",
        )

        return redirect(
            url_for("teacher.coordinator")
        )

    student_id = request.form.get(
        "student_id",
        type=int,
    )

    if not student_id:
        flash(
            "Student selection is required.",
            "warning",
        )

        return redirect(
            url_for(
                "teacher.event_registrations",
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
            "teacher.event_registrations",
            event_id=event_id,
        )
    )


# ============================================================
# ACADEMIC ATTENDANCE
# ============================================================

@teacher_bp.route("/attendance")
@teacher_required
def attendance():
    """
    Open the teacher's academic attendance workspace.

    Actual attendance marking is handled by
    attendance_routes.py.
    """
    return redirect(
        url_for(
            "attendance.teacher_attendance"
        )
    )


# ============================================================
# SINGLE LECTURE ATTENDANCE
# ============================================================

@teacher_bp.route(
    "/attendance/lecture/<int:lecture_id>"
)
@teacher_required
def lecture_attendance(lecture_id):
    """
    Shortcut to the academic attendance sheet.
    """
    return redirect(
        url_for(
            "attendance.lecture_attendance",
            lecture_id=lecture_id,
        )
    )


# ============================================================
# TEACHER PROFILE
# ============================================================

@teacher_bp.route("/profile")
@teacher_required
def profile():
    """
    Show teacher profile information.
    """
    teacher_id = session["user_id"]

    teacher = auth_service.get_user_by_id(
        teacher_id
    )

    if not teacher:
        session.clear()

        flash(
            "Teacher account could not be found.",
            "danger",
        )

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "teacher/dashboard.html",
        teacher=teacher,
        profile_view=True,
    )