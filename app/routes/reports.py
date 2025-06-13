from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    current_app,
    make_response,
)
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app import db, get_user_timezone, localize_datetime, get_current_time
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from functools import wraps
import json

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def admin_or_doctor_required(f):
    """Decorator to require admin or doctor access for reports."""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_app.config.get("DISABLE_DATABASE", False):
            flash(
                "Reports are not available in this deployment environment.", "warning"
            )
            return redirect(url_for("main.home"))

        if current_user.role not in ["doctor", "admin"]:
            flash(
                "Access denied. Doctor or admin privileges required for reports.",
                "error",
            )
            return redirect(url_for("main.home"))

        return f(*args, **kwargs)

    return decorated_function


@reports_bp.route("/")
@admin_or_doctor_required
def dashboard():
    """Reports and analytics dashboard."""
    # Get user's timezone for displaying timestamps
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)
    
    # Get date range from query params or default to last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if date_from:
        try:
            start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            pass

    if date_to:
        try:
            end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Filter by doctor if not admin
    doctor_filter = None
    if current_user.role == "doctor":
        doctor_filter = current_user.id
    elif request.args.get("doctor_id"):
        doctor_filter = int(request.args.get("doctor_id"))

    # Generate summary metrics
    try:
        appointment_metrics = AnalyticsService.generate_appointment_metrics(
            start_date, end_date, doctor_filter
        )

        prescription_trends = AnalyticsService.generate_prescription_trends(
            start_date, end_date, doctor_filter, limit=5
        )

        diagnosis_trends = AnalyticsService.generate_diagnosis_trends(
            start_date, end_date, doctor_filter, limit=5
        )

        doctor_performance = AnalyticsService.generate_doctor_performance(
            start_date, end_date, doctor_filter
        )

        # Get today's summary
        today_summary = AnalyticsService.generate_daily_summary()

        # Get yesterday's summary for comparison
        yesterday_summary = AnalyticsService.generate_daily_summary(
            date.today() - timedelta(days=1)
        )

    except Exception as e:
        current_app.logger.error(f"Error generating analytics: {e}")
        appointment_metrics = {}
        prescription_trends = []
        diagnosis_trends = []
        doctor_performance = []
        today_summary = {}
        yesterday_summary = {}

    # Get all doctors for filter dropdown (admin only)
    doctors = []
    if current_user.role == "admin":
        doctors = (
            User.query.filter_by(role="doctor", active=True)
            .order_by(User.first_name, User.last_name)
            .all()
        )

    return render_template(
        "medical_dashboard/reports/dashboard.html",
        appointment_metrics=appointment_metrics,
        prescription_trends=prescription_trends,
        diagnosis_trends=diagnosis_trends,
        doctor_performance=doctor_performance,
        today_summary=today_summary,
        yesterday_summary=yesterday_summary,
        doctors=doctors,
        start_date=start_date,
        end_date=end_date,
        doctor_filter=doctor_filter,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
    )


@reports_bp.route("/appointments")
@admin_or_doctor_required
def appointment_report():
    """Detailed appointment analytics report."""
    # Get user's timezone for displaying timestamps
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)
    
    # Get parameters
    report_type = request.args.get("type", "daily")
    doctor_id = (
        request.args.get("doctor_id")
        if current_user.role == "admin"
        else current_user.id
    )

    # Date range handling
    if report_type == "daily":
        target_date = request.args.get("date")
        if target_date:
            try:
                target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                target_date = date.today()
        else:
            target_date = date.today()

        data = AnalyticsService.generate_daily_summary(target_date)

    elif report_type == "weekly":
        week_start = request.args.get("week_start")
        if week_start:
            try:
                week_start = datetime.strptime(week_start, "%Y-%m-%d").date()
            except ValueError:
                week_start = date.today() - timedelta(days=7)
        else:
            week_start = date.today() - timedelta(days=7)

        data = AnalyticsService.generate_weekly_summary(week_start)

    elif report_type == "monthly":
        year = int(request.args.get("year", date.today().year))
        month = int(request.args.get("month", date.today().month))

        data = AnalyticsService.generate_monthly_summary(year, month)

    # Get all doctors for filter
    doctors = []
    if current_user.role == "admin":
        doctors = User.query.filter_by(role="doctor", active=True).all()

    return render_template(
        "medical_dashboard/reports/appointments.html",
        data=data,
        report_type=report_type,
        doctors=doctors,
        selected_doctor=doctor_id,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
    )


