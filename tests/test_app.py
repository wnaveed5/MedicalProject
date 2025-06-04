from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

def create_test_app():
    """Create a Flask application for testing."""
    app = Flask(__name__)
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'TESTING': True
    })
    
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)
    
    return app, db, migrate 