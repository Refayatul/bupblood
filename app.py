from flask import Flask, render_template, redirect, url_for, request, flash, session,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from sqlalchemy import func, or_
from config import config
from models import db, User, Admin, Donation, PasswordResetToken, AdminLog
from forms import RegistrationForm, UserLoginForm, UpdateProfileForm, ChangePasswordForm, IdentityVerificationForm, ResetPasswordForm, VerifyEmailForm, DonationForm, CompleteProfileForm, RequestResetForm
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import json
from PIL import Image
from random import shuffle
import io
from datetime import datetime, date, timedelta, timezone
import secrets
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

# Official BUP Programs Data
PROGRAM_DATA = {
    'FASS': [
        # Undergraduate (10)
        'BSS (Hons) in Economics',
        'Bachelor of Social Science (Honours) in Sociology',
        'BSS (Hons) in Development Studies',
        'BSS (Hons) in Public Administration',
        'BA (Hons) in English',
        'BSS (Hons) in Disaster and Human Security Management',
        'Bachelor of Social Science in Disaster Management and Resilience',
        'Bachelor of Arts (Pass)',
        'Bachelor of Social Science (Pass)',
        'Bachelor of Social Science (Honours) in Political Science',
        'Modern Languages (CML)',
        # Graduate (9)
        'Masters in Disaster Management & Resilience',
        'Master of Social Science in Sociology',
        'Master of Development Studies (Professional)',
        'Master of Arts in English Language Teaching & Applied Linguistics',
        'Master of Public Administration',
        'Master of Development Studies',
        'Master of Arts in English Literature & Cultural Studies',
        'Master of Social Science in Economics',
        'Master of Social Science in Disaster and Human Security Management'
    ],
    'FSSS': [
        # Undergraduate (4)
        'BSS (Hons) in International Relations',
        'LLB (Hons) in Law',
        'BSS (Hons) in Mass Communication & Journalism',
        'Bachelor of Social Science in Peace, Conflict and Human Rights Studies',
        # Graduate (6)
        'Master of Social Science in Mass Communication and Journalism',
        'Master of Laws (LLM)',
        'Master of International Relations',
        'Master of Peace, Conflict and Human Rights Studies',
        'Master of Laws (LLM-Professional)',
        'Master of Peace and Human Rights Development Studies'
    ],
    'FST': [
        # Undergraduate (3)
        'B.Sc. in Computer Science and Engineering',
        'B.Sc. in Information and Communication Engineering',
        'B.Sc. (Hons.) in Environmental Science (BES)',
        # Graduate (8)
        'Masters in Computer Science and Engineering (MCSE)',
        'M.Sc. in Environmental Science (MES)',
        'M.Sc. in Environmental Science and Management (MESM)',
        'Masters in Information and Communication Engineering (MICE)',
        'Master in Environmental Science',
        'Masters in Information and Communication Technology (MICT)',
        'Masters in Information Systems Security (MISS)',
        'Masters in Cyber Security'
    ],
    'FBS': [
        # Undergraduate (5)
        'BBA in Management Studies',
        'BBA in Marketing',
        'BBA in Accounting and Information Systems',
        'BBA in Finance & Banking',
        'Bachelor of Business Administration (BBA)',
        # Graduate (6)
        'MBA in Marketing',
        'MBA in Finance and Banking',
        'MBA in Accounting and Information Systems',
        'MBA in Human Resource Management',
        'Master of Business Administration (Professional)',
        'Master of Business Administration'
    ],
    'FMS': [
        # Undergraduate (1)
        'Bachelor of Pharmacy',
        # Graduate (2)
        'Master of Public Health',
        'Certificate Course in Hospital Management'
    ]
}



app = Flask(__name__)

# Initialize Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

from flask_migrate import Migrate

migrate = Migrate(app, db)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret-key')
database_uri = os.environ.get('SQLALCHEMY_DATABASE_URI')
if not database_uri:
    # Fallback to sqlite if no DB URI is set (local dev default)
    database_uri = 'sqlite:///bup_blood_bank.db'

# Handle Vercel Postgres URL format if present (just in case user uses Vercel Postgres + Supabase Storage, but mostly for Supabase DB)
if database_uri and database_uri.startswith("postgres://"):
    database_uri = database_uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

# Configure URL generation for Vercel deployment
if os.environ.get('VERCEL_ENV') or os.environ.get('VERCEL_URL'):
    app.config['SERVER_NAME'] = 'bupblood.vercel.app'
    app.config['PREFERRED_URL_SCHEME'] = 'https'
else:
    # Local development
    app.config['SERVER_NAME'] = '127.0.0.1:5000'
    app.config['PREFERRED_URL_SCHEME'] = 'http'

# Setup ProxyFix middleware for handling reverse proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'user_login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

# Initialize Flask-Mail
mail = Mail(app)

# Initialize URLSafeTimedSerializer for tokens
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Supabase configuration (lazy initialization)
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
_supabase_client = None

def get_supabase_client():
    """Lazy initialization of Supabase client to avoid import-time crashes"""
    global _supabase_client
    if _supabase_client is None and supabase_url and supabase_key:
        try:
            _supabase_client = create_client(supabase_url, supabase_key)
        except Exception as e:
            print(f"Warning: Could not initialize Supabase client: {e}")
            _supabase_client = False  # Mark as failed
    return _supabase_client if _supabase_client is not False else None

@app.context_processor
def inject_now():
    from datetime import datetime, timezone
    return {'now': datetime.now(timezone.utc)}

def mask_email(email):
    """Mask email address: arifbangla@gmail.com -> ar**a@g*.com"""
    if not email or '@' not in email:
        return None
    
    local, domain = email.split('@')
    domain_parts = domain.split('.')
    
    # Mask local part: show first 2 chars + ** + last char
    if len(local) <= 3:
        masked_local = local[0] + '**'
    else:
        masked_local = local[:2] + '**' + local[-1]
    
    # Mask domain: show first char + * + .extension
    masked_domain = domain_parts[0][0] + '*'
    if len(domain_parts) > 1:
        masked_domain += '.' + domain_parts[-1]
    
    return f"{masked_local}@{masked_domain}"

def send_welcome_email(user):
    """Send welcome email to new user with email verification link"""
    try:
        # Generate email verification token (valid for 24 hours)
        token = serializer.dumps(user.email, salt='email-confirm')
        verify_url = url_for('verify_email_address', token=token, _external=True)

        html = f"""
        <html>
        <body>
            <h2>Welcome to BUP Blood Bank, {user.name}!</h2>
            <p>Thank you for registering with the University of Professionals Bangladesh Blood Bank system.</p>

            <h3>Next Steps:</h3>
            <ol>
                <li><strong>Verify Your Email:</strong> Click the link below to verify your email address</li>
                <li><strong>Admin Approval:</strong> After email verification, your account will need admin approval before you can login</li>
                <li><strong>Check Your Inbox:</strong> You will receive another email once your account is approved</li>
            </ol>

            <p><strong>Verify Your Email:</strong></p>
            <p><a href="{verify_url}">Verify Email Address</a></p>

            <p><strong>Your Account Details:</strong></p>
            <ul>
                <li>Student ID: <strong>{user.student_id}</strong></li>
                <li>Name: <strong>{user.name}</strong></li>
                <li>Email: <strong>{user.email}</strong></li>
                <li>Blood Group: <strong>{user.blood_group}</strong></li>
                <li>Department: <strong>{user.department}</strong></li>
                <li>Batch: <strong>{user.batch}</strong></li>
                <li>Mobile: <strong>{user.mobile}</strong></li>
                <li>Address: <strong>{user.address}</strong></li>
                {"<li>Date of Birth: <strong>" + user.date_of_birth.strftime('%B %d, %Y') + "</strong></li>" if user.date_of_birth else ""}
                <li>Registration Date: <strong>{user.created_at.strftime('%B %d, %Y at %I:%M %p')}</strong></li>
            </ul>

            <p><em>Note: Account approval may take some time depending on our admin team's availability.</em></p>

            <p>If you did not register for this account, please ignore this email.</p>

            <br>
            <p>Best regards,<br>BUP Blood Bank Team</p>
        </body>
        </html>
        """

        msg = Message(
            subject="Welcome to BUP Blood Bank - Verify Your Email",
            recipients=[user.email],
            html=html
        )

        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

def send_password_reset_email(user, reset_url):
    """Send password reset email with secure link"""
    try:
        html = f"""
        <html>
        <body>
            <h2>Password Reset Request</h2>
            <p>Hello {user.name},</p>

            <p>You requested a password reset for your BUP Blood Bank account.</p>
            <p>Click the link below to reset your password:</p>

            <p><a href="{reset_url}">Reset Your Password</a></p>

            <p><strong>This link will expire in 1 hour.</strong></p>
            <p>If you did not request this reset, please ignore this email.</p>

            <p>Student ID: {user.student_id}</p>

            <br>
            <p>For security reasons, we recommend adding/changing your email in your profile after login.</p>
            <br>
            <p>Best regards,<br>BUP Blood Bank Team</p>
        </body>
        </html>
        """

        msg = Message(
            subject="BUP Blood Bank - Password Reset Request",
            recipients=[user.email],
            html=html
        )

        mail.send(msg)
        return True
    except Exception as e:
        print(f"Password reset email error: {e}")
        return False

def send_admin_registration_notification(user):
    """Send email notification to admin about new user registration"""
    try:
        # Get admin email from environment or use a default
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@bup.edu.bd')

        # Generate admin panel URL
        admin_url = url_for('login', _external=True)  # Link to admin login

        html = f"""
        <html>
        <body>
            <h2>New User Registration Notification</h2>
            <p>A new user has registered for the BUP Blood Bank system and requires approval.</p>

            <h3>User Details:</h3>
            <ul>
                <li><strong>Name:</strong> {user.name}</li>
                <li><strong>Student ID:</strong> {user.student_id}</li>
                <li><strong>Email:</strong> {user.email}</li>
                <li><strong>Mobile:</strong> {user.mobile}</li>
                <li><strong>Blood Group:</strong> {user.blood_group}</li>
                <li><strong>Department:</strong> {user.department}</li>
                <li><strong>Batch:</strong> {user.batch}</li>
                <li><strong>Address:</strong> {user.address}</li>
                <li><strong>Registration Date:</strong> {user.created_at.strftime('%B %d, %Y at %I:%M %p')}</li>
            </ul>

            <p><strong>Action Required:</strong> Please log in to the admin panel to approve or reject this registration.</p>
            <p><a href="{admin_url}">Go to Admin Panel</a></p>

            <p><strong>Login Credentials:</strong><br>
            Username: {os.environ.get('ADMIN_USERNAME', 'admin')}<br>
            Password: {os.environ.get('ADMIN_PASSWORD', 'adminpassword')}</p>

            <br>
            <p>Best regards,<br>BUP Blood Bank System</p>
        </body>
        </html>
        """

        msg = Message(
            subject="BUP Blood Bank - New User Registration Requires Approval",
            recipients=[admin_email],
            html=html
        )

        mail.send(msg)
        return True
    except Exception as e:
        print(f"Admin notification email error: {e}")
        return False

