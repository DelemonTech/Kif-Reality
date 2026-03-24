from .utils import utf8_json_response as JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.http import HttpResponse
from urllib.parse import urlparse, parse_qs
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from .models import Contact, ContactMessage
import json
import requests
from django.utils.text import slugify
from .services import PropertyService
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from .models import BlogPost, Category, Tag, Newsletter, Comment
from .forms import NewsletterForm, CommentForm
from django.views.decorators.cache import cache_page
from django.utils.html import strip_tags
import re
import os
from dotenv import load_dotenv

load_dotenv()


def blog_list(request):
    """Display blog list page with pagination and filtering"""
    posts = BlogPost.objects.filter(status='published').select_related(
        'category', 'author'
    ).prefetch_related('tags').order_by('-published_at')
    
    # Get featured post
    featured_post = posts.filter(is_featured=True).first()
    
    # Filter by category if specified
    category_slug = request.GET.get('category')
    if category_slug:
        posts = posts.filter(category__slug=category_slug)
    
    # Filter by tag if specified
    tag_slug = request.GET.get('tag')
    if tag_slug:
        posts = posts.filter(tags__slug=tag_slug)
    
    # Search functionality
    search_query = request.GET.get('q')
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).distinct()
    
    # Exclude featured post from the paginated list
    if featured_post:
        posts = posts.exclude(id=featured_post.id)
    
    # Pagination
    paginator = Paginator(posts, 6)  # 6 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Sidebar data
    categories = Category.objects.annotate(
        posts_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(posts_count__gt=0)
    
    recent_posts = BlogPost.objects.filter(status='published').order_by('-published_at')[:3]
    popular_tags = Tag.objects.annotate(
        posts_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(posts_count__gt=0).order_by('-posts_count')[:10]
    
    context = {
        'featured_post': featured_post,
        'page_obj': page_obj,
        'categories': categories,
        'recent_posts': recent_posts,
        'popular_tags': popular_tags,
        'search_query': search_query,
        'category_slug': category_slug,
        'tag_slug': tag_slug,
        'newsletter_form': NewsletterForm(),
    }
    
    return render(request, 'blogs.html', context)


def blog_detail(request, slug):
    """Display individual blog post with comment functionality"""
    post = get_object_or_404(
        BlogPost.objects.select_related('category', 'author').prefetch_related('tags'),
        slug=slug,
        status='published'
    )
    
    # Increment view count
    post.increment_views()
    
    # Get approved comments
    comments = post.comments.filter(is_approved=True).order_by('-created_at')
    
    # Related posts
    related_posts = BlogPost.objects.filter(
        category=post.category,
        status='published'
    ).exclude(id=post.id)[:3]
    
    # Initialize comment form
    comment_form = CommentForm()
    comment_success = False
    
    # Handle comment form submission
    if request.method == 'POST':
        # Check if it's a comment submission
        if 'comment_submit' in request.POST:
            comment_form = CommentForm(request.POST)
            if comment_form.is_valid():
                try:
                    # Create comment but don't save to database yet
                    comment = comment_form.save(commit=False)
                    # Associate comment with the current post
                    comment.post = post
                    # Save to database
                    comment.save()
                    
                    # Set success flag
                    comment_success = True
                    
                    # Add success message
                    messages.success(
                        request, 
                        'Thank you for your comment! It has been submitted and is awaiting approval.'
                    )
                    
                    # Reset form after successful submission
                    comment_form = CommentForm()
                    
                    # Redirect to prevent re-submission on refresh
                    return redirect('blog_detail', slug=slug)
                    
                except Exception as e:
                    print(f"Error saving comment: {e}")  # For debugging
                    messages.error(
                        request, 
                        'Sorry, there was an error submitting your comment. Please try again.'
                    )
            else:
                # Form has validation errors
                messages.error(
                    request, 
                    'Please correct the errors in your comment form.'
                )
    
    context = {
        'post': post,
        'comments': comments,
        'related_posts': related_posts,
        'comment_form': comment_form,
        'comment_success': comment_success,
    }
    
    return render(request, 'blog_detail.html', context)


def blog_category(request, slug):
    """Display posts by category"""
    category = get_object_or_404(Category, slug=slug)
    posts = BlogPost.objects.filter(
        category=category,
        status='published'
    ).select_related('author').prefetch_related('tags')
    
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'page_obj': page_obj,
        'categories': Category.objects.annotate(
            posts_count=Count('posts', filter=Q(posts__status='published'))
        ).filter(posts_count__gt=0),
    }
    
    return render(request, 'blogs.html', context)


def blog_tag(request, slug):
    """Display posts by tag"""
    tag = get_object_or_404(Tag, slug=slug)
    posts = BlogPost.objects.filter(
        tags=tag,
        status='published'
    ).select_related('category', 'author').prefetch_related('tags')
    
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tag': tag,
        'page_obj': page_obj,
        'popular_tags': Tag.objects.annotate(
            posts_count=Count('posts', filter=Q(posts__status='published'))
        ).filter(posts_count__gt=0).order_by('-posts_count')[:10],
    }
    
    return render(request, 'blogs.html', context)

@require_POST
def newsletter_subscribe(request):
    """Handle newsletter subscription via AJAX"""
    try:
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            newsletter, created = Newsletter.objects.get_or_create(
                email=email,
                defaults={'is_active': True}
            )
            
            if created:
                return JsonResponse({
                    'success': True,
                    'message': 'Thank you for subscribing to our newsletter!'
                }, json_dumps_params={'ensure_ascii': False})
            elif not newsletter.is_active:
                newsletter.is_active = True
                newsletter.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Your subscription has been reactivated!'
                }, json_dumps_params={'ensure_ascii': False})
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'You are already subscribed to our newsletter.'
                }, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a valid email address.'
            }, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        print(f"Newsletter subscription error: {e}")  # For debugging
        return JsonResponse({
            'success': False,
            'message': 'Sorry, there was an error processing your subscription. Please try again.'
        }, json_dumps_params={'ensure_ascii': False})


