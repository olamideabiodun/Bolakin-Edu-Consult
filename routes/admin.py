from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_from_directory
from flask_login import login_required, current_user
from sqlalchemy import desc, func, cast, Date
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage # Added FileStorage
from models import db, User, Subscriber, AdmissionApplication, Newsletter, NewsletterDelivery, PageVisit, BlogPost, BlogCategory, BlogComment, UserSession, VisaRequest, FlightBookingRequest, ProofOfFundsRequest, HolidayPackageRequest, HotelAccommodationRequest
from forms.newsletter_form import NewsletterForm
from forms.blog_forms import BlogPostForm, BlogCategoryForm, BlogCommentForm
from forms.admin_forms import AdminUserUpdateForm
from forms.service_forms import UpdateVisaRequestStatusForm, UpdateFlightBookingRequestStatusForm, UpdateProofOfFundsRequestStatusForm, UpdateHolidayPackageRequestStatusForm, UpdateHotelAccommodationRequestStatusForm
from datetime import datetime, timedelta, date as datetime_date
import os
import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps
import io
import json
import re
from unicodedata import normalize

admin = Blueprint('admin', __name__)

# Admin access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard showing overview statistics"""
    # Get overview statistics
    
    # Total subscribers
    total_subscribers = Subscriber.query.count()
    active_subscribers = Subscriber.query.filter_by(is_active=True).count()
    
    # Total applications
    total_applications = AdmissionApplication.query.count()
    
    # Recent applications
    recent_applications = AdmissionApplication.query.order_by(
        desc(AdmissionApplication.created_at)
    ).limit(5).all()
    
    # Total newsletters
    total_newsletters = Newsletter.query.count()
    sent_newsletters = Newsletter.query.filter_by(status='Sent').count()
    
    # Website traffic analytics - last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Daily visits for the last 30 days
    daily_visits = db.session.query(
        func.date(PageVisit.timestamp).label('date'),
        func.count().label('count')
    ).filter(PageVisit.timestamp >= thirty_days_ago).group_by(
        func.date(PageVisit.timestamp)
    ).order_by(func.date(PageVisit.timestamp)).all()
    
    # Format for chart
    visit_dates = []
    for visit in daily_visits:
        if isinstance(visit.date, str):
            try:
                # Assuming visit.date is in 'YYYY-MM-DD' format from func.date()
                dt_obj = datetime.strptime(visit.date, '%Y-%m-%d').date()
                visit_dates.append(dt_obj.strftime('%Y-%m-%d'))
            except ValueError:
                current_app.logger.warning(f"Could not parse date string: {visit.date} in analytics. Using as is.")
                visit_dates.append(visit.date) # Use the string directly if parsing fails
        elif hasattr(visit.date, 'strftime'): # It's already a date/datetime object
            visit_dates.append(visit.date.strftime('%Y-%m-%d'))
        else:
            # Handle unexpected type or log an error
            current_app.logger.warning(f"Unexpected type for visit.date: {type(visit.date)}, value: {visit.date}")
            visit_dates.append(str(visit.date)) # Fallback to string conversion

    visit_counts = [visit.count for visit in daily_visits]
    
    # Top pages in the last 30 days
    top_pages = db.session.query(
        PageVisit.page,
        func.count().label('count')
    ).filter(PageVisit.timestamp >= thirty_days_ago).group_by(
        PageVisit.page
    ).order_by(desc('count')).limit(10).all()
    
    # Convert to list of dicts for easier template rendering
    top_pages_list = [{'page': page.page, 'count': page.count} for page in top_pages]
    
    return render_template('admin/dashboard.html',
                          total_subscribers=total_subscribers,
                          active_subscribers=active_subscribers,
                          total_applications=total_applications,
                          recent_applications=recent_applications,
                          total_newsletters=total_newsletters,
                          sent_newsletters=sent_newsletters,
                          visit_dates=json.dumps(visit_dates),
                          visit_counts=json.dumps(visit_counts),
                          top_pages=top_pages_list)

# Subscriber Management
@admin.route('/subscribers')
@login_required
@admin_required
def subscribers():
    """List all newsletter subscribers"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    # Base query
    query = Subscriber.query
    
    # Apply filters
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    
    # Paginate results
    pagination = query.order_by(desc(Subscriber.created_at)).paginate(
        page=page, 
        per_page=current_app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    
    subscribers = pagination.items
    
    return render_template('admin/subscribers.html', 
                          subscribers=subscribers,
                          pagination=pagination,
                          status=status)

@admin.route('/subscribers/export')
@login_required
@admin_required
def export_subscribers():
    """Export subscribers to CSV"""
    status = request.args.get('status', 'all')
    
    # Base query
    query = Subscriber.query
    
    # Apply filters
    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)
    
    subscribers = query.order_by(desc(Subscriber.created_at)).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Email', 'Name', 'Status', 'Date Subscribed'])
    
    # Write data
    for subscriber in subscribers:
        writer.writerow([
            subscriber.id,
            subscriber.email,
            subscriber.name or '',
            'Active' if subscriber.is_active else 'Inactive',
            subscriber.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # Prepare response
    output.seek(0)
    return current_app.response_class(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=subscribers_{status}_{datetime.now().strftime("%Y%m%d")}.csv'}
    )

@admin.route('/subscribers/<int:id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_subscriber_status(id):
    """Toggle subscriber active status"""
    subscriber = Subscriber.query.get_or_404(id)
    subscriber.is_active = not subscriber.is_active
    
    try:
        db.session.commit()
        status = 'activated' if subscriber.is_active else 'deactivated'
        flash(f'Subscriber {subscriber.email} has been {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling subscriber status: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin.subscribers'))

@admin.route('/subscribers/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subscriber(id):
    """Delete a subscriber"""
    subscriber = Subscriber.query.get_or_404(id)
    
    try:
        db.session.delete(subscriber)
        db.session.commit()
        flash(f'Subscriber {subscriber.email} has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting subscriber: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin.subscribers'))

# Application Management
@admin.route('/applications')
@login_required
@admin_required
def applications():
    """List all admission applications"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    # Base query
    query = AdmissionApplication.query
    
    # Apply filters
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Paginate results
    pagination = query.order_by(desc(AdmissionApplication.created_at)).paginate(
        page=page, 
        per_page=current_app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    
    applications = pagination.items
    
    return render_template('admin/applications.html', 
                          applications=applications,
                          pagination=pagination,
                          status=status)

@admin.route('/applications/<int:id>')
@login_required
@admin_required
def application_details(id):
    """View details of a specific application"""
    application = AdmissionApplication.query.get_or_404(id)
    
    return render_template('admin/application_details.html', application=application)

@admin.route('/applications/<int:id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_application_status(id):
    """Update the status of an application"""
    application = AdmissionApplication.query.get_or_404(id)
    
    status = request.form.get('status')
    notes = request.form.get('admin_notes')
    
    if status not in ['Pending', 'Reviewing', 'Accepted', 'Rejected']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('admin.application_details', id=id))
    
    try:
        application.status = status
        application.admin_notes = notes
        db.session.commit()
        flash(f'Application status updated to {status}.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating application status: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin.application_details', id=id))

