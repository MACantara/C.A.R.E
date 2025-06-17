from flask import make_response, request
from functools import wraps


def no_cache(f):
    """
    Decorator that adds no-cache headers to prevent browser caching.
    Should be used on authenticated routes to prevent back button access after logout.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        
        # Prevent caching of authenticated pages
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        # Additional security headers
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        return response
    
    return decorated_function


def add_cache_headers(response, cache_type='no-cache'):
    """
    Add appropriate cache headers to a response object.
    
    Args:
        response: Flask response object
        cache_type: Type of caching ('no-cache', 'public', 'private')
    """
    if cache_type == 'no-cache':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif cache_type == 'public':
        response.headers['Cache-Control'] = 'public, max-age=3600'
    elif cache_type == 'private':
        response.headers['Cache-Control'] = 'private, max-age=300'
    
    return response


def clear_browser_cache():
    """
    JavaScript code to clear browser cache and force reload.
    Returns a string of JavaScript code.
    """
    return """
    // Clear browser cache and force reload
    if ('caches' in window) {
        caches.keys().then(function(names) {
            names.forEach(function(name) {
                caches.delete(name);
            });
        });
    }
    
    // Clear localStorage and sessionStorage
    if (typeof Storage !== "undefined") {
        localStorage.clear();
        sessionStorage.clear();
    }
    
    // Force reload without cache
    window.location.reload(true);
    """


def is_authenticated_route():
    """
    Check if the current route requires authentication.
    Returns True if the route is protected/authenticated.
    """
    # List of route patterns that require authentication
    protected_patterns = [
        '/dashboard',
        '/medical',
        '/appointments',
        '/consultations',
        '/messages',
        '/reports',
        '/admin',
        '/patients',
        '/prescriptions',
        '/profile'
    ]
    
    current_path = request.path
    return any(current_path.startswith(pattern) for pattern in protected_patterns)


def get_logout_redirect_script():
    """
    JavaScript code to handle post-logout behavior.
    Prevents back button access to authenticated pages.
    """
    return """
    // Prevent back button access after logout
    (function() {
        // Mark that user has logged out
        sessionStorage.setItem('user_logged_out', 'true');
        
        // Clear all cached data
        if ('caches' in window) {
            caches.keys().then(function(names) {
                names.forEach(function(name) {
                    caches.delete(name);
                });
            });
        }
        
        // Clear browser storage
        localStorage.clear();
        
        // Disable back button functionality
        history.pushState(null, null, window.location.href);
        window.onpopstate = function() {
            history.pushState(null, null, window.location.href);
        };
        
        // Redirect to login after a short delay
        setTimeout(function() {
            window.location.replace('/auth/login');
        }, 100);
    })();
    """


def get_auth_check_script():
    """
    JavaScript code to check authentication status on page load.
    Redirects to login if user is not authenticated or has logged out.
    """
    return """
    // Check authentication status on page load
    (function() {
        // Check if user was logged out
        if (sessionStorage.getItem('user_logged_out') === 'true') {
            // Clear the logout flag and redirect
            sessionStorage.removeItem('user_logged_out');
            window.location.replace('/auth/login');
            return;
        }
        
        // For authenticated pages, verify session is still valid
        var isAuthenticatedPage = window.location.pathname.match(/^\/(dashboard|medical_dashboard|appointments|consultations|messages|reports|admin|patients|prescriptions)/);
        
        if (isAuthenticatedPage && !document.body.hasAttribute('data-user-authenticated')) {
            // User is on authenticated page but not logged in
            window.location.replace('/auth/login');
            return;
        }
        
        // Disable caching for authenticated pages
        if (isAuthenticatedPage) {
            // Set cache control headers via JavaScript
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.getRegistrations().then(function(registrations) {
                    registrations.forEach(function(registration) {
                        registration.unregister();
                    });
                });
            }
        }
        
        // Handle browser back/forward buttons for authenticated pages
        if (isAuthenticatedPage) {
            window.addEventListener('pageshow', function(event) {
                if (event.persisted) {
                    // Page was loaded from cache, reload it
                    window.location.reload();
                }
            });
        }
    })();
    """
