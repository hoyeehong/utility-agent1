"""
Vercel entry point for FastAPI application
WSGI handler for serverless deployment
"""

import sys
import os

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Export for Vercel WSGI handler
handler = app
