from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.core.cache import cache
from django.utils.text import slugify
from main.models import BlogPost
import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MICROSERVICE_API = os.getenv("MICROSERVICE_API")

PROPERTIES_API_URL = f'{MICROSERVICE_API}/properties/large/'


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
            'contact',
            'privacy-policy',
            'terms-and-conditions',
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
            'mansions-for-sale',
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
    changefreq = 'daily'
    priority = 0.9
    protocol = 'https'
    limit = 250  # Django auto-splits into multiple sitemaps

    def items(self):
        # """
        # Fetch ALL 1712 properties from API
        # Django will automatically paginate into multiple sitemap files
        # """
        # cache_key = 'sitemap_all_properties_final'
        # cached = cache.get(cache_key)
        """
        Fetch ALL properties from API with slug and ID
        Django will automatically paginate into multiple sitemap files
        """
        cache_key = 'sitemap_properties_slug_id_format'  # ✅ Updated cache key
        cached = cache.get(cache_key)

        if cached:
            logger.info(f"[SITEMAP] ✅ Cache hit: {len(cached)} properties")
            return cached

        all_properties = []
        page = 1
        # max_pages = 10
        max_pages = 100  # Increased to fetch more pages

        logger.info("[SITEMAP] 🚀 Fetching all properties from API...")

        while page <= max_pages:
            try:
                response = requests.get(
                    PROPERTIES_API_URL,
                    params={'page': page},
                    timeout=30
                )

                if response.status_code != 200:
                    logger.error(f"[SITEMAP] HTTP {response.status_code} on page {page}")
                    break

                data = response.json()

                if not data.get('status'):
                    logger.warning(f"[SITEMAP] Status false on page {page}")
                    break

                # Extract: data['data']['results']
                data_block = data.get('data', {})
                results = data_block.get('results', [])

                if not results:
                    logger.info(f"[SITEMAP] No results on page {page}")
                    break


                # Store each property as dict with id
                # for prop in results:
                #     if isinstance(prop, dict) and prop.get('id'):
                #         all_properties.append({
                #             'id': prop['id'],
                #             'title': prop.get('title', '')
                #         })

                 # ✅ Store each property with id, slug, and title
                for prop in results:
                    if isinstance(prop, dict) and prop.get('id'):
                        # Extract title - matches your views.py logic exactly
                        title_data = prop.get('title', {})
                        if isinstance(title_data, dict):
                            title = title_data.get('en', 'Untitled')
                        else:
                            title = title_data or 'Untitled'
                        
                        # Get slug from API or create from title - matches views.py
                        slug = prop.get('slug') or slugify(title)
                        
                        all_properties.append({
                            'id': prop['id'],
                            'slug': slug,
                            'title': title
                        })
                
                logger.info(f"[SITEMAP] Page {page}: {len(results)} properties | Total: {len(all_properties)}")

                # Check if there's a next page
                if not data_block.get('next_page_url'):
                    logger.info("[SITEMAP] ✅ Reached last page")
                    break

                page += 1

            except Exception as e:
                logger.error(f"[SITEMAP] Error on page {page}: {str(e)}")
                break

        logger.info(f"[SITEMAP] ✅ Total fetched: {len(all_properties)} properties")

        # Cache for 6 hours
        if all_properties:
            cache.set(cache_key, all_properties, 60 * 60 * 6)

        return all_properties

    def location(self, obj):
        
        """
        Generate URL for each property in slug-id format
        Format: /property/vue-doree-2492/
        This matches the URL pattern in urls.py: path('property/<slug:slug>-<int:pk>/'...)
        """
        if isinstance(obj, dict) and obj.get('id') and obj.get('slug'):
            # ✅ Return slug-id format - matches your actual URLs
            return f"/property/{obj['slug']}-{obj['id']}/"
        
        # Fallback if slug is missing (shouldn't happen but just in case)
        if isinstance(obj, dict) and obj.get('id'):
            logger.warning(f"[SITEMAP] Missing slug for property {obj['id']}, using ID only")
            return f"/property/{obj['id']}/"
        
        # Debug log if something's wrong
        logger.warning(f"[SITEMAP] Invalid object in location(): {type(obj)}")
        return None

    def lastmod(self, obj):
        """No lastmod data available from this API endpoint"""
        return None
        
    #     """
    #     Generate URL for each property
    #     obj should be a dict with 'id' key
    #     """
    #     if isinstance(obj, dict) and obj.get('id'):
    #         return f"/property/{obj['id']}/"
        
    #     # Debug log if something's wrong
    #     logger.warning(f"[SITEMAP] Invalid object in location(): {type(obj)}")
    #     return None

    # def lastmod(self, obj):
    #     """No lastmod data available from this API endpoint"""
    #     return None