def blog_search(request):
    """Handle blog search functionality"""
    query = request.GET.get('q', '').strip()
    posts = BlogPost.objects.none()
    
    if query:
        posts = BlogPost.objects.filter(
            Q(title__icontains=query) |
            Q(excerpt__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__name__icontains=query) |
            Q(category__name__icontains=query),
            status='published'
        ).distinct().select_related('category', 'author').prefetch_related('tags')
    
    paginator = Paginator(posts, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': query,
        'results_count': posts.count(),
        'categories': Category.objects.annotate(
            posts_count=Count('posts', filter=Q(posts__status='published'))
        ).filter(posts_count__gt=0),
        'popular_tags': Tag.objects.annotate(
            posts_count=Count('posts', filter=Q(posts__status='published'))
        ).filter(posts_count__gt=0).order_by('-posts_count')[:10],
    }
    
    return render(request, 'blog_search.html', context)

API_BASE = os.getenv("MICROSERVICE_API")
# API_BASE = "http://54.197.194.173/api/properties/large/"


# def index(request):
#     """Homepage with featured properties"""
#     properties_result = PropertyService.get_featured_properties()
    
#     featured = []
#     if properties_result['success']:
#         featured = properties_result.get('data', {}).get('results', [])[:4]  # limit to 4
    
#     context = {
#         'featured_properties': featured,
#         'properties_error': properties_result.get('error'),
#     }
#     return render(request, 'index.html', context)

def index(request):
    """Homepage - properties loaded dynamically via JavaScript"""
    context = {
        'MICROSERVICE_API': settings.MICROSERVICE_API,
    }
    return render(request, 'index.html', context)


def exclusive(request):
    """Homepage with featured properties"""
    # Get featured properties
    # properties_result = PropertyService.get_featured_properties()
    
    # context = {
    #     'featured_properties': properties_result.get('data', {}).get('results', []) if properties_result['success'] else [],
    #     'properties_error': properties_result.get('error'),
    # }
    return render(request, 'properties/exclusive_list.html')

def extract_page_number(url):
    if not url:
        return None
    try:
        from urllib.parse import urlparse, parse_qs
        query = urlparse(url).query
        page = parse_qs(query).get('page', [None])[0]
        return page
    except Exception as e:
        print(f"Pagination extraction error: {e}")
        return None



def properties(request):
    """Ultra-fast properties page – all data loaded by JavaScript"""
    return render(request, 'properties.html', {
        'properties': [],
        'total_count': 0,
        'properties_error': None,
        'MICROSERVICE_API': API_BASE,
    })

# @csrf_exempt
# def properties(request):
#     """
#     Optimized properties view with caching and pagination
#     """
#     # Build filters with EXPLICIT defaults
#     filters = {
#         'limit': '12',      # ✅ ALWAYS set limit to 12
#         'page_size': '12',  # ✅ ALWAYS set page_size to 12
#     }

#     if request.method == 'POST':
#         # Get property type
#         property_type = request.POST.get('property_type', 'residential')
#         filters['property_type'] = property_type
        
#         # Get other filters
#         city = request.POST.get('city')
#         if city:
#             filters['city'] = city
            
#         min_price = request.POST.get('min_price')
#         if min_price:
#             filters['min_price'] = min_price
            
#         max_price = request.POST.get('max_price')
#         if max_price:
#             filters['max_price'] = max_price
            
#         page = request.POST.get('page')
#         if page:
#             filters['page'] = page
        
#         # Override limit if provided (but default is already 12)
#         limit = request.POST.get('limit')
#         if limit:
#             filters['limit'] = limit
            
#         page_size = request.POST.get('page_size')
#         if page_size:
#             filters['page_size'] = page_size

#     else:
#         # GET request - set defaults and get URL params
#         page = request.GET.get('page', '1')
#         filters['page'] = page
        
#         city = request.GET.get('city')
#         if city:
#             filters['city'] = city
            
#         district = request.GET.get('district')
#         if district:
#             filters['district'] = district
        
#         # Override limit if provided in GET
#         limit = request.GET.get('limit')
#         if limit:
#             filters['limit'] = limit
            
#         page_size = request.GET.get('page_size')
#         if page_size:
#             filters['page_size'] = page_size

#     # 🐛 DEBUG: Print filters being sent
#     print("=" * 80)
#     print("📤 FILTERS BEING SENT TO PropertyService:")
#     print(filters)
#     print(f"✅ limit = {filters.get('limit')}")
#     print(f"✅ page_size = {filters.get('page_size')}")
#     print("=" * 80)

#     properties_result = PropertyService.get_properties(filters)
    
#     # 🐛 DEBUG: Print API response
#     if properties_result['success'] and properties_result['data'].get('status') is True:
#         data_block = properties_result['data']['data']
#         results_count = len(data_block.get('results', []))
#         print("=" * 80)
#         print("📥 API RESPONSE:")
#         print(f"✅ Properties returned: {results_count}")
#         print(f"✅ Total count: {data_block.get('count', 0)}")
#         print("=" * 80)
    
#     mapped_properties = []
#     property_type_counts = {'residential': 0, 'commercial': 0}
    
#     if properties_result['success'] and properties_result['data'].get('status') is True:
#         data_block = properties_result['data']['data']
        
#         for prop in data_block.get('results', []):
#             # Extract property data
#             title_data = prop.get('title', {})
#             title = title_data.get('en', 'Untitled') if isinstance(title_data, dict) else (title_data or 'Untitled')

