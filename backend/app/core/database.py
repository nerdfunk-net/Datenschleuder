from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from .config import settings

# Create database engine (will be initialized after database check)
engine = None
SessionLocal = None
Base = declarative_base()


def initialize_engine():
    """Initialize the database engine"""
    global engine, SessionLocal
    engine = create_engine(settings.database_url, pool_pre_ping=True, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session_local():
    """Get the SessionLocal instance"""
    return SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    print("Checking if database exists...")

    # Connect to default 'postgres' database to create our database
    try:
        conn = psycopg2.connect(
            host=settings.NOC_DATABASE,
            port=settings.NOC_DATABASE_PORT,
            user=settings.NOC_USERNAME,
            password=settings.NOC_PASSWORD,
            database="postgres",
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (settings.NOC_DATABASE_NAME,),
        )
        exists = cursor.fetchone()

        if not exists:
            print(f"Creating database '{settings.NOC_DATABASE_NAME}'...")
            cursor.execute(f'CREATE DATABASE "{settings.NOC_DATABASE_NAME}"')
            print(f"✓ Database '{settings.NOC_DATABASE_NAME}' created successfully")
        else:
            print(f"✓ Database '{settings.NOC_DATABASE_NAME}' already exists")

        cursor.close()
        conn.close()
        return True

    except psycopg2.OperationalError as e:
        print(f"✗ Failed to connect to PostgreSQL server: {e}")
        print(
            f"Please ensure PostgreSQL is running on {settings.NOC_DATABASE}:{settings.NOC_DATABASE_PORT}"
        )
        return False
    except Exception as e:
        print(f"✗ Failed to create database: {e}")
        return False


def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def init_db():
    """Initialize database tables"""
    print("Starting database initialization...")

    # Step 1: Create database if it doesn't exist
    if not create_database_if_not_exists():
        print(
            "ERROR: Cannot connect to PostgreSQL server. Please check your database configuration."
        )
        print(f"Host: {settings.NOC_DATABASE}")
        print(f"Port: {settings.NOC_DATABASE_PORT}")
        print(f"User: {settings.NOC_USERNAME}")
        sys.exit(1)

    # Step 2: Initialize the engine now that database exists
    initialize_engine()

    # Step 3: Check database connection
    print("\nChecking database connection...")
    if not check_database_connection():
        print(
            "ERROR: Cannot connect to database. Please check your database configuration."
        )
        print(
            f"Database URL: {settings.database_url.replace(settings.NOC_PASSWORD, '***')}"
        )
        sys.exit(1)

    # Step 4: Create all tables
    try:
        print("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables initialized successfully")
    except Exception as e:
        print(f"✗ Failed to create database tables: {e}")
        sys.exit(1)
