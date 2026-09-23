from django.conf import settings


def turnstile(request):
    """Expose the Turnstile site key to every template.

    The site key is public by design - it is rendered into the page. Only the
    secret key (TURNSTILE_SECRET_KEY) must stay on the server.
    """
    return {'TURNSTILE_SITE_KEY': settings.TURNSTILE_SITE_KEY}
