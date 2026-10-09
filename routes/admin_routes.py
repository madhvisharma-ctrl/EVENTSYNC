from datetime import datetime

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from database.db import (
    fetch_all,
    fetch_one,
    execute_write,
)

from services import event_service
from utils.decorators import admin_required


# ============================================================
# BLUEPRINT
# ============================================================

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)


# ============================================================
# CONSTANTS
# ============================================================

EVENT_CATEGORIES = [
    "Technical",
    "Sports",
    "Cultural",
    "Placement & Career",
    "Competitions",
    "Research & Innovation",
    "College Fest",
    "Other",
]

EVENT_TYPES = [
    "Hackathon",
    "Coding Competition",
    "Workshop",
    "Seminar",
    "Conference",
    "Career Guidance",
    "Annual Fest",
    "Sports Meet",
    "Competition",
    "Other",
]

EVENT_STATUSES = [
    "draft",
    "upcoming",
    "live",
    "completed",
    "cancelled",
]


# ============================================================
# DASHBOARD
# ============================================================

@admin_bp.route("/")
@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    """
    Main admin dashboard.
    """

    total_users = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM users
        """
    )["count"]

    total_students = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'student'
        """
    )["count"]

    total_teachers = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'teacher'
        """
    )["count"]

    total_admins = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'admin'
        """
    )["count"]

    total_departments = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM departments
        """
    )["count"]

    total_subjects = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM subjects
        """
    )["count"]

    total_lectures = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM lectures
        """
    )["count"]

    total_events = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM events
        """
    )["count"]

    live_events = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM events
        WHERE status = 'live'
        """
    )["count"]

    total_registrations = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM event_registrations
        WHERE status != 'cancelled'
        """
    )["count"]

    total_verifications = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM event_verifications
        WHERE verification_status = 'verified'
        """
    )["count"]

    total_attendance = fetch_one(
        """
        SELECT COUNT(*) AS count
        FROM attendance
        """
    )["count"]

    recent_events = fetch_all(
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
            e.status,
            u.name AS created_by_name
        FROM events e
        LEFT JOIN users u
            ON u.id = e.created_by
        ORDER BY e.created_at DESC
        LIMIT 8
        """
    )

    recent_verifications = fetch_all(
        """
        SELECT
            ev.id,
            ev.event_id,
            ev.student_id,
            ev.verification_status,
            ev.qr_verified,
            ev.face_verified,
            ev.confidence,
            ev.verified_at,
            e.event_name,
            u.name AS student_name,
            u.roll_no
        FROM event_verifications ev
        JOIN events e
            ON e.id = ev.event_id
        JOIN users u
            ON u.id = ev.student_id
        ORDER BY ev.created_at DESC
        LIMIT 8
        """
    )

    stats = {
        "total_users": total_users,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_admins": total_admins,
        "total_departments": total_departments,
        "total_subjects": total_subjects,
        "total_lectures": total_lectures,
        "total_events": total_events,
        "live_events": live_events,
        "total_registrations": total_registrations,
        "total_verifications": total_verifications,
        "total_attendance": total_attendance,
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_events=recent_events,
        recent_verifications=recent_verifications,
    )


# ============================================================
# USERS
# ============================================================

