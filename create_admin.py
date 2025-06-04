#!/usr/bin/env python3
"""
Script to create an admin user for the Denial Management System
"""

from app import create_app, db
from app.models import User

def create_admin_user():
    app = create_app()
    
    with app.app_context():
        # Check if admin user already exists
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print("Admin user already exists!")
            print(f"Username: {admin.username}")
            print(f"Email: {admin.email}")
            return
        
        # Create admin user
        admin = User(
            username='admin',
            email='admin@denialmanagement.com',
            first_name='System',
            last_name='Administrator',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')  # Change this in production!
        
        db.session.add(admin)
        db.session.commit()
        
        print("Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("Email: admin@denialmanagement.com")
        print("\n⚠️  IMPORTANT: Change the default password after first login!")

if __name__ == '__main__':
    create_admin_user() 