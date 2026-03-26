from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap, index as sitemap_index

from .sitemaps import StaticViewSitemap, BlogPostSitemap,  PropertySitemap
# from .sitemaps import BlogSitemap, StaticViewSitemap, PropertySitemap
# from .sitemaps import (
#     BlogSitemap, 
#     StaticViewSitemap, 
#     PropertySitemap,
# )
from main import views as main_views  # import your app's views


sitemaps_dict = {
    'blogs': BlogPostSitemap,
    'static': StaticViewSitemap,
    'properties': PropertySitemap,   
}


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('tinymce/', include('tinymce.urls')),    
    path('ckeditor/', include('ckeditor_uploader.urls')),
    # path('exclusive-properties/', include('exclusive_properties.urls')),
    
    # Sitemap index (main sitemap file)
    path('sitemap.xml', sitemap_index, {'sitemaps': sitemaps_dict}, name='django.contrib.sitemaps.views.sitemap_index'),
    
    # Individual sitemap sections
    path('sitemap-<section>.xml', sitemap, {'sitemaps': sitemaps_dict}, name='django.contrib.sitemaps.views.sitemap'),
    
    # Robots.txt
    path('robots.txt', main_views.robots_txt, name='robots_txt'),
    
    # ✅ Preview 404 page
    path('preview-404/', main_views.preview_404, name='preview_404'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    
# ✅ ADD THIS LINE - Custom 404 handler
handler404 = 'main.views.custom_404'    