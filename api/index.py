import os
import sys
from vercel_wsgi import run_wsgi_app

# Ensure the project root is in the Python path.
sys.path.insert(0, os.getcwd())

# Set the default Django settings module.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bike_counter.settings")

# Import and initialize the WSGI application.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

def handler(request, context):
    """
    This function is the entry point for Vercel.
    It adapts the Django WSGI application to Vercel's serverless function format.
    """
    return run_wsgi_app(application, request)
