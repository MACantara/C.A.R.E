from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
)
from flask_login import login_required, current_user
from app import db
from app.models.user import User
import re

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


def is_valid_username(username):
    """Validate username format."""
    # Username must be 3-30 characters, alphanumeric and underscores only
    pattern = r"^[a-zA-Z0-9_]{3,30}$"
    return re.match(pattern, username) is not None


@profile_bp.route("/")
@login_required
def profile():
    """User profile page."""
    if current_app.config.get("DISABLE_DATABASE", False):
        flash(
            "User profiles are not available in this deployment environment.", "warning"
        )
        return redirect(url_for("main.home"))

    return render_template("profile/profile.html", user=current_user)


@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    """Edit user profile page."""
    if current_app.config.get("DISABLE_DATABASE", False):
        flash(
            "Profile editing is not available in this deployment environment.",
            "warning",
        )
        return redirect(url_for("main.home"))

    if request.method == "POST":
        # Basic fields that all users can edit
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Personal information fields
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        phone_number = request.form.get("phone_number", "").strip()

        # Role-specific fields
        profile_updates = {}

        if current_user.role == "patient":
            date_of_birth = request.form.get("date_of_birth")
            address = request.form.get("address", "").strip()
            emergency_contact = request.form.get("emergency_contact", "").strip()
            emergency_phone = request.form.get("emergency_phone", "").strip()

            if date_of_birth:
                try:
                    from datetime import datetime

                    profile_updates["date_of_birth"] = datetime.strptime(
                        date_of_birth, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    flash("Invalid date of birth format.", "error")
                    return render_template(
                        "profile/edit-profile.html", user=current_user
                    )

            profile_updates.update(
                {
                    "address": address or None,
                    "emergency_contact": emergency_contact or None,
                    "emergency_phone": emergency_phone or None,
                }
            )

        elif current_user.role in ["doctor", "staff"]:
            license_number = request.form.get("license_number", "").strip()
            specialization = request.form.get("specialization", "").strip()
            facility_name = request.form.get("facility_name", "").strip()

            # Check if license number is being changed and if it's already taken
            if license_number and license_number != current_user.license_number:
                existing_license = User.query.filter_by(
                    license_number=license_number
                ).first()
                if existing_license and existing_license.id != current_user.id:
                    flash(
                        "License number is already registered to another user.", "error"
                    )
                    return render_template(
                        "profile/edit-profile.html", user=current_user
                    )

            profile_updates.update(
                {
                    "license_number": license_number or None,
                    "specialization": specialization or None,
                    "facility_name": facility_name or None,
                }
            )

        # Validate current password for any changes
        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "error")
            return render_template("profile/edit-profile.html", user=current_user)

        # Validate username
        if (
            not username
            or len(username) < 3
            or len(username) > 30
            or not is_valid_username(username)
        ):
            flash("Username must be between 3 and 30 characters.", "error")
            return render_template("profile/edit-profile.html", user=current_user)

        # Check if username is taken by another user
        if username != current_user.username:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash("Username is already taken.", "error")
                return render_template("profile/edit-profile.html", user=current_user)

        # Validate email
        if not email or "@" not in email:
            flash("Please enter a valid email address.", "error")
            return render_template("profile/edit-profile.html", user=current_user)

        # Check if email is taken by another user
        if email != current_user.email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("Email address is already registered.", "error")
                return render_template("profile/edit-profile.html", user=current_user)

        # Validate new password if provided
        if new_password:
            if len(new_password) < 8:
                flash("Password must be at least 8 characters long.", "error")
                return render_template("profile/edit-profile.html", user=current_user)

            if new_password != confirm_password:
                flash("New passwords do not match.", "error")
                return render_template("profile/edit-profile.html", user=current_user)

        try:
            # Update basic user information
            current_user.username = username
            current_user.email = email
            current_user.first_name = first_name or None
            current_user.last_name = last_name or None
            current_user.phone_number = phone_number or None

            # Update role-specific profile information
            for field, value in profile_updates.items():
                if hasattr(current_user, field):
                    setattr(current_user, field, value)

            # Update password if provided
            if new_password:
                current_user.set_password(new_password)

            db.session.commit()

            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile.profile"))

        except Exception as e:
            db.session.rollback()
            flash(
                "An error occurred while updating your profile. Please try again.",
                "error",
            )
            return render_template("profile/edit-profile.html", user=current_user)

    return render_template("profile/edit-profile.html", user=current_user)
