from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_from_directory
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from models import db, Subscriber, AdmissionApplication, BlogPost, BlogCategory, BlogComment, User, VisaRequest, FlightBookingRequest, ProofOfFundsRequest, HolidayPackageRequest, HotelAccommodationRequest
from forms.subscriber_form import SubscriberForm
from forms.admission_form import AdmissionForm
from forms.service_forms import VisaRequestForm, FlightBookingRequestForm, ProofOfFundsRequestForm, HolidayPackageRequestForm, HotelAccommodationRequestForm
import os
import tempfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from flask import current_app
from sqlalchemy import desc

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Home page"""
    subscription_status = request.args.get('subscription')
    return render_template('admission.html', subscription_status=subscription_status)



@main.route('/blog')
def blog():
    """Blog listing page"""
    page = request.args.get('page', 1, type=int)
    category_slug = request.args.get('category')
    
    # Base query
    query = BlogPost.query.filter_by(is_published=True)
    
    # Apply category filter if specified
    category = None
    if category_slug:
        category = BlogCategory.query.filter_by(slug=category_slug).first_or_404()
        query = query.filter(BlogPost.categories.contains(category))
    
    # Paginate results
    pagination = query.order_by(desc(BlogPost.created_at)).paginate(
        page=page,
        per_page=6,  # Show 6 posts per page
        error_out=False
    )
    
    posts = pagination.items
    
    # Get all categories for sidebar
    categories = BlogCategory.query.all()
    
    # Get recent posts for sidebar
    recent_posts = BlogPost.query.filter_by(is_published=True).order_by(
        desc(BlogPost.created_at)
    ).limit(5).all()
    
    # Get popular posts
    popular_posts = BlogPost.query.filter_by(is_published=True).order_by(
        desc(BlogPost.views_count)
    ).limit(5).all()
    
    return render_template('blog/index.html', 
                          posts=posts,
                          pagination=pagination,
                          categories=categories,
                          current_category=category,
                          recent_posts=recent_posts,
                          popular_posts=popular_posts)


@main.route('/blog/<string:slug>')
def blog_post(slug):
    """Single blog post page"""
    # Get the post by slug
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    
    # Increment view count
    post.increment_view()
    
    # Get comments for this post
    comments = BlogComment.query.filter_by(post_id=post.id, is_approved=True).order_by(
        BlogComment.created_at
    ).all()
    
    # Comment form
    from forms.blog_forms import BlogCommentForm
    form = BlogCommentForm()

    if current_user.is_authenticated:
        form.author_name.data = current_user.username # Or current_user.full_name if you have it
        form.author_email.data = current_user.email
    
    # Get categories for sidebar
    categories = BlogCategory.query.all()
    
    # Get recent posts for sidebar
    recent_posts = BlogPost.query.filter_by(is_published=True).order_by(
        desc(BlogPost.created_at)
    ).limit(5).all()
    
    # Get related posts (same category)
    related_posts = []
    if post.categories:
        category_ids = [c.id for c in post.categories]
        related_posts = BlogPost.query.filter(
            BlogPost.is_published == True,
            BlogPost.id != post.id,
            BlogPost.categories.any(BlogCategory.id.in_(category_ids))
        ).order_by(desc(BlogPost.created_at)).limit(3).all()
    
    # If not enough related posts by category, get recent posts
    if len(related_posts) < 3:
        more_posts = BlogPost.query.filter(
            BlogPost.is_published == True,
            BlogPost.id != post.id,
            ~BlogPost.id.in_([p.id for p in related_posts])
        ).order_by(desc(BlogPost.created_at)).limit(3 - len(related_posts)).all()
        related_posts.extend(more_posts)
    
    return render_template('blog/post.html',
                          post=post,
                          comments=comments,
                          form=form,
                          categories=categories,
                          recent_posts=recent_posts,
                          related_posts=related_posts)


@main.route('/blog/<string:slug>/comment', methods=['POST'])
def blog_post_comment(slug):
    """Handle comment submission"""
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    from forms.blog_forms import BlogCommentForm
    form = BlogCommentForm()

    author_to_save = None
    email_to_save = None
    content_to_save = None
    is_valid_submission = False
    current_app.logger.info(f"Comment submission attempt for post: {slug}. Authenticated: {current_user.is_authenticated}")


    if current_user.is_authenticated:
        author_to_save = current_user.username
        email_to_save = current_user.email
        
        # For authenticated users, we primarily care about the content field.
        # Name and email are sourced directly from current_user.
        # We will validate form.content directly.
        if form.content.validate(form): # Check only content validation
            content_to_save = form.content.data
            is_valid_submission = True
            current_app.logger.info("Content validated successfully for authenticated user.")
        else:
            current_app.logger.warning(f"Content validation failed for authenticated user. Errors: {form.content.errors}")
            # Flash content errors
            error_messages = []
            if form.content.errors:
                for error in form.content.errors:
                    error_messages.append(f"Comment content: {error}")
            
            # Also check other form errors, in case something unexpected happened with csrf or other form-level issues
            # but don't let name/email validation (which we override) block submission.
            other_errors = {k: v for k, v in form.errors.items() if k != 'content' and k != 'author_name' and k != 'author_email'}
            if other_errors:
                current_app.logger.warning(f"Other form errors for authenticated user: {other_errors}")
                for field_name, field_errors in other_errors.items():
                    label = getattr(form, field_name).label.text if hasattr(getattr(form, field_name), 'label') else field_name
                    for error in field_errors:
                        error_messages.append(f"{label}: {error}")
            
            if error_messages:
                flash("Please correct the following errors: " + "; ".join(error_messages), 'danger')
            else:
                # This case implies form.content.validate(form) was false but form.content.errors was empty,
                # and no other critical form errors. Unlikely, but possible if a validator raises StopValidation without errors.
                flash('There was an issue with your comment submission. Please check the content.', 'danger')

    else:  # Anonymous user
        current_app.logger.info("Comment submission attempt by anonymous user.")
        if form.validate_on_submit():
            author_to_save = form.author_name.data
            email_to_save = form.author_email.data
            content_to_save = form.content.data
            is_valid_submission = True
            current_app.logger.info("Form validated successfully for anonymous user.")
        else:
            current_app.logger.warning(f"Form validation failed for anonymous user. Errors: {form.errors}")
            # Flash all errors for anonymous user since we are redirecting
            error_messages = []
            for field_name, field_errors in form.errors.items():
                label = getattr(form, field_name).label.text if hasattr(getattr(form, field_name), 'label') else field_name
                for error in field_errors:
                    error_messages.append(f"{label}: {error}")
            if error_messages:
                flash("Please correct the following errors: " + "; ".join(error_messages), 'danger')
            else: # Should ideally not happen if validate_on_submit is false
                flash('There was an issue with your comment. Please try again.', 'danger')

    if is_valid_submission:
        current_app.logger.info(f"Attempting to save comment: Author - {author_to_save}, Email - {email_to_save[:5]}... (masked)")
        try:
            comment = BlogComment(
                content=content_to_save,
                author_name=author_to_save,
                author_email=email_to_save,
                post_id=post.id,
                is_approved=False  # Comments require approval
            )
            current_app.logger.info("BlogComment object created. Attempting to add to session.")
            db.session.add(comment)
            current_app.logger.info("Attempting to commit session.")
            db.session.commit()
            current_app.logger.info("Comment saved successfully and committed to database.")
            flash('Your comment has been submitted and is pending approval.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting comment to database: {str(e)}", exc_info=True)
            flash('An error occurred while submitting your comment. Please try again.', 'danger')
    else:
        current_app.logger.info("Comment submission was not valid. No database action taken.")
    
    return redirect(url_for('main.blog_post', slug=slug, _anchor='comment-form'))


@main.route('/gallery')
def gallery():
    """Gallery page"""
    return render_template('gallery.html')


@main.route('/about')
def about():
    """About page"""
    admin_user = User.query.filter_by(is_admin=True).first()
    return render_template('about.html', admin_user=admin_user)


@main.route('/appointment', methods=['GET', 'POST'])
def appointment():
    """Appointment booking page"""
    if request.method == 'POST':
        # In a real app, this would save to a database
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        preferred_country = request.form.get('preferred_country')
        message = request.form.get('message')
        
        # Process the appointment booking (would send email notifications, etc.)
        # For now, just redirect to a thank you page
        return redirect(url_for('main.thank_you'))
    
    return render_template('appointment.html')


@main.route('/thank-you')
def thank_you():
    """Thank you page after form submission"""
    return render_template('thank_you.html')


@main.route('/country/<country_name>')
def country_details(country_name):
    """Country details page"""
    # This would fetch specific details about the selected country
    # from a database in a real implementation
    return render_template('country_details.html', country=country_name)

@main.route('/subscribe', methods=['POST', 'GET'])
def subscribe():
    """
    Handle newsletter subscription.
    Supports both AJAX and form submissions.
    Handles various content types and data formats.
    """
    # Debug logging
    current_app.logger.info(f"Subscribe route accessed with method: {request.method}")
    current_app.logger.info(f"URL: {request.url}")
    current_app.logger.info(f"Headers: {dict(request.headers)}")
    
    # For GET requests - either return a form or redirect
    if request.method == 'GET':
        current_app.logger.info("GET request to subscribe endpoint")
        # If AJAX, return message
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'This endpoint requires a POST request'}), 405
        # Otherwise redirect to home page
        return redirect(url_for('main.index'))
    
    # Process POST request
    try:
        # Log all possible data sources
        current_app.logger.info(f"Form data: {request.form}")
        current_app.logger.info(f"JSON data: {request.get_json(silent=True)}")
        current_app.logger.info(f"Content type: {request.content_type}")
        
        # Extract email and name from various possible sources
        email = None
        name = ''
        
        # Try form data (application/x-www-form-urlencoded or multipart/form-data)
        if request.form:
            email = request.form.get('email')
            name = request.form.get('name', '')
            current_app.logger.info(f"Extracted from form: email={email}, name={name}")
        
        # Try JSON data (application/json)
        elif request.is_json:
            json_data = request.get_json()
            if json_data:
                email = json_data.get('email')
                name = json_data.get('name', '')
                current_app.logger.info(f"Extracted from JSON: email={email}, name={name}")
        
        # Try request body as raw text (might be malformed JSON or custom format)
        elif request.data:
            try:
                import json
                data = json.loads(request.data.decode('utf-8'))
                email = data.get('email')
                name = data.get('name', '')
                current_app.logger.info(f"Extracted from raw data: email={email}, name={name}")
            except json.JSONDecodeError:
                # Try to parse as URL-encoded form data
                from urllib.parse import parse_qs
                data = parse_qs(request.data.decode('utf-8'))
                email = data.get('email', [None])[0]
                name = data.get('name', [''])[0]
                current_app.logger.info(f"Extracted from parsed data: email={email}, name={name}")
        
        # Validate email
        if not email:
            current_app.logger.warning("No email found in request for /subscribe. Returning 400.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Email is required'}), 400
            flash('Email is required', 'error')
            return redirect(request.referrer or url_for('main.index'))
        
        # Validate email format
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            current_app.logger.warning(f"Invalid email format: {email} for /subscribe. Returning 400.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Invalid email format'}), 400
            flash('Invalid email format', 'error')
            return redirect(request.referrer or url_for('main.index'))
        
        # Check if subscriber already exists
        existing_subscriber = Subscriber.query.filter_by(email=email).first()
        
        if existing_subscriber:
            if not existing_subscriber.is_active:
                # Reactivate subscriber
                existing_subscriber.is_active = True
                existing_subscriber.name = name if name else existing_subscriber.name  # Update name if provided
                db.session.commit()
                current_app.logger.info(f"Reactivated subscriber: {email}")
                
                # Respond appropriately
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True, 
                        'message': 'Your subscription has been reactivated!'
                    })
                flash('Your subscription has been reactivated!', 'success')
                return redirect(request.referrer + '?subscription=reactivated' if request.referrer else url_for('main.index', subscription='reactivated'))
            else:
                # Already subscribed
                current_app.logger.info(f"Existing active subscriber: {email}")
                
                # Respond appropriately
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False, 
                        'message': 'You are already subscribed!'
                    })
                flash('You are already subscribed!', 'info')
                return redirect(request.referrer or url_for('main.index'))
        else:
            # Add new subscriber
            try:
                new_subscriber = Subscriber(email=email, name=name)
                db.session.add(new_subscriber)
                db.session.commit()
                current_app.logger.info(f"Added new subscriber: {email}")
                
                # Try to send confirmation emails (don't block if they fail)
                try:
                    send_admin_notification(email)
                    send_subscriber_confirmation(email)
                    current_app.logger.info(f"Confirmation emails sent for: {email}")
                except Exception as email_error:
                    current_app.logger.error(f"Error sending confirmation emails: {str(email_error)}")
                    # Continue processing - don't block the subscription
                
                # Respond appropriately
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': True, 
                        'message': 'Thank you for subscribing to our newsletter!'
                    })
                flash('Thank you for subscribing to our newsletter!', 'success')
                return redirect(request.referrer + '?subscription=success' if request.referrer else url_for('main.index', subscription='success'))
            
            except Exception as db_error:
                db.session.rollback()
                current_app.logger.error(f"Database error adding subscriber: {str(db_error)}")
                
                # Respond appropriately
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False, 
                        'message': 'A database error occurred. Please try again later.'
                    }), 500
                flash('A database error occurred. Please try again later.', 'error')
                return redirect(request.referrer or url_for('main.index'))
    
    except Exception as e:
        # Catch-all for any other errors
        current_app.logger.error(f"Unexpected error in subscribe route: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        
        # Respond appropriately
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False, 
                'message': 'An unexpected error occurred. Please try again later.'
            }), 500
        flash('An unexpected error occurred. Please try again later.', 'error')
        return redirect(request.referrer or url_for('main.index'))

@main.route('/unsubscribe')
def unsubscribe():
    """Handle newsletter unsubscription"""
    email = request.args.get('email')
    
    if not email:
        return render_template('unsubscribe.html', message='Invalid request')
    
    # Find subscriber
    subscriber = Subscriber.query.filter_by(email=email).first()
    
    if not subscriber:
        return render_template('unsubscribe.html', message='Email not found in our database')
    
    # Deactivate subscription
    subscriber.is_active = False
    db.session.commit()
    
    return render_template('unsubscribe.html', email=email, message='You have been successfully unsubscribed')



# Helper functions for email sending
def send_admin_notification(email):
    """Send notification email to admin about new subscriber"""
    admin_email = current_app.config['ADMIN_EMAIL']
    
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = admin_email
    msg['Subject'] = 'New Newsletter Subscription'
    
    email_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            h2 {{ color: #FF9933; }}
        </style>
    </head>
    <body>
        <h2>New Newsletter Subscription</h2>
        <p>A new user has subscribed to your newsletter:</p>
        <p><strong>Email:</strong> {email}</p>
        <p>You can view all subscribers in the <a href="https://yourdomain.com/admin/subscribers">admin dashboard</a>.</p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(email_body, 'html'))
    
    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)


def send_subscriber_confirmation(email):
    """Send confirmation email to new subscriber"""
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = email
    msg['Subject'] = 'Welcome to Bolakin Educational Consult Newsletter'
    
    subscriber_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            h2 {{ color: #FF9933; }}
        </style>
    </head>
    <body>
        <h2>Welcome to Our Newsletter!</h2>
        <p>Thank you for subscribing to the Bolakin Educational Consult newsletter.</p>
        <p>You'll now receive updates about our services, educational opportunities, and special offers.</p>
        <p>If you have any questions, feel free to contact us!</p>
        <p>Best regards,<br>The Bolakin Educational Consult Team</p>
        <p style="font-size: 12px; color: #666;">If you didn't subscribe to our newsletter, you can <a href="https://yourdomain.com/unsubscribe?email={email}">unsubscribe here</a>.</p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(subscriber_body, 'html'))
    
    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)


def send_application_notification(application):
    """Send notification about new admission application"""
    try:
        admin_email = current_app.config['ADMIN_EMAIL']
        
        msg = MIMEMultipart()
        msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = admin_email
        msg['Subject'] = f'New Admission Application: {application.full_name}'
        
        email_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                h2 {{ color: #FF9933; }}
                .section {{ margin-bottom: 20px; }}
                .label {{ font-weight: bold; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h2>New Admission Application</h2>
            
            <div class="section">
                <h3>Personal Information</h3>
                <table>
                    <tr><td class="label">Full Name:</td><td>{application.full_name}</td></tr>
                    <tr><td class="label">Email:</td><td>{application.email}</td></tr>
                    <tr><td class="label">Phone:</td><td>{application.phone}</td></tr>
                    <tr><td class="label">Date of Birth:</td><td>{application.dob}</td></tr>
                    <tr><td class="label">Gender:</td><td>{application.gender}</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h3>Academic Background</h3>
                <table>
                    <tr><td class="label">Previous Institution:</td><td>{application.prev_institution}</td></tr>
                    <tr><td class="label">Qualification:</td><td>{application.qualification}</td></tr>
                    <tr><td class="label">Year of Graduation:</td><td>{application.grad_year}</td></tr>
                    <tr><td class="label">GPA/Grade:</td><td>{application.gpa}</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h3>Program Selection</h3>
                <table>
                    <tr><td class="label">Preferred Course:</td><td>{application.course}</td></tr>
                    <tr><td class="label">Study Mode:</td><td>{application.study_mode}</td></tr>
                    <tr><td class="label">Campus:</td><td>{application.campus or 'Not specified'}</td></tr>
                </table>
            </div>
            
            <p>Please review this application in the <a href="{current_app.config['SITE_URL']}/admin/dashboard/applications/{application.id}">admin dashboard</a>.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(email_body, 'html'))
        
        # Attach files if available
        file_paths = [
            (application.id_document, "ID Document"),
            (application.transcript, "Transcript"),
            (application.passport_photo, "Passport Photo")
        ]
        
        for file_path, file_desc in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        filename = os.path.basename(file_path)
                        attachment = MIMEApplication(f.read(), _subtype="octet-stream")
                        attachment.add_header('Content-Disposition', 'attachment', 
                                            filename=f"{file_desc}-{application.full_name}-{filename}")
                        msg.attach(attachment)
                except Exception as e:
                    current_app.logger.error(f"Error attaching file {file_path}: {str(e)}")
        
        # Configure SMTP with explicit error logging
        try:
            smtp_server = current_app.config['MAIL_SERVER']
            smtp_port = current_app.config['MAIL_PORT']
            smtp_username = current_app.config['MAIL_USERNAME']
            smtp_password = current_app.config['MAIL_PASSWORD']
            
            current_app.logger.info(f"Connecting to SMTP server: {smtp_server}:{smtp_port}")
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.set_debuglevel(1)  # Enable SMTP debug output
                server.ehlo()  # Identify ourselves to the server
                server.starttls()
                server.ehlo()  # Re-identify ourselves over TLS connection
                
                current_app.logger.info("Attempting SMTP login")
                server.login(smtp_username, smtp_password)
                
                current_app.logger.info(f"Sending email to {admin_email}")
                server.send_message(msg)
                current_app.logger.info("Email sent successfully")
                
                return True
        except smtplib.SMTPAuthenticationError as e:
            current_app.logger.error(f"SMTP Authentication Error: {str(e)}")
            raise Exception(f"SMTP Authentication failed: {str(e)}")
        except smtplib.SMTPException as e:
            current_app.logger.error(f"SMTP Error: {str(e)}")
            raise Exception(f"SMTP Error: {str(e)}")
        except Exception as e:
            current_app.logger.error(f"Unexpected error during SMTP connection: {str(e)}")
            raise
    except Exception as e:
        current_app.logger.error(f"Error in send_application_notification: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        raise



def validate_file(file, allowed_extensions, max_size_mb=5):
    """
    Validate uploaded file
    Args:
        file: The uploaded file object
        allowed_extensions: List of allowed file extensions (e.g. ['.pdf', '.jpg'])
        max_size_mb: Maximum allowed file size in megabytes
    
    Returns:
        tuple: (is_valid, message) - A boolean indicating if file is valid and an error message if not
    """
    # Check if file exists
    if not file or file.filename == '':
        return False, "No file selected"
    
    # Check file extension
    filename = secure_filename(file.filename)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
    
    # Check file size (max_size_mb in MB)
    max_size_bytes = max_size_mb * 1024 * 1024
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset file pointer
    
    if file_size > max_size_bytes:
        return False, f"File size exceeds {max_size_mb}MB limit"
    
    # For images, verify the file is actually an image using file signatures
    if ext in ['.jpg', '.jpeg', '.png', '.gif']:
        try:
            # Read enough data to determine file type
            header = file.read(512)
            file.seek(0)  # Reset file pointer
            
            # Check image file signatures
            is_valid_image = False
            if ext == '.jpg' or ext == '.jpeg':
                # JPEG signature starts with bytes FF D8 FF
                is_valid_image = header.startswith(b'\xff\xd8\xff')
            elif ext == '.png':
                # PNG signature is 89 50 4E 47 0D 0A 1A 0A
                is_valid_image = header.startswith(b'\x89PNG\r\n\x1a\n')
            elif ext == '.gif':
                # GIF signature starts with 'GIF87a' or 'GIF89a'
                is_valid_image = header.startswith(b'GIF87a') or header.startswith(b'GIF89a')
            
            if not is_valid_image:
                return False, "Invalid image file format"
        except Exception:
            return False, "Could not verify image file"
    
    return True, "File is valid"

def save_file(file, directory, filename=None):
    """
    Safely save an uploaded file
    
    Args:
        file: The uploaded file object
        directory: Directory to save the file in
        filename: Optional custom filename (will use secure_filename of original if not provided)
    
    Returns:
        str: Path to the saved file relative to the application
    """
    if not filename:
        filename = secure_filename(file.filename)
    else:
        # Preserve extension
        original_ext = os.path.splitext(secure_filename(file.filename))[1]
        filename = secure_filename(filename) + original_ext
    
    # Ensure directory exists
    os.makedirs(directory, exist_ok=True)
    
    # Generate full path
    filepath = os.path.join(directory, filename)
    
    # Save file
    file.save(filepath)
    
    # Return relative path from application root
    path_to_store = os.path.join(os.path.basename(directory), filename)
    return path_to_store.replace('\\', '/')

# Use in the submit_admission route


@main.route('/submit-admission', methods=['POST'])
def submit_admission():
    """Handle admission application submission"""
    if request.method == 'POST':
        try:
            # Get form data
            full_name = request.form.get('fullName')
            email = request.form.get('email')
            phone = request.form.get('phone')
            dob_str = request.form.get('dob')
            gender = request.form.get('gender')
            
            # Validate required fields
            if not all([full_name, email, phone, dob_str, gender]):
                return jsonify({'success': False, 'message': 'Please fill all required fields'})
            
            # Rest of form data
            prev_institution = request.form.get('prevInstitution')
            qualification = request.form.get('qualification')
            grad_year = request.form.get('gradYear')
            gpa = request.form.get('gpa')
            course = request.form.get('course')
            study_mode = request.form.get('studyMode')
            campus = request.form.get('campus')
            agreement = request.form.get('agreement')
            
            # Parse date of birth
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid date format for Date of Birth'})
            
            # Create new application in database
            application = AdmissionApplication(
                full_name=full_name,
                email=email,
                phone=phone,
                dob=dob,
                gender=gender,
                prev_institution=prev_institution,
                qualification=qualification,
                grad_year=grad_year,
                gpa=gpa,
                course=course,
                study_mode=study_mode,
                campus=campus
            )
            
            # Process file uploads and save to application record
            uploads_folder = current_app.config['UPLOADS_FOLDER']
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
            
            # Create specific folder for this application
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            applicant_folder = os.path.join(uploads_folder, f"{email}_{timestamp}")
            
            # Handle file uploads with validation
            file_mappings = {
                'idUpload': 'id_document',
                'transcriptUpload': 'transcript',
                'photoUpload': 'passport_photo'
            }
            
            # Ensure uploads folder exists
            if not os.path.exists(uploads_folder):
                os.makedirs(uploads_folder, exist_ok=True)
            
            # Ensure applicant folder exists
            if not os.path.exists(applicant_folder):
                os.makedirs(applicant_folder, exist_ok=True)
                
            for file_key, db_field in file_mappings.items():
                if file_key in request.files:
                    file = request.files[file_key]
                    if file.filename:
                        # Validate file
                        is_valid, message = validate_file(file, allowed_extensions, max_size_mb=5)
                        if not is_valid:
                            return jsonify({'success': False, 'message': f"{file_key}: {message}"})
                        
                        # Save file
                        file_path = save_file(file, applicant_folder)
                        setattr(application, db_field, file_path)
            
            # Save application to database
            db.session.add(application)
            db.session.commit()
            current_app.logger.info(f"Application saved to database with ID: {application.id}")
            
            # Send email notification to admin
            admin_email_sent = False
            try:
                send_application_notification(application)
                admin_email_sent = True
                current_app.logger.info(f"Admin notification email sent for application ID: {application.id}")
            except Exception as e:
                current_app.logger.error(f"Error sending admin notification email: {str(e)}")
                # Continue even if admin email fails - the application is saved

            # Send confirmation email to applicant
            applicant_email_sent = False
            try:
                send_applicant_confirmation(application)
                applicant_email_sent = True
                current_app.logger.info(f"Applicant confirmation email sent for application ID: {application.id} to {application.email}")
            except Exception as e:
                current_app.logger.error(f"Error sending applicant confirmation email: {str(e)}")
                # Continue even if applicant email fails
            
            response_message = 'Application submitted successfully'
            if not admin_email_sent and not applicant_email_sent:
                response_message += '. However, we encountered an issue sending email notifications. Your application has been saved and will be reviewed.'
            elif not admin_email_sent:
                response_message += '. An email confirmation has been sent to you. There was an issue notifying the admin, but your application is saved.'
            elif not applicant_email_sent:
                response_message += '. The admin has been notified. There was an issue sending you a confirmation email, but your application is saved.'
            else:
                response_message += '. An email confirmation has been sent to you, and the admin has been notified.'

            return jsonify({
                'success': True, 
                'message': response_message,
                'applicationId': application.id
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing admission form: {str(e)}")
            import traceback
            current_app.logger.error(traceback.format_exc())
            return jsonify({'success': False, 'message': 'An error occurred while processing your application. Please try again or contact support.'})
    
    return jsonify({'success': False, 'message': 'Invalid request method'})

def send_applicant_confirmation(application):
    """Send confirmation email to applicant"""
    msg = MIMEMultipart()
    msg['From'] = current_app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = application.email
    msg['Subject'] = 'Your Admission Application to Bolakin Educational Consult has been Received'
    
    applicant_body = f"""
    Dear {application.full_name},

    Thank you for submitting your admission application to Bolakin Educational Consult.

    We have successfully received your application (ID: {application.id}) for the {application.course} program.
    Our admissions team will review your submission carefully.

    We will get back to you soon regarding the status of your application. 
    If you have any urgent questions, please feel free to contact us.

    Best regards,
    The Bolakin Educational Consult Team
    {current_app.config['SITE_URL']}
    """
    # Using HTML for better formatting, similar to other emails
    html_applicant_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            h2 {{ color: #0056b3; /* Bolakin Blue */ }}
            p {{ margin-bottom: 10px; }}
            .footer {{ font-size: 0.9em; color: #777; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }}
            .logo-text {{ font-weight: bold; color: #FF9933; /* Bolakin Orange */ }}
        </style>
    </head>
    <body>
        <h2>Application Received: Bolakin Educational Consult</h2>
        <p>Dear {application.full_name},</p>
        <p>Thank you for submitting your admission application to <span class="logo-text">Bolakin Educational Consult</span>.</p>
        <p>We have successfully received your application (ID: <strong>{application.id}</strong>) for the <strong>{application.course}</strong> program.</p>
        <p>Our admissions team will review your submission carefully. We appreciate your patience during this process.</p>
        <p>We will get back to you soon regarding the status of your application. If you have any urgent questions in the meantime, please do not hesitate to contact us.</p>
        <p>Best regards,</p>
        <p><strong>The Bolakin Educational Consult Team</strong></p>
        <div class="footer">
            <p><a href="{current_app.config['SITE_URL']}">{current_app.config['SITE_URL']}</a></p>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_applicant_body, 'html')) # Changed to html_applicant_body and 'html'
    
    # SMTP Sending logic (same as other email functions)
    try:
        smtp_server = current_app.config['MAIL_SERVER']
        smtp_port = current_app.config['MAIL_PORT']
        smtp_username = current_app.config['MAIL_USERNAME']
        smtp_password = current_app.config['MAIL_PASSWORD']
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            current_app.logger.info(f"Applicant confirmation email successfully sent to {application.email}")
    except smtplib.SMTPAuthenticationError as e:
        current_app.logger.error(f"SMTP Authentication Error for applicant email ({application.email}): {str(e)}")
        raise # Re-raise to be caught by the caller in submit_admission
    except Exception as e:
        current_app.logger.error(f"General SMTP Error for applicant email ({application.email}): {str(e)}")
        raise # Re-raise

@main.route('/uploads/<path:subpath>')
@login_required
def uploaded_file(subpath):
    upload_dir_name = current_app.config['UPLOADS_FOLDER'] # This is 'uploads'
    absolute_upload_dir = os.path.abspath(upload_dir_name)

    # Normalize slashes first (e.g. db_pathile.pdf -> db_path/file.pdf)
    normalized_subpath_slashes = subpath.replace('\\', '/')

    # Use os.path.normpath to resolve any '.' or '..' segments AFTER initial slash normalization
    # and to get OS-specific separators if needed internally by subsequent os.path calls,
    # though for string manipulation, we'll stick to '/'
    temp_normalized_path = os.path.normpath(normalized_subpath_slashes)

    # Convert back to forward slashes for consistent string operations
    # and remove any leading './' that normpath might produce or was already there.
    cleaned_subpath = temp_normalized_path.replace('\\', '/').lstrip('./')
    
    path_for_send_from_directory = cleaned_subpath
    
    # Check if the cleaned_subpath (from DB) incorrectly starts with the UPLOADS_FOLDER name itself
    # e.g., if DB has 'uploads/email_timestamp/file.pdf' instead of 'email_timestamp/file.pdf'
    # This handles old data. New data saved by corrected save_file shouldn't have this.
    if cleaned_subpath.startswith(upload_dir_name + '/'):
        path_for_send_from_directory = cleaned_subpath[len(upload_dir_name + '/'):]
    
    # Final check: ensure path doesn't start with a slash if it's meant to be relative to absolute_upload_dir
    path_for_send_from_directory = path_for_send_from_directory.lstrip('/')

    # Security check for path traversal 
    # (send_from_directory is generally safe, but this adds an explicit layer)
    # Check against components to be robust
    if '..' in path_for_send_from_directory.split('/'):
        current_app.logger.warning(f"Path traversal attempt detected in uploaded_file. Original subpath: '{subpath}', Processed path: '{path_for_send_from_directory}'")
        return jsonify({'success': False, 'message': 'Invalid path'}), 400
        
    current_app.logger.info(f"Attempting to serve file. Base directory: '{absolute_upload_dir}', Relative path: '{path_for_send_from_directory}'")
    try:
        return send_from_directory(absolute_upload_dir, path_for_send_from_directory, as_attachment=False)
    except Exception as e:
        current_app.logger.error(f"Error serving file. Base: '{absolute_upload_dir}', Path: '{path_for_send_from_directory}'. Error: {str(e)}")
        # Consider a more specific check for NotFound from werkzeug.exceptions if you want to distinguish
        # from other errors, though a generic 404 is often fine.
        return jsonify({'success': False, 'message': 'File not found or an error occurred while serving the file.'}), 404

# New public route for newsletter images
@main.route('/public_uploads/newsletter_content_images/<path:filename>')
def public_newsletter_image(filename):
    """Serves publicly accessible images for newsletters."""
    # Construct the correct directory path
    # UPLOADS_FOLDER is 'uploads'. We need 'uploads/newsletter_content_images'
    directory = os.path.join(current_app.config['UPLOADS_FOLDER'], 'newsletter_content_images')
    absolute_directory = os.path.abspath(directory)
    
    current_app.logger.info(f"Attempting to serve public newsletter image. Base directory: '{absolute_directory}', Filename: '{filename}'")
    try:
        return send_from_directory(absolute_directory, filename, as_attachment=False)
    except Exception as e:
        current_app.logger.error(f"Error serving public newsletter image. Base: '{absolute_directory}', Filename: '{filename}'. Error: {str(e)}")
        return jsonify({'success': False, 'message': 'Image not found or an error occurred.'}), 404

@main.route('/public_uploads/blog_content_images/<path:filename>')
def public_blog_content_image(filename):
    """Serves publicly accessible images for blog content uploaded via CKEditor."""
    # Construct the correct directory path
    # UPLOADS_FOLDER is 'uploads'. We need 'uploads/blog_content_images'
    directory = os.path.join(current_app.config['UPLOADS_FOLDER'], 'blog_content_images')
    absolute_directory = os.path.abspath(directory)
    
    current_app.logger.info(f"Attempting to serve public blog content image. Base directory: '{absolute_directory}', Filename: '{filename}'")
    try:
        return send_from_directory(absolute_directory, filename, as_attachment=False)
    except Exception as e:
        current_app.logger.error(f"Error serving public blog content image. Base: '{absolute_directory}', Filename: '{filename}'. Error: {str(e)}")
        # Consistent error response with other image serving routes
        return jsonify({'success': False, 'message': 'Image not found or an error occurred.'}), 404

@main.route('/visa-processing', methods=['GET', 'POST'])
def visa_processing_request():
    form = VisaRequestForm()
    if form.validate_on_submit():
        try:
            visa_request = VisaRequest(
                full_name=form.full_name.data,
                email=form.email.data,
                phone=form.phone.data,
                destination_country=form.destination_country.data,
                visa_type=form.visa_type.data if form.visa_type.data != 'Other' else form.other_visa_type.data,
                preferred_appointment_date=form.preferred_appointment_date.data,
                message=form.message.data
            )
            db.session.add(visa_request)
            db.session.commit()
            flash('Your visa processing request has been submitted successfully!', 'success')
            # TODO: Send email notification to admin and user
            return redirect(url_for('main.visa_processing_request'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting visa request: {e}")
            flash('An error occurred while submitting your request. Please try again.', 'danger')
    return render_template('services/visa_processing.html', form=form, title="Visa Processing Request")

@main.route('/flight-booking', methods=['GET', 'POST'])
def flight_booking_request():
    form = FlightBookingRequestForm()
    if form.validate_on_submit():
        try:
            booking_request = FlightBookingRequest(
                full_name=form.full_name.data,
                email=form.email.data,
                phone=form.phone.data,
                departure_city=form.departure_city.data,
                arrival_city=form.arrival_city.data,
                departure_date=form.departure_date.data,
                return_date=form.return_date.data,
                trip_type=form.trip_type.data,
                adults=form.adults.data,
                children=form.children.data,
                infants=form.infants.data,
                cabin_class=form.cabin_class.data,
                flexible_dates=form.flexible_dates.data,
                message=form.message.data
            )
            db.session.add(booking_request)
            db.session.commit()
            flash('Your flight booking request has been submitted successfully!', 'success')
            # TODO: Send email notification to admin and user
            return redirect(url_for('main.flight_booking_request'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting flight booking request: {e}")
            flash('An error occurred while submitting your request. Please try again.', 'danger')
    return render_template('services/flight_booking.html', form=form, title="Flight Booking Request")

@main.route('/proof-of-funds', methods=['GET', 'POST'])
def proof_of_funds_request():
    form = ProofOfFundsRequestForm()
    if form.validate_on_submit():
        try:
            pof_request = ProofOfFundsRequest(
                full_name=form.full_name.data,
                email=form.email.data,
                phone=form.phone.data,
                service_type=form.service_type.data,
                purpose=form.purpose.data,
                destination_country=form.destination_country.data,
                amount_required=form.amount_required.data,
                timeline=form.timeline.data,
                message=form.message.data
            )
            db.session.add(pof_request)
            db.session.commit()
            flash('Your Proof of Funds request has been submitted successfully!', 'success')
            # TODO: Send email notification
            return redirect(url_for('main.proof_of_funds_request'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting Proof of Funds request: {e}")
            flash('An error occurred while submitting your request. Please try again.', 'danger')
    return render_template('services/proof_of_funds.html', form=form, title="Proof of Funds Request")

@main.route('/holiday-package', methods=['GET', 'POST'])
def holiday_package_request():
    form = HolidayPackageRequestForm()
    if form.validate_on_submit():
        try:
            package_req = HolidayPackageRequest(
                full_name=form.full_name.data,
                email=form.email.data,
                phone=form.phone.data,
                destination=form.destination.data,
                travel_dates_flexible=form.travel_dates_flexible.data,
                preferred_start_date=form.preferred_start_date.data,
                preferred_end_date=form.preferred_end_date.data,
                duration_days=form.duration_days.data, # Model expects Integer, form gives String. Needs conversion.
                num_adults=form.num_adults.data,
                num_children=form.num_children.data,
                package_type=form.package_type.data,
                interests=form.interests.data,
                budget_preference=form.budget_preference.data,
                message=form.message.data
            )
            # Convert duration_days to integer if provided
            if package_req.duration_days:
                try:
                    # Attempt to extract first number if string like "7 days"
                    import re
                    match = re.search(r'\d+', str(package_req.duration_days))
                    if match:
                        package_req.duration_days = int(match.group(0))
                    else:
                        package_req.duration_days = None # Or handle error
                except ValueError:
                    package_req.duration_days = None # Or handle error / flash message
            else:
                package_req.duration_days = None

            db.session.add(package_req)
            db.session.commit()
            flash('Your Holiday Package request has been submitted successfully!', 'success')
            # TODO: Send email notification
            return redirect(url_for('main.holiday_package_request'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting Holiday Package request: {e}")
            flash('An error occurred while submitting your request. Please try again.', 'danger')
    return render_template('services/holiday_package.html', form=form, title="Holiday Package Request")

@main.route('/hotel-accommodation', methods=['GET', 'POST'])
def hotel_accommodation_request():
    form = HotelAccommodationRequestForm()
    if form.validate_on_submit():
        if form.check_out_date.data <= form.check_in_date.data:
            flash('Check-out date must be after check-in date.', 'danger')
        else:
            try:
                hotel_req = HotelAccommodationRequest(
                    full_name=form.full_name.data,
                    email=form.email.data,
                    phone=form.phone.data,
                    destination_city_hotel=form.destination_city_hotel.data,
                    check_in_date=form.check_in_date.data,
                    check_out_date=form.check_out_date.data,
                    num_adults=form.num_adults.data,
                    num_children=form.num_children.data,
                    num_rooms=form.num_rooms.data,
                    hotel_preferences=form.hotel_preferences.data,
                    room_type_preference=form.room_type_preference.data,
                    budget_per_night=form.budget_per_night.data,
                    special_requests=form.special_requests.data
                )
                db.session.add(hotel_req)
                db.session.commit()
                flash('Your Hotel/Accommodation request has been submitted successfully!', 'success')
                # TODO: Send email notification
                return redirect(url_for('main.hotel_accommodation_request'))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error submitting Hotel Accommodation request: {e}")
                flash('An error occurred while submitting your request. Please try again.', 'danger')
    return render_template('services/hotel_accommodation.html', form=form, title="Hotel & Accommodation Request")

# Placeholder for other service routes to be added later...