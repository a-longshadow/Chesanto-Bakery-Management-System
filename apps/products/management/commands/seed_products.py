"""
Seed Products Management Command
================================
Creates all products, sub-products (leftovers), and mixes with ingredients.

This command should run AFTER seed_superadmins to ensure users exist for audit fields.

Products created:
- Bread (KES 60) + Bread Leftovers (KES 50)
- Scones (KES 45) + Scones Leftovers (KES 40)
- KDF (KES 35) + KDF Leftovers (KES 30)
- Family Bread 800g (KES 80) + Family Bread 800g Leftovers (KES 70)

Usage:
    python manage.py seed_products
    python manage.py seed_products --reset  # Force update existing
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

from apps.accounts.models import User
from apps.products.models import Product, Mix, MixIngredient
from apps.inventory.models import InventoryItem


class Command(BaseCommand):
    help = 'Seed products, mixes, and ingredients for Chesanto Bakery'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Force update existing products',
        )

    def handle(self, *args, **options):
        reset = options.get('reset', False)

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('🍞 SEEDING PRODUCTS: Chesanto Bakery'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))

        # Get system user for audit fields
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            system_user = User.objects.first()

        if not system_user:
            self.stdout.write(self.style.ERROR('❌ No users found. Run seed_superadmins first!'))
            return

        self.stdout.write(f'Using system user: {system_user.email}\n')

        created_products = 0
        updated_products = 0
        created_mixes = 0

        with transaction.atomic():
            # ===== MAIN PRODUCTS =====
            products_data = [
                ('Bread', Decimal('60.00'), 'Main bread product - machine sliced, fixed yield'),
                ('Scones', Decimal('45.00'), 'Main scones product - machine weighed, fixed yield'),
                ('KDF', Decimal('35.00'), 'KDF (Kenyan Doughnut Fritters) - hand-cut, variable yield'),
                ('Family Bread 800g', Decimal('80.00'), 'Large family-sized bread loaf - 800 grams'),
            ]

            main_products = {}
            for name, price, description in products_data:
                product, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        'selling_price': price,
                        'description': description,
                        'created_by': system_user,
                    }
                )
                if created:
                    created_products += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created: {name} (KES {price})'))
                elif reset:
                    product.selling_price = price
                    product.description = description
                    product.save()
                    updated_products += 1
                    self.stdout.write(self.style.WARNING(f'  ↻ Updated: {name} (KES {price})'))
                else:
                    self.stdout.write(f'  ⏭️  Exists: {name}')
                main_products[name] = product

            # ===== SUB-PRODUCTS (LEFTOVERS) =====
            self.stdout.write('\nCreating leftover products...')
            leftovers_data = [
                ('Bread Leftovers', Decimal('50.00'), 'Day-old or lower quality bread', 'Bread'),
                ('Scones Leftovers', Decimal('40.00'), 'Day-old or lower quality scones', 'Scones'),
                ('KDF Leftovers', Decimal('30.00'), 'Day-old or lower quality KDF', 'KDF'),
                ('Family Bread 800g Leftovers', Decimal('70.00'), 'Day-old Family Bread', 'Family Bread 800g'),
            ]

            for name, price, description, parent_name in leftovers_data:
                parent = main_products.get(parent_name)
                if not parent:
                    self.stdout.write(self.style.ERROR(f'  ❌ Parent not found: {parent_name}'))
                    continue

                product, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        'selling_price': price,
                        'description': description,
                        'parent_product': parent,
                        'created_by': system_user,
                    }
                )
                if created:
                    created_products += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created: {name} (sub of {parent_name})'))
                elif reset:
                    product.selling_price = price
                    product.parent_product = parent
                    product.save()
                    updated_products += 1
                    self.stdout.write(self.style.WARNING(f'  ↻ Updated: {name}'))
                else:
                    self.stdout.write(f'  ⏭️  Exists: {name}')

            # ===== MIXES WITH INGREDIENTS =====
            self.stdout.write('\nCreating mixes and recipes...')
            
            # Get inventory items by name
            def get_inventory_item(name):
                try:
                    return InventoryItem.objects.get(name__icontains=name)
                except InventoryItem.DoesNotExist:
                    return None
                except InventoryItem.MultipleObjectsReturned:
                    return InventoryItem.objects.filter(name__icontains=name).first()

            # ----- BREAD MIX -----
            bread = main_products.get('Bread')
            if bread:
                bread_mix, created = Mix.objects.get_or_create(
                    product=bread,
                    name='Bread Mix Standard',
                    defaults={
                        'expected_yield': Decimal('132'),
                        'is_fixed_yield': True,
                        'notes': 'Standard bread recipe - 132 packets per mix',
                        'created_by': system_user,
                    }
                )
                if created:
                    created_mixes += 1
                    self._create_bread_ingredients(bread_mix, get_inventory_item)
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created: Bread Mix (132 yield)'))
                else:
                    self.stdout.write(f'  ⏭️  Exists: Bread Mix')

            # ----- SCONES MIX -----
            scones = main_products.get('Scones')
            if scones:
                scones_mix, created = Mix.objects.get_or_create(
                    product=scones,
                    name='Scones Mix Standard',
                    defaults={
                        'expected_yield': Decimal('102'),
                        'is_fixed_yield': True,
                        'notes': 'Standard scones recipe - 102 packets per mix',
                        'created_by': system_user,
                    }
                )
                if created:
                    created_mixes += 1
                    self._create_scones_ingredients(scones_mix, get_inventory_item)
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created: Scones Mix (102 yield)'))
                else:
                    self.stdout.write(f'  ⏭️  Exists: Scones Mix')

            # ----- KDF MIX -----
            kdf = main_products.get('KDF')
            if kdf:
                kdf_mix, created = Mix.objects.get_or_create(
                    product=kdf,
                    name='KDF Mix Standard',
                    defaults={
                        'expected_yield': Decimal('102'),
                        'is_fixed_yield': False,
                        'yield_variance_min': Decimal('97'),
                        'yield_variance_max': Decimal('107'),
                        'notes': 'Standard KDF recipe - 97-107 packets per mix (hand-cut, variable)',
                        'created_by': system_user,
                    }
                )
                if created:
                    created_mixes += 1
                    self._create_kdf_ingredients(kdf_mix, get_inventory_item)
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created: KDF Mix (97-107 yield)'))
                else:
                    self.stdout.write(f'  ⏭️  Exists: KDF Mix')

            # ----- FAMILY BREAD MIX -----
            family_bread = main_products.get('Family Bread 800g')
            if family_bread:
                fb_mix, created = Mix.objects.get_or_create(
                    product=family_bread,
                    name='Family Bread 800g Mix',
                    defaults={
                        'expected_yield': Decimal('85'),
                        'is_fixed_yield': True,
                        'notes': 'Family Bread 800g recipe - 85 loaves per mix',
                        'created_by': system_user,
                    }
                )
                if created:
                    created_mixes += 1
                    self._create_family_bread_ingredients(fb_mix, get_inventory_item)
                    self.stdout.write(self.style.SUCCESS(f'  ✅ Created: Family Bread Mix (85 yield)'))
                else:
                    self.stdout.write(f'  ⏭️  Exists: Family Bread Mix')

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ PRODUCTS SEEDING COMPLETE!'))
        self.stdout.write(f'   Products: {created_products} created, {updated_products} updated')
        self.stdout.write(f'   Mixes: {created_mixes} created')
        self.stdout.write('='*60 + '\n')

    def _create_bread_ingredients(self, mix, get_item):
        """Create bread mix ingredients"""
        ingredients = [
            ('Wheat Flour', Decimal('36.000'), 'kg', 'Flour Type 1 - main flour'),
            ('Sugar', Decimal('4.500'), 'kg', 'Sugar'),
            ('Bread Improver', Decimal('0.060'), 'kg', 'Bread Improver (60g)'),
            ('Salt', Decimal('0.280'), 'kg', 'Salt (280g)'),
            ('Calcium', Decimal('0.070'), 'kg', 'Calcium (70g)'),
            ('Yeast', Decimal('0.200'), 'kg', 'Yeast (200g)'),
            ('Cooking Fat', Decimal('2.800'), 'kg', 'Cooking Fat'),
        ]
        self._create_mix_ingredients(mix, ingredients, get_item)

    def _create_scones_ingredients(self, mix, get_item):
        """Create scones mix ingredients"""
        ingredients = [
            ('Wheat Flour', Decimal('26.000'), 'kg', 'Flour Type 1'),
            ('Sugar', Decimal('3.800'), 'kg', 'Sugar'),
            ('Bread Improver', Decimal('0.050'), 'kg', 'Bread Improver (50g)'),
            ('Salt', Decimal('0.280'), 'kg', 'Salt (280g)'),
            ('Calcium', Decimal('0.050'), 'kg', 'Calcium (50g)'),
            ('Yeast', Decimal('0.190'), 'kg', 'Yeast (190g)'),
            ('Cooking Fat', Decimal('2.300'), 'kg', 'Cooking Fat'),
        ]
        self._create_mix_ingredients(mix, ingredients, get_item)

    def _create_kdf_ingredients(self, mix, get_item):
        """Create KDF mix ingredients"""
        ingredients = [
            ('Wheat Flour', Decimal('50.000'), 'kg', 'Flour Type 1'),
            ('Sugar', Decimal('2.500'), 'kg', 'Sugar'),
            ('Salt', Decimal('0.300'), 'kg', 'Salt (300g)'),
            ('Calcium', Decimal('0.060'), 'kg', 'Calcium (60g)'),
            ('Yeast', Decimal('0.160'), 'kg', 'Yeast (160g)'),
            ('Cooking Fat', Decimal('1.500'), 'kg', 'Cooking Fat'),
            ('Cooking Oil', Decimal('7.500'), 'L', 'Cooking Oil - for frying'),
        ]
        self._create_mix_ingredients(mix, ingredients, get_item)

    def _create_family_bread_ingredients(self, mix, get_item):
        """Create Family Bread 800g mix ingredients"""
        ingredients = [
            ('Wheat Flour', Decimal('50.000'), 'kg', 'Flour Type 1'),
            ('Sugar', Decimal('6.250'), 'kg', 'Sugar'),
            ('Bread Improver', Decimal('0.085'), 'kg', 'Bread Improver (85g)'),
            ('Salt', Decimal('0.400'), 'kg', 'Salt (400g)'),
            ('Calcium', Decimal('0.100'), 'kg', 'Calcium (100g)'),
            ('Yeast', Decimal('0.280'), 'kg', 'Yeast (280g)'),
            ('Cooking Fat', Decimal('4.000'), 'kg', 'Cooking Fat'),
        ]
        self._create_mix_ingredients(mix, ingredients, get_item)

    def _create_mix_ingredients(self, mix, ingredients, get_item):
        """Helper to create mix ingredients"""
        for item_name, qty, unit, notes in ingredients:
            item = get_item(item_name)
            if item:
                MixIngredient.objects.get_or_create(
                    mix=mix,
                    inventory_item=item,
                    defaults={
                        'quantity_required': qty,
                        'unit_of_measure': unit,
                        'notes': notes,
                    }
                )
            else:
                self.stdout.write(self.style.WARNING(f'    ⚠️  Inventory item not found: {item_name}'))
