## 8. main/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from django import forms
from tinymce.widgets import TinyMCE
from .models import Contact, BlogPost, Category, Tag, Comment, Newsletter

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'posts_count', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']
    
    def posts_count(self, obj):
        return obj.posts.filter(status='published').count()
    posts_count.short_description = 'Published Posts'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'posts_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def posts_count(self, obj):
        return obj.posts.filter(status='published').count()
    posts_count.short_description = 'Posts Count'


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    readonly_fields = ['name', 'email', 'content', 'created_at']
    can_delete = True
    
    def has_add_permission(self, request, obj=None):
        return False

class BlogPostAdminForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))

    class Meta:
        model = BlogPost
        fields = '__all__'


class CommentAdminForm(forms.ModelForm):
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 15}))

    class Meta:
        model = Comment
        fields = '__all__'

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    form = BlogPostAdminForm
    list_display = [
        'title', 'category', 'author', 'status', 'is_featured', 
        'views', 'comments_count', 'published_at', 'thumbnail_preview'
    ]
    list_filter = [
        'status', 'category', 'is_featured', 'created_at', 
        'published_at', 'tags'
    ]
    search_fields = ['title', 'excerpt', 'content', 'meta_keywords']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['views', 'created_at', 'updated_at', 'thumbnail_preview']
    filter_horizontal = ['tags']
    date_hierarchy = 'published_at'
    
    fieldsets = [
        ('Content', {
            'fields': ['title', 'slug', 'excerpt', 'content', 'featured_image', 'thumbnail_preview']
        }),
        ('Classification', {
            'fields': ['category', 'tags', 'author', 'status', 'is_featured']
        }),
        ('SEO', {
            'fields': ['meta_description', 'meta_keywords'],
            'classes': ['collapse']
        }),
        ('Statistics', {
            'fields': ['views', 'created_at', 'updated_at', 'published_at'],
            'classes': ['collapse']
        }),
    ]
    
    inlines = [CommentInline]
    
    actions = ['mark_published', 'mark_draft', 'mark_featured', 'unmark_featured']
    
    def thumbnail_preview(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" width="100" height="60" style="object-fit: cover; border-radius: 5px;" />',
                obj.featured_image.url
            )
        return "No image"
    thumbnail_preview.short_description = 'Preview'
    
    def comments_count(self, obj):
        count = obj.comments.filter(is_approved=True).count()
        if count > 0:
            url = reverse('admin:main_comment_changelist') + f'?post__id__exact={obj.id}'
            return format_html('<a href="{}">{} comments</a>', url, count)
        return '0 comments'
    comments_count.short_description = 'Comments'
    
    def mark_published(self, request, queryset):
        updated = queryset.update(status='published')
        # Set published_at for posts that don't have it
        for post in queryset.filter(published_at__isnull=True):
            from django.utils import timezone
            post.published_at = timezone.now()
            post.save(update_fields=['published_at'])
        self.message_user(request, f'{updated} posts marked as published.')
    mark_published.short_description = 'Mark selected posts as published'
    
    def mark_draft(self, request, queryset):
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated} posts marked as draft.')
    mark_draft.short_description = 'Mark selected posts as draft'
    
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} posts marked as featured.')
    mark_featured.short_description = 'Mark selected posts as featured'
    
    def unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} posts unmarked as featured.')
    unmark_featured.short_description = 'Remove featured status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'author').prefetch_related('tags')
    
    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['name', 'post', 'is_approved', 'created_at', 'content_preview']
    list_filter = ['is_approved', 'created_at', 'post__category']
    search_fields = ['name', 'email', 'content', 'post__title']
    readonly_fields = ['created_at']
    actions = ['approve_comments', 'unapprove_comments']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def approve_comments(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} comments approved.')
    approve_comments.short_description = 'Approve selected comments'
    
    def unapprove_comments(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} comments unapproved.')
    unapprove_comments.short_description = 'Unapprove selected comments'


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['email', 'is_active', 'subscribed_at']
    list_filter = ['is_active', 'subscribed_at']
    search_fields = ['email']
    readonly_fields = ['subscribed_at']
    actions = ['activate_subscriptions', 'deactivate_subscriptions']
    
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscriptions activated.')
    activate_subscriptions.short_description = 'Activate selected subscriptions'
    
    def deactivate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscriptions deactivated.')
    deactivate_subscriptions.short_description = 'Deactivate selected subscriptions'


