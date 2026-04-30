from django.urls import path, include, re_path

from . import views



urlpatterns = [
    path('', views.index, name='index'),

    #Exclusive
    path('exclusive/', include('exclusive_properties.urls')),

    # path('model1/', views.model1, name='model1'),
    #  path('basenew/', views.basenw, name='basenew'),

    # Properties
    path('properties/', views.properties, name='properties'),
    
    # ✅ ADD THIS - Old property URL redirect (MUST come BEFORE the new format)
    path('property/<int:property_id>/', views.property_redirect, name='property_old'),

    # path('property/<int:pk>/', views.property_detail, name='property_detail'),
    re_path(r'^property/(?P<slug>[\w-]+)-(?P<pk>\d+)/$', views.property_detail, name='property_detail'),  # ✅ slug-id format
    # path('property/<int:property_id>/unit/<int:unit_id>/', views.unit_detail, name='unit_detail'),
     # Unit detail
    path('property/<slug:property_slug>-<int:property_id>/unit/<int:unit_id>/', views.unit_detail, name='unit_detail'),


    # Static pages
    path('about/', views.about, name='about'),

    # Blogs
    path('blogs/', views.blog_list, name='blogs'),
    path('blogs/search/', views.blog_search, name='blog_search'),
    path('blogs/category/<slug:slug>/', views.blog_category, name='blog_category'),
    path('blogs/tag/<slug:slug>/', views.blog_tag, name='blog_tag'),
    path('blogs/<slug:slug>/', views.blog_detail, name='blog_detail'),

    # API
    path('api/newsletter/subscribe/', views.subscribe_newsletter, name='subscribe_newsletter'),
    path('api/search/', views.search_properties_api, name='search_properties_api'),
    path('api/properties/filter/', views.filter_properties_api, name='filter_properties_api'),
    path('cities/', views.cities_api, name='cities_api'),  # Cities API for React frontend
    path('api/developers/', views.developers_api, name='developers_api'),
    path('api/developers-local/', views.developers_from_properties, name='developers_local'),
    
    path('contact/', views.contact_view, name='contact'),
    path('contact/submit/', views.contact_submit, name='contact_submit'),
    path('contact/ajax-submit/', views.contact_submit_ajax, name='contact_submit_ajax'),

    # Newsletter
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),

    path('privacy-policy/',views.privacy, name='privacy-policy'),
    path('terms-and-conditions/',views.terms, name='terms-and-conditions'),
    path('rera-compliance/',views.rera, name='rera-compliance'),
    

    # landingpages
    # ---------------KIF REALTY-------------
       
    path('retail-spaces',views.retail, name='retail-spaces'),
    path('secondary-residential-properties',views.second, name='secondary-residential-properties'),
    path('commercial-properties',views.commercial, name='commercial-properties'),
    path('luxury-villas-townhouses',views.luxury, name='luxury-villas-townhouses'),
    path('beachfront-Properties',views.beach, name='beachfront-Properties'),
    path('off-plan-residential-properties',views.offplan, name='off-plan-residential-properties'),
    path('labour-camps',views.labour, name='labour-camps'),
    path('warehouses-for-sale',views.warehouse, name='warehouses-for-sale'),
    path('plots-for-sale',views.plots, name='plots-for-sale'),
    path('mansions-for-sale',views.mansions, name='mansions-for-sale'),
    path('developers/', views.developers, name='developers'),
    
]