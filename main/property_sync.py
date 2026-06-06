# # Create: main/services/property_sync.py

# import requests
# import logging
# from django.conf import settings
# from main.models import Property
# from django.db import transaction
# from typing import Dict, List

# logger = logging.getLogger(__name__)


# class PropertySyncService:
#     """Service to sync properties from external API to database"""
    
#     @staticmethod
#     def extract_multilang_field(data, field_name, default=''):
#         """
#         Extract English value from multilingual field.
#         Handles nested structures like: {'en': 'value'} or {'name': {'en': 'value'}}
#         """
#         field_data = data.get(field_name, {})
        
#         if isinstance(field_data, dict):
#             # Check if it has direct 'en' key
#             if 'en' in field_data:
#                 return field_data.get('en', default)
#             # Check if it has nested 'name' with 'en'
#             elif 'name' in field_data:
#                 name_data = field_data.get('name', {})
#                 if isinstance(name_data, dict):
#                     return name_data.get('en', default)
#                 return name_data or default
#             # If dict but no 'en' or 'name', try to get first value
#             values = list(field_data.values())
#             return values[0] if values else default
        
#         # If not dict, return as is or default
#         return field_data or default
    
#     @staticmethod
#     def map_property_type(property_type_id):
#         """
#         Map property type ID to readable text.
#         Based on your view: 3 = Commercial, 20 = Residential
#         """
#         property_type_id = str(property_type_id) if property_type_id else ''
        
#         if property_type_id == '3':
#             return 'commercial'
#         elif property_type_id == '20':
#             return 'residential'
#         else:
#             return 'residential'  # Default to residential
    
#     @staticmethod
#     def sync_property_from_api_data(api_property: Dict) -> Property:
#         """
#         Create or update a Property from API data.
#         Matches the exact structure from your properties view.
#         Returns the Property instance.
#         """
#         api_id = api_property.get('id')
#         if not api_id:
#             logger.warning("Property missing 'id' field, skipping")
#             return None
        
#         # Extract title (multilingual)
#         title_data = api_property.get('title', {})
#         if isinstance(title_data, dict):
#             title = title_data.get('en', 'Untitled Property')
#         else:
#             title = title_data or 'Untitled Property'
        
#         # Extract city (nested structure: city.name.en)
#         city_data = api_property.get('city', {})
#         city = ''
#         if isinstance(city_data, dict):
#             name_data = city_data.get('name', {})
#             if isinstance(name_data, dict):
#                 city = name_data.get('en', '')
#             else:
#                 city = name_data or ''
        
#         # Extract district (nested structure: district.name.en)
#         district_data = api_property.get('district', {})
#         district = ''
#         if isinstance(district_data, dict):
#             name_data = district_data.get('name', {})
#             if isinstance(name_data, dict):
#                 district = name_data.get('en', '')
#             else:
#                 district = name_data or ''
        
#         # Extract developer (nested structure: developer.name.en)
#         developer_data = api_property.get('developer', {})
#         developer = ''
#         if isinstance(developer_data, dict):
#             name_data = developer_data.get('name', {})
#             if isinstance(name_data, dict):
#                 developer = name_data.get('en', '')
#             else:
#                 developer = name_data or ''
        
#         # Map property type (3 = commercial, 20 = residential)
#         property_type_id = api_property.get('property_type')
#         property_type = PropertySyncService.map_property_type(property_type_id)
        
#         # Create or update property
#         property_obj, created = Property.objects.update_or_create(
#             api_id=api_id,
#             defaults={
#                 'title': title,
#                 'description': PropertySyncService.extract_multilang_field(
#                     api_property, 'description', ''
#                 ),
#                 'property_type': property_type,
#                 'unit_type': api_property.get('unit_type', ''),
#                 'city': city,
#                 'district': district,
#                 'low_price': api_property.get('low_price'),
#                 'high_price': api_property.get('high_price'),
#                 'min_area': api_property.get('min_area'),
#                 'max_area': api_property.get('max_area'),
#                 'bedrooms': api_property.get('bedrooms'),
#                 'bathrooms': api_property.get('bathrooms'),
#                 'rooms': api_property.get('rooms', ''),
#                 'cover_image': api_property.get('cover', ''),  # API uses 'cover' field
#                 'property_status': api_property.get('property_status', ''),
#                 'sales_status': api_property.get('sales_status', ''),
#                 'delivery_year': api_property.get('delivery_year'),
#                 'developer': developer,
#                 'is_featured': api_property.get('is_featured', False) or api_property.get('featured', False),
#                 'is_active': True,
#             }
#         )
        
#         action = "Created" if created else "Updated"
#         logger.info(f"{action} property: {title} (ID: {api_id})")
        
