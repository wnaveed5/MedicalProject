"""
Security utilities for input validation, sanitization, and protection.
"""
import re
import bleach
from functools import wraps
from flask import request, jsonify, current_app, abort
from flask_login import current_user
import pandas as pd
from werkzeug.utils import secure_filename
import os

# Allowed HTML tags and attributes for content sanitization
ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li']
ALLOWED_ATTRIBUTES = {}

def sanitize_html(content):
    """Sanitize HTML content to prevent XSS attacks."""
    if not content:
        return content
    return bleach.clean(content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)

def validate_claim_number(claim_number):
    """Validate claim number format."""
    if not claim_number:
        return False, "Claim number is required"
    
    # Allow alphanumeric characters, hyphens, and underscores, 3-50 characters
    pattern = r'^[A-Za-z0-9_-]{3,50}$'
    if not re.match(pattern, claim_number):
        return False, "Claim number must be 3-50 characters, alphanumeric, hyphens, or underscores only"
    
    return True, ""

def validate_patient_id(patient_id):
    """Validate patient ID format."""
    if not patient_id:
        return False, "Patient ID is required"
    
    # Allow alphanumeric characters, 3-50 characters
    pattern = r'^[A-Za-z0-9]{3,50}$'
    if not re.match(pattern, patient_id):
        return False, "Patient ID must be 3-50 alphanumeric characters"
    
    return True, ""

def validate_provider_id(provider_id):
    """Validate provider ID format."""
    if not provider_id:
        return False, "Provider ID is required"
    
    # Allow alphanumeric characters, 3-50 characters
    pattern = r'^[A-Za-z0-9]{3,50}$'
    if not re.match(pattern, provider_id):
        return False, "Provider ID must be 3-50 alphanumeric characters"
    
    return True, ""

def validate_amount(amount):
    """Validate monetary amount."""
    try:
        amount_float = float(amount)
        if amount_float < 0:
            return False, "Amount cannot be negative"
        if amount_float > 1000000:  # $1M limit
            return False, "Amount cannot exceed $1,000,000"
        return True, ""
    except (ValueError, TypeError):
        return False, "Invalid amount format"

def validate_email(email):
    """Validate email format."""
    if not email:
        return False, "Email is required"
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    if len(email) > 120:
        return False, "Email too long (max 120 characters)"
    
    return True, ""

def validate_username(username):
    """Validate username format."""
    if not username:
        return False, "Username is required"
    
    # Allow alphanumeric and underscores, 3-80 characters
    pattern = r'^[A-Za-z0-9_]{3,80}$'
    if not re.match(pattern, username):
        return False, "Username must be 3-80 characters, alphanumeric and underscores only"
    
    return True, ""

def validate_password(password):
    """Validate password strength."""
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if len(password) > 128:
        return False, "Password too long (max 128 characters)"
    
    # Check for at least one uppercase, lowercase, digit, and special character
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, ""

def validate_name(name, field_name="Name"):
    """Validate name fields."""
    if not name:
        return False, f"{field_name} is required"
    
    if len(name) > 50:
        return False, f"{field_name} too long (max 50 characters)"
    
    # Allow letters, spaces, hyphens, apostrophes
    pattern = r'^[A-Za-z\s\'-]{1,50}$'
    if not re.match(pattern, name):
        return False, f"{field_name} contains invalid characters"
    
    return True, ""

def secure_file_upload(file, allowed_extensions=None):
    """Secure file upload validation."""
    if not file or file.filename == '':
        return False, "No file selected", None
    
    if allowed_extensions is None:
        allowed_extensions = current_app.config.get('UPLOAD_EXTENSIONS', ['.csv'])
    
    # Check file extension
    filename = secure_filename(file.filename)
    if not filename:
        return False, "Invalid filename", None
    
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}", None
    
    # Check file size (Flask handles MAX_CONTENT_LENGTH automatically)
    
    return True, "", filename

def validate_csv_claims_data(df):
    """Validate CSV claims data structure and content."""
    required_columns = ['claim_number', 'patient_id', 'provider_id', 'service_date', 'total_amount']
    
    # Check required columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    # Validate data types and content
    errors = []
    
    for index, row in df.iterrows():
        row_num = index + 2  # +2 because pandas is 0-indexed and we skip header
        
        # Validate claim number
        valid, msg = validate_claim_number(row['claim_number'])
        if not valid:
            errors.append(f"Row {row_num}: {msg}")
        
        # Validate patient ID
        valid, msg = validate_patient_id(row['patient_id'])
        if not valid:
            errors.append(f"Row {row_num}: {msg}")
        
        # Validate provider ID
        valid, msg = validate_provider_id(row['provider_id'])
        if not valid:
            errors.append(f"Row {row_num}: {msg}")
        
        # Validate amount
        valid, msg = validate_amount(row['total_amount'])
        if not valid:
            errors.append(f"Row {row_num}: {msg}")
        
        # Validate date
        try:
            pd.to_datetime(row['service_date'])
        except:
            errors.append(f"Row {row_num}: Invalid service date format")
    
    if errors:
        return False, "; ".join(errors[:5])  # Limit to first 5 errors
    
    return True, ""

def require_role(required_role):
    """Decorator to require specific user role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if current_user.role != required_role and current_user.role != 'admin':
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_security_event(event_type, details, user_id=None):
    """Log security events for monitoring."""
    if user_id is None and current_user.is_authenticated:
        user_id = current_user.id
    
    # In production, this should log to a secure logging system
    current_app.logger.warning(f"SECURITY EVENT: {event_type} - {details} - User: {user_id} - IP: {request.remote_addr}")

def check_rate_limit_exceeded():
    """Check if rate limit has been exceeded."""
    # This would integrate with Flask-Limiter
    # For now, just a placeholder
    return False

def sanitize_user_input(data):
    """Sanitize all user input data."""
    if isinstance(data, dict):
        return {key: sanitize_user_input(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_user_input(item) for item in data]
    elif isinstance(data, str):
        return sanitize_html(data.strip())
    else:
        return data 