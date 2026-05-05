from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import func
from datetime import datetime, timedelta, date


import pytz
db = SQLAlchemy()


# Function to get the current time in Dhaka time zone
def dhaka_time():
    dhaka = pytz.timezone('Asia/Dhaka')
    return datetime.now(dhaka)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    batch = db.Column(db.String(4), nullable=False)
    blood_group = db.Column(db.String(3), nullable=False)
    mobile = db.Column(db.String(50), nullable=False)  # Note: Multiple mobiles stored as comma-separated values
    email = db.Column(db.String(120), nullable=False, unique=True)
    email_verified = db.Column(db.Boolean, default=False)  # Track email verification
    address = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(500), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=dhaka_time)
    password_hash = db.Column(db.String(256))
    last_donation_date = db.Column(db.Date, nullable=True)
    is_available = db.Column(db.Boolean, nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    has_reset_password = db.Column(db.Boolean, default=False)  # Track if user has used forgot password
    last_login = db.Column(db.DateTime, nullable=True)  # Track last login time
    last_availability_update = db.Column(db.DateTime, nullable=True)  # Track when availability was changed
    
    # --- Soft-Archive/Delete Fields ---
    is_archived = db.Column(db.Boolean, default=False, index=True)
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by = db.Column(db.String(100), nullable=True) # 'user' or 'admin'
    
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.String(100), nullable=True) # 'user' or 'admin'
    deletion_reason = db.Column(db.Text, nullable=True)
    
    # Relationship to Donation History
    donations = db.relationship('Donation', backref='donor', lazy=True)

    @property
    def next_eligible_date(self):
        if self.last_donation_date:
            # Standard 120 days gap
            return self.last_donation_date + timedelta(days=120)
        return None

    @property
    def is_actually_available(self):
        """
        DYNAMIC AVAILABILITY LOGIC:
        A user is only truly available if they have explicitly opted-in (is_available == True)
        AND they have passed the 120-day waiting period from their last donation.
        This allows the system to automatically flip their public status on the 121st day
        without requiring any background chron jobs.
        """
        if not self.is_available:
            return False
        
        if self.next_eligible_date and self.next_eligible_date > date.today():
            return False
            
        return True

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    donation_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.String(200), nullable=True)
class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=dhaka_time)
    is_used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('reset_tokens', lazy=True))

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class AdminLog(db.Model):
    """Track all admin actions for audit purposes"""
    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.String(50), nullable=False)  # 'approve', 'delete', 'edit', 'broadcast', 'reject', 'toggle_availability'
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # User being acted upon
    target_user_name = db.Column(db.String(100), nullable=True)  # Store name in case user is deleted
    details = db.Column(db.Text, nullable=True)  # Additional details about the action
    created_at = db.Column(db.DateTime, nullable=False, default=dhaka_time)
    admin_username = db.Column(db.String(100), nullable=True)  # Admin who performed action
    
    target_user = db.relationship('User', backref=db.backref('admin_logs', lazy=True))
