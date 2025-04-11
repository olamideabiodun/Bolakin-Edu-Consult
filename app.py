import os
import logging
from flask import Flask, request, session, redirect, url_for, render_template  # Added render_template
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_mail import Mail
from datetime import datetime
from config import config
from models import db, User, PageVisit
from flask_wtf.csrf import CSRFProtect

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'admin.login'  # Changed to admin.login
mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()

def create_app(config_name=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Determine the configuration to use
    config_name = config_name or os.environ.get('FLASK_CONFIG', 'default')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Ensure uploads directory exists
    os.makedirs(app.config['UPLOADS_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Register blueprints
    from routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # Move auth routes under admin
    from routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/admin')
    
    from routes.admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin/dashboard')
    
    register_error_handlers(app)

    # Protect admin routes
    @app.before_request
    def restrict_admin_access():
        if request.path in ['/subscribe', '/unsubscribe']:
            return None

        """Prevent access to admin pages without authentication"""
        if request.path.startswith('/admin/dashboard'):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
    
    # Setup request handlers for analytics
    @app.before_request
    def track_visitor():
        # Skip tracking for static files and admin routes
        if not request.path.startswith('/static') and not request.path.startswith('/admin'):
            # Record the page visit
            page_visit = PageVisit(
                page=request.path,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                referrer=request.referrer or ''
            )
            
            try:
                db.session.add(page_visit)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error tracking page visit: {str(e)}")
    
    # Create admin user on first run - This uses with_app_context instead of before_first_request, flask at it again
    with app.app_context():
        @app.cli.command("create-admin")
        def create_admin_user():
            db.create_all()  # Create all tables if they don't exist
            
            # Check if admin exists, create if not
            if not User.query.filter_by(is_admin=True).first():
                admin_user = User(
                    username='admin',
                    email=app.config['ADMIN_EMAIL'],
                    is_admin=True
                )
                admin_user.set_password('changeme123')  # Default password, should be changed immediately
                
                try:
                    db.session.add(admin_user)
                    db.session.commit()
                    app.logger.info("Created default admin user")
                except Exception as e:
                    db.session.rollback()
                    app.logger.error(f"Error creating admin user: {str(e)}")
    
    # Explicitly return the app
    return app

def register_error_handlers(app):
    """Register error handlers for the application"""
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/404.html'), 403  # Redirect to 404 for security
    
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/500.html'), 400  # Redirect to 500

    return app

@login_manager.user_loader
def load_user(user_id):
    """User loader function for Flask-Login"""
    return User.query.get(int(user_id))


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)