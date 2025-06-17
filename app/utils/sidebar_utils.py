from datetime import datetime, timedelta
from flask_login import current_user
from sqlalchemy import desc, func, and_, or_
from app import db
from app.utils.timezone_utils import get_user_timezone, get_current_time
from app.models.user import User
from app.models.appointment import Appointment, AppointmentStatus
from app.models.medical_record import Consultation, Prescription, ConsultationStatus
from app.models.message import InternalMessage


def get_sidebar_stats():
    """Get statistics for sidebar display (shared utility for medical dashboard)."""
    # Get user's timezone for displaying timestamps
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)
    today_local = current_time_local.date()

    # Initialize statistics
    stats = {
        "total_patients": 0,
        "todays_appointments": 0,
        "pending_consultations": 0,
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

        # Pending consultations (draft consultations by this doctor)
        stats["pending_consultations"] = Consultation.query.filter(
            and_(
                Consultation.doctor_id == current_user.id,
                Consultation.status == ConsultationStatus.DRAFT,
            )
        ).count()

        # Recent prescriptions by this doctor (last 7 days)
        seven_days_ago = current_time_local - timedelta(days=7)
        stats["recent_prescriptions"] = Prescription.query.filter(
            and_(
                Prescription.doctor_id == current_user.id,
                Prescription.created_at >= seven_days_ago.replace(tzinfo=None),
            )
        ).count()

    elif current_user.role in ["staff", "admin"]:
        # Staff/admin can see system-wide statistics
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

        # All pending consultations (draft status)
        stats["pending_consultations"] = Consultation.query.filter(
            Consultation.status == ConsultationStatus.DRAFT
        ).count()

        # Recent prescriptions system-wide (last 7 days)
        seven_days_ago = current_time_local - timedelta(days=7)
        stats["recent_prescriptions"] = Prescription.query.filter(
            Prescription.created_at >= seven_days_ago.replace(tzinfo=None)
        ).count()

    # Unread messages (common for both roles)
    stats["unread_messages"] = InternalMessage.query.filter(
        and_(
            InternalMessage.recipient_id == current_user.id,
            InternalMessage.is_read == False,
            InternalMessage.is_deleted_by_recipient == False,
        )
    ).count()

    return stats
