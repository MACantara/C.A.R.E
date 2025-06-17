from flask import current_app, render_template_string
from flask_mail import Message
from app import mail
import logging


def send_appointment_confirmation(appointment):
    """Send appointment confirmation email to patient."""
    try:
        if current_app.config.get("DISABLE_DATABASE", False):
            current_app.logger.info("Email sending disabled in this environment")
            return False

        subject = f"C.A.R.E. - Appointment Confirmation"

        # Email template
        email_body = f"""
        <h2>Appointment Confirmed</h2>
        <p>Dear {appointment.patient.display_name},</p>
        
        <p>Your appointment has been successfully booked with our healthcare team.</p>
        
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3>Appointment Details:</h3>
            <ul>
                <li><strong>Doctor:</strong> {appointment.doctor.display_name}</li>
                <li><strong>Date:</strong> {appointment.appointment_date.strftime('%B %d, %Y')}</li>
                <li><strong>Time:</strong> {appointment.appointment_date.strftime('%I:%M %p')}</li>
                <li><strong>Duration:</strong> {appointment.duration_minutes} minutes</li>
                <li><strong>Type:</strong> {appointment.appointment_type.value.replace('_', ' ').title()}</li>
            </ul>
        </div>
        
        <p><strong>Important Notes:</strong></p>
        <ul>
            <li>Please arrive 10 minutes before your appointment time</li>
            <li>Bring a valid ID and your medical records if available</li>
            <li>You can cancel this appointment up to 2 hours before the scheduled time</li>
        </ul>
        
        <p>If you need to reschedule or cancel, please contact us as soon as possible.</p>
        
        <p>Thank you for choosing C.A.R.E. Healthcare Solutions.</p>
        
        <p>Best regards,<br>
        C.A.R.E. Medical Team</p>
        """

        msg = Message(
            subject=subject,
            recipients=[appointment.patient.email],
            html=email_body,
            sender=current_app.config.get(
                "MAIL_DEFAULT_SENDER", "noreply@care-system.com"
            ),
        )

        mail.send(msg)
        current_app.logger.info(
            f"Appointment confirmation sent to {appointment.patient.email}"
        )
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to send appointment confirmation: {e}")
        return False



def send_appointment_cancellation(appointment, reason=None):
    """Send appointment cancellation email to patient."""
    try:
        if current_app.config.get("DISABLE_DATABASE", False):
            current_app.logger.info("Email sending disabled in this environment")
            return False

        subject = f"C.A.R.E. - Appointment Cancelled"

        email_body = f"""
        <h2>Appointment Cancelled</h2>
        <p>Dear {appointment.patient.display_name},</p>
        
        <p>We regret to inform you that your appointment has been cancelled.</p>
        
        <div style="background-color: #fff3cd; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
            <h3>Cancelled Appointment Details:</h3>
            <ul>
                <li><strong>Doctor:</strong> {appointment.doctor.display_name}</li>
                <li><strong>Date:</strong> {appointment.appointment_date.strftime('%B %d, %Y')}</li>
                <li><strong>Time:</strong> {appointment.appointment_date.strftime('%I:%M %p')}</li>
            </ul>
            {f'<p><strong>Reason:</strong> {reason}</p>' if reason else ''}
        </div>
        
        <p>To schedule a new appointment, please contact us or use our online booking system.</p>
        
        <p>We apologize for any inconvenience caused.</p>
        
        <p>Best regards,<br>
        C.A.R.E. Medical Team</p>
        """

        msg = Message(
            subject=subject,
            recipients=[appointment.patient.email],
            html=email_body,
            sender=current_app.config.get(
                "MAIL_DEFAULT_SENDER", "noreply@care-system.com"
            ),
        )

        mail.send(msg)
        current_app.logger.info(
            f"Appointment cancellation sent to {appointment.patient.email}"
        )
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to send appointment cancellation: {e}")
        return False
