import logging
import re
import time
from typing import Dict, List, Optional

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils.text import slugify

logger = logging.getLogger(__name__)

# Filters accepted by GET /properties/ (per partner API doc)
ALLOWED_PROPERTY_FILTERS = {
    'city',
    'property_type',
    'min_price',
    'max_price',
    'page',
    'page_size',
}

# Filters accepted by GET /properties/{id}/units/
ALLOWED_UNIT_FILTERS = {
    'status',
    'bedrooms',
    'min_price',
    'max_price',
    'page',
    'page_size',
}

# Doc recommends caching 15-60 min; catalog changes at most a few times per day.
CACHE_TTL = 30 * 60


class XOPPService:
    """Client for the X-OPP Partner Property API (read-only, X-API-Key auth).

    All methods return {'success': bool, 'data': dict|None, 'error': str|None}.
    Must be called from a whitelisted server IP; non-whitelisted IPs get 401.
    """

    @staticmethod
    def _get(path: str, params: Optional[Dict] = None, cache_key: Optional[str] = None) -> Dict:
        if cache_key:
            cached = cache.get(cache_key)
            if cached is not None:
                return {'success': True, 'data': cached, 'error': None}

        try:
            response = requests.get(
                f"{settings.XOPP_API_BASE.rstrip('/')}{path}",
                params=params or {},
                headers={'X-API-Key': settings.XOPP_API_KEY},
                timeout=settings.API_TIMEOUT,
            )

            if response.status_code == 401:
                detail = response.json().get('message') or response.json().get('detail', '')
                logger.error(f"X-OPP auth failed: {detail}")
                return {'success': False, 'data': None, 'error': 'Property service authentication failed.'}
            if response.status_code == 404:
                return {'success': False, 'data': None, 'error': 'Property not found.'}
            if response.status_code == 429:
                logger.warning("X-OPP rate limit exceeded")
                return {'success': False, 'data': None, 'error': 'Too many requests. Please try again shortly.'}

            response.raise_for_status()
            data = response.json()

            if cache_key:
                cache.set(cache_key, data, CACHE_TTL)
            return {'success': True, 'data': data, 'error': None}

        except requests.exceptions.Timeout:
            logger.error(f"X-OPP request timed out: {path}")
            return {'success': False, 'data': None, 'error': 'Request timed out. Please try again.'}
        except requests.exceptions.RequestException as e:
            logger.error(f"X-OPP request failed: {path}: {e}")
            return {'success': False, 'data': None, 'error': 'Unable to fetch properties. Please try again later.'}
        except Exception as e:
            logger.error(f"Unexpected X-OPP error: {path}: {e}")
            return {'success': False, 'data': None, 'error': 'An unexpected error occurred.'}

    @staticmethod
    def get_properties(filters: Optional[Dict] = None) -> Dict:
        """List properties, newest first. Paginated: {count, next, previous, results}."""
        raw = filters or {}
        params = {
            k: v for k, v in raw.items()
            if k in ALLOWED_PROPERTY_FILTERS and v is not None and v != ''
        }
        cache_key = 'xopp_properties_' + '_'.join(f'{k}={params[k]}' for k in sorted(params))
        return XOPPService._get('/properties/', params, cache_key)

    @staticmethod
    def get_property(property_id) -> Dict:
        """Single property with detail fields (payment plans, amenities, nearby places...)."""
        return XOPPService._get(f'/properties/{property_id}/', cache_key=f'xopp_property_{property_id}')

    @staticmethod
    def get_property_units(property_id, filters: Optional[Dict] = None) -> Dict:
        """Sellable units of one project. Paginated like the property list."""
        raw = filters or {}
        params = {
            k: v for k, v in raw.items()
            if k in ALLOWED_UNIT_FILTERS and v is not None and v != ''
        }
        suffix = '_'.join(f'{k}={params[k]}' for k in sorted(params))
        return XOPPService._get(
            f'/properties/{property_id}/units/', params,
            cache_key=f'xopp_units_{property_id}_{suffix}',
        )

    @staticmethod
    def get_all_units(property_id) -> List[Dict]:
        """All units of a project, walking pagination. Empty list on failure."""
        units, page = [], 1
        while True:
            result = XOPPService.get_property_units(property_id, {'page': page, 'page_size': 100})
            if not result['success']:
                break
            data = result['data']
            units.extend(data.get('results', []))
            if not data.get('next'):
                break
            page += 1
        return units


# ── Full-catalog cache ────────────────────────────────────────────────────────
# The partner API only filters by city / property_type / price. The site's UI
# also filters by district, bedrooms, developer, area, title, status and splits
# Residential vs Commercial — so we pull the whole catalog (stripped to the
# fields we need), cache it, and filter server-side.

CATALOG_CACHE_KEY = 'xopp_catalog_v1'
CATALOG_TTL = 45 * 60

COMMERCIAL_TYPES = {
    'full floor', 'half floor', 'hotel', 'land / plot', 'office',
    'retail', 'shop', 'suite', 'warehouse',
}