# Newsletter Management
@admin.route('/newsletters')
@login_required
@admin_required
def newsletters():
    """List all newsletters"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    # Base query
    query = Newsletter.query
    
    # Apply filters
    if status != 'all':
        query = query.filter_by(status=status)
    
    # Paginate results
    pagination = query.order_by(desc(Newsletter.created_at)).paginate(
        page=page, 
        per_page=current_app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    
    newsletters = pagination.items
    
    return render_template('admin/newsletters.html', 
                          newsletters=newsletters,
                          pagination=pagination,
                          status=status)

@admin.route('/newsletters/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_newsletter():
    """Create a new newsletter"""
    form = NewsletterForm()
    current_app.logger.info(f"Accessing create_newsletter. Method: {request.method}")

    if request.method == 'POST':
        current_app.logger.info(f"POST request to create_newsletter. Form data: {request.form}")
        current_app.logger.info(f"Form submitted: {form.is_submitted()}")
        # It's useful to see if individual validation steps pass
        # For example, check a specific field:
        # current_app.logger.info(f"Subject valid: {form.subject.validate(form)}")
        
        # WTForms' validate_on_submit() checks both is_submitted() and validate()
        # Let's log before and after, and the errors if validate() fails.
        current_app.logger.info("Calling form.validate_on_submit()")
        
        # To see detailed errors, we can call validate() and check form.errors
        # form.validate() # Calling this separately might interfere if not careful
        # current_app.logger.info(f"Form errors after validate(): {form.errors}")

    if form.validate_on_submit():
        current_app.logger.info("form.validate_on_submit() was True.")
        # If status is 'Send Now', we'll save it as 'Draft' first, then redirect to send confirmation.
        actual_status_to_save = 'Draft' if form.status.data == 'Send Now' else form.status.data

        newsletter = Newsletter(
            subject=form.subject.data,
            content=form.content.data,
            status=actual_status_to_save, # Use adjusted status
            creator_id=current_user.id # Assuming creator_id is the correct field for the user
        )
        
        if actual_status_to_save == 'Scheduled' and form.scheduled_at.data:
            newsletter.scheduled_at = form.scheduled_at.data
        
        try:
            current_app.logger.info(f"Attempting to add newsletter to session: Subject - {newsletter.subject}, Status - {newsletter.status}")
            db.session.add(newsletter)
            current_app.logger.info("Attempting to commit session.")
            db.session.commit()
            current_app.logger.info("Commit successful.")
            
            flash(f'Newsletter "{form.subject.data}" has been created.', 'success')
            
            # If status is "Send Now", send the newsletter immediately
            if form.status.data == 'Send Now':
                return redirect(url_for('admin.send_newsletter', id=newsletter.id))
            
            return redirect(url_for('admin.newsletters'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating newsletter: {str(e)}", exc_info=True) # Add exc_info for full traceback
            flash('An error occurred. Please try again.', 'danger')
    else:
        if request.method == 'POST': # Only log errors if it was a POST request that failed validation
            current_app.logger.warning(f"form.validate_on_submit() was False. Errors: {form.errors}")
    
    return render_template('admin/newsletter_form.html', form=form, title='Create Newsletter')

@admin.route('/newsletters/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_newsletter(id):
    """Edit an existing newsletter"""
    newsletter = Newsletter.query.get_or_404(id)
    
    # Don't allow editing of sent newsletters
    if newsletter.status == 'Sent':
        flash('Sent newsletters cannot be edited.', 'warning')
        return redirect(url_for('admin.newsletters'))
    
    form = NewsletterForm(obj=newsletter)
    
    if form.validate_on_submit():
        # If status is 'Send Now', we'll treat it as 'Draft' for saving, then redirect.
        actual_status_to_save = 'Draft' if form.status.data == 'Send Now' else form.status.data

        newsletter.subject = form.subject.data
        newsletter.content = form.content.data
        newsletter.status = actual_status_to_save # Use adjusted status
        
        if actual_status_to_save == 'Scheduled' and form.scheduled_at.data:
            newsletter.scheduled_at = form.scheduled_at.data
        
        try:
            db.session.commit()
            
            flash(f'Newsletter "{form.subject.data}" has been updated.', 'success')
            
            # If status is "Send Now", send the newsletter immediately
            if form.status.data == 'Send Now':
                return redirect(url_for('admin.send_newsletter', id=newsletter.id))
            
            return redirect(url_for('admin.newsletters'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating newsletter: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin/newsletter_form.html', form=form, newsletter=newsletter, title='Edit Newsletter')

@admin.route('/newsletters/<int:id>/preview')
@login_required
@admin_required
def preview_newsletter(id):
    """Preview a newsletter"""
    newsletter = Newsletter.query.get_or_404(id)
    
    return render_template('admin/newsletter_preview.html', newsletter=newsletter)

@admin.route('/newsletters/<int:id>/send', methods=['GET', 'POST'])
@login_required
@admin_required
def send_newsletter(id):
    """Send a newsletter to all active subscribers"""
    newsletter = Newsletter.query.get_or_404(id)
    
    # Don't allow sending already sent newsletters
    if newsletter.status == 'Sent':
        flash('This newsletter has already been sent.', 'warning')
        return redirect(url_for('admin.newsletters'))
    
    if request.method == 'POST':
        active_subscribers = Subscriber.query.filter_by(is_active=True).all()
        
        if not active_subscribers:
            flash('No active subscribers to send to.', 'warning')
            # Redirect back to the confirmation page if no subscribers
            return redirect(url_for('admin.send_newsletter', id=newsletter.id))
        
        try:
            newsletter.status = 'Sending' # Set status to Sending
            db.session.commit() # Commit status change
            
            # Define batch_size here
            batch_size = 50 

            smtp_server = current_app.config['MAIL_SERVER']
            smtp_port = current_app.config['MAIL_PORT']
            smtp_username = current_app.config['MAIL_USERNAME']
            smtp_password = current_app.config['MAIL_PASSWORD']
            sender = current_app.config['MAIL_DEFAULT_SENDER']
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                
                # Send in batches - FIX HERE: Use correct slice syntax for each batch ahhhhhh! fixed
                for i in range(0, len(active_subscribers), batch_size):
                    batch = active_subscribers[i:i+batch_size]
                    
                    for subscriber in batch:
                        # Personalize newsletter content
                        content = newsletter.content
                        if subscriber.name:
                            content = content.replace('{{name}}', subscriber.name)
                        else:
                            content = content.replace('{{name}}', 'Valued Subscriber')
                        
                        # Add unsubscribe link
                        site_url = current_app.config['SITE_URL']
                        unsubscribe_link = f"{site_url}/unsubscribe?email={subscriber.email}"
                        content = content.replace('{{unsubscribe_link}}', unsubscribe_link)
                        
                        # Create and send email
                        msg = MIMEMultipart()
                        msg['From'] = sender
                        msg['To'] = subscriber.email
                        msg['Subject'] = newsletter.subject
                        msg.attach(MIMEText(content, 'html'))
                        
                        server.send_message(msg)
                        
                        # Record delivery
                        delivery = NewsletterDelivery(
                            newsletter_id=newsletter.id,
                            subscriber_id=subscriber.id,
                            delivered_at=datetime.utcnow()
                        )
                        db.session.add(delivery)
                
                # Update newsletter status
                newsletter.status = 'Sent'
                newsletter.sent_at = datetime.utcnow()
                db.session.commit()
                
                flash(f'Newsletter "{newsletter.subject}" has been sent to {len(active_subscribers)} subscribers.', 'success')
                return redirect(url_for('admin.newsletters'))
                
        except Exception as e:
            db.session.rollback() # Rollback any partial changes from the try block
            # Revert status to Draft on error to allow retrying/editing
            newsletter.status = 'Draft' 
            db.session.commit() # Commit the status revert

            current_app.logger.error(f"Error sending newsletter: {str(e)}")
            flash('An error occurred while sending the newsletter. Please try again.', 'danger')
            # Redirect back to the send confirmation page to show the error
            return redirect(url_for('admin.send_newsletter', id=newsletter.id))
    
    # For GET request (loading the confirmation page)
    active_count = Subscriber.query.filter_by(is_active=True).count()
    
    return render_template('admin/send_newsletter.html', 
                          newsletter=newsletter,
                          active_subscriber_count=active_count)


@admin.route('/newsletters/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_newsletter(id):
    """Delete a newsletter"""
    newsletter = Newsletter.query.get_or_404(id)
    
    # Don't allow deleting sent newsletters
    if newsletter.status == 'Sent':
        flash('Sent newsletters cannot be deleted.', 'warning')
        return redirect(url_for('admin.newsletters'))
    
    try:
        db.session.delete(newsletter)
        db.session.commit()
        flash(f'Newsletter "{newsletter.subject}" has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting newsletter: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin.newsletters'))

# Analytics
@admin.route('/analytics')
@login_required
@admin_required
def analytics():
    """Website traffic analytics dashboard"""
    # Date range filter
    days = request.args.get('days', 30, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date and end_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Using default date range.', 'warning')
            start_date = datetime.utcnow() - timedelta(days=days)
            end_date = datetime.utcnow()
    else:
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
    
    # Basic stats
    total_visits = PageVisit.query.filter(
        PageVisit.timestamp >= start_date,
        PageVisit.timestamp <= end_date
    ).count()
    
    # Unique visitors (by IP)
    unique_visitors = db.session.query(PageVisit.ip_address).filter(
        PageVisit.timestamp >= start_date,
        PageVisit.timestamp <= end_date
    ).distinct().count()
    
    # Daily visits
    daily_visits = db.session.query(
        func.date(PageVisit.timestamp).label('date'),
        func.count().label('count')
    ).filter(
        PageVisit.timestamp >= start_date,
        PageVisit.timestamp <= end_date
    ).group_by(
        func.date(PageVisit.timestamp)
    ).order_by(func.date(PageVisit.timestamp)).all()
    
    # Format for chart
    visit_dates = []
    for visit in daily_visits:
        if isinstance(visit.date, str):
            try:
                # Assuming visit.date is in 'YYYY-MM-DD' format from func.date()
                dt_obj = datetime.strptime(visit.date, '%Y-%m-%d').date()
                visit_dates.append(dt_obj.strftime('%Y-%m-%d'))
            except ValueError:
                current_app.logger.warning(f"Could not parse date string: {visit.date} in analytics. Using as is.")
                visit_dates.append(visit.date) # Use the string directly if parsing fails
        elif hasattr(visit.date, 'strftime'): # It's already a date/datetime object
            visit_dates.append(visit.date.strftime('%Y-%m-%d'))
        else:
            # Handle unexpected type or log an error
            current_app.logger.warning(f"Unexpected type for visit.date: {type(visit.date)}, value: {visit.date}")
            visit_dates.append(str(visit.date)) # Fallback to string conversion

    visit_counts = [visit.count for visit in daily_visits]
    
    # Top pages
    top_pages = db.session.query(
        PageVisit.page,
        func.count().label('count')
    ).filter(
        PageVisit.timestamp >= start_date,
        PageVisit.timestamp <= end_date
    ).group_by(
        PageVisit.page
    ).order_by(desc('count')).limit(20).all()
    
    # Top referrers
    top_referrers = db.session.query(
        PageVisit.referrer,
        func.count().label('count')
    ).filter(
        PageVisit.timestamp >= start_date,
        PageVisit.timestamp <= end_date,
        PageVisit.referrer != ''  # Exclude empty referrers
    ).group_by(
        PageVisit.referrer
    ).order_by(desc('count')).limit(10).all()
    
    raw_visit_counts = [visit.count for visit in daily_visits] # Renamed from visit_counts to avoid clash

    return render_template('admin/analytics.html',
                          total_visits=total_visits,
                          unique_visitors=unique_visitors,
                          days=days,
                          start_date=start_date.strftime('%Y-%m-%d'),
                          end_date=end_date.strftime('%Y-%m-%d'),
                          visit_dates_json=json.dumps(visit_dates), # Changed from visit_dates
                          visit_counts_json=json.dumps(raw_visit_counts), # Changed from visit_counts
                          visit_counts_raw=raw_visit_counts, # Added for direct sum
                          top_pages=top_pages,
                          top_referrers=top_referrers)

# User Management
@admin.route('/users')
@login_required
@admin_required
def users():
    """Manage admin users"""
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create a new admin user"""
    form = AdminUserUpdateForm() # Instantiate form for GET request
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on'
        
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin.create_user'))
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.create_user'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.create_user'))
        
        # Create new user
        user = User(username=username, email=email, is_admin=is_admin)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash(f'User {username} has been created.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin/user_form.html', title='Create User', form=form) # Pass form to template

