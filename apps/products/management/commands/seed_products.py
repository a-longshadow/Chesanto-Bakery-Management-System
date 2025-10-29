"""
Django Management Command: Seed Products Data
Seeds products, ingredients, and mixes (recipes)
Based on MILESTONE_2.md specifications
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.products.models import Product, Ingredient, Mix, MixIngredient
from apps.inventory.models import InventoryItem
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed products data: products, ingredients, and mixes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Starting Products Data Seeding ===\n'))
        
        # Get or create a superuser for created_by fields
        admin_user = User.objects.filter(role='SUPERADMIN').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        # Step 1: Seed Products
        self.seed_products(admin_user)
        
        # Step 2: Seed Ingredients (linked to InventoryItems will be done in Day 5)
        self.seed_ingredients(admin_user)
        
        # Step 3: Seed Mixes
        self.seed_mixes(admin_user)
        
        self.stdout.write(self.style.SUCCESS('\n=== Products Data Seeding Complete! ===\n'))

    def seed_products(self, admin_user):
        """Seed 3 main products + 1 sub-product"""
        self.stdout.write('\n🍞 Seeding Products...')
        
        products = [
            {
                'name': 'Bread',
                'alias': 'Loaves',
                'description': 'Standard white bread loaves',
                'has_variable_output': False,
                'baseline_output': 132,
                'min_expected_output': None,
                'max_expected_output': None,
                'units_per_packet': 1,
                'packet_label': 'loaf',
                'price_per_packet': Decimal('60.00'),
                'has_sub_product': True,
                'sub_product_name': 'Bread Rejects',
                'sub_product_price': Decimal('50.00'),
            },
            {
                'name': 'KDF',
                'alias': 'Packets',
                'description': 'KDF mandazi packets (hand-cut, variable output)',
                'has_variable_output': True,
                'baseline_output': 107,
                'min_expected_output': 98,
                'max_expected_output': 107,
                'units_per_packet': 12,
                'packet_label': 'packet',
                'price_per_packet': Decimal('100.00'),
                'has_sub_product': False,
                'sub_product_name': '',
                'sub_product_price': None,
            },
            {
                'name': 'Scones',
                'alias': 'Packets',
                'description': 'Scones packets (12 pieces per packet)',
                'has_variable_output': False,
                'baseline_output': 102,
                'min_expected_output': None,
                'max_expected_output': None,
                'units_per_packet': 12,
                'packet_label': 'packet',
                'price_per_packet': Decimal('50.00'),
                'has_sub_product': False,
                'sub_product_name': '',
                'sub_product_price': None,
            },
        ]
        
        for prod_data in products:
            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    **prod_data,
                    'created_by': admin_user,
                    'updated_by': admin_user
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Created: {product.name} (KES {product.price_per_packet}/{product.packet_label})"
                ))
                if product.has_sub_product:
                    self.stdout.write(self.style.SUCCESS(
                        f"    → Sub-product: {product.sub_product_name} (KES {product.sub_product_price}/{product.packet_label})"
                    ))
            else:
                self.stdout.write(f"  → Already exists: {product.name}")

    def seed_ingredients(self, admin_user):
        """Seed ingredients and link to InventoryItems"""
        self.stdout.write('\n🥖 Seeding Ingredients...')
        
        from apps.inventory.models import InventoryItem
        
        # Map ingredient names to inventory item names
        ingredient_inventory_map = {
            'Wheat Flour': 'Wheat Flour',
            'Sugar': 'Sugar',
            'Cooking Fat': 'Cooking Fat',
            'Cooking Oil': 'Cooking Oil',
            'Yeast (Standard)': 'Yeast (Standard)',
            'Yeast (2-in-1)': 'Yeast (2-in-1)',
            'Bread Improver': 'Bread Improver',
            'Salt': 'Salt',
            'Calcium': 'Calcium',
            'Food Colour': 'Food Colour',
        }
        
        ingredients = [
            # Raw materials
            {'name': 'Wheat Flour', 'default_unit': 'kg'},
            {'name': 'Sugar', 'default_unit': 'kg'},
            {'name': 'Cooking Fat', 'default_unit': 'kg'},
            {'name': 'Cooking Oil', 'default_unit': 'l'},
            {'name': 'Yeast (Standard)', 'default_unit': 'g'},
            {'name': 'Yeast (2-in-1)', 'default_unit': 'g'},
            {'name': 'Bread Improver', 'default_unit': 'g'},
            {'name': 'Salt', 'default_unit': 'g'},
            {'name': 'Calcium', 'default_unit': 'g'},
            {'name': 'Food Colour', 'default_unit': 'ml'},
        ]
        
        for ing_data in ingredients:
            # Find corresponding inventory item
            inventory_item = None
            inventory_name = ingredient_inventory_map.get(ing_data['name'])
            if inventory_name:
                try:
                    inventory_item = InventoryItem.objects.get(name=inventory_name)
                except InventoryItem.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"  ⚠ Inventory item not found for: {ing_data['name']}"
                    ))
            
            ingredient, created = Ingredient.objects.get_or_create(
                name=ing_data['name'],
                defaults={
                    'default_unit': ing_data['default_unit'],
                    'description': f"{ing_data['name']} for recipes",
                    'inventory_item': inventory_item,
                    'created_by': admin_user,
                    'updated_by': admin_user
                }
            )
            
            # Update existing ingredients with inventory link if not set
            if not created and not ingredient.inventory_item and inventory_item:
                ingredient.inventory_item = inventory_item
                ingredient.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Updated: {ingredient.name} → linked to {inventory_item.name}"
                ))
            elif created:
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Created: {ingredient.name} ({ingredient.default_unit})"
                ))
                if inventory_item:
                    self.stdout.write(self.style.SUCCESS(
                        f"    → Linked to inventory: {inventory_item.name}"
                    ))
            else:
                self.stdout.write(f"  → Already exists: {ingredient.name}")

    def seed_mixes(self, admin_user):
        """Seed 3 mixes (recipes) with ingredients"""
        self.stdout.write('\n📋 Seeding Mixes (Recipes)...')
        
        # Get products
        try:
            bread = Product.objects.get(name='Bread')
            kdf = Product.objects.get(name='KDF')
            scones = Product.objects.get(name='Scones')
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR('  ✗ Products not found. Run seed_products first.'))
            return
        
        # Get ingredients
        try:
            flour = Ingredient.objects.get(name='Wheat Flour')
            sugar = Ingredient.objects.get(name='Sugar')
            cooking_fat = Ingredient.objects.get(name='Cooking Fat')
            cooking_oil = Ingredient.objects.get(name='Cooking Oil')
            yeast_standard = Ingredient.objects.get(name='Yeast (Standard)')
            yeast_2in1 = Ingredient.objects.get(name='Yeast (2-in-1)')
            bread_improver = Ingredient.objects.get(name='Bread Improver')
            salt = Ingredient.objects.get(name='Salt')
            calcium = Ingredient.objects.get(name='Calcium')
        except Ingredient.DoesNotExist:
            self.stdout.write(self.style.ERROR('  ✗ Ingredients not found. Run seed_ingredients first.'))
            return
        
        # Mix 1: Bread
        bread_mix, created = Mix.objects.get_or_create(
            product=bread,
            name='Mix 1',
            version=1,
            defaults={
                'expected_packets': 132,
                'notes': 'Standard bread recipe',
                'created_by': admin_user,
                'updated_by': admin_user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {bread_mix}'))
            # Add ingredients
            bread_ingredients = [
                (flour, Decimal('36.000'), 'kg'),
                (sugar, Decimal('4.500'), 'kg'),
                (bread_improver, Decimal('60.000'), 'g'),
                (salt, Decimal('280.000'), 'g'),
                (calcium, Decimal('70.000'), 'g'),
                (yeast_standard, Decimal('200.000'), 'g'),
                (cooking_fat, Decimal('2.800'), 'kg'),
            ]
            for ingredient, quantity, unit in bread_ingredients:
                MixIngredient.objects.get_or_create(
                    mix=bread_mix,
                    ingredient=ingredient,
                    defaults={
                        'quantity': quantity,
                        'unit': unit,
                        'added_by': admin_user
                    }
                )
            self.stdout.write(f'    → Added {len(bread_ingredients)} ingredients')
        else:
            self.stdout.write(f'  → Already exists: {bread_mix}')
        
        # Mix 2: KDF
        kdf_mix, created = Mix.objects.get_or_create(
            product=kdf,
            name='Mix 1',
            version=1,
            defaults={
                'expected_packets': 107,
                'notes': 'Standard KDF recipe (hand-cut, variable output)',
                'created_by': admin_user,
                'updated_by': admin_user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {kdf_mix}'))
            # Add ingredients
            kdf_ingredients = [
                (flour, Decimal('50.000'), 'kg'),
                (sugar, Decimal('2.500'), 'kg'),
                (yeast_2in1, Decimal('160.000'), 'g'),
                (salt, Decimal('300.000'), 'g'),
                (calcium, Decimal('60.000'), 'g'),
                (cooking_fat, Decimal('1.500'), 'kg'),
                (cooking_oil, Decimal('7.500'), 'l'),
            ]
            for ingredient, quantity, unit in kdf_ingredients:
                MixIngredient.objects.get_or_create(
                    mix=kdf_mix,
                    ingredient=ingredient,
                    defaults={
                        'quantity': quantity,
                        'unit': unit,
                        'added_by': admin_user
                    }
                )
            self.stdout.write(f'    → Added {len(kdf_ingredients)} ingredients')
        else:
            self.stdout.write(f'  → Already exists: {kdf_mix}')
        
        # Mix 3: Scones
        scones_mix, created = Mix.objects.get_or_create(
            product=scones,
            name='Mix 1',
            version=1,
            defaults={
                'expected_packets': 102,
                'notes': 'Standard scones recipe',
                'created_by': admin_user,
                'updated_by': admin_user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {scones_mix}'))
            # Add ingredients
            scones_ingredients = [
                (flour, Decimal('26.000'), 'kg'),
                (sugar, Decimal('3.800'), 'kg'),
                (yeast_standard, Decimal('190.000'), 'g'),
                (salt, Decimal('280.000'), 'g'),
                (calcium, Decimal('50.000'), 'g'),
                (cooking_fat, Decimal('2.300'), 'kg'),
                (bread_improver, Decimal('50.000'), 'g'),
            ]
            for ingredient, quantity, unit in scones_ingredients:
                MixIngredient.objects.get_or_create(
                    mix=scones_mix,
                    ingredient=ingredient,
                    defaults={
                        'quantity': quantity,
                        'unit': unit,
                        'added_by': admin_user
                    }
                )
            self.stdout.write(f'    → Added {len(scones_ingredients)} ingredients')
        else:
            self.stdout.write(f'  → Already exists: {scones_mix}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Total Mixes: {Mix.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Total Mix Ingredients: {MixIngredient.objects.count()}'))