#             city_data = prop.get('city', {})
#             city_name = ''
#             if isinstance(city_data, dict):
#                 name_data = city_data.get('name', {})
#                 city_name = name_data.get('en', '') if isinstance(name_data, dict) else name_data

#             district_data = prop.get('district', {})
#             district_name = ''
#             if isinstance(district_data, dict):
#                 name_data = district_data.get('name', {})
#                 district_name = name_data.get('en', '') if isinstance(name_data, dict) else name_data

#             # Map property type ID to readable text
#             property_type_id = prop.get('property_type')
#             property_type_text = 'Residential'  # Default
#             if property_type_id == '3' or property_type_id == 3:
#                 property_type_text = 'Commercial'
#                 property_type_counts['commercial'] += 1
#             elif property_type_id == '20' or property_type_id == 20:
#                 property_type_text = 'Residential'
#                 property_type_counts['residential'] += 1
#             else:
#                 property_type_counts['residential'] += 1

#             # Get ID and create slug from title or use API slug
#             prop_id = prop.get('id')
#             prop_slug = prop.get('slug') or slugify(title)

#             mapped_properties.append({
#                 'id': prop.get('id'),
#                 'slug': prop_slug,
#                 'title': title,
#                 'image': prop.get('cover'),
#                 'location': f"{city_name}, {district_name}",
#                 'price': prop.get('low_price'),
#                 'area': prop.get('min_area'),
#                 'bedrooms': prop.get('bedrooms'),
#                 'bathrooms': prop.get('bathrooms'),
#                 'property_type': property_type_text,
#                 'description': 'Explore more about this project at the detail page.',
#             })

#         # Pagination logic
#         next_page_num = extract_page_number(data_block.get('next_page_url'))
#         prev_page_num = extract_page_number(data_block.get('previous_page_url'))
#         current_page = data_block.get('current_page')
#         last_page = data_block.get('last_page', (data_block.get('count', 0) // 12) + 1)
        
#         def get_page_range(current_page, last_page, max_display=5):
#             page_range = []

#             if last_page <= max_display + 1:
#                 return list(range(1, last_page + 1))

#             start = max(1, current_page - 2)
#             end = min(start + max_display - 1, last_page - 1)

#             page_range = list(range(start, end + 1))

#             if last_page not in page_range:
#                 page_range.append('...')
#                 page_range.append(last_page)

#             return page_range

#         if next_page_num == '3':
#             prev_page_num = '1'

#         # Determine predominant property type
#         predominant_type = 'commercial' if property_type_counts['commercial'] > property_type_counts['residential'] else 'residential'

#         context = {
#             'properties': mapped_properties,
#             'filters': filters,
#             'total_count': data_block.get('count', 0),
#             'next_page': next_page_num,
#             'prev_page': prev_page_num,
#             'current_page': data_block.get('current_page'),
#             'last_page': data_block.get('last_page', (data_block.get('count', 0) // 12) + 1),
#             'page_range': get_page_range(current_page, last_page), 
#             'properties_error': None,
#             'predominant_property_type': predominant_type,
#         }
#     else:
#         context = {
#             'properties': [],
#             'filters': filters,
#             'total_count': 0,
#             'next_page': None,
#             'prev_page': None,
#             'properties_error': properties_result.get('error', 'Unable to load properties.'),
#             'predominant_property_type': 'residential',
#         }

#     return render(request, 'properties.html', context)

# @csrf_exempt
# def properties(request):
    
#     """
#     Optimized properties view with caching and pagination
#     """
#     # Build filters
#     filters = {
#          'limit': '12',      # ✅ ALWAYS set limit to 12
#         'page_size': '12',  # ✅ ALWAYS set page_size to 12
#     }

#     if request.method == 'POST':
#         # Pass exact frontend property type values as they are
#         filters['property_type'] = request.POST.get('property_type', '')
#         filters['city'] = request.POST.get('city')
#         filters['min_price'] = request.POST.get('min_price')
#         filters['max_price'] = request.POST.get('max_price')
#         filters['page'] = request.POST.get('page')
#         # ✅ ADD THESE CRITICAL LINES to limit results per page
#         filters['limit'] = request.POST.get('limit', '12')  # Default to 12 if not provided
#         filters['page_size'] = request.POST.get('page_size', '12')  # Fallback parameter


#     else:
#         filters['page'] = request.GET.get('page')
#         filters['city'] = request.GET.get('city')
#         filters['district'] = request.GET.get('district')  # Add this line
#         # ✅ ADD THESE for GET requests too
#         filters['limit'] = request.GET.get('limit', '12')
#         filters['page_size'] = request.GET.get('page_size', '12')

#     filters = {k: v for k, v in filters.items() if v}    

#     properties_result = PropertyService.get_properties(filters)
    
#     mapped_properties = []
#     property_type_counts = {'residential': 0, 'commercial': 0}
    
#     if properties_result['success'] and properties_result['data'].get('status') is True:
#         data_block = properties_result['data']['data']  # ✅ THIS is where the real results are
        
#         for prop in data_block.get('results', []):
#             # Extract property data
#             title_data = prop.get('title', {})
#             title = title_data.get('en', 'Untitled') if isinstance(title_data, dict) else (title_data or 'Untitled')

#             city_data = prop.get('city', {})
#             city_name = ''
#             if isinstance(city_data, dict):
#                 name_data = city_data.get('name', {})
#                 city_name = name_data.get('en', '') if isinstance(name_data, dict) else name_data

#             district_data = prop.get('district', {})
#             district_name = ''
#             if isinstance(district_data, dict):
#                 name_data = district_data.get('name', {})
#                 district_name = name_data.get('en', '') if isinstance(name_data, dict) else name_data

