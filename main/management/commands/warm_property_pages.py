import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand

from main.xopp_service import fetch_property_page, get_catalog, page_age


class Command(BaseCommand):
    help = (
        "Pre-load every property page's data (detail + units) into the cache, "
        "so the first visit to a page - usually a crawler - is fast instead of "
        "waiting 3-6 s on the partner API. Skips pages fetched recently. "
        "Run after a deploy and nightly from cron (not at the same time as "
        "refresh_xopp, to stay under the partner API's rate limit)."
    )

    def add_arguments(self, parser):
        parser.add_argument('--max-age', type=float, default=20,
                            help='Re-fetch pages older than this many hours (default 20).')
        parser.add_argument('--workers', type=int, default=2,
                            help='Properties fetched at once (default 2; each makes 2 API calls '
                                 'in parallel, so keep it low for the rate limit).')
        parser.add_argument('--limit', type=int, default=0,
                            help='Only warm the first N properties (0 = all).')

    def handle(self, *args, **opts):
        catalog = get_catalog(cached_only=True)
        if not catalog:
            self.stderr.write(self.style.ERROR("Catalog cache is empty - run refresh_xopp first."))
            raise SystemExit(1)

        max_age = opts['max_age'] * 3600
        ids = [p['id'] for p in catalog]
        if opts['limit']:
            ids = ids[:opts['limit']]
        todo = [pid for pid in ids if (age := page_age(pid)) is None or age > max_age]
        self.stdout.write(f"{len(ids)} properties, {len(todo)} need warming "
                          f"(older than {opts['max_age']:g} h or missing)")

        ok = gone = failed = 0
        started = time.monotonic()

        def warm(pid):
            for attempt in range(3):
                result = fetch_property_page(pid)
                if result.get('not_found'):
                    return result
                # The DB cache drops a write silently if the database is busy
                # (SQLite allows one writer), so confirm it was stored.
                if result['success'] and page_age(pid) is not None:
                    return result
                time.sleep(5 * (attempt + 1))   # rate limit / busy DB / transient error: back off
            return {'success': False, 'data': None, 'error': result.get('error') or 'not stored'}

        with ThreadPoolExecutor(max_workers=max(1, opts['workers'])) as ex:
            futures = {ex.submit(warm, pid): pid for pid in todo}
            for n, fut in enumerate(as_completed(futures), 1):
                result = fut.result()
                if result['success']:
                    ok += 1
                elif result.get('not_found'):
                    gone += 1
                else:
                    failed += 1
                if n % 200 == 0:
                    self.stdout.write(f"  {n}/{len(todo)} done ({time.monotonic() - started:.0f}s)")

        self.stdout.write(f"Warmed {ok}, removed from X-OPP {gone}, failed {failed} "
                          f"in {time.monotonic() - started:.0f}s")
        if failed:
            self.stderr.write(self.style.WARNING(
                f"{failed} pages could not be fetched; they will load live on first visit."))
        else:
            self.stdout.write(self.style.SUCCESS("Property pages warm"))
