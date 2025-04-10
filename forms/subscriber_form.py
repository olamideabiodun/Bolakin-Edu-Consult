from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional

class SubscriberForm(FlaskForm):
    """Form for newsletter subscription"""
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    
    name = StringField('Name (Optional)', validators=[
        Optional(),
        Length(max=120)
    ])
    
    is_active = BooleanField('Active Subscription', default=True)
    
    submit = SubmitField('Subscribe')


class SubscriberManagementForm(FlaskForm):
    """Form for admin to manage subscribers"""
    email = StringField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    
    name = StringField('Name', validators=[
        Optional(),
        Length(max=120)
    ])
    
    is_active = BooleanField('Active Subscription', default=True)
    
    submit = SubmitField('Save Changes')