@admin_bp.route("/users")
@admin_required
def users():
    """
    List all users.
    """

    users_list = fetch_all(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.role,
            u.roll_no,
            u.semester,
            u.section,
            u.face_image_path,
            u.is_active,
            u.created_at,
            d.code AS department_code,
            d.name AS department_name
        FROM users u
        LEFT JOIN departments d
            ON d.id = u.department_id
        ORDER BY
            CASE u.role
                WHEN 'admin' THEN 1
                WHEN 'teacher' THEN 2
                WHEN 'student' THEN 3
                ELSE 4
            END,
            u.name ASC
        """
    )

    return render_template(
        "admin/users.html",
        users=users_list,
    )


# ============================================================
# ACTIVATE / DEACTIVATE USER
# ============================================================

@admin_bp.route(
    "/users/<int:user_id>/toggle-status",
    methods=["POST"],
)
@admin_required
def toggle_user_status(user_id):
    """
    Activate or deactivate a user.
    """

    user = fetch_one(
        """
        SELECT
            id,
            name,
            role,
            is_active
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )

    if not user:
        flash(
            "User not found.",
            "danger",
        )

        return redirect(
            url_for("admin.users")
        )

    new_status = 0 if user["is_active"] else 1

    execute_write(
        """
        UPDATE users
        SET is_active = ?
        WHERE id = ?
        """,
        (
            new_status,
            user_id,
        ),
    )

    status_text = (
        "activated"
        if new_status
        else "deactivated"
    )

    flash(
        f"User {status_text} successfully.",
        "success",
    )

    return redirect(
        url_for("admin.users")
    )


# ============================================================
# DEPARTMENTS
# ============================================================

@admin_bp.route("/departments")
@admin_required
def departments():
    """
    List departments.
    """

    department_list = fetch_all(
        """
        SELECT
            d.id,
            d.code,
            d.name,
            d.is_active,
            d.created_at,
            (
                SELECT COUNT(*)
                FROM users u
                WHERE u.department_id = d.id
            ) AS user_count,
            (
                SELECT COUNT(*)
                FROM subjects s
                WHERE s.department_id = d.id
            ) AS subject_count
        FROM departments d
        ORDER BY d.code ASC
        """
    )

    return render_template(
        "admin/dashboard.html",
        departments=department_list,
        department_view=True,
    )


# ============================================================
# ADD DEPARTMENT
# ============================================================

@admin_bp.route(
    "/departments/add",
    methods=["POST"],
)
@admin_required
def add_department():
    """
    Create a department.
    """

    code = request.form.get(
        "code",
        "",
    ).strip().upper()

    name = request.form.get(
        "name",
        "",
    ).strip()

    if not code or not name:
        flash(
            "Department code and name are required.",
            "warning",
        )

        return redirect(
            url_for("admin.departments")
        )

    existing = fetch_one(
        """
        SELECT id
        FROM departments
        WHERE code = ?
           OR name = ?
        """,
        (
            code,
            name,
        ),
    )

    if existing:
        flash(
            "A department with this code or name already exists.",
            "danger",
        )

        return redirect(
            url_for("admin.departments")
        )

    execute_write(
        """
        INSERT INTO departments (
            code,
            name,
            is_active
        )
        VALUES (?, ?, 1)
        """,
        (
            code,
            name,
        ),
    )

    flash(
        "Department created successfully.",
        "success",
    )

    return redirect(
        url_for("admin.departments")
    )


# ============================================================
# SUBJECTS
# ============================================================

@admin_bp.route("/subjects")
@admin_required
def subjects():
    """
    List all subjects.
    """

    subjects_list = fetch_all(
        """
        SELECT
            s.id,
            s.subject_code,
            s.subject_name,
            s.semester,
            s.credits,
            s.is_active,
            d.code AS department_code,
            d.name AS department_name
        FROM subjects s
        LEFT JOIN departments d
            ON d.id = s.department_id
        ORDER BY
            d.code ASC,
            s.semester ASC,
            s.subject_code ASC
        """
    )

    return render_template(
        "admin/dashboard.html",
        subjects=subjects_list,
        subject_view=True,
    )


# ============================================================
# ADD SUBJECT
# ============================================================

