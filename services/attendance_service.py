from datetime import datetime

from database.db import (
    execute_write,
    fetch_all,
    fetch_one,
)


# ============================================================
# CONSTANTS
# ============================================================

ATTENDANCE_STATUSES = {
    "present",
    "absent",
    "late",
}


# ============================================================
# TEACHER LECTURES
# ============================================================

def get_teacher_lectures(teacher_id):
    """
    Return all active lectures assigned to a teacher.

    These are academic lectures only.
    Event coordination is handled separately.
    """
    return fetch_all(
        """
        SELECT
            l.id,
            l.teacher_id,
            l.subject_id,
            l.department_id,
            l.semester,
            l.section,
            l.lecture_date,
            l.start_time,
            l.end_time,
            l.room,
            l.is_active,
            s.subject_code,
            s.subject_name,
            d.code AS department_code,
            d.name AS department_name
        FROM lectures l
        JOIN subjects s
            ON s.id = l.subject_id
        LEFT JOIN departments d
            ON d.id = l.department_id
        WHERE l.teacher_id = ?
          AND l.is_active = 1
        ORDER BY
            l.lecture_date DESC,
            l.start_time DESC,
            s.subject_name ASC
        """,
        (teacher_id,),
    )


# ============================================================
# SINGLE LECTURE
# ============================================================

def get_lecture_for_teacher(lecture_id, teacher_id):
    """
    Return a lecture only when it belongs to the logged-in teacher.
    """
    return fetch_one(
        """
        SELECT
            l.id,
            l.teacher_id,
            l.subject_id,
            l.department_id,
            l.semester,
            l.section,
            l.lecture_date,
            l.start_time,
            l.end_time,
            l.room,
            l.is_active,
            s.subject_code,
            s.subject_name,
            d.code AS department_code,
            d.name AS department_name
        FROM lectures l
        JOIN subjects s
            ON s.id = l.subject_id
        LEFT JOIN departments d
            ON d.id = l.department_id
        WHERE l.id = ?
          AND l.teacher_id = ?
          AND l.is_active = 1
        LIMIT 1
        """,
        (lecture_id, teacher_id),
    )


# ============================================================
# STUDENTS FOR A LECTURE
# ============================================================

