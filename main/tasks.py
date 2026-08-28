import logging

from celery import shared_task

from .xopp_service import get_catalog, get_developers, warm_available_counts

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def refresh_xopp_cache(self):
    """Background refresh of the X-OPP property catalog and developers list.

    Scheduled by celery beat (see CELERY_BEAT_SCHEDULE). Uses force_refresh so
    the old cache keeps serving until the new fetch completes — visitors never
    wait on a rebuild. Retries up to 3 times, 10 minutes apart, on failure.
    """
    catalog = get_catalog(force_refresh=True)
    developers = get_developers(force_refresh=True)

    if not catalog or not developers:
        logger.error(
            f"X-OPP refresh incomplete (catalog={len(catalog)}, developers={len(developers)}), retrying"
        )
        raise self.retry()

    # Pre-warm "available units" for the projects on the first listing pages so
    # web requests never have to wait on the partner API for them.
    try:
        warm_available_counts(catalog)
    except Exception as e:  # never fail the refresh over the warm-up
        logger.warning(f"available-count warm-up failed: {e}")

    logger.info(f"X-OPP refresh done: {len(catalog)} properties, {len(developers)} developers")
    return {'properties': len(catalog), 'developers': len(developers)}
