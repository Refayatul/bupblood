# BUP Blood Bank 🩸

A comprehensive blood donor management system for Bangladesh University of Professionals (BUP) with user authentication, secure password management, and advanced search capabilities.

## 🎯 Project Overview

**Live Website:** [https://bupblood.org/](https://bupblood.org/) (Mirror: [https://bupblood.vercel.app/](https://bupblood.vercel.app/))  
**Purpose:** Blood donor registry and management system  
**Institution:** Bangladesh University of Professionals (BUP)  
**Admin Contact:** refayat.connect@gmail.com  
**Current Users:** 500+ registered donors  

## 🛠️ Tech Stack

- **Backend:** Flask 3.1.3 (Python)
- **Database:** SQLite (local) → Supabase PostgreSQL (production)
- **Image Storage:** Local static files → Supabase Storage (production)
- **Frontend:** Tailwind CSS + DaisyUI
- **Server:** Gunicorn (local), Vercel (production)
- **Authentication:** Flask-Login with secure password hashing

## ✨ Features

### 👤 User Features
- ✅ **Secure Registration** - Password-protected accounts with strength validation
- ✅ **User Authentication** - Login/logout system with session management
- ✅ **Personal Dashboard** - Update profile, availability, last donation date, and profile picture
- ✅ **Password Management** - Change password and secure reset functionality
- ✅ **Self-Service Password Reset** - Multi-factor verification (Student ID + Mobile + Dept + Blood Group)
- ✅ **Email Verification** - Required for password resets (with one-time exception for legacy users)
- ✅ **Availability Status** - Toggle between Available/Unavailable with visual badges
- ✅ **Profile Image Upload** - Custom profile pictures with automatic resizing
- ✅ **BUP Program Integration** - Faculty and program-based filtering using official structure

### 👨‍💼 Admin Features
- ✅ **Admin Panel** - Approve/reject new donor registrations
- ✅ **User Management** - View all pending and approved donors
- ✅ **Secure Admin Login** - Hardcoded credentials (admin/adminpassword)

### 🔍 Public Features
- ✅ **Blood Group Search** - Filter by all 8 blood types (A+, A-, B+, B-, AB+, AB-, O+, O-)
- ✅ **Faculty/Program Filter** - Search by BUP faculties and programs
- ✅ **Donor Cards** - Visual cards showing availability status
- ✅ **Direct Contact** - Call donors via tel: links
- ✅ **Responsive Design** - Mobile-optimized interface

## 🔐 Authentication & Security

### Password Reset Workflow
1. **User clicks "Forgot Password?"** on login page
2. **Identity Verification** - Enter Student ID, Mobile, Department, Blood Group
3. **Email Verification** (for users with email):
   - System shows masked email (e.g., `r***t@gmail.com`)
   - User confirms full email address
   - Password reset allowed upon confirmation
4. **One-Time Reset** (for legacy users without email):
   - System allows single password reset using verified identity
   - Subsequent resets require email verification
   - Users encouraged to add email to profile

### User Categories
- **New Users** (registered after updates): Full email verification required
- **Legacy Users** (441 existing): One-time password reset without email, then email required

## 📂 Directory Structure

```
BloodBank/
├── app.py                          # Main Flask application with routes
├── models.py                       # SQLAlchemy database models
├── forms.py                        # WTForms (registration, login, password reset)
├── config.py                       # Color palette configuration
├── requirements.txt                # Python dependencies
├── vercel.json                     # Vercel deployment config
├── .env.example                    # Environment variables template
├── PROJECT_MEMORY.md              # Detailed project documentation
├── instance/
│   └── bup_blood_bank.db          # SQLite database (local development)
├── migrations/                     # Flask-Migrate database migrations
├── static/
│   ├── css/                       # Tailwind CSS (compiled)
│   └── images/                    # User profile images (local)
├── templates/
│   ├── base.html                  # Base template with navigation
│   ├── home.html                  # Homepage with donor search
│   ├── register.html              # User registration form
│   ├── user_login.html            # User login form
│   ├── dashboard.html             # User dashboard
│   ├── forgot_password.html       # Password reset - identity verification
│   ├── verify_email.html          # Password reset - email confirmation
│   ├── reset_password.html        # Password reset - new password entry
│   ├── change_password.html       # Change password (logged in users)
│   ├── admin_panel.html           # Admin approval panel
│   └── [other templates]
└── utils/
    └── color_palettes.json        # UI color scheme
```

## 🚀 Local Development Setup

### 1. Clone and Setup Environment

```bash
# Navigate to project directory
cd f:\BloodBank

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Node Dependencies (for CSS)

```bash
npm install
```

### 3. Build Tailwind CSS (optional, already compiled)

```bash
npm run build
```

### 4. Database Setup

```bash
# Run migrations (if needed)
flask db upgrade

# Database will be created at instance/bup_blood_bank.db
```

### 5. Run the Application

**Development Mode:**
```bash
python app.py
# or
flask run --host=0.0.0.0 --port=5000
```

**Production Mode (local):**
```bash
gunicorn app:app -b 0.0.0.0:8086 --workers=4
```

### Access Points
- **Homepage:** http://localhost:5000
- **User Login:** http://localhost:5000/user/login
- **User Register:** http://localhost:5000/register
- **User Dashboard:** http://localhost:5000/dashboard
- **Admin Login:** http://localhost:5000/login
- **Admin Panel:** http://localhost:5000/admin

## 👨‍💼 Admin Access

- **URL:** `/admin` or `/login`
- **Username:** `admin`
- **Password:** `adminpassword`

> ⚠️ **IMPORTANT:** Change these credentials before production deployment!

## 🗄️ Database Schema

### User Model
- `id` - Primary key
- `student_id` - Unique identifier (username)
- `name` - Full name
- `department` - Department name
- `batch` - Batch year/number
- `blood_group` - Blood type (A+, A-, B+, B-, AB+, AB-, O+, O-)
- `mobile` - Contact number
- `address` - Residential address
- `email` - Email address (optional for legacy users)
- `image` - Profile picture URL (500 chars for Supabase)
- `password_hash` - Bcrypt hashed password (128 chars)
- `is_approved` - Admin approval status (Boolean)
- `is_available` - Donor availability (Boolean)
- `last_donation_date` - Last donation date (Date, nullable)
- `password_reset_count` - Tracks password reset without email (Integer)
- `created_at` - Registration timestamp (DateTime, Asia/Dhaka)

## 🌐 Production Deployment (Vercel + Supabase)

### Prerequisites
1. **Supabase Account** - Create project at [supabase.com](https://supabase.com)
2. **Vercel Account** - Sign up at [vercel.com](https://vercel.com)
3. **GitHub Repository** - Code must be in Git repo

### Step 1: Supabase Setup
```bash
# 1. Create new project on Supabase
# 2. Get Database connection string from Settings > Database
# 3. Create Storage bucket named 'images' (set to Public)
# 4. Copy Project URL and anon key from Settings > API
```

### Step 2: Environment Variables

Create `.env` file (NEVER commit this):
```env
SECRET_KEY=your-super-secret-key-here
SQLALCHEMY_DATABASE_URI=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT-REF].supabase.co
SUPABASE_KEY=[YOUR-ANON-KEY]
```

### Step 3: Vercel Deployment
1. Push code to GitHub
2. Import repository in Vercel
3. Add environment variables from `.env`
4. Deploy

## 🔒 Security Notes

### Files to NEVER Commit
- `temp_passwords.txt` - Contains all user passwords
- `.env` - Contains API keys and secrets
- `instance/bup_blood_bank.db` - Contains user data
- `venv/` - Virtual environment

### Recommended .gitignore
```gitignore
temp_passwords.txt
.env
instance/
venv/
__pycache__/
*.pyc
*.pyo
*.db
.DS_Store
node_modules/
```

## 📊 Current Statistics
- **Total Registered Users:** 500+
- **All users have secure passwords:** ✅ Yes
- **Email verification enabled:** ✅ Yes
- **Password reset available:** ✅ Yes (with email verification)

## 🐛 Known Issues / TODO

### High Priority
- [ ] Implement rate limiting for password reset attempts

### Medium Priority
- [ ] Add "Remember Me" option on login
- [ ] Improve error messages and user feedback
- [ ] Add donation history tracking

### Low Priority
- [ ] Add blood request system
- [ ] Add notification system for urgent requests
- [ ] Mobile app (React Native/Flutter)

## 📝 Change Log

### Version 3.4 - May 2026
- ✅ **Full Supabase Migration** - SQLite data and images moved to Supabase
- ✅ **Triple-Soft Architecture** - Soft-delete for users (hide/delete without data loss)
- ✅ **SweetAlert2 UI** - Enhanced confirmation dialogs and UI interactions
- ✅ **Admin Panel Upgrades** - Improved user management, filtering, and activity logs
- ✅ **Dynamic Availability** - Mathematical 120-day cooldown logic for donors
- ✅ **Official Program Integration** - Standardized BUP program hierarchy mapped for 500+ users
- ✅ **Email Notifications** - Added email notifications for password resets and registrations

### Version 2.0 - November 2024
- ✅ **User Authentication System** - Full login/logout with session management
- ✅ **Password Reset with Email Verification** - Multi-step secure reset process
- ✅ **BUP Program Integration** - Faculty and program-based filtering
- ✅ **Enhanced Security** - Limited one-time resets for users without email
- ✅ **Profile Management** - Dashboard for updating availability, images, contact info
- ✅ **Password Strength Indicator** - Visual feedback during password creation
- ✅ **Mobile-Responsive Navigation** - Auth state-aware mobile menu

### Version 1.0 - Initial Release
- Basic donor registration
- Blood group search
- Admin approval system

## 📞 Contact & Support

- **Admin Email:** refayat.connect@gmail.com
- **Project Type:** Humanitarian - Blood Donation Management
- **Institution:** Bangladesh University of Professionals (BUP)

## 📄 License

Internal use for BUP Blood Bank project.

---

**Last Updated:** May 2026  
**Version:** 3.4  
**Status:** Active Development
