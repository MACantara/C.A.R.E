from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    jsonify,
)
from flask_login import current_user, login_required
from app import db, get_user_timezone, localize_datetime, get_current_time
from app.models.user import User
from app.models.login_attempt import LoginAttempt
from app.models.email_verification import EmailVerification
from app.models.contact import Contact
from app.models.appointment import Appointment, AppointmentStatus
from datetime import datetime, timedelta
from sqlalchemy import desc, func
from functools import wraps

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    """Decorator to require admin authentication."""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Check if database is disabled
        if current_app.config.get("DISABLE_DATABASE", False):
            flash(
                "Admin panel is not available in this deployment environment.",
                "warning",
            )
            return redirect(url_for("main.home"))

        # Check if user is admin
        if not current_user.is_admin:
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("main.home"))

        return f(*args, **kwargs)

    return decorated_function


@admin_bp.route("/")
@admin_required
def dashboard():
    """Admin dashboard with overview statistics."""
    # Get user's timezone for displaying timestamps
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)

    # Get statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(active=True).count()
    inactive_users = total_users - active_users

    # Recent user registrations (last 30 days) - using timezone-aware calculation
    thirty_days_ago_utc = datetime.utcnow() - timedelta(days=30)
    recent_registrations = User.query.filter(
        User.created_at >= thirty_days_ago_utc
    ).count()

    # Login attempts statistics (last 24 hours) - using timezone-aware calculation
    twenty_four_hours_ago_utc = datetime.utcnow() - timedelta(hours=24)
    recent_login_attempts = LoginAttempt.query.filter(
        LoginAttempt.attempted_at >= twenty_four_hours_ago_utc
    ).count()
    failed_login_attempts = LoginAttempt.query.filter(
        LoginAttempt.attempted_at >= twenty_four_hours_ago_utc,
        LoginAttempt.success == False,
    ).count()

    # Email verification statistics
    verified_emails = EmailVerification.query.filter_by(is_verified=True).count()
    pending_verifications = EmailVerification.query.filter_by(is_verified=False).count()

    # Contact form submissions (last 30 days)
    recent_contacts = Contact.query.filter(
        Contact.created_at >= thirty_days_ago_utc
    ).count()

    # Recent activities with timezone conversion
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    recent_login_logs = (
        LoginAttempt.query.order_by(desc(LoginAttempt.attempted_at)).limit(10).all()
    )

    stats = {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "recent_registrations": recent_registrations,
        "recent_login_attempts": recent_login_attempts,
        "failed_login_attempts": failed_login_attempts,
        "verified_emails": verified_emails,
        "pending_verifications": pending_verifications,
        "recent_contacts": recent_contacts,
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        recent_users=recent_users,
        recent_login_logs=recent_login_logs,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
    )


@admin_bp.route("/users")
@admin_required
def users():
    """User management page."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    # Validate per_page to prevent abuse
    if per_page not in [25, 50, 100]:
        per_page = 25

    # Get user's timezone
    user_timezone = get_user_timezone()

    # Search functionality
    search = request.args.get("search", "")
    if search:
        users_query = User.query.filter(
            (User.username.contains(search)) | (User.email.contains(search))
        )
    else:
        users_query = User.query

    # Filter by status
    status_filter = request.args.get("status", "all")
    if status_filter == "active":
        users_query = users_query.filter_by(active=True)
    elif status_filter == "inactive":
        users_query = users_query.filter_by(active=False)
    elif status_filter == "admin":
        users_query = users_query.filter_by(is_admin=True)

    users_pagination = users_query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        "admin/users.html",
        users=users_pagination.items,
        pagination=users_pagination,
        search=search,
        status_filter=status_filter,
        user_timezone=user_timezone,
    )


@admin_bp.route("/user/<int:user_id>")
@admin_required
def user_detail(user_id):
    """View detailed information about a specific user."""
    user = User.query.get_or_404(user_id)

    # Get admin's timezone for displaying timestamps
    user_timezone = get_user_timezone()

    # Get user's login attempts
    login_attempts = (
        LoginAttempt.query.filter_by(username_or_email=user.username)
        .order_by(desc(LoginAttempt.attempted_at))
        .limit(20)
        .all()
    )

    # Also check by email
    email_attempts = (
        LoginAttempt.query.filter_by(username_or_email=user.email)
        .order_by(desc(LoginAttempt.attempted_at))
        .limit(20)
        .all()
    )

    # Combine and deduplicate
    all_attempts = list(set(login_attempts + email_attempts))
    all_attempts.sort(key=lambda x: x.attempted_at, reverse=True)

    # Get user's email verifications
    verifications = (
        EmailVerification.query.filter_by(user_id=user.id)
        .order_by(desc(EmailVerification.created_at))
        .all()
    )

    return render_template(
        "admin/user-detail.html",
        user=user,
        login_attempts=all_attempts[:20],
        verifications=verifications,
        user_timezone=user_timezone,
    )


@admin_bp.route("/user/<int:user_id>/toggle-status", methods=["POST"])
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status."""
    user = User.query.get_or_404(user_id)

    # Prevent admin from deactivating themselves
    if user.id == session["user_id"]:
        flash("You cannot deactivate your own account.", "error")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    user.active = not user.active
    db.session.commit()

    status = "activated" if user.active else "deactivated"
    flash(f"User {user.username} has been {status}.", "success")

    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/user/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin_status(user_id):
    """Toggle user admin status."""
    user = User.query.get_or_404(user_id)

    # Prevent admin from removing their own admin status
    if user.id == session["user_id"]:
        flash("You cannot remove your own admin privileges.", "error")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    user.is_admin = not user.is_admin
    db.session.commit()

    status = "granted" if user.is_admin else "revoked"
    flash(f"Admin privileges have been {status} for user {user.username}.", "success")

    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/user/<int:user_id>/change-role", methods=["POST"])