@admin.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    """Edit an existing user"""
    user = User.query.get_or_404(id)
    form = AdminUserUpdateForm(obj=user)

    if form.validate_on_submit():
        # Check if username already exists (for a different user)
        existing_user_by_username = User.query.filter(User.username == form.username.data, User.id != id).first()
        if existing_user_by_username:
            flash('Username already exists.', 'danger')
            return render_template('admin/user_form.html', form=form, user=user, title='Edit User')
        
        # Check if email already exists (for a different user)
        existing_user_by_email = User.query.filter(User.email == form.email.data, User.id != id).first()
        if existing_user_by_email:
            flash('Email already exists.', 'danger')
            return render_template('admin/user_form.html', form=form, user=user, title='Edit User')

        user.username = form.username.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data

        # Update social media handles
        user.linkedin_url = form.linkedin_url.data
        user.twitter_url = form.twitter_url.data
        user.instagram_url = form.instagram_url.data
        user.facebook_url = form.facebook_url.data

        # Handle profile picture upload
        if form.profile_image.data:
            # Define profile picture upload folder
            profile_pics_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'profile_pics')
            os.makedirs(profile_pics_folder, exist_ok=True)

            # Delete old profile picture if it exists
            if user.profile_image_file:
                old_pic_path = os.path.join(profile_pics_folder, os.path.basename(user.profile_image_file))
                if os.path.exists(old_pic_path):
                    try:
                        os.remove(old_pic_path)
                    except Exception as e:
                        current_app.logger.error(f"Error deleting old profile picture {old_pic_path}: {str(e)}")
            
            # Save the new profile picture
            picture_file = form.profile_image.data
            picture_filename = secure_filename(f"user_{user.id}_{picture_file.filename}")
            picture_path = os.path.join(profile_pics_folder, picture_filename)
            
            try:
                picture_file.save(picture_path)
                # Store relative path from UPLOADS_FOLDER for consistency with other uploads if served via a common route
                # e.g., profile_pics/user_1_my_pic.jpg
                user.profile_image_file = os.path.join('profile_pics', picture_filename).replace('\\', '/')
            except Exception as e:
                current_app.logger.error(f"Error saving profile picture: {str(e)}")
                flash('Error uploading profile picture. Please try again.', 'danger')
        
        try:
            db.session.commit()
            flash(f'User {user.username} has been updated.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating user: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    # For GET requests, pass the form to the template
    form.username.data = user.username
    form.email.data = user.email
    form.is_admin.data = user.is_admin
    # Populate form with existing social media handles
    form.linkedin_url.data = user.linkedin_url
    form.twitter_url.data = user.twitter_url
    form.instagram_url.data = user.instagram_url
    form.facebook_url.data = user.facebook_url

    return render_template('admin/user_form.html', form=form, user=user, title="Edit User")

@admin.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    """Delete a user"""
    user = User.query.get_or_404(id)
    
    # Don't allow deleting your own account
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))
    
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin.users'))

