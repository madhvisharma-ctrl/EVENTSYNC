"""
EventSync Event Routes

Handles:
- Event browsing
- Event details
- Student event registration
- Student event cancellation
- Student coordinator registration
- Teacher coordinator workspace
- Admin event management
"""

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from services.event_service import (
    EVENT_CATEGORIES,
    EVENT_TYPES,
    PARTICIPATION_ROLES,
    assign_event_coordinator,
    cancel_event_registration,
    create_event,
    delete_event,
    get_all_events,
    get_event_by_id,
    get_event_dashboard_data,
    get_event_statistics,
    get_event_coordinators,
    get_event_registrations,
    get_student_coordinator_events,
    get_teacher_coordinator_events,
    is_event_coordinator,
    mark_registration_attended,
    register_student_for_event,
    remove_event_coordinator,
    update_event,
    update_event_status,
)
from services.auth_service import (
    get_students,
    get_teachers,
)
from utils.decorators import (
    admin_required,
    student_required,
    teacher_required,
    teacher_or_admin_required,
)


event_bp = Blueprint(
    "event",
    __name__,
    url_prefix="/events",
)


def _current_user_id():
    """
    Return the logged-in user's ID.
    """
    return session.get("user_id")


def _get_event_or_404(event_id: int):
    """
    Return an event or raise a 404 through Flask.
    """
    event = get_event_by_id(event_id)

    if event is None:
        from flask import abort

        abort(404)

    return event


