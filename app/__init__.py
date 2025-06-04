import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name=None):
    """Application factory pattern with security configuration."""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_CONFIG', 'development')
    app.config.from_object(config[config_name])
    
    # Ensure secret key is set
    if not app.config.get('SECRET_KEY'):
        raise ValueError("SECRET_KEY must be set in environment variables or config")
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    
    # Configure Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'
    
    # Configure Talisman for security headers (disabled in development)
    if config_name == 'production':
        security_headers = app.config.get('SECURITY_HEADERS', {})
        csp = security_headers.get('content_security_policy')
        
        Talisman(app,
            force_https=security_headers.get('force_https', False),
            strict_transport_security=security_headers.get('strict_transport_security', False),
            content_security_policy=csp if csp else False,
            referrer_policy=security_headers.get('referrer_policy', False),
            feature_policy=security_headers.get('feature_policy', False)
        )
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes import main
    from app.auth import auth
    
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    
    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/' + app.config.get('LOG_FILE', 'app.log'),
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        
        file_handler.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.info('Denial Management System startup')
    
    # Create upload directory
    upload_path = app.config.get('UPLOAD_PATH', 'uploads')
    if not os.path.exists(upload_path):
        os.makedirs(upload_path, mode=0o755)
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        from app.security import log_security_event
        log_security_event('BAD_REQUEST', f'400 error: {error}')
        return '<h1>400 - Bad Request</h1><p>The request could not be understood by the server.</p>', 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        from app.security import log_security_event
        log_security_event('UNAUTHORIZED_ACCESS', f'401 error: {error}')
        return '<h1>401 - Unauthorized</h1><p>Please log in to access this page.</p>', 401
    
    @app.errorhandler(403)
    def forbidden(error):
        from app.security import log_security_event
        log_security_event('FORBIDDEN_ACCESS', f'403 error: {error}')
        return '<h1>403 - Forbidden</h1><p>You do not have permission to access this resource.</p>', 403
    
    @app.errorhandler(404)
    def not_found(error):
        return '<h1>404 - Not Found</h1><p>The requested page could not be found.</p>', 404
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        from app.security import log_security_event
        log_security_event('FILE_TOO_LARGE', 'File upload exceeded size limit')
        return '<h1>413 - File Too Large</h1><p>The uploaded file exceeds the maximum allowed size.</p>', 413
    
    @app.errorhandler(415)
    def unsupported_media_type(error):
        from app.security import log_security_event
        log_security_event('UNSUPPORTED_MEDIA_TYPE', f'415 error: {error}')
        return '<h1>415 - Unsupported Media Type</h1><p>The media type is not supported.</p>', 415
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        from app.security import log_security_event
        log_security_event('RATE_LIMIT_EXCEEDED', f'Rate limit exceeded: {e}')
        return '<h1>429 - Too Many Requests</h1><p>Rate limit exceeded. Please try again later.</p>', 429
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'Server Error: {error}')
        return '<h1>500 - Internal Server Error</h1><p>An internal server error occurred.</p>', 500
    
    # Security middleware
    @app.before_request
    def security_middleware():
        from flask import request
        from app.security import log_security_event
        
        # Log suspicious activity
        if len(request.args) > 50:  # Too many parameters
            log_security_event('SUSPICIOUS_REQUEST', 'Too many request parameters')
        
        # Check for common attack patterns in requests
        suspicious_patterns = ['<script', 'javascript:', 'onload=', 'onerror=', 'eval(', 'union select']
        request_data = str(request.args) + str(request.form)
        try:
            json_data = request.get_json(silent=True)
            if json_data:
                request_data += str(json_data)
        except Exception:
            pass
        for pattern in suspicious_patterns:
            if pattern.lower() in request_data.lower():
                log_security_event('POTENTIAL_XSS_ATTEMPT', f'Suspicious pattern detected: {pattern}')
                break
    
    return app 