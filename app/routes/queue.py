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
from app import db
from app.models.user import User
from app.models.appointment import Appointment
from app.models.queue import PatientQueue, QueueStatus
from app.models.message import InternalMessage, MessageType, MessagePriority
from sqlalchemy import and_, or_

queue_bp = Blueprint("queue", __name__, url_prefix="/queue")


@queue_bp.route("/dashboard")
@login_required
def dashboard():
    """Queue dashboard for staff and doctors."""
    if current_user.role not in ["doctor", "staff"]:
        flash("Access denied. This area is for healthcare professionals only.", "error")
        return redirect(url_for("main.home"))

    # Get today's queue
    today = datetime.now().date()

    if current_user.role == "doctor":
        # Doctor sees their own queue
        queue_entries = (
            db.session.query(PatientQueue)
            .join(Appointment)
            .filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.appointment_date.cast(db.Date) == today,
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
                    Appointment.appointment_date.cast(db.Date) == today,
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

    return render_template("queue/dashboard.html", queue_entries=queue_entries)


@queue_bp.route("/api/current")
@login_required
def api_current_queue():
    """API endpoint for real-time queue updates."""
    today = datetime.now().date()

    if current_user.role == "doctor":
        queue_entries = (
            db.session.query(PatientQueue)
            .join(Appointment)
            .filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.appointment_date.cast(db.Date) == today,
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
                    Appointment.appointment_date.cast(db.Date) == today,
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

    return jsonify(
        {
            "queue_entries": [entry.to_dict() for entry in queue_entries],
            "last_updated": datetime.utcnow().isoformat(),
        }
    )


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
            _send_delay_notification(queue_entry, delay_reason)

        return jsonify({"success": True, "queue_entry": queue_entry.to_dict()})

    except Exception as e:
        current_app.logger.error(f"Error updating queue status: {str(e)}")
        return jsonify({"error": "Failed to update status"}), 500


@queue_bp.route("/api/estimate_wait/<int:queue_id>")
@login_required
def api_estimate_wait(queue_id):
    """Calculate estimated wait time for a queue entry."""
    queue_entry = PatientQueue.query.get_or_404(queue_id)

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
        {"estimated_wait_time": estimated_wait, "entries_ahead": entries_ahead}
    )


def _send_delay_notification(queue_entry, delay_reason):
    """Send internal notification about queue delay."""
    try:
        # Notify patient (if they have an account)
        patient = queue_entry.appointment.patient

        # Create internal message for staff
        staff_users = User.query.filter_by(role="staff").all()
        for staff in staff_users:
            message = InternalMessage(
                sender_id=current_user.id,
                recipient_id=staff.id,
                subject=f"Queue Delay - {patient.first_name} {patient.last_name}",
                content=f"Appointment delayed. Reason: {delay_reason}. Queue #: {queue_entry.queue_number}",
                message_type=MessageType.QUEUE_UPDATE,
                priority=MessagePriority.HIGH,
                related_appointment_id=queue_entry.appointment_id,
                related_patient_id=patient.id,
            )
            db.session.add(message)

        db.session.commit()

    except Exception as e:
        current_app.logger.error(f"Error sending delay notification: {str(e)}")
