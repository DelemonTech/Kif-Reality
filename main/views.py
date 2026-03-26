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
from django.core.cache import cache
from django.utils.html import strip_tags
import re
import os
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────
# ✅ FIX: Helper to normalize image URLs from API
# The remote API returns relative paths like "property_01524_bd7fsZ1.jpg"
# but your local server has no copy of those files.
# This converts them to absolute URLs pointing to the remote media server.
# ─────────────────────────────────────────────
MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "http://54.237.196.120")
REMOTE_MEDIA_HOST = "54.237.196.120"

def _fix_image_url(path):
    """Normalize API image paths, replacing remote IP with correct base URL."""
    if not path:
        return None
    # Replace hardcoded IP with env variable (works for both local and production)
    if REMOTE_MEDIA_HOST in path:
        return path.replace(f"http://{REMOTE_MEDIA_HOST}", MEDIA_BASE_URL)
    # If it's already an absolute URL pointing elsewhere, leave it
    if path.startswith('http'):
        return path
    # Relative path — prepend base URL
    return f"{MEDIA_BASE_URL}{path}"
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
                    print(f"Error saving comment: {e}")
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
        print(f"Newsletter subscription error: {e}")
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


def index(request):
    """Homepage - properties loaded dynamically via JavaScript"""
    context = {
        'MICROSERVICE_API': settings.MICROSERVICE_API,
    }
    return render(request, 'index.html', context)


def exclusive(request):
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
    """Ultra-fast properties page - all data loaded by JavaScript"""
    return render(request, 'properties.html', {
        'properties': [],
        'total_count': 0,
        'properties_error': None,
        'MICROSERVICE_API': settings.MICROSERVICE_API,
    })


def property_redirect(request, property_id):
    """
    Redirect old /property/ID/ URLs to new /property/slug-ID/ format
    """
    url = f"{API_BASE}/{property_id}"
    
    try:
        resp = requests.get(url, timeout=8)
        
        if resp.status_code == 200:
            data = resp.json()
            
            if data.get("status"):
                prop = data.get("data") or {}
                
                title_data = prop.get('title', {})
                title = title_data.get('en', 'property') if isinstance(title_data, dict) else (title_data or 'property')
                slug = prop.get('slug') or slugify(title)
                
                return redirect('property_detail', slug=slug, pk=property_id, permanent=True)
    
    except requests.RequestException:
        pass
    
    return redirect('property_detail', slug='property', pk=property_id, permanent=True)


def property_detail(request, slug, pk):
    """
    Display property details using slug in URL but pk (ID) for API call.
    URL format: /property/luxury-villa-palm-jumeirah-2376/
    API call: uses the pk (2376)

    Caches the raw API response per property ID for 15 minutes.
    """

    print(f"🔍 Property Detail View Called:")
    print(f"   Slug from URL: {slug}")
    print(f"   PK from URL: {pk}")

    cache_key = f"property_api_{pk}"
    prop = cache.get(cache_key)

    if prop is None:
        url = f"{API_BASE}/property/{pk}"
        print(f"   API URL: {url} (cache miss)")

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
        cache.set(cache_key, prop, 60 * 15)
        print(f"   ✅ Property data cached: {prop.get('title', {}).get('en', 'No title')}")
    else:
        print(f"   ✅ Property data served from cache: {prop.get('title', {}).get('en', 'No title')}")

    # ✅ FIX: Normalize cover image URL to absolute remote URL
    prop['cover'] = _fix_image_url(prop.get('cover'))

    # ✅ FIX: Normalize all property_images URLs
    if prop.get('property_images'):
        for img in prop['property_images']:
            if isinstance(img, dict):
                if img.get('image'):
                    img['image'] = _fix_image_url(img['image'])
                if img.get('url'):
                    img['url'] = _fix_image_url(img['url'])

    # Clean the description
    if prop.get('description'):
        desc = prop['description']
        if isinstance(desc, dict) and 'en' in desc:
            raw_html = desc['en']
            
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

    # Ensure slug is in property object for the template
    prop['slug'] = correct_slug

    print(f"   ✅ Rendering template with property data")
    print(f"   Property data keys: {prop.keys()}")
    print(f"   Property slug: {prop.get('slug')}")

    return render(request, "property_detail.html", {
        "property": prop,
        "meta_title": meta_title
    })


