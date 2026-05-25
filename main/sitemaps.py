# main/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.core.cache import cache
from main.models import BlogPost
import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MICROSERVICE_API =  os.getenv("MICROSERVICE_API")

PROPERTIES_API_URL = f'{MICROSERVICE_API}/properties/large/'


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return [
            'index', 'about', 'properties', 'contact', 'blogs',
            'retail', 'second', 'commercial', 'luxury', 'beach',
            'offplan', 'labour', 'warehouse', 'plots', 'mansions',
            'privacy-policy', 'terms-conditions', 'rera-compliance'
        ]

    def location(self, item):
        return reverse(item)


class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return BlogPost.objects.filter(status="published")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('blog_detail', kwargs={'slug': obj.slug})


class PropertySitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9
    protocol = 'https'
    limit = 250  # Django auto-splits into multiple sitemap pages

    def items(self):
        """
        Fetch ALL 1712 properties from API
        Django will automatically split into pages of 250
        """
        cache_key = 'sitemap_all_properties_v10'
        cached = cache.get(cache_key)
        
        if cached:
            logger.info(f"[SITEMAP] ✅ Cache: {len(cached)} properties")
            return cached

        all_properties = []
        page = 1
        max_pages = 10  # 1712 / 250 = ~7 pages

        logger.info("[SITEMAP] 🚀 Fetching all properties...")
        
        while page <= max_pages:
            try:
                response = requests.get(
                    PROPERTIES_API_URL,
                    params={'page': page},
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"[SITEMAP] HTTP {response.status_code}")
                    break

                data = response.json()
                
                if not data.get('status'):
                    logger.warning(f"[SITEMAP] Status false on page {page}")
                    break

                # Extract results from: data['data']['results']
                data_block = data.get('data', {})
                results = data_block.get('results', [])
                
                if not results:
                    logger.info(f"[SITEMAP] No results on page {page}")
                    break

                # Store minimal data for each property
                for prop in results:
                    if isinstance(prop, dict) and prop.get('id'):
                        all_properties.append({
                            'id': prop['id'],
                            'title': prop.get('title', ''),
                        })

                logger.info(f"[SITEMAP] Page {page}: {len(results)} properties | Total: {len(all_properties)}")

                # Check if there's a next page
                if not data_block.get('next_page_url'):
                    logger.info(f"[SITEMAP] ✅ Last page reached")
                    break

                page += 1

            except Exception as e:
                logger.error(f"[SITEMAP] Error on page {page}: {e}")
                break

        logger.info(f"[SITEMAP] ✅ Total fetched: {len(all_properties)} properties")

        # Cache for 6 hours
        if all_properties:
            cache.set(cache_key, all_properties, 60 * 60 * 6)

        return all_properties

    def location(self, obj):
        """
        Generate URL for each property
        obj is a dict with 'id' key
        """
        if isinstance(obj, dict) and obj.get('id'):
            # Direct URL string - no reverse() needed
            return f"/property/{obj['id']}/"
        return None

    def lastmod(self, obj):
        """No lastmod available from this API endpoint"""
        return None