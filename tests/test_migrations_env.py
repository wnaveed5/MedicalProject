import pytest
import os
from unittest.mock import MagicMock, patch, create_autospec
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from alembic.util.exc import CommandError
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from alembic.config import Config
from sqlalchemy import engine_from_config

from tests.test_app import create_test_app

# Patch the Alembic context before importing migrations.env
mock_context_patcher = patch('alembic.context')
mock_context = mock_context_patcher.start()
mock_config = MagicMock(spec=Config)
mock_config.config_file_name = 'tests/alembic.ini'
mock_config.get_main_option.return_value = 'sqlite:///:memory:'
mock_config.get_section.return_value = {'sqlalchemy.url': 'sqlite:///:memory:'}
mock_config.config_ini_section = 'alembic'
mock_context.config = mock_config
mock_context.is_offline_mode.return_value = False
mock_context.configure_args = {}

# Now import the module under test
from migrations.env import get_engine, get_engine_url, get_metadata, run_migrations_offline, run_migrations_online

# Clean up the patcher after all tests
def teardown_module(module):
    mock_context_patcher.stop()

@pytest.fixture(autouse=True)
def mock_alembic_context():
    """Mock the Alembic context for all tests."""
    # Reset the mock for each test
    mock_context.reset_mock()
    mock_context.config = mock_config
    mock_context.is_offline_mode.return_value = False
    mock_context.configure_args = {}
    yield mock_context

@pytest.fixture
def app():
    """Create a Flask application for testing."""
    app = Flask(__name__)
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'TESTING': True
    })
    
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)
    
    return app

@pytest.fixture
def app_context(app):
    """Create an application context for testing."""
    with app.app_context():
        yield app

def test_get_engine_with_app_context(app_context):
    """Test get_engine function with Flask application context."""
    engine = get_engine()
    assert engine is not None
    assert 'sqlite' in str(engine.url)

def test_get_engine_without_app_context():
    """Test get_engine function without Flask application context."""
    with patch('migrations.env.engine_from_config') as mock_engine_from_config:
        mock_engine = MagicMock()
        mock_engine_from_config.return_value = mock_engine
        
        engine = get_engine()
        assert engine == mock_engine
        mock_engine_from_config.assert_called_once()

def test_get_engine_url_with_app_context(app_context):
    """Test get_engine_url function with Flask application context."""
    url = get_engine_url()
    assert url is not None
    assert 'sqlite' in url

def test_get_engine_url_without_app_context():
    """Test get_engine_url function without Flask application context."""
    # Test with config URL
    with patch('migrations.env.get_engine', side_effect=RuntimeError()):
        url = get_engine_url()
        assert 'sqlite' in url

    # Test with environment variable
    with patch('migrations.env.get_engine', side_effect=RuntimeError()):
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test:test@localhost/testdb'}):
            with patch('migrations.env.config.get_main_option', return_value=None):
                url = get_engine_url()
                assert 'postgresql' in url

    # Test fallback to default
    with patch('migrations.env.get_engine', side_effect=RuntimeError()):
        with patch('migrations.env.config.get_main_option', return_value=None):
            with patch.dict(os.environ, {}, clear=True):
                url = get_engine_url()
                assert url == 'sqlite:///app.db'

def test_get_metadata_with_app_context(app_context):
    """Test get_metadata function with Flask application context."""
    metadata = get_metadata()
    assert metadata is not None

def test_get_metadata_without_app_context():
    """Test get_metadata function without Flask application context."""
    metadata = get_metadata()
    assert metadata is None

def test_run_migrations_offline():
    """Test run_migrations_offline function."""
    with patch('migrations.env.context') as mock_context:
        mock_context.configure = MagicMock()
        mock_context.begin_transaction = MagicMock()
        mock_context.run_migrations = MagicMock()
        
        # Mock the context manager
        mock_context.begin_transaction.return_value.__enter__ = MagicMock()
        mock_context.begin_transaction.return_value.__exit__ = MagicMock()
        
        run_migrations_offline()
        
        mock_context.configure.assert_called_once()
        mock_context.run_migrations.assert_called_once()

def test_run_migrations_online_with_app_context(app_context):
    """Test run_migrations_online function with application context."""
    with patch('migrations.env.context') as mock_context:
        mock_context.configure = MagicMock()
        mock_context.begin_transaction = MagicMock()
        mock_context.run_migrations = MagicMock()
        
        # Mock the context manager
        mock_context.begin_transaction.return_value.__enter__ = MagicMock()
        mock_context.begin_transaction.return_value.__exit__ = MagicMock()
        
        run_migrations_online()
        
        mock_context.configure.assert_called_once()
        mock_context.run_migrations.assert_called_once()

def test_run_migrations_online_without_app_context():
    """Test run_migrations_online function without application context."""
    with patch('migrations.env.context') as mock_context, \
         patch('migrations.env.engine_from_config') as mock_engine_from_config:
        
        # Setup mocks
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock()
        mock_engine_from_config.return_value = mock_engine
        
        mock_context.configure = MagicMock()
        mock_context.begin_transaction = MagicMock()
        mock_context.run_migrations = MagicMock()
        
        # Mock the context manager
        mock_context.begin_transaction.return_value.__enter__ = MagicMock()
        mock_context.begin_transaction.return_value.__exit__ = MagicMock()
        
        with patch('migrations.env.get_engine', side_effect=RuntimeError()):
            run_migrations_online()
            
            mock_engine_from_config.assert_called_once()
            mock_context.configure.assert_called_once()
            mock_context.run_migrations.assert_called_once()

def test_migration_mode_selection():
    """Test selection between online and offline migration modes."""
    # Test offline mode
    mock_context.is_offline_mode.return_value = True
    with patch('migrations.env.run_migrations_offline') as mock_offline:
        with patch('migrations.env.run_migrations_online') as mock_online:
            import migrations.env
            migrations.env.run_migrations_offline()
            mock_offline.assert_called_once()
            mock_online.assert_not_called()

    # Test online mode
    mock_context.is_offline_mode.return_value = False
    with patch('migrations.env.run_migrations_offline') as mock_offline:
        with patch('migrations.env.run_migrations_online') as mock_online:
            import migrations.env
            migrations.env.run_migrations_online()
            mock_online.assert_called_once()
            mock_offline.assert_not_called() 