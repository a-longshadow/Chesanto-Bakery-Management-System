"""
Management command to seed sample suppliers for testing
Usage: python manage.py seed_suppliers
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.inventory.models import Supplier


class Command(BaseCommand):
    help = 'Seed sample suppliers for inventory purchases'
    
    def handle(self, *args, **options):
        User = get_user_model()
        
        # Get or create a system user for created_by field
        system_user = User.objects.filter(role='SUPERADMIN').first()
        if not system_user:
            self.stdout.write(self.style.ERROR('No SUPERADMIN user found. Please create one first.'))
            return
        
        # Sample suppliers (common suppliers in Kenya)
        suppliers_data = [
            {
                'name': 'Pembe Flour Mills Ltd',
                'contact_person': 'John Kamau',
                'phone': '+254 722 123456',
                'email': 'sales@pembeflour.co.ke',
                'address': 'Enterprise Road, Industrial Area, Nairobi',
                'payment_terms': 'Net 30 days',
            },
            {
                'name': 'Mumias Sugar Company',
                'contact_person': 'Mary Wanjiru',
                'phone': '+254 733 234567',
                'email': 'orders@mumias.co.ke',
                'address': 'Mumias, Kakamega County',
                'payment_terms': 'Cash on delivery',
            },
            {
                'name': 'Bidco Africa Ltd',
                'contact_person': 'Peter Omondi',
                'phone': '+254 711 345678',
                'email': 'sales@bidco-oil.com',
                'address': 'Thika Road, Ruiru',
                'payment_terms': 'Net 14 days',
            },
            {
                'name': 'Kenya Breweries Ltd (Yeast Division)',
                'contact_person': 'Sarah Muthoni',
                'phone': '+254 722 456789',
                'email': 'industrial@kbl.co.ke',
                'address': 'Ruaraka, Nairobi',
                'payment_terms': 'Net 21 days',
            },
            {
                'name': 'Fresh Dairy Ltd',
                'contact_person': 'James Kipchoge',
                'phone': '+254 733 567890',
                'email': 'sales@freshdairy.co.ke',
                'address': 'Eldoret, Uasin Gishu County',
                'payment_terms': 'Cash on delivery',
            },
            {
                'name': 'Unga Group Ltd',
                'contact_person': 'Grace Njeri',
                'phone': '+254 722 678901',
                'email': 'orders@unga.com',
                'address': 'Mombasa Road, Nairobi',
                'payment_terms': 'Net 30 days',
            },
            {
                'name': 'East African Packaging Industries',
                'contact_person': 'David Otieno',
                'phone': '+254 711 789012',
                'email': 'sales@eapi.co.ke',
                'address': 'Industrial Area, Nairobi',
                'payment_terms': 'Net 14 days',
            },
            {
                'name': 'Kenya Shell Distributors (Fuel)',
                'contact_person': 'Michael Wanyama',
                'phone': '+254 733 890123',
                'email': 'commercial@shell.co.ke',
                'address': 'Shell Service Station, Kisumu Road',
                'payment_terms': 'Cash on delivery',
            },
        ]
        
        created_count = 0
        skipped_count = 0
        
        for supplier_data in suppliers_data:
            # Check if supplier already exists
            if Supplier.objects.filter(name=supplier_data['name']).exists():
                self.stdout.write(
                    self.style.WARNING(f'Supplier "{supplier_data["name"]}" already exists. Skipping.')
                )
                skipped_count += 1
                continue
            
            # Create supplier
            supplier = Supplier.objects.create(
                name=supplier_data['name'],
                contact_person=supplier_data['contact_person'],
                phone=supplier_data['phone'],
                email=supplier_data['email'],
                address=supplier_data['address'],
                payment_terms=supplier_data['payment_terms'],
                is_active=True,
                created_by=system_user
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Created supplier: {supplier.name}')
            )
            created_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(f'Supplier seeding complete!'))
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count} suppliers'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'Skipped: {skipped_count} suppliers (already exist)'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write('You can now create purchase orders with these suppliers.')
        self.stdout.write('Go to: Admin → Inventory → Purchases → Add Purchase')
