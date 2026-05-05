from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, FileField, BooleanField, DateField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Email, Optional
import re
import datetime

def validate_multiple_mobiles(form, field):
    """Custom validator for Bangladeshi mobile numbers in multiple fields"""
    # Get all mobile fields from the form
    mobiles = []
    for i in range(1, 4):  # Check mobile1, mobile2, mobile3
        mobile_field = getattr(form, f'mobile{i}', None)
        if mobile_field and mobile_field.data and mobile_field.data.strip():
            mobiles.append(mobile_field.data.strip())

    if not mobiles:
        raise ValidationError('At least one mobile number is required')
    # Bangladeshi mobile pattern: 01XXXXXXXX (11 digits without hyphen)
    mobile_pattern = re.compile(r'^01\d{9}$')

    seen_mobiles = set()
    for mobile in mobiles:
        if not mobile_pattern.match(mobile):
            raise ValidationError(f'Invalid mobile format: {mobile}. Use format 01XXXXXXXXX (11 digits)')
        if mobile in seen_mobiles:
            raise ValidationError(f'Duplicate mobile number: {mobile}')
        seen_mobiles.add(mobile)

def validate_mobile(form, field):
    """Custom validator for Bangladeshi mobile numbers"""
    if not field.data:
        raise ValidationError('At least one mobile number is required')

    # Split by commas and strip whitespace
    mobiles = [m.strip() for m in field.data.split(',') if m.strip()]

    if not mobiles:
        raise ValidationError('At least one mobile number is required')

    # Bangladeshi mobile pattern: 01XXXXXXXX (11 digits without hyphen)
    mobile_pattern = re.compile(r'^01\d{9}$')

    for mobile in mobiles:
        if not mobile_pattern.match(mobile):
            raise ValidationError(f'Invalid mobile format: {mobile}. Use format 01XXXXXXXXX (11 digits)')
        # Check for duplicates in the same field
        if mobiles.count(mobile) > 1:
            raise ValidationError(f'Duplicate mobile number: {mobile}')

class RegistrationForm(FlaskForm):
    student_id = StringField('Student ID', validators=[DataRequired(), Length(min=10, max=15)])
    name = StringField('Name', validators=[DataRequired()])
    faculty = StringField(validators=[DataRequired()])  # Hidden field populated by JS
    program = StringField(validators=[DataRequired()])  # Hidden field populated by JS
    batch = SelectField('Batch', choices=[(str(year), str(year)) for year in range(datetime.datetime.now().year, 2007, -1)], validators=[DataRequired()])
    blood_group = SelectField('Blood Group', choices=[
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-')
    ], validators=[DataRequired()])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()])
    mobile1 = StringField('Mobile Number 1', validators=[DataRequired()])
    mobile2 = StringField('Mobile Number 2 (Optional)')
    mobile3 = StringField('Mobile Number 3 (Optional)')
    email = StringField('Email', validators=[DataRequired(), Email()])
    address = StringField('Address', validators=[DataRequired()])  # Added address field
    image = FileField('Profile Image')
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=6)])
    is_available = BooleanField('Available to Donate Blood?', default=True)

    def validate_mobile1(self, field):
        """Validate the first mobile number and overall mobile validation"""
        validate_multiple_mobiles(self, field)

    submit = SubmitField('Register')

class UserLoginForm(FlaskForm):
    identifier = StringField('Student ID / Mobile / Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class UpdateProfileForm(FlaskForm):
    mobile1 = StringField('Mobile Number 1', validators=[DataRequired()])
    mobile2 = StringField('Mobile Number 2 (Optional)')
    mobile3 = StringField('Mobile Number 3 (Optional)')
    faculty = SelectField('Faculty', choices=[
        ('', 'Select Faculty'),
        ('FST', 'Faculty of Science and Technology (FST)'),
        ('FASS', 'Faculty of Arts and Social Sciences (FASS)'),
        ('FBS', 'Faculty of Business Studies (FBS)'),
        ('FSSS', 'Faculty of Security and Strategic Studies (FSSS)'),
        ('FMS', 'Faculty of Medical Studies (FMS)')
    ], validators=[DataRequired()])
    program = SelectField('Program', choices=[('', 'Select Program')], validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[Optional()])
    address = StringField('Address', validators=[DataRequired()])
    image = FileField('Update Profile Picture')
    last_donation_date = DateField('Last Donation Date', format='%Y-%m-%d', validators=[Optional()])
    is_available = BooleanField('Available to Donate?')
    is_archived = BooleanField('Hide Profile from Public Search?')


    def validate_mobile1(self, field):
        """Validate the first mobile number and overall mobile validation"""
        validate_multiple_mobiles(self, field)

    submit = SubmitField('Update Profile')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Change Password')

class RequestResetForm(FlaskForm):
    identifier = StringField('Email or Student ID', validators=[DataRequired()])
    submit = SubmitField('Send Reset Link')

class IdentityVerificationForm(FlaskForm):
    student_id = StringField('Student ID', validators=[DataRequired()])

    def validate_mobile(self, field):
        """Custom validation for forgot password - check against existing user mobiles"""
        validate_mobile(self, field)  # Use the same validation
        # Additional check: verify this mobile belongs to the user with this student_id
        if self.student_id.data:
            from models import User
            user = User.query.filter_by(student_id=self.student_id.data).first()
            if user:
                # Check if any of the entered mobiles match user's stored mobiles
                stored_mobiles = [m.strip() for m in user.mobile.split(',') if m.strip()]
                entered_mobiles = [m.strip() for m in field.data.split(',') if m.strip()]
                if not any(em in stored_mobiles for em in entered_mobiles):
                    raise ValidationError('Mobile number does not match our records.')
            else:
                raise ValidationError('Student ID not found.')

    mobile = StringField('Mobile Numbers (comma separated)', validators=[DataRequired()])
    faculty = StringField(validators=[DataRequired()])  # Hidden field populated by JS
    program = StringField(validators=[DataRequired()])  # Hidden field populated by JS
    blood_group = SelectField('Blood Group', choices=[
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-')
    ], validators=[DataRequired()])
    submit = SubmitField('Verify Identity')

class VerifyEmailForm(FlaskForm):
    email = StringField('Confirm your Email', validators=[DataRequired()])
    submit = SubmitField('Verify Email')

class DonationForm(FlaskForm):
    donation_date = DateField('Donation Date', format='%Y-%m-%d', validators=[DataRequired()])
    location = StringField('Location (Hospital/Center)', validators=[Optional()])
    notes = StringField('Notes', validators=[Optional()])
    submit = SubmitField('Add Donation')

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Reset Password')

class CompleteProfileForm(FlaskForm):
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    faculty = SelectField('Faculty', choices=[
        ('', 'Select Faculty'),
        ('FST', 'Faculty of Science and Technology (FST)'),
        ('FASS', 'Faculty of Arts and Social Sciences (FASS)'),
        ('FBS', 'Faculty of Business Studies (FBS)'),
        ('FSSS', 'Faculty of Security and Strategic Studies (FSSS)'),
        ('FMS', 'Faculty of Medical Studies (FMS)')
    ], validators=[DataRequired()])
    program = SelectField('Program', choices=[('', 'Select Program')], validators=[DataRequired()])
    is_available = BooleanField('Available to Donate?', validators=[DataRequired()])
    submit = SubmitField('Complete Profile')
