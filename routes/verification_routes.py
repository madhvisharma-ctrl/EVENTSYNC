"""
EventSync Event Verification Routes

Main verification workflow:

Student
    ↓
Registered Event
    ↓
Dynamic QR
    ↓
Server-side QR Validation
    ↓
Live Camera Face Verification
    ↓
Time/Event Validation
    ↓
EVENT PRESENCE VERIFIED
    ↓
Teacher Coordinator Notification

Important:
- Event verification is separate from academic lecture attendance.
- Academic attendance is never automatically changed here.
"""

from datetime import datetime, timezone

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database.db import (
    execute_write,
    fetch_all,
    fetch_one,
)
from services.event_service import (
    get_event_by_id,
    get_event_registration,
    is_event_coordinator,
)
from services.face_service import verify_face_from_base64
from services.notification_service import (
    notify_event_coordinators,
)
from services.qr_service import (
    QR_PREFIX,
)
from utils.decorators import (
    student_required,
    teacher_required,
)
from utils.helpers import (
    get_absolute_static_path,
)


verification_bp = Blueprint(
    "verification",
    __name__,
    url_prefix="/verification",
)


def _utc_now():
    """
    Return the current timezone-aware UTC datetime.
    """
    return datetime.now(timezone.utc)


def _database_now():
    """
    Return current UTC time in SQLite-friendly format.
    """
    return _utc_now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _normalize_qr_token(token):
    """
    Normalize a QR token received from the browser.
    """
    if not token:
        return ""

    token = str(token).strip()

    if token.startswith(QR_PREFIX):
        token = token[len(QR_PREFIX):]

    return token.strip()


def _validate_qr_token_for_event(
    event_id,
    token,
):
    """
    Validate a QR token directly against the database.

    Conditions:
    - Token exists
    - Token belongs to this event
    - Token is active
    - Token has not expired
    """
    normalized_token = _normalize_qr_token(token)

    if not normalized_token:
        return None

    now = _database_now()

    return fetch_one(
        """
        SELECT
            id,
            event_id,
            token,
            generated_by,
            created_at,
            expires_at,
            is_active
        FROM qr_tokens
        WHERE event_id = ?
          AND token = ?
          AND is_active = 1
          AND expires_at > ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (
            event_id,
            normalized_token,
            now,
        ),
    )


def _is_event_time_valid(event):
    """
    Check whether the current date/time falls within the event window.

    This intentionally uses UTC database values because EventSync
    stores event timestamps in the same database time convention.
    """
    now = _utc_now()

    event_date = event["event_date"]
    start_time = event["start_time"]
    end_time = event["end_time"]

    if not event_date:
        return False

    try:
        event_day = datetime.strptime(
            str(event_date),
            "%Y-%m-%d",
        ).date()
    except ValueError:
        return False

    if event_day != now.date():
        return False

    if not start_time or not end_time:
        return True

    try:
        start = datetime.strptime(
            str(start_time),
            "%H:%M",
        ).time()

        end = datetime.strptime(
            str(end_time),
            "%H:%M",
        ).time()
    except ValueError:
        try:
            start = datetime.strptime(
                str(start_time),
                "%H:%M:%S",
            ).time()

            end = datetime.strptime(
                str(end_time),
                "%H:%M:%S",
            ).time()
        except ValueError:
            return False

    current_time = now.time()

    return start <= current_time <= end


def _get_existing_verification(
    event_id,
    student_id,
):
    """
    Return an existing verification record.
    """
    return fetch_one(
        """
        SELECT
            ev.id,
            ev.event_id,
            ev.student_id,
            ev.qr_token_id,
            ev.qr_verified,
            ev.face_verified,
            ev.verification_status,
            ev.confidence,
            ev.verified_at,
            ev.created_at
        FROM event_verifications ev
        WHERE ev.event_id = ?
          AND ev.student_id = ?
        LIMIT 1
        """,
        (
            event_id,
            student_id,
        ),
    )


def _save_verification(
    event_id,
    student_id,
    qr_token_id,
    qr_verified,
    face_verified,
    verification_status,
    confidence=None,
):
    """
    Insert or update an event verification record.
    """
    now = _database_now()

    existing = _get_existing_verification(
        event_id,
        student_id,
    )

    if existing is None:
        return execute_write(
            """
            INSERT INTO event_verifications (
                event_id,
                student_id,
                qr_token_id,
                qr_verified,
                face_verified,
                verification_status,
                confidence,
                verified_at,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                student_id,
                qr_token_id,
                1 if qr_verified else 0,
                1 if face_verified else 0,
                verification_status,
                confidence,
                now if verification_status == "verified"
                else None,
                now,
            ),
        )

    execute_write(
        """
        UPDATE event_verifications
        SET
            qr_token_id = ?,
            qr_verified = ?,
            face_verified = ?,
            verification_status = ?,
            confidence = ?,
            verified_at = CASE
                WHEN ? = 'verified'
                THEN ?
                ELSE verified_at
            END
        WHERE event_id = ?
          AND student_id = ?
        """,
        (
            qr_token_id,
            1 if qr_verified else 0,
            1 if face_verified else 0,
            verification_status,
            confidence,
            verification_status,
            now,
            event_id,
            student_id,
        ),
    )

    return existing["id"]