#             # Map property type ID to readable text
#             property_type_id = prop.get('property_type')
#             property_type_text = 'Residential'  # Default
#             if property_type_id == '3' or property_type_id == 3:
#                 property_type_text = 'Commercial'
#                 property_type_counts['commercial'] += 1
#             elif property_type_id == '20' or property_type_id == 20:
#                 property_type_text = 'Residential'
#                 property_type_counts['residential'] += 1
#             else:
#                 property_type_counts['residential'] += 1


#             # Get ID and create slug from title or use API slug
#             prop_id = prop.get('id')
#             # Use API slug if available, otherwise create from title
#             prop_slug = prop.get('slug') or slugify(title)

#             mapped_properties.append({
#                 'id': prop.get('id'),
#                 'slug': prop_slug,
#                 'title': title,
#                 'image': prop.get('cover'),
#                 'location': f"{city_name}, {district_name}",
#                 'price': prop.get('low_price'),
#                 'area': prop.get('min_area'),
#                 'bedrooms': prop.get('bedrooms'),
#                 'bathrooms': prop.get('bathrooms'),
#                 'property_type': property_type_text,
#                 'description': 'Explore more about this project at the detail page.',
#             })

            
#          # Pagination logic
#         next_page_num = extract_page_number(data_block.get('next_page_url'))
#         prev_page_num = extract_page_number(data_block.get('previous_page_url'))
#         current_page = data_block.get('current_page')
#         last_page = data_block.get('last_page', (data_block.get('count', 0) // 12) + 1)
        
        
#         def get_page_range(current_page, last_page, max_display=5):
#             page_range = []

#             if last_page <= max_display + 1:
#                 return list(range(1, last_page + 1))

#             start = max(1, current_page - 2)
#             end = min(start + max_display - 1, last_page - 1)

#             page_range = list(range(start, end + 1))

#             if last_page not in page_range:
#                 page_range.append('...')  # Add ellipsis
#                 page_range.append(last_page)

#             return page_range

#         if next_page_num == '3':
#             prev_page_num = '1'

#         # print("➡️ NEXT PAGE:", next_page_num)
#         # print("➡️ PREV PAGE:", prev_page_num)

#         # Determine predominant property type
#         predominant_type = 'commercial' if property_type_counts['commercial'] > property_type_counts['residential'] else 'residential'


#         context = {
#             'properties': mapped_properties,
#             'filters': filters,
#             'total_count': data_block.get('count', 0),
#             'next_page': next_page_num,
#             'prev_page': prev_page_num,
#             'current_page': data_block.get('current_page'),
#             'last_page': data_block.get('last_page', (data_block.get('count', 0) // 12) + 1),  # assuming 12 per page
#             'page_range': get_page_range(current_page, last_page), 
#             'properties_error': None,
#             'predominant_property_type': predominant_type,
#         }
#     else:
#         context = {
#             'properties': [],
#             'filters': filters,
#             'total_count': 0,
#             'next_page': None,
#             'prev_page': None,
#             'properties_error': properties_result.get('error', 'Unable to load properties.'),
#             'predominant_property_type': 'residential',  # Default to residential if no properties
#         }

#     return render(request, 'properties.html', context)


# Add this new function to handle old property URLs
def property_redirect(request, property_id):
    """
    Redirect old /property/ID/ URLs to new /property/slug-ID/ format
    Fetches property from API to get proper slug
    """
    url = f"{API_BASE}/{property_id}"
    
    try:
        resp = requests.get(url, timeout=8)
        
        if resp.status_code == 200:
            data = resp.json()
            
            if data.get("status"):
                prop = data.get("data") or {}
                
                # Get title and generate slug
                title_data = prop.get('title', {})
                title = title_data.get('en', 'property') if isinstance(title_data, dict) else (title_data or 'property')
                
                # Use API slug if available, otherwise create from title
                slug = prop.get('slug') or slugify(title)
                
                # Redirect to new URL format with 301 (permanent)
                return redirect('property_detail', slug=slug, pk=property_id, permanent=True)
    
    except requests.RequestException:
        pass
    
    # If API call fails, create generic slug and redirect
    return redirect('property_detail', slug='property', pk=property_id, permanent=True)


