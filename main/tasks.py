import logging

from celery import shared_task
from django.core.cache import cache

from .xopp_service import (
    CATALOG_CACHE_KEY,
    DEVELOPERS_CACHE_KEY,
    get_catalog,
    get_developers,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def refresh_xopp_cache(self):
    """Nightly refresh of the X-OPP property catalog and developers list.

    Scheduled by celery beat at midnight (see CELERY_BEAT_SCHEDULE).
    Retries up to 3 times, 10 minutes apart, if the API is unreachable.
    """
    cache.delete(CATALOG_CACHE_KEY)
    catalog = get_catalog()

    cache.delete(DEVELOPERS_CACHE_KEY)
    developers = get_developers()

    if not catalog or not developers:
        logger.error(
            f"X-OPP refresh incomplete (catalog={len(catalog)}, developers={len(developers)}), retrying"
        )
        raise self.retry()

    logger.info(f"X-OPP refresh done: {len(catalog)} properties, {len(developers)} developers")
    return {'properties': len(catalog), 'developers': len(developers)}
