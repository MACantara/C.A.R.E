from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import pytz
from app import db, get_user_timezone, localize_datetime, get_current_time
from app.models.user import User
from app.models.appointment import Appointment, AppointmentStatus
from app.models.medical_record import MedicalRecord, Consultation
from app.models.queue import PatientQueue, QueueStatus
from app.models.message import InternalMessage
from sqlalchemy import desc, func, and_, or_

medical_dashboard_bp = Blueprint("medical_dashboard", __name__, url_prefix="/medical")


@medical_dashboard_bp.route("/")
@login_required
def dashboard():
    """Central medical dashboard for healthcare professionals."""
    if current_user.role not in ["doctor", "staff"]:
        flash("Access denied. This area is for healthcare professionals only.", "error")
        return redirect(url_for("main.home"))

    # Get user's timezone for displaying timestamps
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)
    today_local = current_time_local.date()

    # Initialize statistics
    stats = {
        "total_patients": 0,
        "todays_appointments": 0,
        "pending_consultations": 0,
        "queue_waiting": 0,
        "unread_messages": 0,
        "recent_prescriptions": 0,
    }

    # Role-specific data gathering
    if current_user.role == "doctor":
        # Doctor-specific statistics
        stats["total_patients"] = User.query.filter_by(role="patient").count()

        # Today's appointments for this doctor
        stats["todays_appointments"] = Appointment.query.filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.appointment_date.cast(db.Date) == today_local,
                Appointment.status.in_(
                    [AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS]
                ),
            )
        ).count()

        # Pending consultations (appointments that need follow-up)
        stats["pending_consultations"] = Appointment.query.filter(
            and_(
                Appointment.doctor_id == current_user.id,
                Appointment.status == AppointmentStatus.COMPLETED,
                ~Appointment.id.in_(
                    db.session.query(Consultation.appointment_id).filter(
                        Consultation.appointment_id.isnot(None)
                    )
                ),
            )
        ).count()

        # Queue waiting for this doctor
        stats["queue_waiting"] = (
            PatientQueue.query.join(Appointment)
            .filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    PatientQueue.status == QueueStatus.WAITING,
                )
            )
            .count()
        )

        # Recent prescriptions by this doctor (last 7 days)
        seven_days_ago = current_time_local - timedelta(days=7)
        stats["recent_prescriptions"] = Consultation.query.filter(
            and_(
                Consultation.doctor_id == current_user.id,
                Consultation.created_at >= seven_days_ago.replace(tzinfo=None),
            )
        ).count()

    elif current_user.role == "staff":
        # Staff can see system-wide statistics
        stats["total_patients"] = User.query.filter_by(role="patient").count()

        # All appointments today
        stats["todays_appointments"] = Appointment.query.filter(
            and_(
                Appointment.appointment_date.cast(db.Date) == today_local,
                Appointment.status.in_(
                    [AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS]
                ),
            )
        ).count()

        # All pending consultations
        stats["pending_consultations"] = Appointment.query.filter(
            and_(
                Appointment.status == AppointmentStatus.COMPLETED,
                ~Appointment.id.in_(
                    db.session.query(Consultation.appointment_id).filter(
                        Consultation.appointment_id.isnot(None)
                    )
                ),
            )
        ).count()

        # Total queue waiting
        stats["queue_waiting"] = PatientQueue.query.filter(
            PatientQueue.status == QueueStatus.WAITING
        ).count()

        # Recent prescriptions system-wide (last 7 days)
        seven_days_ago = current_time_local - timedelta(days=7)
        stats["recent_prescriptions"] = Consultation.query.filter(
            Consultation.created_at >= seven_days_ago.replace(tzinfo=None)
        ).count()

    # Unread messages (common for both roles)
    stats["unread_messages"] = InternalMessage.query.filter(
        and_(
            InternalMessage.recipient_id == current_user.id,
            InternalMessage.is_read == False,
            InternalMessage.is_deleted_by_recipient == False,
        )
    ).count()

    # Recent activities
    recent_appointments = []
    recent_consultations = []

    if current_user.role == "doctor":
        # Recent appointments for this doctor
        recent_appointments = (
            Appointment.query.filter(Appointment.doctor_id == current_user.id)
            .order_by(desc(Appointment.appointment_date))
            .limit(5)
            .all()
        )

        # Recent consultations by this doctor
        recent_consultations = (
            Consultation.query.filter(Consultation.doctor_id == current_user.id)
            .order_by(desc(Consultation.created_at))
            .limit(5)
            .all()
        )

    elif current_user.role == "staff":
        # Recent appointments system-wide
        recent_appointments = (
            Appointment.query.order_by(desc(Appointment.appointment_date))
            .limit(5)
            .all()
        )

        # Recent consultations system-wide
        recent_consultations = (
            Consultation.query.order_by(desc(Consultation.created_at)).limit(5).all()
        )

    return render_template(
        "medical_dashboard/dashboard.html",
        stats=stats,
        recent_appointments=recent_appointments,
        recent_consultations=recent_consultations,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
    )


