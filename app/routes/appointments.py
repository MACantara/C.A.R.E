from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
)
from flask_login import login_required, current_user
from datetime import datetime, timedelta, date
from app import db
from app.utils.timezone_utils import get_current_time, localize_datetime, get_user_timezone
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.user import User
from app.models.medical_record import Consultation, Prescription, VitalSigns, Allergy
from app.utils.email_utils import (
    send_appointment_confirmation,
)
from app.utils.sidebar_utils import get_sidebar_stats
import calendar

appointments_bp = Blueprint("appointments", __name__, url_prefix="/appointments")


@appointments_bp.route("/")
@login_required
def index():
    """Main appointments page - different view based on user role."""
    if current_app.config.get("DISABLE_DATABASE", False):
        flash(
            "Appointments are not available in this deployment environment.", "warning"
        )
        return redirect(url_for("main.home"))

    if current_user.role == "patient":
        return redirect(url_for("appointments.patient_appointments"))
    elif current_user.role in ["doctor", "staff"]:
        return redirect(url_for("appointments.doctor_schedule"))
    else:
        return redirect(url_for("appointments.admin_view"))


@appointments_bp.route("/book")
@login_required
def book_appointment():
    """Book new appointment form - patients only."""
    if current_user.role != "patient":
        flash("Only patients can book appointments.", "error")
        return redirect(url_for("appointments.index"))

    # Get all doctors
    doctors = User.query.filter_by(role="doctor", active=True).all()

    return render_template("appointments/book.html", doctors=doctors)


