import random
from datetime import datetime, timedelta, date
from faker import Faker
from app import db
from app.models.user import User
from app.models.email_verification import EmailVerification
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.medical_record import (
    Consultation, Prescription, Allergy, VitalSigns,
    ConsultationStatus, PrescriptionStatus
)
from app.models.message import InternalMessage
from app.models.queue import PatientQueue, QueueStatus
from app.utils.timezone_utils import get_user_timezone, get_current_time

fake = Faker()

class SampleDataGenerator:
    """Generate realistic sample data for the C.A.R.E. system."""
    
    def __init__(self):
        self.users = {"patients": [], "doctors": [], "staff": []}
        self.appointments = []
        self.consultations = []
        
        # Medical data lists for realistic generation
        self.specializations = [
            "Internal Medicine", "Pediatrics", "Cardiology", "Dermatology",
            "Orthopedics", "Neurology", "Psychiatry", "Radiology",
            "Emergency Medicine", "Family Medicine", "Oncology", "Surgery"
        ]
        
        self.medications = [
            "Metformin", "Lisinopril", "Atorvastatin", "Amlodipine", "Metoprolol",
            "Omeprazole", "Losartan", "Simvastatin", "Levothyroxine", "Azithromycin",
            "Amoxicillin", "Prednisone", "Ibuprofen", "Acetaminophen", "Aspirin"
        ]
        
        self.allergies = [
            "Penicillin", "Aspirin", "Ibuprofen", "Shellfish", "Peanuts",
            "Latex", "Sulfa drugs", "Codeine", "Morphine", "Contrast dye"
        ]
        
        self.chief_complaints = [
            "Chest pain", "Shortness of breath", "Headache", "Abdominal pain",
            "Back pain", "Fever", "Cough", "Fatigue", "Dizziness", "Nausea",
            "Joint pain", "Skin rash", "Sleep problems", "Anxiety", "Depression"
        ]
        
        self.facilities = [
            "Metro Manila Medical Center", "Makati General Hospital",
            "Philippine Heart Center", "St. Luke's Medical Center",
            "Asian Hospital and Medical Center", "The Medical City"
        ]

    def generate_users(self, num_patients=50, num_doctors=10, num_staff=5):
        """Generate sample users (patients, doctors, staff)."""
        print(f"Generating {num_patients} patients, {num_doctors} doctors, {num_staff} staff...")
        
        # Check if admin user already exists
        existing_admin = User.query.filter_by(username="admin").first()
        if existing_admin:
            print("Admin user already exists, skipping admin creation.")
        
        # Generate patients
        for i in range(num_patients):
            username = f"patient_{i+1:03d}"
            email = f"patient{i+1:03d}@example.com"
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                print(f"User {username} already exists, skipping.")
                continue
                
            user = User(
                username=username,
                email=email,
                role="patient",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=85),
                phone_number=fake.phone_number()[:20],
                address=fake.address(),
                emergency_contact=fake.name(),
                emergency_phone=fake.phone_number()[:20],
                active=True
            )
            user.set_password("password123")
            db.session.add(user)
            self.users["patients"].append(user)
        
        # Generate doctors
        for i in range(num_doctors):
            username = f"doctor_{i+1:02d}"
            email = f"doctor{i+1:02d}@care-system.com"
            license_num = f"MD-{fake.random_number(digits=6)}"
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                print(f"User {username} already exists, skipping.")
                # Still add to list if exists for relationship purposes
                existing_user = User.query.filter_by(username=username).first()
                self.users["doctors"].append(existing_user)
                continue
                
            # Check for unique license number
            while User.query.filter_by(license_number=license_num).first():
                license_num = f"MD-{fake.random_number(digits=6)}"
                
            user = User(
                username=username,
                email=email,
                role="doctor",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                license_number=license_num,
                specialization=random.choice(self.specializations),
                facility_name=random.choice(self.facilities),
                phone_number=fake.phone_number()[:20],
                active=True
            )
            user.set_password("doctor123")
            db.session.add(user)
            self.users["doctors"].append(user)
        
        # Generate staff
        for i in range(num_staff):
            username = f"staff_{i+1:02d}"
            email = f"staff{i+1:02d}@care-system.com"
            
            # Check if user already exists
            if User.query.filter_by(username=username).first():
                print(f"User {username} already exists, skipping.")
                # Still add to list if exists for relationship purposes
                existing_user = User.query.filter_by(username=username).first()
                self.users["staff"].append(existing_user)
                continue
                
            user = User(
                username=username,
                email=email,
                role="staff",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                facility_name=random.choice(self.facilities),
                phone_number=fake.phone_number()[:20],
                active=True
            )
            user.set_password("staff123")
            db.session.add(user)
            self.users["staff"].append(user)
        
        # Create admin user only if it doesn't exist
        if not existing_admin:
            admin = User(
                username="admin",
                email="admin@care-system.com",
                role="staff",
                is_admin=True,
                first_name="Admin",
                last_name="User",
                active=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
        
        try:
            db.session.commit()
            print("Users generated successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating users: {e}")
            raise

    def verify_all_emails(self):
        """Create and verify email verifications for all users."""
        print("Creating and verifying email verifications...")
        
        users = User.query.all()
        for user in users:
            # Check if email verification already exists
            existing_verification = EmailVerification.query.filter_by(
                user_id=user.id, email=user.email, is_verified=True
            ).first()
            
            if existing_verification:
                print(f"Email already verified for user {user.username}, skipping.")
                continue
                
            # Create email verification
            verification = EmailVerification.create_verification(user.id, user.email)
            # Immediately verify it
            verification.verify()
        
        print("Email verifications created and verified!")

    def generate_appointments(self, num_appointments=100):
        """Generate sample appointments."""
        print(f"Generating {num_appointments} appointments...")
        
        patients = self.users["patients"]
        doctors = self.users["doctors"]
        
        if not patients or not doctors:
            print("Error: Need patients and doctors to generate appointments")
            return
        
        for i in range(num_appointments):
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            
            # Generate appointment date (mix of past, present, future)
            if i < num_appointments * 0.3:  # 30% past appointments
                appointment_date = fake.date_time_between(start_date='-30d', end_date='-1d')
                status = random.choice([AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED])
            elif i < num_appointments * 0.7:  # 40% upcoming appointments
                appointment_date = fake.date_time_between(start_date='+1d', end_date='+30d')
                status = random.choice([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
            else:  # 30% today or recent
                appointment_date = fake.date_time_between(start_date='-7d', end_date='+7d')
                status = random.choice([
                    AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS, AppointmentStatus.COMPLETED
                ])
            
            # Ensure appointment is during business hours
            appointment_date = appointment_date.replace(
                hour=random.randint(9, 16),
                minute=random.choice([0, 15, 30, 45]),
                second=0,
                microsecond=0
            )
            
            appointment = Appointment(
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_date=appointment_date,
                duration_minutes=random.choice([30, 45, 60]),
                appointment_type=random.choice(list(AppointmentType)),
                chief_complaint=random.choice(self.chief_complaints),
                status=status,
                confirmation_sent=random.choice([True, False])
            )
            
            # Set additional timestamps based on status
            if status == AppointmentStatus.CONFIRMED:
                appointment.confirmed_at = appointment_date - timedelta(days=random.randint(1, 7))
            elif status == AppointmentStatus.CANCELLED:
                appointment.cancelled_at = appointment_date - timedelta(hours=random.randint(2, 48))
                appointment.cancellation_reason = random.choice([
                    "Patient requested cancellation", "Doctor unavailable",
                    "Emergency situation", "Schedule conflict"
                ])
            
            db.session.add(appointment)
            self.appointments.append(appointment)
        
        db.session.commit()
        print("Appointments generated successfully!")

    def generate_consultations(self, num_consultations=50):
        """Generate sample consultations for completed appointments."""
        print(f"Generating {num_consultations} consultations...")
        
        # Get completed appointments
        completed_appointments = [apt for apt in self.appointments 
                                if apt.status == AppointmentStatus.COMPLETED]
        
        if len(completed_appointments) < num_consultations:
            print(f"Warning: Only {len(completed_appointments)} completed appointments available")
            num_consultations = len(completed_appointments)
        
        selected_appointments = random.sample(completed_appointments, num_consultations)
        
        for appointment in selected_appointments:
            consultation = Consultation(
                patient_id=appointment.patient_id,
                doctor_id=appointment.doctor_id,
                appointment_id=appointment.id,
                consultation_date=appointment.appointment_date,
                status=ConsultationStatus.COMPLETED,
                chief_complaint=appointment.chief_complaint,
                history_present_illness=fake.text(max_nb_chars=200),
                past_medical_history=fake.text(max_nb_chars=150),
                physical_examination=fake.text(max_nb_chars=100),
                assessment=fake.text(max_nb_chars=100),
                treatment_plan=fake.text(max_nb_chars=150),
                follow_up_instructions=fake.text(max_nb_chars=100),
                next_appointment_recommended=random.choice([True, False]),
                next_appointment_timeframe=random.choice([
                    "1 week", "2 weeks", "1 month", "3 months", "6 months"
                ]) if random.choice([True, False]) else None
            )
            
            db.session.add(consultation)
            self.consultations.append(consultation)
        
        db.session.commit()
        print("Consultations generated successfully!")

    def generate_prescriptions(self, num_prescriptions=75):
        """Generate sample prescriptions."""
        print(f"Generating {num_prescriptions} prescriptions...")
        
        patients = self.users["patients"]
        doctors = self.users["doctors"]
        
        for i in range(num_prescriptions):
            patient = random.choice(patients)
            doctor = random.choice(doctors)
            consultation = random.choice(self.consultations) if self.consultations else None
            
            medication = random.choice(self.medications)
            
            prescription = Prescription(
                patient_id=patient.id,
                doctor_id=doctor.id,
                consultation_id=consultation.id if consultation else None,
                medication_name=medication,
                generic_name=f"Generic {medication}",
                dosage=random.choice(["5mg", "10mg", "25mg", "50mg", "100mg"]),
                frequency=random.choice([
                    "Once daily", "Twice daily", "Three times daily",
                    "Every 6 hours", "As needed", "Before meals"
                ]),
                duration=random.choice([
                    "7 days", "14 days", "30 days", "90 days", "As needed"
                ]),
                quantity=random.choice(["30 tablets", "60 tablets", "90 tablets"]),
                instructions=fake.text(max_nb_chars=100),
                indication=random.choice(self.chief_complaints),
                status=random.choice(list(PrescriptionStatus)),
                prescribed_date=fake.date_time_between(start_date='-90d', end_date='now'),
                start_date=fake.date_between(start_date='-30d', end_date='+7d'),
                end_date=fake.date_between(start_date='+7d', end_date='+90d')
            )
            
            db.session.add(prescription)
        
        db.session.commit()
        print("Prescriptions generated successfully!")

    def generate_allergies(self, num_allergies=30):
        """Generate sample allergies for patients."""
        print(f"Generating {num_allergies} allergies...")
        
        patients = self.users["patients"]
        doctors = self.users["doctors"]
        
        for i in range(num_allergies):
            patient = random.choice(patients)
            recorder = random.choice(doctors + self.users["staff"])
            
            allergy = Allergy(
                patient_id=patient.id,
                recorded_by=recorder.id,
                allergen=random.choice(self.allergies),
                allergy_type=random.choice(["drug", "food", "environmental", "contact"]),
                severity=random.choice(["mild", "moderate", "severe", "life-threatening"]),
                reaction=fake.text(max_nb_chars=100),
                notes=fake.text(max_nb_chars=50),
                is_active=random.choice([True, False]),
                recorded_date=fake.date_time_between(start_date='-365d', end_date='now')
            )
            
            db.session.add(allergy)
        
        db.session.commit()
        print("Allergies generated successfully!")

    def generate_vital_signs(self, num_vital_signs=80):
        """Generate sample vital signs."""
        print(f"Generating {num_vital_signs} vital signs...")
        
        patients = self.users["patients"]
        recorders = self.users["doctors"] + self.users["staff"]
        
        for i in range(num_vital_signs):
            patient = random.choice(patients)
            recorder = random.choice(recorders)
            consultation = random.choice(self.consultations) if self.consultations and random.choice([True, False]) else None
            
            vital_signs = VitalSigns(
                patient_id=patient.id,
                recorded_by=recorder.id,
                consultation_id=consultation.id if consultation else None,
                temperature=round(random.uniform(36.0, 39.5), 1),
                blood_pressure_systolic=random.randint(90, 180),
                blood_pressure_diastolic=random.randint(60, 120),
                heart_rate=random.randint(60, 120),
                respiratory_rate=random.randint(12, 25),
                oxygen_saturation=round(random.uniform(95.0, 100.0), 1),
                weight=round(random.uniform(40.0, 120.0), 1),
                height=round(random.uniform(140.0, 200.0), 1),
                pain_scale=random.randint(0, 10),
                notes=fake.text(max_nb_chars=50),
                recorded_date=fake.date_time_between(start_date='-90d', end_date='now')
            )
            
            db.session.add(vital_signs)
        
        db.session.commit()
        print("Vital signs generated successfully!")

    def generate_messages(self, num_messages=40):
        """Generate sample internal messages."""
        print(f"Generating {num_messages} internal messages...")
        
        healthcare_staff = self.users["doctors"] + self.users["staff"]
        
        # Available message types and priorities as strings
        message_types = ["general", "queue_update", "appointment", "patient_info", "system"]
        message_priorities = ["low", "normal", "high", "urgent"]
        
        for i in range(num_messages):
            sender = random.choice(healthcare_staff)
            recipient = random.choice([staff for staff in healthcare_staff if staff.id != sender.id])
            
            appointment = random.choice(self.appointments) if random.choice([True, False]) else None
            patient = random.choice(self.users["patients"]) if random.choice([True, False]) else None
            
            message_subjects = [
                "Patient consultation follow-up",
                "Urgent: Patient requires immediate attention",
                "Schedule change notification",
                "Lab results available",
                "Prescription update needed",
                "Patient discharge instructions",
                "Medical equipment request",
                "Shift handover notes"
            ]
            
            message = InternalMessage(
                sender_id=sender.id,
                recipient_id=recipient.id,
                subject=random.choice(message_subjects),
                content=fake.text(max_nb_chars=300),
                message_type=random.choice(message_types),
                priority=random.choice(message_priorities),
                is_read=random.choice([True, False]),
                related_appointment_id=appointment.id if appointment else None,
                related_patient_id=patient.id if patient else None,
                created_at=fake.date_time_between(start_date='-30d', end_date='now')
            )
            
            # Set read timestamp if message is read
            if message.is_read:
                message.read_at = message.created_at + timedelta(
                    hours=random.randint(1, 48)
                )
            
            db.session.add(message)
        
        db.session.commit()
        print("Messages generated successfully!")

    def generate_queue_entries(self, num_queue_entries=25):
        """Generate sample patient queue entries using timezone-aware datetime."""
        print(f"Generating {num_queue_entries} queue entries...")
        
        # Get current timezone-aware time (handle case when outside request context)
        try:
            user_timezone = get_user_timezone()
            current_time_local = get_current_time(user_timezone)
        except RuntimeError:
            # Running outside of request context, use default timezone
            import pytz
            user_timezone = pytz.timezone("Asia/Manila")
            current_time_local = datetime.now(user_timezone)
        
        today_local = current_time_local.date()
        
        # Get today's and recent appointments using timezone-aware filtering
        yesterday_local = today_local - timedelta(days=1)
        tomorrow_local = today_local + timedelta(days=1)
        
        recent_appointments = [
            apt for apt in self.appointments
            if apt.appointment_date.date() >= yesterday_local
            and apt.appointment_date.date() <= tomorrow_local
        ]
        
        if len(recent_appointments) < num_queue_entries:
            num_queue_entries = len(recent_appointments)
            print(f"Adjusted to {num_queue_entries} queue entries based on available appointments")
        
        if num_queue_entries == 0:
            print("No recent appointments found for queue generation")
            return
        
        selected_appointments = random.sample(recent_appointments, num_queue_entries)
        
        for i, appointment in enumerate(selected_appointments):
            # Create timezone-aware queue creation time
            # Queue entries are typically created 30-120 minutes before appointment
            minutes_before = random.randint(30, 120)
            queue_created_time = appointment.appointment_date - timedelta(minutes=minutes_before)
            
            queue_entry = PatientQueue(
                appointment_id=appointment.id,
                queue_number=i + 1,
                status=random.choice(list(QueueStatus)),
                estimated_wait_time=random.randint(15, 120),
                created_at=queue_created_time
            )
            
            # Set timing based on status using timezone-aware calculations
            if queue_entry.status in [QueueStatus.IN_PROGRESS, QueueStatus.COMPLETED]:
                # Actual start time is some minutes after queue creation
                start_delay = random.randint(10, 60)
                queue_entry.actual_start_time = queue_created_time + timedelta(minutes=start_delay)
            
            if queue_entry.status == QueueStatus.COMPLETED:
                # Consultation duration for completed entries
                consultation_duration = random.randint(15, 45)
                queue_entry.actual_end_time = queue_entry.actual_start_time + timedelta(minutes=consultation_duration)
            
            if queue_entry.status == QueueStatus.DELAYED:
                queue_entry.delay_reason = random.choice([
                    "Doctor running late", "Emergency case priority",
                    "Additional tests required", "Patient arrived late"
                ])
            
            # Set updated_at to a reasonable time after creation
            if queue_entry.status != QueueStatus.WAITING:
                # Status was updated some time after creation
                update_delay = random.randint(5, 30)
                queue_entry.updated_at = queue_created_time + timedelta(minutes=update_delay)
            else:
                queue_entry.updated_at = queue_created_time
            
            db.session.add(queue_entry)
        
        db.session.commit()
        print("Queue entries generated successfully with timezone-aware timestamps!")

    def generate_all_sample_data(self):
        """Generate all sample data in the correct order."""
        print("Starting comprehensive sample data generation...")
        print("=" * 50)
        
        try:
            # Load existing users into our lists for relationship purposes
            existing_patients = User.query.filter_by(role="patient").all()
            existing_doctors = User.query.filter_by(role="doctor").all()
            existing_staff = User.query.filter_by(role="staff").all()
            
            self.users["patients"].extend(existing_patients)
            self.users["doctors"].extend(existing_doctors)
            self.users["staff"].extend(existing_staff)
            
            # Step 1: Generate users
            self.generate_users()
            
            # Step 2: Verify all emails
            self.verify_all_emails()
            
            # Refresh user lists after generation
            self.users["patients"] = User.query.filter_by(role="patient").all()
            self.users["doctors"] = User.query.filter_by(role="doctor").all()
            self.users["staff"] = User.query.filter_by(role="staff").all()
            
            # Step 3: Generate appointments
            self.generate_appointments()
            
            # Step 4: Generate consultations
            self.generate_consultations()
            
            # Step 5: Generate prescriptions
            self.generate_prescriptions()
            
            # Step 6: Generate allergies
            self.generate_allergies()
            
            # Step 7: Generate vital signs
            self.generate_vital_signs()
            
            # Step 8: Generate messages
            self.generate_messages()
            
            # Step 9: Generate queue entries
            self.generate_queue_entries()
            
            print("=" * 50)
            print("✅ All sample data generated successfully!")
            print("\nGenerated data summary:")
            print(f"• Users: {User.query.count()}")
            print(f"• Email Verifications: {EmailVerification.query.count()}")
            print(f"• Appointments: {Appointment.query.count()}")
            print(f"• Consultations: {Consultation.query.count()}")
            print(f"• Prescriptions: {Prescription.query.count()}")
            print(f"• Allergies: {Allergy.query.count()}")
            print(f"• Vital Signs: {VitalSigns.query.count()}")
            print(f"• Messages: {InternalMessage.query.count()}")
            print(f"• Queue Entries: {PatientQueue.query.count()}")
            
            print("\nSample login credentials:")
            print("• Admin: admin / admin123")
            print("• Doctor: doctor_01 / doctor123")
            print("• Staff: staff_01 / staff123")
            print("• Patient: patient_001 / password123")
            
        except Exception as e:
            print(f"❌ Error generating sample data: {e}")
            db.session.rollback()
            raise

def generate_sample_data():
    """Convenience function to generate all sample data."""
    generator = SampleDataGenerator()
    generator.generate_all_sample_data()

if __name__ == "__main__":
    # This allows running the script directly
    from app import create_app
    
    app = create_app()
    with app.app_context():
        generate_sample_data()
