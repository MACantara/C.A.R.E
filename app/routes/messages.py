from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    session,
)
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
import pytz
from app import db, socketio
from app.utils.timezone_utils import get_user_timezone, localize_datetime, get_current_time
from app.models.user import User
from app.models.message import InternalMessage, MessageType, MessagePriority
from app.utils.sidebar_utils import get_sidebar_stats
from sqlalchemy import and_, or_

messages_bp = Blueprint("messages", __name__, url_prefix="/messages")


def format_message_for_api(message, user_timezone=None):
    """Format message for API response with timezone-aware timestamps."""
    if user_timezone is None:
        user_timezone = get_user_timezone()

    message_dict = message.to_dict()

    # Convert timestamps to user's timezone
    if message_dict.get("created_at"):
        utc_time = datetime.fromisoformat(
            message_dict["created_at"].replace("Z", "+00:00")
        )
        local_time = localize_datetime(utc_time, user_timezone)
        message_dict["created_at"] = local_time.isoformat()
        message_dict["created_at_local"] = local_time.strftime("%Y-%m-%d %H:%M:%S %Z")

    if message_dict.get("read_at") and message_dict["read_at"]:
        utc_time = datetime.fromisoformat(
            message_dict["read_at"].replace("Z", "+00:00")
        )
        local_time = localize_datetime(utc_time, user_timezone)
        message_dict["read_at"] = local_time.isoformat()
        message_dict["read_at_local"] = local_time.strftime("%Y-%m-%d %H:%M:%S %Z")

    return message_dict


@messages_bp.route("/")
@login_required
def inbox():
    """Display user's message inbox."""
    if current_user.role not in ["doctor", "staff"]:
        flash("Access denied. This area is for healthcare professionals only.", "error")
        return redirect(url_for("main.home"))

    # Get user's timezone
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)
    
    # Get sidebar statistics
    stats = get_sidebar_stats()

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
        stats=stats,
        user_timezone=user_timezone,
        user_timezone_name=str(user_timezone),
        current_time=current_time_local,
        current_time_local=current_time_local,  # Add this for sidebar compatibility
        localize_datetime=localize_datetime,  # Add this for timezone functions
    )


@messages_bp.route("/compose")
@login_required
def compose():
    """Redirect to inbox for compose functionality."""
    return redirect(url_for("messages.inbox"))


@messages_bp.route("/read/<int:message_id>")
@login_required
def read_message(message_id):
    """Redirect to inbox for reading messages."""
    return redirect(url_for("messages.inbox"))


@messages_bp.route("/send", methods=["POST"])
@login_required
def send_message():
    """Send a new message (legacy form submission - redirects to API)."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    # Redirect form submissions to use the API instead
    flash("Please use the new chat interface to send messages.", "info")
    return redirect(url_for("messages.inbox"))


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
    """Redirect to inbox for reply functionality."""
    return redirect(url_for("messages.inbox"))


@messages_bp.route("/api/latest_messages")
@login_required
def api_latest_messages():
    """Get latest messages for inbox refresh."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    user_timezone = get_user_timezone()

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

    current_time_local = get_current_time(user_timezone)

    return jsonify(
        {
            "received_messages": [
                format_message_for_api(msg, user_timezone) for msg in received_messages
            ],
            "sent_messages": [
                format_message_for_api(msg, user_timezone) for msg in sent_messages
            ],
            "unread_count": unread_count,
            "last_updated": current_time_local.isoformat(),
            "timezone": str(user_timezone),
        }
    )


