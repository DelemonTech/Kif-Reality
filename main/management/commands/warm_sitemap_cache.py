# main/management/commands/warm_sitemap_cache.py

from django.core.management.base import BaseCommand
from django.core.cache import cache
import requests
import time

API_URL = 'http://54.197.194.173/api/properties/large/'
API_PROPERTIES_PER_PAGE = 50
SITEMAP_PROPERTIES_PER_PAGE = 250
CACHE_TIMEOUT = 3600


class Command(BaseCommand):
    help = 'Pre-warm sitemap cache by fetching all property pages from API'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(self.style.WARNING('WARMING SITEMAP CACHE'))
        self.stdout.write(self.style.WARNING('='*60))
        self.stdout.write(f'API: {API_URL}')
        self.stdout.write(f'Properties per sitemap page: {SITEMAP_PROPERTIES_PER_PAGE}')
        self.stdout.write('')
        
        # Calculate number of sitemap pages needed
        # With 1692 properties and 250 per page = 7 sitemap pages
        total_properties = 1692  # You know this from API
        total_sitemap_pages = 7
        
        start_time = time.time()
        success_count = 0
        error_count = 0
        
        try:
            for sitemap_page in range(1, total_sitemap_pages + 1):
                self.stdout.write(f'\n📄 Warming sitemap page {sitemap_page}/{total_sitemap_pages}')
                
                # Calculate which API pages to fetch
                api_pages_per_sitemap = SITEMAP_PROPERTIES_PER_PAGE // API_PROPERTIES_PER_PAGE
                start_api_page = ((sitemap_page - 1) * api_pages_per_sitemap) + 1
                end_api_page = start_api_page + api_pages_per_sitemap - 1
                
                properties = []
                
                for api_page in range(start_api_page, end_api_page + 1):
                    self.stdout.write(f'  Fetching API page {api_page}...', ending=' ')
                    
                    try:
                        response = requests.get(
                            API_URL,
                            params={'page': api_page},
                            timeout=30
                        )
                        
                        if response.status_code != 200:
                            self.stdout.write(self.style.ERROR(f'✗ Error {response.status_code}'))
                            continue
                        
                        data = response.json()
                        
                        if not data.get('status'):
                            self.stdout.write(self.style.ERROR('✗ Status false'))
                            continue
                        
                        data_block = data.get('data', {})
                        results = data_block.get('results', [])
                        
                        if not results:
                            self.stdout.write(self.style.WARNING('✗ Empty'))
                            break
                        
                        valid_properties = [
                            prop for prop in results 
                            if isinstance(prop, dict) and prop.get('id')
                        ]
                        
                        properties.extend(valid_properties)
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ {len(valid_properties)} props')
                        )
                        
                        time.sleep(0.2)
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'✗ Error: {e}'))
                        error_count += 1
                        continue
                
                # Cache this sitemap page
                if properties:
                    cache_key = f'sitemap_properties_page_{sitemap_page}'
                    cache.set(cache_key, properties, CACHE_TIMEOUT)
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'  ✓ Cached {len(properties)} properties for sitemap page {sitemap_page}'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ No properties for sitemap page {sitemap_page}'
                        )
                    )
            
            elapsed_time = time.time() - start_time
            
            # Summary
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(self.style.SUCCESS('CACHE WARMING COMPLETED'))
            self.stdout.write(self.style.SUCCESS('='*60))
            self.stdout.write(self.style.SUCCESS(f'✓ Success: {success_count} sitemap pages cached'))
            if error_count > 0:
                self.stdout.write(self.style.WARNING(f'⚠ Errors: {error_count} API calls failed'))
            self.stdout.write(self.style.SUCCESS(f'✓ Time: {elapsed_time:.1f} seconds'))
            self.stdout.write(self.style.SUCCESS(f'✓ Cache expires in: {CACHE_TIMEOUT/60:.0f} minutes'))
            self.stdout.write(self.style.SUCCESS('='*60))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Fatal error: {e}'))