from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.utils.timezone_utils import get_user_timezone, get_current_time
from app.models.medical_record import (
    Prescription,
    Consultation,
)
from app.models.user import User
from app.utils.sidebar_utils import get_sidebar_stats
from functools import wraps

prescriptions_bp = Blueprint("prescriptions", __name__, url_prefix="/prescriptions")


def doctor_required(f):
    """Decorator to require doctor access."""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role not in ["doctor", "admin"]:
            flash("Access denied. Doctor privileges required.", "error")
            return redirect(url_for("main.home"))

        return f(*args, **kwargs)

    return decorated_function


@prescriptions_bp.route("/new")
@doctor_required
def new_prescription():
    """Create new prescription form."""
    # Get user's timezone
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)

    # Get sidebar statistics
    stats = get_sidebar_stats()

    patient_id = request.args.get("patient_id")
    consultation_id = request.args.get("consultation_id")

    patient = None
    consultation = None

    if patient_id:
        patient = User.query.filter_by(id=patient_id, role="patient").first()

    if consultation_id:
        consultation = Consultation.query.get(consultation_id)
        if consultation:
            patient = consultation.patient

    # Get all patients for selection if no specific patient
    patients = (
        User.query.filter_by(role="patient", active=True)
        .order_by(User.last_name, User.first_name)
        .all()
    )

    return render_template(
        "medical_dashboard/medical_records/prescription_form.html",
        patient=patient,
        consultation=consultation,
        patients=patients,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
        stats=stats,
    )


@prescriptions_bp.route("/new", methods=["POST"])
@doctor_required
def create_prescription():
    """Create new prescription."""
    patient_id = request.form.get("patient_id")
    consultation_id = request.form.get("consultation_id") or None

    # Validation
    if not patient_id:
        flash("Please select a patient.", "error")
        return redirect(url_for("prescriptions.new_prescription"))

    medication_name = request.form.get("medication_name", "").strip()
    dosage = request.form.get("dosage", "").strip()
    frequency = request.form.get("frequency", "").strip()
    duration = request.form.get("duration", "").strip()

    if not all([medication_name, dosage, frequency, duration]):
        flash("Please provide all required prescription details.", "error")
        return redirect(url_for("prescriptions.new_prescription"))

    try:
        prescription = Prescription(
            patient_id=patient_id,
            doctor_id=current_user.id,
            consultation_id=consultation_id,
            medication_name=medication_name,
            generic_name=request.form.get("generic_name", "").strip(),
            dosage=dosage,
            frequency=frequency,
            duration=duration,
            quantity=request.form.get("quantity", "").strip(),
            instructions=request.form.get("instructions", "").strip(),
            warnings=request.form.get("warnings", "").strip(),
            indication=request.form.get("indication", "").strip(),
            start_date=(
                datetime.strptime(request.form.get("start_date"), "%Y-%m-%d").date()
                if request.form.get("start_date")
                else None
            ),
            end_date=(
                datetime.strptime(request.form.get("end_date"), "%Y-%m-%d").date()
                if request.form.get("end_date")
                else None
            ),
        )

        db.session.add(prescription)
        db.session.commit()

        # Mark the appointment as completed if this prescription came from a consultation
        if consultation_id:
            consultation = Consultation.query.get(consultation_id)
            if consultation and consultation.appointment_id:
                appointment = consultation.appointment
                if appointment and appointment.status.value != 'completed':
                    from app.models.appointment import AppointmentStatus
                    appointment.status = AppointmentStatus.COMPLETED
                    appointment.completed_at = get_current_time().replace(tzinfo=None)
                    db.session.commit()

        patient = User.query.get(patient_id)
        
        # Provide different success messages based on context
        if consultation_id:
            flash(f"Prescription created for {patient.display_name} following consultation.", "success")
        else:
            flash(f"Prescription created for {patient.display_name}.", "success")
        
        # Always redirect to patient records after prescription creation
        return redirect(
            url_for("medical_records.patient_records", patient_id=patient_id)
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating prescription: {e}")
        flash("Error creating prescription. Please try again.", "error")
        return redirect(url_for("prescriptions.new_prescription"))


@prescriptions_bp.route("/<int:prescription_id>/discontinue", methods=["POST"])
@doctor_required
def discontinue_prescription(prescription_id):
    """Discontinue a prescription."""
    prescription = Prescription.query.get_or_404(prescription_id)

    # Check if current doctor can modify this prescription
    if prescription.doctor_id != current_user.id and not current_user.is_admin:
        flash("You can only modify your own prescriptions.", "error")
        return redirect(
            url_for(
                "medical_records.patient_records", patient_id=prescription.patient_id
            )
        )

    reason = request.form.get("reason", "").strip()

    try:
        prescription.discontinue(reason)
        db.session.commit()

        flash(
            f"Prescription for {prescription.medication_name} has been discontinued.",
            "success",
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error discontinuing prescription: {e}")
        flash("Error discontinuing prescription. Please try again.", "error")

    return redirect(
        url_for("medical_records.patient_records", patient_id=prescription.patient_id)
    )
