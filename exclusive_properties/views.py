from main.utils import utf8_json_response as JsonResponse
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from .models import ExclusiveProperty, PropertyInquiry
from django.conf import settings
import json

def exclusive_properties_list(request):
    """List view for exclusive properties with comprehensive filtering"""
    properties = ExclusiveProperty.objects.filter(
        is_exclusive=True,
        status__in=['available', 'under_offer']
    ).select_related('assigned_agent').prefetch_related('images', 'amenities')
    
    # Apply comprehensive filters - handle both GET and POST
    if request.method == 'POST':
        # Handle POST request from form submission
        property_type = request.POST.get('property_type', 'residential')
        unit_type = request.POST.get('unit_type')
        city = request.POST.get('city')
        district = request.POST.get('district')
        price_range = request.POST.get('price_range')
        bedrooms = request.POST.get('bedrooms')
        delivery_year = request.POST.get('delivery_year')
        developer = request.POST.get('developer')
        project_name = request.POST.get('project_name')
        property_status = request.POST.get('property_status')
        min_price = request.POST.get('min_price')
        max_price = request.POST.get('max_price')
        min_area = request.POST.get('min_area')
        max_area = request.POST.get('max_area')
    else:
        # Handle GET request (initial page load or URL parameters)
        property_type = request.GET.get('property_type', 'residential')
        unit_type = request.GET.get('unit_type')
        city = request.GET.get('city')
        district = request.GET.get('district')
        price_range = request.GET.get('price_range')
        bedrooms = request.GET.get('bedrooms')
        delivery_year = request.GET.get('delivery_year')
        developer = request.GET.get('developer')
        project_name = request.GET.get('project_name')
        property_status = request.GET.get('property_status')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        min_area = request.GET.get('min_area')
        max_area = request.GET.get('max_area')
    
    # Property type filter (residential/commercial mapping)
    if property_type == 'residential':
        properties = properties.filter(
            property_type__in=['apartment', 'villa', 'townhouse', 'penthouse', 'studio', 'duplex']
        )
    elif property_type == 'commercial':
        # For exclusive properties, we'll treat certain types as commercial
        properties = properties.filter(
            property_type__in=['apartment', 'villa', 'townhouse', 'penthouse', 'duplex']
        )
    
    # Unit type filter
    if unit_type:
        properties = properties.filter(property_type=unit_type)
    
    # Location filters
    if city:
        properties = properties.filter(city__icontains=city)
    
    if district:
        properties = properties.filter(
            Q(district__icontains=district) |
            Q(neighborhood__icontains=district)
        )
    
    # Price range filter
    if price_range:
        if price_range.endswith('+'):
            min_price_val = int(price_range.replace('+', ''))
            properties = properties.filter(price__gte=min_price_val)
        elif '-' in price_range:
            min_price_val, max_price_val = map(int, price_range.split('-'))
            properties = properties.filter(price__gte=min_price_val, price__lte=max_price_val)
    
    # Custom price range
    if min_price and min_price != '0':
        properties = properties.filter(price__gte=float(min_price))
    if max_price and max_price != '100000000':
        properties = properties.filter(price__lte=float(max_price))
    
    # Bedrooms filter
    if bedrooms:
        if bedrooms == 'studio':
            properties = properties.filter(bedrooms=0)
        elif bedrooms == '6+':
            properties = properties.filter(bedrooms__gte=6)
        elif bedrooms.isdigit():
            bedroom_count = int(bedrooms)
            properties = properties.filter(bedrooms=bedroom_count)
    
    # Delivery year filter
    if delivery_year:
        properties = properties.filter(completion_year=delivery_year)
    
    # Developer filter
    if developer:
        properties = properties.filter(developer_name__icontains=developer)
    
    # Project name filter
    if project_name:
        properties = properties.filter(
            Q(title__icontains=project_name) |
            Q(developer_name__icontains=project_name)
        )
    
    # Property status filter
    if property_status:
        if property_status == 'Ready':
            properties = properties.filter(completion_year__lte=timezone.now().year)
        elif property_status == 'Off Plan':
            properties = properties.filter(completion_year__gt=timezone.now().year)
        elif property_status == 'Under Construction':
            properties = properties.filter(completion_year__gt=timezone.now().year)
    
    # Area range filter
    if min_area and min_area != '0':
        properties = properties.filter(area_sqft__gte=float(min_area))
    if max_area and max_area != '50000':
        properties = properties.filter(area_sqft__lte=float(max_area))
    
    # Pagination
    paginator = Paginator(properties, 12)
    page_number = request.GET.get('page') or request.POST.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Enhanced filter options with fallback data
    property_types = ExclusiveProperty.PROPERTY_TYPES
    
    # Get cities with fallback to popular Dubai areas - ensure uniqueness
    cities_raw = list(ExclusiveProperty.objects.values_list('city', flat=True).exclude(city=''))
    # Clean and deduplicate cities (handle case sensitivity and whitespace)
    cities = list(set([city.strip() for city in cities_raw if city and city.strip()]))
    if not cities:
        cities = ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Ras Al Khaimah']
    else:
        # Add popular cities if not already present
        popular_cities = ['Dubai', 'Abu Dhabi', 'Sharjah']
        for city in popular_cities:
            if city not in cities:
                cities.append(city)
    
    # Get districts with fallback to popular Dubai neighborhoods - ensure uniqueness
    districts_raw = list(ExclusiveProperty.objects.values_list('district', flat=True).exclude(district=''))
    # Clean and deduplicate districts (handle case sensitivity and whitespace)
    districts = list(set([district.strip() for district in districts_raw if district and district.strip()]))
    if not districts:
        districts = [
            'Downtown Dubai', 'Dubai Marina', 'Palm Jumeirah', 'Dubai Hills Estate',
            'Business Bay', 'Jumeirah Village Circle', 'Dubai South', 'Palm Jebel Ali',
            'Jumeirah Beach Residence', 'Dubai Creek Harbour', 'Dubai Harbour',
            'Bluewaters Island', 'Dubai Silicon Oasis', 'Dubai Sports City',
            'Dubai Production City', 'Dubai Media City', 'Dubai Internet City'
        ]
    else:
        # Add popular districts if not already present
        popular_districts = [
            'Downtown Dubai', 'Dubai Marina', 'Palm Jumeirah', 'Dubai Hills Estate',
            'Business Bay', 'Jumeirah Village Circle'
        ]
        for district in popular_districts:
            if district not in districts:
                districts.append(district)
    
    # Get developers with fallback - ensure uniqueness
    developers_raw = list(ExclusiveProperty.objects.values_list('developer_name', flat=True).exclude(developer_name=''))
    # Clean and deduplicate developers (handle case sensitivity and whitespace)
    developers = list(set([developer.strip() for developer in developers_raw if developer and developer.strip()]))
    if not developers:
        developers = [
            'Emaar Properties', 'Damac Properties', 'Nakheel', 'Meraas',
            'Dubai Properties', 'Sobha Realty', 'Azizi Developments',
            'Deyaar Development', 'Union Properties', 'Al Habtoor Group'
        ]
    
    # Get completion years with fallback - ensure uniqueness
    completion_years = list(set(ExclusiveProperty.objects.values_list('completion_year', flat=True).exclude(completion_year__isnull=True)))
    if not completion_years:
        current_year = timezone.now().year
        completion_years = list(range(current_year, current_year + 6))  # Current year + 5 years
    else:
        # Sort completion years numerically
        completion_years = sorted(completion_years)
    
    # Debug prints
    print(f"🔍 Debug - Total properties: {properties.count()}")
    print(f"🔍 Debug - Cities found: {cities}")
    print(f"🔍 Debug - Districts found: {districts}")
    print(f"🔍 Debug - Developers found: {developers}")
    print(f"🔍 Debug - Completion years found: {completion_years}")
    
    # Clean filter values to ensure empty strings don't get selected
    def clean_filter_value(value):
        if not value or not value.strip():
            return None
        return value.strip()
    
    context = {
        'properties': page_obj,
        'property_types': property_types,
        'cities': sorted(cities),
        'districts': sorted(districts),
        'developers': sorted(developers),
        'completion_years': completion_years,
        'total_count': properties.count(),
        'filters': {
            'property_type': clean_filter_value(property_type),
            'unit_type': clean_filter_value(unit_type),
            'city': clean_filter_value(city),
            'district': clean_filter_value(district),
            'price_range': clean_filter_value(price_range),
            'bedrooms': clean_filter_value(bedrooms),
            'delivery_year': clean_filter_value(delivery_year),
            'developer': clean_filter_value(developer),
            'project_name': clean_filter_value(project_name),
            'property_status': clean_filter_value(property_status),
            'min_price': clean_filter_value(min_price),
            'max_price': clean_filter_value(max_price),
            'min_area': clean_filter_value(min_area),
            'max_area': clean_filter_value(max_area),
            'MICROSERVICE_API': settings.MICROSERVICE_API,  
        }
    }
    
    return render(request, 'properties/exclusive_list.html', context)