def _mark_event_registration_attended(
    event_id,
    student_id,
):
    """
    Mark the student's event registration as attended.

    This does NOT update the academic attendance table.
    """
    execute_write(
        """
        UPDATE event_registrations
        SET status = 'attended'
        WHERE event_id = ?
          AND student_id = ?
          AND status = 'registered'
        """,
        (
            event_id,
            student_id,
        ),
    )


@verification_bp.route(
    "/event/<int:event_id>",
    methods=["GET"],
)
@student_required
def verify_event_page(event_id):
    """
    Display the event verification page.
    """
    event = get_event_by_id(event_id)

    if event is None:
        from flask import abort

        abort(404)

    student_id = session.get("user_id")

    registration = get_event_registration(
        event_id=event_id,
        student_id=student_id,
    )

    if registration is None:
        flash(
            "You must register for this event before verification.",
            "warning",
        )

        return redirect(
            url_for(
                "event.event_details",
                event_id=event_id,
            )
        )

    existing_verification = _get_existing_verification(
        event_id,
        student_id,
    )

    return render_template(
        "student/verify_event.html",
        event=event,
        registration=registration,
        verification=existing_verification,
    )


@verification_bp.route(
    "/event/<int:event_id>/verify",
    methods=["POST"],
)
@student_required
def verify_event(event_id):
    """
    Perform complete event verification.

    Expected JSON or form data:

        qr_token:
            Dynamic QR token scanned by the student.

        face_image:
            Base64 image captured from the student's camera.

    Successful workflow:

        valid registration
        + valid event
        + valid time
        + valid dynamic QR
        + successful face verification
        = verified event presence
    """
    student_id = session.get("user_id")

    event = get_event_by_id(event_id)

    if event is None:
        return _verification_response(
            success=False,
            message="Event not found.",
            status_code=404,
        )

    registration = get_event_registration(
        event_id=event_id,
        student_id=student_id,
    )

    if registration is None:
        return _verification_response(
            success=False,
            message=(
                "You are not registered for this event."
            ),
            status_code=403,
        )

    if registration["status"] == "cancelled":
        return _verification_response(
            success=False,
            message=(
                "Your registration for this event "
                "has been cancelled."
            ),
            status_code=403,
        )

    if registration["status"] == "attended":
        existing = _get_existing_verification(
            event_id,
            student_id,
        )

        return _verification_response(
            success=True,
            message=(
                "Your event presence has already "
                "been verified."
            ),
            verification=existing,
        )

    if event["status"] != "live":
        return _verification_response(
            success=False,
            message=(
                "This event is not currently live. "
                "Verification is available only "
                "during the active event."
            ),
            status_code=400,
        )

    if not _is_event_time_valid(event):
        return _verification_response(
            success=False,
            message=(
                "Event verification is not available "
                "at this time."
            ),
            status_code=400,
        )

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):
        data = request.form

    qr_token = str(
        data.get("qr_token", "")
    ).strip()

    face_image = data.get(
        "face_image"
    )

    if not qr_token:
        return _verification_response(
            success=False,
            message="Please scan the event QR code.",
            status_code=400,
        )

    if not face_image:
        return _verification_response(
            success=False,
            message=(
                "Please capture your face using "
                "the camera."
            ),
            status_code=400,
        )

    qr_record = _validate_qr_token_for_event(
        event_id=event_id,
        token=qr_token,
    )

    if qr_record is None:
        _save_verification(
            event_id=event_id,
            student_id=student_id,
            qr_token_id=None,
            qr_verified=False,
            face_verified=False,
            verification_status="failed",
            confidence=0.0,
        )

        return _verification_response(
            success=False,
            message=(
                "QR code is invalid or expired. "
                "Please scan the current event QR code."
            ),
            status_code=400,
        )

    qr_verified = True

    student = fetch_one(
        """
        SELECT
            id,
            name,
            email,
            roll_no,
            face_image_path,
            is_active
        FROM users
        WHERE id = ?
          AND role = 'student'
          AND is_active = 1
        LIMIT 1
        """,
        (student_id,),
    )

    if student is None:
        return _verification_response(
            success=False,
            message="Student account could not be found.",
            status_code=403,
        )

    if not student["face_image_path"]:
        _save_verification(
            event_id=event_id,
            student_id=student_id,
            qr_token_id=qr_record["id"],
            qr_verified=True,
            face_verified=False,
            verification_status="failed",
            confidence=0.0,
        )

        return _verification_response(
            success=False,
            message=(
                "No registered face image was found "
                "for your account."
            ),
            status_code=400,
        )

    face_result = verify_face_from_base64(
        registered_face_path=student["face_image_path"],
        live_image_data=face_image,
    )

    face_verified = bool(
        face_result.get("verified", False)
    )

    confidence = face_result.get(
        "confidence_percent",
        0.0,
    )

    if not face_verified:
        _save_verification(
            event_id=event_id,
            student_id=student_id,
            qr_token_id=qr_record["id"],
            qr_verified=True,
            face_verified=False,
            verification_status="failed",
            confidence=confidence,
        )

        return _verification_response(
            success=False,
            message=(
                face_result.get(
                    "reason",
                    "Face verification failed.",
                )
            ),
            verification={
                "qr_verified": True,
                "face_verified": False,
                "confidence": confidence,
            },
            status_code=400,
        )

    verification_id = _save_verification(
        event_id=event_id,
        student_id=student_id,
        qr_token_id=qr_record["id"],
        qr_verified=True,
        face_verified=True,
        verification_status="verified",
        confidence=confidence,
    )

    _mark_event_registration_attended(
        event_id=event_id,
        student_id=student_id,
    )

    try:
        notify_event_coordinators(
            event_id=event_id,
            student_id=student_id,
            student_name=student["name"],
            roll_no=student["roll_no"],
            verification_time=_database_now(),
        )
    except Exception:
        # Verification must remain successful even if a
        # notification encounters a non-critical error.
        pass

    verification = fetch_one(
        """
        SELECT
            ev.id,
            ev.event_id,
            ev.student_id,
            ev.qr_token_id,
            ev.qr_verified,
            ev.face_verified,
            ev.verification_status,
            ev.confidence,
            ev.verified_at,
            ev.created_at
        FROM event_verifications ev
        WHERE ev.id = ?
        LIMIT 1
        """,
        (verification_id,),
    )

    return _verification_response(
        success=True,
        message=(
            "EVENT PRESENCE VERIFIED successfully."
        ),
        verification=verification,
        extra={
            "event_name": event["event_name"],
            "student_name": student["name"],
            "roll_no": student["roll_no"],
            "qr_verified": True,
            "face_verified": True,
            "confidence": confidence,
        },
    )