@admin_bp.route(
    "/subjects/add",
    methods=["POST"],
)
@admin_required
def add_subject():
    """
    Create an academic subject.
    """

    subject_code = request.form.get(
        "subject_code",
        "",
    ).strip().upper()

    subject_name = request.form.get(
        "subject_name",
        "",
    ).strip()

    department_id = request.form.get(
        "department_id",
        type=int,
    )

    semester = request.form.get(
        "semester",
        type=int,
    )

    credits = request.form.get(
        "credits",
        type=int,
        default=3,
    )

    if (
        not subject_code
        or not subject_name
        or not department_id
        or not semester
    ):
        flash(
            "Subject code, name, department and semester are required.",
            "warning",
        )

        return redirect(
            url_for("admin.subjects")
        )

    existing = fetch_one(
        """
        SELECT id
        FROM subjects
        WHERE subject_code = ?
        """,
        (subject_code,),
    )

    if existing:
        flash(
            "A subject with this code already exists.",
            "danger",
        )

        return redirect(
            url_for("admin.subjects")
        )

    execute_write(
        """
        INSERT INTO subjects (
            subject_code,
            subject_name,
            department_id,
            semester,
            credits,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (
            subject_code,
            subject_name,
            department_id,
            semester,
            credits,
        ),
    )

    flash(
        "Subject created successfully.",
        "success",
    )

    return redirect(
        url_for("admin.subjects")
    )


# ============================================================
# LECTURES
# ============================================================

@admin_bp.route("/lectures")
@admin_required
def lectures():
    """
    List academic lectures / timetable.
    """

    lectures_list = fetch_all(
        """
        SELECT
            l.id,
            l.lecture_date,
            l.start_time,
            l.end_time,
            l.room,
            l.semester,
            l.section,
            l.is_active,

            u.id AS teacher_id,
            u.name AS teacher_name,

            s.id AS subject_id,
            s.subject_code,
            s.subject_name,

            d.code AS department_code,
            d.name AS department_name

        FROM lectures l

        JOIN users u
            ON u.id = l.teacher_id

        JOIN subjects s
            ON s.id = l.subject_id

        LEFT JOIN departments d
            ON d.id = l.department_id

        ORDER BY
            l.lecture_date DESC,
            l.start_time DESC
        """
    )

    teachers = fetch_all(
        """
        SELECT
            id,
            name,
            email
        FROM users
        WHERE role = 'teacher'
          AND is_active = 1
        ORDER BY name ASC
        """
    )

    subjects_list = fetch_all(
        """
        SELECT
            id,
            subject_code,
            subject_name,
            department_id,
            semester
        FROM subjects
        WHERE is_active = 1
        ORDER BY subject_code ASC
        """
    )

    departments_list = fetch_all(
        """
        SELECT
            id,
            code,
            name
        FROM departments
        WHERE is_active = 1
        ORDER BY code ASC
        """
    )

    return render_template(
        "admin/lectures.html",
        lectures=lectures_list,
        teachers=teachers,
        subjects=subjects_list,
        departments=departments_list,
    )


# ============================================================
# ADD LECTURE
# ============================================================

@admin_bp.route(
    "/lectures/add",
    methods=["POST"],
)
@admin_required
def add_lecture():
    """
    Create an academic lecture / timetable entry.
    """

    teacher_id = request.form.get(
        "teacher_id",
        type=int,
    )

    subject_id = request.form.get(
        "subject_id",
        type=int,
    )

    department_id = request.form.get(
        "department_id",
        type=int,
    )

    semester = request.form.get(
        "semester",
        type=int,
    )

    section = request.form.get(
        "section",
        "",
    ).strip()

    lecture_date = request.form.get(
        "lecture_date",
        "",
    ).strip()

    start_time = request.form.get(
        "start_time",
        "",
    ).strip()

    end_time = request.form.get(
        "end_time",
        "",
    ).strip()

    room = request.form.get(
        "room",
        "",
    ).strip()

    if not all(
        [
            teacher_id,
            subject_id,
            department_id,
            semester,
            section,
            lecture_date,
            start_time,
            end_time,
            room,
        ]
    ):
        flash(
            "All lecture fields are required.",
            "warning",
        )

        return redirect(
            url_for("admin.lectures")
        )

    teacher = fetch_one(
        """
        SELECT id
        FROM users
        WHERE id = ?
          AND role = 'teacher'
          AND is_active = 1
        """,
        (teacher_id,),
    )

    subject = fetch_one(
        """
        SELECT id
        FROM subjects
        WHERE id = ?
          AND is_active = 1
        """,
        (subject_id,),
    )

    if not teacher or not subject:
        flash(
            "Invalid teacher or subject selected.",
            "danger",
        )

        return redirect(
            url_for("admin.lectures")
        )

    execute_write(
        """
        INSERT INTO lectures (
            teacher_id,
            subject_id,
            department_id,
            semester,
            section,
            lecture_date,
            start_time,
            end_time,
            room,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            teacher_id,
            subject_id,
            department_id,
            semester,
            section,
            lecture_date,
            start_time,
            end_time,
            room,
        ),
    )

    flash(
        "Lecture/timetable entry created successfully.",
        "success",
    )

    return redirect(
        url_for("admin.lectures")
    )


