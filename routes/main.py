from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from models import db, Subscriber, AdmissionApplication
from forms.subscriber_form import SubscriberForm
from forms.admission_form import AdmissionForm
import os
import tempfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from flask import current_app

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
    # Get the post by slug
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    
    # Process form
    from forms.blog_forms import BlogCommentForm
    form = BlogCommentForm()
    
    if form.validate_on_submit():
        comment = BlogComment(
            content=form.content.data,
            author_name=form.author_name.data,
            author_email=form.author_email.data,
            post_id=post.id,
            is_approved=False  # Comments require approval
        )
        
        try:
            db.session.add(comment)
            db.session.commit()
            flash('Your comment has been submitted and is pending approval.', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting comment: {str(e)}")
            flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('main.blog_post', slug=slug))


@main.route('/gallery')
def gallery():
    """Gallery page"""
    return render_template('gallery.html')


@main.route('/about')
def about():
    """About page"""
    return render_template('about.html')


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
            current_app.logger.warning("No email found in request")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'Email is required'}), 400
            flash('Email is required', 'error')
            return redirect(request.referrer or url_for('main.index'))
        
        # Validate email format
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            current_app.logger.warning(f"Invalid email format: {email}")
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
    uploads_folder = current_app.config['UPLOADS_FOLDER']
    relative_path = os.path.relpath(filepath, uploads_folder)
    
    return os.path.join(uploads_folder, relative_path)

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
            email_sent = False
            try:
                send_application_notification(application)
                email_sent = True
                current_app.logger.info(f"Notification email sent for application ID: {application.id}")
            except Exception as e:
                current_app.logger.error(f"Error sending notification email: {str(e)}")
                # Continue even if email fails - the application is saved
            
            response_message = 'Application submitted successfully'
            if not email_sent:
                response_message += ', but there was an issue sending the notification email. Your application has been saved and will be reviewed.'
                
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