from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import *

@admin.register(ExclusiveProperty)
class ExclusivePropertyAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'property_type', 'district', 'formatted_price_display', 
        'bedroom_display', 'status', 'priority', 'is_featured', 'view_count',
        'inquiry_count', 'created_at'
    ]
    list_filter = [
        'property_type', 'status', 'priority', 'is_featured', 'is_exclusive',
        'city', 'district', 'bedrooms', 'created_at'
    ]
    search_fields = ['title', 'district', 'neighborhood', 'description']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['id', 'view_count', 'inquiry_count', 'price_per_sqft', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'property_type', 'short_description')
        }),
        ('Location', {
            'fields': ('city', 'district', 'neighborhood', 'address', 'latitude', 'longitude')
        }),
        ('Specifications', {
            'fields': ('bedrooms', 'bathrooms', 'area_sqft', 'plot_size')
        }),
        ('Pricing', {
            'fields': ('price', 'price_per_sqft', 'service_charge')
        }),
        ('Content', {
            'fields': ('description', 'key_features', 'nearby_amenities')
        }),
        ('Media', {
            'fields': ('cover_image', 'video_url', 'virtual_tour_url', 'floor_plan')
        }),
        ('Status & Management', {
            'fields': ('status', 'priority', 'is_featured', 'is_exclusive', 'assigned_agent')
        }),
        ('Contact Information', {
            'fields': ('contact_phone', 'contact_email')
        }),
        ('Developer Info', {
            'fields': ('developer_name', 'completion_year')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('view_count', 'inquiry_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        })
    )
    
    def formatted_price_display(self, obj):
        return obj.formatted_price
    formatted_price_display.short_description = 'Price'
    
    def bedroom_display(self, obj):
        return obj.bedroom_display
    bedroom_display.short_description = 'Bedrooms'
    
    actions = ['make_featured', 'remove_featured', 'mark_available', 'mark_sold']
    
    def make_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} properties marked as featured.')
    make_featured.short_description = "Mark selected properties as featured"
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} properties removed from featured.')
    remove_featured.short_description = "Remove from featured"
    
    def mark_available(self, request, queryset):
        updated = queryset.update(status='available')
        self.message_user(request, f'{updated} properties marked as available.')
    mark_available.short_description = "Mark as available"
    
    def mark_sold(self, request, queryset):
        updated = queryset.update(status='sold')
        self.message_user(request, f'{updated} properties marked as sold.')
    mark_sold.short_description = "Mark as sold"


class ExclusivePropertyImageInline(admin.TabularInline):
    model = ExclusivePropertyImage
    extra = 1
    fields = ['image', 'title', 'description', 'order', 'is_cover']


class ExclusivePropertyAmenityInline(admin.TabularInline):
    model = ExclusivePropertyAmenity
    extra = 1


@admin.register(ExclusivePropertyImage)
class ExclusivePropertyImageAdmin(admin.ModelAdmin):
    list_display = ['property', 'title', 'order', 'is_cover', 'image_preview']
    list_filter = ['is_cover', 'property__district']
    search_fields = ['property__title', 'title']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "No Image"
    image_preview.short_description = 'Preview'


@admin.register(PropertyAmenity)
class PropertyAmenityAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'category']
    list_filter = ['category']
    search_fields = ['name']


@admin.register(PropertyInquiry)
class PropertyInquiryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'property', 'inquiry_type', 'email', 'phone',
        'is_responded', 'created_at'
    ]
    list_filter = [
        'inquiry_type', 'is_responded', 'preferred_contact_method',
        'property__district', 'created_at'
    ]
    search_fields = ['name', 'email', 'phone', 'property__title']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Inquiry Details', {
            'fields': ('property', 'inquiry_type', 'message')
        }),
        ('Contact Information', {
            'fields': ('name', 'email', 'phone', 'preferred_contact_method')
        }),
        ('Additional Info', {
            'fields': ('budget_min', 'budget_max', 'preferred_viewing_time')
        }),
        ('Response Status', {
            'fields': ('is_responded', 'responded_at', 'responded_by')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_responded']
    
    def mark_responded(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            is_responded=True,
            responded_at=timezone.now(),
            responded_by=request.user
        )
        self.message_user(request, f'{updated} inquiries marked as responded.')
    mark_responded.short_description = "Mark as responded"
