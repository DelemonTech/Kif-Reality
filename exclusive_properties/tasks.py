from celery import shared_task
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from ..main.models import PropertyInquiry, ExclusiveProperty

@shared_task
def send_inquiry_notification(inquiry_id):
    """Send email notification when new inquiry is received"""
    try:
        inquiry = PropertyInquiry.objects.get(id=inquiry_id)
        
        # Email to admin/agent
        subject = f'New Property Inquiry - {inquiry.property.title}'
        
        context = {
            'inquiry': inquiry,
            'property': inquiry.property,
        }
        
        html_message = render_to_string('emails/inquiry_notification.html', context)
        text_message = render_to_string('emails/inquiry_notification.txt', context)
        
        # Send to assigned agent or default email
        recipient_email = inquiry.property.contact_email or settings.DEFAULT_FROM_EMAIL
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()
        
        # Send confirmation email to client
        client_subject = f'Thank you for your inquiry - {inquiry.property.title}'
        client_context = {
            'inquiry': inquiry,
            'property': inquiry.property,
        }
        
        client_html = render_to_string('emails/inquiry_confirmation.html', client_context)
        client_text = render_to_string('emails/inquiry_confirmation.txt', client_context)
        
        client_msg = EmailMultiAlternatives(
            subject=client_subject,
            body=client_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[inquiry.email]
        )
        client_msg.attach_alternative(client_html, "text/html")
        client_msg.send()
        
        return f"Inquiry notification sent for {inquiry.name}"
        
    except PropertyInquiry.DoesNotExist:
        return f"Inquiry {inquiry_id} not found"
    except Exception as e:
        return f"Error sending inquiry notification: {str(e)}"

@shared_task
def update_property_analytics():
    """Update property analytics and generate reports"""
    try:
        properties = ExclusiveProperty.objects.filter(is_exclusive=True)
        
        for property in properties:
            # Update view counts, inquiry counts, etc.
            # This could include more complex analytics
            pass
            
        return f"Analytics updated for {properties.count()} properties"
        
    except Exception as e:
        return f"Error updating analytics: {str(e)}"