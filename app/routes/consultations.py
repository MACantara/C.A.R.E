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
from datetime import datetime, date
from app import db
from app.utils.timezone_utils import get_user_timezone, localize_datetime, get_current_time
from app.models.medical_record import (
    Consultation,
    VitalSigns,
    ConsultationStatus,
)
from app.models.user import User
from app.models.appointment import Appointment
from app.utils.sidebar_utils import get_sidebar_stats
from functools import wraps

consultations_bp = Blueprint("consultations", __name__, url_prefix="/consultations")


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


@consultations_bp.route("/new")
@doctor_required
def new_consultation():
    """Create new consultation form."""
    # Get user's timezone
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)

    # Get sidebar statistics
    stats = get_sidebar_stats()

    patient_id = request.args.get("patient_id")
    appointment_id = request.args.get("appointment_id")
    chief_complaint = ""

    patient = None
    appointment = None
    existing_consultation = None
    existing_vital_signs = None

    if patient_id:
        patient = User.query.filter_by(id=patient_id, role="patient").first()

    if appointment_id:
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            patient = appointment.patient
            # Auto-fill the chief complaint from the appointment
            chief_complaint = appointment.chief_complaint or ""
            
            # Check for existing consultation (draft or completed)
            existing_consultation = Consultation.query.filter_by(
                appointment_id=appointment_id,
                doctor_id=current_user.id
            ).first()
            
            # If there's an existing consultation, get its vital signs too
            if existing_consultation:
                existing_vital_signs = VitalSigns.query.filter_by(
                    consultation_id=existing_consultation.id
                ).first()

    # Get all patients for selection
    patients = (
        User.query.filter_by(role="patient", active=True)
        .order_by(User.last_name, User.first_name)
        .all()
    )

    return render_template(
        "medical_dashboard/medical_records/consultation_form.html",
        patient=patient,
        appointment=appointment,
        patients=patients,
        chief_complaint=chief_complaint,
        existing_consultation=existing_consultation,
        existing_vital_signs=existing_vital_signs,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
        stats=stats,
    )


