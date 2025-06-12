# C.A.R.E. - Clinical Appointment & Record Entry

A modern healthcare management system featuring comprehensive role-based authentication, patient records management, and appointment scheduling.

## ✨ Key Features

-   **🏥 Healthcare-Focused**: Designed specifically for clinical environments
-   **👥 Role-Based Access**: Patient, Doctor, Staff, and Admin user types
-   **🔐 Complete Authentication**: Registration, login, password reset, email verification
-   **📋 Electronic Medical Records**: Digital patient records and consultation notes
-   **📅 Appointment Management**: Online booking and scheduling system
-   **🛡️ Advanced Security**: Account lockout, rate limiting, hCaptcha integration
-   **🌓 Theme System**: Light/Dark/System modes with persistent preferences
-   **📧 Email Integration**: Contact forms, password reset, verification emails
-   **📋 Legal Compliance**: Privacy policy, terms of service, cookie policy (RA 10173 compliant)
-   **🚀 Deployment Ready**: Vercel serverless and traditional hosting support

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd C.A.R.E
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Activate Virtual Environment

```bash
# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configuration

```bash
# On Windows
copy .env.template .env

# On macOS/Linux
cp .env.template .env

# Edit .env with your settings
```

### 6. Initialize Database

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 7. Run Application

```bash
python run.py
```

Visit `http://localhost:5000` to view the C.A.R.E. system.

## 📚 Documentation

### Core Documentation
- **[Authentication System](docs/AUTHENTICATION.md)** - Complete authentication with email verification
- **[Admin Panel](docs/ADMIN_PANEL.md)** - User management and system monitoring
- **[hCaptcha Integration](docs/HCAPTCHA.md)** - Bot protection and security
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Vercel, VPS, and production deployment

### Features Overview

#### 🔐 Authentication & Security
- User registration with mandatory email verification
- Secure login with username or email
- Password reset functionality
- Account lockout protection (IP-based)
- Argon2 password hashing
- Session management with security headers

#### 👥 Admin Panel
- **Default Login**: username: `admin`, password: `admin123` ⚠️ *Change in production!*
- User management (activate/deactivate, admin privileges)
- Real-time dashboard with statistics
- Security logs and monitoring
- Automated cleanup tools
- Contact form management

#### 🛡️ Security Features
- **Account Lockout**: 5 failed attempts = 15-minute lockout (configurable)
- **hCaptcha Protection**: Bot prevention on forms
- **Rate Limiting**: IP-based request limiting
- **CSRF Protection**: Built-in CSRF protection
- **Secure Headers**: Security headers for production

#### 📧 Email Verification System
- **Verification Pending Page**: Clear instructions and status
- **Auto-refresh**: Automatic verification status checking
- **Resend Functionality**: Easy verification email resending
- **Login Blocking**: Prevents login until email verified
- **24-hour Expiration**: Secure, time-limited tokens

#### 🌓 Theme System
- **Light Mode**: Clean, bright interface
- **Dark Mode**: Modern dark theme
- **System Mode**: Follows OS theme preference
- **Persistent Settings**: Saved in localStorage
- **Smooth Transitions**: Elegant theme switching

## 👤 Default User Accounts

The system automatically creates sample accounts for testing all user roles:

### 🔧 Administrator Account

-   **Username**: `admin`
-   **Password**: `admin123`
-   **Email**: `admin@care-system.com`
-   **Role**: Admin (Full system access)
-   **Status**: ✅ Email Verified

### 👩‍⚕️ Healthcare Professional Accounts

#### Doctor Account

-   **Username**: `doctor_sample`
-   **Password**: `doctor123`
-   **Email**: `doctor@care-system.com`
-   **Role**: Doctor
-   **License**: `MD-2024-001`
-   **Specialization**: Internal Medicine
-   **Facility**: C.A.R.E. Medical Center
-   **Status**: ✅ Email Verified

#### Staff Account

-   **Username**: `staff_sample`
-   **Password**: `staff123`
-   **Email**: `staff@care-system.com`
-   **Role**: Staff
-   **License**: `RN-2024-001`
-   **Facility**: C.A.R.E. Medical Center
-   **Status**: ✅ Email Verified

### 👤 Patient Account

-   **Username**: `patient_sample`
-   **Password**: `patient123`
-   **Email**: `patient@care-system.com`
-   **Role**: Patient
-   **Name**: Ana Reyes
-   **DOB**: May 15, 1990
-   **Address**: 123 Health Street, Wellness City, Metro Manila
-   **Emergency Contact**: Pedro Reyes (+63 555 EMER-123)
-   **Status**: ✅ Email Verified

> ⚠️ **Important**: Change these default credentials in production environments!

## 🔧 Environment Configuration

### Required Variables

```bash
# Core Settings
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=sqlite:///app.db

# Email Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Security Settings
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15

# hCaptcha (optional)
HCAPTCHA_ENABLED=true
HCAPTCHA_SITE_KEY=your-site-key
HCAPTCHA_SECRET_KEY=your-secret-key
```

## 📚 User Roles & Permissions

### 👤 Patient

-   ✅ Register and manage personal profile
-   ✅ Book appointments online
-   ✅ View own medical records
-   ✅ Update personal information
-   ✅ Manage emergency contacts

### 👩‍⚕️ Doctor

-   ✅ All patient permissions
-   ✅ View patient records
-   ✅ Manage appointments
-   ✅ Write prescriptions
-   ✅ Add consultation notes
-   ✅ Manage medical specialization

### 👥 Staff

