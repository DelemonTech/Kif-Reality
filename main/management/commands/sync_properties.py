# from django.core.management.base import BaseCommand
# from main.property_sync import PropertySyncService


# class Command(BaseCommand):
#     help = 'Sync properties from external API to database'

#     def add_arguments(self, parser):
#         parser.add_argument(
#             '--max-pages',
#             type=int,
#             default=None,
#             help='Maximum number of pages to fetch',
#         )

#     def handle(self, *args, **options):
#         max_pages = options.get('max_pages')
        
#         self.stdout.write("Starting property sync from API...")
        
#         if max_pages:
#             self.stdout.write(f"Max pages limit: {max_pages}")
        
#         stats = PropertySyncService.sync_all_properties(max_pages=max_pages)
        
#         self.stdout.write("\n" + "="*50)
#         self.stdout.write(self.style.SUCCESS("SYNC COMPLETED"))
#         self.stdout.write("="*50)
#         self.stdout.write(f"Pages processed: {stats['pages_processed']}")
#         self.stdout.write(f"Total fetched: {stats['total_fetched']}")
#         self.stdout.write(self.style.SUCCESS(f"✓ Created: {stats['created']}"))
#         self.stdout.write(self.style.WARNING(f"↻ Updated: {stats['updated']}"))
        
#         if stats['errors'] > 0:
#             self.stdout.write(self.style.ERROR(f"✗ Errors: {stats['errors']}"))
        
#         self.stdout.write("="*50)