@messages_bp.route("/api/conversations")
@login_required
def api_conversations():
    """Get all conversations for the current user."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    user_timezone = get_user_timezone()

    # Get all unique conversation partners
    conversations_query = (
        db.session.query(
            User.id,
            User.first_name,
            User.last_name,
            User.role,
            db.func.max(InternalMessage.created_at).label("last_message_time"),
        )
        .join(
            InternalMessage,
            or_(
                and_(
                    InternalMessage.sender_id == User.id,
                    InternalMessage.recipient_id == current_user.id,
                ),
                and_(
                    InternalMessage.recipient_id == User.id,
                    InternalMessage.sender_id == current_user.id,
                ),
            ),
        )
        .filter(User.id != current_user.id)
        .group_by(User.id, User.first_name, User.last_name, User.role)
        .order_by(db.func.max(InternalMessage.created_at).desc())
        .all()
    )

    conversations = []
    for conv in conversations_query:
        # Get last message
        last_message = (
            InternalMessage.query.filter(
                or_(
                    and_(
                        InternalMessage.sender_id == conv.id,
                        InternalMessage.recipient_id == current_user.id,
                    ),
                    and_(
                        InternalMessage.recipient_id == conv.id,
                        InternalMessage.sender_id == current_user.id,
                    ),
                )
            )
            .order_by(InternalMessage.created_at.desc())
            .first()
        )

        # Count unread messages from this user
        unread_count = InternalMessage.query.filter(
            and_(
                InternalMessage.sender_id == conv.id,
                InternalMessage.recipient_id == current_user.id,
                InternalMessage.is_read == False,
                InternalMessage.is_deleted_by_recipient == False,
            )
        ).count()

        conversations.append(
            {
                "other_user": {
                    "id": conv.id,
                    "first_name": conv.first_name,
                    "last_name": conv.last_name,
                    "role": conv.role,
                },
                "last_message": (
                    format_message_for_api(last_message, user_timezone)
                    if last_message
                    else None
                ),
                "unread_count": unread_count,
            }
        )

    return jsonify({"conversations": conversations, "timezone": str(user_timezone)})


@messages_bp.route("/api/conversation/<int:user_id>")
@login_required
def api_conversation(user_id):
    """Get conversation messages with a specific user."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    user_timezone = get_user_timezone()
    other_user = User.query.get_or_404(user_id)

    # Get all messages between current user and specified user
    messages = (
        InternalMessage.query.filter(
            or_(
                and_(
                    InternalMessage.sender_id == current_user.id,
                    InternalMessage.recipient_id == user_id,
                ),
                and_(
                    InternalMessage.sender_id == user_id,
                    InternalMessage.recipient_id == current_user.id,
                ),
            )
        )
        .filter(
            and_(
                InternalMessage.is_deleted_by_sender == False,
                InternalMessage.is_deleted_by_recipient == False,
            )
        )
        .order_by(InternalMessage.created_at.asc())
        .all()
    )

    formatted_messages = []
    for msg in messages:
        msg_dict = format_message_for_api(msg, user_timezone)
        msg_dict["sender_name"] = f"{msg.sender.first_name} {msg.sender.last_name}"
        formatted_messages.append(msg_dict)

    return jsonify(
        {
            "other_user": {
                "id": other_user.id,
                "first_name": other_user.first_name,
                "last_name": other_user.last_name,
                "role": other_user.role,
            },
            "messages": formatted_messages,
            "timezone": str(user_timezone),
        }
    )


@messages_bp.route("/api/send", methods=["POST"])
@login_required
def api_send_message():
    """Send a message via API."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    user_timezone = get_user_timezone()

    recipient_id = data.get("recipient_id")
    subject = data.get("subject", "").strip()
    content = data.get("content", "").strip()
    priority = data.get("priority", "normal")
    message_type = data.get("message_type", "general")

    if not recipient_id or not content:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        message = InternalMessage(
            sender_id=current_user.id,
            recipient_id=int(recipient_id),
            subject=subject or "Chat Message",
            content=content,
            message_type=MessageType(message_type),
            priority=MessagePriority(priority),
        )

        db.session.add(message)
        db.session.commit()

        # Get current time in user's timezone for consistent display
        current_time_local = get_current_time(user_timezone)

        # Emit real-time notification to recipient
        socketio.emit(
            "new_message",
            {
                "message": format_message_for_api(message, user_timezone),
                "notification": {
                    "title": f"New message from {current_user.first_name} {current_user.last_name}",
                    "body": content[:100] + ("..." if len(content) > 100 else ""),
                    "priority": priority,
                    "timestamp": current_time_local.isoformat(),
                },
            },
            room=f"user_{recipient_id}",
        )

        # Emit delivery confirmation to sender
        socketio.emit(
            "message_delivered",
            {
                "message_id": message.id,
                "delivered_at": current_time_local.isoformat(),
                "timezone": str(user_timezone),
            },
            room=f"user_{current_user.id}",
        )

        return jsonify(
            {
                "success": True,
                "message": format_message_for_api(message, user_timezone),
                "timezone": str(user_timezone),
            }
        )

    except Exception as e:
        return jsonify({"error": "Failed to send message"}), 500


@messages_bp.route("/api/mark_conversation_read/<int:user_id>", methods=["POST"])
@login_required
def api_mark_conversation_read(user_id):
    """Mark all messages from a user as read."""
    if current_user.role not in ["doctor", "staff"]:
        return jsonify({"error": "Unauthorized"}), 403

    user_timezone = get_user_timezone()

    # Mark all unread messages from this user as read
    unread_messages = InternalMessage.query.filter(
        and_(
            InternalMessage.sender_id == user_id,
            InternalMessage.recipient_id == current_user.id,
            InternalMessage.is_read == False,
        )
    ).all()

    for message in unread_messages:
        message.mark_as_read()

    # Notify sender that messages were read
    if unread_messages:
        current_time_local = get_current_time(user_timezone)

        for message in unread_messages:
            read_time_local = (
                localize_datetime(message.read_at, user_timezone)
                if message.read_at
                else current_time_local
            )

            socketio.emit(
                "message_read",
                {
                    "message_id": message.id,
                    "read_at": read_time_local.isoformat(),
                    "reader_id": current_user.id,
                    "reader_name": f"{current_user.first_name} {current_user.last_name}",
                    "timezone": str(user_timezone),
                },
                room=f"user_{message.sender_id}",
            )

    return jsonify(
        {
            "success": True,
            "marked_read": len(unread_messages),
            "timezone": str(user_timezone),
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
