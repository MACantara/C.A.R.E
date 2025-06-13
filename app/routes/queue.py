from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    current_app,
)
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db, get_user_timezone, localize_datetime, get_current_time
from app.models.user import User
from app.models.appointment import Appointment
from app.models.queue import PatientQueue, QueueStatus
from app.models.message import InternalMessage, MessageType, MessagePriority
from sqlalchemy import and_, or_

queue_bp = Blueprint("queue", __name__, url_prefix="/queue")


def format_queue_entry_for_api(queue_entry, user_timezone=None):
    """Format queue entry for API response with timezone-aware timestamps."""
    if user_timezone is None:
        user_timezone = get_user_timezone()

    entry_dict = queue_entry.to_dict()

    # Convert timestamps to user's timezone
    if entry_dict.get("created_at"):
        utc_time = datetime.fromisoformat(
            entry_dict["created_at"].replace("Z", "+00:00")
        )
        local_time = localize_datetime(utc_time, user_timezone)
        entry_dict["created_at"] = local_time.isoformat()
        entry_dict["created_at_local"] = local_time.strftime("%Y-%m-%d %H:%M:%S %Z")

    if entry_dict.get("updated_at"):
        utc_time = datetime.fromisoformat(
            entry_dict["updated_at"].replace("Z", "+00:00")
        )
        local_time = localize_datetime(utc_time, user_timezone)
        entry_dict["updated_at"] = local_time.isoformat()
        entry_dict["updated_at_local"] = local_time.strftime("%Y-%m-%d %H:%M:%S %Z")

    # Convert appointment time to user's timezone
    if hasattr(queue_entry, "appointment") and queue_entry.appointment.appointment_date:
        appointment_dt = queue_entry.appointment.appointment_date
        if appointment_dt.tzinfo is None:
            # Assume UTC if no timezone info
            import pytz

            appointment_dt = pytz.utc.localize(appointment_dt)

        local_appointment_time = localize_datetime(appointment_dt, user_timezone)
        entry_dict["appointment_time"] = local_appointment_time.isoformat()
        entry_dict["appointment_time_local"] = local_appointment_time.strftime("%H:%M")
        entry_dict["appointment_date_local"] = local_appointment_time.strftime(
            "%Y-%m-%d"
        )

    return entry_dict


@queue_bp.route("/dashboard")
@login_required
def dashboard():
    """Queue dashboard for staff and doctors."""
    if current_user.role not in ["doctor", "staff"]:
        flash("Access denied. This area is for healthcare professionals only.", "error")
        return redirect(url_for("main.home"))

    # Get today's queue in user's timezone
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)
    today_local = current_time_local.date()

    if current_user.role == "doctor":
        # Doctor sees their own queue
        queue_entries = (
            db.session.query(PatientQueue)
            .join(Appointment)
            .filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.appointment_date.cast(db.Date) == today_local,
                    PatientQueue.status.in_(
                        [
                            QueueStatus.WAITING,
                            QueueStatus.IN_PROGRESS,
                            QueueStatus.DELAYED,
                        ]
                    ),
                )
            )
            .order_by(PatientQueue.queue_number)
            .all()
        )
    else:
        # Staff sees all queues
        queue_entries = (
            db.session.query(PatientQueue)
            .join(Appointment)
            .filter(
                and_(
                    Appointment.appointment_date.cast(db.Date) == today_local,
                    PatientQueue.status.in_(
                        [
                            QueueStatus.WAITING,
                            QueueStatus.IN_PROGRESS,
                            QueueStatus.DELAYED,
                        ]
                    ),
                )
            )
            .order_by(Appointment.doctor_id, PatientQueue.queue_number)
            .all()
        )

    return render_template(
        "queue/dashboard.html",
        queue_entries=queue_entries,
        current_time_local=current_time_local,
        user_timezone=user_timezone,
    )


