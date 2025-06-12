from app import db
from datetime import datetime, timedelta
from enum import Enum
import pytz


class AppointmentStatus(Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentType(Enum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    ROUTINE_CHECKUP = "routine_checkup"
    VACCINATION = "vaccination"
    PROCEDURE = "procedure"


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)

    # Foreign keys
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Appointment details
    appointment_date = db.Column(db.DateTime, nullable=False, index=True)
    duration_minutes = db.Column(db.Integer, default=30, nullable=False)
    appointment_type = db.Column(
        db.Enum(AppointmentType), default=AppointmentType.CONSULTATION, nullable=False
    )
    status = db.Column(
        db.Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False
    )

    # Appointment information
    chief_complaint = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    confirmed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancellation_reason = db.Column(db.String(500), nullable=True)

    # Relationships
    patient = db.relationship(
        "User", foreign_keys=[patient_id], backref="patient_appointments"
    )
    doctor = db.relationship(
        "User", foreign_keys=[doctor_id], backref="doctor_appointments"
    )

    # Notification tracking
    reminder_sent = db.Column(db.Boolean, default=False, nullable=False)
    confirmation_sent = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, **kwargs):
        super(Appointment, self).__init__(**kwargs)
        if self.appointment_date and self.duration_minutes is None:
            self.duration_minutes = 30

    @property
    def end_time(self):
        """Calculate appointment end time based on duration."""
        if self.appointment_date and self.duration_minutes:
            return self.appointment_date + timedelta(minutes=self.duration_minutes)
        return None

    @property
    def is_past(self):
        """Check if appointment is in the past."""
        return self.appointment_date < datetime.utcnow()

    @property
    def is_today(self):
        """Check if appointment is today."""
        today = datetime.utcnow().date()
        return self.appointment_date.date() == today

    @property
    def is_upcoming(self):
        """Check if appointment is upcoming (within next 24 hours)."""
        now = datetime.utcnow()
        return now <= self.appointment_date <= now + timedelta(hours=24)

    @property
    def time_until_appointment(self):
        """Get time remaining until appointment."""
        if self.appointment_date > datetime.utcnow():
            return self.appointment_date - datetime.utcnow()
        return timedelta(0)

    @property
    def can_be_cancelled(self):
        """Check if appointment can be cancelled (at least 2 hours in advance)."""
        if self.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
            return False
        return self.appointment_date > datetime.utcnow() + timedelta(hours=2)

    @property
    def can_be_rescheduled(self):
        """Check if appointment can be rescheduled."""
        return (
            self.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]
            and not self.is_past
        )

    def confirm(self):
        """Confirm the appointment."""
        self.status = AppointmentStatus.CONFIRMED
        self.confirmed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def cancel(self, reason=None):
        """Cancel the appointment."""
        self.status = AppointmentStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.cancellation_reason = reason
        self.updated_at = datetime.utcnow()

    def mark_in_progress(self):
        """Mark appointment as in progress."""
        self.status = AppointmentStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()

    def complete(self):
        """Mark appointment as completed."""
        self.status = AppointmentStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def mark_no_show(self):
        """Mark appointment as no show."""
        self.status = AppointmentStatus.NO_SHOW
        self.updated_at = datetime.utcnow()

    @staticmethod
    def get_available_slots(doctor_id, date, duration_minutes=30):
        """Get available appointment slots for a doctor on a specific date."""
        from app.models.user import User

        doctor = User.query.get(doctor_id)
        if not doctor or doctor.role != "doctor":
            return []

        # Define working hours (9 AM to 5 PM)
        start_hour = 9
        end_hour = 17

        # Create datetime objects for the day
        start_time = datetime.combine(
            date, datetime.min.time().replace(hour=start_hour)
        )
        end_time = datetime.combine(date, datetime.min.time().replace(hour=end_hour))

        # Get existing appointments for the doctor on this date
        existing_appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date >= start_time,
            Appointment.appointment_date < end_time + timedelta(days=1),
            Appointment.status.in_(
                [
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS,
                ]
            ),
        ).all()

        # Generate possible time slots
        available_slots = []
        current_time = start_time

        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            slot_end = current_time + timedelta(minutes=duration_minutes)

            # Check if this slot conflicts with existing appointments
            is_available = True
            for appointment in existing_appointments:
                if (
                    current_time < appointment.end_time
                    and slot_end > appointment.appointment_date
                ):
                    is_available = False
                    break

            if is_available:
                available_slots.append(current_time)

            current_time += timedelta(minutes=duration_minutes)

        return available_slots

    @staticmethod
    def has_conflict(
        doctor_id, appointment_date, duration_minutes, exclude_appointment_id=None
    ):
        """Check if there's a scheduling conflict for a doctor."""
        end_time = appointment_date + timedelta(minutes=duration_minutes)

        query = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(
                [
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS,
                ]
            ),
            Appointment.appointment_date < end_time,
            db.func.datetime(
                Appointment.appointment_date,
                "+" + db.cast(Appointment.duration_minutes, db.String) + " minutes",
            )
            > appointment_date,
        )

        if exclude_appointment_id:
            query = query.filter(Appointment.id != exclude_appointment_id)

        return query.first() is not None

    def __repr__(self):
        return f"<Appointment {self.id}: {self.patient.display_name} with {self.doctor.display_name} on {self.appointment_date}>"


class AppointmentReminder(db.Model):
    __tablename__ = "appointment_reminders"

    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(
        db.Integer, db.ForeignKey("appointments.id"), nullable=False
    )

    # Reminder details
    reminder_type = db.Column(db.String(50), nullable=False)  # email, sms
    reminder_time = db.Column(db.DateTime, nullable=False)  # when to send reminder
    sent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.String(20), default="pending", nullable=False
    )  # pending, sent, failed

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    appointment = db.relationship("Appointment", backref="reminders")

    def __repr__(self):
        return f"<AppointmentReminder {self.id}: {self.reminder_type} for appointment {self.appointment_id}>"
