from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import pytz
from app import db
from app.utils.timezone_utils import get_user_timezone, localize_datetime, get_current_time
from app.models.user import User
from app.models.appointment import Appointment, AppointmentStatus
from app.models.medical_record import Consultation, Prescription, VitalSigns, Allergy
from app.models.message import InternalMessage
from app.utils.sidebar_utils import get_sidebar_stats
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

    # Get sidebar statistics using the shared function
    stats = get_sidebar_stats()

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
                "url": url_for("consultations.new_consultation"),
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
