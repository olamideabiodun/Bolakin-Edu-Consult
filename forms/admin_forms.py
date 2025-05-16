from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, EqualTo
from flask_wtf.file import FileField, FileAllowed

class AdminUserUpdateForm(FlaskForm):
    """Form for admin to update user details, including profile picture."""
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=50, message='Username must be between 3 and 50 characters.')
    ])
    email = StringField('Email', validators=[
        DataRequired(), 
        Email(message='Invalid email address.')
    ])
    profile_image = FileField('Profile Picture', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only! (jpg, jpeg, png)')
    ])
    new_password = PasswordField('New Password', validators=[
        Optional(),
        Length(min=8, message='Password must be at least 8 characters long.')
    ])
    confirm_new_password = PasswordField('Confirm New Password', validators=[
        EqualTo('new_password', message='Passwords must match.')
    ])
    is_admin = BooleanField('Is Admin')

    # Social Media Links
    linkedin_url = StringField('LinkedIn URL', validators=[Optional(), Length(max=255)])
    twitter_url = StringField('Twitter URL', validators=[Optional(), Length(max=255)])
    instagram_url = StringField('Instagram URL', validators=[Optional(), Length(max=255)])
    facebook_url = StringField('Facebook URL', validators=[Optional(), Length(max=255)])

    current_password = PasswordField('Current Password', validators=[
        Optional(),
        Length(min=8, message='Password must be at least 8 characters long.')
    ])
    submit = SubmitField('Update User') 