# ============================================================
# EVENTS
# ============================================================

@admin_bp.route("/events")
@admin_required
def events():
    """
    Admin event management page.
    """

    events_list = fetch_all(
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
            e.created_at,

            u.name AS created_by_name,

            (
                SELECT COUNT(*)
                FROM event_registrations er
                WHERE er.event_id = e.id
                  AND er.status != 'cancelled'
            ) AS registration_count,

            (
                SELECT COUNT(*)
                FROM event_verifications ev
                WHERE ev.event_id = e.id
                  AND ev.verification_status = 'verified'
            ) AS verification_count

        FROM events e

        LEFT JOIN users u
            ON u.id = e.created_by

        ORDER BY
            e.event_date DESC,
            e.start_time DESC
        """
    )

    return render_template(
        "admin/events.html",
        events=events_list,
    )


# ============================================================
# NEW EVENT FORM
# ============================================================

@admin_bp.route("/events/new")
@admin_required
def new_event():
    """
    Show event creation form.
    """

    teachers = fetch_all(
        """
        SELECT
            id,
            name,
            email
        FROM users
        WHERE role = 'teacher'
          AND is_active = 1
        ORDER BY name ASC
        """
    )

    students = fetch_all(
        """
        SELECT
            id,
            name,
            roll_no,
            email
        FROM users
        WHERE role = 'student'
          AND is_active = 1
        ORDER BY
            roll_no ASC,
            name ASC
        """
    )

    lectures_list = fetch_all(
        """
        SELECT
            l.id,
            l.lecture_date,
            l.start_time,
            l.end_time,
            l.room,
            s.subject_code,
            s.subject_name,
            u.name AS teacher_name
        FROM lectures l
        JOIN subjects s
            ON s.id = l.subject_id
        JOIN users u
            ON u.id = l.teacher_id
        WHERE l.is_active = 1
        ORDER BY
            l.lecture_date DESC,
            l.start_time DESC
        """
    )

    return render_template(
        "admin/event_form.html",
        event=None,
        teachers=teachers,
        students=students,
        lectures=lectures_list,
        event_categories=EVENT_CATEGORIES,
        event_types=EVENT_TYPES,
        event_statuses=EVENT_STATUSES,
    )


# ============================================================
# CREATE EVENT
# ============================================================

@admin_bp.route(
    "/events/create",
    methods=["POST"],
)
@admin_required
def create_event():
    """
    Create a new event.
    """

    event_name = request.form.get(
        "event_name",
        "",
    ).strip()

    event_category = request.form.get(
        "event_category",
        "",
    ).strip()

    event_type = request.form.get(
        "event_type",
        "",
    ).strip()

    event_date = request.form.get(
        "event_date",
        "",
    ).strip()

    start_time = request.form.get(
        "start_time",
        "",
    ).strip()

    end_time = request.form.get(
        "end_time",
        "",
    ).strip()

    venue = request.form.get(
        "venue",
        "",
    ).strip()

    description = request.form.get(
        "description",
        "",
    ).strip()

    status = request.form.get(
        "status",
        "upcoming",
    ).strip().lower()

    if status not in EVENT_STATUSES:
        status = "upcoming"

    if not all(
        [
            event_name,
            event_category,
            event_type,
            event_date,
            start_time,
            end_time,
            venue,
        ]
    ):
        flash(
            "Event name, category, type, date, time and venue are required.",
            "warning",
        )

        return redirect(
            url_for("admin.new_event")
        )

    execute_write(
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
            event_name,
            event_category,
            event_type,
            event_date,
            start_time,
            end_time,
            venue,
            description,
            request_user_id(),
            status,
        ),
    )

    flash(
        "Event created successfully.",
        "success",
    )

    return redirect(
        url_for("admin.events")
    )


# ============================================================
# EVENT DETAILS
# ============================================================

@admin_bp.route(
    "/events/<int:event_id>"
)
@admin_required
def event_details(event_id):
    """
    Show complete event administration details.
    """

    event = fetch_one(
        """
        SELECT
            e.*,
            u.name AS created_by_name
        FROM events e
        LEFT JOIN users u
            ON u.id = e.created_by
        WHERE e.id = ?
        """,
        (event_id,),
    )

    if not event:
        flash(
            "Event not found.",
            "danger",
        )

        return redirect(
            url_for("admin.events")
        )

    coordinators = event_service.get_event_coordinators(
        event_id
    )

    registrations = event_service.get_event_registrations(
        event_id
    )

    mappings = fetch_all(
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
            l.section,
            l.semester,

            s.subject_code,
            s.subject_name,

            u.name AS teacher_name

        FROM event_lecture_mapping elm

        JOIN lectures l
            ON l.id = elm.lecture_id

        JOIN subjects s
            ON s.id = l.subject_id

        JOIN users u
            ON u.id = l.teacher_id

        WHERE elm.event_id = ?

        ORDER BY
            l.lecture_date DESC,
            l.start_time DESC
        """,
        (event_id,),
    )

    teachers = fetch_all(
        """
        SELECT
            id,
            name,
            email
        FROM users
        WHERE role = 'teacher'
          AND is_active = 1
        ORDER BY name ASC
        """
    )

    students = fetch_all(
        """
        SELECT
            id,
            name,
            roll_no,
            email
        FROM users
        WHERE role = 'student'
          AND is_active = 1
        ORDER BY
            roll_no ASC,
            name ASC
        """
    )

    lectures_list = fetch_all(
        """
        SELECT
            l.id,
            l.lecture_date,
            l.start_time,
            l.end_time,
            l.room,
            l.section,
            l.semester,
            s.subject_code,
            s.subject_name,
            u.name AS teacher_name
        FROM lectures l
        JOIN subjects s
            ON s.id = l.subject_id
        JOIN users u
            ON u.id = l.teacher_id
        WHERE l.is_active = 1
        ORDER BY
            l.lecture_date DESC,
            l.start_time DESC
        """
    )

    return render_template(
        "admin/events.html",
        event=event,
        coordinators=coordinators,
        registrations=registrations,
        mappings=mappings,
        teachers=teachers,
        students=students,
        lectures=lectures_list,
        event_details_view=True,
    )