# Scheduled task to send newsletters
# Scheduled task to send newsletters
def send_scheduled_newsletters():
    """Send all newsletters scheduled for now or earlier"""
    with current_app.app_context():
        now = datetime.utcnow()
        
        # Find newsletters scheduled for now or earlier that haven't been sent
        scheduled_newsletters = Newsletter.query.filter(
            Newsletter.status == 'Scheduled',
            Newsletter.scheduled_at <= now
        ).all()
        
        for newsletter in scheduled_newsletters:
            try:
                # Redirect to the send newsletter route
                current_app.logger.info(f"Sending scheduled newsletter: {newsletter.subject}")
                
                # Get all active subscribers
                active_subscribers = Subscriber.query.filter_by(is_active=True).all()
                
                if not active_subscribers:
                    current_app.logger.warning("No active subscribers to send newsletter to")
                    continue
                
                # Batch size to avoid overwhelming SMTP server
                batch_size = 50
                
                # Update newsletter status
                newsletter.status = 'Sending'
                db.session.commit()
                
                smtp_server = current_app.config['MAIL_SERVER']
                smtp_port = current_app.config['MAIL_PORT']
                smtp_username = current_app.config['MAIL_USERNAME']
                smtp_password = current_app.config['MAIL_PASSWORD']
                sender = current_app.config['MAIL_DEFAULT_SENDER']
                
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_username, smtp_password)
                    
                    # FIX: Remove duplicate loop and correctly slice each batch
                    for i in range(0, len(active_subscribers), batch_size):
                        batch = active_subscribers[i:i+batch_size]
                        
                        for subscriber in batch:
                            # Personalize newsletter content
                            content = newsletter.content
                            if subscriber.name:
                                content = content.replace('{{name}}', subscriber.name)
                            else:
                                content = content.replace('{{name}}', 'Valued Subscriber')
                            
                            # Add unsubscribe link with configurable domain
                            site_url = current_app.config.get('SITE_URL')
                            unsubscribe_link = f"{site_url}/unsubscribe?email={subscriber.email}"
                            content = content.replace('{{unsubscribe_link}}', unsubscribe_link)
                            
                            # Create and send email
                            msg = MIMEMultipart()
                            msg['From'] = sender
                            msg['To'] = subscriber.email
                            msg['Subject'] = newsletter.subject
                            msg.attach(MIMEText(content, 'html'))
                            
                            server.send_message(msg)
                            
                            # Record delivery
                            delivery = NewsletterDelivery(
                                newsletter_id=newsletter.id,
                                subscriber_id=subscriber.id,
                                delivered_at=datetime.utcnow()
                            )
                            db.session.add(delivery)
                
                # Update newsletter status
                newsletter.status = 'Sent'
                newsletter.sent_at = datetime.utcnow()
                db.session.commit()
                
                current_app.logger.info(f"Successfully sent scheduled newsletter: {newsletter.subject}")
                
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error sending scheduled newsletter: {str(e)}")


