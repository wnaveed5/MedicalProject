from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='user')  # user, admin, manager
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<User {self.username}>'

class Claim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    claim_number = db.Column(db.String(50), unique=True, nullable=False)
    patient_id = db.Column(db.String(50), nullable=False)
    provider_id = db.Column(db.String(50), nullable=False)
    service_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, denied, approved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add user tracking
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # Relationships
    denials = db.relationship('Denial', backref='claim', lazy=True)
    issues = db.relationship('Issue', backref='claim', lazy=True)
    creator = db.relationship('User', backref='created_claims')
    
    def __repr__(self):
        return f'<Claim {self.claim_number}>'

class Denial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claim.id'), nullable=False)
    denial_code = db.Column(db.String(20), nullable=False)
    denial_reason = db.Column(db.Text, nullable=False)
    denial_date = db.Column(db.Date, nullable=False)
    appeal_deadline = db.Column(db.Date)
    appeal_status = db.Column(db.String(20), default='pending')  # pending, submitted, approved, denied
    appeal_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Denial {self.denial_code} for Claim {self.claim_id}>'

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    claim_id = db.Column(db.Integer, db.ForeignKey('claim.id'), nullable=False)
    issue_type = db.Column(db.String(50), nullable=False)  # missing_code, invalid_code, documentation, etc.
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), default='medium')  # low, medium, high
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved
    resolution_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Issue {self.issue_type} for Claim {self.claim_id}>' 