def exclusive_property_detail(request, slug):
    """Detail view for individual exclusive property"""
    property_obj = get_object_or_404(
        ExclusiveProperty,
        slug=slug,
        is_exclusive=True
    )
    
    # Increment view count
    property_obj.view_count += 1
    property_obj.save(update_fields=['view_count'])
    
    # Get related properties
    related_properties = ExclusiveProperty.objects.filter(
        is_exclusive=True,
        status__in=['available', 'under_offer'],
        district=property_obj.district
    ).exclude(id=property_obj.id)[:3]
    
    context = {
        'property': property_obj,
        'related_properties': related_properties,
        'images': property_obj.images.all(),
        'amenities': property_obj.amenities.all(),
        'MICROSERVICE_API':settings.MICROSERVICE_API,
    }
    
    return render(request, 'properties/exclusive_detail.html', context)


@require_POST
@csrf_exempt
def submit_property_inquiry(request):
    """Handle property inquiry form submissions"""
    try:
        data = json.loads(request.body)
        
        property_id = data.get('property_id')
        property_obj = get_object_or_404(ExclusiveProperty, id=property_id)
        
        inquiry = PropertyInquiry.objects.create(
            property=property_obj,
            inquiry_type=data.get('inquiry_type', 'info'),
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone', ''),
            message=data.get('message', ''),
            preferred_contact_method=data.get('contact_method', 'email'),
            budget_min=data.get('budget_min'),
            budget_max=data.get('budget_max'),
        )
        
        # Increment inquiry count
        property_obj.inquiry_count += 1
        property_obj.save(update_fields=['inquiry_count'])
        
        # Send notification email (implement as needed)
        # send_inquiry_notification.delay(inquiry.id)
        
        return JsonResponse({
            'success': True,
            'message': 'Your inquiry has been submitted successfully. We will contact you soon.'
        }, json_dumps_params={'ensure_ascii': False})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }, status=400, json_dumps_params={'ensure_ascii': False})


