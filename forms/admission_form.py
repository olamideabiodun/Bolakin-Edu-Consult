from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, FileField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional
from flask_wtf.file import FileAllowed

class AdmissionForm(FlaskForm):
    """Form for admission applications"""
    # Personal Information
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    dob = DateField('Date of Birth', validators=[DataRequired()], format='%Y-%m-%d')
    gender = SelectField('Gender', choices=[
        ('', 'Select Gender'),
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
        ('Prefer not to say', 'Prefer not to say')
    ], validators=[DataRequired()])
    
    # Academic Background
    prev_institution = StringField('Previous Institution', validators=[DataRequired(), Length(max=255)])
    qualification = StringField('Qualification', validators=[DataRequired(), Length(max=255)])
    grad_year = StringField('Year of Graduation', validators=[DataRequired()])
    gpa = StringField('GPA or Grade', validators=[DataRequired(), Length(max=20)])
    
    # Program Selection
    course = StringField('Preferred Course or Program', validators=[DataRequired(), Length(max=255)])
    study_mode = SelectField('Study Mode', choices=[
        ('', 'Select Study Mode'),
        ('Full-time', 'Full-time'),
        ('Part-time', 'Part-time'),
        ('Distance Learning', 'Distance Learning')
    ], validators=[DataRequired()])
    campus = StringField('Campus', validators=[Optional(), Length(max=100)])
    
    # Documents
    id_document = FileField('Upload ID', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF and image files are allowed.')
    ])
    transcript = FileField('Upload Transcript', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Only PDF and image files are allowed.')
    ])
    passport_photo = FileField('Upload Passport Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Only image files are allowed.')
    ])
    
    # Declaration
    agreement = BooleanField('I agree to the terms and conditions', validators=[DataRequired()])
    
    submit = SubmitField('Submit Application')