def classify_property_type(type_str) -> str:
    """'Residential' if any offered type is residential, else 'Commercial'."""
    types = [t.strip().lower() for t in (type_str or '').split(',') if t.strip()]
    if types and all(t in COMMERCIAL_TYPES for t in types):
        return 'Commercial'
    return 'Residential'


def delivery_year(delivery_date) -> Optional[int]:
    m = re.search(r'(20\d{2})', delivery_date or '')
    return int(m.group(1)) if m else None


def _strip_catalog_item(p: Dict) -> Dict:
    """Keep only what listing cards and filtering need — the catalog is cached whole."""
    return {
        'id': p.get('id'),
        'title': p.get('title') or '',
        'developer_name': p.get('developer_name') or '',
        'city': p.get('city') or '',
        'district': p.get('district') or '',
        'property_type': p.get('property_type') or '',
        'bedrooms_from': p.get('bedrooms_from'),
        'bedrooms_to': p.get('bedrooms_to'),
        'bedroom_labels': p.get('bedroom_labels') or '',
        'price_from': p.get('price_from'),
        'price_to': p.get('price_to'),
        'area_from': p.get('area_from'),
        'area_to': p.get('area_to'),
        'property_status_name': p.get('property_status_name') or '',
        'sales_status_name': p.get('sales_status_name') or '',
        'delivery_date': p.get('delivery_date') or '',
        'cover': p.get('cover'),
        'created_at': p.get('created_at') or '',
    }


CATALOG_BACKUP_KEY = 'xopp_catalog_backup_v1'
CATALOG_BACKUP_TTL = 7 * 24 * 3600
CATALOG_PARTIAL_TTL = 5 * 60


def _fetch_catalog_page(page: int, retries: int = 3) -> Optional[Dict]:
    """One catalog page, retrying transient errors and honoring 429 Retry-After."""
    for attempt in range(retries):
        try:
            r = requests.get(
                f"{settings.XOPP_API_BASE.rstrip('/')}/properties/",
                params={'page': page, 'page_size': 100},
                headers={'X-API-Key': settings.XOPP_API_KEY},
                timeout=settings.API_TIMEOUT,
            )
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                wait = int(r.headers.get('Retry-After') or 0) or (2 ** attempt * 2)
                logger.warning(f"Catalog page {page}: rate limited, waiting {wait}s")
                time.sleep(min(wait, 30))
                continue
            logger.error(f"Catalog page {page}: HTTP {r.status_code}")
        except requests.RequestException as e:
            logger.warning(f"Catalog page {page} attempt {attempt + 1} failed: {e}")
            time.sleep(1 + attempt)
    return None


def get_catalog() -> List[Dict]:
    """The full property catalog (stripped), newest first. Cached 45 minutes.

    A partial fetch is never cached over a known-good full catalog: on failure
    the last complete catalog (kept 7 days) is served instead, and the retry
    happens again in a few minutes.
    """
    cached = cache.get(CATALOG_CACHE_KEY)
    if cached is not None:
        return cached

    catalog, page, complete = [], 1, False
    while True:
        data = _fetch_catalog_page(page)
        if data is None:
            break
        catalog.extend(_strip_catalog_item(p) for p in data.get('results', []))
        if not data.get('next'):
            complete = True
            break
        page += 1

    if complete:
        cache.set(CATALOG_CACHE_KEY, catalog, CATALOG_TTL)
        cache.set(CATALOG_BACKUP_KEY, catalog, CATALOG_BACKUP_TTL)
        logger.info(f"X-OPP catalog cached: {len(catalog)} properties")
        return catalog

    backup = cache.get(CATALOG_BACKUP_KEY)
    best = backup if backup and len(backup) > len(catalog) else catalog
    logger.error(
        f"Catalog fetch incomplete at page {page} ({len(catalog)} items); "
        f"serving {'backup' if best is backup else 'partial'} of {len(best)} for {CATALOG_PARTIAL_TTL}s"
    )
    if best:
        cache.set(CATALOG_CACHE_KEY, best, CATALOG_PARTIAL_TTL)
    return best


DEVELOPERS_CACHE_KEY = 'xopp_developers_v1'


def get_developers() -> List[Dict]:
    """All developers from the partner API, sorted by name. Cached 45 minutes.

    Returns [] (uncached) if the walk cannot complete.
    """
    cached = cache.get(DEVELOPERS_CACHE_KEY)
    if cached is not None:
        return cached

    devs, page = [], 1
    while True:
        result = XOPPService._get('/developers/', {'page': page, 'page_size': 100})
        if not result['success']:
            logger.error(f"Developers fetch failed on page {page}: {result['error']}")
            return []  # incomplete — don't cache
        data = result['data']
        devs.extend(data.get('results', []))
        if not data.get('next'):
            break
        page += 1

    cache.set(DEVELOPERS_CACHE_KEY, devs, CATALOG_TTL)
    logger.info(f"X-OPP developers cached: {len(devs)}")
    return devs


