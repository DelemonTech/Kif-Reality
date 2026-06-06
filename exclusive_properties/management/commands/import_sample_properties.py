from django.core.management.base import BaseCommand
from exclusive_properties.models import ExclusiveProperty, PropertyAmenity, ExclusivePropertyAmenity
from django.utils.text import slugify
from django.contrib.auth.models import User
import random

class Command(BaseCommand):
    help = 'Import sample exclusive properties for demonstration'
    
    def handle(self, *args, **options):
        # Create sample amenities
        amenities_data = [
            ('Swimming Pool', 'fas fa-swimming-pool', 'Recreation'),
            ('Gym & Fitness', 'fas fa-dumbbell', 'Recreation'),
            ('Covered Parking', 'fas fa-car', 'Convenience'),
            ('24/7 Security', 'fas fa-shield-alt', 'Security'),
            ('Concierge Service', 'fas fa-concierge-bell', 'Service'),
            ('Garden & Landscaping', 'fas fa-leaf', 'Recreation'),
            ('Children\'s Playground', 'fas fa-child', 'Recreation'),
            ('Business Center', 'fas fa-briefcase', 'Business'),
            ('Spa & Wellness', 'fas fa-spa', 'Recreation'),
            ('Rooftop Terrace', 'fas fa-building', 'Recreation'),
            ('Private Beach Access', 'fas fa-umbrella-beach', 'Recreation'),
            ('Tennis Court', 'fas fa-table-tennis', 'Recreation'),
            ('BBQ Area', 'fas fa-fire', 'Recreation'),
            ('Pet Friendly', 'fas fa-paw', 'Convenience'),
            ('Smart Home System', 'fas fa-home', 'Technology'),
        ]
        
        for name, icon, category in amenities_data:
            PropertyAmenity.objects.get_or_create(
                name=name,
                defaults={'icon': icon, 'category': category}
            )
        
        # Get or create a default user for assigned_agent
        default_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@kifrealty.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        # Create comprehensive sample properties
        sample_properties = [
            # Dubai Marina Properties
            {
                'title': 'Luxury Marina Penthouse',
                'property_type': 'penthouse',
                'city': 'Dubai',
                'district': 'Dubai Marina',
                'neighborhood': 'Marina Gate',
                'bedrooms': 3,
                'bathrooms': 4,
                'area_sqft': 2400,
                'price': 2850000,
                'developer_name': 'Emaar Properties',
                'completion_year': 2024,
                'short_description': 'Stunning penthouse with panoramic marina views and premium finishes.',
                'description': '<p>Experience luxury living at its finest in this spectacular penthouse overlooking the iconic Dubai Marina. Features include floor-to-ceiling windows, private elevator access, and world-class amenities.</p>'
            },
            {
                'title': 'Marina Waterfront Apartment',
                'property_type': 'apartment',
                'city': 'Dubai',
                'district': 'Dubai Marina',
                'neighborhood': 'Marina Heights',
                'bedrooms': 2,
                'bathrooms': 2,
                'area_sqft': 1200,
                'price': 1200000,
                'developer_name': 'Damac Properties',
                'completion_year': 2023,
                'short_description': 'Modern apartment with direct marina access and contemporary design.',
                'description': '<p>This beautifully designed apartment offers the perfect blend of comfort and luxury in the heart of Dubai Marina.</p>'
            },
            
            # Downtown Dubai Properties
            {
                'title': 'Burj Views Luxury Apartment',
                'property_type': 'apartment',
                'city': 'Dubai',
                'district': 'Downtown Dubai',
                'neighborhood': 'Burj Views',
                'bedrooms': 2,
                'bathrooms': 3,
                'area_sqft': 1400,
                'price': 1800000,
                'developer_name': 'Emaar Properties',
                'completion_year': 2024,
                'short_description': 'Exclusive apartment with direct views of the Burj Khalifa.',
                'description': '<p>Wake up to breathtaking views of the world\'s tallest building from this premium apartment in Downtown Dubai.</p>'
            },
            {
                'title': 'Downtown Studio Loft',
                'property_type': 'studio',
                'city': 'Dubai',
                'district': 'Downtown Dubai',
                'neighborhood': 'The Address',
                'bedrooms': 0,
                'bathrooms': 1,
                'area_sqft': 650,
                'price': 850000,
                'developer_name': 'Emaar Properties',
                'completion_year': 2023,
                'short_description': 'Sophisticated studio loft in the heart of Downtown Dubai.',
                'description': '<p>Perfect for young professionals, this studio loft offers modern living in Dubai\'s most prestigious location.</p>'
            },
            
            # Palm Jumeirah Properties
            {
                'title': 'Palm Beach Villa',
                'property_type': 'villa',
                'city': 'Dubai',
                'district': 'Palm Jumeirah',
                'neighborhood': 'Palm West Beach',
                'bedrooms': 6,
                'bathrooms': 7,
                'area_sqft': 5200,
                'price': 8500000,
                'developer_name': 'Nakheel',
                'completion_year': 2024,
                'short_description': 'Exclusive beachfront villa with private pool and garden.',
                'description': '<p>Experience ultimate luxury in this beachfront villa on the iconic Palm Jumeirah with private beach access.</p>'
            },
            {
                'title': 'Palm Marina Apartment',
                'property_type': 'apartment',
                'city': 'Dubai',
                'district': 'Palm Jumeirah',
                'neighborhood': 'Marina Residences',
                'bedrooms': 3,
                'bathrooms': 3,
                'area_sqft': 1800,
                'price': 2200000,
                'developer_name': 'Nakheel',
                'completion_year': 2023,
                'short_description': 'Premium apartment with marina and sea views.',
                'description': '<p>Enjoy the best of both worlds with marina and sea views from this premium Palm Jumeirah apartment.</p>'
            },
            
            # Dubai Hills Estate Properties
            {
                'title': 'Hills Golf Villa',
                'property_type': 'villa',
                'city': 'Dubai',
                'district': 'Dubai Hills Estate',
                'neighborhood': 'Golf Views',
                'bedrooms': 4,
                'bathrooms': 5,
                'area_sqft': 3200,
                'price': 3800000,
                'developer_name': 'Emaar Properties',
                'completion_year': 2024,
                'short_description': 'Golf course villa with panoramic views and modern amenities.',
                'description': '<p>Perfect for golf enthusiasts, this villa offers stunning golf course views and premium amenities.</p>'
            },
            {
                'title': 'Hills Townhouse',
                'property_type': 'townhouse',
                'city': 'Dubai',
                'district': 'Dubai Hills Estate',
                'neighborhood': 'Park Views',
                'bedrooms': 3,
                'bathrooms': 3,
                'area_sqft': 2100,
                'price': 2200000,
                'developer_name': 'Emaar Properties',
                'completion_year': 2023,
                'short_description': 'Modern townhouse with park views and family-friendly amenities.',
                'description': '<p>Ideal for families, this townhouse offers spacious living with access to parks and community facilities.</p>'
            },
            
            # Business Bay Properties
            {
                'title': 'Bay Business Apartment',
                'property_type': 'apartment',
                'city': 'Dubai',
                'district': 'Business Bay',
                'neighborhood': 'Bay Square',
                'bedrooms': 2,
                'bathrooms': 2,
                'area_sqft': 1100,
                'price': 1400000,
                'developer_name': 'Damac Properties',
                'completion_year': 2024,
                'short_description': 'Executive apartment in Dubai\'s business district.',
                'description': '<p>Perfect for business professionals, this apartment offers easy access to Dubai\'s major business hubs.</p>'
            },
            
            # JVC Properties
            {
                'title': 'JVC Family Villa',
                'property_type': 'villa',
                'city': 'Dubai',
                'district': 'Jumeirah Village Circle',
                'neighborhood': 'Circle Village',
                'bedrooms': 4,
                'bathrooms': 4,
                'area_sqft': 2800,
                'price': 2100000,
                'developer_name': 'Azizi Developments',
                'completion_year': 2023,
                'short_description': 'Family villa with garden and community amenities.',
                'description': '<p>Spacious family villa in the peaceful JVC community with excellent amenities and schools nearby.</p>'
            },
            
            # Abu Dhabi Properties
            {
                'title': 'Saadiyat Beach Villa',
                'property_type': 'villa',
                'city': 'Abu Dhabi',
                'district': 'Saadiyat Island',
                'neighborhood': 'Beach Villas',
                'bedrooms': 5,
                'bathrooms': 6,
                'area_sqft': 4500,
                'price': 6500000,
                'developer_name': 'Mubadala',
                'completion_year': 2024,
                'short_description': 'Luxury beachfront villa on Saadiyat Island.',
                'description': '<p>Experience the epitome of luxury living on Abu Dhabi\'s cultural island with private beach access.</p>'
            },
            
            # Sharjah Properties
            {
                'title': 'Sharjah Waterfront Apartment',
                'property_type': 'apartment',
                'city': 'Sharjah',
                'district': 'Al Khan',
                'neighborhood': 'Waterfront',
                'bedrooms': 2,
                'bathrooms': 2,
                'area_sqft': 1000,
                'price': 800000,
                'developer_name': 'Sharjah Investment and Development Authority',
                'completion_year': 2023,
                'short_description': 'Affordable luxury apartment with waterfront views.',
                'description': '<p>Enjoy waterfront living at an affordable price in this modern Sharjah apartment.</p>'
            },
        ]
        
        for prop_data in sample_properties:
            prop_data['slug'] = slugify(f"{prop_data['title']}-{prop_data['district']}")
            prop_data['assigned_agent'] = default_user
            prop_data['is_exclusive'] = True
            prop_data['status'] = 'available'
            
            # Check if property already exists by title and district
            existing_property = ExclusiveProperty.objects.filter(
                title=prop_data['title'],
                district=prop_data['district']
            ).first()
            
            if existing_property:
                self.stdout.write(
                    self.style.WARNING(f'Property already exists: {prop_data["title"]} - {prop_data["district"]}')
                )
                continue
            
            try:
                property_obj = ExclusiveProperty.objects.create(**prop_data)
                created = True
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating property {prop_data["title"]}: {str(e)}')
                )
                continue
            
            if created:
                # Add random amenities (3-6 amenities per property)
                amenities = list(PropertyAmenity.objects.all())
                selected_amenities = random.sample(amenities, random.randint(3, 6))
                
                # Create ExclusivePropertyAmenity instances
                for amenity in selected_amenities:
                    ExclusivePropertyAmenity.objects.create(
                        property=property_obj,
                        amenity=amenity
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Created property: {property_obj.title} - {property_obj.district}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully imported {len(sample_properties)} sample exclusive properties')
        )
        
        # Print summary
        total_properties = ExclusiveProperty.objects.filter(is_exclusive=True).count()
        cities = ExclusiveProperty.objects.values_list('city', flat=True).distinct()
        districts = ExclusiveProperty.objects.values_list('district', flat=True).distinct()
        
        self.stdout.write(
            self.style.SUCCESS(f'Total exclusive properties: {total_properties}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Cities available: {", ".join(cities)}')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Districts available: {", ".join(districts)}')
        )