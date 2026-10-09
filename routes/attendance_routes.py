from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from services import attendance_service
from utils.decorators import student_required, teacher_required


attendance_bp = Blueprint(
    "attendance",
    __name__,
    url_prefix="/attendance",
)


# ============================================================
# TEACHER — ATTENDANCE DASHBOARD
# ============================================================

@attendance_bp.route("/teacher")
@teacher_required
def teacher_attendance():
    """
    Show the logged-in teacher's academic lectures.

    Event verification is intentionally NOT used to mark
    academic attendance automatically.
    """
    teacher_id = session["user_id"]

    lectures = attendance_service.get_teacher_lectures(
        teacher_id=teacher_id
    )

    return render_template(
        "teacher/attendance.html",
        lectures=lectures,
    )


# ============================================================
# TEACHER — SINGLE LECTURE ATTENDANCE
# ============================================================

@attendance_bp.route("/lecture/<int:lecture_id>")
@teacher_required
def lecture_attendance(lecture_id):
    """
    Open attendance sheet for one lecture.

    Only the teacher assigned to the lecture can access it.
    """
    teacher_id = session["user_id"]

    lecture = attendance_service.get_lecture_for_teacher(
        lecture_id=lecture_id,
        teacher_id=teacher_id,
    )

    if not lecture:
        flash(
            "Lecture not found or you are not assigned to this lecture.",
            "danger",
        )
        return redirect(url_for("attendance.teacher_attendance"))

    students = attendance_service.get_lecture_students(
        lecture_id=lecture_id
    )

    attendance_records = attendance_service.get_lecture_attendance(
        lecture_id=lecture_id
    )

    # Event-verified students are shown as information only.
    # They are NEVER automatically marked present.
    event_verified_students = (
        attendance_service.get_event_verified_students_for_lecture(
            lecture_id=lecture_id
        )
    )

    return render_template(
        "teacher/attendance.html",
        lecture=lecture,
        students=students,
        attendance_records=attendance_records,
        event_verified_students=event_verified_students,
    )


# ============================================================
# TEACHER — MARK ONE STUDENT
# ============================================================

@attendance_bp.route("/lecture/<int:lecture_id>/mark", methods=["POST"])
@teacher_required
def mark_attendance(lecture_id):
    """
    Manually mark one student's academic attendance.

    Allowed values:
        present
        absent
        late
    """
    teacher_id = session["user_id"]

    lecture = attendance_service.get_lecture_for_teacher(
        lecture_id=lecture_id,
        teacher_id=teacher_id,
    )

    if not lecture:
        flash(
            "Lecture not found or you are not assigned to this lecture.",
            "danger",
        )
        return redirect(url_for("attendance.teacher_attendance"))

    student_id = request.form.get("student_id", type=int)
    attendance_status = (
        request.form.get("attendance_status", "")
        .strip()
        .lower()
    )

    allowed_statuses = {"present", "absent", "late"}

    if not student_id:
        flash("Student selection is required.", "warning")
        return redirect(
            url_for(
                "attendance.lecture_attendance",
                lecture_id=lecture_id,
            )
        )

    if attendance_status not in allowed_statuses:
        flash("Invalid attendance status.", "warning")
        return redirect(
            url_for(
                "attendance.lecture_attendance",
                lecture_id=lecture_id,
            )
        )

    result = attendance_service.mark_student_attendance(
        lecture_id=lecture_id,
        student_id=student_id,
        attendance_status=attendance_status,
        marked_by=teacher_id,
    )

    if result.get("success"):
        flash(
            result.get(
                "message",
                "Attendance marked successfully.",
            ),
            "success",
        )
    else:
        flash(
            result.get(
                "message",
                "Unable to mark attendance.",
            ),
            "danger",
        )

    return redirect(
        url_for(
            "attendance.lecture_attendance",
            lecture_id=lecture_id,
        )
    )


# ============================================================
# TEACHER — BULK ATTENDANCE
# ============================================================

@attendance_bp.route(
    "/lecture/<int:lecture_id>/bulk-mark",
    methods=["POST"],
)
@teacher_required
def bulk_mark_attendance(lecture_id):
    """
    Mark attendance for multiple students at once.

    The teacher submits a dictionary-like form:
        attendance[student_id] = present/absent/late

    This remains completely manual.
    """
    teacher_id = session["user_id"]

    lecture = attendance_service.get_lecture_for_teacher(
        lecture_id=lecture_id,
        teacher_id=teacher_id,
    )

    if not lecture:
        flash(
            "Lecture not found or you are not assigned to this lecture.",
            "danger",
        )
        return redirect(url_for("attendance.teacher_attendance"))

    submitted_attendance = {}

    for key, value in request.form.items():
        if not key.startswith("attendance["):
            continue

        student_id_text = key[
            len("attendance["):-1
        ]

        try:
            student_id = int(student_id_text)
        except (TypeError, ValueError):
            continue

        attendance_status = str(value).strip().lower()

        if attendance_status in {
            "present",
            "absent",
            "late",
        }:
            submitted_attendance[student_id] = attendance_status

    if not submitted_attendance:
        flash(
            "No attendance records were submitted.",
            "warning",
        )
        return redirect(
            url_for(
                "attendance.lecture_attendance",
                lecture_id=lecture_id,
            )
        )

    result = attendance_service.mark_bulk_attendance(
        lecture_id=lecture_id,
        attendance_data=submitted_attendance,
        marked_by=teacher_id,
    )

    if result.get("success"):
        flash(
            result.get(
                "message",
                "Attendance updated successfully.",
            ),
            "success",
        )
    else:
        flash(
            result.get(
                "message",
                "Unable to update attendance.",
            ),
            "danger",
        )

    return redirect(
        url_for(
            "attendance.lecture_attendance",
            lecture_id=lecture_id,
        )
    )


# ============================================================
# STUDENT — MY ATTENDANCE
# ============================================================

@attendance_bp.route("/my")
@student_required
def my_attendance():
    """
    Student's academic attendance history.

    Event verification is displayed separately and does not
    change these attendance records.
    """
    student_id = session["user_id"]

    summary = attendance_service.get_student_attendance_summary(
        student_id=student_id
    )

    history = attendance_service.get_student_attendance_history(
        student_id=student_id
    )

    return render_template(
        "student/dashboard.html",
        attendance_summary=summary,
        attendance_history=history,
    )


# ============================================================
# TEACHER — VERIFIED STUDENTS FOR A LECTURE
# ============================================================

@attendance_bp.route(
    "/lecture/<int:lecture_id>/event-verified"
)
@teacher_required
def lecture_event_verified_students(lecture_id):
    """
    Show students belonging to this lecture who have verified
    their presence at an event.

    This is INFORMATION ONLY.

    It does NOT create or modify academic attendance.
    """
    teacher_id = session["user_id"]

    lecture = attendance_service.get_lecture_for_teacher(
        lecture_id=lecture_id,
        teacher_id=teacher_id,
    )

    if not lecture:
        flash(
            "Lecture not found or you are not assigned to this lecture.",
            "danger",
        )
        return redirect(url_for("attendance.teacher_attendance"))

    students = (
        attendance_service.get_event_verified_students_for_lecture(
            lecture_id=lecture_id
        )
    )

    return render_template(
        "teacher/attendance.html",
        lecture=lecture,
        students=students,
        event_verified_students=students,
        attendance_records=attendance_service.get_lecture_attendance(
            lecture_id=lecture_id
        ),
    )