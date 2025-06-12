from app import db
from datetime import datetime
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, HashingError
import secrets
from flask_login import UserMixin

ph = PasswordHasher()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Role-based access control
    role = db.Column(
        db.String(20), default="patient", nullable=False
    )  # patient, doctor, staff, admin
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Healthcare professional information
    license_number = db.Column(db.String(50), unique=True, nullable=True, index=True)
    specialization = db.Column(db.String(100), nullable=True)
    facility_name = db.Column(db.String(200), nullable=True)

    # Patient information
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    emergency_contact = db.Column(db.String(100), nullable=True)
    emergency_phone = db.Column(db.String(20), nullable=True)

    # Relationship with password reset tokens
    password_reset_tokens = db.relationship(
        "PasswordResetToken",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        """Hash and set password using Argon2."""
        try:
            self.password_hash = ph.hash(password)
        except HashingError:
            raise ValueError("Error hashing password")

    def check_password(self, password):
        """Verify password against stored hash."""
        try:
            ph.verify(self.password_hash, password)
            return True
        except VerifyMismatchError:
            return False

    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def generate_reset_token(self):
        """Generate a password reset token."""
        # Deactivate any existing tokens
        for token in self.password_reset_tokens:
            token.is_active = False

        # Create new token
        reset_token = PasswordResetToken(user_id=self.id)
        db.session.add(reset_token)
        db.session.commit()
        return reset_token.token

    def get_id(self):
        """Required by Flask-Login."""
        return str(self.id)

    @property
    def is_authenticated(self):
        """Required by Flask-Login."""
        return True

    @property
    def is_active(self):
        """Required by Flask-Login."""
        return self.active

    @property
    def full_name(self):
        """Get full name for patients."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    @property
    def display_name(self):
        """Get appropriate display name based on role."""
        if self.role == "patient" and self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.role in ["doctor", "staff"] and self.first_name and self.last_name:
            title = "Dr." if self.role == "doctor" else ""
            return f"{title} {self.first_name} {self.last_name}".strip()
        return self.username

    @property
    def is_healthcare_professional(self):
        """Check if user is a healthcare professional."""
        return self.role in ["doctor", "staff", "admin"]

    @property
    def is_patient(self):
        """Check if user is a patient."""
        return self.role == "patient"

    @property
    def is_doctor(self):
        """Check if user is a doctor."""
        return self.role == "doctor"

    @property
    def is_staff(self):
        """Check if user is staff."""
        return self.role == "staff"

    def has_role(self, role):
        """Check if user has specific role."""
        return self.role == role

    def has_permission(self, permission):
        """Check if user has specific permission based on role."""
        permissions = {
            "patient": ["view_own_records", "book_appointments"],
            "staff": ["view_patient_records", "manage_appointments", "manage_queue"],
            "doctor": [
                "view_patient_records",
                "manage_appointments",
                "write_prescriptions",
                "add_consultation_notes",
            ],
            "admin": ["all"],
        }

        user_permissions = permissions.get(self.role, [])
        return (
            permission in user_permissions or "all" in user_permissions or self.is_admin
        )

    def update_profile(self, **kwargs):
        """Update user profile information."""
        allowed_fields = [
            "first_name",
            "last_name",
            "phone_number",
            "address",
            "emergency_contact",
            "emergency_phone",
            "specialization",
            "facility_name",
            "license_number",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(self, field):
                setattr(self, field, value)

        db.session.commit()

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"  # Add explicit table name for consistency

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )  # Update foreign key reference
    token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    used_at = db.Column(db.DateTime)

    def __init__(self, user_id):
        self.user_id = user_id
        self.token = secrets.token_urlsafe(32)
        self.created_at = datetime.utcnow()
        # Token expires in 1 hour
        from datetime import timedelta

        self.expires_at = self.created_at + timedelta(hours=1)

    def is_valid(self):
        """Check if token is valid (active and not expired)."""
        return (
            self.is_active and not self.used_at and datetime.utcnow() < self.expires_at
        )

    def use_token(self):
        """Mark token as used."""
        self.used_at = datetime.utcnow()
        self.is_active = False
        db.session.commit()

    @staticmethod
    def find_valid_token(token):
        """Find a valid token by token string."""
        reset_token = PasswordResetToken.query.filter_by(token=token).first()
        if reset_token and reset_token.is_valid():
            return reset_token
        return None

    def __repr__(self):
        return f"<PasswordResetToken {self.token[:8]}...>"