def get_lecture_students(lecture_id):
    """
    Get active students belonging to the lecture's:

        department
        semester
        section

    Event registration is NOT used to determine academic
    attendance eligibility.
    """
    lecture = fetch_one(
        """
        SELECT
            department_id,
            semester,
            section
        FROM lectures
        WHERE id = ?
          AND is_active = 1
        LIMIT 1
        """,
        (lecture_id,),
    )

    if not lecture:
        return []

    return fetch_all(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.roll_no,
            u.department_id,
            u.semester,
            u.section,
            d.code AS department_code,
            d.name AS department_name
        FROM users u
        LEFT JOIN departments d
            ON d.id = u.department_id
        WHERE u.role = 'student'
          AND u.is_active = 1
          AND u.department_id = ?
          AND u.semester = ?
          AND (
                u.section = ?
                OR (
                    u.section IS NULL
                    AND ? IS NULL
                )
          )
        ORDER BY
            CASE
                WHEN u.roll_no IS NULL THEN 1
                ELSE 0
            END,
            u.roll_no ASC,
            u.name ASC
        """,
        (
            lecture["department_id"],
            lecture["semester"],
            lecture["section"],
            lecture["section"],
        ),
    )


# ============================================================
# EXISTING ATTENDANCE
# ============================================================

def get_lecture_attendance(lecture_id):
    """
    Return attendance records for one lecture.

    A dictionary keyed by student_id is returned so templates
    can easily find the current attendance status.
    """
    rows = fetch_all(
        """
        SELECT
            a.id,
            a.lecture_id,
            a.student_id,
            a.attendance_status,
            a.marked_by,
            a.marked_at,
            u.name AS student_name,
            u.roll_no
        FROM attendance a
        JOIN users u
            ON u.id = a.student_id
        WHERE a.lecture_id = ?
        ORDER BY
            CASE
                WHEN u.roll_no IS NULL THEN 1
                ELSE 0
            END,
            u.roll_no ASC,
            u.name ASC
        """,
        (lecture_id,),
    )

    return {
        row["student_id"]: row
        for row in rows
    }


# ============================================================
# VERIFY STUDENT BELONGS TO LECTURE
# ============================================================

def _student_belongs_to_lecture(lecture_id, student_id):
    """
    Verify that a student belongs to the lecture's
    department/semester/section.
    """
    return fetch_one(
        """
        SELECT
            u.id
        FROM users u
        JOIN lectures l
            ON l.department_id = u.department_id
            AND l.semester = u.semester
            AND (
                l.section = u.section
                OR (
                    l.section IS NULL
                    AND u.section IS NULL
                )
            )
        WHERE l.id = ?
          AND u.id = ?
          AND l.is_active = 1
          AND u.role = 'student'
          AND u.is_active = 1
        LIMIT 1
        """,
        (lecture_id, student_id),
    ) is not None


# ============================================================
# MARK ONE STUDENT
# ============================================================

def mark_student_attendance(
    lecture_id,
    student_id,
    attendance_status,
    marked_by,
):
    """
    Create or update one academic attendance record.

    This function never checks event verification and never
    automatically marks a student present because of an event.
    """
    attendance_status = str(
        attendance_status or ""
    ).strip().lower()

    if attendance_status not in ATTENDANCE_STATUSES:
        return {
            "success": False,
            "message": "Invalid attendance status.",
        }

    lecture = fetch_one(
        """
        SELECT
            id,
            teacher_id
        FROM lectures
        WHERE id = ?
          AND is_active = 1
        LIMIT 1
        """,
        (lecture_id,),
    )

    if not lecture:
        return {
            "success": False,
            "message": "Lecture not found.",
        }

    if lecture["teacher_id"] != marked_by:
        return {
            "success": False,
            "message": "You are not assigned to this lecture.",
        }

    if not _student_belongs_to_lecture(
        lecture_id,
        student_id,
    ):
        return {
            "success": False,
            "message": "Student does not belong to this lecture.",
        }

    existing = fetch_one(
        """
        SELECT
            id
        FROM attendance
        WHERE lecture_id = ?
          AND student_id = ?
        LIMIT 1
        """,
        (lecture_id, student_id),
    )

    marked_at = datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    if existing:
        execute_write(
            """
            UPDATE attendance
            SET
                attendance_status = ?,
                marked_by = ?,
                marked_at = ?
            WHERE id = ?
            """,
            (
                attendance_status,
                marked_by,
                marked_at,
                existing["id"],
            ),
        )

        return {
            "success": True,
            "message": "Attendance updated successfully.",
            "attendance_id": existing["id"],
            "action": "updated",
        }

    attendance_id = execute_write(
        """
        INSERT INTO attendance (
            lecture_id,
            student_id,
            attendance_status,
            marked_by,
            marked_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            lecture_id,
            student_id,
            attendance_status,
            marked_by,
            marked_at,
        ),
    )

    return {
        "success": True,
        "message": "Attendance marked successfully.",
        "attendance_id": attendance_id,
        "action": "created",
    }


# ============================================================
# BULK ATTENDANCE
# ============================================================

def mark_bulk_attendance(
    lecture_id,
    attendance_data,
    marked_by,
):
    """
    Mark attendance for multiple students.

    attendance_data format:

        {
            student_id: "present",
            student_id: "absent",
            student_id: "late"
        }

    Invalid students/statuses are skipped.
    """
    if not isinstance(attendance_data, dict):
        return {
            "success": False,
            "message": "Invalid attendance data.",
        }

    lecture = fetch_one(
        """
        SELECT
            id,
            teacher_id
        FROM lectures
        WHERE id = ?
          AND is_active = 1
        LIMIT 1
        """,
        (lecture_id,),
    )

    if not lecture:
        return {
            "success": False,
            "message": "Lecture not found.",
        }

    if lecture["teacher_id"] != marked_by:
        return {
            "success": False,
            "message": "You are not assigned to this lecture.",
        }

    success_count = 0
    failed_count = 0

    for student_id, status in attendance_data.items():
        try:
            student_id = int(student_id)
        except (TypeError, ValueError):
            failed_count += 1
            continue

        result = mark_student_attendance(
            lecture_id=lecture_id,
            student_id=student_id,
            attendance_status=status,
            marked_by=marked_by,
        )

        if result.get("success"):
            success_count += 1
        else:
            failed_count += 1

    if success_count == 0:
        return {
            "success": False,
            "message": "No attendance records were updated.",
            "updated": 0,
            "failed": failed_count,
        }

    message = (
        f"{success_count} attendance record"
        f"{'s' if success_count != 1 else ''} "
        "updated successfully."
    )

    if failed_count:
        message += (
            f" {failed_count} record"
            f"{'s' if failed_count != 1 else ''} "
            "could not be updated."
        )

    return {
        "success": True,
        "message": message,
        "updated": success_count,
        "failed": failed_count,
    }


