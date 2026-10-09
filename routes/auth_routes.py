from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from services.auth_service import (
    authenticate_user,
    register_student,
    get_user_by_id
)


auth_bp = Blueprint("auth", __name__)


def redirect_by_role(role):
    """Redirect logged-in user to the correct dashboard."""

    if role == "student":
        return redirect(url_for("student.dashboard"))

    if role == "teacher":
        return redirect(url_for("teacher.dashboard"))

    if role == "admin":
        return redirect(url_for("admin.dashboard"))

    session.clear()
    flash("Invalid user role.", "error")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page for Student, Teacher and Admin."""

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("login.html")

        user = authenticate_user(email, password)

        if user is None:
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        if not user["is_active"]:
            flash("Your account is inactive. Please contact the administrator.", "error")
            return render_template("login.html")

        # Store logged-in user information
        session.clear()

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        session["email"] = user["email"]
        session["user_role"] = user["role"]

        flash(f"Welcome, {user['name']}!", "success")

        return redirect_by_role(user["role"])

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Public student registration.

    Coordinator is NOT a separate account.
    A student can later become a coordinator for a particular event.
    """

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        department = request.form.get("department", "").strip()
        semester = request.form.get("semester", "").strip()
        section = request.form.get("section", "").strip()
        roll_no = request.form.get("roll_no", "").strip()

        # Basic validation
        if not name:
            flash("Please enter your name.", "error")
            return render_template("register.html")

        if not email:
            flash("Please enter your email.", "error")
            return render_template("register.html")

        if not password:
            flash("Please enter a password.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("register.html")

        if not department:
            flash("Please enter your department.", "error")
            return render_template("register.html")

        if not semester:
            flash("Please enter your semester.", "error")
            return render_template("register.html")

        if not section:
            flash("Please enter your section.", "error")
            return render_template("register.html")

        if not roll_no:
            flash("Please enter your university roll number.", "error")
            return render_template("register.html")

        try:
            user_id = register_student(
                name=name,
                email=email,
                password=password,
                department=department,
                semester=semester,
                section=section,
                roll_no=roll_no
            )

            if user_id:
                flash(
                    "Registration successful. You can now log in.",
                    "success"
                )
                return redirect(url_for("auth.login"))

            flash(
                "Registration could not be completed.",
                "error"
            )

        except ValueError as error:
            flash(str(error), "error")

        except Exception as error:
            print("Registration error:", error)
            flash(
                "An unexpected error occurred during registration.",
                "error"
            )

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    """Logout the currently logged-in user."""

    session.clear()

    flash("You have been logged out successfully.", "success")

    return redirect(url_for("auth.login"))


@auth_bp.route("/profile")
def profile():
    """Basic logged-in user profile route."""

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("auth.login"))

    user = get_user_by_id(user_id)

    if user is None:
        session.clear()
        flash("User account could not be found.", "error")
        return redirect(url_for("auth.login"))

    return redirect_by_role(user["role"])