from pathlib import Path
import os

from flask import Flask, render_template, session, redirect, url_for

from database.db import init_database_directory
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.teacher_routes import teacher_bp
from routes.admin_routes import admin_bp
from routes.event_routes import event_bp
from routes.verification_routes import verification_bp
from routes.attendance_routes import attendance_bp


# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent


# =========================================================
# Flask Application
# =========================================================

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


# =========================================================
# Configuration
# =========================================================

app.config.update(
    SECRET_KEY=os.environ.get(
        "EVENTSYNC_SECRET_KEY",
        "eventsync-hackathon-secret-change-later",
    ),
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,
    JSON_SORT_KEYS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)


# =========================================================
# Prepare required directories
# =========================================================

init_database_directory()

(BASE_DIR / "static").mkdir(
    parents=True,
    exist_ok=True,
)

(BASE_DIR / "static" / "images").mkdir(
    parents=True,
    exist_ok=True,
)

(BASE_DIR / "static" / "uploads").mkdir(
    parents=True,
    exist_ok=True,
)

(BASE_DIR / "static" / "uploads" / "faces").mkdir(
    parents=True,
    exist_ok=True,
)

(BASE_DIR / "static" / "generated").mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# Blueprints
# =========================================================

app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(teacher_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(event_bp)
app.register_blueprint(verification_bp)
app.register_blueprint(attendance_bp)


# =========================================================
# Context Processor
# =========================================================

@app.context_processor
def inject_global_context():
    """
    Makes commonly used session information available
    to every template.
    """

    return {
        "current_user_id": session.get("user_id"),
        "current_user_role": session.get("user_role"),
        "current_user_name": session.get("user_name"),
        "current_user_email": session.get("email"),
    }


# =========================================================
# Public Home Page
# =========================================================

@app.route("/")
def index():
    return render_template("index.html")


# =========================================================
# Health Check
# =========================================================

@app.route("/health")
def health():
    return {
        "success": True,
        "application": "EventSync",
        "status": "running",
    }


# =========================================================
# Smart Dashboard Redirect
# =========================================================

@app.route("/dashboard")
def dashboard_redirect():
    """
    Sends the logged-in user to the correct dashboard.
    """

    role = session.get("user_role")

    if role == "student":
        return redirect(url_for("student.dashboard"))

    if role == "teacher":
        return redirect(url_for("teacher.dashboard"))

    if role == "admin":
        return redirect(url_for("admin.dashboard"))

    return redirect(url_for("auth.login"))


# =========================================================
# Error Handlers
# =========================================================

@app.errorhandler(404)
def page_not_found(error):
    return (
        render_template(
            "404.html",
            error=error,
        ),
        404,
    )


@app.errorhandler(500)
def internal_server_error(error):
    return (
        render_template(
            "500.html",
            error=error,
        ),
        500,
    )


@app.errorhandler(413)
def request_entity_too_large(error):
    return (
        """
        <h1>File Too Large</h1>
        <p>The uploaded file is larger than the allowed 10 MB limit.</p>
        """,
        413,
    )


# =========================================================
# Application Startup
# =========================================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )