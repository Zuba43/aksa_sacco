from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, DateField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, Email, Length, EqualTo


RELATIONSHIP_CHOICES = [
    ('', 'Select relationship'),
    ('Mother', 'Mother'),
    ('Father', 'Father'),
    ('Sibling', 'Sibling'),
    ('Guardian/Friend', 'Guardian / Friend')
]

class LoginForm(FlaskForm):
    login_id = StringField('Username or Phone Number', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    # Tab 1: Bio Data
    fname = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    lname = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=20)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    #role = SelectField('Role', choices=[('student', 'Student'), ('admin', 'Admin')], validators=[DataRequired()]) # Added role field
    gender = SelectField('Gender', choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female')], validators=[DataRequired()])
    dob = StringField('Date of Birth', validators=[DataRequired()])
    home_district = StringField('Home District', validators=[DataRequired()])
    nin = StringField('NIN (National ID Number)', validators=[DataRequired(), Length(min=10, max=30)])

    # Tab 2: KYC Documents
    passport_photo = FileField('Passport Photo', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    id_scan = FileField('National ID Scan', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images or PDF only!')])

    # Emergency Contact 1
    emergency_name_1 = StringField('Emergency Contact 1 Full Name', validators=[DataRequired()])
    emergency_phone_1 = StringField('Emergency Contact 1 Phone', validators=[DataRequired()])
    emergency_relation_1 = SelectField(
        'Relationship', 
        choices=RELATIONSHIP_CHOICES, 
        validators=[DataRequired(message="Please select a relationship.")]
    )
    
    # Emergency Contact 2
    emergency_name_2 = StringField('Emergency Contact 2 Full Name', validators=[DataRequired()])
    emergency_phone_2 = StringField('Emergency Contact 2 Phone', validators=[DataRequired()])
    emergency_relation_2 = SelectField(
        'Relationship', 
        choices=RELATIONSHIP_CHOICES, 
        validators=[DataRequired(message="Please select a relationship.")]
    )
    
    # Emergency Contact 3 (Next of Kin - Primary Beneficiary)
    nok_name = StringField('Next of Kin Full Name', validators=[DataRequired()])
    nok_phone = StringField('Next of Kin Phone', validators=[DataRequired()])
    nok_relation = SelectField(
        'Relationship to Next of Kin', 
        choices=RELATIONSHIP_CHOICES, 
        validators=[DataRequired(message="Please select a relationship.")]
    )

    # Tab 4: Security
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    
    submit = SubmitField('Submit Application')