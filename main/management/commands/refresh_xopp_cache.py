"""Nightly refresh of the X-OPP partner API caches.

Run manually:      python manage.py refresh_xopp_cache
Schedule (Linux):  0 0 * * * cd /path/to/Kif-Reality && venv/bin/python manage.py refresh_xopp_cache
Schedule (Windows): registered in Task Scheduler as "KifRealty XOPP Cache Refresh".
"""
from django.core.management.base import BaseCommand

from main.xopp_service import get_catalog, get_developers


class Command(BaseCommand):
    help = "Fetch the full X-OPP property catalog and developers list into the cache"

    def handle(self, *args, **options):
        catalog = get_catalog(force_refresh=True)
        if catalog:
            self.stdout.write(self.style.SUCCESS(f"Catalog refreshed: {len(catalog)} properties"))
        else:
            self.stderr.write("Catalog refresh FAILED (API unreachable, nothing cached)")

        developers = get_developers(force_refresh=True)
        if developers:
            self.stdout.write(self.style.SUCCESS(f"Developers refreshed: {len(developers)}"))
        else:
            self.stderr.write("Developers refresh FAILED (API unreachable, nothing cached)")
