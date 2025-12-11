"""
Management command to seed default miscellaneous expense categories.
Run with: python manage.py seed_expense_categories
"""
from django.core.management.base import BaseCommand
from apps.payroll.models import MiscExpenseCategory


class Command(BaseCommand):
    help = 'Seed default miscellaneous expense categories'

    # Default expense categories for a bakery business
    DEFAULT_CATEGORIES = [
        {
            'name': 'Bank Charges',
            'description': 'Bank fees, transaction charges, ATM fees, account maintenance fees'
        },
        {
            'name': 'License & Permits',
            'description': 'Business licenses, health permits, fire safety certificates, trade licenses'
        },
        {
            'name': 'Repairs & Maintenance',
            'description': 'Equipment repairs, building maintenance, plumbing, electrical work'
        },
        {
            'name': 'Transport & Delivery',
            'description': 'Fuel costs, delivery charges, vehicle maintenance, courier services'
        },
        {
            'name': 'Utilities',
            'description': 'Electricity, water, gas, internet, phone bills'
        },
        {
            'name': 'Rent',
            'description': 'Shop rent, storage rent, equipment rental'
        },
        {
            'name': 'Insurance',
            'description': 'Business insurance, property insurance, vehicle insurance'
        },
        {
            'name': 'Office Supplies',
            'description': 'Stationery, printer ink, paper, office equipment'
        },
        {
            'name': 'Cleaning Supplies',
            'description': 'Detergents, sanitizers, cleaning tools, waste disposal'
        },
        {
            'name': 'Packaging Materials',
            'description': 'Boxes, bags, labels, wrapping materials (not tracked in inventory)'
        },
        {
            'name': 'Professional Fees',
            'description': 'Accountant fees, legal fees, consultant fees'
        },
        {
            'name': 'Marketing & Advertising',
            'description': 'Signage, flyers, social media ads, promotions'
        },
        {
            'name': 'Training & Development',
            'description': 'Staff training, workshops, courses, certifications'
        },
        {
            'name': 'Miscellaneous',
            'description': 'Other expenses that do not fit into specific categories'
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of all categories (will not delete existing)'
        )

    def handle(self, *args, **options):
        self.stdout.write('Seeding expense categories...\n')
        
        created_count = 0
        existing_count = 0
        
        for category_data in self.DEFAULT_CATEGORIES:
            category, created = MiscExpenseCategory.objects.get_or_create(
                name=category_data['name'],
                defaults={
                    'description': category_data['description'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {category.name}')
                )
            else:
                existing_count += 1
                self.stdout.write(
                    self.style.WARNING(f'  • Exists: {category.name}')
                )
        
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(
            self.style.SUCCESS(f'Summary: {created_count} created, {existing_count} already existed')
        )
        self.stdout.write(
            self.style.SUCCESS('Expense categories seeded successfully!')
        )