# Cache the view for 15 minutes to reduce API calls
@cache_page(60 * 15)
def property_detail(request, slug, pk):
    """
    Display property details using slug in URL but pk (ID) for API call
    URL format: /property/luxury-villa-palm-jumeirah-2376/
    API call: uses the pk (2376)
    """
    
    print(f"🔍 Property Detail View Called:")
    print(f"   Slug from URL: {slug}")
    print(f"   PK from URL: {pk}")
    
    url = f"{API_BASE}/property/{pk}"
    print(f"   API URL: {url}")
    
    try:
        resp = requests.get(url, timeout=8)
        print(f"   API Response Status: {resp.status_code}")
    except requests.RequestException as e:
        print(f"   ❌ API Request Error: {e}")
        return render(request, "property_detail.html", {
            "property_error": "Failed to retrieve property data."
        })

    if resp.status_code != 200:
        print(f"   ❌ API returned non-200 status")
        return render(request, "property_detail.html", {
            "property_error": "Property not found or API error."
        })
    
    data = resp.json()
    print(f"   API Response Data Keys: {data.keys() if data else 'None'}")
    
    if not data.get("status"):
        print(f"   ❌ API status is False")
        return render(request, "property_detail.html", {
            "property_error": data.get("message") or "API returned error."
        })

    prop = data.get("data") or {}
    print(f"   ✅ Property data retrieved: {prop.get('title', {}).get('en', 'No title')}")
    
    # Clean the description
    if prop.get('description'):
        desc = prop['description']
        if isinstance(desc, dict) and 'en' in desc:
            raw_html = desc['en']
            
            # Remove all style attributes
            raw_html = re.sub(r'style\s*=\s*["\'][^"\']*["\']?', '', raw_html, flags=re.IGNORECASE | re.DOTALL)
            raw_html = re.sub(r'(color-scheme|forced-color-adjust|font-family|position-anchor)[^>]*', '', raw_html, flags=re.IGNORECASE)
            
            clean_text = strip_tags(raw_html)
            clean_text = re.sub(r'<\s*p[^a-zA-Z0-9>]*', '', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            clean_text = re.sub(r'unset[;:\s]+', '', clean_text)
            clean_text = re.sub(r'(color-scheme|forced-color-adjust|mask|math-depth|position|appearance)[:\s]+[^;]*;?', '', clean_text)
            
            sentences = re.split(r'(?<=[.!?])\s+', clean_text)
            paragraphs = []
            for i in range(0, len(sentences), 3):
                para_sentences = sentences[i:i+3]
                para_text = ' '.join(para_sentences).strip()
                if para_text:
                    paragraphs.append(f'<p>{para_text}</p>')
            
            prop['description']['en'] = '\n'.join(paragraphs) if paragraphs else '<p>No description available.</p>'
    
    # Get title and correct slug
    title_data = prop.get('title', {})
    title = title_data.get('en', 'property') if isinstance(title_data, dict) else (title_data or 'property')
    
    # Get slug from API or generate from title
    correct_slug = prop.get('slug') or slugify(title)
    
    print(f"   URL slug: {slug}")
    print(f"   Correct slug: {correct_slug}")
    
    # Only redirect if slugs are different
    if correct_slug != slug:
        print(f"   ⚠️ Slug mismatch - redirecting to correct URL")
        return redirect('property_detail', slug=correct_slug, pk=pk)
    
    # Get district name
    district_name = prop.get('district', {}).get('name', {}).get('en', '')

    # Generate meta title
    combined_title_length = len(title) + len(district_name) + 13
    id_suffix = f" #{pk}"

    if combined_title_length >= 55:
        meta_title = f"{title} - | {district_name}{id_suffix}"
    elif combined_title_length >= 30:
        meta_title = f"{title} - | {district_name} - KIF Realty{id_suffix}"
    else:
        meta_title = f"{title} - | {district_name} - KIF Realty - Dubai{id_suffix}"

    if len(meta_title) > 64:
        available_length = 64 - len(id_suffix)
        meta_title = meta_title[:available_length].rsplit(' ', 1)[0] + id_suffix
    
    # Ensure lists exist
    prop.setdefault("property_images", [])
    prop.setdefault("facilities", [])
    prop.setdefault("grouped_apartments", [])
    prop.setdefault("payment_plans", [])
    prop.setdefault("property_units", [])
    
    # Limit images
    if len(prop["property_images"]) > 20:
        prop["property_images"] = prop["property_images"][:20]

    print(f"   ✅ Rendering template with property data")
    
    # In property_detail view, add this after getting prop:
    print(f"   Property data keys: {prop.keys()}")
    print(f"   Property slug from API: {prop.get('slug')}")
    
    # ✅ CRITICAL: Ensure slug is in the property object for the template
    prop['slug'] = correct_slug  # This ensures grouped_apartments have access to property slug

    
    return render(request, "property_detail.html", {
        "property": prop,
        "meta_title": meta_title
    })


def unit_detail(request, property_slug, property_id, unit_id):
    """
    Display unit details
    URL format: /property/luxury-villa-2376/unit/123/
    """
    
    print(f"🔍 Unit Detail View:")
    print(f"   Property Slug: {property_slug}")
    print(f"   Property ID: {property_id}")
    print(f"   Unit ID: {unit_id}")
    
    # TRY MULTIPLE API ENDPOINT PATTERNS
    api_patterns = [
        f"{API_BASE}/units/{unit_id}",                              # Pattern 1: Direct unit access
        f"{API_BASE}/apartment/{unit_id}",                          # Pattern 2: Apartment endpoint
        f"{API_BASE}/property/{property_id}/unit/{unit_id}",        # Pattern 3: Nested (singular)
        f"{API_BASE}/grouped-apartments/{unit_id}",                 # Pattern 4: Grouped apartments
        f"{API_BASE}/property-units/{unit_id}",                     # Pattern 5: Property units
    ]
    
    unit = None
    unit_data = None
    
    # Try each API pattern until one works
    for pattern_index, unit_url in enumerate(api_patterns, 1):
        print(f"   🔄 Trying API Pattern #{pattern_index}: {unit_url}")
        
        try:
            unit_resp = requests.get(unit_url, timeout=8)
            print(f"      Response Status: {unit_resp.status_code}")
            
            if unit_resp.status_code == 200:
                unit_data = unit_resp.json()
                
                if unit_data.get("status"):
                    unit = unit_data.get("data", {})
                    print(f"   ✅ SUCCESS with Pattern #{pattern_index}!")
                    print(f"   Unit Type: {unit.get('unit_type', 'Unknown')}")
                    break
                else:
                    print(f"      ⚠️ Status is False: {unit_data.get('message', 'No message')}")
            else:
                print(f"      ❌ Failed with status {unit_resp.status_code}")
                
        except requests.RequestException as e:
            print(f"      ❌ Request error: {e}")
            continue
    
    # If no API pattern worked, try fetching from property data
    if not unit:
        print(f"   ⚠️ All API patterns failed. Trying to find unit in property data...")
        
        # Fetch property data to get units
        property_url = f"{API_BASE}/property/{property_id}"
        print(f"   Fetching property: {property_url}")
        
        try:
            property_resp = requests.get(property_url, timeout=8)
            if property_resp.status_code == 200:
                property_data = property_resp.json()
                if property_data.get("status"):
                    property = property_data.get("data", {})
                    
                    # Search in grouped_apartments
                    for apt in property.get("grouped_apartments", []):
                        if str(apt.get("id")) == str(unit_id):
                            unit = apt
                            print(f"   ✅ Found unit in grouped_apartments!")
                            break
                    
                    # If not found, search in property_units
                    if not unit:
                        for apt in property.get("property_units", []):
                            if str(apt.get("id")) == str(unit_id):
                                unit = apt
                                print(f"   ✅ Found unit in property_units!")
                                break
        except requests.RequestException as e:
            print(f"   ❌ Error fetching property: {e}")
    
    # If still no unit found, show error
    if not unit:
        print(f"   ❌ Unit not found in any source")
        return render(request, "unit_detail.html", {
            "unit_error": f"Unit #{unit_id} not found. Please contact us for availability."
        })
    
    print(f"   📦 Unit data keys: {unit.keys() if unit else 'None'}")
    
    # FETCH PROPERTY DATA for template
    property_url = f"{API_BASE}/property/{property_id}"
    print(f"   Fetching property details: {property_url}")
    
    property = None
    try:
        property_resp = requests.get(property_url, timeout=8)
        if property_resp.status_code == 200:
            property_data = property_resp.json()
            if property_data.get("status"):
                property = property_data.get("data", {})
                
                # Get slug from property or generate it
                if not property.get('slug'):
                    title = property.get('title', {})
                    title_en = title.get('en', 'property') if isinstance(title, dict) else str(title)
                    property['slug'] = slugify(title_en)
                
                print(f"   ✅ Property retrieved: {property.get('title', {}).get('en', 'Unknown')}")
                print(f"   📌 Property ID: {property.get('id')}")
                print(f"   📌 Property Slug: {property.get('slug')}")
                
                # Ensure required fields exist
                property.setdefault("facilities", [])
                property.setdefault("payment_plans", [])
                property.setdefault("title", {"en": "Property Details"})
                property.setdefault("district", {"name": {"en": "Dubai"}})
                property.setdefault("city", {"name": {"en": "Dubai"}})
                property.setdefault("developer", {"name": "Developer"})
                property.setdefault("delivery_date", None)
                property.setdefault("sales_status", {"name": {"en": "Available"}})
                property.setdefault("residential_units", 0)
                property.setdefault("completion_rate", 0)
                property.setdefault("cover", "")
                
    except requests.RequestException as e:
        print(f"   ⚠️ Error fetching property: {e}")
    
    # Create fallback property if fetch failed
    if not property:
        print(f"   ⚠️ Using fallback property data")
        
        # Use property_slug from URL or generate one
        fallback_slug = property_slug if (property_slug and property_slug != 'property') else slugify(f"property-{property_id}")

        
        property = {
            "id": property_id,
            "slug": fallback_slug,  # ✅ ALWAYS valid slug
            "title": {"en": "Property Details"},
            "district": {"name": {"en": "Dubai"}},
            "city": {"name": {"en": "Dubai"}},
            "developer": {"name": "Developer"},
            "facilities": [],
            "payment_plans": [],
            "delivery_date": None,
            "sales_status": {"name": {"en": "Available"}},
            "residential_units": 0,
            "completion_rate": 0,
            "cover": ""
        }
    
    print(f"   ✅ Rendering template with unit and property data")
    print(f"   🔗 Final Property Slug: {property.get('slug')}")
    print(f"   🔗 Final Property ID: {property.get('id')}")
    
    return render(request, "unit_detail.html", {
        "unit": unit,
        "property": property
    })


def extract_page_number(url):
    """Helper to extract page number from URL"""
    if not url:
        return None
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        page = parse_qs(parsed.query).get('page', [None])[0]
        return page
    except:
        return None


def model1(request):
    """Model 1 page"""
    return render(request, 'model1.html')

def about(request):
    """About us page"""
    return render(request, 'about.html')

def basenw(request):
       return render(request, 'basenew.html')

def blogs(request):
    """About us page"""
    return render(request, 'blogs.html')

def contact(request):
    """Contact us page"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        
        # Create contact message
        contact_message = ContactMessage.objects.create(
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message_text
        )
        
        messages.success(request, 'Thank you for your message! We will get back to you soon.')
        return redirect('contact')
    
    return render(request, 'contact.html')

@csrf_exempt
@require_http_methods(["POST"])
def subscribe_newsletter(request):
    """Subscribe to newsletter"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'}, json_dumps_params={'ensure_ascii': False})
        
        newsletter, created = Newsletter.objects.get_or_create(
            email=email,
            defaults={'is_active': True}
        )
        
        if created:
            return JsonResponse({'success': True, 'message': 'Successfully subscribed to newsletter!'}, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse({'success': False, 'error': 'Email already subscribed'}, json_dumps_params={'ensure_ascii': False})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'An error occurred'}, json_dumps_params={'ensure_ascii': False})

