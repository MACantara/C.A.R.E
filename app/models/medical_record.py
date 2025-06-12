from app import db
from datetime import datetime
from enum import Enum
from sqlalchemy import Index


class RecordType(Enum):
    CONSULTATION = "consultation"
    DIAGNOSIS = "diagnosis"
    PRESCRIPTION = "prescription"
    LAB_RESULT = "lab_result"
    IMAGING = "imaging"
    SURGERY = "surgery"
    VACCINATION = "vaccination"
    ALLERGY = "allergy"
    CHRONIC_CONDITION = "chronic_condition"


class ConsultationStatus(Enum):
    DRAFT = "draft"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    AMENDED = "amended"


class PrescriptionStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"
    EXPIRED = "expired"


class MedicalRecord(db.Model):
    __tablename__ = "medical_records"

    id = db.Column(db.Integer, primary_key=True)

    # Patient and doctor information
    patient_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    doctor_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=True
    )

    # Record details
    record_type = db.Column(db.Enum(RecordType), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # Clinical information
    chief_complaint = db.Column(db.Text, nullable=True)
    symptoms = db.Column(db.Text, nullable=True)
    diagnosis = db.Column(db.Text, nullable=True)
    treatment_plan = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Vital signs
    temperature = db.Column(db.Float, nullable=True)  # Celsius
    blood_pressure_systolic = db.Column(db.Integer, nullable=True)
    blood_pressure_diastolic = db.Column(db.Integer, nullable=True)
    heart_rate = db.Column(db.Integer, nullable=True)  # BPM
    respiratory_rate = db.Column(db.Integer, nullable=True)  # per minute
    weight = db.Column(db.Float, nullable=True)  # kg
    height = db.Column(db.Float, nullable=True)  # cm

    # Metadata
    record_date = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    patient = db.relationship(
        "User", foreign_keys=[patient_id], backref="medical_records"
    )
    doctor = db.relationship(
        "User", foreign_keys=[doctor_id], backref="created_records"
    )
    appointment = db.relationship("Appointment", backref="medical_records")

    @property
    def bmi(self):
        """Calculate BMI if height and weight are available."""
        if self.height and self.weight and self.height > 0:
            height_m = self.height / 100  # Convert cm to meters
            return round(self.weight / (height_m**2), 1)
        return None

    @property
    def blood_pressure(self):
        """Get formatted blood pressure reading."""
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"
        return None

    def __repr__(self):
        return (
            f"<MedicalRecord {self.id}: {self.title} for {self.patient.display_name}>"
        )


# Add composite index for efficient queries
Index(
    "idx_medical_records_patient_date",
    MedicalRecord.patient_id,
    MedicalRecord.record_date.desc(),
)
Index(
    "idx_medical_records_doctor_date",
    MedicalRecord.doctor_id,
    MedicalRecord.record_date.desc(),
)


class Consultation(db.Model):
    __tablename__ = "consultations"

    id = db.Column(db.Integer, primary_key=True)

    # References
    patient_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    doctor_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=True
    )

    # Consultation details
    consultation_date = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    status = db.Column(
        db.Enum(ConsultationStatus), default=ConsultationStatus.DRAFT, nullable=False
    )

    # Clinical information
    chief_complaint = db.Column(db.Text, nullable=False)
    history_present_illness = db.Column(db.Text, nullable=True)
    past_medical_history = db.Column(db.Text, nullable=True)
    family_history = db.Column(db.Text, nullable=True)
    social_history = db.Column(db.Text, nullable=True)

    # Physical examination
    general_appearance = db.Column(db.Text, nullable=True)
    physical_examination = db.Column(db.Text, nullable=True)

    # Assessment and plan
    assessment = db.Column(db.Text, nullable=True)
    differential_diagnosis = db.Column(db.Text, nullable=True)
    treatment_plan = db.Column(db.Text, nullable=True)
    follow_up_instructions = db.Column(db.Text, nullable=True)

    # Next appointment
    next_appointment_recommended = db.Column(db.Boolean, default=False)
    next_appointment_timeframe = db.Column(db.String(100), nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    patient = db.relationship(
        "User", foreign_keys=[patient_id], backref="consultations"
    )
    doctor = db.relationship(
        "User", foreign_keys=[doctor_id], backref="doctor_consultations"
    )
    appointment = db.relationship("Appointment", backref="consultation", uselist=False)

    def complete_consultation(self):
        """Mark consultation as completed."""
        self.status = ConsultationStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def __repr__(self):
        return f"<Consultation {self.id}: {self.patient.display_name} on {self.consultation_date}>"


class Prescription(db.Model):
    __tablename__ = "prescriptions"

    id = db.Column(db.Integer, primary_key=True)

    # References
    patient_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    doctor_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    consultation_id = db.Column(
        db.Integer, db.ForeignKey("consultations.id"), nullable=True
    )

    # Prescription details
    medication_name = db.Column(db.String(200), nullable=False, index=True)
    generic_name = db.Column(db.String(200), nullable=True)
    dosage = db.Column(db.String(100), nullable=False)
    frequency = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50), nullable=True)

    # Instructions
    instructions = db.Column(db.Text, nullable=True)
    warnings = db.Column(db.Text, nullable=True)
    indication = db.Column(db.String(500), nullable=True)

    # Status and dates
    status = db.Column(
        db.Enum(PrescriptionStatus), default=PrescriptionStatus.ACTIVE, nullable=False
    )
    prescribed_date = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    patient = db.relationship(
        "User", foreign_keys=[patient_id], backref="prescriptions"
    )
    doctor = db.relationship(
        "User", foreign_keys=[doctor_id], backref="prescribed_medications"
    )
    consultation = db.relationship("Consultation", backref="prescriptions")

    @property
    def is_active(self):
        """Check if prescription is currently active."""
        return self.status == PrescriptionStatus.ACTIVE

    @property
    def is_expired(self):
        """Check if prescription has expired."""
        if self.end_date:
            return datetime.now().date() > self.end_date
        return False

    def discontinue(self, reason=None):
        """Discontinue the prescription."""
        self.status = PrescriptionStatus.DISCONTINUED
        self.updated_at = datetime.utcnow()
        if reason:
            self.instructions = f"DISCONTINUED: {reason}\n\n{self.instructions or ''}"

    def __repr__(self):
        return f"<Prescription {self.id}: {self.medication_name} for {self.patient.display_name}>"


