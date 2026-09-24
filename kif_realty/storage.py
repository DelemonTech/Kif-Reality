"""
Static files storage: minify our own CSS/JS and give every file a
content-hashed name during `collectstatic`.

Hashed names (e.g. css/index-styles.3f2a9c.css) let Nginx cache /static/
for a year with `immutable` while still delivering edits immediately —
a changed file gets a new name, so browsers fetch it fresh.
"""
import logging

import rcssmin
import rjsmin
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# Only our own assets from static/css and static/js. Third-party files
# (admin, ckeditor, tinymce) ship pre-built and are left untouched.
MINIFY_PREFIXES = ('css/', 'js/')


class MinifiedManifestStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False

    def stored_name(self, name):
        # A template referencing a missing static file falls back to the
        # unhashed URL instead of raising a 500 in production.
        try:
            return super().stored_name(name)
        except ValueError:
            logger.warning("[STATIC] Missing static file referenced: %s", name)
            return name

    def _save(self, name, content):
        normalized = name.replace('\\', '/')
        if normalized.startswith(MINIFY_PREFIXES) and '.min.' not in normalized:
            if normalized.endswith('.css'):
                content = self._minify(name, content, rcssmin.cssmin)
            elif normalized.endswith('.js'):
                content = self._minify(name, content, rjsmin.jsmin)
        return super()._save(name, content)

    @staticmethod
    def _minify(name, content, minifier):
        content.seek(0)
        raw = content.read()
        try:
            text = raw.decode('utf-8') if isinstance(raw, bytes) else raw
            return ContentFile(minifier(text).encode('utf-8'))
        except Exception:
            # Never break a deploy over minification; ship the original.
            logger.exception("[STATIC] Minify failed for %s; saving unminified", name)
            return ContentFile(raw if isinstance(raw, bytes) else raw.encode('utf-8'))
