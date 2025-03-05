import os
import sys
# Ensure the project root is in the Python path.
sys.path.insert(0, os.getcwd())

# Set the default Django settings module.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bike_counter.settings")

# Import and initialize the Django WSGI application.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Import your local adapter.
from api.vercel_wsgi import run_wsgi_app

def handler(request, context):
    """
    Entry point for Vercel.
    'request' is a dict representing the incoming HTTP request.
    """
    return run_wsgi_app(application, request)
