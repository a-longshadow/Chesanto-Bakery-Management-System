"""
Seed Production Stock Management Command
=========================================
Creates initial ProductStock entries for all products.

This command should run AFTER seed_products to ensure products exist.

Usage:
    python manage.py seed_production_stock
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

from apps.accounts.models import User
from apps.products.models import Product
from apps.production.models import ProductStock


class Command(BaseCommand):
    help = 'Seed production stock entries for all products'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('📦 SEEDING PRODUCTION STOCK'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # Get system user
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            system_user = User.objects.first()

        if not system_user:
            self.stdout.write(self.style.ERROR('❌ No users found. Run seed_superadmins first!'))
            return

        # Get all products
        products = Product.objects.all()
        if not products.exists():
            self.stdout.write(self.style.ERROR('❌ No products found. Run seed_products first!'))
            return

        created_count = 0

        with transaction.atomic():
            for product in products:
                stock, created = ProductStock.objects.get_or_create(
                    product=product,
                    defaults={
                        'quantity': Decimal('0'),
                        'crates_out': 0,
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created stock: {product.name}'))
                else:
                    self.stdout.write(f'  ⏭️  Exists: {product.name}')

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'✅ PRODUCTION STOCK SEEDING COMPLETE!'))
        self.stdout.write(f'   Created: {created_count} stock entries')
        self.stdout.write('='*60 + '\n')