#         return property_obj
    
#     @staticmethod
#     def sync_all_properties(max_pages: int = None) -> Dict:
#         """
#         Fetch all properties from API and sync to database.
#         Matches your API structure with 'data.data.results' nesting.
        
#         Args:
#             max_pages: Maximum number of pages to fetch (None = all pages)
        
#         Returns:
#             Dict with sync statistics
#         """
#         stats = {
#             'total_fetched': 0,
#             'created': 0,
#             'updated': 0,
#             'errors': 0,
#             'pages_processed': 0
#         }
        
#         current_page = 1
#         has_more_pages = True
        
#         logger.info("Starting property sync from API...")
#         print("🔄 Starting property sync from API...")
        
#         while has_more_pages:
#             if max_pages and current_page > max_pages:
#                 logger.info(f"Reached max_pages limit ({max_pages})")
#                 print(f"✋ Reached max_pages limit ({max_pages})")
#                 break
            
#             try:
#                 # Fetch page from API
#                 logger.info(f"Fetching page {current_page}...")
#                 print(f"📄 Fetching page {current_page}...")
                
#                 response = requests.post(
#                     settings.PROPERTIES_API_URL,
#                     params={'page': current_page},
#                     json={},  # Empty filters to get all properties
#                     headers={'Content-Type': 'application/json'},
#                     timeout=settings.API_TIMEOUT
#                 )
#                 response.raise_for_status()
#                 data = response.json()
                
#                 # Check API response status (your API returns {status: true/false, data: {...}})
#                 if not data.get('status'):
#                     logger.error(f"API returned error status on page {current_page}")
#                     print(f"❌ API returned error status on page {current_page}")
#                     break
                
#                 # Navigate nested structure: data.data.results
#                 data_block = data.get('data', {})
#                 results = data_block.get('results', [])
                
#                 if not results:
#                     logger.info(f"No results on page {current_page}, stopping")
#                     print(f"⚠️ No results on page {current_page}, stopping")
#                     break
                
#                 print(f"✅ Found {len(results)} properties on page {current_page}")
                
#                 # Process each property
#                 with transaction.atomic():
#                     for api_property in results:
#                         try:
#                             # Check if property already exists
#                             api_id = api_property.get('id')
#                             existed_before = Property.objects.filter(api_id=api_id).exists()
                            
#                             property_obj = PropertySyncService.sync_property_from_api_data(api_property)
                            
#                             if property_obj:
#                                 stats['total_fetched'] += 1
#                                 if existed_before:
#                                     stats['updated'] += 1
#                                 else:
#                                     stats['created'] += 1
#                         except Exception as e:
#                             stats['errors'] += 1
#                             logger.error(f"Error syncing property {api_property.get('id')}: {str(e)}")
#                             print(f"❌ Error syncing property {api_property.get('id')}: {str(e)}")
                
#                 stats['pages_processed'] += 1
                
#                 # Check if there are more pages
#                 next_page_url = data_block.get('next_page_url')
#                 has_more_pages = next_page_url is not None
#                 current_page += 1
                
#             except requests.exceptions.RequestException as e:
#                 logger.error(f"API request failed on page {current_page}: {str(e)}")
#                 print(f"❌ API request failed on page {current_page}: {str(e)}")
#                 stats['errors'] += 1
#                 break
#             except Exception as e:
#                 logger.error(f"Unexpected error on page {current_page}: {str(e)}")
#                 print(f"❌ Unexpected error on page {current_page}: {str(e)}")
#                 stats['errors'] += 1
#                 break
        
#         logger.info(f"Property sync completed: {stats}")
#         print(f"\n✅ Property sync completed!")
#         print(f"📊 Stats: {stats}")
#         return stats
    
#     @staticmethod
#     def sync_single_property(api_id: int) -> Property:
#         """
#         Fetch and sync a single property by its API ID.
#         """
#         try:
#             # Use the detail endpoint format from your views
#             url = f"{settings.PROPERTIES_API_URL.rstrip('/')}/{api_id}"
#             print(f"🔍 Fetching single property from: {url}")
            
#             response = requests.get(url, timeout=settings.API_TIMEOUT)
#             response.raise_for_status()
#             data = response.json()
            
#             if data.get('status') and data.get('data'):
#                 return PropertySyncService.sync_property_from_api_data(data['data'])
#             else:
#                 logger.error(f"Failed to fetch property {api_id} from API")
#                 print(f"❌ Failed to fetch property {api_id} from API")
#                 return None
                
#         except Exception as e:
#             logger.error(f"Error syncing single property {api_id}: {str(e)}")
#             print(f"❌ Error syncing single property {api_id}: {str(e)}")
#             return None