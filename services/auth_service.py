"""
EventSync Authentication Service

Handles:
- Password hashing and verification
- User authentication
- Student registration
- User lookup
- Department lookup
- Session-ready user information
"""

from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from database.db import execute_write, fetch_all, fetch_one
from utils.helpers import (
    clean_text,
    is_valid_email,
    normalize_email,
    normalize_roll_number,
    save_face_image,
)


def hash_password(password: str) -> str:
    """
    Create a secure password hash.
    """
    if not password:
        raise ValueError("Password is required.")

    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a plain-text password against a stored password hash.
    """
    if not password or not password_hash:
        return False

    try:
        return check_password_hash(password_hash, password)
    except (ValueError, TypeError):
        return False


def get_user_by_id(user_id: int):
    """
    Return an active user by ID.
    """
    return fetch_one(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.password_hash,
            u.role,
            u.department_id,
            u.semester,
            u.section,
            u.roll_no,
            u.face_image_path,
            u.is_active,
            u.created_at,
            d.code AS department_code,
            d.name AS department_name
        FROM users u
        LEFT JOIN departments d
            ON d.id = u.department_id
        WHERE u.id = ?
          AND u.is_active = 1
        LIMIT 1
        """,
        (user_id,),
    )


def get_user_by_email(email: str):
    """
    Return an active user by email address.
    """
    normalized_email = normalize_email(email)

    if not normalized_email:
        return None

    return fetch_one(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.password_hash,
            u.role,
            u.department_id,
            u.semester,
            u.section,
            u.roll_no,
            u.face_image_path,
            u.is_active,
            u.created_at,
            d.code AS department_code,
            d.name AS department_name
        FROM users u
        LEFT JOIN departments d
            ON d.id = u.department_id
        WHERE LOWER(u.email) = ?
          AND u.is_active = 1
        LIMIT 1
        """,
        (normalized_email,),
    )


def get_user_by_roll_number(roll_no: str):
    """
    Return an active student by roll number.
    """
    normalized_roll_no = normalize_roll_number(roll_no)

    if not normalized_roll_no:
        return None

    return fetch_one(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.password_hash,
            u.role,
            u.department_id,
            u.semester,
            u.section,
            u.roll_no,
            u.face_image_path,
            u.is_active,
            u.created_at,
            d.code AS department_code,
            d.name AS department_name
        FROM users u
        LEFT JOIN departments d
            ON d.id = u.department_id
        WHERE UPPER(u.roll_no) = ?
          AND u.is_active = 1
        LIMIT 1
        """,
        (normalized_roll_no,),
    )


def get_departments():
    """
    Return all active departments for registration/forms.
    """
    return fetch_all(
        """
        SELECT
            id,
            code,
            name
        FROM departments
        WHERE is_active = 1
        ORDER BY name ASC
        """
    )


def authenticate_user(email: str, password: str):
    """
    Authenticate any active EventSync user.

    Returns:
        User row on success.
        None on failure.
    """
    user = get_user_by_email(email)

    if user is None:
        return None

    if not verify_password(password, user["password_hash"]):
        return None

    return user


def authenticate_student(email: str, password: str):
    """
    Authenticate an active student.
    """
    user = authenticate_user(email, password)

    if user is None or user["role"] != "student":
        return None

    return user


def authenticate_teacher(email: str, password: str):
    """
    Authenticate an active teacher.
    """
    user = authenticate_user(email, password)

    if user is None or user["role"] != "teacher":
        return None

    return user


def authenticate_admin(email: str, password: str):
    """
    Authenticate an active administrator.
    """
    user = authenticate_user(email, password)

    if user is None or user["role"] != "admin":
        return None

    return user


