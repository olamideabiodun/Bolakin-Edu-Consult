from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, DateTimeField
from wtforms.validators import DataRequired, Length
from datetime import datetime, timedelta

class NewsletterForm(FlaskForm):
    """Form for creating and editing newsletters"""
    subject = StringField('Subject', validators=[
        DataRequired(),
        Length(max=255, message='Subject must be less than 255 characters.')
    ])
    
    content = TextAreaField('Content (HTML)', validators=[
        DataRequired()
    ])
    
    status = SelectField('Status', choices=[
        ('Draft', 'Save as Draft'),
        ('Scheduled', 'Schedule for Later'),
        ('Send Now', 'Send Now')
    ], validators=[DataRequired()])
    
    scheduled_at = DateTimeField('Schedule Date and Time', 
                               format='%Y-%m-%d %H:%M', 
                               default=(datetime.now() + timedelta(days=1)).replace(
                                   hour=9, minute=0, second=0, microsecond=0))
    
    submit = SubmitField('Save Newsletter')