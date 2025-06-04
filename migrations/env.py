import logging
from logging.config import fileConfig
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from flask import current_app
from alembic import context
from alembic.util.exc import CommandError
import sqlalchemy as sa
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger('alembic.env')


def get_engine():
    """Get the database engine from Flask-Migrate."""
    try:
        # Flask-Migrate approach - using the new recommended way
        db = current_app.extensions['migrate'].db
        if hasattr(db, 'engine'):
            return db.engine
        return db.get_engine()  # Fallback for older versions
    except (RuntimeError, KeyError):
        # Fallback: get engine from config
        return engine_from_config(
            config.get_section(config.config_ini_section),
            prefix='sqlalchemy.',
            poolclass=pool.NullPool
        )


def get_engine_url():
    """Get the database URL for migrations."""
    try:
        # Try to get from Flask app context first
        engine = get_engine()
        return str(engine.url)
    except (RuntimeError, KeyError):
        # Fallback: get from config or environment
        url = config.get_main_option('sqlalchemy.url')
        if url:
            return url
        
        # Last resort: try to get from environment
        import os
        return os.environ.get('DATABASE_URL', 'sqlite:///app.db')


def get_metadata():
    """Get the metadata object for autogenerate support."""
    try:
        if hasattr(current_app.extensions['migrate'], 'db'):
            return current_app.extensions['migrate'].db.metadata
    except (RuntimeError, KeyError):
        pass
    return None


# Only set the URL if we're in an application context
try:
    if current_app:
        config.set_main_option('sqlalchemy.url', get_engine_url())
except RuntimeError:
    # We're outside application context, URL will be set later
    pass

target_metadata = get_metadata()


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_engine_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # If we don't have an application context, create a basic engine
    try:
        engine = get_engine()
    except RuntimeError:
        # Create engine from config when outside app context
        engine = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix='sqlalchemy.',
            poolclass=pool.NullPool
        )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
