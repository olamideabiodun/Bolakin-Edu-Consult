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

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Home page"""
    subscription_status = request.args.get('subscription')
    return render_template('admission.html', subscription_status=subscription_status)


@main.route('/blog')
def blog():
    """Blog listing page"""
    # This would be connected to a database in a real implementation
    blog_posts = [
        {
            'title': 'Tips for Studying Abroad',
            'date': 'April 1, 2025',
            'excerpt': 'Planning to study abroad? Here are some essential tips to prepare...'
        },
        {
            'title': 'Top Universities in Europe',
            'date': 'March 25, 2025',
            'excerpt': 'Discover the highest-ranked universities across Europe for international students...'
        },
        {
            'title': 'Scholarship Opportunities for 2025',
            'date': 'March 15, 2025',
            'excerpt': 'A comprehensive guide to scholarship opportunities available for international students...'
        }
    ]
    return render_template('blog.html', posts=blog_posts)


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


@main.route('/subscribe', methods=['POST'])
def subscribe():
    """Handle newsletter subscription"""
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name', '')
        
        if not email:
            return jsonify({'success': False, 'message': 'Email is required'})
        
        try:
            # Check if subscriber already exists
            existing_subscriber = Subscriber.query.filter_by(email=email).first()
            
            if existing_subscriber:
                if not existing_subscriber.is_active:
                    # Reactivate subscriber
                    existing_subscriber.is_active = True
                    db.session.commit()
                    flash('Your subscription has been reactivated!', 'success')
                else:
                    return jsonify({'success': False, 'message': 'You are already subscribed!'})
            else:
                # Add new subscriber
                new_subscriber = Subscriber(email=email, name=name)
                db.session.add(new_subscriber)
                db.session.commit()
            
            # Send confirmation emails
            try:
                # Email to admin
                send_admin_notification(email)
                
                # Email to subscriber
                send_subscriber_confirmation(email)
                
                # Redirect with success message
                if request.referrer:
                    return redirect(request.referrer + '?subscription=success')
                else:
                    return redirect(url_for('main.index', subscription='success'))
                
            except Exception as e:
                current_app.logger.error(f"Email sending error: {str(e)}")
                return jsonify({'success': False, 'message': 'Subscribed, but failed to send confirmation email'})
                
        except Exception as e:
            current_app.logger.error(f"Subscription error: {str(e)}")
            return jsonify({'success': False, 'message': 'An error occurred while processing your subscription'})
    
    return jsonify({'success': False, 'message': 'Invalid request method'})


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
            
            prev_institution = request.form.get('prevInstitution')
            qualification = request.form.get('qualification')
            grad_year = request.form.get('gradYear')
            gpa = request.form.get('gpa')
            
            course = request.form.get('course')
            study_mode = request.form.get('studyMode')
            campus = request.form.get('campus')
            
            agreement = request.form.get('agreement')
            signature = request.form.get('signature')
            
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
            
            # Create specific folder for this application
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            applicant_folder = os.path.join(uploads_folder, f"{email}_{timestamp}")
            os.makedirs(applicant_folder, exist_ok=True)
            
            # Handle file uploads
            file_mappings = {
                'idUpload': 'id_document',
                'transcriptUpload': 'transcript',
                'photoUpload': 'passport_photo'
            }
            
            for file_key, db_field in file_mappings.items():
                if file_key in request.files:
                    file = request.files[file_key]
                    if file.filename:
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(applicant_folder, filename)
                        file.save(file_path)
                        setattr(application, db_field, file_path)
            
            # Save application to database
            db.session.add(application)
            db.session.commit()
            
            # Send email notification to admin
            send_application_notification(application)
            
            return jsonify({'success': True, 'message': 'Application submitted successfully'})
            
        except Exception as e:
            current_app.logger.error(f"Error processing admission form: {str(e)}")
            return jsonify({'success': False, 'message': 'An error occurred while processing your application'})
    
    return jsonify({'success': False, 'message': 'Invalid request method'})


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
        
        <p>Please review this application in the <a href="https://yourdomain.com/admin/applications/{application.id}">admin dashboard</a>.</p>
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
    
    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as server:
        server.starttls()
        server.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        server.send_message(msg)