def register_student(
    name: str,
    email: str,
    password: str,
    department_id: int | str,
    semester: int | str,
    section: str,
    roll_no: str,
    face_image_data: str | None = None,
):
    """
    Register a new student account.

    Students are never pre-seeded. Every student account is
    created through this registration workflow.

    The participation role is intentionally NOT stored here.
    Participant/student-coordinator is an event-level decision
    and is handled when the student registers for an event.

    Returns:
        {
            "success": True,
            "user_id": <new user id>,
            "message": <success message>
        }

    Raises:
        ValueError for validation or duplicate-account errors.
    """

    name = clean_text(name)
    email = normalize_email(email)
    section = clean_text(section)
    roll_no = normalize_roll_number(roll_no)

    try:
        department_id = int(department_id)
    except (TypeError, ValueError):
        raise ValueError("Please select a valid department.")

    try:
        semester = int(semester)
    except (TypeError, ValueError):
        raise ValueError("Please select a valid semester.")

    if not name:
        raise ValueError("Full name is required.")

    if len(name) < 2:
        raise ValueError("Please enter a valid full name.")

    if not is_valid_email(email):
        raise ValueError("Please enter a valid email address.")

    if not password:
        raise ValueError("Password is required.")

    if len(password) < 6:
        raise ValueError("Password must contain at least 6 characters.")

    if semester < 1 or semester > 12:
        raise ValueError("Semester must be between 1 and 12.")

    if not section:
        raise ValueError("Section is required.")

    if not roll_no:
        raise ValueError("Roll number is required.")

    existing_email = fetch_one(
        """
        SELECT id
        FROM users
        WHERE LOWER(email) = ?
        LIMIT 1
        """,
        (email,),
    )

    if existing_email is not None:
        raise ValueError("An account with this email already exists.")

    existing_roll = fetch_one(
        """
        SELECT id
        FROM users
        WHERE UPPER(roll_no) = ?
        LIMIT 1
        """,
        (roll_no,),
    )

    if existing_roll is not None:
        raise ValueError("This roll number is already registered.")

    department = fetch_one(
        """
        SELECT id
        FROM departments
        WHERE id = ?
          AND is_active = 1
        LIMIT 1
        """,
        (department_id,),
    )

    if department is None:
        raise ValueError("Selected department is not available.")

    face_image_path = None

    if face_image_data:
        try:
            face_image_path = save_face_image(face_image_data)
        except (ValueError, OSError) as error:
            raise ValueError(
                f"Face image could not be saved: {error}"
            ) from error

    password_hash = hash_password(password)

    try:
        user_id = execute_write(
            """
            INSERT INTO users (
                name,
                email,
                password_hash,
                role,
                department_id,
                semester,
                section,
                roll_no,
                face_image_path,
                is_active
            )
            VALUES (?, ?, ?, 'student', ?, ?, ?, ?, ?, 1)
            """,
            (
                name,
                email,
                password_hash,
                department_id,
                semester,
                section,
                roll_no,
                face_image_path,
            ),
        )
    except Exception:
        # If the database insert fails after the face image was saved,
        # the image is intentionally left harmlessly on disk rather
        # than risking deletion of a file belonging to another request.
        raise

    return {
        "success": True,
        "user_id": user_id,
        "message": "Student account created successfully.",
    }


def get_user_profile(user_id: int):
    """
    Return profile information without exposing the password hash.
    """
    user = get_user_by_id(user_id)

    if user is None:
        return None

    profile = dict(user)
    profile.pop("password_hash", None)

    return profile


def user_exists_by_email(email: str) -> bool:
    """
    Check whether an account already exists for an email.
    """
    normalized_email = normalize_email(email)

    if not normalized_email:
        return False

    row = fetch_one(
        """
        SELECT id
        FROM users
        WHERE LOWER(email) = ?
        LIMIT 1
        """,
        (normalized_email,),
    )

    return row is not None


def student_exists_by_roll_number(roll_no: str) -> bool:
    """
    Check whether a student roll number already exists.
    """
    normalized_roll_no = normalize_roll_number(roll_no)

    if not normalized_roll_no:
        return False

    row = fetch_one(
        """
        SELECT id
        FROM users
        WHERE UPPER(roll_no) = ?
          AND role = 'student'
        LIMIT 1
        """,
        (normalized_roll_no,),
    )

    return row is not None


def get_users_by_role(role: str):
    """
    Return active users belonging to a specific role.
    """
    normalized_role = clean_text(role).lower()

    if normalized_role not in {"student", "teacher", "admin"}:
        return []

    return fetch_all(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.role,
            u.department_id,
            u.semester,
            u.section,
            u.roll_no,
            u.face_image_path,
            u.is_active,
            u.created_at,
            d.code AS department_code,
            d.name AS department_name
        FROM users u
        LEFT JOIN departments d
            ON d.id = u.department_id
        WHERE u.role = ?
          AND u.is_active = 1
        ORDER BY u.name ASC
        """,
        (normalized_role,),
    )


def get_students():
    """
    Return all active students.
    """
    return get_users_by_role("student")


def get_teachers():
    """
    Return all active teachers.
    """
    return get_users_by_role("teacher")


def get_admins():
    """
    Return all active administrators.
    """
    return get_users_by_role("admin")


def get_user_summary(user_id: int) -> dict[str, Any] | None:
    """
    Return a small safe user object suitable for templates/API responses.
    """
    user = get_user_by_id(user_id)

    if user is None:
        return None

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "department_id": user["department_id"],
        "department_code": user["department_code"],
        "department_name": user["department_name"],
        "semester": user["semester"],
        "section": user["section"],
        "roll_no": user["roll_no"],
        "face_image_path": user["face_image_path"],
        "created_at": user["created_at"],
    }