@consultations_bp.route("/new", methods=["POST"])
@doctor_required
def create_consultation():
    """Create new consultation."""
    patient_id = request.form.get("patient_id")
    appointment_id = request.form.get("appointment_id") or None
    consultation_id = request.form.get("consultation_id") or None  # For updating existing

    # Validation
    if not patient_id:
        flash("Please select a patient.", "error")
        return redirect(url_for("consultations.new_consultation"))

    patient = User.query.filter_by(id=patient_id, role="patient").first()
    if not patient:
        flash("Invalid patient selected.", "error")
        return redirect(url_for("consultations.new_consultation"))

    try:
        # Check if we're updating an existing consultation
        if consultation_id:
            consultation = Consultation.query.get(consultation_id)
            if not consultation or consultation.doctor_id != current_user.id:
                flash("Invalid consultation.", "error")
                return redirect(url_for("consultations.new_consultation"))
            
            # Update existing consultation
            consultation.chief_complaint = request.form.get("chief_complaint", "").strip()
            consultation.history_present_illness = request.form.get("history_present_illness", "").strip()
            consultation.past_medical_history = request.form.get("past_medical_history", "").strip()
            consultation.family_history = request.form.get("family_history", "").strip()
            consultation.social_history = request.form.get("social_history", "").strip()
            consultation.general_appearance = request.form.get("general_appearance", "").strip()
            consultation.physical_examination = request.form.get("physical_examination", "").strip()
            consultation.assessment = request.form.get("assessment", "").strip()
            consultation.differential_diagnosis = request.form.get("differential_diagnosis", "").strip()
            consultation.treatment_plan = request.form.get("treatment_plan", "").strip()
            consultation.follow_up_instructions = request.form.get("follow_up_instructions", "").strip()
            consultation.next_appointment_recommended = bool(request.form.get("next_appointment_recommended"))
            consultation.next_appointment_timeframe = request.form.get("next_appointment_timeframe", "").strip()
            consultation.status = (
                ConsultationStatus.COMPLETED
                if request.form.get("complete_consultation")
                else ConsultationStatus.DRAFT
            )
            consultation.updated_at = get_current_time().replace(tzinfo=None)
        else:
            # Create new consultation
            consultation = Consultation(
                patient_id=patient_id,
                doctor_id=current_user.id,
                appointment_id=appointment_id,
                chief_complaint=request.form.get("chief_complaint", "").strip(),
                history_present_illness=request.form.get("history_present_illness", "").strip(),
                past_medical_history=request.form.get("past_medical_history", "").strip(),
                family_history=request.form.get("family_history", "").strip(),
                social_history=request.form.get("social_history", "").strip(),
                general_appearance=request.form.get("general_appearance", "").strip(),
                physical_examination=request.form.get("physical_examination", "").strip(),
                assessment=request.form.get("assessment", "").strip(),
                differential_diagnosis=request.form.get("differential_diagnosis", "").strip(),
                treatment_plan=request.form.get("treatment_plan", "").strip(),
                follow_up_instructions=request.form.get("follow_up_instructions", "").strip(),
                next_appointment_recommended=bool(request.form.get("next_appointment_recommended")),
                next_appointment_timeframe=request.form.get("next_appointment_timeframe", "").strip(),
                status=(
                    ConsultationStatus.COMPLETED
                    if request.form.get("complete_consultation")
                    else ConsultationStatus.DRAFT
                ),
            )
            db.session.add(consultation)

        db.session.commit()

        # Handle vital signs - update existing or create new
        if any([
            request.form.get("temperature"),
            request.form.get("blood_pressure_systolic"),
            request.form.get("heart_rate"),
            request.form.get("weight"),
        ]):
            # Check for existing vital signs
            existing_vitals = VitalSigns.query.filter_by(consultation_id=consultation.id).first()
            
            if existing_vitals:
                # Update existing vital signs
                existing_vitals.temperature = (
                    float(request.form.get("temperature"))
                    if request.form.get("temperature")
                    else None
                )
                existing_vitals.blood_pressure_systolic = (
                    int(request.form.get("blood_pressure_systolic"))
                    if request.form.get("blood_pressure_systolic")
                    else None
                )
                existing_vitals.blood_pressure_diastolic = (
                    int(request.form.get("blood_pressure_diastolic"))
                    if request.form.get("blood_pressure_diastolic")
                    else None
                )
                existing_vitals.heart_rate = (
                    int(request.form.get("heart_rate"))
                    if request.form.get("heart_rate")
                    else None
                )
                existing_vitals.respiratory_rate = (
                    int(request.form.get("respiratory_rate"))
                    if request.form.get("respiratory_rate")
                    else None
                )
                existing_vitals.oxygen_saturation = (
                    float(request.form.get("oxygen_saturation"))
                    if request.form.get("oxygen_saturation")
                    else None
                )
                existing_vitals.weight = (
                    float(request.form.get("weight"))
                    if request.form.get("weight")
                    else None
                )
                existing_vitals.height = (
                    float(request.form.get("height"))
                    if request.form.get("height")
                    else None
                )
                existing_vitals.pain_scale = (
                    int(request.form.get("pain_scale"))
                    if request.form.get("pain_scale")
                    else None
                )
                existing_vitals.notes = request.form.get("vital_notes", "").strip()
                existing_vitals.recorded_date = get_current_time().replace(tzinfo=None)
            else:
                # Create new vital signs
                vital_signs = VitalSigns(
                    patient_id=patient_id,
                    recorded_by=current_user.id,
                    consultation_id=consultation.id,
                    temperature=(
                        float(request.form.get("temperature"))
                        if request.form.get("temperature")
                        else None
                    ),
                    blood_pressure_systolic=(
                        int(request.form.get("blood_pressure_systolic"))
                        if request.form.get("blood_pressure_systolic")
                        else None
                    ),
                    blood_pressure_diastolic=(
                        int(request.form.get("blood_pressure_diastolic"))
                        if request.form.get("blood_pressure_diastolic")
                        else None
                    ),
                    heart_rate=(
                        int(request.form.get("heart_rate"))
                        if request.form.get("heart_rate")
                        else None
                    ),
                    respiratory_rate=(
                        int(request.form.get("respiratory_rate"))
                        if request.form.get("respiratory_rate")
                        else None
                    ),
                    oxygen_saturation=(
                        float(request.form.get("oxygen_saturation"))
                        if request.form.get("oxygen_saturation")
                        else None
                    ),
                    weight=(
                        float(request.form.get("weight"))
                        if request.form.get("weight")
                        else None
                    ),
                    height=(
                        float(request.form.get("height"))
                        if request.form.get("height")
                        else None
                    ),
                    pain_scale=(
                        int(request.form.get("pain_scale"))
                        if request.form.get("pain_scale")
                        else None
                    ),
                    notes=request.form.get("vital_notes", "").strip(),
                )
                db.session.add(vital_signs)
            
            db.session.commit()

        action = "updated" if consultation_id else "recorded"
        flash(f"Consultation {action} for {patient.display_name}.", "success")
        return redirect(
            url_for("medical_records.patient_records", patient_id=patient_id)
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating/updating consultation: {e}")
        flash("Error recording consultation. Please try again.", "error")
        return redirect(url_for("consultations.new_consultation"))


@consultations_bp.route("/api/generate-sample")
@doctor_required
def generate_sample_consultation():
    """Generate sample consultation data for testing."""
    import random
    
    sample_data_sets = [
        {
            "chief_complaint": "Patient complains of runny nose, sneezing, and mild headache for the past 3 days.",
            "history_present_illness": "Patient developed rhinorrhea and sneezing 3 days ago. No fever, but reports mild frontal headache. Symptoms worse in the morning. No cough or sore throat.",
            "assessment": "Upper respiratory tract infection (common cold). Viral etiology most likely.",
            "treatment_plan": "Symptomatic treatment with rest, fluids, and over-the-counter decongestants. Saline nasal rinses recommended.",
            "vitals": {
                "temperature": 36.8,
                "bp_systolic": 118,
                "bp_diastolic": 76,
                "heart_rate": 72,
                "pain_scale": 2
            }
        },
        {
            "chief_complaint": "Follow-up visit for hypertension management. Patient reports good adherence to medications.",
            "history_present_illness": "Patient diagnosed with hypertension 6 months ago. Currently on lisinopril 10mg daily. Reports good medication compliance. No side effects noted.",
            "assessment": "Hypertension, well-controlled on current medication regimen.",
            "treatment_plan": "Continue current lisinopril 10mg daily. Maintain low-sodium diet and regular exercise.",
            "vitals": {
                "temperature": 36.5,
                "bp_systolic": 128,
                "bp_diastolic": 82,
                "heart_rate": 68,
                "pain_scale": 0
            }
        },
        {
            "chief_complaint": "Patient presents with nausea, vomiting, and diarrhea for 2 days.",
            "history_present_illness": "Sudden onset of nausea and vomiting 2 days ago, followed by watery diarrhea. 4-5 episodes of vomiting yesterday, 6-7 loose stools today.",
            "assessment": "Acute gastroenteritis, likely viral or food-borne illness.",
            "treatment_plan": "Supportive care with oral rehydration. BRAT diet when tolerated. Probiotics recommended.",
            "vitals": {
                "temperature": 37.2,
                "bp_systolic": 110,
                "bp_diastolic": 70,
                "heart_rate": 88,
                "pain_scale": 4
            }
        }
    ]
    
    return jsonify(random.choice(sample_data_sets))