def _parse_int(value, default=None):
    """
    Safely convert a form/query value to int.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _get_form_value(name: str, default: str = "") -> str:
    """
    Read and trim a form value.
    """
    return str(request.form.get(name, default)).strip()


@event_bp.route("/")
def events():
    """
    Public event listing page.
    """
    events_list = get_all_events(
        include_cancelled=False
    )

    return render_template(
        "student/events.html",
        events=events_list,
        event_categories=sorted(EVENT_CATEGORIES),
    )


@event_bp.route("/<int:event_id>")
def event_details(event_id: int):
    """
    Display detailed information about one event.
    """
    event = _get_event_or_404(event_id)

    user_id = _current_user_id()

    registration = None
    coordinator = False

    if user_id:
        registration = get_event_registration(
            event_id=event_id,
            student_id=user_id,
        )

        coordinator = is_event_coordinator(
            event_id=event_id,
            user_id=user_id,
        )

    coordinators = get_event_coordinators(event_id)

    return render_template(
        "student/event_details.html",
        event=event,
        registration=registration,
        is_coordinator=coordinator,
        coordinators=coordinators,
    )


@event_bp.route(
    "/<int:event_id>/register",
    methods=["POST"],
)
@student_required
def register(event_id):
    """
    Register the logged-in student for an event.
    """
    event = _get_event_or_404(event_id)

    student_id = _current_user_id()

    participation_role = _get_form_value(
        "participation_role",
        "participant",
    ).lower()

    if participation_role not in PARTICIPATION_ROLES:
        flash(
            "Please select a valid participation role.",
            "danger",
        )
        return redirect(
            url_for(
                "event.event_details",
                event_id=event_id,
            )
        )

    try:
        result = register_student_for_event(
            event_id=event_id,
            student_id=student_id,
            participation_role=participation_role,
        )

        if result.get("success", True):
            if participation_role == "student_coordinator":
                flash(
                    f"You are registered for {event['event_name']} "
                    "as a Student Coordinator.",
                    "success",
                )
            else:
                flash(
                    f"You are registered for "
                    f"{event['event_name']}.",
                    "success",
                )
        else:
            flash(
                result.get(
                    "message",
                    "Event registration could not be completed.",
                ),
                "danger",
            )

    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        flash(
            "Unable to complete event registration.",
            "danger",
        )

    return redirect(
        url_for(
            "event.event_details",
            event_id=event_id,
        )
    )


@event_bp.route(
    "/<int:event_id>/cancel-registration",
    methods=["POST"],
)
@student_required
def cancel_registration(event_id):
    """
    Cancel the logged-in student's event registration.
    """
    _get_event_or_404(event_id)

    student_id = _current_user_id()

    try:
        cancelled = cancel_event_registration(
            event_id=event_id,
            student_id=student_id,
        )

        if cancelled:
            flash(
                "Your event registration has been cancelled.",
                "success",
            )
        else:
            flash(
                "No active registration was found.",
                "warning",
            )

    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        flash(
            "Unable to cancel event registration.",
            "danger",
        )

    return redirect(
        url_for(
            "event.event_details",
            event_id=event_id,
        )
    )


@event_bp.route("/my-events")
@student_required
def my_events():
    """
    Display events registered by the current student.
    """
    from services.event_service import get_student_registered_events

    student_id = _current_user_id()

    events_list = get_student_registered_events(
        student_id
    )

    return render_template(
        "student/my_events.html",
        events=events_list,
    )


@event_bp.route("/coordinator")
@student_required
def student_coordinator():
    """
    Display the student's event coordinator workspace.
    """
    student_id = _current_user_id()

    coordinator_events = get_student_coordinator_events(
        student_id
    )

    return render_template(
        "student/coordinator.html",
        events=coordinator_events,
    )


@event_bp.route(
    "/<int:event_id>/mark-attended",
    methods=["POST"],
)
@student_required
def mark_attended(event_id):
    """
    Mark a registered student as attended.

    Normally this action is triggered by successful event
    verification. It is kept separate from academic attendance.
    """
    _get_event_or_404(event_id)

    student_id = _current_user_id()

    try:
        result = mark_registration_attended(
            event_id=event_id,
            student_id=student_id,
        )

        if result:
            flash(
                "Event attendance marked successfully.",
                "success",
            )
        else:
            flash(
                "Event attendance could not be updated.",
                "warning",
            )

    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        flash(
            "Unable to update event attendance.",
            "danger",
        )

    return redirect(
        url_for(
            "event.event_details",
            event_id=event_id,
        )
    )


@event_bp.route("/teacher/coordinator")
@teacher_required
def teacher_coordinator():
    """
    Display events for which the current teacher is assigned
    as a coordinator.
    """
    teacher_id = _current_user_id()

    events_list = get_teacher_coordinator_events(
        teacher_id
    )

    return render_template(
        "teacher/coordinator.html",
        events=events_list,
    )


@event_bp.route(
    "/teacher/<int:event_id>/registrations"
)
@teacher_required
def teacher_event_registrations(event_id):
    """
    Display registered students for a teacher-coordinated event.
    """
    event = _get_event_or_404(event_id)

    teacher_id = _current_user_id()

    if not is_event_coordinator(
        event_id,
        teacher_id,
    ):
        flash(
            "You are not assigned to coordinate this event.",
            "danger",
        )
        return redirect(
            url_for(
                "event.teacher_coordinator"
            )
        )

    registrations = get_event_registrations(
        event_id
    )

    coordinators = get_event_coordinators(
        event_id
    )

    statistics = get_event_statistics(
        event_id
    )

    return render_template(
        "teacher/verified_students.html",
        event=event,
        registrations=registrations,
        coordinators=coordinators,
        statistics=statistics,
    )


@event_bp.route(
    "/teacher/<int:event_id>/attendance/<int:student_id>",
    methods=["POST"],
)
@teacher_required
def teacher_mark_attended(
    event_id,
    student_id,
):
    """
    Allow an assigned event coordinator to manually mark
    event registration attendance.

    This does NOT touch academic lecture attendance.
    """
    event = _get_event_or_404(event_id)

    teacher_id = _current_user_id()

    if not is_event_coordinator(
        event_id,
        teacher_id,
    ):
        flash(
            "You are not assigned to coordinate this event.",
            "danger",
        )
        return redirect(
            url_for(
                "event.teacher_coordinator"
            )
        )

    try:
        result = mark_registration_attended(
            event_id=event_id,
            student_id=student_id,
        )

        if result:
            flash(
                "Event attendance updated.",
                "success",
            )
        else:
            flash(
                "Student registration was not found.",
                "warning",
            )

    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        flash(
            "Unable to update event attendance.",
            "danger",
        )

    return redirect(
        url_for(
            "event.teacher_event_registrations",
            event_id=event_id,
        )
    )


# ------------------------------------------------------------------
# ADMIN EVENT MANAGEMENT
# ------------------------------------------------------------------


@event_bp.route("/admin")
@admin_required
def admin_events():
    """
    Display all events for administrators.
    """
    events_list = get_all_events(
        include_cancelled=True
    )

    return render_template(
        "admin/events.html",
        events=events_list,
        event_categories=sorted(EVENT_CATEGORIES),
        event_types=sorted(EVENT_TYPES),
    )


@event_bp.route(
    "/admin/create",
    methods=["GET", "POST"],
)
@admin_required
def admin_create_event():
    """
    Create a new event.
    """
    teachers = get_teachers()
    students = get_students()

    if request.method == "POST":
        event_data = {
            "event_name": _get_form_value("event_name"),
            "event_category": _get_form_value(
                "event_category"
            ),
            "event_type": _get_form_value("event_type"),
            "event_date": _get_form_value("event_date"),
            "start_time": _get_form_value("start_time"),
            "end_time": _get_form_value("end_time"),
            "venue": _get_form_value("venue"),
            "description": _get_form_value("description"),
            "status": _get_form_value(
                "status",
                "upcoming",
            ).lower(),
        }

        created_by = _current_user_id()

        try:
            event_id = create_event(
                created_by=created_by,
                **event_data,
            )

            flash(
                "Event created successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "event.admin_event_details",
                    event_id=event_id,
                )
            )

        except ValueError as error:
            flash(str(error), "danger")
        except Exception:
            flash(
                "Unable to create the event.",
                "danger",
            )

    return render_template(
        "admin/event_form.html",
        event=None,
        teachers=teachers,
        students=students,
        event_categories=sorted(EVENT_CATEGORIES),
        event_types=sorted(EVENT_TYPES),
    )


@event_bp.route(
    "/admin/<int:event_id>"
)
@admin_required
def admin_event_details(event_id):
    """
    Display complete event administration information.
    """
    event = _get_event_or_404(event_id)

    dashboard_data = get_event_dashboard_data(
        event_id
    )

    statistics = get_event_statistics(
        event_id
    )

    coordinators = get_event_coordinators(
        event_id
    )

    registrations = get_event_registrations(
        event_id
    )

    return render_template(
        "admin/events.html",
        event=event,
        dashboard_data=dashboard_data,
        statistics=statistics,
        coordinators=coordinators,
        registrations=registrations,
        events=[event],
        event_categories=sorted(EVENT_CATEGORIES),
        event_types=sorted(EVENT_TYPES),
    )


@event_bp.route(
    "/admin/<int:event_id>/edit",
    methods=["GET", "POST"],
)
@admin_required
def admin_edit_event(event_id):
    """
    Edit an existing event.
    """
    event = _get_event_or_404(event_id)

    teachers = get_teachers()
    students = get_students()

    if request.method == "POST":
        event_data = {
            "event_name": _get_form_value("event_name"),
            "event_category": _get_form_value(
                "event_category"
            ),
            "event_type": _get_form_value("event_type"),
            "event_date": _get_form_value("event_date"),
            "start_time": _get_form_value("start_time"),
            "end_time": _get_form_value("end_time"),
            "venue": _get_form_value("venue"),
            "description": _get_form_value("description"),
            "status": _get_form_value(
                "status",
                "upcoming",
            ).lower(),
        }

        try:
            updated = update_event(
                event_id=event_id,
                **event_data,
            )

            if updated:
                flash(
                    "Event updated successfully.",
                    "success",
                )
            else:
                flash(
                    "No event changes were made.",
                    "warning",
                )

            return redirect(
                url_for(
                    "event.admin_event_details",
                    event_id=event_id,
                )
            )

        except ValueError as error:
            flash(str(error), "danger")
        except Exception:
            flash(
                "Unable to update the event.",
                "danger",
            )

    return render_template(
        "admin/event_form.html",
        event=event,
        teachers=teachers,
        students=students,
        event_categories=sorted(EVENT_CATEGORIES),
        event_types=sorted(EVENT_TYPES),
    )


@event_bp.route(
    "/admin/<int:event_id>/status",
    methods=["POST"],
)
@admin_required
def admin_update_event_status(event_id):
    """
    Update an event's lifecycle status.
    """
    _get_event_or_404(event_id)

    status = _get_form_value("status").lower()

    try:
        updated = update_event_status(
            event_id=event_id,
            status=status,
        )

        if updated:
            flash(
                f"Event status changed to {status}.",
                "success",
            )
        else:
            flash(
                "Event status could not be changed.",
                "warning",
            )

    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        flash(
            "Unable to update event status.",
            "danger",
        )

    return redirect(
        url_for(
            "event.admin_event_details",
            event_id=event_id,
        )
    )


@event_bp.route(
    "/admin/<int:event_id>/delete",
    methods=["POST"],
)
@admin_required
def admin_delete_event(event_id):
    """
    Delete an event.
    """
    _get_event_or_404(event_id)

    try:
        deleted = delete_event(
            event_id
        )

        if deleted:
            flash(
                "Event deleted successfully.",
                "success",
            )
        else:
            flash(
                "Event could not be deleted.",
                "warning",
            )

    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        flash(
            "Unable to delete the event.",
            "danger",
        )

    return redirect(
        url_for(
            "event.admin_events"
        )
    )


# ------------------------------------------------------------------
# ADMIN COORDINATOR MANAGEMENT
# ------------------------------------------------------------------


@event_bp.route(
    "/admin/<int:event_id>/coordinators/add",
    methods=["POST"],
)
@admin_required
def admin_add_coordinator(event_id):
    """
    Assign a teacher or student as an event coordinator.
    """
    _get_event_or_404(event_id)

    user_id = _parse_int(
        request.form.get("user_id")
    )

    coordinator_role = _get_form_value(
        "coordinator_role"
    ).lower()

    if not user_id:
        flash(
            "Please select a user.",
            "danger",
        )
        return redirect(
            url_for(
                "event.admin_event_details",
                event_id=event_id,
            )
        )

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
                "event.admin_event_details",
                event_id=event_id,
            )
        )

    try:
        assigned = assign_event_coordinator(
            event_id=event_id,
            user_id=user_id,
            coordinator_role=coordinator_role,
        )

        if assigned:
            flash(
                "Event coordinator assigned successfully.",
                "success",
            )
        else:
            flash(
                "Coordinator could not be assigned.",
                "warning",
            )

    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        flash(
            "Unable to assign event coordinator.",
            "danger",
        )

    return redirect(
        url_for(
            "event.admin_event_details",
            event_id=event_id,
        )
    )


@event_bp.route(
    "/admin/<int:event_id>/coordinators/<int:user_id>/remove",
    methods=["POST"],
)
@admin_required
def admin_remove_coordinator(
    event_id,
    user_id,
):
    """
    Remove an event coordinator.
    """
    _get_event_or_404(event_id)

    try:
        removed = remove_event_coordinator(
            event_id=event_id,
            user_id=user_id,
        )

        if removed:
            flash(
                "Event coordinator removed.",
                "success",
            )
        else:
            flash(
                "Coordinator assignment was not found.",
                "warning",
            )

    except ValueError as error:
        flash(str(error), "danger")
    except Exception:
        flash(
            "Unable to remove event coordinator.",
            "danger",
        )

    return redirect(
        url_for(
            "event.admin_event_details",
            event_id=event_id,
        )
    )


@event_bp.route(
    "/admin/<int:event_id>/registrations"
)
@admin_required
def admin_event_registrations(event_id):
    """
    Display all registrations for an event.
    """
    event = _get_event_or_404(event_id)

    registrations = get_event_registrations(
        event_id
    )

    statistics = get_event_statistics(
        event_id
    )

    return render_template(
        "admin/reports.html",
        event=event,
        registrations=registrations,
        statistics=statistics,
    )