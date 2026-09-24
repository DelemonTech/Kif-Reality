from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from main.models import BlogPost
from main.xopp_service import get_catalog, property_path
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class StaticViewSitemap(Sitemap):
    """Sitemap for all static pages."""
    priority = 0.8
    changefreq = "monthly"

    def items(self):
        # Include only static named routes from urls.py
        return [
            'index',
            'about',
            'blogs',
            'careers',
            'contact',
            'privacy-policy',
            'terms-and-conditions',
            'property_directory',
            'rera-compliance',
            # Landing pages
            'retail-spaces',
            'secondary-residential-properties',
            'commercial-properties',
            'luxury-villas-townhouses',
            'beachfront-Properties',
            'off-plan-residential-properties',
            'labour-camps',
            'warehouses-for-sale',
            'plots-for-sale',
        ]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(Sitemap):
    """Sitemap for all published blog posts."""
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return BlogPost.objects.filter(status='published')

    def lastmod(self, obj):
        return obj.updated_at


class PropertySitemap(Sitemap):
    """Every property in the X-OPP catalog — the same source and URL scheme as
    the property pages, so each entry is a final 200 URL (no redirect)."""
    changefreq = 'daily'
    priority = 0.9
    protocol = 'https'
    limit = 250  # Django auto-splits into multiple sitemaps

    def items(self):
        # cached_only: never walk the partner API inside a crawler request;
        # the Celery refresh keeps the catalog warm.
        return [p for p in get_catalog(cached_only=True) if p.get('id')]

    def location(self, obj):
        return property_path(obj)