# ============================================================
# UPDATE EVENT STATUS
# ============================================================

@admin_bp.route(
    "/events/<int:event_id>/status",
    methods=["POST"],
)
@admin_required
def update_event_status(event_id):
    """
    Update event lifecycle status.
    """

    status = request.form.get(
        "status",
        "",
    ).strip().lower()

    if status not in EVENT_STATUSES:
        flash(
            "Invalid event status.",
            "danger",
        )

        return redirect(
            url_for(
                "admin.event_details",
                event_id=event_id,
            )
        )

    event = fetch_one(
        """
        SELECT id
        FROM events
        WHERE id = ?
        """,
        (event_id,),
    )

    if not event:
        flash(
            "Event not found.",
            "danger",
        )

        return redirect(
            url_for("admin.events")
        )

    execute_write(
        """
        UPDATE events
        SET status = ?
        WHERE id = ?
        """,
        (
            status,
            event_id,
        ),
    )

    flash(
        f"Event status changed to {status}.",
        "success",
    )

    return redirect(
        url_for(
            "admin.event_details",
            event_id=event_id,
        )
    )


# ============================================================
# DELETE EVENT
# ============================================================

@admin_bp.route(
    "/events/<int:event_id>/delete",
    methods=["POST"],
)
@admin_required
def delete_event(event_id):
    """
    Delete an event.

    Related records are deleted first because the database
    uses foreign-key constraints.
    """

    event = fetch_one(
        """
        SELECT
            id,
            event_name
        FROM events
        WHERE id = ?
        """,
        (event_id,),
    )

    if not event:
        flash(
            "Event not found.",
            "danger",
        )

        return redirect(
            url_for("admin.events")
        )

    # Delete dependent records first.

    execute_write(
        """
        DELETE FROM notifications
        WHERE event_id = ?
        """,
        (event_id,),
    )

    execute_write(
        """
        DELETE FROM event_verifications
        WHERE event_id = ?
        """,
        (event_id,),
    )

    execute_write(
        """
        DELETE FROM qr_tokens
        WHERE event_id = ?
        """,
        (event_id,),
    )

    execute_write(
        """
        DELETE FROM event_lecture_mapping
        WHERE event_id = ?
        """,
        (event_id,),
    )

    execute_write(
        """
        DELETE FROM event_registrations
        WHERE event_id = ?
        """,
        (event_id,),
    )

    execute_write(
        """
        DELETE FROM event_coordinators
        WHERE event_id = ?
        """,
        (event_id,),
    )

    execute_write(
        """
        DELETE FROM events
        WHERE id = ?
        """,
        (event_id,),
    )

    flash(
        f"Event '{event['event_name']}' deleted successfully.",
        "success",
    )

    return redirect(
        url_for("admin.events")
    )


