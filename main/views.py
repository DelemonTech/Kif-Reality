# ✅ Use utf8_json_response as JsonResponse throughout — auto-sets ensure_ascii=False
# Do NOT re-import django.http.JsonResponse anywhere below (it would override this)
from .utils import utf8_json_response as JsonResponse

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings
from django.core.mail import send_mail
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.utils import timezone
from django.utils.text import slugify
from django.utils.html import strip_tags
from urllib.parse import urlparse, parse_qs

from .models import Contact, ContactMessage, BlogPost, Category, Tag, Newsletter, Comment
from .forms import NewsletterForm, CommentForm
from .services import PropertyService
from .xopp_service import (
    XOPPService, get_catalog, filter_catalog, to_card, classify_property_type,
    get_available_counts, get_developers as xopp_get_developers,
)

import json
import requests
import logging

logger = logging.getLogger(__name__)

# ── x-opperp CRM webhook ──────────────────────────────────────────────────────
XOPPERP_WEBHOOK_URL = "https://x-opperp.com/api/v1/integrations/webhooks/website-lead/"
XOPPERP_API_TOKEN   = "47399e08-7406-4426-836f-bfc81bc09ae8"

def send_lead_to_xopperp(first_name, last_name, email, phone, message=""):
    """Send lead to x-opperp CRM. Never raises — won't break form flow."""
    payload = {
        "api_token": XOPPERP_API_TOKEN,
        "first_name": first_name or "",
        "last_name":  last_name  or "",
        "email":      email      or "",
        "phone":      phone      or "",
        "message":    message    or "",
    }
    try:
        resp = requests.post(XOPPERP_WEBHOOK_URL, json=payload, timeout=5)
        resp.raise_for_status()
        logger.info("x-opperp lead sent (status %s)", resp.status_code)
    except Exception as exc:
        logger.error("x-opperp webhook error: %s", exc)
# ─────────────────────────────────────────────────────────────────────────────
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
    result = XOPPService.get_property(property_id)
    if result['success']:
        slug = slugify(result['data'].get('title') or 'property') or 'property'
        return redirect('property_detail', slug=slug, pk=property_id, permanent=True)

    return redirect('property_detail', slug='property', pk=property_id, permanent=True)


def _clean_description_html(raw_html):
    """Strip editor markup/inline styles from an API description, re-paragraphed."""
    if not raw_html:
        return ''
    raw_html = re.sub(r'style\s*=\s*["\'][^"\']*["\']?', '', raw_html, flags=re.IGNORECASE | re.DOTALL)
    clean_text = strip_tags(raw_html)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    sentences = re.split(r'(?<=[.!?])\s+', clean_text)
    paragraphs = []
    for i in range(0, len(sentences), 3):
        para_text = ' '.join(sentences[i:i + 3]).strip()
        if para_text:
            paragraphs.append(f'<p>{para_text}</p>')
    return '\n'.join(paragraphs)


def _map_unit_for_template(u):
    """Map an X-OPP unit object to the shape unit_detail/property_detail expect."""
    label = u.get('bedroom_label') or ''
    if not label and u.get('bedrooms') is not None:
        label = 'Studio' if u['bedrooms'] == 0 else str(u['bedrooms'])
    rooms_text = 'Studio' if label.lower() == 'studio' else (f"{label} Bedroom" if label else '')
    unit_type = f"Unit {u['unit_no']}" if u.get('unit_no') else (rooms_text or 'Unit')
    return {
        'id': u.get('id'),
        'unit_type': {'en': unit_type},
        'rooms': {'en': rooms_text or label},
        'min_price': u.get('price'),
        'min_area': u.get('area'),
        'floor_no': u.get('floor_no'),
        'bathrooms': u.get('bathrooms'),
        'view': u.get('view'),
        'status': u.get('status'),
        'unit_image': u.get('unit_image'),
        'floor_plan_image': u.get('floor_plan_image'),
        'description': '',
    }


def _fmt_price_short(v):
    """866000 -> '866K', 2298000 -> '2.3M'."""
    if not v:
        return None
    if v >= 1_000_000:
        s = f"{v / 1_000_000:.1f}".rstrip('0').rstrip('.')
        return f"{s}M"
    if v >= 1_000:
        return f"{round(v / 1_000)}K"
    return f"{v:,.0f}"


