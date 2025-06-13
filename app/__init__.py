from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_login import LoginManager
from flask_socketio import SocketIO
from config import config
import os
import pytz
from datetime import datetime, timedelta, date

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
login_manager = LoginManager()
socketio = SocketIO()


def get_user_timezone():
    """Get user's timezone from session or default to Philippines timezone."""
    user_timezone = session.get("user_timezone", "Asia/Manila")
    try:
        return pytz.timezone(user_timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        return pytz.timezone("Asia/Manila")


def localize_datetime(dt, timezone=None):
    """Convert UTC datetime to user's timezone."""
    if dt is None:
        return None

    if timezone is None:
        timezone = get_user_timezone()

    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)

    return dt.astimezone(timezone)


def get_current_time(timezone=None):
    """Get current time in user's timezone."""
    if timezone is None:
        timezone = get_user_timezone()

    utc_now = datetime.utcnow()
    utc_dt = pytz.utc.localize(utc_now)
    return utc_dt.astimezone(timezone)


def create_app(config_name=None):
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.environ.get("FLASK_CONFIG", "default")
    app.config.from_object(config[config_name])

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        if app.config.get("DISABLE_DATABASE", False):
            return None
        try:
            from app.models.user import User

            return User.query.get(int(user_id))
        except:
            return None

    # Initialize extensions only if database is not disabled
    if not app.config.get("DISABLE_DATABASE", False):
        db.init_app(app)
        migrate.init_app(app, db)
    else:
        # Initialize a dummy db for compatibility
        db.init_app(app)

    # Initialize Flask-SocketIO
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    # Initialize Flask-Mail
    mail.init_app(app)

    # Initialize hCaptcha
    from app.utils.hcaptcha_utils import init_hcaptcha

    init_hcaptcha(app)

    # Import models to ensure they are registered with SQLAlchemy
    if not app.config.get("DISABLE_DATABASE", False):
        from app.models import Contact, User, PasswordResetToken
        from app.models.appointment import Appointment, AppointmentReminder
        from app.models.medical_record import (
            MedicalRecord,
            Consultation,
            Prescription,
            Allergy,
            VitalSigns,
        )
        from app.models.email_verification import EmailVerification
        from app.models.login_attempt import LoginAttempt

    # Register blueprints
    from app.routes import register_blueprints

    register_blueprints(app)

    # Create database tables only in non-Vercel environments
    with app.app_context():
        if not app.config.get("DISABLE_DATABASE", False):
            try:
                db.create_all()

                # Create default admin user if it doesn't exist
                from app.models.user import User
                from app.models.email_verification import EmailVerification

                admin_user = User.query.filter_by(username="admin").first()
                if not admin_user:
                    admin_user = User(
                        username="admin",
                        email="admin@care-system.com",
                        role="admin",
                        is_admin=True,
                        active=True,
                        first_name="System",
                        last_name="Administrator",
                        phone_number="+63 555 123-CARE",
                    )
                    admin_user.set_password("admin123")  # Change this in production!
                    db.session.add(admin_user)
                    db.session.commit()

                    # Create verified email verification for admin
                    admin_verification = EmailVerification(
                        user_id=admin_user.id, email=admin_user.email
                    )
                    db.session.add(admin_verification)
                    db.session.commit()
                    admin_verification.verify()

                    app.logger.info(
                        "Default admin user created: admin/admin123 (email verified)"
                    )
                else:
                    # Ensure existing admin has verified email
                    if not EmailVerification.is_email_verified(
                        admin_user.id, admin_user.email
                    ):
                        admin_verification = EmailVerification(
                            user_id=admin_user.id, email=admin_user.email
                        )
                        db.session.add(admin_verification)
                        db.session.commit()
                        admin_verification.verify()
                        app.logger.info("Admin email verification created and verified")

                # Create sample doctor user if it doesn't exist
                doctor_user = User.query.filter_by(username="doctor_sample").first()
                if not doctor_user:
                    doctor_user = User(
                        username="doctor_sample",
                        email="doctor@care-system.com",
                        role="doctor",
                        is_admin=False,
                        active=True,
                        first_name="Maria",
                        last_name="Santos",
                        phone_number="+63 555 DOC-1234",
                        license_number="MD-2024-001",
                        specialization="Internal Medicine",
                        facility_name="C.A.R.E. Medical Center",
                    )
                    doctor_user.set_password("doctor123")
                    db.session.add(doctor_user)
                    db.session.commit()

                    # Create verified email verification for doctor
                    doctor_verification = EmailVerification(
                        user_id=doctor_user.id, email=doctor_user.email
                    )
                    db.session.add(doctor_verification)
                    db.session.commit()
                    doctor_verification.verify()

                    app.logger.info(
                        "Sample doctor user created: doctor_sample/doctor123 (email verified)"
                    )

                # Create sample staff user if it doesn't exist
                staff_user = User.query.filter_by(username="staff_sample").first()
                if not staff_user:
                    staff_user = User(
                        username="staff_sample",
                        email="staff@care-system.com",
                        role="staff",
                        is_admin=False,
                        active=True,
                        first_name="Juan",
                        last_name="Cruz",
                        phone_number="+63 555 STAFF-01",
                        license_number="RN-2024-001",
                        facility_name="C.A.R.E. Medical Center",
                    )
                    staff_user.set_password("staff123")
                    db.session.add(staff_user)
                    db.session.commit()

                    # Create verified email verification for staff
                    staff_verification = EmailVerification(
                        user_id=staff_user.id, email=staff_user.email
                    )
                    db.session.add(staff_verification)
                    db.session.commit()
                    staff_verification.verify()

                    app.logger.info(
                        "Sample staff user created: staff_sample/staff123 (email verified)"
                    )

                # Create sample patient user if it doesn't exist
                patient_user = User.query.filter_by(username="patient_sample").first()
                if not patient_user:
                    patient_user = User(
                        username="patient_sample",
                        email="patient@care-system.com",
                        role="patient",
                        is_admin=False,
                        active=True,
                        first_name="Ana",
                        last_name="Reyes",
                        phone_number="+63 555 PAT-1234",
                        date_of_birth=date(1990, 5, 15),
                        address="123 Health Street, Wellness City, Metro Manila",
                        emergency_contact="Pedro Reyes",
                        emergency_phone="+63 555 EMER-123",
                    )
                    patient_user.set_password("patient123")
                    db.session.add(patient_user)
                    db.session.commit()

                    # Create verified email verification for patient
                    patient_verification = EmailVerification(
                        user_id=patient_user.id, email=patient_user.email
                    )
                    db.session.add(patient_verification)
                    db.session.commit()
                    patient_verification.verify()

                    app.logger.info(
                        "Sample patient user created: patient_sample/patient123 (email verified)"
                    )

            except Exception as e:
                app.logger.warning(f"Database initialization failed: {e}")

        # Add timezone-aware datetime functions to template context
        @app.context_processor
        def inject_current_date():
            """Inject timezone-aware datetime utilities into templates."""
            user_tz = get_user_timezone()
            current_time_local = get_current_time(user_tz)

            # Common Philippine timezones for user selection
            common_timezones = [
                ("Asia/Manila", "Philippines (Manila)"),
                ("UTC", "UTC"),
                ("America/New_York", "Eastern Time (US)"),
                ("America/Los_Angeles", "Pacific Time (US)"),
                ("Europe/London", "London"),
                ("Asia/Tokyo", "Tokyo"),
                ("Asia/Singapore", "Singapore"),
                ("Australia/Sydney", "Sydney"),
            ]

            return {
                "current_year": current_time_local.year,
                "current_date": current_time_local,
                "current_time": current_time_local,
                "user_timezone": user_tz,
                "user_timezone_name": str(user_tz),
                "common_timezones": common_timezones,
                "datetime": datetime,
                "timedelta": timedelta,
                "date": date,
                "pytz": pytz,
                "localize_datetime": localize_datetime,
                "get_current_time": get_current_time,
                "get_user_timezone": get_user_timezone,
            }

    # Add timezone route for AJAX updates
    @app.route("/api/set_timezone", methods=["POST"])
    def set_timezone():
        """Set user's timezone preference."""
        from flask import request, jsonify

        timezone = request.json.get("timezone", "Asia/Manila")
        try:
            # Validate timezone
            pytz.timezone(timezone)
            session["user_timezone"] = timezone
            return jsonify({"success": True, "timezone": timezone})
        except pytz.exceptions.UnknownTimeZoneError:
            return jsonify({"success": False, "error": "Invalid timezone"}), 400

    # Make hCaptcha and timezone functions available in templates
    from app.utils.hcaptcha_utils import hcaptcha, is_hcaptcha_enabled

    app.jinja_env.globals.update(
        hcaptcha=hcaptcha,
        hcaptcha_enabled=is_hcaptcha_enabled,
        localize_datetime=localize_datetime,
        get_current_time=get_current_time,
        get_user_timezone=get_user_timezone,
    )

    return app
