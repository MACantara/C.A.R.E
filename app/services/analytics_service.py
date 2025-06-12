from datetime import datetime, date, timedelta
from sqlalchemy import func, desc, and_, or_
from app import db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.medical_record import (
    Consultation,
    Prescription,
    ConsultationStatus,
    PrescriptionStatus,
)
from app.models.user import User
import json


class AnalyticsService:

    @staticmethod
    def generate_appointment_metrics(start_date=None, end_date=None, doctor_id=None):
        """Generate appointment metrics for a date range."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Base query
        query = Appointment.query.filter(
            func.date(Appointment.appointment_date) >= start_date,
            func.date(Appointment.appointment_date) <= end_date,
        )

        if doctor_id:
            query = query.filter(Appointment.doctor_id == doctor_id)

        appointments = query.all()

        # Calculate metrics
        total = len(appointments)
        scheduled = len(
            [a for a in appointments if a.status == AppointmentStatus.SCHEDULED]
        )
        confirmed = len(
            [a for a in appointments if a.status == AppointmentStatus.CONFIRMED]
        )
        completed = len(
            [a for a in appointments if a.status == AppointmentStatus.COMPLETED]
        )
        cancelled = len(
            [a for a in appointments if a.status == AppointmentStatus.CANCELLED]
        )

        # Calculate patient metrics
        patient_ids = [a.patient_id for a in appointments]
        unique_patients = len(set(patient_ids))

        return {
            "total_appointments": total,
            "scheduled_appointments": scheduled,
            "confirmed_appointments": confirmed,
            "completed_appointments": completed,
            "cancelled_appointments": cancelled,
            "unique_patients": unique_patients,
            "completion_rate": round((completed / total * 100) if total > 0 else 0, 2),
            "cancellation_rate": round(
                (cancelled / total * 100) if total > 0 else 0, 2
            ),
        }

    @staticmethod
    def generate_prescription_trends(
        start_date=None, end_date=None, doctor_id=None, limit=10
    ):
        """Generate prescription trends and most prescribed medications."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Query prescriptions with counts
        query = db.session.query(
            Prescription.medication_name,
            func.count(Prescription.id).label("count"),
            func.count(func.distinct(Prescription.patient_id)).label("unique_patients"),
        ).filter(
            func.date(Prescription.prescribed_date) >= start_date,
            func.date(Prescription.prescribed_date) <= end_date,
        )

        if doctor_id:
            query = query.filter(Prescription.doctor_id == doctor_id)

        results = (
            query.group_by(Prescription.medication_name)
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )

        return [
            {
                "medication": r.medication_name,
                "total_prescriptions": r.count,
                "unique_patients": r.unique_patients,
            }
            for r in results
        ]

    @staticmethod
    def generate_diagnosis_trends(
        start_date=None, end_date=None, doctor_id=None, limit=10
    ):
        """Generate common diagnosis trends from consultations."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Query consultations for assessment/diagnosis data
        query = db.session.query(
            Consultation.assessment,
            func.count(Consultation.id).label("count"),
            func.count(func.distinct(Consultation.patient_id)).label("unique_patients"),
        ).filter(
            func.date(Consultation.consultation_date) >= start_date,
            func.date(Consultation.consultation_date) <= end_date,
            Consultation.assessment.isnot(None),
            Consultation.assessment != "",
        )

        if doctor_id:
            query = query.filter(Consultation.doctor_id == doctor_id)

        results = (
            query.group_by(Consultation.assessment)
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )

        return [
            {
                "diagnosis": r.assessment,
                "total_cases": r.count,
                "unique_patients": r.unique_patients,
            }
            for r in results
        ]

    @staticmethod
    def generate_doctor_performance(start_date=None, end_date=None, doctor_id=None):
        """Generate doctor performance metrics from existing data."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Get doctors to analyze
        doctors_query = User.query.filter_by(role="doctor", active=True)
        if doctor_id:
            doctors_query = doctors_query.filter_by(id=doctor_id)

        doctors = doctors_query.all()
        performance_data = []

        for doctor in doctors:
            # Appointment metrics
            appointments = Appointment.query.filter(
                Appointment.doctor_id == doctor.id,
                func.date(Appointment.appointment_date) >= start_date,
                func.date(Appointment.appointment_date) <= end_date,
            ).all()

            # Consultation metrics
            consultations = Consultation.query.filter(
                Consultation.doctor_id == doctor.id,
                func.date(Consultation.consultation_date) >= start_date,
                func.date(Consultation.consultation_date) <= end_date,
            ).all()

            # Prescription metrics
            prescriptions = Prescription.query.filter(
                Prescription.doctor_id == doctor.id,
                func.date(Prescription.prescribed_date) >= start_date,
                func.date(Prescription.prescribed_date) <= end_date,
            ).all()

            # Calculate performance metrics
            total_appointments = len(appointments)
            completed_appointments = len(
                [a for a in appointments if a.status == AppointmentStatus.COMPLETED]
            )
            total_consultations = len(consultations)
            completed_consultations = len(
                [c for c in consultations if c.status == ConsultationStatus.COMPLETED]
            )
            total_prescriptions = len(prescriptions)

            # Patient metrics
            unique_patients = len(set([a.patient_id for a in appointments]))

            performance_data.append(
                {
                    "doctor_id": doctor.id,
                    "doctor_name": doctor.display_name,
                    "specialization": doctor.specialization,
                    "total_appointments": total_appointments,
                    "completed_appointments": completed_appointments,
                    "completion_rate": round(
                        (
                            (completed_appointments / total_appointments * 100)
                            if total_appointments > 0
                            else 0
                        ),
                        2,
                    ),
                    "total_consultations": total_consultations,
                    "completed_consultations": completed_consultations,
                    "total_prescriptions": total_prescriptions,
                    "unique_patients": unique_patients,
                    "avg_patients_per_day": round(
                        unique_patients / ((end_date - start_date).days + 1), 2
                    ),
                }
            )

        return performance_data

    @staticmethod
    def generate_daily_summary(target_date=None):
        """Generate daily summary metrics from existing data."""
        if not target_date:
            target_date = date.today()

        # Appointment metrics for the day
        appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) == target_date
        ).all()

        # Consultation metrics for the day
        consultations = Consultation.query.filter(
            func.date(Consultation.consultation_date) == target_date
        ).all()

        # Prescription metrics for the day
        prescriptions = Prescription.query.filter(
            func.date(Prescription.prescribed_date) == target_date
        ).all()

        # New patient registrations
        new_patients = User.query.filter(
            User.role == "patient", func.date(User.created_at) == target_date
        ).count()

        return {
            "date": target_date.strftime("%Y-%m-%d"),
            "total_appointments": len(appointments),
            "completed_appointments": len(
                [a for a in appointments if a.status == AppointmentStatus.COMPLETED]
            ),
            "total_consultations": len(consultations),
            "completed_consultations": len(
                [c for c in consultations if c.status == ConsultationStatus.COMPLETED]
            ),
            "total_prescriptions": len(prescriptions),
            "new_patients": new_patients,
            "unique_patients_seen": len(
                set(
                    [
                        a.patient_id
                        for a in appointments
                        if a.status == AppointmentStatus.COMPLETED
                    ]
                )
            ),
        }

    @staticmethod
    def generate_weekly_summary(start_date=None):
        """Generate weekly summary metrics."""
        if not start_date:
            start_date = date.today() - timedelta(days=7)
        end_date = start_date + timedelta(days=6)

        # Generate daily summaries for the week
        daily_summaries = []
        current_date = start_date

        while current_date <= end_date:
            daily_summaries.append(
                AnalyticsService.generate_daily_summary(current_date)
            )
            current_date += timedelta(days=1)

        # Calculate weekly totals
        weekly_totals = {
            "week_start": start_date.strftime("%Y-%m-%d"),
            "week_end": end_date.strftime("%Y-%m-%d"),
            "total_appointments": sum(d["total_appointments"] for d in daily_summaries),
            "completed_appointments": sum(
                d["completed_appointments"] for d in daily_summaries
            ),
            "total_consultations": sum(
                d["total_consultations"] for d in daily_summaries
            ),
            "completed_consultations": sum(
                d["completed_consultations"] for d in daily_summaries
            ),
            "total_prescriptions": sum(
                d["total_prescriptions"] for d in daily_summaries
            ),
            "new_patients": sum(d["new_patients"] for d in daily_summaries),
            "daily_breakdown": daily_summaries,
        }

        return weekly_totals

    @staticmethod
    def generate_monthly_summary(year=None, month=None):
        """Generate monthly summary metrics."""
        if not year:
            year = date.today().year
        if not month:
            month = date.today().month

        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        # Get monthly metrics directly from existing models
        appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) >= start_date,
            func.date(Appointment.appointment_date) <= end_date,
        ).all()

        consultations = Consultation.query.filter(
            func.date(Consultation.consultation_date) >= start_date,
            func.date(Consultation.consultation_date) <= end_date,
        ).all()

        prescriptions = Prescription.query.filter(
            func.date(Prescription.prescribed_date) >= start_date,
            func.date(Prescription.prescribed_date) <= end_date,
        ).all()

        # Calculate weekly breakdowns
        weekly_summaries = []
        current_week_start = start_date

        while current_week_start <= end_date:
            weekly_summaries.append(
                AnalyticsService.generate_weekly_summary(current_week_start)
            )
            current_week_start += timedelta(days=7)

        return {
            "month": f"{year}-{month:02d}",
            "month_name": start_date.strftime("%B %Y"),
            "total_appointments": len(appointments),
            "completed_appointments": len(
                [a for a in appointments if a.status == AppointmentStatus.COMPLETED]
            ),
            "total_consultations": len(consultations),
            "completed_consultations": len(
                [c for c in consultations if c.status == ConsultationStatus.COMPLETED]
            ),
            "total_prescriptions": len(prescriptions),
            "unique_patients": len(set([a.patient_id for a in appointments])),
            "weekly_breakdown": weekly_summaries,
        }

    @staticmethod
    def get_system_statistics():
        """Get overall system statistics."""
        # Total counts
        total_patients = User.query.filter_by(role="patient", active=True).count()
        total_doctors = User.query.filter_by(role="doctor", active=True).count()
        total_appointments = Appointment.query.count()
        total_consultations = Consultation.query.count()
        total_prescriptions = Prescription.query.count()

        # Recent activity (last 30 days)
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) >= thirty_days_ago
        ).count()

        recent_consultations = Consultation.query.filter(
            func.date(Consultation.consultation_date) >= thirty_days_ago
        ).count()

        return {
            "total_patients": total_patients,
            "total_doctors": total_doctors,
            "total_appointments": total_appointments,
            "total_consultations": total_consultations,
            "total_prescriptions": total_prescriptions,
            "recent_appointments": recent_appointments,
            "recent_consultations": recent_consultations,
            "avg_appointments_per_day": round(recent_appointments / 30, 1),
            "avg_consultations_per_day": round(recent_consultations / 30, 1),
        }

    @staticmethod
    def export_report_data(
        report_type, start_date, end_date, format="json", doctor_id=None
    ):
        """Export report data in specified format."""
        data = {}

        if report_type == "appointments":
            data = AnalyticsService.generate_appointment_metrics(
                start_date, end_date, doctor_id
            )
        elif report_type == "prescriptions":
            data = AnalyticsService.generate_prescription_trends(
                start_date, end_date, doctor_id
            )
        elif report_type == "performance":
            data = AnalyticsService.generate_doctor_performance(
                start_date, end_date, doctor_id
            )
        elif report_type == "daily":
            data = AnalyticsService.generate_daily_summary(start_date)
        elif report_type == "weekly":
            data = AnalyticsService.generate_weekly_summary(start_date)
        elif report_type == "monthly":
            data = AnalyticsService.generate_monthly_summary(
                start_date.year, start_date.month
            )
        elif report_type == "system":
            data = AnalyticsService.get_system_statistics()

        if format == "json":
            return json.dumps(data, indent=2, default=str)
        elif format == "csv":
            return AnalyticsService._convert_to_csv(data, report_type)

        return data

    @staticmethod
    def _convert_to_csv(data, report_type):
        """Convert data to CSV format."""
        import csv
        import io

        output = io.StringIO()

        if report_type == "appointments" and isinstance(data, dict):
            writer = csv.writer(output)
            writer.writerow(["Metric", "Value"])
            for key, value in data.items():
                writer.writerow([key.replace("_", " ").title(), value])

        elif report_type in ["prescriptions", "performance"] and isinstance(data, list):
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

        return output.getvalue()

    @staticmethod
    def _convert_to_csv(data, report_type):
        """Convert data to CSV format."""
        import csv
        import io

        output = io.StringIO()

        if report_type == "appointments" and isinstance(data, dict):
            writer = csv.writer(output)
            writer.writerow(["Metric", "Value"])
            for key, value in data.items():
                writer.writerow([key.replace("_", " ").title(), value])

        elif report_type in ["prescriptions", "performance"] and isinstance(data, list):
            if data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

        return output.getvalue()
