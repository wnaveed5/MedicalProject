from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from app import db
from app.models import Claim, Denial, Issue
from datetime import datetime
import pandas as pd
from werkzeug.utils import secure_filename
import os

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

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/claims')
def claims_list():
    claims = Claim.query.order_by(Claim.created_at.desc()).all()
    return render_template('claims/list.html', claims=claims)

@main.route('/claims/new', methods=['GET', 'POST'])
def new_claim():
    if request.method == 'POST':
        try:
            claim = Claim(
                claim_number=request.form['claim_number'],
                patient_id=request.form['patient_id'],
                provider_id=request.form['provider_id'],
                service_date=datetime.strptime(request.form['service_date'], '%Y-%m-%d').date(),
                total_amount=float(request.form['total_amount']),
                status='pending'
            )
            db.session.add(claim)
            db.session.commit()
            
            # Analyze claim for potential issues
            analyze_claim(claim)
            
            flash('Claim created successfully!', 'success')
            return redirect(url_for('main.claims_list'))
        except Exception as e:
            flash(f'Error creating claim: {str(e)}', 'error')
    
    return render_template('claims/new.html')

@main.route('/claims/upload', methods=['GET', 'POST'])
def upload_claims():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            try:
                df = pd.read_csv(file)
                for _, row in df.iterrows():
                    claim = Claim(
                        claim_number=row['claim_number'],
                        patient_id=row['patient_id'],
                        provider_id=row['provider_id'],
                        service_date=pd.to_datetime(row['service_date']).date(),
                        total_amount=float(row['total_amount']),
                        status='pending'
                    )
                    db.session.add(claim)
                    analyze_claim(claim)
                
                db.session.commit()
                flash('Claims uploaded and processed successfully!', 'success')
                return redirect(url_for('main.claims_list'))
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Please upload a CSV file', 'error')
    
    return render_template('claims/upload.html')

@main.route('/claims/<int:claim_id>')
def view_claim(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    return render_template('claims/view.html', claim=claim)

@main.route('/claims/<int:claim_id>/deny', methods=['POST'])
def deny_claim(claim_id):
    claim = Claim.query.get_or_404(claim_id)
    try:
        denial = Denial(
            claim_id=claim.id,
            denial_code=request.form['denial_code'],
            denial_reason=DENIAL_CODES.get(request.form['denial_code'], 'Unknown reason'),
            denial_date=datetime.strptime(request.form['denial_date'], '%Y-%m-%d').date(),
            appeal_deadline=datetime.strptime(request.form['appeal_deadline'], '%Y-%m-%d').date() if request.form.get('appeal_deadline') else None
        )
        claim.status = 'denied'
        db.session.add(denial)
        db.session.commit()
        flash('Claim denied successfully', 'success')
    except Exception as e:
        flash(f'Error denying claim: {str(e)}', 'error')
    
    return redirect(url_for('main.view_claim', claim_id=claim_id))

def analyze_claim(claim):
    """Analyze a claim for potential issues and create Issue records"""
    # Example analysis logic - expand based on requirements
    issues = []
    
    # Check for missing claim number
    if not claim.claim_number:
        issues.append(Issue(
            claim_id=claim.id,
            issue_type='missing_code',
            description='Claim number is missing',
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
    
    # Add more analysis logic here
    
    # Save any issues found
    if issues:
        db.session.add_all(issues)
        db.session.commit()

@main.route('/api/denial-codes')
def get_denial_codes():
    return jsonify(DENIAL_CODES) 