# Blog Management Routes
@admin.route('/blog')
@login_required
@admin_required
def blog_posts():
    """List all blog posts"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    # Base query
    query = BlogPost.query
    
    # Apply filters
    if status == 'published':
        query = query.filter_by(is_published=True)
    elif status == 'draft':
        query = query.filter_by(is_published=False)
    
    # Paginate results
    pagination = query.order_by(desc(BlogPost.created_at)).paginate(
        page=page, 
        per_page=current_app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    
    return render_template('admin/blog/posts.html', 
                          posts=pagination,
                          status=status)


@admin.route('/blog/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_blog_post():
    """Create a new blog post"""
    from forms.blog_forms import BlogPostForm
    
    form = BlogPostForm()
    
    # Load categories for the select field
    categories = BlogCategory.query.all()
    form.categories.choices = [(c.id, c.name) for c in categories]
    
    if form.validate_on_submit():
        # Generate slug if not provided
        slug = form.slug.data if form.slug.data else slugify(form.title.data)
        
        # Check for duplicate slug
        existing_post = BlogPost.query.filter_by(slug=slug).first()
        if existing_post:
            flash('A post with this slug already exists. Please choose a different slug.', 'danger')
            return render_template('admin/blog/create_edit_post.html', form=form, title='Create Post')
        
        # Handle featured image upload
        featured_image_path = None
        if form.featured_image.data:
            try:
                uploads_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'blog')
                os.makedirs(uploads_folder, exist_ok=True)
                
                filename = secure_filename(form.featured_image.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_feat_{filename}"
                
                filepath = os.path.join(uploads_folder, filename)
                form.featured_image.data.save(filepath)
                featured_image_path = os.path.join('blog', filename) # Store path relative to UPLOADS_FOLDER
            except Exception as e:
                current_app.logger.error(f"Error uploading featured image: {str(e)}")
                flash('Error uploading featured image. Please try again.', 'danger')

        # Handle hero background image upload
        hero_background_image_path = None
        if form.hero_background_image.data:
            try:
                hero_uploads_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'blog', 'hero_backgrounds')
                os.makedirs(hero_uploads_folder, exist_ok=True)
                
                hero_filename = secure_filename(form.hero_background_image.data.filename)
                hero_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                hero_filename = f"{hero_timestamp}_hero_{hero_filename}"
                
                hero_filepath = os.path.join(hero_uploads_folder, hero_filename)
                form.hero_background_image.data.save(hero_filepath)
                hero_background_image_path = os.path.join('blog', 'hero_backgrounds', hero_filename) # Store path relative to UPLOADS_FOLDER
            except Exception as e:
                current_app.logger.error(f"Error uploading hero background image: {str(e)}")
                flash('Error uploading hero background image. Please try again.', 'danger')
        
        # Create blog post
        post = BlogPost(
            title=form.title.data,
            slug=slug,
            excerpt=form.excerpt.data,
            content=form.content.data,
            featured_image=featured_image_path,
            hero_background_image=hero_background_image_path,
            is_published=form.is_published.data,
            author_id=current_user.id
        )
        
        # Add selected categories
        if form.categories.data:
            selected_categories = BlogCategory.query.filter(BlogCategory.id.in_(form.categories.data)).all()
            post.categories = selected_categories
        
        try:
            db.session.add(post)
            db.session.commit()
            flash('Blog post created successfully!', 'success')

            # Send notification to subscribers if post is published
            if post.is_published:
                try:
                    active_subscribers = Subscriber.query.filter_by(is_active=True).all()
                    if active_subscribers:
                        subscriber_emails = [s.email for s in active_subscribers]
                        send_new_post_notification(post, subscriber_emails)
                        flash(f'Notification sent to {len(subscriber_emails)} subscribers.', 'info')
                    else:
                        flash('Post created and published, but no active subscribers to notify.', 'info')
                except Exception as e:
                    current_app.logger.error(f"Error sending new post notification: {str(e)}")
                    flash('Blog post created, but failed to send notifications to subscribers.', 'warning')

            return redirect(url_for('admin.blog_posts'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating blog post: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin/blog/create_edit_post.html', form=form, title='Create Blog Post')


@admin.route('/blog/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_blog_post(id):
    """Edit an existing blog post"""
    from forms.blog_forms import BlogPostForm
    
    post = BlogPost.query.get_or_404(id)
    
    form = BlogPostForm(obj=post)
    
    # Load categories for the select field
    categories = BlogCategory.query.all()
    form.categories.choices = [(c.id, c.name) for c in categories]
    
    if request.method == 'GET':
        # Set the selected categories
        form.categories.data = [c.id for c in post.categories]
    
    if form.validate_on_submit():
        # Check if slug changed and if new slug is unique
        if form.slug.data != post.slug:
            existing_post = BlogPost.query.filter_by(slug=form.slug.data).first()
            if existing_post and existing_post.id != post.id:
                flash('A post with this slug already exists. Please choose a different slug.', 'danger')
                return render_template('admin/blog/create_edit_post.html', form=form, post=post, title='Edit Blog Post')
        
        # Handle featured image upload
        if form.featured_image.data and isinstance(form.featured_image.data, FileStorage):
            try:
                uploads_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'blog')
                os.makedirs(uploads_folder, exist_ok=True)
                
                filename = secure_filename(form.featured_image.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_feat_{filename}"
                
                filepath = os.path.join(uploads_folder, filename)
                form.featured_image.data.save(filepath)
                # Delete old image if exists and new one is uploaded
                if post.featured_image:
                    old_image_path = os.path.join(current_app.config['UPLOADS_FOLDER'], post.featured_image)
                    if os.path.exists(old_image_path):
                        try: os.remove(old_image_path)
                        except Exception as e: current_app.logger.error(f"Error deleting old featured image: {str(e)}")
                post.featured_image = os.path.join('blog', filename)
            except Exception as e:
                current_app.logger.error(f"Error uploading featured image: {str(e)}")
                flash('Error uploading featured image. The post will be updated without changing the featured image.', 'warning')
        
        # Handle hero background image upload
        if form.hero_background_image.data and isinstance(form.hero_background_image.data, FileStorage):
            try:
                hero_uploads_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'blog', 'hero_backgrounds')
                os.makedirs(hero_uploads_folder, exist_ok=True)
                hero_filename = secure_filename(form.hero_background_image.data.filename)
                hero_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                hero_filename = f"{hero_timestamp}_hero_{hero_filename}"
                hero_filepath = os.path.join(hero_uploads_folder, hero_filename)
                form.hero_background_image.data.save(hero_filepath)
                # Delete old hero image if exists and new one is uploaded
                if post.hero_background_image:
                    old_hero_image_path = os.path.join(current_app.config['UPLOADS_FOLDER'], post.hero_background_image)
                    if os.path.exists(old_hero_image_path):
                        try: os.remove(old_hero_image_path)
                        except Exception as e: current_app.logger.error(f"Error deleting old hero image: {str(e)}")
                post.hero_background_image = os.path.join('blog', 'hero_backgrounds', hero_filename)
            except Exception as e:
                current_app.logger.error(f"Error uploading hero background image: {str(e)}")
                flash('Error uploading hero background image. The post will be updated without changing the hero image.', 'warning')
        
        # Update post data
        post.title = form.title.data
        post.slug = form.slug.data
        post.excerpt = form.excerpt.data
        post.content = form.content.data
        post.is_published = form.is_published.data
        
        # Update categories
        if form.categories.data:
            selected_categories = BlogCategory.query.filter(BlogCategory.id.in_(form.categories.data)).all()
            post.categories = selected_categories
        else:
            post.categories = []
        
        try:
            db.session.commit()
            flash('Blog post updated successfully!', 'success')
            return redirect(url_for('admin.blog_posts'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating blog post: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin/blog/create_edit_post.html', form=form, post=post, title='Edit Blog Post')


@admin.route('/blog/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_blog_post(id):
    """Delete a blog post"""
    post = BlogPost.query.get_or_404(id)
    
    try:
        # Delete featured image if exists
        if post.featured_image and os.path.exists(post.featured_image):
            try:
                os.remove(post.featured_image)
            except Exception as e:
                current_app.logger.error(f"Error deleting image: {str(e)}")
        
        # Delete the post
        db.session.delete(post)
        db.session.commit()
        flash('Blog post deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting blog post: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin.blog_posts'))


# Blog Categories Management
@admin.route('/blog/categories')
@login_required
@admin_required
def blog_categories():
    """List all blog categories and provide form for creation/editing."""
    from forms.blog_forms import BlogCategoryForm # Import here
    
    edit_id = request.args.get('edit_id', type=int)
    category_to_edit = None
    
    if edit_id:
        category_to_edit = BlogCategory.query.get_or_404(edit_id)
        # Populate form for editing
        category_form = BlogCategoryForm(obj=category_to_edit)
    else:
        # Empty form for creating
        category_form = BlogCategoryForm()

    # For listing existing categories
    page = request.args.get('page', 1, type=int)
    categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
        page=page,
        per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), 
        error_out=False
    )
    
    return render_template('admin/blog/categories.html', 
                           categories=categories_pagination, 
                           category_form=category_form, # Pass the form
                           editing_category=category_to_edit)


@admin.route('/blog/categories/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_blog_category():
    """Create a new blog category"""
    from forms.blog_forms import BlogCategoryForm
    
    form = BlogCategoryForm() # This is for POST, GET is handled by blog_categories
    
    if form.validate_on_submit():
        name = form.name.data.strip()
        slug = form.slug.data.strip() if form.slug.data.strip() else slugify(name)

        if not name: # Should be caught by DataRequired, but as an extra check
            flash('Category name cannot be empty.', 'danger')
            # Re-render form (copied from below, consider refactoring this re-render logic)
            page = request.args.get('page', 1, type=int)
            categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
                page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
            )
            return render_template('admin/blog/categories.html', 
                                   categories=categories_pagination, 
                                   category_form=form, 
                                   editing_category=None)

        if not slug: # Check if slugify resulted in an empty string
            flash('Could not generate a valid slug from the category name. Please provide a valid name or a manual slug.', 'danger')
            page = request.args.get('page', 1, type=int)
            categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
                page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
            )
            return render_template('admin/blog/categories.html', 
                                   categories=categories_pagination, 
                                   category_form=form, 
                                   editing_category=None)

        # Check for duplicate name or slug
        existing_by_name = BlogCategory.query.filter_by(name=name).first()
        existing_by_slug = BlogCategory.query.filter_by(slug=slug).first()
        
        error_found = False
        if existing_by_name:
            flash(f'A category with the name \\"{name}\\" already exists.', 'danger')
            error_found = True
        if existing_by_slug and slug:
             flash(f'A category with the slug \\"{slug}\\" already exists.', 'danger')
             error_found = True

        if error_found:
            # If errors, re-render the main categories page with the form containing errors
            page = request.args.get('page', 1, type=int)
            categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
                page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
            )
            return render_template('admin/blog/categories.html', 
                                   categories=categories_pagination, 
                                   category_form=form, 
                                   editing_category=None)

        category = BlogCategory(
            name=name,
            slug=slug,
            description=form.description.data
        )
        
        try:
            db.session.add(category)
            db.session.commit()
            flash('Category created successfully!', 'success')
            return redirect(url_for('admin.blog_categories'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating category: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
            # Re-render the main categories page if save fails
            page = request.args.get('page', 1, type=int)
            categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
                page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
            )
            return render_template('admin/blog/categories.html', 
                                   categories=categories_pagination, 
                                   category_form=form, 
                                   editing_category=None)
    
    # If GET request, or POST failed basic validation (handled by WTForms on template)
    # redirect to the main categories view which handles displaying the form correctly.
    # This assumes the form on categories.html points its POST to this route.
    # For simplicity if GET, show the form on the main categories page.
    # A more robust way is to have blog_categories handle GET for the form,
    # and this route only handle POST.
    
    # If it's a GET request to /create, it's better to show the form on the categories page itself.
    # For now, if validate_on_submit is false (e.g. initial GET or WTForms error), show the main page.
    # The form's action in categories.html should point to this create_blog_category route for POST.
    page = request.args.get('page', 1, type=int)
    categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
    )
    # Pass the current form (which might have errors)
    return render_template('admin/blog/categories.html', categories=categories_pagination, category_form=form, editing_category=None)


@admin.route('/blog/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_blog_category(id):
    """Edit an existing blog category"""
    from forms.blog_forms import BlogCategoryForm
    
    category = BlogCategory.query.get_or_404(id)
    form = BlogCategoryForm(obj=category) # Populate with existing data for GET
    
    if form.validate_on_submit(): # This is for POST
        new_name = form.name.data.strip()
        new_slug = form.slug.data.strip() if form.slug.data.strip() else slugify(new_name)

        if not new_name: # Should be caught by DataRequired
            flash('Category name cannot be empty.', 'danger')
            page = request.args.get('page', 1, type=int)
            categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
                page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
            )
            return render_template('admin/blog/categories.html', 
                                   categories=categories_pagination, 
                                   category_form=form, 
                                   editing_category=category)

        if not new_slug: # Check if slugify resulted in an empty string
            flash('Could not generate a valid slug from the category name. Please provide a valid name or a manual slug.', 'danger')
            page = request.args.get('page', 1, type=int)
            categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
                page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
            )
            return render_template('admin/blog/categories.html', 
                                   categories=categories_pagination, 
                                   category_form=form, 
                                   editing_category=category)


        # Check if new name or slug conflicts with others
        query_name = BlogCategory.query.filter_by(name=new_name).filter(BlogCategory.id != id)
        query_slug = BlogCategory.query.filter_by(slug=new_slug).filter(BlogCategory.id != id)
        
        existing_by_name = query_name.first()
        existing_by_slug = query_slug.first()

        error_found = False
        if existing_by_name:
            flash(f'Another category with the name \\"{new_name}\\" already exists.', 'danger')
            error_found = True
        if existing_by_slug and new_slug:
             flash(f'Another category with the slug \\"{new_slug}\\" already exists.', 'danger')
             error_found = True
        
        if error_found:
            # If errors, re-render the main categories page with the form containing errors
            page = request.args.get('page', 1, type=int)
            categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
                page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
            )
            # Pass the current form (with errors) and the category being edited
            return render_template('admin/blog/categories.html', 
                                   categories=categories_pagination, 
                                   category_form=form, 
                                   editing_category=category)

        category.name = new_name
        category.slug = new_slug
        category.description = form.description.data
        
        try:
            db.session.commit()
            flash('Category updated successfully!', 'success')
            return redirect(url_for('admin.blog_categories'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating category: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
            # Re-render the main categories page if save fails
            page = request.args.get('page', 1, type=int)
            categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
                page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
            )
            return render_template('admin/blog/categories.html', 
                                   categories=categories_pagination, 
                                   category_form=form, 
                                   editing_category=category)
    
    # For GET request, the main blog_categories route now handles displaying the form.
    # This route (/edit) is primarily for the POST action of an edit.
    # For a GET to /edit, it's better to redirect to blog_categories with edit_id.
    if request.method == 'GET':
        return redirect(url_for('admin.blog_categories', edit_id=id, page=request.args.get('page',1)))

    # Fallback if POST but not validate_on_submit (e.g. CSRF error, though unlikely with hidden_tag)
    # Or if somehow reached with GET despite the redirect above.
    page = request.args.get('page', 1, type=int)
    categories_pagination = BlogCategory.query.order_by(BlogCategory.name).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE_SMALL', 10), error_out=False
    )
    return render_template('admin/blog/categories.html', categories=categories_pagination, category_form=form, editing_category=category)


@admin.route('/blog/categories/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_blog_category(id):
    """Delete a blog category"""
    category = BlogCategory.query.get_or_404(id)
    
    # Check if category is in use
    if category.posts:
        flash('Cannot delete category that is assigned to posts. Remove the category from all posts first.', 'danger')
        return redirect(url_for('admin.blog_categories'))
    
    try:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting category: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin.blog_categories'))


# Blog Comments Management
@admin.route('/blog/comments')
@login_required
@admin_required
def blog_comments():
    """List all blog comments"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'all')
    
    # Base query
    query = BlogComment.query
    
    # Apply filters
    if status == 'approved':
        query = query.filter_by(is_approved=True)
    elif status == 'pending':
        query = query.filter_by(is_approved=False)
    
    # Paginate results
    pagination = query.order_by(desc(BlogComment.created_at)).paginate(
        page=page, 
        per_page=current_app.config['ITEMS_PER_PAGE'],
        error_out=False
    )
    
    comments = pagination.items
    
    return render_template('admin/blog/comments.html', 
                          comments=comments,
                          pagination=pagination,
                          status=status)