@queue_bp.route("/api/current")
@login_required
def api_current_queue():
    """API endpoint for real-time queue updates."""
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)
    today_local = current_time_local.date()

    if current_user.role == "doctor":
        queue_entries = (
            db.session.query(PatientQueue)
            .join(Appointment)
            .filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.appointment_date.cast(db.Date) == today_local,
                    PatientQueue.status.in_(
                        [
                            QueueStatus.WAITING,
                            QueueStatus.IN_PROGRESS,
                            QueueStatus.DELAYED,
                        ]
                    ),
                )
            )
            .order_by(PatientQueue.queue_number)
            .all()
        )
    else:
        queue_entries = (
            db.session.query(PatientQueue)
            .join(Appointment)
            .filter(
                and_(
                    Appointment.appointment_date.cast(db.Date) == today_local,
                    PatientQueue.status.in_(
                        [
                            QueueStatus.WAITING,
                            QueueStatus.IN_PROGRESS,
                            QueueStatus.DELAYED,
                        ]
                    ),
                )
            )
            .order_by(Appointment.doctor_id, PatientQueue.queue_number)
            .all()
        )

    # Calculate statistics
    statistics = {
        "waiting_count": sum(
            1 for entry in queue_entries if entry.status == QueueStatus.WAITING
        ),
        "in_progress_count": sum(
            1 for entry in queue_entries if entry.status == QueueStatus.IN_PROGRESS
        ),
        "delayed_count": sum(
            1 for entry in queue_entries if entry.status == QueueStatus.DELAYED
        ),
        "total_count": len(queue_entries),
        "avg_wait_time": _calculate_average_wait_time(queue_entries),
    }

    return jsonify(
        {
            "queue_entries": [
                format_queue_entry_for_api(entry, user_timezone)
                for entry in queue_entries
            ],
            "statistics": statistics,
            "last_updated": current_time_local.isoformat(),
            "timezone": str(user_timezone),
            "current_date": current_time_local.strftime("%Y-%m-%d"),
            "current_time": current_time_local.strftime("%H:%M:%S"),
        }
    )


def _calculate_average_wait_time(queue_entries):
    """Calculate average wait time for current queue entries."""
    if not queue_entries:
        return 0

    total_wait = 0
    count = 0

    for entry in queue_entries:
        if entry.estimated_wait_time:
            total_wait += entry.estimated_wait_time
            count += 1

    return round(total_wait / count) if count > 0 else 0


@queue_bp.route("/api/update_status", methods=["POST"])
@login_required
def api_update_status():
    """Update queue entry status."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    queue_id = data.get("queue_id")
    new_status = data.get("status")
    delay_reason = data.get("delay_reason")
    notes = data.get("notes")

    user_timezone = get_user_timezone()

    try:
        queue_entry = PatientQueue.query.get_or_404(queue_id)

        # Check permissions
        if (
            current_user.role == "doctor"
            and queue_entry.appointment.doctor_id != current_user.id
        ):
            return jsonify({"error": "You can only update your own appointments"}), 403

        old_status = queue_entry.status
        queue_entry.update_status(QueueStatus(new_status), delay_reason, notes)

        # Send notification if status changed to delayed
        if new_status == "delayed" and old_status != QueueStatus.DELAYED:
            _send_delay_notification(queue_entry, delay_reason, user_timezone)

        return jsonify(
            {
                "success": True,
                "queue_entry": format_queue_entry_for_api(queue_entry, user_timezone),
                "timezone": str(user_timezone),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error updating queue status: {str(e)}")
        return jsonify({"error": "Failed to update status"}), 500


@queue_bp.route("/api/estimate_wait/<int:queue_id>")
@login_required
def api_estimate_wait(queue_id):
    """Calculate estimated wait time for a queue entry."""
    queue_entry = PatientQueue.query.get_or_404(queue_id)
    user_timezone = get_user_timezone()

    # Get entries ahead in queue for same doctor
    entries_ahead = (
        PatientQueue.query.join(Appointment)
        .filter(
            and_(
                Appointment.doctor_id == queue_entry.appointment.doctor_id,
                PatientQueue.queue_number < queue_entry.queue_number,
                PatientQueue.status.in_([QueueStatus.WAITING, QueueStatus.IN_PROGRESS]),
            )
        )
        .count()
    )

    # Average consultation time (configurable)
    avg_consultation_time = current_app.config.get(
        "AVG_CONSULTATION_TIME", 15
    )  # minutes
    estimated_wait = entries_ahead * avg_consultation_time

    # Update the queue entry
    queue_entry.estimated_wait_time = estimated_wait
    db.session.commit()

    return jsonify(
        {
            "estimated_wait_time": estimated_wait,
            "entries_ahead": entries_ahead,
            "timezone": str(user_timezone),
            "updated_at": get_current_time(user_timezone).isoformat(),
        }
    )


def _send_delay_notification(queue_entry, delay_reason, user_timezone=None):
    """Send internal notification about queue delay."""
    try:
        if user_timezone is None:
            user_timezone = get_user_timezone()

        current_time_local = get_current_time(user_timezone)

        # Notify patient (if they have an account)
        patient = queue_entry.appointment.patient

        # Create internal message for staff
        staff_users = User.query.filter_by(role="staff").all()
        for staff in staff_users:
            message = InternalMessage(
                sender_id=current_user.id,
                recipient_id=staff.id,
                subject=f"Queue Delay - {patient.first_name} {patient.last_name}",
                content=f"Appointment delayed at {current_time_local.strftime('%H:%M')}. Reason: {delay_reason}. Queue #: {queue_entry.queue_number}",
                message_type=MessageType.QUEUE_UPDATE,
                priority=MessagePriority.HIGH,
                related_appointment_id=queue_entry.appointment_id,
                related_patient_id=patient.id,
            )
            db.session.add(message)

        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Error sending delay notification: {str(e)}")