# ============================================================
# ASSIGN EVENT COORDINATOR
# ============================================================

@admin_bp.route(
    "/events/<int:event_id>/coordinators/add",
    methods=["POST"],
)
@admin_required
def add_event_coordinator(event_id):
    """
    Assign a teacher or student as an event coordinator.
    """

    user_id = request.form.get(
        "user_id",
        type=int,
    )

    coordinator_role = request.form.get(
        "coordinator_role",
        "main_coordinator",
    ).strip().lower()

    if coordinator_role not in {
        "main_coordinator",
        "student_coordinator",
    }:
        flash(
            "Invalid coordinator role.",
            "danger",
        )

        return redirect(
            url_for(
                "admin.event_details",
                event_id=event_id,
            )
        )

    if not user_id:
        flash(
            "Please select a user.",
            "warning",
        )

        return redirect(
            url_for(
                "admin.event_details",
                event_id=event_id,
            )
        )

    user = fetch_one(
        """
        SELECT
            id,
            role,
            name
        FROM users
        WHERE id = ?
          AND is_active = 1
        """,
        (user_id,),
    )

    if not user:
        flash(
            "Selected user not found.",
            "danger",
        )

        return redirect(
            url_for(
                "admin.event_details",
                event_id=event_id,
            )
        )

    if (
        coordinator_role == "main_coordinator"
        and user["role"] != "teacher"
    ):
        flash(
            "Main coordinator must be a teacher.",
            "warning",
        )

        return redirect(
            url_for(
                "admin.event_details",
                event_id=event_id,
            )
        )

    if (
        coordinator_role == "student_coordinator"
        and user["role"] != "student"
    ):
        flash(
            "Student coordinator must be a student.",
            "warning",
        )

        return redirect(
            url_for(
                "admin.event_details",
                event_id=event_id,
            )
        )

    result = event_service.assign_event_coordinator(
        event_id=event_id,
        user_id=user_id,
        coordinator_role=coordinator_role,
    )

    if result.get("success"):
        flash(
            result.get(
                "message",
                "Coordinator assigned successfully.",
            ),
            "success",
        )
    else:
        flash(
            result.get(
                "message",
                "Unable to assign coordinator.",
            ),
            "danger",
        )

    return redirect(
        url_for(
            "admin.event_details",
            event_id=event_id,
        )
    )


