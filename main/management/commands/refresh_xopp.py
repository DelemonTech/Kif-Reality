from django.core.management.base import BaseCommand

from main.xopp_service import get_catalog, get_developers, warm_available_counts


class Command(BaseCommand):
    help = (
        "Rebuild the X-OPP catalog/developers caches and warm availability "
        "counts. Run after a deploy (and from cron if Celery is not running) "
        "so visitors never wait on a cold cache."
    )

    def handle(self, *args, **options):
        catalog = get_catalog(force_refresh=True)
        self.stdout.write(f"Catalog: {len(catalog)} properties")

        developers = get_developers(force_refresh=True)
        self.stdout.write(f"Developers: {len(developers)}")

        counts = warm_available_counts(catalog)
        self.stdout.write(f"Availability counts warmed: {len(counts)}")

        if not catalog:
            self.stderr.write(self.style.ERROR("Catalog fetch FAILED — site will show no properties"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("X-OPP caches warm"))
