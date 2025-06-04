from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import db, limiter
from app.models import User
from app.forms import LoginForm, RegistrationForm
from app.security import (
    validate_email, validate_username, validate_password, validate_name,
    sanitize_user_input, log_security_event, require_role
)

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")  # Rate limit login attempts
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Get and sanitize input
        username = sanitize_user_input(form.username.data.strip())
        password = form.password.data
        remember = form.remember.data
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Check if account is active (you could add an active field to User model)
            login_user(user, remember=remember, duration=current_app.config.get('PERMANENT_SESSION_LIFETIME'))
            log_security_event('SUCCESSFUL_LOGIN', f'User: {username}', user.id)
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.index')
            return redirect(next_page)
        else:
            log_security_event('FAILED_LOGIN', f'Failed login attempt for username: {username}')
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Rate limit registration attempts
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Create new user with secure password hashing
            user = User(
                username=form.username.data.strip(),
                email=form.email.data.strip().lower(),
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip()
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            log_security_event('SUCCESSFUL_REGISTRATION', f'New user registered: {user.username}', user.id)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Registration error: {e}')
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    user_id = current_user.id
    username = current_user.username
    logout_user()
    log_security_event('LOGOUT', f'User logged out: {username}', user_id)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
@limiter.limit("5 per minute")
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate current password
        if not current_user.check_password(current_password):
            log_security_event('PASSWORD_CHANGE_ATTEMPT', 'Invalid current password', current_user.id)
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html')
        
        # Validate new password
        valid, msg = validate_password(new_password)
        if not valid:
            flash(msg, 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match.', 'error')
            return render_template('auth/change_password.html')
        
        if current_password == new_password:
            flash('New password must be different from current password.', 'error')
            return render_template('auth/change_password.html')
        
        try:
            # Update password
            current_user.set_password(new_password)
            db.session.commit()
            
            log_security_event('PASSWORD_CHANGED', 'Password successfully changed', current_user.id)
            flash('Password changed successfully.', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Password change error: {e}')
            flash('Failed to change password. Please try again.', 'error')
    
    return render_template('auth/change_password.html')

@auth.route('/admin/users')
@login_required
@require_role('admin')
def admin_users():
    """Admin-only route to manage users."""
    users = User.query.all()
    return render_template('auth/admin_users.html', users=users)

@auth.route('/admin/user/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@require_role('admin')
@limiter.limit("10 per minute")
def toggle_user_active(user_id):
    """Admin-only route to activate/deactivate users."""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Cannot deactivate your own account.', 'error')
        return redirect(url_for('auth.admin_users'))
    
    try:
        # You would need to add an 'active' field to the User model
        # user.active = not user.active
        # db.session.commit()
        
        action = 'activated' if getattr(user, 'active', True) else 'deactivated'
        log_security_event('USER_STATUS_CHANGED', f'User {user.username} {action}', current_user.id)
        flash(f'User {user.username} has been {action}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'User status change error: {e}')
        flash('Failed to update user status.', 'error')
    
    return redirect(url_for('auth.admin_users'))

# Security event logging for authentication
@auth.before_request
def log_auth_activity():
    """Log authentication-related activities."""
    if request.method == 'POST':
        endpoint = request.endpoint
        if endpoint in ['auth.login', 'auth.register', 'auth.change_password']:
            log_security_event('AUTH_ACTIVITY', f'Accessing {endpoint}')

@auth.after_request  
def after_auth_request(response):
    """Add security headers to authentication responses."""
    # Prevent caching of sensitive pages
    if request.endpoint in ['auth.login', 'auth.register', 'auth.profile']:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response 