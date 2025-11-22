#!/usr/bin/env python3
"""
Startup script for Datenschleuder Backend
Run with: python start.py
"""

import uvicorn
import sys
import os

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)


def main():
    """Start the FastAPI application using uvicorn"""
    # Check if running in Docker/production mode
    is_production = (
        os.getenv("DOCKER_BUILD", "false").lower() == "true"
        or os.getenv("ENVIRONMENT", "development") == "production"
    )

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=not is_production,  # Disable reload in production
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,  # Enable access logs
    )


if __name__ == "__main__":
    main()
