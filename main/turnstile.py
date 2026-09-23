"""Cloudflare Turnstile verification.

Every public form on the site carries a Turnstile widget. The widget only
produces a token in the browser; it proves nothing until the token is checked
against Cloudflare from our server, which is what this module does.

Tokens are single use and expire after five minutes, so a replayed token comes
back as 'timeout-or-duplicate' and is rejected.
"""

import requests
from django.conf import settings

VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
TIMEOUT = 8

# Cloudflare's documented error codes, mapped to something worth logging.
_QUIET_CODES = {'invalid-input-response', 'missing-input-response', 'timeout-or-duplicate'}


def client_ip(request):
    """Best-effort visitor IP. Nginx sets X-Forwarded-For in front of gunicorn."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def verify(request, token=None):
    """Return (ok, error_message).

    Fails closed: if the token is missing or Cloudflare rejects it, the caller
    must not process the submission. A network failure talking to Cloudflare
    fails *open* - we would rather accept a lead we cannot verify than lose a
    real enquiry because Cloudflare was briefly unreachable.
    """
    if token is None:
        token = request.POST.get('cf-turnstile-response', '')
    token = (token or '').strip()

    if not token:
        return False, 'Please complete the security check and try again.'

    try:
        resp = requests.post(
            VERIFY_URL,
            data={
                'secret': settings.TURNSTILE_SECRET_KEY,
                'response': token,
                'remoteip': client_ip(request),
            },
            timeout=TIMEOUT,
        )
        result = resp.json()
    except Exception as e:
        # Cloudflare unreachable - do not punish the visitor for it.
        print(f'Turnstile verification unavailable, allowing submission: {e}')
        return True, ''

    if result.get('success'):
        return True, ''

    codes = result.get('error-codes') or []
    if not set(codes) & _QUIET_CODES:
        print(f'Turnstile rejected a submission: {codes}')
    return False, 'Security check failed. Please try again.'