@appointments_bp.route("/book", methods=["POST"])
@login_required
def book_appointment_post():
    """Process appointment booking."""
    if current_user.role != "patient":
        flash("Only patients can book appointments.", "error")
        return redirect(url_for("appointments.index"))

    doctor_id = request.form.get("doctor_id")
    appointment_date_str = request.form.get("appointment_date")
    appointment_time_str = request.form.get("appointment_time")
    appointment_type = request.form.get("appointment_type", "consultation")
    chief_complaint = request.form.get("chief_complaint", "").strip()
    duration = int(request.form.get("duration", 30))

    # Validation
    errors = []

    if not doctor_id:
        errors.append("Please select a doctor.")

    if not appointment_date_str or not appointment_time_str:
        errors.append("Please select appointment date and time.")

    if not chief_complaint:
        errors.append("Please provide the reason for your visit.")

    try:
        # Parse datetime
        appointment_datetime_str = f"{appointment_date_str} {appointment_time_str}"
        appointment_datetime = datetime.strptime(
            appointment_datetime_str, "%Y-%m-%d %H:%M"
        )

        # Check if appointment is in the future (using timezone-aware current time)
        current_time = get_current_time()
        if appointment_datetime <= current_time.replace(tzinfo=None):
            errors.append("Appointment must be scheduled for a future date and time.")

        # Check if appointment is within business hours (9 AM - 5 PM)
        if appointment_datetime.hour < 9 or appointment_datetime.hour >= 17:
            errors.append("Appointments can only be scheduled between 9 AM and 5 PM.")

    except ValueError:
        errors.append("Invalid date or time format.")
        appointment_datetime = None

    # Verify doctor exists and is active
    doctor = User.query.filter_by(id=doctor_id, role="doctor", active=True).first()
    if not doctor:
        errors.append("Selected doctor is not available.")

    # Check for conflicts
    if doctor and appointment_datetime:
        if Appointment.has_conflict(doctor_id, appointment_datetime, duration):
            errors.append(
                "Selected time slot is not available. Please choose another time."
            )

    if errors:
        for error in errors:
            flash(error, "error")
        doctors = User.query.filter_by(role="doctor", active=True).all()
        return render_template(
            "appointments/book.html",
            doctors=doctors,
            user_timezone=get_user_timezone().zone,
            current_time_local=get_current_time(),
        )

    try:
        # Create appointment
        appointment = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            appointment_date=appointment_datetime,
            duration_minutes=duration,
            appointment_type=AppointmentType(appointment_type),
            chief_complaint=chief_complaint,
            status=AppointmentStatus.SCHEDULED,
        )

        db.session.add(appointment)
        db.session.commit()

        # Send confirmation email
        try:
            send_appointment_confirmation(appointment)
            appointment.confirmation_sent = True
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to send appointment confirmation: {e}")

        # Localize appointment time for display
        localized_time = localize_datetime(appointment_datetime)
        flash(
            f"Appointment booked successfully with Dr. {doctor.display_name} on {localized_time.strftime('%B %d, %Y at %I:%M %p %Z')}.",
            "success",
        )
        return redirect(url_for("appointments.patient_appointments"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error booking appointment: {e}")
        flash("Error booking appointment. Please try again.", "error")
        doctors = User.query.filter_by(role="doctor", active=True).all()
        return render_template(
            "appointments/book.html",
            doctors=doctors,
            user_timezone=get_user_timezone().zone,
            current_time_local=get_current_time(),
        )


@appointments_bp.route("/my-appointments")
@login_required
def patient_appointments():
    """View patient's appointments."""
    if current_user.role != "patient":
        flash("Access denied.", "error")
        return redirect(url_for("appointments.index"))

    page = request.args.get("page", 1, type=int)
    status_filter = request.args.get("status", "all")
    current_time = get_current_time()

    # Build query
    query = Appointment.query.filter_by(patient_id=current_user.id)

    if status_filter != "all":
        if status_filter == "upcoming":
            query = query.filter(
                Appointment.appointment_date >= current_time.replace(tzinfo=None),
                Appointment.status.in_(
                    [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
                ),
            )
        elif status_filter == "past":
            query = query.filter(
                Appointment.appointment_date < current_time.replace(tzinfo=None)
            )
        else:
            query = query.filter(Appointment.status == AppointmentStatus(status_filter))

    appointments = query.order_by(Appointment.appointment_date.desc()).paginate(
        page=page, per_page=10, error_out=False
    )

    return render_template(
        "appointments/patient_list.html",
        appointments=appointments,
        status_filter=status_filter,
        user_timezone=get_user_timezone().zone,
        current_time_local=current_time,
        localize_datetime=localize_datetime,
    )


@appointments_bp.route("/schedule")
@login_required
def doctor_schedule():
    """View doctor's schedule."""
    if current_user.role not in ["doctor", "staff"]:
        flash("Access denied.", "error")
        return redirect(url_for("appointments.index"))

    # Get filter from query params
    filter_type = request.args.get("filter", "today")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)  # Allow customizable per_page
    # Ensure per_page is within reasonable bounds
    per_page = max(10, min(100, per_page))
    
    current_time = get_current_time()
    user_tz = get_user_timezone()  # This returns a timezone object, not a string
    
    # Calculate date range based on filter
    if filter_type == "today":
        start_date = current_time.date()
        end_date = start_date
    elif filter_type == "tomorrow":
        start_date = current_time.date() + timedelta(days=1)
        end_date = start_date
    elif filter_type == "week":
        start_date = current_time.date()
        end_date = start_date + timedelta(days=7)
    elif filter_type == "month":
        start_date = current_time.date()
        end_date = start_date + timedelta(days=30)
    else:  # "all"
        start_date = None
        end_date = None

    # For staff, they might view other doctors' schedules
    doctor_id = request.args.get("doctor_id")
    if current_user.role == "staff" and doctor_id:
        doctor = User.query.filter_by(id=doctor_id, role="doctor", active=True).first()
        if not doctor:
            flash("Doctor not found.", "error")
            return redirect(url_for("appointments.doctor_schedule"))
    else:
        doctor = current_user if current_user.role == "doctor" else None

    # Build base query
    if not doctor:
        # Staff viewing general schedule
        base_query = Appointment.query.options(db.joinedload(Appointment.doctor), db.joinedload(Appointment.patient))
        doctors = User.query.filter_by(role="doctor", active=True).all()
    else:
        # Specific doctor's schedule
        base_query = Appointment.query.filter(Appointment.doctor_id == doctor.id).options(db.joinedload(Appointment.doctor), db.joinedload(Appointment.patient))
        doctors = [doctor]

    # Apply date filtering and pagination for all filters
    if start_date and end_date:
        if start_date == end_date:
            # Single day filter
            filtered_query = base_query.filter(
                db.func.date(Appointment.appointment_date) == start_date
            ).order_by(Appointment.appointment_date)
        else:
            # Multi-day filter (week/month)
            filtered_query = base_query.filter(
                Appointment.appointment_date >= datetime.combine(start_date, datetime.min.time()),
                Appointment.appointment_date <= datetime.combine(end_date, datetime.max.time())
            ).order_by(Appointment.appointment_date)
    else:
        # "all" filter
        filtered_query = base_query.order_by(Appointment.appointment_date.desc())

    # Apply pagination to all filters
    appointments_pagination = filtered_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    appointments = appointments_pagination.items

    # Get all doctors for staff dropdown
    all_doctors = (
        User.query.filter_by(role="doctor", active=True).all()
        if current_user.role == "staff"
        else []
    )

    # Organize appointments based on filter
    today = current_time.date()
    
    if filter_type == "today":
        # For today filter, show today's appointments in main section
        filtered_appointments = [apt for apt in appointments if apt.appointment_date.date() == today]
        # Show upcoming appointments (next 5 after today) in separate section
        if doctor:
            upcoming_query = Appointment.query.filter(
                Appointment.doctor_id == doctor.id,
                Appointment.appointment_date > datetime.combine(today, datetime.max.time()),
                Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
            ).options(db.joinedload(Appointment.doctor), db.joinedload(Appointment.patient)).order_by(Appointment.appointment_date).limit(5)
        else:
            upcoming_query = Appointment.query.filter(
                Appointment.appointment_date > datetime.combine(today, datetime.max.time()),
                Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
            ).options(db.joinedload(Appointment.doctor), db.joinedload(Appointment.patient)).order_by(Appointment.appointment_date).limit(5)
        upcoming_appointments = upcoming_query.all()
    else:
        # For other filters, show all filtered appointments in main section
        filtered_appointments = appointments
        # Don't show separate upcoming section for filtered views
        upcoming_appointments = []
    
    # Calculate stats for cards - get stats from all appointments (without pagination limits)
    if doctor:
        all_appointments_for_stats = Appointment.query.filter(Appointment.doctor_id == doctor.id).all()
    else:
        all_appointments_for_stats = Appointment.query.all()
    
    todays_appointments_count = len([apt for apt in all_appointments_for_stats if apt.appointment_date.date() == today])
    completed_today_count = len([apt for apt in all_appointments_for_stats if apt.appointment_date.date() == today and apt.status == AppointmentStatus.COMPLETED])
    
    # Get weekly appointments for stats
    week_start = today
    week_end = today + timedelta(days=7)
    weekly_appointments_count = len([
        apt for apt in all_appointments_for_stats
        if week_start <= apt.appointment_date.date() <= week_end
    ])

    # Get sidebar stats for medical dashboard template
    stats = get_sidebar_stats()

    return render_template(
        "medical_dashboard/appointments/schedule.html",
        filtered_appointments=filtered_appointments,  # Main appointments to display
        upcoming_appointments=upcoming_appointments,  # Only shown for "today" filter
        pagination=appointments_pagination,  # Pagination object for all filters
        todays_appointments_count=todays_appointments_count,
        completed_today_count=completed_today_count,
        weekly_appointments_count=weekly_appointments_count,
        filter_type=filter_type,
        doctor=doctor,
        doctors=all_doctors,
        user_timezone=user_tz.zone,
        user_tz=user_tz,
        current_time_local=current_time,
        localize_datetime=localize_datetime,
        stats=stats,
    )


@appointments_bp.route("/api/available-slots")
@login_required
def get_available_slots():
    """API endpoint to get available time slots for a doctor on a specific date."""
    doctor_id = request.args.get("doctor_id")
    date_str = request.args.get("date")
    duration = int(request.args.get("duration", 30))

    if not doctor_id or not date_str:
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        current_time = get_current_time()

        # Don't allow booking in the past
        if appointment_date < current_time.date():
            return jsonify({"slots": []})

        available_slots = Appointment.get_available_slots(
            doctor_id, appointment_date, duration
        )

        # Convert to time strings
        slot_strings = [slot.strftime("%H:%M") for slot in available_slots]

        return jsonify({"slots": slot_strings})

    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400
    except Exception as e:
        current_app.logger.error(f"Error getting available slots: {e}")
        return jsonify({"error": "Internal server error"}), 500


@appointments_bp.route("/<int:appointment_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    """Cancel an appointment."""
    appointment = Appointment.query.get_or_404(appointment_id)

    # Check permissions
    if current_user.role == "patient" and appointment.patient_id != current_user.id:
        flash("You can only cancel your own appointments.", "error")
        return redirect(url_for("appointments.index"))
    elif current_user.role == "doctor" and appointment.doctor_id != current_user.id:
        flash("You can only cancel your own appointments.", "error")
        return redirect(url_for("appointments.index"))
    elif current_user.role not in ["patient", "doctor", "staff", "admin"]:
        flash("Access denied.", "error")
        return redirect(url_for("appointments.index"))

    if not appointment.can_be_cancelled:
        flash("This appointment cannot be cancelled.", "error")
        return redirect(url_for("appointments.index"))

    reason = request.form.get("cancellation_reason", "").strip()

    try:
        appointment.cancel(reason)
        db.session.commit()

        flash("Appointment cancelled successfully.", "success")

        # Redirect based on user role
        if current_user.role == "patient":
            return redirect(url_for("appointments.patient_appointments"))
        else:
            return redirect(url_for("appointments.doctor_schedule"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling appointment: {e}")
        flash("Error cancelling appointment. Please try again.", "error")
        return redirect(url_for("appointments.index"))


@appointments_bp.route("/<int:appointment_id>/confirm", methods=["POST"])
@login_required
def confirm_appointment(appointment_id):
    """Confirm an appointment - doctors and staff only."""
    if current_user.role not in ["doctor", "staff"]:
        flash("Only healthcare professionals can confirm appointments.", "error")
        return redirect(url_for("appointments.index"))

    appointment = Appointment.query.get_or_404(appointment_id)

    # Check if doctor is confirming their own appointment
    if current_user.role == "doctor" and appointment.doctor_id != current_user.id:
        flash("You can only confirm your own appointments.", "error")
        return redirect(url_for("appointments.doctor_schedule"))

    try:
        appointment.confirm()
        db.session.commit()

        flash("Appointment confirmed successfully.", "success")
        return redirect(url_for("appointments.doctor_schedule"))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error confirming appointment: {e}")
        flash("Error confirming appointment. Please try again.", "error")
        return redirect(url_for("appointments.doctor_schedule"))


@appointments_bp.route("/<int:appointment_id>/update-status", methods=["POST"])
@login_required
def update_appointment_status(appointment_id):
    """Update appointment status - doctors and staff only, but only doctors can start consultations."""
    if current_user.role not in ["doctor", "staff"]:
        flash("Access denied.", "error")
        return redirect(url_for("appointments.index"))

    appointment = Appointment.query.get_or_404(appointment_id)
    new_status = request.form.get("status")

    if not new_status or new_status not in [
        status.value for status in AppointmentStatus
    ]:
        flash("Invalid status.", "error")
        return redirect(url_for("appointments.doctor_schedule"))

    # Only doctors can start consultations or mark appointments as in-progress
    if current_user.role == "staff" and new_status == AppointmentStatus.IN_PROGRESS.value:
        flash("Only doctors can start consultations.", "error")
        return redirect(url_for("appointments.doctor_schedule"))

    # Only doctors can complete appointments (as this typically involves consultation notes)
    if current_user.role == "staff" and new_status == AppointmentStatus.COMPLETED.value:
        flash("Only doctors can complete appointments.", "error")
        return redirect(url_for("appointments.doctor_schedule"))

    try:
        appointment.status = AppointmentStatus(new_status)
        appointment.updated_at = get_current_time().replace(tzinfo=None)

        # Set additional timestamps based on status
        if new_status == AppointmentStatus.IN_PROGRESS.value:
            appointment.mark_in_progress()
            db.session.commit()
            flash("Appointment started successfully.", "success")
            # Redirect to consultation form when starting an appointment
            return redirect(url_for('consultations.new_consultation', appointment_id=appointment.id))
        elif new_status == AppointmentStatus.COMPLETED.value:
            appointment.complete()
        elif new_status == AppointmentStatus.NO_SHOW.value:
            appointment.mark_no_show()

        db.session.commit()
        flash("Appointment status updated successfully.", "success")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating appointment status: {e}")
        flash("Error updating appointment status. Please try again.", "error")

    return redirect(url_for("appointments.doctor_schedule"))