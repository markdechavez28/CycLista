"""
A minimal WSGI adapter for Vercel.
This code is inspired by vercel-wsgi but is simplified for your Django app.
"""

import io
from urllib.parse import unquote_plus

def run_wsgi_app(app, request):
    """
    Convert the Vercel event (a dict) into a WSGI environ, pass it to the WSGI app,
    and then convert the response back to a Vercel-compatible dict.
    
    Note: This is a minimal implementation and may need adjustments for your use case.
    """
    # Build a minimal WSGI environ from the Vercel request.
    # Vercel passes the request as a dict with keys like "httpMethod", "headers", "query", "body", etc.
    # For our purposes we assume the request is in the format provided by Vercel's Python builder.
    environ = {
        "REQUEST_METHOD": request.get("method", "GET"),
        "SCRIPT_NAME": "",
        "PATH_INFO": unquote_plus(request.get("path", "/")),
        "QUERY_STRING": request.get("query", ""),
        "SERVER_NAME": request.get("headers", {}).get("host", "localhost"),
        "SERVER_PORT": request.get("headers", {}).get("x-forwarded-port", "80"),
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": request.get("headers", {}).get("x-forwarded-proto", "http"),
        "wsgi.input": io.BytesIO(request.get("body", "").encode("utf-8")),
        "wsgi.errors": io.StringIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": True,
    }
    
    # Add headers to the environ (HTTP_... keys)
    headers = request.get("headers", {})
    for header_name, header_value in headers.items():
        key = "HTTP_" + header_name.upper().replace("-", "_")
        environ[key] = header_value

    # Container for status and headers from start_response.
    response_data = {}
    def start_response(status, response_headers, exc_info=None):
        response_data["status"] = status
        response_data["headers"] = response_headers

    # Call the WSGI application.
    result = app(environ, start_response)
    body = b"".join(result)
    if hasattr(result, "close"):
        result.close()
    
    # Parse the status code from the status string.
    status_code = int(response_data["status"].split(" ")[0])
    
    # Convert headers list to a dict.
    response_headers = dict(response_data.get("headers", []))
    
    # Return the Vercel-compatible response.
    return {
        "statusCode": status_code,
        "headers": response_headers,
        "body": body.decode("utf-8")
    }