# Customize admin site header and title
admin.site.site_header = "KIF Realty Blog Administration"
admin.site.site_title = "KIF Realty Admin"
admin.site.index_title = "Welcome to KIF Realty Blog Admin"

# @admin.register(ContactMessage)
# class ContactMessageAdmin(admin.ModelAdmin):
#     list_display = ['name', 'email', 'subject', 'created_at', 'is_read']
#     list_filter = ['is_read', 'created_at']
#     search_fields = ['name', 'email', 'subject']
#     readonly_fields = ['created_at']
    
#     def mark_as_read(self, request, queryset):
#         queryset.update(is_read=True)
#     mark_as_read.short_description = "Mark selected messages as read"
    
#     actions = [mark_as_read]

# @admin.register(Newsletter)
# class NewsletterAdmin(admin.ModelAdmin):
#     list_display = ['email', 'subscribed_at', 'is_active']
#     list_filter = ['is_active', 'subscribed_at']
#     search_fields = ['email']
#     readonly_fields = ['subscribed_at']

# @admin.register(ContactInquiry)
# class ContactInquiryAdmin(admin.ModelAdmin):
#     list_display = ("first_name", "last_name", "email", "phone", "investment_budget", "submitted_at")
#     search_fields = ("first_name", "last_name", "email", "phone")
#     list_filter = ("investment_budget", "investment_type", "timeline", "preferred_location")

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'email', 'phone', 'investment_budget', 
        'investment_type', 'timeline', 'is_contacted', 'created_at'
    ]
    list_filter = [
        'investment_budget', 'investment_type', 'preferred_location', 
        'timeline', 'is_contacted', 'created_at'
    ]
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_contacted']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Investment Details', {
            'fields': (
                'investment_budget', 'investment_type', 'preferred_location', 
                'timeline', 'property_interests'
            )
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('Status', {
            'fields': ('is_contacted',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'
    full_name.admin_order_field = 'first_name'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related()
    
    def changelist_view(self, request, extra_context=None):
        # Add summary statistics
        extra_context = extra_context or {}
        
        # Get statistics
        total_contacts = Contact.objects.count()
        contacted = Contact.objects.filter(is_contacted=True).count()
        pending = total_contacts - contacted
        
        # Recent contacts (last 7 days)
        from django.utils import timezone
        from datetime import timedelta
        recent_date = timezone.now() - timedelta(days=7)
        recent_contacts = Contact.objects.filter(created_at__gte=recent_date).count()
        
        extra_context['contact_stats'] = {
            'total': total_contacts,
            'contacted': contacted,
            'pending': pending,
            'recent': recent_contacts
        }
        
        return super().changelist_view(request, extra_context=extra_context)
    
    actions = ['mark_as_contacted', 'mark_as_not_contacted', 'export_as_csv']
    
    def mark_as_contacted(self, request, queryset):
        updated = queryset.update(is_contacted=True)
        self.message_user(request, f'{updated} contact(s) marked as contacted.')
    mark_as_contacted.short_description = 'Mark selected contacts as contacted'
    
    def mark_as_not_contacted(self, request, queryset):
        updated = queryset.update(is_contacted=False)
        self.message_user(request, f'{updated} contact(s) marked as not contacted.')
    mark_as_not_contacted.short_description = 'Mark selected contacts as not contacted'
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="contact_inquiries.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Name', 'Email', 'Phone', 'Investment Budget', 'Investment Type',
            'Property Interests', 'Preferred Location', 'Timeline', 'Message',
            'Contacted', 'Created At'
        ])
        
        for contact in queryset:
            writer.writerow([
                contact.full_name,
                contact.email,
                contact.phone,
                contact.get_investment_budget_display(),
                contact.get_investment_type_display(),
                contact.property_interests,
                contact.get_preferred_location_display(),
                contact.get_timeline_display(),
                contact.message,
                'Yes' if contact.is_contacted else 'No',
                contact.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_as_csv.short_description = 'Export selected contacts as CSV'