@require_POST
@csrf_exempt
def exclusive_properties_filter_api(request):
    """API endpoint for AJAX filtering of exclusive properties"""
    try:
        data = json.loads(request.body)
        
        properties = ExclusiveProperty.objects.filter(
            is_exclusive=True,
            status__in=['available', 'under_offer']
        ).select_related('assigned_agent').prefetch_related('images', 'amenities')
        
        # Apply filters from request data
        property_type = data.get('property_type', 'residential')
        unit_type = data.get('unit_type')
        city = data.get('city')
        district = data.get('district')
        price_range = data.get('price_range')
        bedrooms = data.get('bedrooms')
        delivery_year = data.get('delivery_year')
        developer = data.get('developer')
        project_name = data.get('project_name')
        property_status = data.get('property_status')
        min_price = data.get('min_price')
        max_price = data.get('max_price')
        min_area = data.get('min_area')
        max_area = data.get('max_area')
        
        # Property type filter (residential/commercial mapping)
        if property_type == 'residential':
            properties = properties.filter(
                property_type__in=['apartment', 'villa', 'townhouse', 'penthouse', 'studio', 'duplex']
            )
        elif property_type == 'commercial':
            properties = properties.filter(
                property_type__in=['apartment', 'villa', 'townhouse', 'penthouse', 'duplex']
            )
        
        # Unit type filter
        if unit_type:
            properties = properties.filter(property_type=unit_type)
        
        # Location filters
        if city:
            properties = properties.filter(city__icontains=city)
        
        if district:
            properties = properties.filter(
                Q(district__icontains=district) |
                Q(neighborhood__icontains=district)
            )
        
        # Price range filter
        if price_range:
            if price_range.endswith('+'):
                min_price_val = int(price_range.replace('+', ''))
                properties = properties.filter(price__gte=min_price_val)
            elif '-' in price_range:
                min_price_val, max_price_val = map(int, price_range.split('-'))
                properties = properties.filter(price__gte=min_price_val, price__lte=max_price_val)
        
        # Custom price range
        if min_price and min_price != '0':
            properties = properties.filter(price__gte=float(min_price))
        if max_price and max_price != '100000000':
            properties = properties.filter(price__lte=float(max_price))
        
        # Bedrooms filter
        if bedrooms:
            if bedrooms == 'studio':
                properties = properties.filter(bedrooms=0)
            elif bedrooms == '6+':
                properties = properties.filter(bedrooms__gte=6)
            elif bedrooms.isdigit():
                bedroom_count = int(bedrooms)
                properties = properties.filter(bedrooms=bedroom_count)
        
        # Delivery year filter
        if delivery_year:
            properties = properties.filter(completion_year=delivery_year)
        
        # Developer filter
        if developer:
            properties = properties.filter(developer_name__icontains=developer)
        
        # Project name filter
        if project_name:
            properties = properties.filter(
                Q(title__icontains=project_name) |
                Q(developer_name__icontains=project_name)
            )
        
        # Property status filter
        if property_status:
            if property_status == 'Ready':
                properties = properties.filter(completion_year__lte=timezone.now().year)
            elif property_status == 'Off Plan':
                properties = properties.filter(completion_year__gt=timezone.now().year)
            elif property_status == 'Under Construction':
                properties = properties.filter(completion_year__gt=timezone.now().year)
        
        # Area range filter
        if min_area and min_area != '0':
            properties = properties.filter(area_sqft__gte=float(min_area))
        if max_area and max_area != '50000':
            properties = properties.filter(area_sqft__lte=float(max_area))
        
        # Pagination
        page = data.get('page', 1)
        paginator = Paginator(properties, 12)
        page_obj = paginator.get_page(page)
        
        # Prepare response data
        properties_data = []
        for prop in page_obj:
            properties_data.append({
                'id': prop.id,
                'title': prop.title,
                'slug': prop.slug,
                'property_type': prop.get_property_type_display(),
                'city': prop.city,
                'district': prop.district,
                'neighborhood': prop.neighborhood,
                'bedrooms': prop.bedrooms,
                'bathrooms': float(prop.bathrooms),
                'area_sqft': prop.area_sqft,
                'price': float(prop.price),
                'formatted_price': prop.formatted_price,
                'cover_image': prop.cover_image.url if prop.cover_image else None,
                'short_description': prop.short_description,
                'status': prop.get_status_display(),
                'developer_name': prop.developer_name,
                'completion_year': prop.completion_year,
                'url': prop.get_absolute_url(),
            })
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'results': properties_data,
                'count': paginator.count,
                'current_page': page_obj.number,
                'last_page': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'next_page_url': page_obj.next_page_number() if page_obj.has_next() else None,
                'prev_page_url': page_obj.previous_page_number() if page_obj.has_previous() else None,
            }
        }, json_dumps_params={'ensure_ascii': False})
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400, json_dumps_params={'ensure_ascii': False})


