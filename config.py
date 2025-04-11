import os
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler  # Added import for RotatingFileHandler
import logging  # Added for logging module 

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('SMTP_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('SMTP_USERNAME')
    MAIL_PASSWORD = os.environ.get('SMTP_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@bolakineduconsult.com')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL')
    UPLOADS_FOLDER = os.environ.get('UPLOADS_FOLDER', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size
    
    # Site URL configuration - Used to replace hardcoded domain
    SITE_URL = os.environ.get('SITE_URL', 'https://bolakineduconsult.ng')
    
    # Pagination
    ITEMS_PER_PAGE = 10
    
    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///bolakin_dev.db'
    SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5000')


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'postgresql://postgres:postgres@localhost/bolakin_test'
    SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5000')


class ProductionConfig(Config):
    """Production configuration for render.com deployment"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # If render.com provides the DATABASE_URL with postgres:// prefix,
    # we need to replace it with postgresql:// for SQLAlchemy
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    # Configure logging for production
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'true').lower() in ['true', 'on', '1']
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Set up production logging
        import logging
        from logging import StreamHandler
        # RotatingFileHandler already imported at the top of the file
        
        if cls.LOG_TO_STDOUT:
            # Log to stderr
            stream_handler = StreamHandler()
            stream_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            )
            stream_handler.setFormatter(formatter)
            app.logger.addHandler(stream_handler)
        else:
            # Ensure logs directory exists
            os.makedirs('logs', exist_ok=True)
            
            # Log to file with rotation
            file_handler = RotatingFileHandler(
                'logs/bolakin.log', 
                maxBytes=10485760,  # 10MB
                backupCount=10
            )
            file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
            formatter = logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            )
            file_handler.setFormatter(formatter)
            app.logger.addHandler(file_handler)
        
        app.logger.setLevel(getattr(logging, cls.LOG_LEVEL))
        app.logger.info('Bolakin Educational Consult startup')
        
        # Import render_template for error handler
        from flask import render_template
        
        # Register exception handler to log unhandled exceptions
        @app.errorhandler(Exception)
        def handle_exception(e):
            app.logger.error(f'Unhandled exception: {e}', exc_info=True)
            return render_template('errors/500.html'), 500


# Map environment names to config classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}