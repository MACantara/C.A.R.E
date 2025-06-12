from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.models.user import User
from app.models.message import InternalMessage, MessageType, MessagePriority
from sqlalchemy import and_, or_

messages_bp = Blueprint("messages", __name__, url_prefix="/messages")


@messages_bp.route("/")
@login_required
def inbox():
    """Display user's message inbox."""
    if current_user.role not in ["doctor", "staff"]:
        flash("Access denied. This area is for healthcare professionals only.", "error")
        return redirect(url_for("main.home"))

    # Get received messages
    received_messages = (
        InternalMessage.query.filter(
            and_(
                InternalMessage.recipient_id == current_user.id,
                InternalMessage.is_deleted_by_recipient == False,
            )
        )
        .order_by(InternalMessage.created_at.desc())
        .all()
    )

    # Get sent messages
    sent_messages = (
        InternalMessage.query.filter(
            and_(
                InternalMessage.sender_id == current_user.id,
                InternalMessage.is_deleted_by_sender == False,
            )
        )
        .order_by(InternalMessage.created_at.desc())
        .all()
    )

    # Count unread messages
    unread_count = InternalMessage.query.filter(
        and_(
            InternalMessage.recipient_id == current_user.id,
            InternalMessage.is_read == False,
            InternalMessage.is_deleted_by_recipient == False,
        )
    ).count()

    return render_template(
        "messages/inbox.html",
        received_messages=received_messages,
        sent_messages=sent_messages,
        unread_count=unread_count,
    )


@messages_bp.route("/compose")
@login_required
def compose():
    """Display compose message form."""
    if current_user.role not in ["doctor", "staff"]:
        flash("Access denied.", "error")
        return redirect(url_for("main.home"))

    # Get all healthcare professionals for recipient list
    recipients = (
        User.query.filter(
            and_(
                User.role.in_(["doctor", "staff"]),
                User.id != current_user.id,
                User.active == True,
            )
        )
        .order_by(User.first_name, User.last_name)
        .all()
    )

    return render_template("messages/compose.html", recipients=recipients)


@messages_bp.route("/send", methods=["POST"])
@login_required
def send_message():
    """Send a new message."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    recipient_id = request.form.get("recipient_id")
    subject = request.form.get("subject", "").strip()
    content = request.form.get("content", "").strip()
    priority = request.form.get("priority", "normal")
    message_type = request.form.get("message_type", "general")

    # Validation
    if not recipient_id or not subject or not content:
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("messages.compose"))

    try:
        message = InternalMessage(
            sender_id=current_user.id,
            recipient_id=int(recipient_id),
            subject=subject,
            content=content,
            message_type=MessageType(message_type),
            priority=MessagePriority(priority),
        )

        db.session.add(message)
        db.session.commit()

        flash("Message sent successfully!", "success")
        return redirect(url_for("messages.inbox"))

    except Exception as e:
        flash("Failed to send message. Please try again.", "error")
        return redirect(url_for("messages.compose"))


@messages_bp.route("/read/<int:message_id>")
@login_required
def read_message(message_id):
    """Display a specific message."""
    message = InternalMessage.query.get_or_404(message_id)

    # Check if user has permission to read this message
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("messages.inbox"))

    # Mark as read if recipient is viewing
    if message.recipient_id == current_user.id and not message.is_read:
        message.mark_as_read()

    return render_template("messages/read.html", message=message)


@messages_bp.route("/api/unread_count")
@login_required
def api_unread_count():
    """Get count of unread messages for current user."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"count": 0})

    count = InternalMessage.query.filter(
        and_(
            InternalMessage.recipient_id == current_user.id,
            InternalMessage.is_read == False,
            InternalMessage.is_deleted_by_recipient == False,
        )
    ).count()

    return jsonify({"count": count})


@messages_bp.route("/delete/<int:message_id>", methods=["POST"])
@login_required
def delete_message(message_id):
    """Delete a message (soft delete)."""
    message = InternalMessage.query.get_or_404(message_id)

    # Check permissions and mark as deleted
    if message.recipient_id == current_user.id:
        message.is_deleted_by_recipient = True
    elif message.sender_id == current_user.id:
        message.is_deleted_by_sender = True
    else:
        flash("Access denied.", "error")
        return redirect(url_for("messages.inbox"))

    db.session.commit()
    flash("Message deleted successfully.", "success")
    return redirect(url_for("messages.inbox"))
