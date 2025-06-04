from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file, make_response, current_app
from flask_login import login_required, current_user
from app import db, limiter
from app.models import Claim, Denial, Issue
from app.security import (
    validate_claim_number, validate_patient_id, validate_provider_id, validate_amount,
    secure_file_upload, validate_csv_claims_data, sanitize_user_input, 
    log_security_event, require_role
)
from datetime import datetime
import pandas as pd
from werkzeug.utils import secure_filename
import os
import io

main = Blueprint('main', __name__)

# Common denial codes and their descriptions
DENIAL_CODES = {
    'CO-16': 'Claim/service lacks information or has submission/billing error(s)',
    'CO-18': 'Duplicate claim/service',
    'CO-29': 'The time limit for filing has expired',
    'CO-97': 'The benefit for this service is included in the payment/allowance for another service/procedure',
    'PR-1': 'Patient ineligible for benefits',
    'PR-2': 'Service not covered by this payer/insurance',
    'PR-3': 'Patient ineligible for benefits on date of service',
}

@main.route('/test')
def test():
    """Simple test endpoint to debug issues."""
    return '<h1>Security Test - Application Working!</h1>'

@main.route('/')
@login_required
@limiter.limit("100 per hour")
def index():
    try:
        # Get all claims for statistics (limit for performance)
        all_claims = Claim.query.filter_by(created_by=current_user.id).all()
        pending_claims = Claim.query.filter_by(status='pending', created_by=current_user.id).all()
        denied_claims = Claim.query.filter_by(status='denied', created_by=current_user.id).all()
        approved_claims = Claim.query.filter_by(status='approved', created_by=current_user.id).all()
        
        # Get recent claims (last 10) for current user
        recent_claims = Claim.query.filter_by(created_by=current_user.id).order_by(Claim.created_at.desc()).limit(10).all()
        
        return render_template('index.html', 
                             claims=all_claims,
                             pending_claims=pending_claims,
                             denied_claims=denied_claims,
                             approved_claims=approved_claims,
                             recent_claims=recent_claims)
    except Exception as e:
        current_app.logger.error(f'Dashboard error: {e}')
        flash('Error loading dashboard data.', 'error')
        return render_template('index.html', claims=[], pending_claims=[], 
                             denied_claims=[], approved_claims=[], recent_claims=[])

@main.route('/claims')
@login_required
@limiter.limit("50 per hour")
def claims_list():
    try:
        # Users can only see their own claims unless they are admin
        if current_user.role == 'admin':
            claims = Claim.query.order_by(Claim.created_at.desc()).all()
        else:
            claims = Claim.query.filter_by(created_by=current_user.id).order_by(Claim.created_at.desc()).all()
        
        return render_template('claims/list.html', claims=claims, denial_codes=DENIAL_CODES)
    except Exception as e:
        current_app.logger.error(f'Claims list error: {e}')
        flash('Error loading claims.', 'error')
        return render_template('claims/list.html', claims=[], denial_codes=DENIAL_CODES)