def get_available_counts(property_ids) -> Dict:
    """{property_id: n} of units with status 'available', or None when unknown.

    Cached per property; cache misses are fetched concurrently so a page of
    results enriches in one round-trip time instead of one per property.
    """
    from concurrent.futures import ThreadPoolExecutor

    result, misses = {}, []
    for pid in property_ids:
        cached = cache.get(f'xopp_avail_{pid}')
        if cached is not None:
            result[pid] = cached
        else:
            misses.append(pid)

    def fetch(pid):
        try:
            r = requests.get(
                f"{settings.XOPP_API_BASE.rstrip('/')}/properties/{pid}/units/",
                params={'status': 'available', 'page_size': 1},
                headers={'X-API-Key': settings.XOPP_API_KEY},
                timeout=settings.API_TIMEOUT,
            )
            if r.status_code == 200:
                return pid, r.json().get('count', 0)
            if r.status_code == 404:
                return pid, 0
        except requests.RequestException as e:
            logger.warning(f"available-count fetch failed for {pid}: {e}")
        return pid, None

    if misses:
        with ThreadPoolExecutor(max_workers=min(8, len(misses))) as ex:
            for pid, count in ex.map(fetch, misses):
                result[pid] = count
                if count is not None:
                    cache.set(f'xopp_avail_{pid}', count, CACHE_TTL)
    return result


def to_card(p: Dict) -> Dict:
    """Map a catalog item to the legacy shape the frontend JS renders."""
    title = p['title'] or 'Property'
    return {
        'id': p['id'],
        'slug': slugify(title) or 'property',
        'title': {'en': title},
        'city': {'name': {'en': p['city']}},
        'district': {'name': {'en': p['district']}},
        'developer': {'name': p['developer_name']},
        'property_type': classify_property_type(p['property_type']),
        'unit_types': p['property_type'],
        'bedrooms': p['bedroom_labels'] or 'N/A',
        'low_price': p['price_from'] or None,
        'currency': 'AED',
        'min_area': p['area_from'],
        'max_area': p['area_to'],
        'area': p['area_from'] or 'N/A',
        'price': p['price_from'],
        'cover': p['cover'],
        'image': p['cover'],
        'location': ', '.join(x for x in (p['district'], p['city']) if x) or 'Dubai',
        'property_status': p['property_status_name'],
        'sales_status': p['sales_status_name'],
        'delivery_date': p['delivery_date'],
        'detail_url': f"/property/{slugify(title) or 'property'}-{p['id']}/",
    }


def _rooms_match(p: Dict, rooms: str) -> bool:
    rooms = str(rooms).strip().lower()
    plus = rooms.endswith('+')
    try:
        wanted = float(rooms.rstrip('+').replace('studio', '0'))
    except ValueError:
        return True
    lo = p['bedrooms_from'] if p['bedrooms_from'] is not None else p['bedrooms_to']
    hi = p['bedrooms_to'] if p['bedrooms_to'] is not None else p['bedrooms_from']
    if lo is None:
        return False
    if plus:
        return hi >= wanted
    return lo <= wanted <= hi


def filter_catalog(catalog: List[Dict], filters: Dict) -> List[Dict]:
    """Apply the site's filter form to the catalog, server-side."""
    out = catalog

    city = (filters.get('city') or '').strip().lower()
    if city:
        out = [p for p in out if city in p['city'].lower()]

    district = (filters.get('district') or '').strip().lower()
    if district:
        out = [p for p in out if district in p['district'].lower()]

    unit_type = (filters.get('unit_type') or '').strip().lower()
    if unit_type:
        out = [p for p in out if unit_type in p['property_type'].lower()]

    prop_class = (filters.get('property_type') or '').strip().lower()
    if prop_class in ('residential', 'commercial'):
        out = [p for p in out if classify_property_type(p['property_type']).lower() == prop_class]

    rooms = filters.get('rooms')
    if rooms:
        out = [p for p in out if _rooms_match(p, rooms)]

    year = filters.get('delivery_year')
    if year:
        out = [p for p in out if delivery_year(p['delivery_date']) == int(year)]

    low_price = filters.get('low_price') or filters.get('min_price')
    if low_price:
        out = [p for p in out if p['price_from'] and p['price_from'] >= int(low_price)]

    max_price = filters.get('max_price')
    if max_price:
        out = [p for p in out if p['price_from'] and p['price_from'] <= int(max_price)]

    min_area = filters.get('min_area')
    if min_area:
        out = [p for p in out if (p['area_to'] or p['area_from'] or 0) >= int(min_area)]

    max_area = filters.get('max_area')
    if max_area:
        out = [p for p in out if p['area_from'] and p['area_from'] <= int(max_area)]

    title = (filters.get('title') or filters.get('search') or '').strip().lower()
    if title:
        out = [p for p in out if title in p['title'].lower()]

    developer = (filters.get('developer') or '').strip().lower()
    if developer:
        out = [p for p in out if developer in p['developer_name'].lower()]

    status = (filters.get('property_status') or '').strip().lower()
    if status:
        out = [p for p in out if p['property_status_name'].lower() == status]

    sales_status = (filters.get('sales_status') or '').strip().lower()
    if sales_status:
        out = [p for p in out if sales_status in p['sales_status_name'].lower()]

    return out
