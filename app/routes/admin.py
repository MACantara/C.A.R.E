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
from app import db
from app.models.user import User
from app.models.login_attempt import LoginAttempt
from app.models.email_verification import EmailVerification
from app.models.contact import Contact
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
    # Get statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(active=True).count()  # Changed from is_active
    inactive_users = total_users - active_users

    # Recent user registrations (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_registrations = User.query.filter(User.created_at >= thirty_days_ago).count()

    # Login attempts statistics (last 24 hours)
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    recent_login_attempts = LoginAttempt.query.filter(
        LoginAttempt.attempted_at >= twenty_four_hours_ago
    ).count()
    failed_login_attempts = LoginAttempt.query.filter(
        LoginAttempt.attempted_at >= twenty_four_hours_ago,
        LoginAttempt.success == False,
    ).count()

    # Email verification statistics
    verified_emails = EmailVerification.query.filter_by(is_verified=True).count()
    pending_verifications = EmailVerification.query.filter_by(is_verified=False).count()

    # Contact form submissions (last 30 days)
    recent_contacts = Contact.query.filter(
        Contact.created_at >= thirty_days_ago
    ).count()

    # Recent activities
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
        users_query = users_query.filter_by(active=True)  # Changed from is_active
    elif status_filter == "inactive":
        users_query = users_query.filter_by(active=False)  # Changed from is_active
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
    )


@admin_bp.route("/user/<int:user_id>")
@admin_required
def user_detail(user_id):
    """View detailed information about a specific user."""
    user = User.query.get_or_404(user_id)

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

    user.active = not user.active  # Changed from is_active
    db.session.commit()

    status = "activated" if user.active else "deactivated"  # Changed from is_active
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
    """API endpoint for dashboard statistics."""
    # Login attempts over time (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_stats = []

    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        total_attempts = LoginAttempt.query.filter(
            LoginAttempt.attempted_at >= day_start, LoginAttempt.attempted_at < day_end
        ).count()

        failed_attempts = LoginAttempt.query.filter(
            LoginAttempt.attempted_at >= day_start,
            LoginAttempt.attempted_at < day_end,
            LoginAttempt.success == False,
        ).count()

        daily_stats.append(
            {
                "date": day.strftime("%Y-%m-%d"),
                "total_attempts": total_attempts,
                "failed_attempts": failed_attempts,
                "success_attempts": total_attempts - failed_attempts,
            }
        )

    return jsonify(daily_stats)


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