def send_user_approval_email(user):
    """Send email notification to user about account approval"""
    try:
        # Generate login URL
        login_url = url_for('user_login', _external=True)

        html = f"""
        <html>
        <body>
            <h2>🎉 Account Approved! Welcome to BUP Blood Bank</h2>
            <p>Congratulations, {user.name}! Your account has been approved by our administrators.</p>

            <p>You can now log in to your account and start using all the features of the BUP Blood Bank system.</p>

            <p><strong>Login Details:</strong></p>
            <ul>
                <li><strong>Student ID:</strong> {user.student_id}</li>
                <li><strong>Email:</strong> {user.email}</li>
            </ul>

            <p><a href="{login_url}">Click here to Login</a></p>

            <p>We encourage you to:</p>
            <ul>
                <li>Update your profile information</li>
                <li>Complete your donor profile</li>
                <li>Explore available donation opportunities</li>
            </ul>

            <p>Thank you for joining our community of life-saving donors!</p>

            <br>
            <p>Best regards,<br>BUP Blood Bank Team</p>
        </body>
        </html>
        """

        msg = Message(
            subject="BUP Blood Bank - Your Account Has Been Approved!",
            recipients=[user.email],
            html=html
        )

        mail.send(msg)
        return True
    except Exception as e:
        print(f"User approval email error: {e}")
        return False

def send_user_change_request_email(user, change_reason, admin_name="Admin"):
    """Send email to user requesting profile changes"""
    try:
        # Check if user is approved - determines what instructions to show
        is_pending = not user.is_approved
        
        # Generate appropriate URLs
        profile_url = url_for('user_profile', _external=True)
        register_url = url_for('register', _external=True)
        contact_url = url_for('contact_admin', _external=True) if 'contact_admin' in app.view_functions else None

        # Different messaging for pending vs approved users
        if is_pending:
            action_section = f"""
            <p><strong>⚠️ Important:</strong> Since your account is still pending approval, you cannot log in yet to make changes.</p>
            
            <p><strong>To update your information, please:</strong></p>
            <ol>
                <li>Reply to this email with the corrected information, OR</li>
                <li><a href="{register_url}">Re-register</a> with the correct details (your previous registration will be removed)</li>
            </ol>
            
            <p>Once you've provided the correct information, we will process your registration.</p>
            """
        else:
            action_section = f"""
            <p>Please log in to your account and update the requested information as soon as possible.</p>

            <p><strong>Login Details:</strong></p>
            <ul>
                <li><strong>Student ID:</strong> {user.student_id}</li>
                <li><strong>Email:</strong> {user.email}</li>
            </ul>

            <p><a href="{profile_url}">Go to My Profile</a></p>
            """

        html = f"""
        <html>
        <body>
            <h2>📝 Profile Update Request - BUP Blood Bank</h2>
            <p>Hello {user.name},</p>

            <p>Our administrative team has requested that you update certain information in your {'registration' if is_pending else 'profile'}.</p>

            <h3>Requested Changes:</h3>
            <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                {change_reason.replace(chr(10), '<br>')}
            </div>

            {action_section}

            <p>If you have any questions about these changes or need assistance, please contact us.</p>

            <p><strong>Note:</strong> This request was sent by <em>{admin_name}</em></p>

            <br>
            <p>Best regards,<br>BUP Blood Bank Team</p>
        </body>
        </html>
        """

        msg = Message(
            subject="BUP Blood Bank - Profile Update Request",
            recipients=[user.email],
            html=html
        )

        mail.send(msg)
        return True
    except Exception as e:
        print(f"User change request email error: {e}")
        return False

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Tables are already created in Supabase via migrations
# No need to call db.create_all() on production



# Home route with donor search and latest users with pagination
@app.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    # --- DYNAMIC AVAILABILITY LOGIC ---
    # We only show donors who are approved, not archived/deleted, and medically eligible (120 days)
    today = date.today()
    cooldown_date = today - timedelta(days=120)
    
    results = User.query.filter_by(
        is_approved=True, 
        is_archived=False, 
        is_deleted=False,
        is_available=True # Explicitly available
    ).filter(
        or_(
            User.last_donation_date.is_(None),  # Never donated
            User.last_donation_date <= cooldown_date # Medically eligible
        )
    ).order_by(User.id.desc()).paginate(page=page, per_page=21)



    
    # Shuffle the results on each request
    items = list(results.items)  # Convert items to a list
    shuffle(items)
    results.items = items  # Replace the paginated items with the shuffled ones

    # --- Live Stats Calculation ---
    total_donors = User.query.filter_by(is_approved=True, is_deleted=False).count()

    # Blood Group Distribution
    blood_group_stats = db.session.query(User.blood_group, func.count(User.id)).filter_by(is_approved=True, is_deleted=False).group_by(User.blood_group).all()
    # Ensure all groups are present even if 0
    all_bg = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    bg_data_map = {bg: count for bg, count in blood_group_stats}
    blood_group_data = {bg: bg_data_map.get(bg, 0) for bg in all_bg}

    # Faculty Distribution (Map Program -> Faculty)
    # Fetch all approved departments (which store Program names)
    programs_list = db.session.query(User.department).filter_by(is_approved=True, is_deleted=False).all()
    
    faculty_counts = {k: 0 for k in PROGRAM_DATA.keys()}
    
    # Create a reverse map for faster lookup: {'BSc in CSE': 'FST', ...}
    program_to_faculty = {}
    for faculty, programs in PROGRAM_DATA.items():
        for prog in programs:
            program_to_faculty[prog] = faculty
            
    for (prog_name,) in programs_list:
        if not prog_name:
            continue
            
        # 1. Map any dirty/legacy department name to official program name
        official_prog = map_department_to_program(prog_name)
            
        # 2. Look up Faculty for the official program
        fac = program_to_faculty.get(official_prog)
        
        # 3. Fallback: maybe the department field is actually the faculty code itself (legacy data)
        if not fac:
            if prog_name in PROGRAM_DATA:
                fac = prog_name
        
        if fac:
            faculty_counts[fac] += 1
            
    stats = {
        'total_donors': total_donors,
        'blood_group_data': blood_group_data,
        'faculty_data': faculty_counts
    }
    
    return render_template('home.html', results=results, stats=stats, current_palette=config.current_palette)

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid input'}), 400

    # Get filter values
    blood_group = data.get('blood_group', '').strip()
    faculty = data.get('faculty', '').strip()
    program = data.get('program', '').strip()
    batch = data.get('batch', '').strip()
    available_only = data.get('available_only', False)
    page = request.args.get('page', 1, type=int)

    # Build query with filters
    query = User.query.filter_by(is_approved=True, is_archived=False, is_deleted=False)

    if blood_group:
        query = query.filter_by(blood_group=blood_group)

    if program:
        # Fuzzy matching using department mapping to handle legacy/dirty data
        conditions = [User.department == program]

        # Add fuzzy matches from department mapping
        if program in DEPARTMENT_MAPPING:
            for dirty_term in DEPARTMENT_MAPPING[program]:
                # Use ILIKE for case-insensitive partial matching
                conditions.append(User.department.ilike(f"%{dirty_term}%"))

        # Apply filter: (Exact Match OR Fuzzy Match 1 OR Fuzzy Match 2...)
        query = query.filter(or_(*conditions))

    elif faculty:
        # If no program selected but faculty is, match any program in that faculty
        if faculty in PROGRAM_DATA:
            valid_programs = PROGRAM_DATA[faculty]

            conditions = [User.department.in_(valid_programs)]

            # Add fuzzy matches for all dirty terms in programs within this faculty
            if faculty in PROGRAM_DATA:
                for official_program in PROGRAM_DATA[faculty]:
                    if official_program in DEPARTMENT_MAPPING:
                        for dirty_term in DEPARTMENT_MAPPING[official_program]:
                            conditions.append(User.department.ilike(f"%{dirty_term}%"))

            query = query.filter(or_(*conditions))

    if batch:
        query = query.filter_by(batch=batch)


    # --- DYNAMIC AVAILABILITY LOGIC ---
    # When 'Available Only' is checked, we don't just check the `is_available` flag.
    # We also mathematically verify they haven't donated in the last 120 days.
    # This ensures that even if a user forgot to set themselves to unavailable after 
    # donating, the system protects them (and the recipient) automatically.
    # To reverse this: simply remove the .filter(or_(...)) block and keep only .filter_by(is_available=True).
    if available_only:
        today = date.today()
        cooldown_date = today - timedelta(days=120)

        query = query.filter_by(is_available=True).filter(
            or_(
                User.last_donation_date.is_(None),
                User.last_donation_date <= cooldown_date
            )
        )




    # Prioritize available donors first when no availability filter is selected
    if not available_only:
        # When no availability filter: show available (True) first, then everything else (False/NULL)
        query = query.order_by(
            User.is_available.desc().nullslast(),  # True first, then False/NULL
            User.id.desc()  # Newest registration first within each group
        )
    else:
        # When availability filter is selected: prioritize explicitly confirmed available donors
        # Sort by availability status (True before others) then by donation readiness
        query = query.order_by(
            User.last_donation_date.is_(None).desc(),  # NULL values (never donated) first
            User.last_donation_date.asc(),  # Oldest donation date first (longest ago)
            User.id.desc()  # Newest registered first for same donation history
        )

    results = query.paginate(page=page, per_page=20)

    # For search results, keep the order by availability first (no shuffling)
    # This ensures available donors appear before unavailable ones

    # Render donor cards
    rendered_cards = [render_template('donor_card.html', user=user) for user in results.items]
    pagination = {
        'has_next': results.has_next,
        'next_num': results.next_num,
        'has_prev': results.has_prev,
        'prev_num': results.prev_num,
        'pages': results.pages,
        'current_page': results.page,
    }

    return jsonify({
        'cards': rendered_cards,
        'pagination': pagination,
        'total': results.total
    })


