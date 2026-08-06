# main/middleware.py
from django.shortcuts import redirect

class RemoveWWW:
    """Redirect www to non-www domain"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        if host.startswith("www."):
            new_url = request.build_absolute_uri().replace("//www.", "//")
            return redirect(new_url, permanent=True)
        return self.get_response(request)


class UTF8EnforcementMiddleware:
    """Ensure all responses are UTF-8 encoded"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add UTF-8 charset to Content-Type if not present
        if 'Content-Type' in response:
            content_type = response['Content-Type']
            if 'charset' not in content_type:
                if content_type.startswith('application/json'):
                    response['Content-Type'] = 'application/json; charset=utf-8'
                elif content_type.startswith('text/html'):
                    response['Content-Type'] = 'text/html; charset=utf-8'
        
        return response