@admin_required
def change_user_role(user_id):
    """Change user role."""
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("new_role")

    # Prevent admin from changing their own role
    if user.id == session["user_id"]:
        flash("You cannot change your own role.", "error")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    # Validate role
    if new_role not in ["patient", "doctor", "staff"]:
        flash("Invalid role selected.", "error")
        return redirect(url_for("admin.user_detail", user_id=user_id))

    old_role = user.role
    user.role = new_role

    # If changing to/from doctor role, handle license number requirements
    if new_role == "doctor" and not user.license_number:
        flash(
            f"Warning: User role changed from {old_role} to {new_role}, but no license number is set. Please ensure the user updates their profile with a valid license number.",
            "warning",
        )
    elif old_role == "doctor" and new_role != "doctor":
        # Optionally clear doctor-specific fields or leave them for reference
        pass

    # Clear admin status if role is changed to patient (optional business rule)
    if new_role == "patient" and user.is_admin:
        user.is_admin = False
        flash(
            f"User role changed from {old_role} to {new_role}. Admin privileges have been revoked.",
            "success",
        )
    else:
        flash(f"User role changed from {old_role} to {new_role}.", "success")

    db.session.commit()
    return redirect(url_for("admin.user_detail", user_id=user_id))


@admin_bp.route("/api/stats")
@admin_required
def api_stats():
    """API endpoint for dashboard statistics with timezone awareness."""
    user_timezone = get_user_timezone()

    # Login attempts over time (last 7 days) - using timezone-aware calculation
    seven_days_ago_utc = datetime.utcnow() - timedelta(days=7)
    daily_stats = []

    for i in range(7):
        day_utc = seven_days_ago_utc + timedelta(days=i)
        day_start_utc = day_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end_utc = day_start_utc + timedelta(days=1)

        total_attempts = LoginAttempt.query.filter(
            LoginAttempt.attempted_at >= day_start_utc,
            LoginAttempt.attempted_at < day_end_utc,
        ).count()

        failed_attempts = LoginAttempt.query.filter(
            LoginAttempt.attempted_at >= day_start_utc,
            LoginAttempt.attempted_at < day_end_utc,
            LoginAttempt.success == False,
        ).count()

        # Convert day to user's timezone for display
        day_local = localize_datetime(day_start_utc, user_timezone)

        daily_stats.append(
            {
                "date": day_local.strftime("%Y-%m-%d"),
                "date_display": day_local.strftime("%m/%d"),
                "total_attempts": total_attempts,
                "failed_attempts": failed_attempts,
                "success_attempts": total_attempts - failed_attempts,
            }
        )

    return jsonify({"daily_stats": daily_stats, "timezone": str(user_timezone)})


@admin_bp.route("/cleanup", methods=["POST"])
@admin_required
def cleanup_logs():
    """Clean up old logs and expired tokens."""
    try:
        # Clean up old login attempts (older than 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        old_attempts = LoginAttempt.query.filter(
            LoginAttempt.attempted_at < thirty_days_ago
        ).delete()

        # Clean up expired email verification tokens
        expired_verifications = EmailVerification.cleanup_expired_tokens()

        # Clean up old contact submissions (older than 90 days)
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        old_contacts = Contact.query.filter(
            Contact.created_at < ninety_days_ago
        ).delete()

        db.session.commit()

        flash(
            f"Cleanup completed: {old_attempts} login attempts, {expired_verifications} verification tokens, and {old_contacts} contact submissions removed.",
            "success",
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Cleanup error: {e}")
        flash("Error during cleanup process.", "error")

    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/appointments")
@admin_required
def appointments():
    """Admin view of all appointments."""
    page = request.args.get("page", 1, type=int)
    doctor_filter = request.args.get("doctor")
    status_filter = request.args.get("status")
    date_filter = request.args.get("date")

    # Build query
    query = Appointment.query

    if doctor_filter:
        query = query.filter(Appointment.doctor_id == doctor_filter)

    if status_filter and status_filter != "all":
        query = query.filter(Appointment.status == AppointmentStatus(status_filter))

    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
            query = query.filter(
                db.func.date(Appointment.appointment_date) == filter_date
            )
        except ValueError:
            pass

    appointments = query.order_by(Appointment.appointment_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    # Get all doctors for filter dropdown
    doctors = User.query.filter_by(role="doctor", active=True).all()

    # Get user's timezone
    user_timezone = get_user_timezone()
    current_time_local = get_current_time()

    return render_template(
        "admin/appointments-admin-list.html",
        appointments=appointments,
        doctors=doctors,
        doctor_filter=doctor_filter,
        status_filter=status_filter,
        date_filter=date_filter,
        user_timezone=user_timezone.zone,
        current_time_local=current_time_local,
        localize_datetime=localize_datetime,
    )