-   ✅ View patient records
-   ✅ Manage appointments
-   ✅ Manage patient queue
-   ✅ Update facility information
-   ✅ Assist with administrative tasks

### 🔧 Admin

-   ✅ All system permissions
-   ✅ User management (activate/deactivate, role changes)
-   ✅ Real-time dashboard with statistics
-   ✅ Security logs and monitoring
-   ✅ System maintenance tools

## 🔐 Security Features

### 🛡️ Authentication & Access Control

-   **Email Verification**: Mandatory for all accounts
-   **Role-Based Access**: Granular permissions per user type
-   **Account Lockout**: 5 failed attempts = 15-minute lockout
-   **Password Security**: Argon2 hashing with strength validation
-   **Session Management**: Secure sessions with "Remember Me" option

### 🔒 Healthcare Data Protection

-   **RA 10173 Compliance**: Follows Philippine Data Privacy Act
-   **Secure File Handling**: Encrypted data storage
-   **Audit Trails**: Complete logging of data access and modifications
-   **Professional Verification**: License number validation for healthcare staff

## 📁 Project Structure

```
C.A.R.E/
├── app/                          # Main application package
│   ├── models/                   # Database models
│   ├── routes/                   # Application routes
│   ├── static/                   # Static files (CSS, JS, images)
│   │   ├── css/                  # CSS files
│   │   ├── images/               # Image files
│   │   └── js/                   # JavaScript files
│   │       ├── components/       # Reusable JavaScript components
│   │       ├── utils/            # Utility JavaScript files
│   │       │   ├── pagination/   # Pagination utilities
│   │       │   └── theme/        # Theme utilities
│   │       └── main.js           # Main JavaScript file
│   ├── templates/                # HTML templates
│   │   ├── admin/                # Admin panel templates
│   │   ├── auth/                 # Authentication templates
│   │   ├── partials/             # Reusable template components
│   │   │   ├── admin/            # Admin panel components
│   │   │   │   ├── dashboard/    # Admin dashboard components
│   │   │   │   ├── logs/         # Admin logs components
│   │   │   │   ├── user-details/ # User details components
│   │   │   │   └── users/        # User management components
│   │   │   ├── shared/           # Shared components
│   │   │   ├── footer.html       # Footer component
│   │   │   └── navbar.html       # Navbar component
│   │   ├── password/             # Password reset templates
│   │   ├── policy-pages/         # Policy page templates
│   │   ├── profile/              # Profile templates
│   │   ├── about.html            # About page template
│   │   ├── base.html             # Base template
│   │   ├── contact.html          # Contact page template
│   │   └── home.html             # Home page template
│   ├── utils/                    # Utility modules
│   └── __init__.py               # Application factory
├── docs/                         # Documentation files
├── instance/                     # Instance-specific files
├── migrations/                   # Database migrations
├── .env.template                 # Environment variables template
├── .gitignore                    # Git ignore file
├── .vercelignore                 # Vercel ignore file
├── config.py                     # Configuration
├── LICENSE                       # MIT License file
├── README.md                     # Project README
├── requirements.txt              # Dependencies
├── run.py                        # Application entry point
└── vercel.json                   # Vercel deployment config
```

## 🚀 Deployment Options

### Vercel (Serverless)

-   **One-click Deploy**: Automatic detection and deployment
-   **Environment Adaptation**: Auto-disables database features for demo
-   **Contact Form**: Logs submissions for demonstration

### Traditional Hosting

-   **Full Features**: Complete database and authentication
-   **VPS/Dedicated**: Full control and customization
-   **Healthcare Compliance**: Full HIPAA/RA 10173 compliance features

## 🛡️ Security in Production

### Essential Steps

1. **Change Default Credentials**: Update all sample account passwords
2. **Configure HTTPS**: Essential for healthcare data protection
3. **Set Strong Secret Key**: Use cryptographically secure secret
4. **Enable hCaptcha**: Protect forms from bot submissions
5. **Configure Email**: Set up production email service
6. **Monitor Logs**: Regular review of security and access logs

### Healthcare Compliance Checklist

-   [ ] HTTPS configured with valid SSL certificate
-   [ ] All default credentials changed
-   [ ] Professional license verification implemented
-   [ ] Patient data encryption enabled
-   [ ] Audit logging configured
-   [ ] Backup and recovery procedures established
-   [ ] Staff training on data privacy completed

## 🔨 Technologies

-   **Backend**: Python Flask, SQLAlchemy, Flask-Migrate
-   **Frontend**: Tailwind CSS, Bootstrap Icons, Vanilla JavaScript
-   **Database**: SQLite (dev), PostgreSQL/MySQL (production)
-   **Security**: Argon2, Flask-WTF, hCaptcha
-   **Email**: Flask-Mail with SMTP support
-   **Deployment**: Vercel, traditional hosting
-   **Compliance**: RA 10173 (Data Privacy Act of 2012) compliant

## 📋 Requirements Tracking

-   **[Functional Requirements](FUNCTIONAL-REQUIREMENTS.md)**: ✅ Feature checklist
-   **[Non-Functional Requirements](NON-FUNCTIONAL-REQUIREMENTS.md)**: 🚀 Performance & security checklist

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

-   **Documentation**: Check the [docs/](docs/) directory for detailed guides
-   **Issues**: Open an issue on GitHub for bug reports or feature requests
-   **Email**: Contact form available in the application

---

**⚡ Quick Deploy**: [![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/your-username/C.A.R.E)

**🏥 C.A.R.E.** - Transforming healthcare management from manual processes to modern digital solutions.
