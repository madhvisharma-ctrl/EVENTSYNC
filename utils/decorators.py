"""
EventSync Authentication and Authorization Decorators

Provides reusable decorators for:
- Login protection
- Role-based access control
"""

from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view_function):
    """
    Require the user to be logged in before accessing a route.
    """

    @wraps(view_function)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))

        return view_function(*args, **kwargs)

    return wrapped_view


def role_required(*allowed_roles):
    """
    Require the logged-in user to have one of the specified roles.

    Example:
        @role_required("admin")
        @role_required("teacher", "admin")
    """

    normalized_roles = {
        str(role).strip().lower()
        for role in allowed_roles
        if role is not None
    }

    def decorator(view_function):
        @wraps(view_function)
        def wrapped_view(*args, **kwargs):
            user_id = session.get("user_id")
            user_role = str(session.get("user_role", "")).strip().lower()

            if not user_id:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login"))

            if user_role not in normalized_roles:
                flash(
                    "You do not have permission to access this page.",
                    "danger",
                )

                if user_role == "admin":
                    return redirect(url_for("admin.dashboard"))

                if user_role == "teacher":
                    return redirect(url_for("teacher.dashboard"))

                if user_role == "student":
                    return redirect(url_for("student.dashboard"))

                session.clear()
                return redirect(url_for("auth.login"))

            return view_function(*args, **kwargs)

        return wrapped_view

    return decorator


def student_required(view_function):
    """
    Allow access only to logged-in students.
    """
    return role_required("student")(view_function)


def teacher_required(view_function):
    """
    Allow access only to logged-in teachers.
    """
    return role_required("teacher")(view_function)


def admin_required(view_function):
    """
    Allow access only to logged-in administrators.
    """
    return role_required("admin")(view_function)


def teacher_or_admin_required(view_function):
    """
    Allow access to teachers or administrators.
    """
    return role_required("teacher", "admin")(view_function)


def student_or_teacher_required(view_function):
    """
    Allow access to students or teachers.
    """
    return role_required("student", "teacher")(view_function)


def any_authenticated_user(view_function):
    """
    Allow access to any authenticated EventSync user.
    """
    return login_required(view_function)