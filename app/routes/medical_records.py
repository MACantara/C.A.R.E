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
from app import db, get_user_timezone, localize_datetime, get_current_time
from app.models.medical_record import (
    MedicalRecord,
    Consultation,
    Prescription,
    Allergy,
    VitalSigns,
    RecordType,
    ConsultationStatus,
    PrescriptionStatus,
)
from app.models.user import User
from app.models.appointment import Appointment
from app.routes.medical_dashboard import get_sidebar_stats
from sqlalchemy import or_, and_, desc, func
from functools import wraps

medical_records_bp = Blueprint(
    "medical_records", __name__, url_prefix="/medical-records"
)


def healthcare_professional_required(f):
    """Decorator to require healthcare professional access."""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_app.config.get("DISABLE_DATABASE", False):
            flash(
                "Medical records are not available in this deployment environment.",
                "warning",
            )
            return redirect(url_for("main.home"))

        if current_user.role not in ["doctor", "staff", "admin"]:
            flash(
                "Access denied. Healthcare professional privileges required.", "error"
            )
            return redirect(url_for("main.home"))

        return f(*args, **kwargs)

    return decorated_function


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


@medical_records_bp.route("/")
@healthcare_professional_required
def index():
    """Medical records dashboard."""
    # Get user's timezone for displaying timestamps
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)

    # Get sidebar statistics using the shared function
    stats = get_sidebar_stats()

    # Get recent records
    recent_records = (
        MedicalRecord.query.order_by(desc(MedicalRecord.created_at)).limit(10).all()
    )

    # Get recent consultations
    recent_consultations = (
        Consultation.query.order_by(desc(Consultation.consultation_date)).limit(5).all()
    )

    # Get statistics
    total_patients = User.query.filter_by(role="patient", active=True).count()
    total_records = MedicalRecord.query.count()
    today_consultations = Consultation.query.filter(
        func.date(Consultation.consultation_date) == date.today()
    ).count()

    stats = {
        "total_patients": total_patients,
        "total_records": total_records,
        "today_consultations": today_consultations,
        "pending_consultations": Consultation.query.filter_by(
            status=ConsultationStatus.DRAFT
        ).count(),
    }

    return render_template(
        "medical_dashboard/medical_records/dashboard.html",
        recent_records=recent_records,
        recent_consultations=recent_consultations,
        stats=stats,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
    )


@medical_records_bp.route("/patients")
@healthcare_professional_required
def patients():
    """List all patients with search functionality."""
    # Get user's timezone
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)

    # Get sidebar statistics
    stats = get_sidebar_stats()

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "").strip()

    # Build query
    query = User.query.filter_by(role="patient", active=True)

    if search:
        query = query.filter(
            or_(
                User.first_name.contains(search),
                User.last_name.contains(search),
                User.username.contains(search),
                User.email.contains(search),
            )
        )

    patients_pagination = query.order_by(User.last_name, User.first_name).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template(
        "medical_dashboard/medical_records/patients.html",
        patients=patients_pagination,
        search=search,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
        stats=stats,
    )


@medical_records_bp.route("/patient/<int:patient_id>")
@healthcare_professional_required
def patient_records(patient_id):
    """View all records for a specific patient."""
    # Get user's timezone
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)

    # Get sidebar statistics
    stats = get_sidebar_stats()

    patient = User.query.filter_by(id=patient_id, role="patient").first_or_404()

    # Get all medical records
    records = (
        MedicalRecord.query.filter_by(patient_id=patient_id)
        .order_by(desc(MedicalRecord.record_date))
        .all()
    )

    # Get consultations
    consultations = (
        Consultation.query.filter_by(patient_id=patient_id)
        .order_by(desc(Consultation.consultation_date))
        .all()
    )

    # Get prescriptions
    prescriptions = (
        Prescription.query.filter_by(patient_id=patient_id)
        .order_by(desc(Prescription.prescribed_date))
        .all()
    )

    # Get allergies
    allergies = Allergy.query.filter_by(patient_id=patient_id, is_active=True).all()

    # Get vital signs
    vital_signs = (
        VitalSigns.query.filter_by(patient_id=patient_id)
        .order_by(desc(VitalSigns.recorded_date))
        .limit(10)
        .all()
    )

    return render_template(
        "medical_dashboard/medical_records/patient_detail.html",
        patient=patient,
        records=records,
        consultations=consultations,
        prescriptions=prescriptions,
        allergies=allergies,
        vital_signs=vital_signs,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
        stats=stats,
    )


@medical_records_bp.route("/consultation/new")
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

    patient = None
    appointment = None

    if patient_id:
        patient = User.query.filter_by(id=patient_id, role="patient").first()

    if appointment_id:
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            patient = appointment.patient

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
        user_timezone=user_timezone,
        current_time_local=current_time_local,
        stats=stats,
    )