@require_http_methods(["GET"])
def search_properties_api(request):
    """API endpoint for property search"""
    query = request.GET.get('q', '')
    filters = {
        'search': query
    }
    
    result = PropertyService.search_properties(query, filters)
    
    if result['success']:
        return JsonResponse({
            'success': True,
            'properties': result['data'].get('results', []),
            'total': result['data'].get('count', 0)
        }, json_dumps_params={'ensure_ascii': False})
    else:
        return JsonResponse({
            'success': False,
            'error': result['error']
        }, json_dumps_params={'ensure_ascii': False})

@csrf_exempt
@require_http_methods(["POST"])
def filter_properties_api(request):
    """API endpoint for property filtering with JSON body"""
    try:
        # Parse JSON data
        data = json.loads(request.body)

        
        # Extract filters from JSON body - only include non-empty/non-zero values
        print(f"🔍 Received filters from frontend: {data}")
        filters = {}
        
        # Always include property_type if provided
        if data.get('property_type'):
            filters['property_type'] = data.get('property_type')
        
        # Only add string fields if they have values
        string_fields = ['city', 'district', 'unit_type', 'rooms', 'sales_status', 'title', 'developer', 'property_status']
        for field in string_fields:
            value = data.get(field)
            if value and str(value).strip():
                filters[field] = str(value).strip()
        
        # Only add numeric fields if they are greater than 0
        numeric_fields = ['delivery_year', 'low_price', 'max_price', 'min_area', 'max_area']
        for field in numeric_fields:
            value = data.get(field)
            if value and (isinstance(value, (int, float)) and value > 0):
                filters[field] = value
        
        print(f"🔍 Sending to external API: {filters}")
        
        # Get properties using the service
        properties_result = PropertyService.get_properties(filters)
        
        if properties_result['success'] and properties_result['data'].get('status') is True:
            data_block = properties_result['data']['data']
            
            # Map properties to frontend format
            mapped_properties = []
            for prop in data_block.get('results', []):
                title_data = prop.get('title', {})
                
                # Map property type ID to readable text
                property_type_id = prop.get('property_type')
                property_type_text = 'Residential'  # Default
                if property_type_id == '3' or property_type_id == 3:
                    property_type_text = 'Commercial'
                elif property_type_id == '20' or property_type_id == 20:
                    property_type_text = 'Residential'
                
                # Debug log to check property type mapping
                print(f"🏠 Backend property type mapping: ID={property_type_id} -> Text={property_type_text} (3=Commercial, 20=Residential)")
                
                mapped_properties.append({
                    'id': prop.get('id'),
                    'title': title_data.get('en', 'Luxury Property'),
                    'location': prop.get('location', 'Premium Location, Dubai'),
                    'bedrooms': prop.get('bedrooms', 'N/A'),
                    'area': prop.get('area', 'N/A'),
                    'price': prop.get('price'),
                    'low_price': prop.get('low_price'),
                    'min_area': prop.get('min_area'),
                    'property_type': property_type_text,
                    'cover': prop.get('cover'),  # Add cover field
                    'image': prop.get('image'),  # Keep image as backup
                    'city': prop.get('city'),    # Add city object
                    'district': prop.get('district'),  # Add district object
                    'detail_url': f"/property/{prop.get('id')}/"
                })
            
            # Debug pagination data
            pagination_data = {
                'count': data_block.get('count', 0),
                'current_page': data_block.get('current_page', 1),
                'last_page': data_block.get('last_page', 1),
                'next_page_url': data_block.get('next_page_url'),
                'previous_page_url': data_block.get('previous_page_url')  # Fixed: use previous_page_url instead of prev_page_url
            }
            print(f"📄 Backend pagination data: {pagination_data}")
            
            return JsonResponse({
                'status': True,
                'data': {
                    'results': mapped_properties,
                    **pagination_data
                }
            }, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse({
                'status': False,
                'error': properties_result.get('error', 'Unable to load properties.')
            }, json_dumps_params={'ensure_ascii': False})
            
    except json.JSONDecodeError:
        return JsonResponse({
            'status': False,
            'error': 'Invalid JSON data'
        }, status=400, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        print(f"Filter API error: {e}")
        return JsonResponse({
            'status': False,
            'error': 'An error occurred while filtering properties'
        }, status=500, json_dumps_params={'ensure_ascii': False})

def contact_view(request):
    """Display the contact page"""
    return render(request, 'contact.html')

@require_http_methods(["POST"])
def contact_submit(request):
    """Handle contact form submission"""
    try:
        # Get form data
        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        # Validate required fields
        if not all([first_name, last_name, email, phone]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('contact')
        
        # Get optional fields
        investment_budget = request.POST.get('investmentBudget', '')
        investment_type = request.POST.get('investmentType', '')
        preferred_location = request.POST.get('preferredLocation', '')
        timeline = request.POST.get('timeline', '')
        message = request.POST.get('message', '')
        
        # Handle property interests (multiple checkboxes)
        property_interests = request.POST.getlist('propertyInterest')
        
        # Create contact record
        contact = Contact.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            investment_budget=investment_budget,
            investment_type=investment_type,
            preferred_location=preferred_location,
            timeline=timeline,
            message=message,
            property_interests=', '.join(property_interests) if property_interests else ''
        )
        
        # Send notification email (optional)
        try:
            send_notification_email(contact)
        except Exception as e:
            # Log the error but don't fail the form submission
            print(f"Email notification failed: {e}")
        
        messages.success(request, 'Thank you for your inquiry! Our team will contact you within 24 hours.')
        return redirect('contact')
        
    except Exception as e:
        print(f"Contact form error: {e}")
        messages.error(request, 'An error occurred while submitting your inquiry. Please try again.')
        return redirect('contact')

@csrf_exempt
@require_http_methods(["POST"])
def contact_submit_ajax(request):
    """Handle AJAX contact form submission"""
    try:
        # Parse JSON data for AJAX requests
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Get form data
        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        # Validate required fields
        if not all([first_name, last_name, email, phone]):
            return JsonResponse({
                'success': False,
                'message': 'Please fill in all required fields.'
            }, status=400, json_dumps_params={'ensure_ascii': False})
        
        # Get optional fields
        investment_budget = data.get('investmentBudget', '')
        investment_type = data.get('investmentType', '')
        preferred_location = data.get('preferredLocation', '')
        timeline = data.get('timeline', '')
        message = data.get('message', '')
        
        # Handle property interests
        if isinstance(data.get('propertyInterest'), list):
            property_interests = data.get('propertyInterest', [])
        else:
            property_interests = data.getlist('propertyInterest') if hasattr(data, 'getlist') else []
        
        # Create contact record
        contact = Contact.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            investment_budget=investment_budget,
            investment_type=investment_type,
            preferred_location=preferred_location,
            timeline=timeline,
            message=message,
            property_interests=', '.join(property_interests) if property_interests else ''
        )
        
        # Send notification email (optional)
        try:
            send_notification_email(contact)
        except Exception as e:
            print(f"Email notification failed: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you for your inquiry! Our team will contact you within 24 hours.',
            'contact_id': contact.id
        }, json_dumps_params={'ensure_ascii': False})
        
    except Exception as e:
        print(f"AJAX Contact form error: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while submitting your inquiry. Please try again.'
        }, status=500, json_dumps_params={'ensure_ascii': False})

