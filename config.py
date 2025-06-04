import os
import secrets
from datetime import timedelta

class Config:
    """Base configuration class with security defaults."""
    
    # Security Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///denial_management.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Session Security
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # File Upload Security
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_EXTENSIONS = ['.csv', '.xlsx', '.xls']
    UPLOAD_PATH = 'uploads'
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Email Configuration (for notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # Security Headers
    SECURITY_HEADERS = {
        'force_https': False,  # Set to True in production with HTTPS
        'strict_transport_security': True,
        'content_security_policy': {
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline' cdn.jsdelivr.net",
            'style-src': "'self' 'unsafe-inline' cdn.jsdelivr.net",
            'img-src': "'self' data:",
            'font-src': "'self' cdn.jsdelivr.net",
        },
        'referrer_policy': 'strict-origin-when-cross-origin',
        'feature_policy': {
            'geolocation': "'none'",
            'microphone': "'none'",
            'camera': "'none'",
        }
    }

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Allow HTTP in development
    SECURITY_HEADERS = {
        **Config.SECURITY_HEADERS,
        'force_https': False,
    }

class ProductionConfig(Config):
    """Production configuration with enhanced security."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SECURITY_HEADERS = {
        **Config.SECURITY_HEADERS,
        'force_https': True,
    }
    
    # Enhanced security for production
    RATELIMIT_DEFAULT = "50 per hour"
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 