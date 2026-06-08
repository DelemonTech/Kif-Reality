from django.core.management.base import BaseCommand
from main.models import BlogPost

SEO_FIXES = {
    "dubai-workers-accommodation": {
        "meta_description": "Explore Dubai workers accommodation options — types, legal requirements, pricing, and what businesses need to know before renting."
    },
    "warehouse-for-sale-in-dubai-industrial-city": {
        "meta_description": "Find warehouses for sale in Dubai Industrial City — pricing, zoning rules, investment potential, and how to buy with expert guidance."
    },
    "trusted-real-estate-advisor-in-dubai": {
        "meta_description": "Work with a trusted real estate advisor in Dubai for expert guidance on buying, selling, and investing in Dubai property."
    },
    "trusted-real-estate-advisor-in-uae": {
        "meta_description": "Find a trusted real estate advisor across the UAE — expert property counsel for Abu Dhabi, Dubai, Sharjah, and beyond."
    },
    "labour-camps-uae": {
        "title": "Labour Camps in UAE: Rules, Costs & Approved Facilities Guide",
        "meta_description": "Complete guide to labour camps in the UAE — approved facilities, MOHRE regulations, costs per bed, and compliance tips for employers.",
    },
    "staff-housing-dip": {
        "title": "Staff Housing in Dubai Investment Park: Options & Pricing",
        "meta_description": "Explore staff housing options in Dubai Investment Park (DIP) — facilities, rental rates, proximity to free zones, and booking tips.",
    },
}

class Command(BaseCommand):
    help = "Fix duplicate meta descriptions and short titles on blog posts"

    def handle(self, *args, **options):
        for slug, fields in SEO_FIXES.items():
            updated = BlogPost.objects.filter(slug=slug).update(**fields)
            if updated:
                self.stdout.write(self.style.SUCCESS(f"Updated: {slug}"))
            else:
                self.stdout.write(self.style.WARNING(f"Not found: {slug}"))