def send_notification_email(contact):
    """Send notification email to admin and confirmation to user"""
    
    # Admin notification email
    admin_subject = f"New Contact Inquiry from {contact.full_name}"
    admin_message = f"""
    New contact inquiry received:
    
    Name: {contact.full_name}
    Email: {contact.email}
    Phone: {contact.phone}
    
    Investment Details:
    Budget: {contact.get_investment_budget_display() if contact.investment_budget else 'Not specified'}
    Type: {contact.get_investment_type_display() if contact.investment_type else 'Not specified'}
    Location: {contact.get_preferred_location_display() if contact.preferred_location else 'Not specified'}
    Timeline: {contact.get_timeline_display() if contact.timeline else 'Not specified'}
    
    Property Interests: {contact.property_interests or 'None specified'}
    
    Message: {contact.message or 'No additional message'}
    
    Submitted: {contact.created_at.strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    # Send to admin
    if hasattr(settings, 'ADMIN_EMAIL'):
        send_mail(
            admin_subject,
            admin_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=True,
        )
    
    # User confirmation email
    user_subject = "Thank you for contacting KIF Realty"
    user_message = f"""
    Dear {contact.first_name},
    
    Thank you for your interest in Dubai real estate investment. We have received your inquiry and our RERA-certified experts will contact you within 24 hours.
    
    Your Inquiry Details:
    - Investment Budget: {contact.get_investment_budget_display() if contact.investment_budget else 'Not specified'}
    - Investment Type: {contact.get_investment_type_display() if contact.investment_type else 'Not specified'}
    - Preferred Location: {contact.get_preferred_location_display() if contact.preferred_location else 'Not specified'}
    - Timeline: {contact.get_timeline_display() if contact.timeline else 'Not specified'}
    
    In the meantime, feel free to reach out directly:
    📞 +971 569599966
    📧 info@kifrealty.com
    💬 WhatsApp: https://wa.me/971 569599966


    
    Best regards,
    KIF Realty Team
    """
    
    send_mail(
        user_subject,
        user_message,
        settings.DEFAULT_FROM_EMAIL,
        [contact.email],
        fail_silently=True,
    )

@require_POST
@csrf_exempt  # Remove this in production and handle CSRF properly
def submit_comment_ajax(request, slug):
    """Handle comment submission via AJAX"""
    try:
        post = get_object_or_404(BlogPost, slug=slug, status='published')
        
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you for your comment! It has been submitted and is awaiting approval.',
                'comment_count': post.comments.filter(is_approved=True).count()
            }, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse({
                'success': False,
                'message': 'Please correct the errors in your form.',
                'errors': form.errors
            }, json_dumps_params={'ensure_ascii': False})
    except Exception as e:
        print(f"Comment submission error: {e}")  # For debugging
        return JsonResponse({
            'success': False,
            'message': 'Sorry, there was an error submitting your comment. Please try again.'
        }, json_dumps_params={'ensure_ascii': False})

@csrf_exempt
@require_http_methods(["GET"])
def cities_api(request):
    """API endpoint to get cities with districts for React frontend"""
    try:
        # Get cities data from PropertyService
        result = PropertyService.get_cities()
        
        if result['success']:
            return JsonResponse({
                'status': True,
                'data': result['data']
            }, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse({'status': False, 'error': result['error']}, status=400, json_dumps_params={'ensure_ascii': False})
            
    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)}, status=500, json_dumps_params={'ensure_ascii': False})

@csrf_exempt  
@require_http_methods(["GET"])
def developers_api(request):
    """API endpoint to get developers list for React frontend"""
    try:
        # Get developers data from PropertyService
        result = PropertyService.get_developers()
        
        if result['success']:
            return JsonResponse({
                'status': True,
                'data': result['data']
            }, json_dumps_params={'ensure_ascii': False})
        else:
            return JsonResponse({'status': False, 'error': result['error']}, status=400, json_dumps_params={'ensure_ascii': False})
            
    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)}, status=500, json_dumps_params={'ensure_ascii': False})




# landingpages
def retail(request):
    return render(request,'landingpages/retail.html')

def second(request):
    return render(request,'landingpages/second.html')

def commercial(request):
    return render(request,'landingpages/commercial.html')

def luxury(request):
    return render(request,'landingpages/luxury.html')

def beach(request):
    return render(request,'landingpages/beach.html')

def offplan(request):
    return render(request,'landingpages/offplan.html')

def labour(request):
    return render(request,'landingpages/labour.html')

def warehouse(request):
    return render(request,'landingpages/warehouse.html')

def plots(request):
    return render(request,'landingpages/plots.html')

def mansions(request):
    return render(request,'landingpages/mansions.html')


def privacy(request):
    return render(request,'privacy_policy.html')

def terms(request):
    return render(request,'terms.html')

def rera(request):
    return render(request,'rera.html')



def robots_txt(request):
    content = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Allow: /\n"
        "Sitemap: https://kifrealty.com/sitemap.xml\n"
    )
    return HttpResponse(content, content_type="text/plain")


# main/views.py


def custom_404(request, exception):
    """Custom 404 error handler"""
    return render(request, '404.html', status=404)

def preview_404(request):
    """Preview the 404 page during development"""
    return render(request, '404.html', status=404)