@admin.route('/blog/comments/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_comment(id):
    """Approve a blog comment"""
    comment = BlogComment.query.get_or_404(id)
    
    comment.is_approved = True
    
    try:
        db.session.commit()
        flash('Comment approved successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving comment: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin.blog_comments'))


@admin.route('/blog/comments/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_comment(id):
    """Delete a blog comment"""
    comment = BlogComment.query.get_or_404(id)
    
    try:
        db.session.delete(comment)
        db.session.commit()
        flash('Comment deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting comment: {str(e)}")
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin.blog_comments'))

def send_new_post_notification(post, recipients):
    """Sends an email notification to a list of recipients about a new blog post."""
    if not recipients:
        return

    site_name = "Bolakin Educational Consult" # Or get from config
    post_url = url_for('main.blog_post', slug=post.slug, _external=True)

    subject = f"New Blog Post: {post.title}"
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ padding: 20px; border: 1px solid #ddd; border-radius: 5px; max-width: 600px; margin: 20px auto; }}
            h2 {{ color: #0056b3; }}
            p {{ margin-bottom: 10px; }}
            .button {{
                display: inline-block; padding: 10px 20px; margin-top:15px; 
                background-color: #FF9933; color: #ffffff; text-decoration: none; border-radius: 5px;
            }}
            .footer {{ font-size: 0.9em; color: #777; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>New Blog Post on {site_name}!</h2>
            <p>Hello,</p>
            <p>We've just published a new article that you might find interesting:</p>
            <h3>{post.title}</h3>
            
            <p>{post.excerpt if post.excerpt else 'Click below to read more.'}</p>
            
            <a href="{post_url}" class="button">Read Full Article</a>
            
            <div class="footer">
                <p>You are receiving this email because you subscribed to updates from {site_name}.</p>
                <!-- Consider adding a generic unsubscribe link or link to manage preferences -->
            </div>
        </div>
    </body>
    </html>
    """

    # Using a BCC approach for multiple recipients is better for privacy
    # However, smtplib direct send_message usually takes one 'To'. 
    # For multiple individual emails, loop or use a proper mailing library for batching.
    # For now, sending one by one for simplicity, but this is not efficient for large lists.
    
    current_app.logger.info(f"Attempting to send new post notification for '{post.title}' to {len(recipients)} recipients.")
    emails_sent_count = 0
    try:
        smtp_server = current_app.config['MAIL_SERVER']
        smtp_port = current_app.config['MAIL_PORT']
        smtp_username = current_app.config['MAIL_USERNAME']
        smtp_password = current_app.config['MAIL_PASSWORD']
        sender = current_app.config['MAIL_DEFAULT_SENDER']

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            for recipient_email in recipients:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = sender
                    msg['To'] = recipient_email
                    msg['Subject'] = subject
                    msg.attach(MIMEText(html_body, 'html'))
                    server.send_message(msg)
                    emails_sent_count += 1
                except Exception as e_indiv:
                    current_app.logger.error(f"Failed to send new post email to {recipient_email}: {str(e_indiv)}")
            current_app.logger.info(f"New post notification sent to {emails_sent_count}/{len(recipients)} recipients.")

    except Exception as e_smtp:
        current_app.logger.error(f"SMTP error during new post notification: {str(e_smtp)}")
        raise # Re-raise to be caught by the caller to flash a general error message

# slugify utility needs to be defined or imported
# from utils.helpers import slugify # Ensure this is available

# Helper for slugifying text (if not using a separate utility file)
_punct_re = re.compile(r'[\t !"#$%&\'()*\[\],./:;<=>?@\^_`{|}~-]+')
def slugify(text, delim='-'):
    """Generates an ASCII-only slug."""
    result = []
    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore').decode('utf-8')
        if word:
            result.append(word)
    return delim.join(result)

# Need to import re and unicodedata.normalize for slugify if defined here
from unicodedata import normalize

# Helper function to save newsletter content images
def save_newsletter_image(file):
    """Saves an image uploaded from the newsletter editor."""
    try:
        # Define a specific subfolder for newsletter content images
        newsletter_images_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'newsletter_content_images')
        os.makedirs(newsletter_images_folder, exist_ok=True)

        # Generate a secure, unique filename
        filename = secure_filename(file.filename)
        # Add a timestamp or unique ID to prevent overwrites and ensure uniqueness
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f') # microseconds for better uniqueness
        unique_filename = f"{timestamp}_{filename}"
        
        filepath = os.path.join(newsletter_images_folder, unique_filename)
        file.save(filepath)
        
        # Return the URL path for the image
        # This will be served by the existing 'uploaded_file' route or a similar one.
        # The path should be relative to the UPLOADS_FOLDER.
        # url_path = os.path.join('newsletter_content_images', unique_filename).replace('\\\\', '/') # Old way
        # return url_for('main.uploaded_file', subpath=url_path, _external=True) # Old way
        
        # New way: Use the public route. It expects just the filename.
        return url_for('main.public_newsletter_image', filename=unique_filename, _external=True)
    except Exception as e:
        current_app.logger.error(f"Error saving newsletter image: {str(e)}")
        return None

@admin.route('/upload_newsletter_image', methods=['POST'])
@login_required
@admin_required
def upload_newsletter_image():
    """Endpoint for Summernote image uploads."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        # You might want to add more robust validation here (file type, size)
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif'}
        filename, ext = os.path.splitext(file.filename)
        if ext.lower() not in allowed_extensions:
            return jsonify({'error': 'File type not allowed'}), 400

        image_url = save_newsletter_image(file)
        if image_url:
            # Summernote expects just the URL of the image in the response body for success
            return image_url 
        else:
            return jsonify({'error': 'Could not save image'}), 500
            
    return jsonify({'error': 'Unknown error'}), 500

# Helper function to save images uploaded via CKEditor
def save_ckeditor_image(file):
    """Saves an image uploaded from CKEditor's SimpleUploadAdapter."""
    try:
        # Define a specific subfolder for blog content images
        blog_content_images_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'blog_content_images')
        os.makedirs(blog_content_images_folder, exist_ok=True)

        # Generate a secure, unique filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f') # microseconds for better uniqueness
        unique_filename = f"{timestamp}_{filename}"
        
        filepath = os.path.join(blog_content_images_folder, unique_filename)
        file.save(filepath)
        
        # Return the URL path for the image, served by a new public route
        # This assumes a route like 'main.public_blog_content_image' will handle serving these.
        image_url = url_for('main.public_blog_content_image', filename=unique_filename, _external=True)
        return image_url, unique_filename
    except Exception as e:
        current_app.logger.error(f"Error saving CKEditor image: {str(e)}")
        return None, None

@admin.route('/upload-ckeditor-image', methods=['POST'])
@login_required
@admin_required
def upload_ckeditor_image():
    """Endpoint for CKEditor 5 SimpleUploadAdapter image uploads."""
    file = request.files.get('upload') # CKEditor's SimpleUploadAdapter sends the file with the key 'upload'

    if not file:
        return jsonify({'error': {'message': 'No file uploaded.'}}), 400

    # Basic validation (can be expanded)
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    filename, ext = os.path.splitext(file.filename)
    if ext.lower() not in allowed_extensions:
        return jsonify({'error': {'message': 'Invalid image type.'}}), 400

    # Add file size validation if needed
    # max_size = 2 * 1024 * 1024 # 2MB
    # if file.content_length > max_size:
    #     return jsonify({'error': {'message': 'File too large.'}}), 400

    image_url, unique_filename = save_ckeditor_image(file)

    if image_url:
        return jsonify({
            'uploaded': 1,
            'fileName': unique_filename,
            'url': image_url
        })
    else:
        return jsonify({'error': {'message': 'Could not save image. Check server logs.'}}), 500

# Helper function to save images uploaded via Blog Post Summernote editor
def save_blog_image(file):
    """Saves an image uploaded from Summernote for blog posts."""
    try:
        # Define a specific subfolder for blog content images
        blog_content_images_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'blog_content_images')
        os.makedirs(blog_content_images_folder, exist_ok=True)

        # Generate a secure, unique filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f') # microseconds for better uniqueness
        unique_filename = f"{timestamp}_{filename}"
        
        filepath = os.path.join(blog_content_images_folder, unique_filename)
        file.save(filepath)
        
        # Return the URL path for the image, served by the existing public blog content image route
        image_url = url_for('main.public_blog_content_image', filename=unique_filename, _external=True)
        return image_url
    except Exception as e:
        current_app.logger.error(f"Error saving blog image for Summernote: {str(e)}")
        return None

@admin.route('/upload-blog-image', methods=['POST'])
@login_required
@admin_required
def upload_blog_image():
    """Endpoint for Summernote image uploads in blog post editor."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request.'}), 400 # Return JSON for Summernote to parse error
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file.'}), 400
    
    if file:
        # Basic validation (can be expanded)
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        filename, ext = os.path.splitext(file.filename)
        if ext.lower() not in allowed_extensions:
            return jsonify({'error': 'Invalid image type. Allowed: png, jpg, jpeg, gif, webp.'}), 400

        # Add file size validation if needed (example: 5MB)
        # max_size = 5 * 1024 * 1024 
        # if file.content_length > max_size:
        #     return jsonify({'error': 'File too large (max 5MB).'}), 400

        image_url = save_blog_image(file)

        if image_url:
            # Summernote expects the URL directly in the response body for success
            return image_url
        else:
            return jsonify({'error': 'Could not save image. Check server logs.'}), 500
            
    return jsonify({'error': 'Unknown error during blog image upload.'}), 500

# Visa Requests Management
@admin.route('/visa-requests')
@login_required
@admin_required
def visa_requests_list():
    page = request.args.get('page', 1, type=int)
    requests = VisaRequest.query.order_by(desc(VisaRequest.submission_date)).paginate(page=page, per_page=15)
    return render_template('admin/services/visa_requests_list.html', 
                           title='Visa Processing Requests', 
                           requests=requests)

@admin.route('/visa-request/<int:request_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def visa_request_details(request_id):
    visa_req = VisaRequest.query.get_or_404(request_id)
    form = UpdateVisaRequestStatusForm(obj=visa_req)
    if form.validate_on_submit():
        try:
            visa_req.status = form.status.data
            visa_req.admin_notes = form.admin_notes.data
            db.session.commit()
            flash('Visa request status updated successfully.', 'success')
            return redirect(url_for('admin.visa_requests_list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating visa request status: {e}")
            flash('An error occurred while updating status. Please try again.', 'danger')
    return render_template('admin/services/visa_request_details.html', visa_req=visa_req, form=form, title="Visa Request Details")

# Flight Booking Management
@admin.route('/flight-bookings')
@login_required
@admin_required
def flight_bookings_list():
    page = request.args.get('page', 1, type=int)
    flight_bookings = FlightBookingRequest.query.order_by(desc(FlightBookingRequest.submission_date)).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 15), error_out=False
    )
    return render_template('admin/services/flight_bookings_list.html', flight_bookings=flight_bookings, title="Flight Booking Requests")

@admin.route('/flight-booking/<int:request_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def flight_booking_details(request_id):
    booking_req = FlightBookingRequest.query.get_or_404(request_id)
    form = UpdateFlightBookingRequestStatusForm(obj=booking_req)
    if form.validate_on_submit():
        try:
            booking_req.status = form.status.data
            booking_req.admin_notes = form.admin_notes.data
            db.session.commit()
            flash('Flight booking request status updated successfully.', 'success')
            return redirect(url_for('admin.flight_bookings_list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating flight booking status: {e}")
            flash('An error occurred while updating status. Please try again.', 'danger')
    return render_template('admin/services/flight_booking_details.html', booking_req=booking_req, form=form, title="Flight Booking Request Details")

# Proof of Funds Requests Management
@admin.route('/proof-of-funds-requests')
@login_required
@admin_required
def proof_of_funds_requests_list():
    page = request.args.get('page', 1, type=int)
    pof_requests = ProofOfFundsRequest.query.order_by(desc(ProofOfFundsRequest.submission_date)).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 15), error_out=False
    )
    return render_template('admin/services/proof_of_funds_list.html', pof_requests=pof_requests, title="Proof of Funds Requests")

@admin.route('/proof-of-funds-request/<int:request_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def proof_of_funds_request_details(request_id):
    pof_req = ProofOfFundsRequest.query.get_or_404(request_id)
    form = UpdateProofOfFundsRequestStatusForm(obj=pof_req)
    if form.validate_on_submit():
        try:
            pof_req.status = form.status.data
            pof_req.admin_notes = form.admin_notes.data
            db.session.commit()
            flash('Proof of Funds request status updated successfully.', 'success')
            return redirect(url_for('admin.proof_of_funds_requests_list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating Proof of Funds request status: {e}")
            flash('An error occurred while updating status. Please try again.', 'danger')
    return render_template('admin/services/proof_of_funds_details.html', pof_req=pof_req, form=form, title="Proof of Funds Request Details")

# Holiday Package Requests Management
@admin.route('/holiday-package-requests')
@login_required
@admin_required
def holiday_package_requests_list():
    page = request.args.get('page', 1, type=int)
    package_requests = HolidayPackageRequest.query.order_by(desc(HolidayPackageRequest.submission_date)).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 15), error_out=False
    )
    return render_template('admin/services/holiday_package_requests_list.html', package_requests=package_requests, title="Holiday Package Requests")

@admin.route('/holiday-package-request/<int:request_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def holiday_package_request_details(request_id):
    package_req = HolidayPackageRequest.query.get_or_404(request_id)
    form = UpdateHolidayPackageRequestStatusForm(obj=package_req)
    if form.validate_on_submit():
        try:
            package_req.status = form.status.data
            package_req.admin_notes = form.admin_notes.data
            db.session.commit()
            flash('Holiday Package request status updated successfully.', 'success')
            return redirect(url_for('admin.holiday_package_requests_list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating Holiday Package request status: {e}")
            flash('An error occurred while updating status. Please try again.', 'danger')
    return render_template('admin/services/holiday_package_request_details.html', package_req=package_req, form=form, title="Holiday Package Request Details")

# Hotel Accommodation Requests Management
@admin.route('/hotel-accommodation-requests')
@login_required
@admin_required
def hotel_accommodation_requests_list():
    page = request.args.get('page', 1, type=int)
    hotel_requests = HotelAccommodationRequest.query.order_by(desc(HotelAccommodationRequest.submission_date)).paginate(
        page=page, per_page=current_app.config.get('ITEMS_PER_PAGE', 15), error_out=False
    )
    return render_template('admin/services/hotel_accommodation_requests_list.html', hotel_requests=hotel_requests, title="Hotel/Accommodation Requests")

@admin.route('/hotel-accommodation-request/<int:request_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def hotel_accommodation_request_details(request_id):
    hotel_req = HotelAccommodationRequest.query.get_or_404(request_id)
    form = UpdateHotelAccommodationRequestStatusForm(obj=hotel_req)
    if form.validate_on_submit():
        try:
            hotel_req.status = form.status.data
            hotel_req.admin_notes = form.admin_notes.data
            db.session.commit()
            flash('Hotel/Accommodation request status updated successfully.', 'success')
            return redirect(url_for('admin.hotel_accommodation_requests_list'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating Hotel/Accommodation request status: {e}")
            flash('An error occurred while updating status. Please try again.', 'danger')
    return render_template('admin/services/hotel_accommodation_request_details.html', hotel_req=hotel_req, form=form, title="Hotel/Accommodation Request Details")