@verification_bp.route(
    "/event/<int:event_id>/qr-check",
    methods=["POST"],
)
@student_required
def check_qr(event_id):
    """
    Validate only the dynamic QR.

    This endpoint is useful for the frontend to provide
    immediate feedback before camera verification.
    """
    event = get_event_by_id(event_id)

    if event is None:
        return jsonify(
            {
                "success": False,
                "message": "Event not found.",
            }
        ), 404

    student_id = session.get("user_id")

    registration = get_event_registration(
        event_id=event_id,
        student_id=student_id,
    )

    if registration is None:
        return jsonify(
            {
                "success": False,
                "message": (
                    "You are not registered for this event."
                ),
            }
        ), 403

    data = request.get_json(
        silent=True
    ) or request.form

    qr_token = str(
        data.get("qr_token", "")
    ).strip()

    qr_record = _validate_qr_token_for_event(
        event_id=event_id,
        token=qr_token,
    )

    if qr_record is None:
        return jsonify(
            {
                "success": False,
                "qr_verified": False,
                "message": (
                    "QR code is invalid or expired."
                ),
            }
        ), 400

    return jsonify(
        {
            "success": True,
            "qr_verified": True,
            "message": "QR code verified successfully.",
            "expires_at": qr_record["expires_at"],
        }
    )


