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


class MessagePriority(enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageType(enum.Enum):
    GENERAL = "general"
    QUEUE_UPDATE = "queue_update"
    APPOINTMENT = "appointment"
    PATIENT_INFO = "patient_info"
    SYSTEM = "system"


class InternalMessage(db.Model):
    """Internal messaging system for doctors and staff."""

    __tablename__ = "internal_messages"

    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(
        Enum(MessageType), default=MessageType.GENERAL, nullable=False
    )
    priority = Column(
        Enum(MessagePriority), default=MessagePriority.NORMAL, nullable=False
    )
    is_read = Column(Boolean, default=False, nullable=False)
    is_deleted_by_sender = Column(Boolean, default=False, nullable=False)
    is_deleted_by_recipient = Column(Boolean, default=False, nullable=False)
    related_appointment_id = Column(
        Integer, ForeignKey("appointments.id"), nullable=True
    )
    related_patient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    recipient = relationship(
        "User", foreign_keys=[recipient_id], backref="received_messages"
    )
    related_appointment = relationship("Appointment", backref="related_messages")
    related_patient = relationship("User", foreign_keys=[related_patient_id])

    def __repr__(self):
        return f"<Message {self.subject} from {self.sender.username} to {self.recipient.username}>"

    def mark_as_read(self):
        """Mark message as read."""
        self.is_read = True
        self.read_at = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        """Convert message to dictionary for JSON responses."""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": f"{self.sender.first_name} {self.sender.last_name}",
            "sender_role": self.sender.role,
            "recipient_id": self.recipient_id,
            "recipient_name": f"{self.recipient.first_name} {self.recipient.last_name}",
            "subject": self.subject,
            "content": self.content,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "is_read": self.is_read,
            "related_appointment_id": self.related_appointment_id,
            "related_patient_id": self.related_patient_id,
            "created_at": self.created_at.isoformat(),
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }


class MessageThread(db.Model):
    """Group related messages into threads."""

    __tablename__ = "message_threads"

    id = Column(Integer, primary_key=True)
    subject = Column(String(200), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    created_by = relationship("User", backref="created_threads")

    def __repr__(self):
        return f"<MessageThread {self.subject}>"
