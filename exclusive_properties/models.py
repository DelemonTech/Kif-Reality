from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from ckeditor.fields import RichTextField
import uuid

class ExclusiveProperty(models.Model):
    PROPERTY_TYPES = [
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('townhouse', 'Townhouse'),
        ('penthouse', 'Penthouse'),
        ('studio', 'Studio'),
        ('duplex', 'Duplex'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('under_offer', 'Under Offer'),
        ('off_market', 'Off Market'),
    ]
    
    PRIORITY_LEVELS = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Featured'),
        (5, 'Premium'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, blank=True)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    
    # Location Details
    city = models.CharField(max_length=100, default='Dubai')
    district = models.CharField(max_length=100)
    neighborhood = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    
    # Property Specifications
    bedrooms = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(20)])
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, validators=[MinValueValidator(0.5)])
    area_sqft = models.PositiveIntegerField(help_text="Area in square feet")
    plot_size = models.PositiveIntegerField(blank=True, null=True, help_text="Plot size in square feet")
    
    # Pricing
    price = models.DecimalField(max_digits=12, decimal_places=2)
    price_per_sqft = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    service_charge = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    
    # Content
    description = RichTextField()
    short_description = models.TextField(max_length=300, blank=True)
    key_features = models.JSONField(default=list, blank=True)
    nearby_amenities = models.JSONField(default=list, blank=True)
    
    # Media
    cover_image = models.ImageField(upload_to='exclusive_properties/covers/')
    video_url = models.URLField(blank=True, help_text="YouTube or Vimeo URL")
    virtual_tour_url = models.URLField(blank=True)
    floor_plan = models.FileField(upload_to='exclusive_properties/floor_plans/', blank=True)
    
    # Status & Management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    priority = models.IntegerField(choices=PRIORITY_LEVELS, default=1)
    is_featured = models.BooleanField(default=False)
    is_exclusive = models.BooleanField(default=True)
    
    # Contact Information
    assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    
    # Developer Information
    developer_name = models.CharField(max_length=200, blank=True)
    completion_year = models.PositiveIntegerField(blank=True, null=True)
    
    # SEO & Marketing
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(max_length=300, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    inquiry_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = 'Exclusive Property'
        verbose_name_plural = 'Exclusive Properties'
    
    def __str__(self):
        return f"{self.title} - {self.get_property_type_display()}"
    
    def get_absolute_url(self):
        return reverse('exclusive_property_detail', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(f"{self.title}-{self.district}")
        
        if self.area_sqft and self.price:
            self.price_per_sqft = self.price / self.area_sqft
            
        super().save(*args, **kwargs)
    
    @property
    def formatted_price(self):
        return f"AED {self.price:,.0f}"
    
    @property
    def bedroom_display(self):
        if self.bedrooms == 0:
            return "Studio"
        return f"{self.bedrooms} BR"


class ExclusivePropertyImage(models.Model):
    property = models.ForeignKey(ExclusiveProperty, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='exclusive_properties/gallery/')
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"{self.property.title} - Image {self.order}"


class PropertyAmenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(max_length=50, help_text="FontAwesome icon class")
    category = models.CharField(max_length=50, blank=True)
    
    class Meta:
        verbose_name_plural = 'Property Amenities'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class ExclusivePropertyAmenity(models.Model):
    property = models.ForeignKey(ExclusiveProperty, on_delete=models.CASCADE, related_name='amenities')
    amenity = models.ForeignKey(PropertyAmenity, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['property', 'amenity']
    
    def __str__(self):
        return f"{self.property.title} - {self.amenity.name}"


class PropertyInquiry(models.Model):
    INQUIRY_TYPES = [
        ('viewing', 'Property Viewing'),
        ('info', 'More Information'),
        ('offer', 'Make Offer'),
        ('callback', 'Request Callback'),
        ('brochure', 'Request Brochure'),
    ]
    
    property = models.ForeignKey(ExclusiveProperty, on_delete=models.CASCADE, related_name='inquiries')
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_TYPES)
    
    # Contact Details
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    # Inquiry Details
    message = models.TextField(blank=True)
    preferred_contact_method = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('whatsapp', 'WhatsApp'),
    ], default='email')
    
    # Additional Info
    budget_min = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    budget_max = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    preferred_viewing_time = models.DateTimeField(blank=True, null=True)
    
    # Status
    is_responded = models.BooleanField(default=False)
    responded_at = models.DateTimeField(blank=True, null=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.property.title} ({self.get_inquiry_type_display()})"

