from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy import event
from sqlalchemy.orm import attributes

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """Admin user model for authentication"""
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    password_changed = db.Column(db.Boolean, default=False, nullable=False)
    profile_image_file = db.Column(db.String(200), nullable=True)  # Added field for profile picture

    # Social Media Handles
    linkedin_url = db.Column(db.String(255), nullable=True)
    twitter_url = db.Column(db.String(255), nullable=True)
    instagram_url = db.Column(db.String(255), nullable=True)
    facebook_url = db.Column(db.String(255), nullable=True) # Added Facebook as well
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'

    # Relationship to Newsletters will be created by backref 'created_newsletters' from Newsletter.creator
    # newsletters_created = db.relationship('Newsletter', lazy='dynamic') # This line is redundant due to backref


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
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Define relationship for creator
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_newsletters')
    
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


class BlogPost(db.Model):
    """Blog posts for the website"""
    __tablename__ = 'blog_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(300))
    featured_image = db.Column(db.String(255))
    hero_background_image = db.Column(db.String(255), nullable=True)
    is_published = db.Column(db.Boolean, default=True)
    views_count = db.Column(db.Integer, default=0)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = db.relationship('User', backref='blog_posts')
    categories = db.relationship('BlogCategory', secondary='blog_post_categories', backref='posts')
    
    def __repr__(self):
        return f'<BlogPost {self.id}: {self.title}>'
    
    @property
    def formatted_date(self):
        """Return a formatted date string"""
        return self.created_at.strftime('%B %d, %Y')
    
    def increment_view(self):
        """Increment the view count for this post"""
        self.views_count += 1
        db.session.commit()


class BlogCategory(db.Model):
    """Categories for blog posts"""
    __tablename__ = 'blog_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(300))
    
    def __repr__(self):
        return f'<BlogCategory {self.id}: {self.name}>'


# Association table for many-to-many relationship between posts and categories
blog_post_categories = db.Table('blog_post_categories',
    db.Column('post_id', db.Integer, db.ForeignKey('blog_posts.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('blog_categories.id'), primary_key=True)
)


class BlogComment(db.Model):
    """Comments on blog posts"""
    __tablename__ = 'blog_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    author_email = db.Column(db.String(120), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    post = db.relationship('BlogPost', backref=db.backref('comments', lazy=True))
    
    def __repr__(self):
        return f'<BlogComment {self.id} on post {self.post_id}>'


class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.String(255), nullable=True)
    login_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<UserSession {self.id}: User {self.user_id}>'


class VisaRequest(db.Model):
    __tablename__ = 'visa_requests'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    destination_country = db.Column(db.String(100), nullable=False)
    visa_type = db.Column(db.String(100), nullable=False) # e.g., Tourist, Student, Work
    preferred_appointment_date = db.Column(db.Date, nullable=True)
    message = db.Column(db.Text, nullable=True)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Pending') # e.g., Pending, In Review, Processed, Action Required, Rejected, Completed
    admin_notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<VisaRequest {self.full_name} - {self.destination_country}>'


class FlightBookingRequest(db.Model):
    __tablename__ = 'flight_booking_requests'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    departure_city = db.Column(db.String(100), nullable=False)
    arrival_city = db.Column(db.String(100), nullable=False)
    departure_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=True) # Optional for one-way
    trip_type = db.Column(db.String(20), nullable=False, default='Round Trip') # Round Trip, One Way
    adults = db.Column(db.Integer, nullable=False, default=1)
    children = db.Column(db.Integer, nullable=False, default=0) # Ages 2-11
    infants = db.Column(db.Integer, nullable=False, default=0) # Under 2
    cabin_class = db.Column(db.String(50), nullable=False, default='Economy') # Economy, Premium Economy, Business, First
    flexible_dates = db.Column(db.Boolean, default=False)
    message = db.Column(db.Text, nullable=True)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    admin_notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<FlightBookingRequest {self.id} for {self.full_name}>'


class ProofOfFundsRequest(db.Model):
    __tablename__ = 'proof_of_funds_requests'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service_type = db.Column(db.String(100), nullable=False) # E.g., "Bank Statement", "Sponsorship Letter"
    purpose = db.Column(db.String(150), nullable=False) # E.g., "Study Permit", "Visitor Visa"
    destination_country = db.Column(db.String(100), nullable=True)
    amount_required = db.Column(db.String(100), nullable=True) # Store as string to include currency, e.g., "15,000 CAD"
    timeline = db.Column(db.String(100), nullable=True) # E.g., "Urgent - Within 1 week"
    message = db.Column(db.Text, nullable=True)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    admin_notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<ProofOfFundsRequest {self.id} for {self.full_name}>'


class HolidayPackageRequest(db.Model):
    __tablename__ = 'holiday_package_requests'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    travel_dates_flexible = db.Column(db.Boolean, default=False)
    preferred_start_date = db.Column(db.Date, nullable=True)
    preferred_end_date = db.Column(db.Date, nullable=True)
    duration_days = db.Column(db.Integer, nullable=True)
    num_adults = db.Column(db.Integer, nullable=False, default=1)
    num_children = db.Column(db.Integer, nullable=False, default=0)
    package_type = db.Column(db.String(100), nullable=True)
    interests = db.Column(db.Text, nullable=True)
    budget_preference = db.Column(db.String(50), nullable=True)
    message = db.Column(db.Text, nullable=True)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    admin_notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<HolidayPackageRequest {self.id} for {self.full_name} to {self.destination}>'


class HotelAccommodationRequest(db.Model):
    __tablename__ = 'hotel_accommodation_requests'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    destination_city_hotel = db.Column(db.String(150), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    num_adults = db.Column(db.Integer, nullable=False, default=1)
    num_children = db.Column(db.Integer, nullable=False, default=0)
    num_rooms = db.Column(db.Integer, nullable=False, default=1)
    hotel_preferences = db.Column(db.Text, nullable=True)
    room_type_preference = db.Column(db.String(100), nullable=True)
    budget_per_night = db.Column(db.String(100), nullable=True)
    special_requests = db.Column(db.Text, nullable=True)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    admin_notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<HotelAccommodationRequest {self.id} for {self.full_name} in {self.destination_city_hotel}>'


# Event listener to set default profile image for new users
# Ensure this is after User model definition
@event.listens_for(User, 'after_insert')
def set_default_profile_image(mapper, connection, target):
    if not target.profile_image_file:
        target.profile_image_file = 'default.jpg'