def unit_detail(request, property_slug, property_id, unit_id):
    """
    Display unit details.
    URL format: /property/luxury-villa-2376/unit/123/
    """

    print(f"🔍 Unit Detail View:")
    print(f"   Property Slug: {property_slug}")
    print(f"   Property ID: {property_id}")
    print(f"   Unit ID: {unit_id}")

    api_patterns = [
        f"{API_BASE}/units/{unit_id}",
        f"{API_BASE}/apartment/{unit_id}",
        f"{API_BASE}/property/{property_id}/unit/{unit_id}",
        f"{API_BASE}/grouped-apartments/{unit_id}",
        f"{API_BASE}/property-units/{unit_id}",
    ]

    unit = None
    unit_data = None

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

    # Fallback: search within property data
    if not unit:
        print(f"   ⚠️ All API patterns failed. Searching within property data...")

        property_url = f"{API_BASE}/property/{property_id}"
        print(f"   Fetching property: {property_url}")

        try:
            property_resp = requests.get(property_url, timeout=8)
            if property_resp.status_code == 200:
                property_data = property_resp.json()
                if property_data.get("status"):
                    property_obj = property_data.get("data", {})

                    for apt in property_obj.get("grouped_apartments", []):
                        if str(apt.get("id")) == str(unit_id):
                            unit = apt
                            print(f"   ✅ Found unit in grouped_apartments!")
                            break

                    if not unit:
                        for apt in property_obj.get("property_units", []):
                            if str(apt.get("id")) == str(unit_id):
                                unit = apt
                                print(f"   ✅ Found unit in property_units!")
                                break
        except requests.RequestException as e:
            print(f"   ❌ Error fetching property: {e}")

    if not unit:
        print(f"   ❌ Unit not found in any source")
        return render(request, "unit_detail.html", {
            "unit_error": f"Unit #{unit_id} not found. Please contact us for availability."
        })

    print(f"   📦 Unit data keys: {unit.keys() if unit else 'None'}")

    # Fetch property data for the template
    property_url = f"{API_BASE}/property/{property_id}"
    print(f"   Fetching property details: {property_url}")

    property_obj = None
    try:
        property_resp = requests.get(property_url, timeout=8)
        if property_resp.status_code == 200:
            property_data = property_resp.json()
            if property_data.get("status"):
                property_obj = property_data.get("data", {})

                if not property_obj.get('slug'):
                    title = property_obj.get('title', {})
                    title_en = title.get('en', 'property') if isinstance(title, dict) else str(title)
                    property_obj['slug'] = slugify(title_en)

                print(f"   ✅ Property retrieved: {property_obj.get('title', {}).get('en', 'Unknown')}")

                # ✅ FIX: Normalize cover image URL
                property_obj['cover'] = _fix_image_url(property_obj.get('cover'))

                property_obj.setdefault("facilities", [])
                property_obj.setdefault("payment_plans", [])
                property_obj.setdefault("title", {"en": "Property Details"})
                property_obj.setdefault("district", {"name": {"en": "Dubai"}})
                property_obj.setdefault("city", {"name": {"en": "Dubai"}})
                property_obj.setdefault("developer", {"name": "Developer"})
                property_obj.setdefault("delivery_date", None)
                property_obj.setdefault("sales_status", {"name": {"en": "Available"}})
                property_obj.setdefault("residential_units", 0)
                property_obj.setdefault("completion_rate", 0)
                property_obj.setdefault("cover", "")

    except requests.RequestException as e:
        print(f"   ⚠️ Error fetching property: {e}")

    if not property_obj:
        print(f"   ⚠️ Using fallback property data")
        fallback_slug = property_slug if (property_slug and property_slug != 'property') else slugify(f"property-{property_id}")

        property_obj = {
            "id": property_id,
            "slug": fallback_slug,
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

    return render(request, "unit_detail.html", {
        "unit": unit,
        "property": property_obj
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
    return render(request, 'model1.html')


def about(request):
    return render(request, 'about.html')


def basenw(request):
    return render(request, 'basenew.html')


def blogs(request):
    return render(request, 'blogs.html')


def contact(request):
    """Contact us page"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')

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
    filters = {'search': query}

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
        data = json.loads(request.body)

        print(f"🔍 Received filters from frontend: {data}")
        filters = {}

        if data.get('property_type'):
            filters['property_type'] = data.get('property_type')

        string_fields = ['city', 'district', 'unit_type', 'rooms', 'sales_status', 'title', 'developer', 'property_status']
        for field in string_fields:
            value = data.get(field)
            if value and str(value).strip():
                filters[field] = str(value).strip()

        numeric_fields = ['delivery_year', 'low_price', 'max_price', 'min_area', 'max_area']
        for field in numeric_fields:
            value = data.get(field)
            if value and (isinstance(value, (int, float)) and value > 0):
                filters[field] = value

        print(f"🔍 Sending to external API: {filters}")

        properties_result = PropertyService.get_properties(filters)

        if properties_result['success'] and properties_result['data'].get('status') is True:
            data_block = properties_result['data']['data']

            mapped_properties = []
            for prop in data_block.get('results', []):
                title_data = prop.get('title', {})

                property_type_id = prop.get('property_type')
                property_type_text = 'Residential'
                if property_type_id == '3' or property_type_id == 3:
                    property_type_text = 'Commercial'
                elif property_type_id == '20' or property_type_id == 20:
                    property_type_text = 'Residential'

                print(f"🏠 Backend property type mapping: ID={property_type_id} -> Text={property_type_text}")

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
                    # ✅ FIX: Normalize cover and image URLs
                    'cover': _fix_image_url(prop.get('cover')),
                    'image': _fix_image_url(prop.get('image')),
                    'city': prop.get('city'),
                    'district': prop.get('district'),
                    'detail_url': f"/property/{prop.get('id')}/"
                })

            pagination_data = {
                'count': data_block.get('count', 0),
                'current_page': data_block.get('current_page', 1),
                'last_page': data_block.get('last_page', 1),
                'next_page_url': data_block.get('next_page_url'),
                'previous_page_url': data_block.get('previous_page_url')
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
    return render(request, 'contact.html')


@require_http_methods(["POST"])
def contact_submit(request):
    """Handle contact form submission"""
    try:
        first_name = request.POST.get('firstName', '').strip()
        last_name = request.POST.get('lastName', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not all([first_name, last_name, email, phone]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('contact')

        investment_budget = request.POST.get('investmentBudget', '')
        investment_type = request.POST.get('investmentType', '')
        preferred_location = request.POST.get('preferredLocation', '')
        timeline = request.POST.get('timeline', '')
        message = request.POST.get('message', '')
        property_interests = request.POST.getlist('propertyInterest')

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

        try:
            send_notification_email(contact)
        except Exception as e:
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
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()

        if not all([first_name, last_name, email, phone]):
            return JsonResponse({
                'success': False,
                'message': 'Please fill in all required fields.'
            }, status=400, json_dumps_params={'ensure_ascii': False})

        investment_budget = data.get('investmentBudget', '')
        investment_type = data.get('investmentType', '')
        preferred_location = data.get('preferredLocation', '')
        timeline = data.get('timeline', '')
        message = data.get('message', '')

        if isinstance(data.get('propertyInterest'), list):
            property_interests = data.get('propertyInterest', [])
        else:
            property_interests = data.getlist('propertyInterest') if hasattr(data, 'getlist') else []

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

    if hasattr(settings, 'ADMIN_EMAIL'):
        send_mail(
            admin_subject,
            admin_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            fail_silently=True,
        )

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
    💬 WhatsApp: https://wa.me/971569599966
    
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
@csrf_exempt
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
        print(f"Comment submission error: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Sorry, there was an error submitting your comment. Please try again.'
        }, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@require_http_methods(["GET"])
def cities_api(request):
    """API endpoint to get cities with districts for React frontend"""
    try:
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


# Landing pages
def retail(request):
    return render(request, 'landingpages/retail.html')

def second(request):
    return render(request, 'landingpages/second.html')

def commercial(request):
    return render(request, 'landingpages/commercial.html')

def luxury(request):
    return render(request, 'landingpages/luxury.html')

def beach(request):
    return render(request, 'landingpages/beach.html')

def offplan(request):
    return render(request, 'landingpages/offplan.html')

def labour(request):
    return render(request, 'landingpages/labour.html')

def warehouse(request):
    return render(request, 'landingpages/warehouse.html')

def plots(request):
    return render(request, 'landingpages/plots.html')

def mansions(request):
    return render(request, 'landingpages/mansions.html')


def privacy(request):
    return render(request, 'privacy_policy.html')

def terms(request):
    return render(request, 'terms.html')

def rera(request):
    return render(request, 'rera.html')


def robots_txt(request):
    content = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Allow: /\n"
        "Sitemap: https://kifrealty.com/sitemap.xml\n"
    )
    return HttpResponse(content, content_type="text/plain")


def custom_404(request, exception):
    """Custom 404 error handler"""
    return render(request, '404.html', status=404)

def preview_404(request):
    """Preview the 404 page during development"""
    return render(request, '404.html', status=404)