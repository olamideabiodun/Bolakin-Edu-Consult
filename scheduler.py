import os
from datetime import datetime
from flask_apscheduler import APScheduler
from app import create_app
from routes.admin import send_scheduled_newsletters

scheduler = APScheduler()

def setup_scheduler(app):
    """Set up the APScheduler with the Flask app"""
    scheduler.init_app(app)
    
    # Add job to send scheduled newsletters
    scheduler.add_job(
        id='send_scheduled_newsletters',
        func=send_scheduled_newsletters,
        trigger='interval',
        minutes=15,  # Check every 15 minutes
        misfire_grace_time=900  # 15 minutes grace time
    )
    
    # Add job to run at the end of each month
    scheduler.add_job(
        id='send_monthly_newsletter',
        func=send_monthly_newsletter,
        trigger='cron',
        day='last',
        hour=9,  # 9 AM
        minute=0,
        misfire_grace_time=3600  # 1 hour grace time
    )
    
    scheduler.start()
    app.logger.info("Scheduler started")
    return scheduler


def send_monthly_newsletter():
    """Send the monthly newsletter to all subscribers"""
    app = create_app()
    with app.app_context():
        from models import db, Newsletter, User
        from datetime import datetime
        
        app.logger.info("Running monthly newsletter job")
        
        # Check if there's already a newsletter for this month
        today = datetime.utcnow()
        month_year = today.strftime("%B %Y")
        
        existing_newsletter = Newsletter.query.filter(
            Newsletter.subject.like(f'Monthly Update - {month_year}%')
        ).first()
        
        if existing_newsletter:
            app.logger.info(f"Monthly newsletter for {month_year} already exists")
            return
        
        # Find admin user to set as creator
        admin_user = User.query.filter_by(is_admin=True).first()
        
        if not admin_user:
            app.logger.error("No admin user found for creating monthly newsletter")
            return
        
        # Create newsletter with template
        newsletter = Newsletter(
            subject=f'Monthly Update - {month_year}',
            content=create_monthly_newsletter_template(month_year),
            status='Draft',
            created_by=admin_user.id
        )
        
        try:
            db.session.add(newsletter)
            db.session.commit()
            app.logger.info(f"Created monthly newsletter draft for {month_year}")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error creating monthly newsletter: {str(e)}")


def create_monthly_newsletter_template(month_year):
    """Create a template for the monthly newsletter"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Bolakin Educational Consult - Monthly Newsletter</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #FF9933;
                color: white;
                padding: 20px;
                text-align: center;
            }}
            .content {{
                padding: 20px;
            }}
            .footer {{
                background-color: #f1f1f1;
                padding: 10px 20px;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
            .button {{
                display: inline-block;
                background-color: #FF9933;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 0;
            }}
            h2 {{
                color: #FF9933;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Bolakin Educational Consult</h1>
                <h2>Monthly Update - {month_year}</h2>
            </div>
            
            <div class="content">
                <p>Hello {{{{name}}}},</p>
                
                <h2>This Month's Highlights</h2>
                <p>We hope this newsletter finds you well. Here are the latest updates from Bolakin Educational Consult:</p>
                <ul>
                    <li>New scholarship opportunities available for study in Canada</li>
                    <li>Upcoming virtual education fair - Join us to learn about studying abroad</li>
                    <li>Success story: Meet our student who got admitted to Oxford University</li>
                </ul>
                
                <h2>Featured Destination: Switzerland</h2>
                <p>Switzerland offers world-class education with its prestigious universities and polytechnics.
                Learn more about studying in this beautiful country.</p>
                
                <p style="text-align: center;">
                    <a href="https://yourdomain.com/countries/switzerland" class="button">
                        Learn More About Switzerland
                    </a>
                </p>
                
                <h2>Upcoming Events</h2>
                <p>Don't miss our upcoming virtual information sessions:</p>
                <ul>
                    <li>Study in UK - Virtual Session on [Date]</li>
                    <li>Scholarship Application Workshop - [Date]</li>
                    <li>Visa Application Tips and Tricks - [Date]</li>
                </ul>
                
                <p>Join us to learn more about your study abroad options!</p>
                
                <p>If you have any questions or need assistance with your applications, please don't hesitate to contact us.</p>
                
                <p>Best regards,<br>The Bolakin Educational Consult Team</p>
            </div>
            
            <div class="footer">
                <p>&copy; {datetime.utcnow().year} Bolakin Educational Consult. All rights reserved.</p>
                <p>You're receiving this email because you subscribed to our newsletter.</p>
                <p><a href="{{{{unsubscribe_link}}}}">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """


if __name__ == '__main__':
    app = create_app()
    setup_scheduler(app)
    app.run(debug=True)