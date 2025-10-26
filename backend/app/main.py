from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.database import init_db, get_session_local
from app.core.config import settings
from app.core.security import get_password_hash
from app.api.auth import router as auth_router
from app.api.credentials import router as credentials_router
from app.api.settings import router as settings_router
from app.api.nifi import router as nifi_router
from app.api.nifi_instances import router as nifi_instances_router
from app.api.nifi_flows import router as nifi_flows_router
from app.api.flow_views import router as flow_views_router
from app.api.registry_flows import router as registry_flows_router
from app.api.deploy import router as deploy_router
from app.models.user import User

# Create FastAPI application
app = FastAPI(
    title="Datenschleuder API",
    description="Backend API for Datenschleuder application",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(credentials_router)
app.include_router(settings_router)
app.include_router(nifi_router)
app.include_router(nifi_instances_router)
app.include_router(nifi_flows_router)
app.include_router(flow_views_router)
app.include_router(registry_flows_router)
app.include_router(deploy_router, prefix="/api/deploy", tags=["deployment"])


@app.on_event("startup")
async def startup_event():
    """Initialize database and create default admin user on startup"""
    print("=" * 50)
    print("Starting Datenschleuder Backend...")
    print("=" * 50)

    # Initialize database (checks connection and creates tables)
    init_db()

    # Create default admin user if it doesn't exist
    print("\nChecking default admin user...")
    SessionLocal = get_session_local()
    db: Session = SessionLocal()
    try:
        # Check if any users exist
        user_count = db.query(User).count()

        if user_count == 0:
            print("No users found in database. Creating default admin user...")
            # Hash the default password
            hashed_password = get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)
            print(f"Password hash created (first 20 chars): {hashed_password[:20]}...")

            admin_user = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                hashed_password=hashed_password,
                is_superuser=True,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"✓ Created default admin user: {settings.DEFAULT_ADMIN_USERNAME}")
            print(f"  Username: {settings.DEFAULT_ADMIN_USERNAME}")
            print(f"  Password: {settings.DEFAULT_ADMIN_PASSWORD}")
            print(f"  Role: Administrator")
        else:
            admin_user = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
            if admin_user:
                print(f"✓ Admin user already exists: {settings.DEFAULT_ADMIN_USERNAME}")
            else:
                print(f"⚠ Users exist but no admin user found. You may need to create one manually.")
    except Exception as e:
        print(f"✗ Failed to create admin user: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        import sys
        sys.exit(1)
    finally:
        db.close()

    print("\n" + "=" * 50)
    print("✓ Application started successfully!")
    print("=" * 50)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Datenschleuder API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
