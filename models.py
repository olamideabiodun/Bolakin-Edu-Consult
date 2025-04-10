from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """Admin user model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'


class Subscriber(db.Model):
    """Newsletter subscribers"""
    __tablename__ = 'subscribers'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Subscriber {self.email}>'


class AdmissionApplication(db.Model):
    """Students who applied for admission"""
    __tablename__ = 'admission_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    
    # Academic background
    prev_institution = db.Column(db.String(255), nullable=False)
    qualification = db.Column(db.String(255), nullable=False)
    grad_year = db.Column(db.Integer, nullable=False)
    gpa = db.Column(db.String(20), nullable=False)
    
    # Program selection
    course = db.Column(db.String(255), nullable=False)
    study_mode = db.Column(db.String(50), nullable=False)
    campus = db.Column(db.String(100))
    
    # Documents - store file paths
    id_document = db.Column(db.String(255))
    transcript = db.Column(db.String(255))
    passport_photo = db.Column(db.String(255))
    
    # Status
    status = db.Column(db.String(50), default='Pending')  # Pending, Reviewing, Accepted, Rejected
    admin_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Application {self.id}: {self.full_name}>'


class Newsletter(db.Model):
    """Newsletter campaigns"""
    __tablename__ = 'newsletters'
    
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Draft')  # Draft, Scheduled, Sent
    scheduled_at = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = db.relationship('User', backref='newsletters')
    
    def __repr__(self):
        return f'<Newsletter {self.id}: {self.subject}>'


class NewsletterDelivery(db.Model):
    """Tracks newsletter deliveries to each subscriber"""
    __tablename__ = 'newsletter_deliveries'
    
    id = db.Column(db.Integer, primary_key=True)
    newsletter_id = db.Column(db.Integer, db.ForeignKey('newsletters.id'), nullable=False)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('subscribers.id'), nullable=False)
    delivered_at = db.Column(db.DateTime)
    opened_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    
    # Relationships
    newsletter = db.relationship('Newsletter', backref='deliveries')
    subscriber = db.relationship('Subscriber', backref='received_newsletters')
    
    def __repr__(self):
        return f'<Delivery {self.id}: Newsletter {self.newsletter_id} to {self.subscriber_id}>'


class PageVisit(db.Model):
    """Tracks website traffic"""
    __tablename__ = 'page_visits'
    
    id = db.Column(db.Integer, primary_key=True)
    page = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.String(255))
    referrer = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PageVisit {self.id}: {self.page}>'