# ============================================================
# REMOVE EVENT COORDINATOR
# ============================================================

@admin_bp.route(
    "/events/<int:event_id>/coordinators/<int:user_id>/remove",
    methods=["POST"],
)
@admin_required
def remove_event_coordinator(
    event_id,
    user_id,
):
    """
    Remove an event coordinator.
    """

    result = event_service.remove_event_coordinator(
        event_id=event_id,
        user_id=user_id,
    )

    if result.get("success"):
        flash(
            result.get(
                "message",
                "Coordinator removed successfully.",
            ),
            "success",
        )
    else:
        flash(
            result.get(
                "message",
                "Unable to remove coordinator.",
            ),
            "danger",
        )

    return redirect(
        url_for(
            "admin.event_details",
            event_id=event_id,
        )
    )


# ============================================================
# MAP EVENT TO LECTURE
# ============================================================

@admin_bp.route(
    "/events/<int:event_id>/lectures/map",
    methods=["POST"],
)
@admin_required
def map_event_to_lecture(event_id):
    """
    Map an event to an academic lecture.

    This mapping is informational/administrative.
    It does NOT automatically mark academic attendance.
    """

    lecture_id = request.form.get(
        "lecture_id",
        type=int,
    )

    if not lecture_id:
        flash(
            "Please select a lecture.",
            "warning",
        )

        return redirect(
            url_for(
                "admin.event_details",
                event_id=event_id,
            )
        )

    event = fetch_one(
        """
        SELECT id
        FROM events
        WHERE id = ?
        """,
        (event_id,),
    )

    lecture = fetch_one(
        """
        SELECT id
        FROM lectures
        WHERE id = ?
        """,
        (lecture_id,),
    )

    if not event or not lecture:
        flash(
            "Invalid event or lecture.",
            "danger",
        )

        return redirect(
            url_for(
                "admin.event_details",
                event_id=event_id,
            )
        )

    existing = fetch_one(
        """
        SELECT id
        FROM event_lecture_mapping
        WHERE event_id = ?
          AND lecture_id = ?
        """,
        (
            event_id,
            lecture_id,
        ),
    )

    if existing:
        flash(
            "This event is already mapped to the selected lecture.",
            "warning",
        )

        return redirect(
            url_for(
                "admin.event_details",
                event_id=event_id,
            )
        )

    execute_write(
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

    flash(
        "Event mapped to lecture successfully.",
        "success",
    )

    return redirect(
        url_for(
            "admin.event_details",
            event_id=event_id,
        )
    )


# ============================================================
# REMOVE EVENT ↔ LECTURE MAPPING
# ============================================================

@admin_bp.route(
    "/events/<int:event_id>/lectures/<int:lecture_id>/unmap",
    methods=["POST"],
)
@admin_required
def unmap_event_from_lecture(
    event_id,
    lecture_id,
):
    """
    Remove event-to-lecture mapping.
    """

    execute_write(
        """
        DELETE FROM event_lecture_mapping
        WHERE event_id = ?
          AND lecture_id = ?
        """,
        (
            event_id,
            lecture_id,
        ),
    )

    flash(
        "Event-lecture mapping removed.",
        "success",
    )

    return redirect(
        url_for(
            "admin.event_details",
            event_id=event_id,
        )
    )


# ============================================================
# EVENT REGISTRATIONS
# ============================================================

@admin_bp.route(
    "/events/<int:event_id>/registrations"
)
@admin_required
def event_registrations(event_id):
    """
    Show all student registrations for an event.
    """

    event = fetch_one(
        """
        SELECT
            id,
            event_name,
            event_date,
            venue,
            status
        FROM events
        WHERE id = ?
        """,
        (event_id,),
    )

    if not event:
        flash(
            "Event not found.",
            "danger",
        )

        return redirect(
            url_for("admin.events")
        )

    registrations = event_service.get_event_registrations(
        event_id
    )

    return render_template(
        "admin/events.html",
        event=event,
        registrations=registrations,
        registration_view=True,
    )


# ============================================================
# REPORTS
# ============================================================

@admin_bp.route("/reports")
@admin_required
def reports():
    """
    Admin reporting dashboard.
    """

    event_report = fetch_all(
        """
        SELECT
            e.id,
            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.status,

            (
                SELECT COUNT(*)
                FROM event_registrations er
                WHERE er.event_id = e.id
                  AND er.status != 'cancelled'
            ) AS registrations,

            (
                SELECT COUNT(*)
                FROM event_verifications ev
                WHERE ev.event_id = e.id
                  AND ev.verification_status = 'verified'
            ) AS verified_students,

            (
                SELECT COUNT(*)
                FROM event_coordinators ec
                WHERE ec.event_id = e.id
            ) AS coordinator_count

        FROM events e

        ORDER BY
            e.event_date DESC,
            e.event_name ASC
        """
    )

    attendance_report = fetch_all(
        """
        SELECT
            u.id AS student_id,
            u.name,
            u.roll_no,
            d.code AS department_code,

            COUNT(a.id) AS total_classes,

            SUM(
                CASE
                    WHEN a.attendance_status = 'present'
                    THEN 1 ELSE 0
                END
            ) AS present_count,

            SUM(
                CASE
                    WHEN a.attendance_status = 'absent'
                    THEN 1 ELSE 0
                END
            ) AS absent_count,

            SUM(
                CASE
                    WHEN a.attendance_status = 'late'
                    THEN 1 ELSE 0
                END
            ) AS late_count

        FROM users u

        LEFT JOIN departments d
            ON d.id = u.department_id

        LEFT JOIN attendance a
            ON a.student_id = u.id

        WHERE u.role = 'student'

        GROUP BY
            u.id,
            u.name,
            u.roll_no,
            d.code

        ORDER BY
            u.roll_no ASC,
            u.name ASC
        """
    )

    verification_report = fetch_all(
        """
        SELECT
            e.event_name,

            COUNT(ev.id) AS total_attempts,

            SUM(
                CASE
                    WHEN ev.verification_status = 'verified'
                    THEN 1 ELSE 0
                END
            ) AS successful_verifications,

            SUM(
                CASE
                    WHEN ev.qr_verified = 1
                    THEN 1 ELSE 0
                END
            ) AS qr_verified_count,

            SUM(
                CASE
                    WHEN ev.face_verified = 1
                    THEN 1 ELSE 0
                END
            ) AS face_verified_count

        FROM events e

        LEFT JOIN event_verifications ev
            ON ev.event_id = e.id

        GROUP BY
            e.id,
            e.event_name

        ORDER BY
            e.event_date DESC
        """
    )

    return render_template(
        "admin/reports.html",
        event_report=event_report,
        attendance_report=attendance_report,
        verification_report=verification_report,
    )


# ============================================================
# HELPER
# ============================================================

def request_user_id():
    """
    Return the currently logged-in admin user id.

    Kept as a small helper so event creation has one clear
    source for created_by.
    """

    from flask import session

    return session.get("user_id")