class Allergy(db.Model):
    __tablename__ = "allergies"

    id = db.Column(db.Integer, primary_key=True)

    # References
    patient_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Allergy details
    allergen = db.Column(db.String(200), nullable=False, index=True)
    allergy_type = db.Column(
        db.String(100), nullable=True
    )  # drug, food, environmental, etc.
    severity = db.Column(
        db.String(50), nullable=True
    )  # mild, moderate, severe, life-threatening
    reaction = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Metadata
    recorded_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    patient = db.relationship("User", foreign_keys=[patient_id], backref="allergies")
    recorder = db.relationship("User", foreign_keys=[recorded_by])

    def __repr__(self):
        return f"<Allergy {self.id}: {self.allergen} for {self.patient.display_name}>"


class VitalSigns(db.Model):
    __tablename__ = "vital_signs"

    id = db.Column(db.Integer, primary_key=True)

    # References
    patient_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    consultation_id = db.Column(
        db.Integer, db.ForeignKey("consultations.id"), nullable=True
    )

    # Vital signs
    temperature = db.Column(db.Float, nullable=True)  # Celsius
    blood_pressure_systolic = db.Column(db.Integer, nullable=True)
    blood_pressure_diastolic = db.Column(db.Integer, nullable=True)
    heart_rate = db.Column(db.Integer, nullable=True)  # BPM
    respiratory_rate = db.Column(db.Integer, nullable=True)  # per minute
    oxygen_saturation = db.Column(db.Float, nullable=True)  # %
    weight = db.Column(db.Float, nullable=True)  # kg
    height = db.Column(db.Float, nullable=True)  # cm

    # Additional measurements
    pain_scale = db.Column(db.Integer, nullable=True)  # 1-10
    notes = db.Column(db.Text, nullable=True)

    # Metadata
    recorded_date = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = db.relationship("User", foreign_keys=[patient_id], backref="vital_signs")
    recorder = db.relationship("User", foreign_keys=[recorded_by])
    consultation = db.relationship("Consultation", backref="vital_signs")

    @property
    def bmi(self):
        """Calculate BMI if height and weight are available."""
        if self.height and self.weight and self.height > 0:
            height_m = self.height / 100  # Convert cm to meters
            return round(self.weight / (height_m**2), 1)
        return None

    @property
    def blood_pressure(self):
        """Get formatted blood pressure reading."""
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"
        return None

    def __repr__(self):
        return f"<VitalSigns {self.id}: {self.patient.display_name} on {self.recorded_date}>"