@medical_records_bp.route("/consultation/new", methods=["POST"])
@doctor_required
def create_consultation():
    """Create new consultation."""
    patient_id = request.form.get("patient_id")
    appointment_id = request.form.get("appointment_id") or None

    # Validation
    if not patient_id:
        flash("Please select a patient.", "error")
        return redirect(url_for("medical_records.new_consultation"))

    patient = User.query.filter_by(id=patient_id, role="patient").first()
    if not patient:
        flash("Invalid patient selected.", "error")
        return redirect(url_for("medical_records.new_consultation"))

    try:
        consultation = Consultation(
            patient_id=patient_id,
            doctor_id=current_user.id,
            appointment_id=appointment_id,
            chief_complaint=request.form.get("chief_complaint", "").strip(),
            history_present_illness=request.form.get(
                "history_present_illness", ""
            ).strip(),
            past_medical_history=request.form.get("past_medical_history", "").strip(),
            family_history=request.form.get("family_history", "").strip(),
            social_history=request.form.get("social_history", "").strip(),
            general_appearance=request.form.get("general_appearance", "").strip(),
            physical_examination=request.form.get("physical_examination", "").strip(),
            assessment=request.form.get("assessment", "").strip(),
            differential_diagnosis=request.form.get(
                "differential_diagnosis", ""
            ).strip(),
            treatment_plan=request.form.get("treatment_plan", "").strip(),
            follow_up_instructions=request.form.get(
                "follow_up_instructions", ""
            ).strip(),
            next_appointment_recommended=bool(
                request.form.get("next_appointment_recommended")
            ),
            next_appointment_timeframe=request.form.get(
                "next_appointment_timeframe", ""
            ).strip(),
            status=(
                ConsultationStatus.COMPLETED
                if request.form.get("complete_consultation")
                else ConsultationStatus.DRAFT
            ),
        )

        db.session.add(consultation)
        db.session.commit()

        # Record vital signs if provided
        if any(
            [
                request.form.get("temperature"),
                request.form.get("blood_pressure_systolic"),
                request.form.get("heart_rate"),
                request.form.get("weight"),
            ]
        ):
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

        flash(f"Consultation recorded for {patient.display_name}.", "success")
        return redirect(
            url_for("medical_records.patient_records", patient_id=patient_id)
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating consultation: {e}")
        flash("Error recording consultation. Please try again.", "error")
        return redirect(url_for("medical_records.new_consultation"))


@medical_records_bp.route("/prescription/new")
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


@medical_records_bp.route("/prescription/new", methods=["POST"])
@doctor_required
def create_prescription():
    """Create new prescription."""
    patient_id = request.form.get("patient_id")
    consultation_id = request.form.get("consultation_id") or None

    # Validation
    if not patient_id:
        flash("Please select a patient.", "error")
        return redirect(url_for("medical_records.new_prescription"))

    medication_name = request.form.get("medication_name", "").strip()
    dosage = request.form.get("dosage", "").strip()
    frequency = request.form.get("frequency", "").strip()
    duration = request.form.get("duration", "").strip()

    if not all([medication_name, dosage, frequency, duration]):
        flash("Please provide all required prescription details.", "error")
        return redirect(url_for("medical_records.new_prescription"))

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

        patient = User.query.get(patient_id)
        flash(f"Prescription created for {patient.display_name}.", "success")
        return redirect(
            url_for("medical_records.patient_records", patient_id=patient_id)
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating prescription: {e}")
        flash("Error creating prescription. Please try again.", "error")
        return redirect(url_for("medical_records.new_prescription"))


@medical_records_bp.route("/search")
@healthcare_professional_required
def search_records():
    """Search medical records."""
    # Get user's timezone
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)

    # Get sidebar statistics
    stats = get_sidebar_stats()

    query = request.args.get("q", "").strip()
    record_type = request.args.get("type", "")
    patient_name = request.args.get("patient", "").strip()
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    results = []

    if query or patient_name or date_from or date_to:
        # Build search query
        search_query = MedicalRecord.query

        if query:
            search_query = search_query.filter(
                or_(
                    MedicalRecord.title.contains(query),
                    MedicalRecord.description.contains(query),
                    MedicalRecord.diagnosis.contains(query),
                    MedicalRecord.chief_complaint.contains(query),
                )
            )

        if record_type:
            try:
                search_query = search_query.filter(
                    MedicalRecord.record_type == RecordType(record_type)
                )
            except ValueError:
                pass

        if patient_name:
            # Join with user table to search patient names
            search_query = search_query.join(
                User, MedicalRecord.patient_id == User.id
            ).filter(
                or_(
                    User.first_name.contains(patient_name),
                    User.last_name.contains(patient_name),
                    User.username.contains(patient_name),
                )
            )

        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
                search_query = search_query.filter(
                    MedicalRecord.record_date >= date_from_obj
                )
            except ValueError:
                pass

        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
                search_query = search_query.filter(
                    MedicalRecord.record_date <= date_to_obj
                )
            except ValueError:
                pass

        results = search_query.order_by(desc(MedicalRecord.record_date)).limit(50).all()

    return render_template(
        "medical_dashboard/medical_records/search.html",
        results=results,
        query=query,
        record_type=record_type,
        patient_name=patient_name,
        date_from=date_from,
        date_to=date_to,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
        stats=stats,
    )


@medical_records_bp.route("/api/patient-search")
@healthcare_professional_required
def api_patient_search():
    """API endpoint for patient search autocomplete."""
    query = request.args.get("q", "").strip()

    if len(query) < 2:
        return jsonify([])

    patients = (
        User.query.filter(
            User.role == "patient",
            User.active == True,
            or_(
                User.first_name.contains(query),
                User.last_name.contains(query),
                User.username.contains(query),
            ),
        )
        .limit(10)
        .all()
    )

    results = [
        {
            "id": patient.id,
            "name": patient.display_name,
            "username": patient.username,
            "email": patient.email,
        }
        for patient in patients
    ]

    return jsonify(results)


@medical_records_bp.route(
    "/prescription/<int:prescription_id>/discontinue", methods=["POST"]
)
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