def exclusive_properties_api(request):
    """API endpoint for exclusive properties (for AJAX calls)"""
    properties = ExclusiveProperty.objects.filter(
        is_exclusive=True,
        status__in=['available', 'under_offer']
    ).values(
        'id', 'title', 'slug', 'property_type', 'district',
        'bedrooms', 'bathrooms', 'area_sqft', 'price',
        'cover_image', 'short_description'
    )
    
    return JsonResponse(list(properties), safe=False)


def get_filter_options(request):
    """API endpoint to get filter options for dynamic loading"""
    try:
        # Get cities
        cities = list(ExclusiveProperty.objects.values_list('city', flat=True).distinct().exclude(city=''))
        if not cities:
            cities = ['Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman', 'Ras Al Khaimah']
        
        # Get districts
        districts = list(ExclusiveProperty.objects.values_list('district', flat=True).distinct().exclude(district=''))
        if not districts:
            districts = [
                'Downtown Dubai', 'Dubai Marina', 'Palm Jumeirah', 'Dubai Hills Estate',
                'Business Bay', 'Jumeirah Village Circle', 'Dubai South', 'Palm Jebel Ali',
                'Jumeirah Beach Residence', 'Dubai Creek Harbour', 'Dubai Harbour',
                'Bluewaters Island', 'Dubai Silicon Oasis', 'Dubai Sports City',
                'Dubai Production City', 'Dubai Media City', 'Dubai Internet City'
            ]
        
        # Get developers
        developers = list(ExclusiveProperty.objects.values_list('developer_name', flat=True).distinct().exclude(developer_name=''))
        if not developers:
            developers = [
                'Emaar Properties', 'Damac Properties', 'Nakheel', 'Meraas',
                'Dubai Properties', 'Sobha Realty', 'Azizi Developments',
                'Deyaar Development', 'Union Properties', 'Al Habtoor Group'
            ]
        
        # Get completion years
        completion_years = list(ExclusiveProperty.objects.values_list('completion_year', flat=True).distinct().exclude(completion_year__isnull=True).order_by('completion_year'))
        if not completion_years:
            current_year = timezone.now().year
            completion_years = list(range(current_year, current_year + 6))
        
        return JsonResponse({
            'status': 'success',
            'data': {
                'cities': sorted(cities),
                'districts': sorted(districts),
                'developers': sorted(developers),
                'completion_years': completion_years,
            }
        }, json_dumps_params={'ensure_ascii': False})
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400, json_dumps_params={'ensure_ascii': False})