def _group_units(units, main_type='Apartment', property_title=''):
    """Group raw X-OPP units by bedroom label into summary cards with ranges."""
    groups = {}
    for u in units:
        label = (u.get('bedroom_label') or '').strip()
        if not label and u.get('bedrooms') is not None:
            label = 'Studio' if u['bedrooms'] == 0 else str(u['bedrooms'])
        if not label:
            label = 'Other'

        g = groups.setdefault(label, {'raw_units': [], 'prices': [], 'areas': []})
        g['raw_units'].append(u)
        if u.get('price'):
            g['prices'].append(u['price'])
        if u.get('area'):
            g['areas'].append(u['area'])

    def sort_key(label):
        low = label.lower()
        if low == 'studio':
            return 0.0
        try:
            return float(label)
        except ValueError:
            return 999.0

    result = []
    for label in sorted(groups, key=sort_key):
        g = groups[label]
        prices, areas = g['prices'], g['areas']

        if prices:
            lo, hi = _fmt_price_short(min(prices)), _fmt_price_short(max(prices))
            price_range = f"AED {lo}" if lo == hi else f"AED {lo} – {hi}"
        else:
            price_range = 'Price on request'

        if areas:
            lo, hi = min(areas), max(areas)
            area_range = f"{lo:,.0f}" if lo == hi else f"{lo:,.0f} – {hi:,.0f}"
        else:
            area_range = None

        display_label = label if sort_key(label) in (0.0, 999.0) else f"{label} Bedroom"
        group_title = f"{display_label} {main_type}".strip()
        bed_label = 'Studio' if display_label == 'Studio' else f"{label} Bed"

        mapped_units = []
        for u in sorted(g['raw_units'], key=lambda x: (x.get('price') is None, x.get('price') or 0)):
            m = _map_unit_for_template(u)
            m['unit_no'] = u.get('unit_no') or ''
            m['price_display'] = f"{u['price']:,.0f} AED" if u.get('price') else 'On request'
            m['price_short'] = f"AED {_fmt_price_short(u['price'])}" if u.get('price') else 'On request'
            m['area_display'] = f"{u['area']:,.0f} sq.ft" if u.get('area') else '—'
            m['bed_label'] = bed_label
            status = (u.get('status') or '').lower()
            m['status'] = status
            m['status_display'] = status.title() if status in ('available', 'reserved', 'sold') else ''
            unit_ref = u.get('unit_no') or u.get('id')
            m['wa_text'] = (
                f"Hi, I'm interested in {property_title} - {group_title}, "
                f"Unit {unit_ref} ({m['price_display']}). Please share more details."
            )
            mapped_units.append(m)

        result.append({
            'label': display_label,
            'title': group_title,
            'count': len(mapped_units),
            'price_range': price_range,
            'area_range': area_range,
            'units': mapped_units,
        })
    return result


def _map_property_for_template(prop, units=None):
    """Map an X-OPP property detail object to the nested shape the templates use."""
    title = prop.get('title') or 'Property'
    return {
        'id': prop.get('id'),
        'slug': slugify(title) or 'property',
        'title': {'en': title},
        'description': {'en': _clean_description_html(prop.get('description'))},
        'cover': prop.get('cover') or '',
        'property_images': [{'image': url} for url in (prop.get('images') or [])[:20]],
        'city': {'name': {'en': prop.get('city') or ''}},
        'district': {'name': {'en': prop.get('district') or ''}},
        'developer': {'name': prop.get('developer_name') or '', 'description': ''},
        'property_type': {'name': {'en': prop.get('property_type') or ''}},
        'low_price': prop.get('price_from'),
        'min_area': prop.get('area_from'),
        'max_area': prop.get('area_to'),
        'latitude': prop.get('latitude'),
        'longitude': prop.get('longitude'),
        'completion_rate': prop.get('completion_rate') or 0,
        'delivery_date': prop.get('delivery_date') or '',
        'residential_units': prop.get('residential_units') or 0,
        'sales_status': {'name': {'en': prop.get('sales_status_name') or 'Available'}},
        'facilities': [{'name': {'en': a}} for a in (prop.get('amenities') or [])],
        'payment_plans': [
            {'name': {'en': pl.get('name') or 'Payment Plan'}, **pl}
            for pl in (prop.get('payment_plans') or [])
        ],
        'grouped_apartments': [_map_unit_for_template(u) for u in (units or [])],
        'unit_groups': _group_units(
            units or [],
            main_type=(prop.get('property_type') or 'Apartment').split(',')[0].strip() or 'Apartment',
            property_title=title,
        ),
        'property_units': [],
    }