@verification_bp.route(
    "/event/<int:event_id>/status",
    methods=["GET"],
)
@student_required
def verification_status(event_id):
    """
    Return the current verification state for the
    logged-in student.
    """
    event = get_event_by_id(event_id)

    if event is None:
        return jsonify(
            {
                "success": False,
                "message": "Event not found.",
            }
        ), 404

    student_id = session.get("user_id")

    verification = _get_existing_verification(
        event_id=event_id,
        student_id=student_id,
    )

    if verification is None:
        return jsonify(
            {
                "success": True,
                "verified": False,
                "status": "not_started",
            }
        )

    return jsonify(
        {
            "success": True,
            "verified": (
                verification["verification_status"]
                == "verified"
            ),
            "status": verification[
                "verification_status"
            ],
            "qr_verified": bool(
                verification["qr_verified"]
            ),
            "face_verified": bool(
                verification["face_verified"]
            ),
            "confidence": (
                verification["confidence"]
                or 0
            ),
            "verified_at": verification[
                "verified_at"
            ],
        }
    )


@verification_bp.route(
    "/teacher/event/<int:event_id>",
)
@teacher_required
def teacher_verification_records(event_id):
    """
    Display verification records for a teacher-coordinated event.
    """
    event = get_event_by_id(event_id)

    if event is None:
        from flask import abort

        abort(404)

    teacher_id = session.get("user_id")

    if not is_event_coordinator(
        event_id,
        teacher_id,
    ):
        flash(
            "You are not assigned to this event.",
            "danger",
        )

        return redirect(
            url_for(
                "event.teacher_coordinator"
            )
        )

    records = fetch_all(
        """
        SELECT
            ev.id,
            ev.event_id,
            ev.student_id,
            ev.qr_token_id,
            ev.qr_verified,
            ev.face_verified,
            ev.verification_status,
            ev.confidence,
            ev.verified_at,
            ev.created_at,
            u.name AS student_name,
            u.email AS student_email,
            u.roll_no AS student_roll_no,
            u.department_id,
            u.semester,
            u.section
        FROM event_verifications ev
        INNER JOIN users u
            ON u.id = ev.student_id
        WHERE ev.event_id = ?
        ORDER BY
            CASE
                WHEN ev.verification_status = 'verified'
                THEN 0
                WHEN ev.verification_status = 'pending'
                THEN 1
                ELSE 2
            END,
            ev.verified_at DESC,
            ev.created_at DESC
        """,
        (event_id,),
    )

    verified_count = sum(
        1
        for record in records
        if record["verification_status"]
        == "verified"
    )

    return render_template(
        "teacher/verified_students.html",
        event=event,
        records=records,
        verifications=records,
        verified_count=verified_count,
    )


def _verification_response(
    success,
    message,
    verification=None,
    status_code=200,
    extra=None,
):
    """
    Return either JSON or an HTML redirect depending on
    how the frontend requested verification.

    JSON is used when:
        - Content-Type is application/json
        - X-Requested-With is XMLHttpRequest
        - ?format=json is supplied

    Otherwise the user is redirected to the result page.
    """
    payload = {
        "success": bool(success),
        "message": message,
    }

    if verification is not None:
        payload["verification"] = _row_to_dict(
            verification
        )

    if extra:
        payload.update(extra)

    wants_json = (
        request.is_json
        or request.headers.get(
            "X-Requested-With"
        )
        == "XMLHttpRequest"
        or request.args.get("format")
        == "json"
    )

    if wants_json:
        return jsonify(payload), status_code

    if success:
        return redirect(
            url_for(
                "verification.verification_result",
                event_id=payload.get(
                    "event_id",
                    request.view_args.get("event_id"),
                ),
            )
        )

    flash(
        message,
        "success" if success else "danger",
    )

    return redirect(
        url_for(
            "verification.verify_event_page",
            event_id=request.view_args.get(
                "event_id"
            ),
        )
    )


def _row_to_dict(row):
    """
    Convert sqlite3.Row or a mapping into a normal dictionary.
    """
    if row is None:
        return {}

    try:
        return dict(row)
    except (TypeError, ValueError):
        return {
            key: row[key]
            for key in row.keys()
        }


@verification_bp.route(
    "/event/<int:event_id>/result",
)
@student_required
def verification_result(event_id):
    """
    Display the final verification result page.
    """
    event = get_event_by_id(event_id)

    if event is None:
        from flask import abort

        abort(404)

    student_id = session.get("user_id")

    verification = _get_existing_verification(
        event_id=event_id,
        student_id=student_id,
    )

    registration = get_event_registration(
        event_id=event_id,
        student_id=student_id,
    )

    return render_template(
        "student/verification_result.html",
        event=event,
        verification=verification,
        registration=registration,
    )