@medical_dashboard_bp.route("/api/stats")
@login_required
def api_stats():
    """API endpoint for dashboard statistics with timezone awareness."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)

    # Get daily appointment statistics for the last 7 days
    seven_days_ago = current_time_local - timedelta(days=7)
    daily_stats = []

    for i in range(7):
        day_local = seven_days_ago + timedelta(days=i)
        day_start = day_local.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # Convert to UTC for database query
        day_start_utc = day_start.astimezone(pytz.utc).replace(tzinfo=None)
        day_end_utc = day_end.astimezone(pytz.utc).replace(tzinfo=None)

        if current_user.role == "doctor":
            appointment_count = Appointment.query.filter(
                and_(
                    Appointment.doctor_id == current_user.id,
                    Appointment.appointment_date >= day_start_utc,
                    Appointment.appointment_date < day_end_utc,
                )
            ).count()
        else:
            appointment_count = Appointment.query.filter(
                and_(
                    Appointment.appointment_date >= day_start_utc,
                    Appointment.appointment_date < day_end_utc,
                )
            ).count()

        daily_stats.append(
            {
                "date": day_local.strftime("%Y-%m-%d"),
                "date_display": day_local.strftime("%m/%d"),
                "appointments": appointment_count,
            }
        )

    return jsonify(
        {
            "daily_stats": daily_stats,
            "timezone": str(user_timezone),
            "last_updated": current_time_local.isoformat(),
        }
    )


@medical_dashboard_bp.route("/quick-actions")
@login_required
def quick_actions():
    """Quick actions menu for common medical tasks."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    actions = []

    if current_user.role == "doctor":
        actions = [
            {
                "title": "New Consultation",
                "description": "Start a new patient consultation",
                "url": url_for("medical_records.new_consultation"),
                "icon": "bi-plus-circle",
                "color": "green",
            },
            {
                "title": "View Schedule",
                "description": "Check today's appointments",
                "url": url_for("appointments.doctor_schedule"),
                "icon": "bi-calendar-week",
                "color": "blue",
            },
            {
                "title": "Patient Search",
                "description": "Find patient records",
                "url": url_for("medical_records.search_records"),
                "icon": "bi-search",
                "color": "purple",
            },
            {
                "title": "Queue Status",
                "description": "Monitor patient queue",
                "url": url_for("queue.dashboard"),
                "icon": "bi-people",
                "color": "orange",
            },
        ]
    elif current_user.role == "staff":
        actions = [
            {
                "title": "Patient Directory",
                "description": "Browse all patients",
                "url": url_for("medical_records.patients"),
                "icon": "bi-people",
                "color": "blue",
            },
            {
                "title": "Appointment Reports",
                "description": "View appointment analytics",
                "url": url_for("reports.appointment_report"),
                "icon": "bi-graph-up",
                "color": "green",
            },
            {
                "title": "Queue Management",
                "description": "Manage patient queues",
                "url": url_for("queue.dashboard"),
                "icon": "bi-clock",
                "color": "orange",
            },
            {
                "title": "Performance Reports",
                "description": "System performance metrics",
                "url": url_for("reports.performance"),
                "icon": "bi-speedometer2",
                "color": "purple",
            },
        ]

    return jsonify({"actions": actions})
