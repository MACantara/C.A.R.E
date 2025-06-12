from datetime import datetime
from app import db
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Enum,
)
from sqlalchemy.orm import relationship
import enum


class QueueStatus(enum.Enum):
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    NO_SHOW = "no_show"


class PatientQueue(db.Model):
    """Patient queue management for real-time tracking."""

    __tablename__ = "patient_queue"

    id = Column(Integer, primary_key=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)
    queue_number = Column(Integer, nullable=False)
    status = Column(Enum(QueueStatus), default=QueueStatus.WAITING, nullable=False)
    estimated_wait_time = Column(Integer, default=0)  # minutes
    actual_start_time = Column(DateTime)
    actual_end_time = Column(DateTime)
    delay_reason = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    appointment = relationship("Appointment", backref="queue_entry")

    def __repr__(self):
        return f"<PatientQueue {self.queue_number}: {self.status.value}>"

    def to_dict(self):
        """Convert queue entry to dictionary for JSON responses."""
        return {
            "id": self.id,
            "appointment_id": self.appointment_id,
            "queue_number": self.queue_number,
            "status": self.status.value,
            "estimated_wait_time": self.estimated_wait_time,
            "actual_start_time": (
                self.actual_start_time.isoformat() if self.actual_start_time else None
            ),
            "actual_end_time": (
                self.actual_end_time.isoformat() if self.actual_end_time else None
            ),
            "delay_reason": self.delay_reason,
            "notes": self.notes,
            "patient_name": f"{self.appointment.patient.first_name} {self.appointment.patient.last_name}",
            "patient_id": self.appointment.patient.id,
            "doctor_name": f"Dr. {self.appointment.doctor.first_name} {self.appointment.doctor.last_name}",
            "appointment_time": self.appointment.appointment_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def update_status(self, new_status, delay_reason=None, notes=None):
        """Update queue status with automatic timing."""
        self.status = new_status
        self.updated_at = datetime.utcnow()

        if new_status == QueueStatus.IN_PROGRESS:
            self.actual_start_time = datetime.utcnow()
        elif new_status == QueueStatus.COMPLETED:
            self.actual_end_time = datetime.utcnow()
        elif new_status == QueueStatus.DELAYED:
            self.delay_reason = delay_reason

        if notes:
            self.notes = notes

        db.session.commit()
