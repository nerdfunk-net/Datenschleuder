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
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
