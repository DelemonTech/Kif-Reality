from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.text import slugify
from .models import ExclusiveProperty, PropertyInquiry
from .tasks import send_inquiry_notification

@receiver(post_save, sender=ExclusiveProperty)
def property_post_save(sender, instance, created, **kwargs):
    """Handle property save operations"""
    if created:
        # Generate slug if not provided
        if not instance.slug:
            instance.slug = slugify(f"{instance.title}-{instance.district}")
            instance.save(update_fields=['slug'])
    
    # Update search indexes if using search functionality
    # update_search_index.delay(instance.id)

@receiver(post_save, sender=PropertyInquiry)
def inquiry_post_save(sender, instance, created, **kwargs):
    """Handle new inquiries"""
    if created:
        # Send notification email
        send_inquiry_notification.delay(instance.id)
        
        # Update property inquiry count
        instance.property.inquiry_count += 1
        instance.property.save(update_fields=['inquiry_count'])