# ============================================================
# STUDENT ATTENDANCE SUMMARY
# ============================================================

def get_student_attendance_summary(student_id):
    """
    Return overall academic attendance statistics for a student.
    """
    totals = fetch_one(
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
        totals["total_classes"] or 0
    )

    present_count = int(
        totals["present_count"] or 0
    )

    absent_count = int(
        totals["absent_count"] or 0
    )

    late_count = int(
        totals["late_count"] or 0
    )

    # For the percentage, late attendance is treated as attended.
    attended_count = present_count + late_count

    percentage = (
        round(
            (attended_count / total_classes) * 100,
            2,
        )
        if total_classes
        else 0
    )

    return {
        "total_classes": total_classes,
        "present_count": present_count,
        "absent_count": absent_count,
        "late_count": late_count,
        "attended_count": attended_count,
        "attendance_percentage": percentage,
    }


# ============================================================
# STUDENT ATTENDANCE HISTORY
# ============================================================

def get_student_attendance_history(student_id):
    """
    Return the student's academic attendance history.
    """
    return fetch_all(
        """
        SELECT
            a.id,
            a.lecture_id,
            a.student_id,
            a.attendance_status,
            a.marked_by,
            a.marked_at,
            l.lecture_date,
            l.start_time,
            l.end_time,
            l.room,
            l.section,
            l.semester,
            s.subject_code,
            s.subject_name,
            u.name AS marked_by_name
        FROM attendance a
        JOIN lectures l
            ON l.id = a.lecture_id
        JOIN subjects s
            ON s.id = l.subject_id
        LEFT JOIN users u
            ON u.id = a.marked_by
        WHERE a.student_id = ?
        ORDER BY
            l.lecture_date DESC,
            l.start_time DESC
        """,
        (student_id,),
    )


# ============================================================
# EVENT-VERIFIED STUDENTS FOR LECTURE
# ============================================================

def get_event_verified_students_for_lecture(lecture_id):
    """
    Return students belonging to a lecture who have successfully
    verified themselves at an event.

    IMPORTANT:

    This is informational only.

    It does NOT create attendance records.
    It does NOT mark students present.
    """
    return fetch_all(
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

            u.name AS student_name,
            u.roll_no,
            u.email,

            e.event_name,
            e.event_category,
            e.event_type,
            e.event_date,
            e.start_time AS event_start_time,
            e.end_time AS event_end_time,
            e.venue

        FROM event_verifications ev

        JOIN users u
            ON u.id = ev.student_id

        JOIN events e
            ON e.id = ev.event_id

        JOIN lectures l
            ON l.id = ?

        WHERE ev.verification_status = 'verified'
          AND ev.qr_verified = 1
          AND ev.face_verified = 1

          AND u.role = 'student'
          AND u.is_active = 1

          AND u.department_id = l.department_id
          AND u.semester = l.semester
          AND (
                u.section = l.section
                OR (
                    u.section IS NULL
                    AND l.section IS NULL
                )
          )

        ORDER BY
            ev.verified_at DESC,
            u.roll_no ASC,
            u.name ASC
        """,
        (lecture_id,),
    )


# ============================================================
# SINGLE STUDENT ATTENDANCE LOOKUP
# ============================================================

def get_student_lecture_attendance(
    student_id,
    lecture_id,
):
    """
    Return one student's attendance record for one lecture.
    """
    return fetch_one(
        """
        SELECT
            a.id,
            a.lecture_id,
            a.student_id,
            a.attendance_status,
            a.marked_by,
            a.marked_at
        FROM attendance a
        WHERE a.student_id = ?
          AND a.lecture_id = ?
        LIMIT 1
        """,
        (student_id, lecture_id),
    )


# ============================================================
# ATTENDANCE COUNTS FOR A LECTURE
# ============================================================

def get_lecture_attendance_summary(lecture_id):
    """
    Return attendance counts for one lecture.
    """
    row = fetch_one(
        """
        SELECT
            COUNT(*) AS total_marked,
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
        WHERE lecture_id = ?
        """,
        (lecture_id,),
    )

    return {
        "total_marked": int(
            row["total_marked"] or 0
        ),
        "present_count": int(
            row["present_count"] or 0
        ),
        "absent_count": int(
            row["absent_count"] or 0
        ),
        "late_count": int(
            row["late_count"] or 0
        ),
    }