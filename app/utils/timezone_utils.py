from flask import session
import pytz
from datetime import datetime


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
