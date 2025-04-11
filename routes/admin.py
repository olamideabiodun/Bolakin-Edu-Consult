from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from werkzeug.utils import secure_filename
from models import db, User, Subscriber, AdmissionApplication, Newsletter, NewsletterDelivery, PageVisit
from forms.newsletter_form import NewsletterForm
from datetime import datetime, timedelta
import os
import csv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps
import io
import json

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
    
    # Format for chart - handle both string and datetime types
    visit_dates = []
    visit_counts = []
    
    for visit in daily_visits:
        # Check if visit.date is already a string
        if isinstance(visit.date, str):
            visit_dates.append(visit.date)
        else:
            # It's a datetime object, use strftime
            visit_dates.append(visit.date.strftime('%Y-%m-%d'))
        
        visit_counts.append(visit.count)
    
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
    
    if form.validate_on_submit():
        newsletter = Newsletter(
            subject=form.subject.data,
            content=form.content.data,
            status=form.status.data,
            created_by=current_user.id
        )
        
        if form.status.data == 'Scheduled' and form.scheduled_at.data:
            newsletter.scheduled_at = form.scheduled_at.data
        
        try:
            db.session.add(newsletter)
            db.session.commit()
            
            flash(f'Newsletter "{form.subject.data}" has been created.', 'success')
            
            # If status is "Send Now", send the newsletter immediately
            if form.status.data == 'Send Now':
                return redirect(url_for('admin.send_newsletter', id=newsletter.id))
            
            return redirect(url_for('admin.newsletters'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating newsletter: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
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
        newsletter.subject = form.subject.data
        newsletter.content = form.content.data
        newsletter.status = form.status.data
        
        if form.status.data == 'Scheduled' and form.scheduled_at.data:
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
        # Get all active subscribers
        active_subscribers = Subscriber.query.filter_by(is_active=True).all()
        
        if not active_subscribers:
            flash('No active subscribers to send to.', 'warning')
            return redirect(url_for('admin.newsletters'))
        
        # Batch size to avoid overwhelming SMTP server
        batch_size = 50
        
        try:
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
            db.session.rollback()
            current_app.logger.error(f"Error sending newsletter: {str(e)}")
            flash('An error occurred while sending the newsletter. Please try again.', 'danger')
    
    # Count active subscribers
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
    visit_dates = [visit.date.strftime('%Y-%m-%d') for visit in daily_visits]
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
    
    return render_template('admin/analytics.html',
                          total_visits=total_visits,
                          unique_visitors=unique_visitors,
                          days=days,
                          start_date=start_date.strftime('%Y-%m-%d'),
                          end_date=end_date.strftime('%Y-%m-%d'),
                          visit_dates=json.dumps(visit_dates),
                          visit_counts=json.dumps(visit_counts),
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
    
    return render_template('admin/user_form.html', title='Create User')

@admin.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    """Edit an existing user"""
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        is_admin = request.form.get('is_admin') == 'on'
        new_password = request.form.get('new_password')
        
        if not username or not email:
            flash('Username and email are required.', 'danger')
            return redirect(url_for('admin.edit_user', id=id))
        
        # Check if username already exists (for a different user)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != id:
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.edit_user', id=id))
        
        # Check if email already exists (for a different user)
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != id:
            flash('Email already exists.', 'danger')
            return redirect(url_for('admin.edit_user', id=id))
        
        # Update user
        user.username = username
        user.email = email
        user.is_admin = is_admin
        
        # Update password if provided
        if new_password:
            user.set_password(new_password)
        
        try:
            db.session.commit()
            flash(f'User {username} has been updated.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating user: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin/user_form.html', user=user, title='Edit User')

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
    
    posts = pagination.items
    
    return render_template('admin/blog/posts.html', 
                          posts=posts,
                          pagination=pagination,
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
            return render_template('admin/blog/form.html', form=form, title='Create Post')
        
        # Handle featured image upload
        featured_image_path = None
        if form.featured_image.data:
            try:
                uploads_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'blog')
                os.makedirs(uploads_folder, exist_ok=True)
                
                # Save the file
                filename = secure_filename(form.featured_image.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                filepath = os.path.join(uploads_folder, filename)
                form.featured_image.data.save(filepath)
                
                # Store the relative path
                featured_image_path = os.path.join('uploads', 'blog', filename)
            except Exception as e:
                current_app.logger.error(f"Error uploading featured image: {str(e)}")
                flash('Error uploading image. Please try again.', 'danger')
        
        # Create blog post
        post = BlogPost(
            title=form.title.data,
            slug=slug,
            excerpt=form.excerpt.data,
            content=form.content.data,
            featured_image=featured_image_path,
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
            return redirect(url_for('admin.blog_posts'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating blog post: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin/blog/form.html', form=form, title='Create Blog Post')


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
                return render_template('admin/blog/form.html', form=form, post=post, title='Edit Blog Post')
        
        # Handle featured image upload
        if form.featured_image.data:
            try:
                uploads_folder = os.path.join(current_app.config['UPLOADS_FOLDER'], 'blog')
                os.makedirs(uploads_folder, exist_ok=True)
                
                # Save the file
                filename = secure_filename(form.featured_image.data.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                filepath = os.path.join(uploads_folder, filename)
                form.featured_image.data.save(filepath)
                
                # Delete old image if exists
                if post.featured_image and os.path.exists(post.featured_image):
                    try:
                        os.remove(post.featured_image)
                    except Exception as e:
                        current_app.logger.error(f"Error deleting old image: {str(e)}")
                
                # Store the relative path
                post.featured_image = os.path.join('uploads', 'blog', filename)
            except Exception as e:
                current_app.logger.error(f"Error uploading featured image: {str(e)}")
                flash('Error uploading image. The post will be updated without changing the image.', 'warning')
        
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
    
    return render_template('admin/blog/form.html', form=form, post=post, title='Edit Blog Post')


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
    """List all blog categories"""
    categories = BlogCategory.query.order_by(BlogCategory.name).all()
    return render_template('admin/blog/categories.html', categories=categories)


@admin.route('/blog/categories/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_blog_category():
    """Create a new blog category"""
    from forms.blog_forms import BlogCategoryForm
    
    form = BlogCategoryForm()
    
    if form.validate_on_submit():
        # Check for duplicate slug
        existing_category = BlogCategory.query.filter_by(slug=form.slug.data).first()
        if existing_category:
            flash('A category with this slug already exists. Please choose a different slug.', 'danger')
            return render_template('admin/blog/category_form.html', form=form, title='Create Category')
        
        # Create category
        category = BlogCategory(
            name=form.name.data,
            slug=form.slug.data,
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
    
    return render_template('admin/blog/category_form.html', form=form, title='Create Category')


@admin.route('/blog/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_blog_category(id):
    """Edit an existing blog category"""
    from forms.blog_forms import BlogCategoryForm
    
    category = BlogCategory.query.get_or_404(id)
    form = BlogCategoryForm(obj=category)
    
    if form.validate_on_submit():
        # Check if slug changed and if new slug is unique
        if form.slug.data != category.slug:
            existing_category = BlogCategory.query.filter_by(slug=form.slug.data).first()
            if existing_category:
                flash('A category with this slug already exists. Please choose a different slug.', 'danger')
                return render_template('admin/blog/category_form.html', form=form, category=category, title='Edit Category')
        
        # Update category
        category.name = form.name.data
        category.slug = form.slug.data
        category.description = form.description.data
        
        try:
            db.session.commit()
            flash('Category updated successfully!', 'success')
            return redirect(url_for('admin.blog_categories'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating category: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin/blog/category_form.html', form=form, category=category, title='Edit Category')


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