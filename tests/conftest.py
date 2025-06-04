import pytest
import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables and cleanup after tests."""
    # Store original environment variables
    original_env = dict(os.environ)
    
    # Set test environment variables
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['FLASK_APP'] = 'app.py'
    os.environ['ALEMBIC_CONFIG'] = str(project_root / 'tests' / 'alembic.ini')
    
    # Create a temporary directory for test files if needed
    test_dir = project_root / 'tests'
    test_dir.mkdir(exist_ok=True)
    
    yield
    
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for tests."""
    import logging
    logging.basicConfig(level=logging.INFO)
    # Prevent logging from interfering with test output
    logging.getLogger('alembic').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING) 