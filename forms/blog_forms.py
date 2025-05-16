from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from flask_wtf.file import FileField, FileAllowed
import re

class BlogPostForm(FlaskForm):
    """Form for creating and editing blog posts"""
    title = StringField('Title', validators=[
        DataRequired(), 
        Length(max=200, message='Title must be less than 200 characters.')
    ])
    
    slug = StringField('Slug (URL)', validators=[
        DataRequired(),
        Length(max=200, message='Slug must be less than 200 characters.')
    ])
    
    excerpt = TextAreaField('Excerpt', validators=[
        Optional(),
        Length(max=300, message='Excerpt must be less than 300 characters.')
    ])
    
    content = TextAreaField('Content', validators=[
        DataRequired()
    ])
    
    categories = SelectMultipleField('Categories', coerce=int, validators=[Optional()])
    
    featured_image = FileField('Featured Image (Thumbnail/Preview)', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    
    hero_background_image = FileField('Hero Background Image (Large, for top of post)', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    
    is_published = BooleanField('Publish Post', default=True)
    
    submit = SubmitField('Save Post')
    
    def validate_slug(self, field):
        """Validate that slug contains only URL-safe characters"""
        pattern = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
        if not pattern.match(field.data):
            raise ValidationError('Slug must contain only lowercase letters, numbers, and hyphens')


class BlogCategoryForm(FlaskForm):
    """Form for creating and editing blog categories"""
    name = StringField('Category Name', validators=[
        DataRequired(),
        Length(max=100, message='Name must be less than 100 characters.')
    ])
    
    slug = StringField('Slug (URL)', validators=[
        Optional(),
        Length(max=100, message='Slug must be less than 100 characters.')
    ])
    
    description = TextAreaField('Description', validators=[
        Optional(),
        Length(max=300, message='Description must be less than 300 characters.')
    ])
    
    submit = SubmitField('Save Category')
    
    def validate_slug(self, field):
        """Validate that slug contains only URL-safe characters"""
        if field.data: # Only validate if data is provided
            pattern = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
            if not pattern.match(field.data):
                raise ValidationError('Slug must contain only lowercase letters, numbers, and hyphens')


class BlogCommentForm(FlaskForm):
    """Form for users to comment on blog posts"""
    author_name = StringField('Name', validators=[
        DataRequired(),
        Length(max=100, message='Name must be less than 100 characters.')
    ])
    
    author_email = StringField('Email', validators=[
        DataRequired(),
        Length(max=120, message='Email must be less than 120 characters.')
    ])
    
    content = TextAreaField('Comment', validators=[
        DataRequired()
    ])
    
    submit = SubmitField('Post Comment')