def property_detail(request, slug, pk):
    """
    Display property details using slug in URL but pk (ID) for the X-OPP API call.
    URL format: /property/luxury-villa-palm-jumeirah-2376/
    """
    result = XOPPService.get_property(pk)
    if not result['success']:
        return render(request, "property_detail.html", {
            "property_error": result['error'] or "Property not found or API error."
        })

    raw = result['data']
    units = XOPPService.get_all_units(pk) if raw.get('units_count') else []
    prop = _map_property_for_template(raw, units)

    title = prop['title']['en']
    correct_slug = prop['slug']

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

    units = XOPPService.get_all_units(property_id)
    unit = next((u for u in units if str(u.get('id')) == str(unit_id)), None)

    if not unit:
        return render(request, "unit_detail.html", {
            "unit_error": f"Unit #{unit_id} not found. Please contact us for availability."
        })

    result = XOPPService.get_property(property_id)
    if result['success']:
        property_obj = _map_property_for_template(result['data'])
    else:
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

    return render(request, "unit_detail.html", {
        "unit": _map_unit_for_template(unit),
        "property": property_obj
    })


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

        # Send lead to x-opperp CRM
        parts = (name or "").strip().split(" ", 1)
        send_lead_to_xopperp(parts[0], parts[1] if len(parts) > 1 else "", email, phone, message_text)

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
    """API endpoint for property search (X-OPP catalog, title match)"""
    query = request.GET.get('q', '')
    catalog = get_catalog()

    if not catalog:
        return JsonResponse({
            'success': False,
            'error': 'Unable to fetch properties. Please try again later.'
        }, json_dumps_params={'ensure_ascii': False})

    matched = filter_catalog(catalog, {'title': query}) if query else catalog
    return JsonResponse({
        'success': True,
        'properties': [to_card(p) for p in matched[:50]],
        'total': len(matched)
    }, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@require_http_methods(["POST"])
def filter_properties_api(request):
    """Property filtering over the X-OPP catalog (server-side, cached)."""
    try:
        data = json.loads(request.body)

        filters = {}
        string_fields = ['property_type', 'city', 'district', 'unit_type', 'rooms',
                         'sales_status', 'title', 'developer', 'property_status']
        for field in string_fields:
            value = data.get(field)
            if value and str(value).strip():
                filters[field] = str(value).strip()

        numeric_fields = ['delivery_year', 'low_price', 'min_price', 'max_price', 'min_area', 'max_area']
        for field in numeric_fields:
            value = data.get(field)
            if value and (isinstance(value, (int, float)) and value > 0):
                filters[field] = value

        catalog = get_catalog()
        if not catalog:
            return JsonResponse({
                'status': False,
                'error': 'Unable to load properties.'
            }, json_dumps_params={'ensure_ascii': False})

        matched = filter_catalog(catalog, filters)

        # page comes as a query param (?page=N) or in the body; page size from limit
        try:
            page = max(1, int(request.GET.get('page') or data.get('page') or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            per_page = int(data.get('limit') or data.get('page_size') or 12)
        except (TypeError, ValueError):
            per_page = 12
        per_page = max(1, min(per_page, 100))

        count = len(matched)
        last_page = max(1, -(-count // per_page))
        page = min(page, last_page)
        start = (page - 1) * per_page
        page_items = matched[start:start + per_page]

        cards = [to_card(p) for p in page_items]
        avail_counts = get_available_counts([c['id'] for c in cards])
        for c in cards:
            c['available_units'] = avail_counts.get(c['id'])

        base_url = '/api/properties/filter/'
        return JsonResponse({
            'status': True,
            'data': {
                'results': cards,
                'count': count,
                'current_page': page,
                'last_page': last_page,
                'next_page_url': f'{base_url}?page={page + 1}' if page < last_page else None,
                'previous_page_url': f'{base_url}?page={page - 1}' if page > 1 else None,
            }
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

        # Send lead to x-opperp CRM
        try:
            send_lead_to_xopperp(first_name, last_name, email, phone, message)
        except Exception as e:
            print(f"CRM webhook failed: {e}")

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

        # Send lead to x-opperp CRM
        try:
            send_lead_to_xopperp(first_name, last_name, email, phone, message)
        except Exception as e:
            print(f"CRM webhook failed: {e}")

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

    📞 +971 567655599
    📧 info@kifrealty.com
    💬 WhatsApp: https://wa.me/971567655599

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


# ─────────────────────────────────────────────
# ✅ FIXED: cities_api — fallback to hardcoded UAE cities when microservice is down
# ─────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["GET"])
def cities_api(request):
    """Cities with districts, derived from the X-OPP catalog.

    Response is double-wrapped ({data: {status, data}}) because the frontend
    checks result.data.status / result.data.data.
    """
    try:
        catalog = get_catalog()

        cities = {}
        for p in catalog:
            city = p['city'].strip()
            if not city:
                continue
            districts = cities.setdefault(city, set())
            if p['district'].strip():
                districts.add(p['district'].strip())

        if not cities:
            cities = {c: set() for c in [
                'Dubai', 'Abu Dhabi', 'Sharjah', 'Ajman',
                'Ras Al Khaimah', 'Fujairah', 'Umm Al Quwain',
            ]}

        cities_list = [
            {
                'id': i,
                'name': {'en': city},
                'districts': [{'name': {'en': d}} for d in sorted(districts)],
            }
            for i, (city, districts) in enumerate(sorted(cities.items()), start=1)
        ]

        payload = {'status': True, 'data': cities_list}
        return JsonResponse({
            'status': True,
            'data': payload
        }, json_dumps_params={'ensure_ascii': False})

    except Exception as e:
        print(f"Cities API error: {e}")
        return JsonResponse({'status': False, 'error': str(e)}, status=500, json_dumps_params={'ensure_ascii': False})


# ─────────────────────────────────────────────
# ✅ FIXED: developers_api — unwraps nested response { data: { data: [...] } }
#    and falls back gracefully when microservice is down
# ─────────────────────────────────────────────
def _xopp_developers_response():
    """Developers from the partner /developers/ endpoint, enriched with the
    number of catalog projects per developer. None if the endpoint is down."""
    devs = xopp_get_developers()
    if not devs:
        return None

    from collections import Counter
    counts = Counter(
        p['developer_name'].strip() for p in get_catalog() if p['developer_name'].strip()
    )

    data = [{
        'id': d.get('id'),
        'name': d.get('name') or '',
        'slug': d.get('slug') or '',
        'logo': d.get('logo') or '',
        'website': d.get('website') or '',
        'email': d.get('email') or '',
        'phone': d.get('phone') or '',
        'location': d.get('address') or 'Dubai, UAE',
        'overview': d.get('overview') or '',
        'projects_count': counts.get((d.get('name') or '').strip(), 0),
    } for d in devs if d.get('name')]

    return JsonResponse({'status': True, 'data': data}, json_dumps_params={'ensure_ascii': False})


@csrf_exempt
@require_http_methods(["GET"])
def developers_api(request):
    """Developers list from the X-OPP partner API (catalog-derived fallback)."""
    try:
        resp = _xopp_developers_response()
        if resp:
            return resp

        names = sorted({p['developer_name'].strip() for p in get_catalog() if p['developer_name'].strip()})
        if names:
            return JsonResponse({
                'status': True,
                'data': [{'name': n} for n in names]
            }, json_dumps_params={'ensure_ascii': False})

        return developers_from_properties(request)

    except Exception as e:
        print(f"Developers API error: {e}")
        return developers_from_properties(request)  # always fall back, never 500


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

def office_space(request):
    return render(request, 'landingpages/office-space.html')


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

def developers(request):
    # Templates build '<MICROSERVICE_API>/developers/' — point them at our own API
    if request.GET.get('name'):
        return render(request, 'developer_detail.html', {
            'MICROSERVICE_API': '/api',
        })
    return render(request, 'developers.html', {
        'MICROSERVICE_API': '/api',
    })


@require_http_methods(["GET"])
def developers_from_properties(request):
    """Get developers - tries the X-OPP partner API first, then DB, then fallbacks"""
    resp = _xopp_developers_response()
    if resp:
        return resp

    from .models import Property

    # Try DB first
    qs = (Property.objects
          .exclude(developer='')
          .exclude(developer__isnull=True)
          .values_list('developer', flat=True)
          .distinct()
          .order_by('developer'))

    if qs.exists():
        data = [{'name': d} for d in qs]
        return JsonResponse({'status': True, 'data': data}, json_dumps_params={'ensure_ascii': False})

    # Fallback: try the microservice developers API
    result = PropertyService.get_developers()
    if result['success'] and result['data']:
        raw = result['data']
        if isinstance(raw, dict):
            inner = raw.get('data')
            if isinstance(inner, list):
                developers_list = inner
            elif isinstance(inner, dict):
                developers_list = inner.get('data', [])
            else:
                developers_list = []
        elif isinstance(raw, list):
            developers_list = raw
        else:
            developers_list = []

        if developers_list:
            return JsonResponse({'status': True, 'data': developers_list}, json_dumps_params={'ensure_ascii': False})

    # Hardcoded fallback — top UAE developers
    fallback = [
        {'name': 'Emaar Properties'},
        {'name': 'DAMAC Properties'},
        {'name': 'Nakheel'},
        {'name': 'Meraas'},
        {'name': 'Dubai Properties'},
        {'name': 'Sobha Realty'},
        {'name': 'Aldar Properties'},
        {'name': 'Azizi Developments'},
        {'name': 'Binghatti Developers'},
        {'name': 'Omniyat'},
        {'name': 'Select Group'},
        {'name': 'Ellington Properties'},
        {'name': 'Tiger Properties'},
        {'name': 'Danube Properties'},
        {'name': 'Object 1'},
    ]
    return JsonResponse({'status': True, 'data': fallback}, json_dumps_params={'ensure_ascii': False})