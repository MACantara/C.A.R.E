from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
from app import db, socketio
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

    # Handle reply functionality
    reply_to_id = request.args.get("reply_to")
    reply_data = None

    if reply_to_id:
        try:
            original_message = InternalMessage.query.get(int(reply_to_id))
            if original_message and (
                original_message.recipient_id == current_user.id
                or original_message.sender_id == current_user.id
            ):
                # Determine who to reply to (sender if we're the recipient, recipient if we're the sender)
                reply_to_user = (
                    original_message.sender
                    if original_message.recipient_id == current_user.id
                    else original_message.recipient
                )

                reply_data = {
                    "recipient_id": reply_to_user.id,
                    "subject": (
                        f"Re: {original_message.subject}"
                        if not original_message.subject.startswith("Re:")
                        else original_message.subject
                    ),
                    "priority": original_message.priority.value,
                    "message_type": original_message.message_type.value,
                    "original_content": original_message.content,
                    "original_sender": f"{original_message.sender.first_name} {original_message.sender.last_name}",
                    "original_date": original_message.created_at.strftime(
                        "%B %d, %Y at %I:%M %p"
                    ),
                }
        except (ValueError, AttributeError):
            pass  # Invalid reply_to_id, ignore

    return render_template(
        "messages/compose.html", recipients=recipients, reply_data=reply_data
    )


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

        # Emit real-time notification to recipient
        socketio.emit(
            "new_message",
            {
                "message": message.to_dict(),
                "notification": {
                    "title": f"New message from {current_user.first_name} {current_user.last_name}",
                    "body": subject,
                    "priority": priority,
                },
            },
            room=f"user_{recipient_id}",
        )

        # Emit message sent confirmation to sender
        socketio.emit(
            "message_sent",
            {"message": message.to_dict()},
            room=f"user_{current_user.id}",
        )

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

        # Notify sender that message was read
        socketio.emit(
            "message_read",
            {
                "message_id": message.id,
                "read_at": message.read_at.isoformat() if message.read_at else None,
            },
            room=f"user_{message.sender_id}",
        )

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


@messages_bp.route("/reply/<int:message_id>")
@login_required
def reply_to_message(message_id):
    """Redirect to compose with reply parameters."""
    message = InternalMessage.query.get_or_404(message_id)

    # Check if user has permission to reply to this message
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        flash("Access denied.", "error")
        return redirect(url_for("messages.inbox"))

    return redirect(url_for("messages.compose", reply_to=message_id))


@messages_bp.route("/api/latest_messages")
@login_required
def api_latest_messages():
    """Get latest messages for inbox refresh."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    # Get received messages
    received_messages = (
        InternalMessage.query.filter(
            and_(
                InternalMessage.recipient_id == current_user.id,
                InternalMessage.is_deleted_by_recipient == False,
            )
        )
        .order_by(InternalMessage.created_at.desc())
        .limit(20)  # Limit to recent messages for performance
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
        .limit(20)
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

    return jsonify(
        {
            "received_messages": [msg.to_dict() for msg in received_messages],
            "sent_messages": [msg.to_dict() for msg in sent_messages],
            "unread_count": unread_count,
            "last_updated": datetime.utcnow().isoformat(),
        }
    )


# WebSocket Events
@socketio.on("connect")
def on_connect():
    """Handle client connection."""
    if current_user.is_authenticated and current_user.role in ["doctor", "staff"]:
        join_room(f"user_{current_user.id}")
        emit("connected", {"status": "Connected to messaging system"})


@socketio.on("disconnect")
def on_disconnect():
    """Handle client disconnection."""
    if current_user.is_authenticated and current_user.role in ["doctor", "staff"]:
        leave_room(f"user_{current_user.id}")


@socketio.on("join_user_room")
def on_join_user_room():
    """Explicitly join user room for messages."""
    if current_user.is_authenticated and current_user.role in ["doctor", "staff"]:
        join_room(f"user_{current_user.id}")
        emit("room_joined", {"room": f"user_{current_user.id}"})


@socketio.on("typing_start")
def on_typing_start(data):
    """Handle typing indicator start."""
    if current_user.is_authenticated and current_user.role in ["doctor", "staff"]:
        recipient_id = data.get("recipient_id")
        if recipient_id:
            emit(
                "user_typing",
                {
                    "user_id": current_user.id,
                    "user_name": f"{current_user.first_name} {current_user.last_name}",
                    "typing": True,
                },
                room=f"user_{recipient_id}",
            )


@socketio.on("typing_stop")
def on_typing_stop(data):
    """Handle typing indicator stop."""
    if current_user.is_authenticated and current_user.role in ["doctor", "staff"]:
        recipient_id = data.get("recipient_id")
        if recipient_id:
            emit(
                "user_typing",
                {
                    "user_id": current_user.id,
                    "user_name": f"{current_user.first_name} {current_user.last_name}",
                    "typing": False,
                },
                room=f"user_{recipient_id}",
            )


@socketio.on("request_unread_count")
def on_request_unread_count():
    """Send current unread message count to client."""
    if current_user.is_authenticated and current_user.role in ["doctor", "staff"]:
        count = InternalMessage.query.filter(
            and_(
                InternalMessage.recipient_id == current_user.id,
                InternalMessage.is_read == False,
                InternalMessage.is_deleted_by_recipient == False,
            )
        ).count()

        emit("unread_count_update", {"count": count})