# Admin login route (hardcoded login)
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Load admin credentials from environment variables
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')

        if username == admin_username and password == admin_password:
            session['admin_logged_in'] = True
            flash("✅ Admin access granted. Welcome back!", "success")
            return redirect(url_for('admin_panel'))
        else:
            flash("❌ Invalid admin credentials. Please try again.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html', current_palette=config.current_palette)

# Admin panel for approval
@app.route('/admin', methods=['GET'])
def admin_panel():
    # Ensure admin is logged in
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("🚫 Access denied. Administrator privileges required.", "danger")
        return redirect(url_for('login'))

    pending_users = User.query.filter_by(is_approved=False, is_deleted=False).all()
    
    # Calculate statistics
    total_donors = User.query.filter_by(is_approved=True, is_deleted=False).count()
    total_pending = len(pending_users)
    
    # Count by blood group (approved donors only)
    blood_stats = db.session.query(
        User.blood_group, 
        func.count(User.id)
    ).filter_by(is_approved=True, is_deleted=False).group_by(User.blood_group).all()
    
    blood_counts = {bg: count for bg, count in blood_stats}
    
    blood_counts = {bg: count for bg, count in blood_stats}
    
    # Count available donors (approved AND is_available = True)
    available_donors = User.query.filter_by(is_approved=True, is_available=True, is_deleted=False).count()
    
    # Count hidden and deleted
    hidden_donors = User.query.filter_by(is_archived=True, is_deleted=False).count()
    deleted_accounts = User.query.filter_by(is_deleted=True).count()
    
    # Total Donations
    total_donations = Donation.query.count()
    
    # --- Calculate Faculty Stats for Admin (Same logic as Home) ---
    all_users = User.query.filter_by(is_approved=True, is_deleted=False).with_entities(User.department).all()
    faculty_counts = {fac: 0 for fac in PROGRAM_DATA.keys()} # Initialize with 0
    
    # Precompute mapping: program -> faculty
    program_to_faculty = {}
    for faculty, programs in PROGRAM_DATA.items():
        for prog in programs:
            program_to_faculty[prog] = faculty
            
    for user_row in all_users:
        prog_name = user_row.department
        if not prog_name:
            continue
            
        # 1. Map any dirty/legacy department name to official program name
        official_prog = map_department_to_program(prog_name)
            
        # 2. Look up Faculty for the official program
        fac = program_to_faculty.get(official_prog)
        
        # 3. Fallback: maybe the department field is actually the faculty code itself (legacy data)
        if not fac:
            if prog_name in PROGRAM_DATA:
                fac = prog_name
        
        if fac:
            faculty_counts[fac] += 1
            
    return render_template('admin_panel.html', 
                         users=pending_users, 
                         total_donors=total_donors,
                         total_pending=total_pending,
                         blood_counts=blood_counts,
                         available_donors=available_donors,
                         hidden_donors=hidden_donors,
                         deleted_accounts=deleted_accounts,
                         total_donations=total_donations,
                         faculty_counts=faculty_counts, # Pass faculty counts to template
                         current_palette=config.current_palette)

@app.route('/admin/filter/<filter_type>', methods=['GET'])
def admin_filter_users(filter_type):
    """Filter and display users/donations based on category clicked from stats"""
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('login'))
    
    # Get pagination and sorting parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    search_query = request.args.get('q', '').strip()
    
    # Advanced filter parameters
    blood_groups_select = request.args.getlist('blood_groups')  # Multi-select
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    def apply_advanced_filters(query):
        """Apply advanced filters (multi-blood groups, date range) to a user query"""
        nonlocal blood_groups_select, date_from, date_to
        
        # Multi-select blood groups
        if blood_groups_select:
            query = query.filter(User.blood_group.in_(blood_groups_select))
        
        # Date range filter on created_at
        if date_from:
            try:
                from datetime import datetime
                from_date = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(User.created_at >= from_date)
            except:
                pass
        
        if date_to:
            try:
                from datetime import datetime, timedelta
                to_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(User.created_at < to_date)
            except:
                pass
        
        return query
    
    # Valid sort columns for users
    valid_user_sorts = ['name', 'blood_group', 'department', 'batch', 'created_at', 'email', 'mobile', 'student_id']
    valid_donation_sorts = ['donation_date', 'location']
    
    # Filter based on type
    filter_title = ""
    filter_icon = ""
    filter_color = ""
    items = []
    is_donations = False
    blood_type_filter = None
    
    # Check if filter_type is a blood group (like 'A+', 'B-', etc.)
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    if filter_type in blood_groups:
        # Blood group filter
        blood_type_filter = filter_type
        query = User.query.filter_by(is_approved=True, blood_group=filter_type, is_deleted=False)
        
        # Apply search if provided
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
        
        # Apply sorting
        if sort_by in valid_user_sorts:
            sort_col = getattr(User, sort_by, User.created_at)
            if sort_order == 'asc':
                query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(User.created_at.desc())
            
        items = query.paginate(page=page, per_page=per_page, error_out=False)
        filter_title = f"Blood Group {filter_type} Donors"
        filter_icon = "fa-tint"
        filter_color = "red"
        
    elif filter_type == 'donors':
        # All approved donors
        query = User.query.filter_by(is_approved=True, is_deleted=False)
        
        # Apply search if provided
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
        
        # Apply sorting
        if sort_by in valid_user_sorts:
            sort_col = getattr(User, sort_by, User.created_at)
            if sort_order == 'asc':
                query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(User.created_at.desc())
        
        # Apply advanced filters
        query = apply_advanced_filters(query)
            
        items = query.paginate(page=page, per_page=per_page, error_out=False)
        filter_title = "All Approved Donors"
        filter_icon = "fa-users"
        filter_color = "blue"
        
    elif filter_type == 'available':
        # Available donors (approved + is_available=True)
        query = User.query.filter_by(is_approved=True, is_available=True, is_deleted=False)
        
        # Apply search if provided
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
        
        # Apply sorting
        if sort_by in valid_user_sorts:
            sort_col = getattr(User, sort_by, User.created_at)
            if sort_order == 'asc':
                query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(User.created_at.desc())
        
        # Apply advanced filters
        query = apply_advanced_filters(query)
            
        items = query.paginate(page=page, per_page=per_page, error_out=False)
        filter_title = "Available Donors"
        filter_icon = "fa-heartbeat"
        filter_color = "green"
        
    elif filter_type == 'pending':
        # Pending approvals
        query = User.query.filter_by(is_approved=False, is_deleted=False)
        
        # Apply search if provided
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
        
        # Apply sorting
        if sort_by in valid_user_sorts:
            sort_col = getattr(User, sort_by, User.created_at)
            if sort_order == 'asc':
                query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(User.created_at.desc())
            
        items = query.paginate(page=page, per_page=per_page, error_out=False)
        filter_title = "Pending Approvals"
        filter_icon = "fa-clock"
        filter_color = "orange"
        
    elif filter_type == 'hidden':
        # Hidden (Archived) Donors
        query = User.query.filter_by(is_archived=True, is_deleted=False)
        
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
            
        if sort_by in valid_user_sorts:
            sort_col = getattr(User, sort_by, User.created_at)
            if sort_order == 'asc':
                query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(User.created_at.desc())
            
        items = query.paginate(page=page, per_page=per_page, error_out=False)
        filter_title = "Hidden Accounts"
        filter_icon = "fa-eye-slash"
        filter_color = "gray"
        
    elif filter_type == 'deleted':
        # Deleted Accounts
        query = User.query.filter_by(is_deleted=True)
        
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
            
        if sort_by in valid_user_sorts:
            sort_col = getattr(User, sort_by, User.created_at)
            if sort_order == 'asc':
                query = query.order_by(sort_col.asc())
            else:
                query = query.order_by(sort_col.desc())
        else:
            query = query.order_by(User.deleted_at.desc())
            
        items = query.paginate(page=page, per_page=per_page, error_out=False)
        filter_title = "Deleted Accounts"
        filter_icon = "fa-trash"
        filter_color = "red"
        
    elif filter_type == 'donations':
        # Get filter parameters early for donations
        filter_blood_group = request.args.get('blood_group', '')
        filter_department = request.args.get('department', '')
        filter_batch = request.args.get('batch', '')
        filter_faculty = request.args.get('faculty', '')
        
        # All donations with user info
        query = db.session.query(Donation, User).join(User, Donation.user_id == User.id)
        
        # Apply blood group filter
        if filter_blood_group:
            query = query.filter(User.blood_group == filter_blood_group)
        
        # Apply faculty filter (match department starting pattern)
        if filter_faculty:
            faculty_prefixes = {
                'FST': ['BSc in', 'MSc in'],
                'FASS': ['BA in', 'MA in'],
                'FBS': ['BBA', 'MBA', 'Bachelor of Business', 'Master of Business'],
                'FSSS': ['BSS', 'MSS', 'Bachelor of Laws', 'Master of Laws', 'Master in Peace'],
                'FMS': ['MPH', 'Certificate in Hospital']
            }
            if filter_faculty in faculty_prefixes:
                from sqlalchemy import or_
                conditions = [User.department.ilike(f'{prefix}%') for prefix in faculty_prefixes[filter_faculty]]
                query = query.filter(or_(*conditions))
        
        # Apply department/program filter
        if filter_department:
            query = query.filter(User.department == filter_department)
        
        # Apply batch filter
        if filter_batch:
            query = query.filter(User.batch == filter_batch)
        
        # Apply search if provided (search by user name/student_id)
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%'))
            )
        
        # Apply sorting for donations
        if sort_by == 'donation_date':
            if sort_order == 'asc':
                query = query.order_by(Donation.donation_date.asc())
            else:
                query = query.order_by(Donation.donation_date.desc())
        elif sort_by == 'name':
            if sort_order == 'asc':
                query = query.order_by(User.name.asc())
            else:
                query = query.order_by(User.name.desc())
        elif sort_by == 'blood_group':
            if sort_order == 'asc':
                query = query.order_by(User.blood_group.asc())
            else:
                query = query.order_by(User.blood_group.desc())
        else:
            query = query.order_by(Donation.donation_date.desc())
            
        items = query.paginate(page=page, per_page=per_page, error_out=False)
        filter_title = "All Donations"
        filter_icon = "fa-hand-holding-heart"
        filter_color = "purple"
        is_donations = True
        
    else:
        flash("Invalid filter type.", "warning")
        return redirect(url_for('admin_panel'))
    
    # Get stats for the header
    total_donors = User.query.filter_by(is_approved=True, is_deleted=False).count()
    available_donors = User.query.filter_by(is_approved=True, is_available=True, is_deleted=False).count()
    total_pending = User.query.filter_by(is_approved=False, is_deleted=False).count()
    total_donations = Donation.query.count()
    hidden_donors = User.query.filter_by(is_archived=True, is_deleted=False).count()
    deleted_accounts = User.query.filter_by(is_deleted=True).count()
    
    # Get blood group counts for the filter dropdown
    blood_stats = db.session.query(
        User.blood_group, 
        func.count(User.id)
    ).filter_by(is_approved=True, is_deleted=False).group_by(User.blood_group).all()
    blood_counts = {bg: count for bg, count in blood_stats}
    
    # Get department counts for filter dropdown
    departments = db.session.query(
        User.department,
        func.count(User.id)
    ).filter(User.is_approved==True, User.department.isnot(None), User.department != '').group_by(User.department).order_by(func.count(User.id).desc()).all()
    
    # Get batch counts for filter dropdown
    batches = db.session.query(
        User.batch,
        func.count(User.id)
    ).filter(User.is_approved==True, User.batch.isnot(None)).group_by(User.batch).order_by(User.batch.desc()).all()
    
    # Apply additional filters from query parameters
    filter_blood_group = request.args.get('blood_group', '')
    filter_department = request.args.get('department', '')
    filter_batch = request.args.get('batch', '')
    filter_status = request.args.get('status', '')
    
    # Re-run query with additional filters — only for standard filter types
    # 'hidden' and 'deleted' already set their `items` above, skip them here
    SKIP_REFILTER = ['hidden', 'deleted', 'donations', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    if filter_type not in SKIP_REFILTER:
        # Build base query based on filter_type (with soft-delete awareness)
        if filter_type == 'donors':
            base_query = User.query.filter_by(is_approved=True, is_deleted=False, is_archived=False)
        elif filter_type == 'available':
            base_query = User.query.filter_by(is_approved=True, is_available=True, is_deleted=False, is_archived=False)
        elif filter_type == 'pending':
            base_query = User.query.filter_by(is_approved=False, is_deleted=False)
        else:
            base_query = User.query.filter_by(is_approved=True, is_deleted=False, is_archived=False)
        
        # Apply search
        if search_query:
            base_query = base_query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
        
        # Apply additional filters
        if filter_blood_group:
            base_query = base_query.filter(User.blood_group == filter_blood_group)
        if filter_department:
            base_query = base_query.filter(User.department == filter_department)
        if filter_batch:
            base_query = base_query.filter(User.batch == filter_batch)
        if filter_status == 'available':
            base_query = base_query.filter(User.is_available == True)
        elif filter_status == 'unavailable':
            base_query = base_query.filter(User.is_available == False)
        
        # Apply sorting
        if sort_by in valid_user_sorts:
            sort_col = getattr(User, sort_by, User.created_at)
            if sort_order == 'asc':
                base_query = base_query.order_by(sort_col.asc())
            else:
                base_query = base_query.order_by(sort_col.desc())
        else:
            base_query = base_query.order_by(User.created_at.desc())
        
        items = base_query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('admin_filter.html',
                         items=items,
                         filter_type=filter_type,
                         filter_title=filter_title,
                         filter_icon=filter_icon,
                         filter_color=filter_color,
                         is_donations=is_donations,
                         total_donors=total_donors,
                         available_donors=available_donors,
                         total_pending=total_pending,
                         total_donations=total_donations,
                         hidden_donors=hidden_donors,
                         deleted_accounts=deleted_accounts,
                         blood_counts=blood_counts,
                         blood_type_filter=blood_type_filter,
                         departments=departments,
                         batches=batches,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         search_query=search_query,
                         current_palette=config.current_palette)


@app.route('/admin/restore/<int:user_id>', methods=['POST'])
def admin_restore_user(user_id):
    """Restore a soft-deleted user account"""
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    user.is_deleted = False
    user.deleted_at = None
    user.deleted_by = None
    user.deletion_reason = None
    db.session.commit()
    log_admin_action('restore', user, 'Account restored from deleted')
    flash(f"Account for {user.name} has been restored successfully.", "success")
    return redirect(url_for('admin_filter_users', filter_type='deleted'))


@app.route('/admin/export-csv/<filter_type>')
def admin_export_csv(filter_type):
    """Export filtered user/donation list to CSV"""
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
    
    import csv
    from io import StringIO
    from flask import Response
    from datetime import datetime
    
    # Get filter parameters
    search_query = request.args.get('q', '')
    filter_blood_group = request.args.get('blood_group', '')
    filter_department = request.args.get('department', '')
    filter_batch = request.args.get('batch', '')
    filter_status = request.args.get('status', '')
    filter_faculty = request.args.get('faculty', '')
    
    output = StringIO()
    writer = csv.writer(output)
    
    if filter_type == 'donations':
        # Export donations
        query = db.session.query(Donation, User).join(User, Donation.user_id == User.id)
        
        if filter_blood_group:
            query = query.filter(User.blood_group == filter_blood_group)
        if filter_department:
            query = query.filter(User.department == filter_department)
        if filter_batch:
            query = query.filter(User.batch == filter_batch)
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%'))
            )
        
        query = query.order_by(Donation.donation_date.desc())
        donations = query.all()
        
        # Write CSV header
        writer.writerow(['Donor Name', 'Student ID', 'Blood Group', 'Department', 'Batch', 
                        'Donation Date', 'Location', 'Notes', 'Email', 'Mobile'])
        
        for donation, user in donations:
            writer.writerow([
                user.name,
                user.student_id,
                user.blood_group,
                user.department or '',
                user.batch or '',
                donation.donation_date.strftime('%Y-%m-%d') if donation.donation_date else '',
                donation.location or '',
                donation.notes or '',
                user.email or '',
                user.mobile or ''
            ])
        
        filename = f"donations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
    else:
        # Export users
        if filter_type == 'donors':
            query = User.query.filter_by(is_approved=True)
        elif filter_type == 'available':
            query = User.query.filter_by(is_approved=True, is_available=True)
        elif filter_type == 'pending':
            query = User.query.filter_by(is_approved=False)
        elif filter_type in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
            query = User.query.filter_by(is_approved=True, blood_group=filter_type)
        else:
            query = User.query.filter_by(is_approved=True)
        
        # Apply additional filters
        if filter_blood_group:
            query = query.filter(User.blood_group == filter_blood_group)
        if filter_department:
            query = query.filter(User.department == filter_department)
        if filter_batch:
            query = query.filter(User.batch == filter_batch)
        if filter_status == 'available':
            query = query.filter(User.is_available == True)
        elif filter_status == 'unavailable':
            query = query.filter(User.is_available == False)
        if search_query:
            query = query.filter(
                (User.name.ilike(f'%{search_query}%')) |
                (User.student_id.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%'))
            )
        
        users = query.order_by(User.created_at.desc()).all()
        
        # Write CSV header
        writer.writerow(['Name', 'Student ID', 'Blood Group', 'Department', 'Batch',
                        'Email', 'Mobile', 'Address', 'Available', 'Approved', 'Registered'])
        
        for user in users:
            writer.writerow([
                user.name,
                user.student_id,
                user.blood_group,
                user.department or '',
                user.batch or '',
                user.email or '',
                user.mobile or '',
                user.address or '',
                'Yes' if user.is_available else 'No',
                'Yes' if user.is_approved else 'No',
                user.created_at.strftime('%Y-%m-%d') if user.created_at else ''
            ])
        
        filename = f"{filter_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@app.route('/admin/donation-stats')
def admin_donation_stats():
    """API endpoint for donation statistics"""
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return {'error': 'Access denied'}, 403
    
    from datetime import datetime, timedelta
    from sqlalchemy import func, extract
    
    # Get monthly donations for last 6 months
    today = datetime.today()
    monthly_data = []
    for i in range(5, -1, -1):
        month_date = today - timedelta(days=i*30)
        month_name = month_date.strftime('%b')
        year = month_date.year
        month = month_date.month
        
        count = db.session.query(func.count(Donation.id)).filter(
            extract('year', Donation.donation_date) == year,
            extract('month', Donation.donation_date) == month
        ).scalar() or 0
        
        monthly_data.append({'month': month_name, 'count': count})
    
    # This month's donations
    this_month_count = db.session.query(func.count(Donation.id)).filter(
        extract('year', Donation.donation_date) == today.year,
        extract('month', Donation.donation_date) == today.month
    ).scalar() or 0
    
    # Top 5 donors
    top_donors = db.session.query(
        User.name,
        User.blood_group,
        func.count(Donation.id).label('donation_count')
    ).join(Donation, User.id == Donation.user_id).group_by(User.id).order_by(
        func.count(Donation.id).desc()
    ).limit(5).all()
    
    return {
        'monthly_data': monthly_data,
        'this_month': this_month_count,
        'top_donors': [
            {'name': d.name, 'blood_group': d.blood_group, 'count': d.donation_count}
            for d in top_donors
        ]
    }


def log_admin_action(action_type, target_user=None, details=None):
    """Helper function to log admin actions"""
    try:
        log = AdminLog(
            action_type=action_type,
            target_user_id=target_user.id if target_user else None,
            target_user_name=target_user.name if target_user else None,
            details=details,
            admin_username=session.get('admin_username', 'admin')
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Failed to log admin action: {e}")


@app.route('/admin/activity-log')
def admin_activity_log():
    """View admin action history/audit log"""
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
    
    page = request.args.get('page', 1, type=int)
    action_filter = request.args.get('action', '')
    
    query = AdminLog.query.order_by(AdminLog.created_at.desc())
    
    if action_filter:
        query = query.filter(AdminLog.action_type == action_filter)
    
    logs = query.paginate(page=page, per_page=50, error_out=False)
    
    # Get action types for filter dropdown
    action_types = db.session.query(AdminLog.action_type).distinct().all()
    action_types = [a[0] for a in action_types]
    
    return render_template('admin_activity_log.html',
                          logs=logs,
                          action_filter=action_filter,
                          action_types=action_types,
                          current_palette=config.current_palette)


@app.route('/admin/broadcast', methods=['POST'])
def admin_broadcast_email():
    """Send broadcast email to donors with optional filters"""
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
    
    broadcast_type = request.form.get('broadcast_type', 'available')
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    
    # Get filter parameters
    filter_blood_group = request.form.get('filter_blood_group', '')
    filter_faculty = request.form.get('filter_faculty', '')
    filter_batch = request.form.get('filter_batch', '')
    
    if not subject or not message:
        flash("⚠️ Both Subject and Message body are required.", "warning")
        return redirect(url_for('admin_panel'))
    
    # Build base query
    if broadcast_type == 'all':
        query = User.query.filter_by(is_approved=True).filter(User.email.isnot(None))
        target_desc = "all approved donors"
    elif broadcast_type == 'available':
        query = User.query.filter_by(is_approved=True, is_available=True).filter(User.email.isnot(None))
        target_desc = "available donors"
    else:
        flash("Invalid broadcast type.", "warning")
        return redirect(url_for('admin_panel'))
    
    # Apply additional filters
    filter_parts = []
    
    if filter_blood_group:
        query = query.filter(User.blood_group == filter_blood_group)
        filter_parts.append(f"Blood: {filter_blood_group}")
    
    if filter_faculty:
        faculty_prefixes = {
            'FST': ['BSc in', 'MSc in'],
            'FASS': ['BA in', 'MA in'],
            'FBS': ['BBA', 'MBA', 'Bachelor of Business', 'Master of Business'],
            'FSSS': ['BSS', 'MSS', 'Bachelor of Laws', 'Master of Laws'],
            'FMS': ['MPH', 'Certificate in Hospital']
        }
        if filter_faculty in faculty_prefixes:
            from sqlalchemy import or_
            conditions = [User.department.ilike(f'{prefix}%') for prefix in faculty_prefixes[filter_faculty]]
            query = query.filter(or_(*conditions))
            filter_parts.append(f"Faculty: {filter_faculty}")
    
    if filter_batch:
        query = query.filter(User.batch == filter_batch)
        filter_parts.append(f"Batch: {filter_batch}")
    
    if filter_parts:
        target_desc += f" ({', '.join(filter_parts)})"
    
    recipients = query.all()
    
    if not recipients:
        flash(f"No {target_desc} with email addresses found.", "info")
        return redirect(url_for('admin_panel'))
    
    success_count = 0
    error_count = 0
    
    for user in recipients:
        try:
            if not user.email:
                continue
                
            html = f"""
            <html>
            <body>
                <h2>📢 {subject}</h2>
                <p>Hello {user.name},</p>
                
                <div style="background-color: #f5f5f5; padding: 20px; border-left: 4px solid #3b82f6; margin: 20px 0;">
                    {message.replace(chr(10), '<br>')}
                </div>
                
                <p>Thank you for being part of the BUP Blood Bank community!</p>
                
                <br>
                <p>Best regards,<br>BUP Blood Bank Team</p>
            </body>
            </html>
            """
            
            msg = Message(
                subject=f"BUP Blood Bank - {subject}",
                recipients=[user.email],
                html=html
            )
            
            mail.send(msg)
            success_count += 1
        except Exception as e:
            print(f"Failed to send to {user.email}: {e}")
            error_count += 1
    
    if success_count > 0:
        flash(f"Broadcast sent to {success_count} {target_desc}.", "success")
        log_admin_action('broadcast', None, f"Sent to {success_count} recipients ({target_desc}): {subject[:50]}")
    if error_count > 0:
        flash(f"Failed to send to {error_count} recipients.", "warning")
    
    return redirect(url_for('admin_panel'))


@app.route('/admin/quick-toggle-availability/<int:user_id>', methods=['POST'])
def admin_toggle_availability(user_id):
    """Quick action to toggle user archive/hidden status"""
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return {'success': False, 'error': 'Access denied'}, 403
    
    user = User.query.get_or_404(user_id)
    user.is_archived = not user.is_archived
    
    from datetime import datetime
    if user.is_archived:
        user.archived_at = datetime.utcnow()
        user.archived_by = session.get('admin_username', 'admin')
    else:
        user.archived_at = None
        user.archived_by = None
    
    try:
        db.session.commit()
        log_admin_action('toggle_archive', user, f"Profile {'Hidden' if user.is_archived else 'Visible'}")
        return {
            'success': True, 
            'is_archived': user.is_archived,
            'message': f"{user.name} is now {'Hidden' if user.is_archived else 'Visible'}"
        }
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}, 500


@app.route('/admin/quick-approve/<int:user_id>', methods=['POST'])
def admin_quick_approve(user_id):
    """Quick action to approve a pending user"""
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        return {'success': False, 'error': 'Access denied'}, 403
    
    user = User.query.get_or_404(user_id)
    
    if user.is_approved:
        return {'success': False, 'error': 'User already approved'}, 400
    
    user.is_approved = True
    
    try:
        db.session.commit()
        # Try to send approval email
        try:
            send_user_approval_email(user)
        except:
            pass  # Email failure shouldn't break the approval
        
        log_admin_action('approve', user, 'Quick approved from filter page')
        
        return {
            'success': True,
            'message': f"{user.name} has been approved!"
        }
    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': str(e)}, 500


@app.route('/admin/edit-user/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    """Admin route to edit any user's information"""
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        try:
            # Update user fields
            user.name = request.form.get('name', user.name).strip()
            user.email = request.form.get('email', user.email).strip() if request.form.get('email') else user.email
            user.student_id = request.form.get('student_id', user.student_id).strip()
            user.blood_group = request.form.get('blood_group', user.blood_group)
            user.department = request.form.get('department', user.department)
            user.batch = request.form.get('batch', user.batch)
            user.mobile = request.form.get('mobile', user.mobile)
            user.address = request.form.get('address', user.address)
            user.date_of_birth = request.form.get('date_of_birth', user.date_of_birth) if request.form.get('date_of_birth') else user.date_of_birth
            
            # Toggle fields (convert string values to booleans)
            user.is_available = request.form.get('is_available', 'false') == 'true'
            user.is_approved = request.form.get('is_approved', 'false') == 'true'
            
            db.session.commit()
            log_admin_action('edit', user, 'Profile updated by admin')
            flash(f"✅ User '{user.name}' updated successfully!", "success")
            return redirect(request.args.get('next') or url_for('admin_panel'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Error updating user: {e}", "danger")
    
    # Get faculty/program data for dropdowns
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    
    return render_template('admin_edit_user.html',
                         user=user,
                         blood_groups=blood_groups,
                         current_palette=config.current_palette)

@app.route('/admin/bulk-reset-availability', methods=['POST'])
def admin_bulk_reset():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
        
    try:
        # Set all users to unavailable
        User.query.update({User.is_available: False})
        db.session.commit()
        flash("✅ All users marked as 'Not Available'.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error resetting availability: {e}", "danger")
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/cleanup-stale', methods=['POST'])
def admin_cleanup_stale():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
        
    try:
        # Delete pending users created more than 7 days ago
        seven_days_ago = datetime.now() - timedelta(days=7)
        stale_users = User.query.filter(User.is_approved==False, User.created_at < seven_days_ago).all()
        count = len(stale_users)
        
        for user in stale_users:
            user.is_deleted = True
            user.deleted_at = datetime.now()
            user.deleted_by = 'system'
            user.deletion_reason = 'Cleanup stale request'
            
        db.session.commit()
        flash(f"Cleanup complete. Removed {count} stale registration requests.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error cleaning stale users: {e}", "danger")
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject-all-pending', methods=['POST'])
def admin_reject_all_pending():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
        
    try:
        # Delete ALL pending users
        pending_users = User.query.filter_by(is_approved=False).all()
        count = len(pending_users)
        
        for user in pending_users:
            user.is_deleted = True
            user.deleted_at = datetime.now()
            user.deleted_by = session.get('admin_username', 'admin')
            user.deletion_reason = 'Bulk rejection'
            
        db.session.commit()
        flash(f"Bulk action complete. Rejected {count} pending requests.", "warning")
    except Exception as e:
        db.session.rollback()
        flash(f"Error rejecting all: {e}", "danger")
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/approve-all-pending', methods=['POST'])
def admin_approve_all_pending():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
        
    try:
        # Approve ALL pending users
        pending_users = User.query.filter_by(is_approved=False).all()
        count = len(pending_users)
        
        for user in pending_users:
            user.is_approved = True
            # Optional: Send emails (might be slow for many users, keeping it simple for now)
            try:
                send_user_approval_email(user)
            except:
                pass # Don't fail transaction if email fails
            
        db.session.commit()
        flash(f"✅ Bulk action complete. Approved {count} new donors.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error approving all: {e}", "danger")
        
    return redirect(url_for('admin_panel'))

@app.route('/admin/export-data')
def admin_export_data():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
        
    try:
        # Re-use existing backup logic dynamically
        from backup_data import DateTimeEncoder
        
        users = User.query.all()
        donations = Donation.query.all()
        
        data = {
            'users': [u.to_dict() for u in users],
            'donations': [d.to_dict() for d in donations],
            'export_date': datetime.now().isoformat()
        }
        
        #Create in-memory file
        import io
        mem_file = io.BytesIO()
        mem_file.write(json.dumps(data, cls=DateTimeEncoder, indent=2).encode('utf-8'))
        mem_file.seek(0)
        
        return flask.send_file(
            mem_file,
            as_attachment=True,
            download_name=f'bloodbank_export_{datetime.now().strftime("%Y%m%d_%H%M")}.json',
            mimetype='application/json'
        )
    except Exception as e:
        flash(f"Export failed: {e}", "danger")
        return redirect(url_for('admin_panel'))

# Admin approve/reject routes
@app.route('/admin/approve/<int:user_id>', methods=['POST'])
def approve_user(user_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()

        # Send approval email to user
        send_user_approval_email(user)
        flash(f"✅ User {user.name} has been approved and notified.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject/<int:user_id>', methods=['POST'])
def reject_user(user_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        user.is_deleted = True
        user.deleted_at = datetime.now()
        user.deleted_by = session.get('admin_username', 'admin')
        user.deletion_reason = 'Rejected registration'
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/search', methods=['GET'])
def admin_search():
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))
        
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('admin_panel'))
        
    # Search by Name, Student ID, or Mobile
    users = User.query.filter(
        User.is_deleted == False,
        (
            (User.name.ilike(f'%{query}%')) |
            (User.student_id.ilike(f'%{query}%')) |
            # Handle comma-separated mobile search
            (db.func.concat(',', User.mobile, ',').like(f'%,{query},%') |
             db.func.concat(',', User.mobile, ',').like(f'%,{query}%') |
             db.func.concat(',', User.mobile, ',').like(f'%{query},%'))
        )
    ).all()
    
    # Reuse admin_panel logic for stats
    pending_users = User.query.filter_by(is_approved=False, is_deleted=False).all()
    total_donors = User.query.filter_by(is_approved=True, is_deleted=False).count()
    total_pending = len(pending_users)
    available_donors = User.query.filter_by(is_approved=True, is_available=True, is_deleted=False).count()
    hidden_donors = User.query.filter_by(is_archived=True, is_deleted=False).count()
    deleted_accounts = User.query.filter_by(is_deleted=True).count()
    total_donations = Donation.query.count()
    
    blood_stats = db.session.query(
        User.blood_group, 
        func.count(User.id)
    ).filter_by(is_approved=True, is_deleted=False).group_by(User.blood_group).all()
    blood_counts = {bg: count for bg, count in blood_stats}

    # Faculty Stats (Python-based to support Department -> Faculty mapping)
    all_users = User.query.filter_by(is_approved=True, is_deleted=False).with_entities(User.department).all()
    faculty_counts = {fac: 0 for fac in PROGRAM_DATA.keys()} # Initialize with 0
    
    # Precompute mapping: program -> faculty
    program_to_faculty = {}
    for faculty, programs in PROGRAM_DATA.items():
        for prog in programs:
            program_to_faculty[prog] = faculty
            
    for user_row in all_users:
        prog_name = user_row.department
        if not prog_name:
            continue
            
        # 1. Map any dirty/legacy department name to official program name
        official_prog = map_department_to_program(prog_name)
            
        # 2. Look up Faculty for the official program
        fac = program_to_faculty.get(official_prog)
        
        # 3. Fallback: maybe the department field is actually the faculty code itself (legacy data)
        if not fac:
            if prog_name in PROGRAM_DATA:
                fac = prog_name
        
        if fac:
            faculty_counts[fac] += 1
    
    # Note: Monthly stats removed as they caused DB dialect issues and aren't used in the template currently
    
    return render_template('admin_panel.html', 
                         users=pending_users,
                         search_results=users,
                         search_query=query,
                         total_donors=total_donors,
                         total_pending=total_pending,
                         blood_counts=blood_counts,
                         faculty_counts=faculty_counts,
                         available_donors=available_donors,
                         hidden_donors=hidden_donors,
                         deleted_accounts=deleted_accounts,
                         total_donations=total_donations, # Use Total Donations
                         current_palette=config.current_palette)

@app.route('/admin/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)
    try:
        # Attempt to delete the user's image from Supabase storage
        supabase = get_supabase_client()
        if supabase:
            try:
                supabase.storage.from_("images").remove([f"{user.student_id}.jpg"])
            except Exception as e:
                print(f"Warning: Could not delete image for user {user.student_id} from Supabase: {e}")

        user.is_deleted = True
        user.deleted_at = datetime.now()
        user.deleted_by = session.get('admin_username', 'admin')
        user.deletion_reason = 'Admin deleted via panel'
        
        db.session.commit()
        log_admin_action('delete', user, f"Soft deleted account")
        flash(f"User {user.name} deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting user: {e}", "danger")

    return redirect(url_for('admin_panel'))

@app.route('/admin/send-change-request/<int:user_id>', methods=['GET', 'POST'])
def admin_send_change_request(user_id):
    if 'admin_logged_in' not in session or not session['admin_logged_in']:
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        change_reason = request.form.get('change_reason', '').strip()
        admin_name = request.form.get('admin_name', 'System Admin').strip()

        if not change_reason:
            flash("Please provide a reason for the requested changes.", "warning")
        else:
            # Send email to user
            if send_user_change_request_email(user, change_reason, admin_name):
                flash(f"Change request sent to {user.name} via email.", "success")
            else:
                flash("Failed to send email. Please try again.", "danger")

        return redirect(url_for('admin_panel'))

    # GET request - show form
    return render_template('send_change_request.html', user=user, current_palette=config.current_palette)

# Logout route
@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))
# Registration route
@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("100 per hour")
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        student_id = form.student_id.data

        # Check if student_id already exists in the database
        existing_user = User.query.filter_by(student_id=student_id).first()
        if existing_user:
            flash("⚠️ An account already exists with this Student ID. Please login or reset your password.", "warning")
            return redirect(url_for('user_login'))
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash("⚠️ An account already exists with this email address.", "warning")
            return render_template('register.html', form=form, program_data=PROGRAM_DATA, current_palette=config.current_palette)

        # Check if any mobile number already exists
        entered_mobiles = []
        for i in range(1, 4):  # mobile1, mobile2, mobile3
            mobile_value = getattr(form, f'mobile{i}').data
            if mobile_value and mobile_value.strip():
                entered_mobiles.append(mobile_value.strip())

        for mobile in entered_mobiles:
            existing_mobile = db.session.query(User).filter(
                db.func.concat(',', User.mobile, ',').ilike(f'%,{mobile},%') |
                db.func.concat(',', User.mobile, ',').ilike(f'{mobile},%') |
                db.func.concat(',', User.mobile, ',').ilike(f'%,{mobile}') |
                db.func.concat(',', User.mobile, ',').ilike(f'{mobile}')
            ).first()
            if existing_mobile:
                flash(f"⚠️ An account already exists with the mobile number {mobile}.", "warning")
                return render_template('register.html', form=form, program_data=PROGRAM_DATA, current_palette=config.current_palette)

        # Combine mobiles into comma-separated string
        mobile_combined = ','.join(entered_mobiles)

        if form.password.data != form.confirm_password.data:
            flash("❌ Passwords do not match. Please try again.", "danger")
            return render_template('register.html', form=form, current_palette=config.current_palette)

        name = form.name.data
        faculty = form.faculty.data
        program_key = form.program.data

        # Validate that the program belongs to the selected faculty
        if faculty not in PROGRAM_DATA:
            flash("❌ Invalid faculty selected.", "danger")
            return render_template('register.html', form=form, current_palette=config.current_palette)

        faculty_programs = PROGRAM_DATA[faculty]
        if program_key not in faculty_programs:
            flash("❌ Invalid program selected for the chosen faculty.", "danger")
            return render_template('register.html', form=form, current_palette=config.current_palette)

        # Use the program name as department
        department = program_key
        batch = form.batch.data
        blood_group = form.blood_group.data
        address = form.address.data
        image_file = form.image.data

        image_url = ""
        
        # Upload to Supabase
        try:
            supabase = get_supabase_client()
            if supabase:
                image_filename = f"{student_id}.jpg"
                
                # Backend validation for image size (2MB limit)
                image_file.seek(0, os.SEEK_END)
                file_size = image_file.tell()
                image_file.seek(0) # Reset cursor
                
                if file_size > 2 * 1024 * 1024:
                    flash("Image size exceeds 2MB limit. Please choose a smaller image.", "danger")
                    return render_template('register.html', form=form, current_palette=config.current_palette)

                # Compress image in memory
                img = Image.open(image_file)
                img = img.convert('RGB')
                img_io = io.BytesIO()
                img.save(img_io, 'JPEG', optimize=True, quality=60)
                img_content = img_io.getvalue()
                
                # Upload to Supabase Storage bucket 'images'
                res = supabase.storage.from_("images").upload(
                    path=image_filename,
                    file=img_content,
                    file_options={"content-type": "image/jpeg", "upsert": "true"}
                )
                
                # Get Public URL
                image_url = supabase.storage.from_("images").get_public_url(image_filename)
            else:
                # Supabase not configured - use local default image
                image_url = url_for('static', filename='images/default.jpg', _external=True)
                flash("Image uploaded locally (Supabase not configured).", "info")
        except Exception as e:
            print(f"Error uploading to Supabase: {e}")
            # Don't block registration - use default image
            image_url = url_for('static', filename='images/default.jpg', _external=True)
            flash("Image upload failed. Using default profile picture.", "warning")

        new_user = User(student_id=student_id, name=name, department=department, batch=batch,
                        blood_group=blood_group, mobile=mobile_combined, email=form.email.data,
                        date_of_birth=form.date_of_birth.data, address=address, image=image_url,
                        is_available=form.is_available.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        # Send admin notification for new user approval
        send_admin_registration_notification(new_user)

        # Send welcome email with verification link
        send_welcome_email(new_user)

        flash("Registration successful! Please check your email to verify your account. You will also need admin approval before you can login.", "success")
        return redirect(url_for('user_login'))

    return render_template('register.html', form=form, current_palette=config.current_palette)

# Helper functions for department mapping
def get_faculty_from_program(program_name):
    """Get faculty code for a given program name"""
    for faculty_code, programs in PROGRAM_DATA.items():
        if program_name in programs:
            return faculty_code
    return None

def map_department_to_program(department_name):
    """Map any department name (clean or dirty) to the official program name"""
    def normalize(name):
        """Normalize: strip spaces, replace multiple spaces with single, lowercase"""
        return ' '.join(name.strip().split()).lower()

    # First check if it's already a clean program name
    normalized_dept = normalize(department_name)
    for programs in PROGRAM_DATA.values():
        for prog in programs:
            if normalize(prog) == normalized_dept:
                return prog

    # Check the mapping for dirty terms
    for official_name, dirty_terms in DEPARTMENT_MAPPING.items():
        for dirty_term in dirty_terms:
            if normalize(dirty_term) == normalized_dept:
                return official_name

    return department_name  # Return as-is if no mapping found

def match_mobile_in_list(mobile_input, mobile_list):
    """Check if a mobile number matches any in a comma-separated list"""
    if not mobile_input or not mobile_list:
        return False

    mobile_input_clean = mobile_input.strip()
    mobiles = [m.strip() for m in mobile_list.split(',') if m.strip()]

    return mobile_input_clean in mobiles

# Department mapping for fuzzy search (official names to lists of dirty/clean variations)
DEPARTMENT_MAPPING = {
    'B.Sc. (Hons.) in Environmental Science (BES)': [
        'Environmental science',
        'Environmental Science',
        'Department of Environmental Science',
        'Environment Science',
        'ES',
    ],
    'B.Sc. in Computer Science and Engineering': [
        'B.Sc. in Computer Science & Engineering',
    ],
    'B.Sc. in Information and Communication Engineering': [
        'Information and Communication Engineering',
        'ICE',
        'Information and Communication Technology',
        'Information & Communication Technology',
        'Ict',
        'Information and Communication Technology',
    ],
    'BA (Hons) in English': [
        'English',
        'ENGLISH',
        'English ',
    ],
    'BBA in Accounting and Information Systems': [
        'Accounting and information systems AIS',
        'Accounting and Information Systems',
        'Accounting and information systems',
        'Ais',
        'Department of Accounting and Information Systems',
        'Accounting and Information System',
        'Accounting & Information Systems',
        'Bba in AIS',
        'Accounting & Information System',
        'AIS',
        'AIS 1',
        'Accounting and Information System',
        'Accounting & Information Systems (AIS)',
    ],
    'BBA in Finance & Banking': [
        'Finance & banking',
        'Finance and Banking',
        'Finance and banking',
        'F&B',
        'BBA In Finance & Banking',
        'Department of Business Administration in Finance and Banking',
        'Finance & Banking',
        'Finanace and Banking',
        'Finance and Banking ',
        'Finance & Banking ',
    ],
    'BBA in Management Studies': [
        'Management Studies',
        'Management',
        'MGT',
        'Management studies',
        'BBA in Management',
        'Management 01',
        'BBA Management',
        'MANAGEMENT STUDIES',
        'Management ',
        'Management Studies ',
        'Management studies ',
    ],
    'BBA in Marketing': [
        'Marketing',
        'Mkt',
        'BBA in marketing',
        'MARKETING',
        'Marketing ',
    ],
    'BSS (Hons) in Development Studies': [
        'Development Studies',
        'DEVELOPMENT STUDIES',
        'Development studies',
        'DEVELOPMENT STUDIES ',
    ],
    'BSS (Hons) in Disaster and Human Security Management': [
        'Disaster and Human Security Management',
        'DHSM',
    ],
    'BSS (Hons) in Economics': [
        'Economics',
        'Department of Economics',
        'Economic',
        'Economics ',
        'Economic ',
    ],
    'BSS (Hons) in International Relations': [
        'International Relations',
        'International Relations (IR-5)',
        'IR',
        'Department of international Relations',
        'International relations',
        'INTERNATIONAL RELATIONS',
        'International Relations ',
        'Department of international Relations ',
        'International relations ',
        'INTERNATIONAL RELATIONS ',
    ],
    'BSS (Hons) in Mass Communication & Journalism': [
        'MCJ',
        'Mass Communication and Journalism (MC& J)',
        'Mass communication & journalism',
        'Mass Communication & Journalism',
        'Mass communication and Journalism',
        'Mass communication & journalism ',
        'Mass Communication & Journalism ',
        'Mass communication and Journalism ',
        'Mass communication & Journalism ',
        'Mass Communication and Journalism ',
    ],
    'BSS (Hons) in Public Administration': [
        'Public Administration',
        'PUBLIC ADMINISTRATION',
        'public Administration',
        'Public administration',
        'Public Administration ',
        'public Administration ',
        'Public administration ',
    ],
    'Bachelor of Arts (Pass)': [
        # 'Modern Languages',  # Not found in DB
    ],
    'Bachelor of Business Administration (BBA)': [
        'BBA',
        'BBA GEN',
        'BBA Gen',
        'BBA-General',
        'BBA(general)',
        'BBA General',
        'FBS',
        'BBA (Gen)',
    ],
    'Bachelor of Social Science (Honours) in Sociology': [
        'Sociology',
        'SOCIOLOGY',
        'Soc',
        'Sociology ',
        'SOCIOLOGY ',
    ],
    'Bachelor of Social Science (Pass)': [
        'BSS',
    ],
    'Bachelor of Social Science in Disaster Management and Resilience': [
        'DMR',
        'Disaster Management and Resilience',
        'Disaster Management',
        'Disaster Management & Resilience',
        'Disaster Management And Resilience',
        'Disaster Management and Residence (DMR)',
        'DMR ',
        'Disaster Management and Resilience ',
        'Disaster Management & Resilience ',
        'Disaster Management And Resilience ',
    ],
    'Bachelor of Social Science in Peace, Conflict and Human Rights Studies': [
        'Peace, Conflict and Human Rights',
        'Peace Conflict and Human Rights',
        'Peace , Conflict and Human Rights',
        'Peace, Conflict and Human Rights Studies',
        'PEACE CONFLICT AND HUMAN RIGHTS',
        'Peace, Conflict and Human Rights ',
        'Peace Conflict and Human Rights ',
    ],
    'LLB (Hons) in Law': [
        # 'Law',  # Not found in DB
        # 'Department of Law',  # Not found in DB
        # 'LAW',  # Not found in DB
    ],
    'MBA in Marketing': [
        'MBA Marketing',
        'MBA Marketing ',
    ],
    'Master of Business Administration (MBA)': [
        'MBA',
        'MBA (Professional)',
        'MBA - Regular',
    ],
}

@app.route('/login', methods=['GET', 'POST'])

@limiter.limit("30 per minute")
def user_login():
    if current_user.is_authenticated:
        return redirect(url_for('user_profile'))
    
    form = UserLoginForm()
    if form.validate_on_submit():
        identifier = form.identifier.data.strip()
        
        # Try to find user by Student ID, Mobile (handling comma-separated), or Email
        user = None

        # First try direct match for student_id and email
        user = User.query.filter(
            (User.student_id == identifier) |
            (User.email == identifier)
        ).first()

        # If not found, check comma-separated mobile numbers
        if not user:
            # Handle comma-separated mobile search - check if identifier is in any mobile list
            identifier_clean = identifier.strip()
            # Find all users and check their mobile list
            all_users = User.query.all()
            for u in all_users:
                mobiles = [m.strip() for m in u.mobile.split(',') if m.strip()]
                if identifier_clean in mobiles:
                    user = u
                    break
        
        if user and user.check_password(form.password.data):
            if user.is_deleted:
                flash("⚠️ This account has been deactivated. Please contact the admin for assistance.", "danger")
                return redirect(url_for('user_login'))
                
            if not user.is_approved:
                flash("⏳ Your account is pending admin approval. You will receive an email once approved.", "warning")
                return redirect(url_for('home'))
            
            remember = form.remember_me.data
            login_user(user, remember=remember)
            
            # Check if profile needs completion (missing email or old department format or availability not set)
            all_programs = [p for programs in PROGRAM_DATA.values() for p in programs]
            needs_completion = not user.email or user.department not in all_programs or user.is_available is None

            if needs_completion:
                flash("ℹ️ Please complete your profile with your email, updated department information, and availability status.", "info")
                return redirect(url_for('complete_profile'))
            
            flash(f"✅ Welcome back, {user.name}! You are now logged in.", "success")
            return redirect(url_for('user_profile'))
        elif user and not user.check_password(form.password.data):
            flash("❌ Incorrect password. Please try again or use 'Forgot Password' to reset it.", "danger")
        else:
            flash("❌ No account found with that Student ID, mobile, or email address. Please check your details or register.", "danger")
    return render_template('user_login.html', form=form, current_palette=config.current_palette)

@app.route('/user/profile', methods=['GET', 'POST'])
@login_required
def user_profile():
    form = UpdateProfileForm()

    # Populate program choices dynamically
    all_programs = []
    for programs in PROGRAM_DATA.values():
        all_programs.extend(programs)
    form.program.choices = [(p, p) for p in all_programs]

    if form.validate_on_submit():
        # Validate faculty and program selection
        faculty = form.faculty.data
        program_key = form.program.data

        if faculty not in PROGRAM_DATA:
            flash("Invalid faculty selected.", "danger")
            return redirect(url_for('user_profile'))

        faculty_programs = PROGRAM_DATA[faculty]
        if program_key not in faculty_programs:
            flash("Invalid program selected for the chosen faculty.", "danger")
            return redirect(url_for('user_profile'))

        # Check if email is being changed
        email_changed = current_user.email != form.email.data

        # Collect mobile fields and combine into comma-separated string
        mobiles_combined = []
        for i in range(1, 4):  # mobile1, mobile2, mobile3
            mobile_value = getattr(form, f'mobile{i}').data
            if mobile_value and mobile_value.strip():
                mobiles_combined.append(mobile_value.strip())
        current_user.mobile = ','.join(mobiles_combined)

        current_user.department = program_key  # Store the program name
        current_user.date_of_birth = form.date_of_birth.data
        current_user.address = form.address.data
        current_user.last_donation_date = form.last_donation_date.data
        current_user.is_available = form.is_available.data
        
        # Profile Visibility (Archive) logic
        was_archived = current_user.is_archived
        current_user.is_archived = form.is_archived.data
        
        if current_user.is_archived and not was_archived:
            from datetime import datetime
            current_user.archived_at = datetime.utcnow()
            current_user.archived_by = 'user'
        elif not current_user.is_archived and was_archived:
            current_user.archived_at = None
            current_user.archived_by = None


        # Handle email change with verification
        if email_changed:
            current_user.email = form.email.data
            current_user.email_verified = False

            # Send verification email for the new email
            try:
                token = serializer.dumps(form.email.data, salt='email-confirm')
                verify_url = url_for('verify_email_address', token=token, _external=True)

                verify_html = f"""
                <html>
                <body>
                    <h2>Email Verification Required - BUP Blood Bank</h2>
                    <p>Hello {current_user.name},</p>

                    <p>You have updated your email address. To maintain account security, please verify your new email by clicking the link below:</p>

                    <p><a href="{verify_url}">Verify My New Email Address</a></p>

                    <p><strong>This verification link will expire in 24 hours.</strong></p>

                    <p>Until your email is verified, you may experience limited functionality with password reset features.</p>

                    <p>If you did not change your email address, please contact the admin immediately.</p>

                    <p><strong>Your Account Details:</strong></p>
                    <ul>
                        <li>Student ID: <strong>{current_user.student_id}</strong></li>
                        <li>Blood Group: <strong>{current_user.blood_group}</strong></li>
                        <li>Department: <strong>{current_user.department}</strong></li>
                        <li>Batch: <strong>{current_user.batch}</strong></li>
                    </ul>

                    <br>
                    <p>Best regards,<br>BUP Blood Bank Team</p>
                </body>
                </html>
                """

                msg = Message(
                    subject="BUP Blood Bank - Email Verification Required (Email Updated)",
                    recipients=[form.email.data],
                    html=verify_html
                )

                mail.send(msg)
                flash(f"✅ Profile updated successfully! A verification email has been sent to {form.email.data}. Please verify your new email address.", "success")
            except Exception as e:
                print(f"Verification email error: {e}")
                flash("❌ Profile updated, but verification email could not be sent. Please contact admin for assistance.", "warning")
        else:
            flash("✅ Profile updated successfully!", "success")
        
        if form.image.data:
            image_file = form.image.data
            try:
                # Backend validation for image size (2MB limit)
                image_file.seek(0, os.SEEK_END)
                file_size = image_file.tell()
                image_file.seek(0) # Reset cursor
                
                if file_size > 2 * 1024 * 1024:
                    flash("❌ Image size exceeds 2MB limit. Please choose a smaller image.", "danger")
                    # Re-populate form with current user data to avoid empty fields on reload
                    form.process(obj=current_user)
                    donation_form = DonationForm()
                    donations = Donation.query.filter_by(donor_id=current_user.id).order_by(Donation.donation_date.desc()).all()
                    return render_template('profile.html', form=form, donation_form=donation_form, donations=donations, current_palette=config.current_palette)

                supabase = get_supabase_client()
                if supabase:
                    image_filename = f"{current_user.student_id}.jpg"
                    
                    img = Image.open(image_file)
                    img = img.convert('RGB')
                    img_io = io.BytesIO()
                    img.save(img_io, 'JPEG', optimize=True, quality=60)
                    img_content = img_io.getvalue()
                    
                    res = supabase.storage.from_("images").upload(
                        path=image_filename,
                        file=img_content,
                        file_options={"content-type": "image/jpeg", "upsert": "true"}
                    )
                    
                    current_user.image = supabase.storage.from_("images").get_public_url(image_filename)
                else:
                    flash("⚠️ Supabase not configured. Image not uploaded.", "warning")
            except Exception as e:
                print(f"Error uploading to Supabase: {e}")
                flash("❌ Error uploading image.", "danger")

        db.session.commit()
        return redirect(url_for('user_profile'))
    
    elif request.method == 'GET':
        # Split mobile numbers for display in mobile1, mobile2, mobile3 fields
        mobile_numbers = [m.strip() for m in current_user.mobile.split(',') if m.strip()]
        form.mobile1.data = mobile_numbers[0] if len(mobile_numbers) > 0 else ''
        form.mobile2.data = mobile_numbers[1] if len(mobile_numbers) > 1 else ''
        form.mobile3.data = mobile_numbers[2] if len(mobile_numbers) > 2 else ''

        form.email.data = current_user.email
        form.date_of_birth.data = current_user.date_of_birth
        form.address.data = current_user.address
        form.last_donation_date.data = current_user.last_donation_date
        form.is_available.data = current_user.is_available
        form.is_archived.data = current_user.is_archived


        # Populate faculty and program fields based on current department
        current_dept = current_user.department
        if current_dept:
            # Find which faculty this program belongs to
            for faculty_code, programs in PROGRAM_DATA.items():
                if current_dept in programs:
                    form.faculty.data = faculty_code
                    form.program.data = current_dept
                    break

    donation_form = DonationForm()
    donations = Donation.query.filter_by(user_id=current_user.id).order_by(Donation.donation_date.desc()).all()

    return render_template('profile.html', form=form, donation_form=donation_form, donations=donations, current_palette=config.current_palette, today=date.today(), program_data=PROGRAM_DATA, mobile_numbers=mobile_numbers)

@app.route('/user/complete-profile', methods=['GET', 'POST'])
@login_required
def complete_profile():
    form = CompleteProfileForm()
    
    # Populate choices for validation (CRITICAL for dynamic SelectField)
    all_programs = []
    for programs in PROGRAM_DATA.values():
        all_programs.extend(programs)
    form.program.choices = [(p, p) for p in all_programs]
    
    # Pre-fill email if it exists
    if request.method == 'GET':
        form.email.data = current_user.email or ''
        # Try to guess faculty if possible (optional)
        # We can't easily guess faculty from old department names, so we leave it empty
    
    if form.validate_on_submit():
        current_user.email = form.email.data
        current_user.department = form.program.data  # Store the full program name
        current_user.is_available = form.is_available.data
        db.session.commit()
        flash("✅ Profile completed successfully!", "success")
        return redirect(url_for('user_profile'))
    
    return render_template('complete_profile.html', form=form, current_palette=config.current_palette)


@app.route('/user/add_donation', methods=['POST'])
@login_required
def add_donation():
    form = DonationForm()
    if form.validate_on_submit():
        if form.donation_date.data > date.today():
            flash("❌ Donation date cannot be in the future.", "danger")
            return redirect(url_for('user_dashboard'))

        # Check for overlap with existing donations (must be at least 90 days apart)
        existing_donations = Donation.query.filter_by(user_id=current_user.id).all()
        for donation in existing_donations:
            delta = abs((form.donation_date.data - donation.donation_date).days)
            if delta < 90:
                flash(f"⚠️ Invalid date! You donated on {donation.donation_date}. Minimum gap is 90 days.", "danger")
                return redirect(url_for('user_dashboard'))

        new_donation = Donation(
            user_id=current_user.id,
            donation_date=form.donation_date.data,
            location=form.location.data,
            notes=form.notes.data
        )
        
        # --- DYNAMIC AVAILABILITY LOGIC ---
        # Read the user's preference from the SweetAlert prompt (sent as hidden input)
        auto_available = request.form.get('auto_available', 'true') == 'true'
        
        # We set `is_available` to whatever the user requested.
        # But wait! If auto_available is True, won't they show up as Available IMMEDIATELY? 
        # No. The public search and home page queries natively check: 
        #   User.last_donation_date <= date.today() - timedelta(days=120)
        # Because we are setting their last_donation_date to TODAY below, those public queries
        # will mathematically hide them for exactly 120 days, effectively making them Unavailable.
        # On the 121st day, the date condition will suddenly pass, and since is_available is True,
        # they will magically reappear on the Available donors list without any cron jobs.
        # If auto_available is False, then even after 120 days, they remain explicitly blocked.
        current_user.is_available = auto_available


        # Update user's last donation date automatically
        if current_user.last_donation_date is None or form.donation_date.data > current_user.last_donation_date:
            current_user.last_donation_date = form.donation_date.data

            
        db.session.add(new_donation)
        db.session.commit()
        flash("✅ Donation record saved! Thank you for your contribution.", "success")
    else:
        flash("❌ Error saving donation record. Please check the details.", "danger")
        
    return redirect(url_for('user_dashboard'))

@app.route('/user/logout')
@login_required
def user_logout():
    logout_user()
    flash("👋 Logged out successfully.", "success")
    return redirect(url_for('home'))

@app.route('/user/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # Check if current password is correct
        if not current_user.check_password(form.current_password.data):
            flash("❌ Current password is incorrect.", "danger")
            return render_template('change_password.html', form=form, current_palette=config.current_palette)
        
        # Check if new passwords match
        if form.new_password.data != form.confirm_password.data:
            flash("❌ New passwords do not match.", "danger")
            return render_template('change_password.html', form=form, current_palette=config.current_palette)
        
        # Check if new password is different from current
        if form.current_password.data == form.new_password.data:
            flash("⚠️ New password must be different from current password.", "warning")
            return render_template('change_password.html', form=form, current_palette=config.current_palette)
        
        # Update password
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash("✅ Password updated successfully!", "success")
        return redirect(url_for('user_dashboard'))
    
    return render_template('change_password.html', form=form, current_palette=config.current_palette)

@app.route('/user/forgot-password', methods=['GET', 'POST'])
@limiter.limit("20 per hour")
def forgot_password():
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for('user_dashboard'))

    form = RequestResetForm()
    if form.validate_on_submit():
        identifier = form.identifier.data.strip()
        
        # Try to find user by Email OR Student ID
        user = User.query.filter(or_(User.email == identifier, User.student_id == identifier)).first()
        
        if user:
            # SCENARIO A: User has a Verified Email (Standard Safe Flow)
            if user.email and user.email_verified:
                reset_token = serializer.dumps(user.email, salt='password-reset')
                reset_url = url_for('reset_password_with_token', token=reset_token, _external=True)

                if send_password_reset_email(user, reset_url):
                    flash("✅ Password reset link sent to your registered email. Please check your inbox (and spam folder).", "success")
                    return redirect(url_for('user_login'))
                else:
                    flash("❌ Failed to send email. Please contact admin.", "danger")
            
            # SCENARIO B: User has Email but UNVERIFIED
            elif user.email and not user.email_verified:
                 flash("⚠️ Your email address is not verified. Please contact your department admin to verify your account manually.", "warning")

            # SCENARIO C: NO EMAIL (Legacy Account) -> Fallback to complex identity verification
            else:
                flash("ℹ️ No email linked to this account. Please verify your identity.", "info")
                return redirect(url_for('verify_identity', student_id=user.student_id))
        else:
            # Security: Don't reveal if user exists or not, but for this specific university context 
            # where IDs are public, we might be more lenient, but standard practice is generic message.
            # However, for UX in this closed system, we'll say:
            flash("❌ No account found with that Email or Student ID.", "danger")
            
    return render_template('forgot_password.html', form=form, current_palette=config.current_palette)

@app.route('/user/verify-identity', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def verify_identity():
    # Only for users without email access
    if current_user.is_authenticated:
        return redirect(url_for('user_dashboard'))

    form = IdentityVerificationForm()
    
    # Pre-fill student_id if passed in args
    if request.method == 'GET' and request.args.get('student_id'):
        form.student_id.data = request.args.get('student_id')

    if form.validate_on_submit():
        # Validate faculty and program selection
        faculty = form.faculty.data
        program_key = form.program.data

        if faculty not in PROGRAM_DATA:
            flash("❌ Invalid faculty selected.", "danger")
            return render_template('verify_identity.html', form=form, program_data=PROGRAM_DATA, current_palette=config.current_palette)

        faculty_programs = PROGRAM_DATA[faculty]
        if program_key not in faculty_programs:
            flash("❌ Invalid program selected.", "danger")
            return render_template('verify_identity.html', form=form, program_data=PROGRAM_DATA, current_palette=config.current_palette)

        user = User.query.filter_by(student_id=form.student_id.data).first()

        if user:
            # Map user's old department to clean program name for comparison
            user_program = map_department_to_program(user.department)

            # Strict Identity Verification
            verification_passed = (
                match_mobile_in_list(form.mobile.data, user.mobile) and
                user_program == program_key and
                user.blood_group == form.blood_group.data
            )

            if not verification_passed:
                flash("❌ Identity verification failed. Details do not match.", "danger")
            else:
                # Verification SUCCESS
                
                # Check if they have already abused this manual reset?
                if user.has_reset_password:
                     flash("⚠️ You have already used the manual recovery option once. Please contact admin.", "danger")
                     return redirect(url_for('contact'))
                
                # Allow Reset
                session['reset_user_id'] = user.id
                session['email_verified'] = True # Bypass email check for this session
                
                flash("✅ Identity confirmed. Please set a new password immediately.", "success")
                return redirect(url_for('reset_password'))

        else:
            flash("❌ Student ID not found.", "danger")

    return render_template('verify_identity.html', form=form, program_data=PROGRAM_DATA, current_palette=config.current_palette)

@app.route('/user/verify-email', methods=['GET', 'POST'])
def verify_email():
    if 'reset_user_id' not in session:
        return redirect(url_for('forgot_password'))
    
    user = User.query.get(session['reset_user_id'])
    if not user or not user.email:
        return redirect(url_for('forgot_password'))
        
    form = VerifyEmailForm()
    masked = mask_email(user.email)
    
    if form.validate_on_submit():
        if form.email.data.lower().strip() == user.email.lower().strip():
            session['email_verified'] = True
            flash("✅ Email verified successfully.", "success")
            return redirect(url_for('reset_password'))
        else:
            flash("❌ Email does not match.", "danger")
            
    return render_template('verify_email.html', form=form, masked_email=masked, current_palette=config.current_palette)

@app.route('/user/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_user_id' not in session:
        return redirect(url_for('forgot_password'))
        
    # Check if email verification was required and completed
    user = User.query.get(session['reset_user_id'])
    if user.email and not session.get('email_verified'):
        return redirect(url_for('verify_email'))
        
    form = ResetPasswordForm()
    if form.validate_on_submit():
        if form.new_password.data != form.confirm_password.data:
            flash("❌ Passwords do not match.", "danger")
        else:
            user.set_password(form.new_password.data)
            user.has_reset_password = True  # Mark that user has used forgot password
            db.session.commit()
            
            # Clear session
            session.pop('reset_user_id', None)
            session.pop('email_verified', None)
            
            flash("✅ Password reset successful. Please login.", "success")
            return redirect(url_for('user_login'))
            
    return render_template('reset_password.html', form=form, current_palette=config.current_palette)


@app.route('/user/delete_donation/<int:donation_id>', methods=['POST'])
@login_required
def delete_donation(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    
    # Check ownership
    if donation.user_id != current_user.id:
        flash("❌ You do not have permission to delete this record.", "danger")
        return redirect(url_for('user_dashboard'))
    
    # Check 1-week limit
    if (date.today() - donation.donation_date).days > 7:
        flash("⚠️ You can only delete donation records within 1 week of the donation date.", "warning")
        return redirect(url_for('user_dashboard'))
        
    db.session.delete(donation)
    
    # Update user's last donation date if needed
    if current_user.last_donation_date == donation.donation_date:
        latest_donation = Donation.query.filter(Donation.user_id == current_user.id, Donation.id != donation.id).order_by(Donation.donation_date.desc()).first()
        if latest_donation:
            current_user.last_donation_date = latest_donation.donation_date
        else:
            current_user.last_donation_date = None
            
    db.session.commit()
    flash("✅ Donation record deleted successfully.", "success")
    return redirect(url_for('user_dashboard'))

@app.route('/user/edit_donation/<int:donation_id>', methods=['GET', 'POST'])
@login_required
def edit_donation(donation_id):
    donation = Donation.query.get_or_404(donation_id)
    
    # Check ownership
    if donation.user_id != current_user.id:
        flash("❌ You do not have permission to edit this record.", "danger")
        return redirect(url_for('user_dashboard'))
    
    # Check 1-week limit
    if (date.today() - donation.donation_date).days > 7:
        flash("⚠️ You can only edit donation records within 1 week of the donation date.", "warning")
        return redirect(url_for('user_dashboard'))
        
    form = DonationForm()
    
    if form.validate_on_submit():
        donation.donation_date = form.donation_date.data
        donation.location = form.location.data
        donation.notes = form.notes.data
        
        db.session.commit()
        
        # Re-calculate last donation date
        latest_donation = Donation.query.filter_by(user_id=current_user.id).order_by(Donation.donation_date.desc()).first()
        if latest_donation:
            current_user.last_donation_date = latest_donation.donation_date
        else:
            current_user.last_donation_date = None
        db.session.commit()
        
        flash("✅ Donation record updated successfully.", "success")
        return redirect(url_for('user_profile'))
    
    # Pre-fill form
    elif request.method == 'GET':
        form.donation_date.data = donation.donation_date
        form.location.data = donation.location
        form.notes.data = donation.notes
        
    return render_template('edit_donation.html', form=form, donation=donation, current_palette=config.current_palette)

# Static pages (Terms of Service, About, Contact)

@app.route('/tos')
def tos():
    return render_template('tos.html', current_palette=config.current_palette)

@app.route('/about')
def about():
    return render_template('about.html', current_palette=config.current_palette)

@app.route('/verify-email/<token>')
def verify_email_address(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=86400)  # 24 hours
        user = User.query.filter_by(email=email).first()
        if user and not user.email_verified:
            user.email_verified = True
            db.session.commit()
            flash("✅ Email verified successfully! Your account will now need admin approval before you can login.", "success")
            return redirect(url_for('user_login'))
        else:
            flash("ℹ️ Email already verified or invalid token.", "info")
            return redirect(url_for('user_login'))
    except SignatureExpired:
        flash("⚠️ Verification link expired. Please register again.", "warning")
        return redirect(url_for('register'))
    except Exception as e:
        print(f"Email verification error: {e}")
        flash("❌ Invalid verification link.", "danger")
        return redirect(url_for('user_login'))

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_with_token(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)  # 1 hour
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("❌ Invalid reset link.", "danger")
            return redirect(url_for('user_login'))

        form = ResetPasswordForm()
        if form.validate_on_submit():
            if form.new_password.data != form.confirm_password.data:
                flash("❌ Passwords do not match.", "danger")
            else:
                user.set_password(form.new_password.data)
                user.has_reset_password = True
                db.session.commit()
                flash("✅ Password reset successful. Please login.", "success")
                return redirect(url_for('user_login'))

        return render_template('reset_password_with_token.html', form=form, current_palette=config.current_palette)
    except SignatureExpired:
        flash("⚠️ Password reset link expired. Please request a new one.", "warning")
        return redirect(url_for('forgot_password'))
    except Exception as e:
        print(f"Password reset error: {e}")
        flash("Invalid reset link.", "danger")
        return redirect(url_for('user_login'))

@app.route('/contact')
def contact():
    return render_template('contact.html', current_palette=config.current_palette)

if __name__ == '__main__':
    app.run(debug=True)