@reports_bp.route("/prescriptions")
@admin_or_doctor_required
def prescription_report():
    """Prescription analytics and trends report."""
    # Get user's timezone for displaying timestamps
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)
    
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if date_from:
        try:
            start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            pass

    if date_to:
        try:
            end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            pass

    doctor_filter = None
    if current_user.role == "doctor":
        doctor_filter = current_user.id
    elif request.args.get("doctor_id"):
        doctor_filter = int(request.args.get("doctor_id"))

    # Generate prescription analytics
    prescription_trends = AnalyticsService.generate_prescription_trends(
        start_date, end_date, doctor_filter, limit=20
    )

    # Get all doctors for filter
    doctors = []
    if current_user.role == "admin":
        doctors = User.query.filter_by(role="doctor", active=True).all()

    return render_template(
        "medical_dashboard/reports/prescriptions.html",
        prescription_trends=prescription_trends,
        doctors=doctors,
        start_date=start_date,
        end_date=end_date,
        doctor_filter=doctor_filter,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
    )


@reports_bp.route("/performance")
@admin_or_doctor_required
def performance_report():
    """Doctor performance analytics report."""
    # Get user's timezone for displaying timestamps
    user_timezone = get_user_timezone()
    current_time_local = get_current_time(user_timezone)
    
    # Get date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if date_from:
        try:
            start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        except ValueError:
            pass

    if date_to:
        try:
            end_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        except ValueError:
            pass

    doctor_filter = None
    if current_user.role == "doctor":
        doctor_filter = current_user.id
    elif request.args.get("doctor_id"):
        doctor_filter = int(request.args.get("doctor_id"))

    # Generate performance metrics
    performance_data = AnalyticsService.generate_doctor_performance(
        start_date, end_date, doctor_filter
    )

    # Get all doctors for filter
    doctors = []
    if current_user.role == "admin":
        doctors = User.query.filter_by(role="doctor", active=True).all()

    return render_template(
        "medical_dashboard/reports/performance.html",
        performance_data=performance_data,
        doctors=doctors,
        start_date=start_date,
        end_date=end_date,
        doctor_filter=doctor_filter,
        user_timezone=user_timezone,
        current_time_local=current_time_local,
    )


@reports_bp.route("/api/chart-data/<chart_type>")
@admin_or_doctor_required
def api_chart_data(chart_type):
    """API endpoint for chart data."""
    try:
        # Get parameters
        days = int(request.args.get("days", 7))
        doctor_id = (
            request.args.get("doctor_id")
            if current_user.role == "admin"
            else current_user.id
        )

        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        if chart_type == "appointments_timeline":
            # Generate daily appointment counts
            data = []
            current_date = start_date

            while current_date <= end_date:
                daily_summary = AnalyticsService.generate_daily_summary(current_date)
                data.append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "appointments": daily_summary["total_appointments"],
                        "completed": daily_summary["completed_appointments"],
                    }
                )
                current_date += timedelta(days=1)

            return jsonify(data)

        elif chart_type == "prescription_trends":
            trends = AnalyticsService.generate_prescription_trends(
                start_date, end_date, doctor_id, limit=10
            )
            return jsonify(trends)

        elif chart_type == "appointment_status":
            metrics = AnalyticsService.generate_appointment_metrics(
                start_date, end_date, doctor_id
            )

            data = [
                {
                    "status": "Completed",
                    "count": metrics.get("completed_appointments", 0),
                },
                {
                    "status": "Scheduled",
                    "count": metrics.get("scheduled_appointments", 0),
                },
                {
                    "status": "Confirmed",
                    "count": metrics.get("confirmed_appointments", 0),
                },
                {
                    "status": "Cancelled",
                    "count": metrics.get("cancelled_appointments", 0),
                },
            ]
            return jsonify(data)

        return jsonify({"error": "Invalid chart type"}), 400

    except Exception as e:
        current_app.logger.error(f"Error generating chart data: {e}")
        return jsonify({"error": "Failed to generate chart data"}), 500


@reports_bp.route("/export/<report_type>")
@admin_or_doctor_required
def export_report(report_type):
    """Export report data in various formats."""
    try:
        # Get parameters
        format_type = request.args.get("format", "json")
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        doctor_id = (
            request.args.get("doctor_id")
            if current_user.role == "admin"
            else current_user.id
        )

        # Parse dates
        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        else:
            start_date = date.today() - timedelta(days=30)

        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        else:
            end_date = date.today()

        # Generate report data
        report_data = AnalyticsService.export_report_data(
            report_type, start_date, end_date, format_type, doctor_id
        )

        # Create response
        if format_type == "csv":
            response = make_response(report_data)
            response.headers["Content-Type"] = "text/csv"
            response.headers["Content-Disposition"] = (
                f"attachment; filename={report_type}_report_{start_date}_{end_date}.csv"
            )
        else:
            response = make_response(report_data)
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Disposition"] = (
                f"attachment; filename={report_type}_report_{start_date}_{end_date}.json"
            )

        return response

    except Exception as e:
        current_app.logger.error(f"Error exporting report: {e}")
        flash("Error exporting report. Please try again.", "error")
        return redirect(url_for("reports.dashboard"))
