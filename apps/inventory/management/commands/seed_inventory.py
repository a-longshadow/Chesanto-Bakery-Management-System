"""
Django Management Command: Seed Inventory Data
Seeds expense categories, inventory items, and unit conversions
Based on MILESTONE_2.md specifications
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.inventory.models import ExpenseCategory, InventoryItem, UnitConversion
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed inventory data: expense categories, items, and unit conversions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Starting Inventory Data Seeding ===\n'))
        
        # Get or create a superuser for created_by fields
        admin_user = User.objects.filter(role='SUPERADMIN').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        # Step 1: Seed Expense Categories
        self.seed_expense_categories(admin_user)
        
        # Step 2: Seed Unit Conversions
        self.seed_unit_conversions()
        
        # Step 3: Seed Inventory Items
        self.seed_inventory_items(admin_user)
        
        self.stdout.write(self.style.SUCCESS('\n=== Inventory Data Seeding Complete! ===\n'))

    def seed_expense_categories(self, admin_user):
        """Seed 5 expense categories"""
        self.stdout.write('\n📁 Seeding Expense Categories...')
        
        categories = [
            {
                'name': 'Raw Materials',
                'code': 'RAW_MATERIALS',
                'description': 'Direct ingredients for production (flour, sugar, yeast, etc.)'
            },
            {
                'name': 'Packaging',
                'code': 'PACKAGING',
                'description': 'Packaging materials (bags, papers, etc.)'
            },
            {
                'name': 'Fuel & Energy',
                'code': 'FUEL_ENERGY',
                'description': 'Fuel, diesel, firewood, electricity'
            },
            {
                'name': 'Consumables',
                'code': 'CONSUMABLES',
                'description': 'Cleaning supplies, utensils, misc consumables'
            },
            {
                'name': 'Other',
                'code': 'OTHER',
                'description': 'Other miscellaneous expenses'
            },
        ]
        
        for cat_data in categories:
            category, created = ExpenseCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description'],
                    'created_by': admin_user
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {category.name}'))
            else:
                self.stdout.write(f'  → Already exists: {category.name}')

    def seed_unit_conversions(self):
        """Seed 6 unit conversions"""
        self.stdout.write('\n📐 Seeding Unit Conversions...')
        
        conversions = [
            {'from_unit': 'bag', 'to_unit': 'kg', 'factor': Decimal('50.000'), 'notes': '1 bag (flour) = 50 kg'},
            {'from_unit': 'jerycan', 'to_unit': 'l', 'factor': Decimal('20.000'), 'notes': '1 jerycan (oil) = 20 L'},
            {'from_unit': 'kg', 'to_unit': 'g', 'factor': Decimal('1000.000'), 'notes': '1 kg = 1000 g'},
            {'from_unit': 'l', 'to_unit': 'ml', 'factor': Decimal('1000.000'), 'notes': '1 L = 1000 mL'},
            {'from_unit': 'packet', 'to_unit': 'g', 'factor': Decimal('450.000'), 'notes': '1 packet (yeast) = 450 g'},
            {'from_unit': 'dozen', 'to_unit': 'pcs', 'factor': Decimal('12.000'), 'notes': '1 dozen = 12 pieces'},
        ]
        
        for conv_data in conversions:
            conversion, created = UnitConversion.objects.get_or_create(
                from_unit=conv_data['from_unit'],
                to_unit=conv_data['to_unit'],
                defaults={
                    'factor': conv_data['factor'],
                    'notes': conv_data['notes']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created: {conversion}"))
            else:
                self.stdout.write(f"  → Already exists: {conversion}")

    def seed_inventory_items(self, admin_user):
        """Seed 37+ inventory items from MILESTONE_2.md"""
        self.stdout.write('\n📦 Seeding Inventory Items...')
        
        # Get categories
        raw_materials = ExpenseCategory.objects.get(code='RAW_MATERIALS')
        packaging = ExpenseCategory.objects.get(code='PACKAGING')
        fuel_energy = ExpenseCategory.objects.get(code='FUEL_ENERGY')
        consumables = ExpenseCategory.objects.get(code='CONSUMABLES')
        
        items = [
            # RAW MATERIALS
            {
                'name': 'Wheat Flour',
                'category': raw_materials,
                'purchase_unit': 'bag',
                'recipe_unit': 'kg',
                'conversion_factor': Decimal('50.000'),
                'current_stock': Decimal('500.000'),  # 500 kg
                'reorder_level': Decimal('350.000'),  # 7 days supply
                'cost_per_purchase_unit': Decimal('3650.00'),  # KES 3,650 per 50kg bag
                'description': '50kg bags of wheat flour for bread production'
            },
            {
                'name': 'Sugar',
                'category': raw_materials,
                'purchase_unit': 'kg',
                'recipe_unit': 'kg',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('100.000'),
                'reorder_level': Decimal('70.000'),
                'cost_per_purchase_unit': Decimal('144.00'),  # KES 144/kg
                'description': 'Granulated white sugar'
            },
            {
                'name': 'Cooking Fat',
                'category': raw_materials,
                'purchase_unit': 'kg',
                'recipe_unit': 'kg',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('50.000'),
                'reorder_level': Decimal('30.000'),
                'cost_per_purchase_unit': Decimal('274.00'),  # KES 274/kg
                'description': 'Vegetable cooking fat'
            },
            {
                'name': 'Cooking Oil',
                'category': raw_materials,
                'purchase_unit': 'jerycan',
                'recipe_unit': 'l',
                'conversion_factor': Decimal('20.000'),  # 20L per jerycan
                'current_stock': Decimal('80.000'),  # 80 liters
                'reorder_level': Decimal('50.000'),
                'cost_per_purchase_unit': Decimal('4740.00'),  # KES 4,740 per 20L jerycan
                'description': '20L jerycans of cooking oil'
            },
            {
                'name': 'Yeast (Standard)',
                'category': raw_materials,
                'purchase_unit': 'packet',
                'recipe_unit': 'g',
                'conversion_factor': Decimal('450.000'),  # 450g per packet
                'current_stock': Decimal('2700.000'),  # 2700g = 6 packets
                'reorder_level': Decimal('1350.000'),  # 3 packets
                'cost_per_purchase_unit': Decimal('270.00'),  # KES 270 per 450g packet
                'description': '450g packets of standard yeast'
            },
            {
                'name': 'Yeast (2-in-1)',
                'category': raw_materials,
                'purchase_unit': 'packet',
                'recipe_unit': 'g',
                'conversion_factor': Decimal('450.000'),
                'current_stock': Decimal('1800.000'),  # 4 packets
                'reorder_level': Decimal('900.000'),  # 2 packets
                'cost_per_purchase_unit': Decimal('405.00'),  # KES 405 per 450g packet
                'description': '450g packets of 2-in-1 yeast (premium)'
            },
            {
                'name': 'Bread Improver',
                'category': raw_materials,
                'purchase_unit': 'kg',
                'recipe_unit': 'g',
                'conversion_factor': Decimal('1000.000'),
                'current_stock': Decimal('5000.000'),  # 5 kg
                'reorder_level': Decimal('2000.000'),
                'cost_per_purchase_unit': Decimal('600.00'),  # KES 600/kg
                'description': 'Bread improver additive'
            },
            {
                'name': 'Salt',
                'category': raw_materials,
                'purchase_unit': 'kg',
                'recipe_unit': 'g',
                'conversion_factor': Decimal('1000.000'),
                'current_stock': Decimal('20000.000'),  # 20 kg
                'reorder_level': Decimal('10000.000'),
                'cost_per_purchase_unit': Decimal('35.00'),  # KES 35/kg
                'description': 'Table salt for recipes'
            },
            {
                'name': 'Calcium',
                'category': raw_materials,
                'purchase_unit': 'kg',
                'recipe_unit': 'g',
                'conversion_factor': Decimal('1000.000'),
                'current_stock': Decimal('3000.000'),  # 3 kg
                'reorder_level': Decimal('1500.000'),
                'cost_per_purchase_unit': Decimal('340.00'),  # KES 340/kg
                'description': 'Calcium supplement for dough'
            },
            {
                'name': 'Food Colour',
                'category': raw_materials,
                'purchase_unit': 'ml',
                'recipe_unit': 'ml',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('500.000'),
                'reorder_level': Decimal('200.000'),
                'cost_per_purchase_unit': Decimal('5.00'),  # KES 5/ml
                'description': 'Food coloring for products'
            },
            
            # PACKAGING
            {
                'name': 'Packaging Bags (Bread)',
                'category': packaging,
                'purchase_unit': 'pcs',
                'recipe_unit': 'pcs',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('5000.000'),
                'reorder_level': Decimal('2000.000'),
                'cost_per_purchase_unit': Decimal('3.30'),  # KES 3.3 per bag
                'description': 'Plastic bags for packaging bread loaves'
            },
            {
                'name': 'Packaging Bags (KDF)',
                'category': packaging,
                'purchase_unit': 'pcs',
                'recipe_unit': 'pcs',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('3000.000'),
                'reorder_level': Decimal('1500.000'),
                'cost_per_purchase_unit': Decimal('3.30'),
                'description': 'Plastic bags for packaging KDF packets'
            },
            {
                'name': 'Packaging Bags (Scones)',
                'category': packaging,
                'purchase_unit': 'pcs',
                'recipe_unit': 'pcs',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('2000.000'),
                'reorder_level': Decimal('1000.000'),
                'cost_per_purchase_unit': Decimal('3.30'),
                'description': 'Plastic bags for packaging scones packets'
            },
            {
                'name': 'Packaging Papers',
                'category': packaging,
                'purchase_unit': 'pcs',
                'recipe_unit': 'pcs',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('1000.000'),
                'reorder_level': Decimal('500.000'),
                'cost_per_purchase_unit': Decimal('2.00'),
                'description': 'Wrapping papers for products'
            },
            
            # FUEL & ENERGY
            {
                'name': 'Diesel',
                'category': fuel_energy,
                'purchase_unit': 'l',
                'recipe_unit': 'l',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('100.000'),
                'reorder_level': Decimal('50.000'),
                'cost_per_purchase_unit': Decimal('150.00'),  # KES 150/L (estimated)
                'description': 'Diesel fuel for generator/vehicles'
            },
            {
                'name': 'Firewood',
                'category': fuel_energy,
                'purchase_unit': 'kg',
                'recipe_unit': 'kg',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('500.000'),
                'reorder_level': Decimal('200.000'),
                'cost_per_purchase_unit': Decimal('15.00'),  # KES 15/kg
                'description': 'Firewood for oven heating'
            },
            {
                'name': 'Charcoal',
                'category': fuel_energy,
                'purchase_unit': 'bag',
                'recipe_unit': 'kg',
                'conversion_factor': Decimal('50.000'),  # 50kg per bag
                'current_stock': Decimal('150.000'),
                'reorder_level': Decimal('100.000'),
                'cost_per_purchase_unit': Decimal('2000.00'),  # KES 2,000 per 50kg bag
                'description': 'Charcoal for heating'
            },
            
            # CONSUMABLES
            {
                'name': 'Cleaning Detergent',
                'category': consumables,
                'purchase_unit': 'kg',
                'recipe_unit': 'kg',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('10.000'),
                'reorder_level': Decimal('5.000'),
                'cost_per_purchase_unit': Decimal('150.00'),
                'description': 'Cleaning detergent for equipment'
            },
            {
                'name': 'Baking Trays',
                'category': consumables,
                'purchase_unit': 'pcs',
                'recipe_unit': 'pcs',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('50.000'),
                'reorder_level': Decimal('20.000'),
                'cost_per_purchase_unit': Decimal('500.00'),
                'description': 'Metal baking trays (reusable)'
            },
            {
                'name': 'Mixing Bowls',
                'category': consumables,
                'purchase_unit': 'pcs',
                'recipe_unit': 'pcs',
                'conversion_factor': Decimal('1.000'),
                'current_stock': Decimal('20.000'),
                'reorder_level': Decimal('10.000'),
                'cost_per_purchase_unit': Decimal('300.00'),
                'description': 'Large mixing bowls for dough'
            },
        ]
        
        for item_data in items:
            item, created = InventoryItem.objects.get_or_create(
                name=item_data['name'],
                defaults={
                    'category': item_data['category'],
                    'purchase_unit': item_data['purchase_unit'],
                    'recipe_unit': item_data['recipe_unit'],
                    'conversion_factor': item_data['conversion_factor'],
                    'current_stock': item_data['current_stock'],
                    'reorder_level': item_data['reorder_level'],
                    'cost_per_purchase_unit': item_data['cost_per_purchase_unit'],
                    'description': item_data.get('description', ''),
                    'created_by': admin_user
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Created: {item.name} ({item.current_stock} {item.recipe_unit}, "
                    f"KES {item.cost_per_recipe_unit:.2f}/{item.recipe_unit})"
                ))
            else:
                self.stdout.write(f"  → Already exists: {item.name}")
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Total Inventory Items: {InventoryItem.objects.count()}'))