@main.route('/claims/new', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per hour")
def new_claim():
    if request.method == 'POST':
        try:
            # Sanitize and validate input
            data = sanitize_user_input({
                'claim_number': request.form.get('claim_number', '').strip(),
                'patient_id': request.form.get('patient_id', '').strip(),
                'provider_id': request.form.get('provider_id', '').strip(),
                'service_date': request.form.get('service_date', '').strip(),
                'total_amount': request.form.get('total_amount', '').strip(),
            })
            
            # Validate all fields
            errors = []
            
            # Validate claim number
            valid, msg = validate_claim_number(data['claim_number'])
            if not valid:
                errors.append(msg)
            elif Claim.query.filter_by(claim_number=data['claim_number']).first():
                errors.append('Claim number already exists.')
            
            # Validate patient ID
            valid, msg = validate_patient_id(data['patient_id'])
            if not valid:
                errors.append(msg)
            
            # Validate provider ID
            valid, msg = validate_provider_id(data['provider_id'])
            if not valid:
                errors.append(msg)
            
            # Validate amount
            valid, msg = validate_amount(data['total_amount'])
            if not valid:
                errors.append(msg)
            
            # Validate service date
            try:
                service_date = datetime.strptime(data['service_date'], '%Y-%m-%d').date()
                if service_date > datetime.now().date():
                    errors.append('Service date cannot be in the future.')
            except ValueError:
                errors.append('Invalid service date format.')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('claims/new.html')
            
            # Create claim
            claim = Claim(
                claim_number=data['claim_number'],
                patient_id=data['patient_id'],
                provider_id=data['provider_id'],
                service_date=service_date,
                total_amount=float(data['total_amount']),
                status='pending',
                created_by=current_user.id
            )
            db.session.add(claim)
            db.session.commit()
            
            # Analyze claim for potential issues
            analyze_claim(claim)
            
            log_security_event('CLAIM_CREATED', f'New claim created: {claim.claim_number}', current_user.id)
            flash('Claim created successfully!', 'success')
            return redirect(url_for('main.claims_list'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating claim: {e}')
            flash('Error creating claim. Please try again.', 'error')
    
    return render_template('claims/new.html')

@main.route('/claims/upload', methods=['GET', 'POST'])
@login_required
@limiter.limit("5 per hour")  # Strict limit for file uploads
def upload_claims():
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                flash('No file uploaded', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            
            # Secure file validation
            valid, error_msg, filename = secure_file_upload(file, current_app.config.get('UPLOAD_EXTENSIONS'))
            if not valid:
                flash(error_msg, 'error')
                return redirect(request.url)
            
            # Read and validate CSV
            try:
                df = pd.read_csv(file, dtype=str)  # Read as strings for validation
                
                # Validate CSV structure and content
                valid, error_msg = validate_csv_claims_data(df)
                if not valid:
                    flash(f'Invalid CSV data: {error_msg}', 'error')
                    return redirect(request.url)
                
                # Process valid claims
                claims_created = 0
                claims_skipped = 0
                
                for _, row in df.iterrows():
                    # Check for duplicate claim numbers
                    if Claim.query.filter_by(claim_number=row['claim_number']).first():
                        claims_skipped += 1
                        continue
                    
                    try:
                        claim = Claim(
                            claim_number=row['claim_number'],
                            patient_id=row['patient_id'],
                            provider_id=row['provider_id'],
                            service_date=pd.to_datetime(row['service_date']).date(),
                            total_amount=float(row['total_amount']),
                            status='pending',
                            created_by=current_user.id
                        )
                        db.session.add(claim)
                        analyze_claim(claim)
                        claims_created += 1
                        
                    except Exception as e:
                        current_app.logger.warning(f'Skipped invalid claim row: {e}')
                        claims_skipped += 1
                        continue
                
                db.session.commit()
                
                log_security_event('BULK_CLAIMS_UPLOAD', f'Uploaded {claims_created} claims, skipped {claims_skipped}', current_user.id)
                flash(f'Upload completed! Created {claims_created} claims, skipped {claims_skipped} invalid/duplicate entries.', 'success')
                return redirect(url_for('main.claims_list'))
                
            except pd.errors.EmptyDataError:
                flash('Uploaded file is empty.', 'error')
            except pd.errors.ParserError:
                flash('Invalid CSV format.', 'error')
            except Exception as e:
                current_app.logger.error(f'CSV processing error: {e}')
                flash('Error processing file. Please check the format.', 'error')
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'File upload error: {e}')
            flash('Upload failed. Please try again.', 'error')
    
    return render_template('claims/upload.html')

@main.route('/claims/download-sample')
@login_required
@limiter.limit("10 per hour")
def download_sample():
    try:
        # Create sample CSV data
        sample_data = {
            'claim_number': ['CLM001', 'CLM002', 'CLM003'],
            'patient_id': ['PAT001', 'PAT002', 'PAT001'],
            'provider_id': ['PROV001', 'PROV001', 'PROV002'],
            'service_date': ['2024-03-15', '2024-03-16', '2024-03-17'],
            'total_amount': [1500.00, 2750.50, 950.75]
        }
        
        # Create DataFrame and convert to CSV
        df = pd.DataFrame(sample_data)
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        
        # Create response with security headers
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = 'attachment; filename=sample_claims.csv'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        
        return response
        
    except Exception as e:
        current_app.logger.error(f'Sample download error: {e}')
        flash('Error generating sample file.', 'error')
        return redirect(url_for('main.claims_list'))

@main.route('/claims/<int:claim_id>')
@login_required
@limiter.limit("100 per hour")
def view_claim(claim_id):
    try:
        claim = Claim.query.get_or_404(claim_id)
        
        # Authorization check - users can only view their own claims unless admin
        if current_user.role != 'admin' and claim.created_by != current_user.id:
            log_security_event('UNAUTHORIZED_CLAIM_ACCESS', f'Attempted access to claim {claim_id}', current_user.id)
            flash('Access denied.', 'error')
            return redirect(url_for('main.claims_list'))
        
        return render_template('claims/view.html', claim=claim, denial_codes=DENIAL_CODES)
        
    except Exception as e:
        current_app.logger.error(f'Claim view error: {e}')
        flash('Error loading claim.', 'error')
        return redirect(url_for('main.claims_list'))

@main.route('/claims/<int:claim_id>/deny', methods=['POST'])
@login_required
@require_role('manager')  # Only managers and admins can deny claims
@limiter.limit("20 per hour")
def deny_claim(claim_id):
    try:
        claim = Claim.query.get_or_404(claim_id)
        
        # Validate input
        data = sanitize_user_input({
            'denial_code': request.form.get('denial_code', '').strip(),
            'denial_date': request.form.get('denial_date', '').strip(),
            'appeal_deadline': request.form.get('appeal_deadline', '').strip(),
        })
        
        # Validate denial code
        if data['denial_code'] not in DENIAL_CODES:
            flash('Invalid denial code.', 'error')
            return redirect(url_for('main.view_claim', claim_id=claim_id))
        
        # Validate dates
        try:
            denial_date = datetime.strptime(data['denial_date'], '%Y-%m-%d').date()
            appeal_deadline = None
            if data['appeal_deadline']:
                appeal_deadline = datetime.strptime(data['appeal_deadline'], '%Y-%m-%d').date()
                if appeal_deadline <= denial_date:
                    flash('Appeal deadline must be after denial date.', 'error')
                    return redirect(url_for('main.view_claim', claim_id=claim_id))
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('main.view_claim', claim_id=claim_id))
        
        # Create denial record
        denial = Denial(
            claim_id=claim.id,
            denial_code=data['denial_code'],
            denial_reason=DENIAL_CODES.get(data['denial_code'], 'Unknown reason'),
            denial_date=denial_date,
            appeal_deadline=appeal_deadline
        )
        claim.status = 'denied'
        
        db.session.add(denial)
        db.session.commit()
        
        log_security_event('CLAIM_DENIED', f'Claim {claim.claim_number} denied with code {data["denial_code"]}', current_user.id)
        flash('Claim denied successfully', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error denying claim: {e}')
        flash('Error processing denial. Please try again.', 'error')
    
    return redirect(url_for('main.view_claim', claim_id=claim_id))

def analyze_claim(claim):
    """Analyze a claim for potential issues and create Issue records"""
    try:
        issues = []
        
        # Check for missing or invalid claim number
        if not claim.claim_number or len(claim.claim_number) < 3:
            issues.append(Issue(
                claim_id=claim.id,
                issue_type='missing_code',
                description='Claim number is missing or too short',
                severity='high'
            ))
        
        # Check for zero or negative amount
        if claim.total_amount <= 0:
            issues.append(Issue(
                claim_id=claim.id,
                issue_type='invalid_amount',
                description='Claim amount is zero or negative',
                severity='high'
            ))
        
        # Check for unusually high amounts
        if claim.total_amount > 50000:  # $50k threshold
            issues.append(Issue(
                claim_id=claim.id,
                issue_type='high_amount',
                description='Claim amount is unusually high and requires review',
                severity='medium'
            ))
        
        # Check for future service dates
        if claim.service_date > datetime.now().date():
            issues.append(Issue(
                claim_id=claim.id,
                issue_type='future_date',
                description='Service date is in the future',
                severity='high'
            ))
        
        # Check for old service dates (over 1 year)
        if (datetime.now().date() - claim.service_date).days > 365:
            issues.append(Issue(
                claim_id=claim.id,
                issue_type='old_claim',
                description='Service date is over 1 year old',
                severity='medium'
            ))
        
        # Save any issues found
        if issues:
            db.session.add_all(issues)
            # Don't commit here - let the caller handle the transaction
            
    except Exception as e:
        current_app.logger.error(f'Claim analysis error: {e}')

@main.route('/api/denial-codes')
@login_required
@limiter.limit("50 per hour")
def get_denial_codes():
    """API endpoint to get denial codes - secured and rate limited"""
    try:
        return jsonify(DENIAL_CODES)
    except Exception as e:
        current_app.logger.error(f'API error: {e}')
        return jsonify({'error': 'Internal server error'}), 500

# Security middleware for main routes
@main.before_request
def main_security_middleware():
    """Additional security checks for main routes."""
    # Log API access
    if request.endpoint and request.endpoint.startswith('main.'):
        if request.method in ['POST', 'PUT', 'DELETE']:
            log_security_event('DATA_MODIFICATION', f'Accessing {request.endpoint}', 
                             current_user.id if current_user.is_authenticated else None) 