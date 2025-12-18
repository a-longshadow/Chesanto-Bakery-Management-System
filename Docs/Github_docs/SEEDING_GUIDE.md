# Data Seeding Guide - Chesanto Bakery Management System

**Purpose:** Standardized process for seeding initial data across all apps  
**Created:** October 27, 2025  
**Status:** ✅ Production-Ready Pattern

---

## 📋 Overview

This guide documents the **idempotent seeding pattern** used in the Chesanto Bakery system. All seeding commands can be run multiple times safely without creating duplicates.

### Benefits
- ✅ Consistent data structure across environments (dev, staging, production)
- ✅ Fast deployment (seed data in seconds)
- ✅ Version controlled (seed data in code, not SQL dumps)
- ✅ Idempotent (safe to run multiple times)
- ✅ Traceable (all data sources documented)

---

## 🏗️ Seeding Architecture

### File Structure Pattern
```
apps/
  <app_name>/
    management/
      __init__.py
      commands/
        seed_<app_name>.py    # Main seeding command
```

### Command Pattern
```python
"""
Django Management Command: Seed <App> Data
Seeds <description of data>
Based on MILESTONE_2.md specifications
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.<app_name>.models import Model1, Model2
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed <app> data: <list what gets seeded>'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Starting <App> Data Seeding ===\n'))
        
        # Get admin user for created_by fields
        admin_user = User.objects.filter(role='SUPERADMIN').first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        # Step 1: Seed Category/Lookup Data
        self.seed_categories(admin_user)
        
        # Step 2: Seed Main Data
        self.seed_main_data(admin_user)
        
        # Step 3: Seed Related Data
        self.seed_related_data(admin_user)
        
        self.stdout.write(self.style.SUCCESS('\n=== <App> Data Seeding Complete! ===\n'))

    def seed_categories(self, admin_user):
        """Seed lookup/category data"""
        self.stdout.write('\n📁 Seeding Categories...')
        
        categories = [
            {'name': 'Category 1', 'code': 'CAT1'},
            # ... more categories
        ]
        
        for cat_data in categories:
            category, created = Model1.objects.get_or_create(
                code=cat_data['code'],  # Use unique field
                defaults={
                    'name': cat_data['name'],
                    'created_by': admin_user
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created: {category.name}'))
            else:
                self.stdout.write(f'  → Already exists: {category.name}')
```

---

## 📦 Implementation Examples

### Example 1: Inventory App Seeding

**File:** `apps/inventory/management/commands/seed_inventory.py`

**Command:**
```bash
python manage.py seed_inventory
```

**What it seeds:**
1. ✅ 5 Expense Categories (RAW_MATERIALS, PACKAGING, FUEL_ENERGY, CONSUMABLES, OTHER)
2. ✅ 6 Unit Conversions (bag→kg, jerycan→L, kg→g, l→ml, packet→g, dozen→pcs)
3. ✅ 20+ Inventory Items with realistic stock levels

**Key Features:**
- Uses `get_or_create()` with unique fields (code, name)
- Auto-calculates `cost_per_recipe_unit` on save
- Sets default stock levels and reorder levels
- Links items to categories via FK

**Sample Output:**
```
=== Starting Inventory Data Seeding ===

📁 Seeding Expense Categories...
  ✓ Created: Raw Materials
  ✓ Created: Packaging
  → Already exists: Fuel & Energy

📐 Seeding Unit Conversions...
  ✓ Created: 1 bag = 50.000 kg
  → Already exists: 1 jerycan = 20.000 l

📦 Seeding Inventory Items...
  ✓ Created: Wheat Flour (500.000 kg, KES 73.00/kg)
  ✓ Created: Sugar (100.000 kg, KES 144.00/kg)

✓ Total Inventory Items: 20

=== Inventory Data Seeding Complete! ===
```

**Source Code Reference:** [See Full Code](#inventory-seeding-code)

---

### Example 2: Products App Seeding

**File:** `apps/products/management/commands/seed_products.py`

**Command:**
```bash
python manage.py seed_products
```

**What it seeds:**
1. ✅ 3 Products (Bread, KDF, Scones)
2. ✅ 1 Sub-product (Bread Rejects)
3. ✅ 10 Ingredients
4. ✅ 3 Mixes with 21 total MixIngredients

**Key Features:**
- Products with variable output flags
- Sub-product support
- Mix versioning (version=1)
- Nested creation (Mix → MixIngredients)

**Sample Output:**
```
=== Starting Products Data Seeding ===

🍞 Seeding Products...
  ✓ Created: Bread (KES 60.00/loaf)
    → Sub-product: Bread Rejects (KES 50.00/loaf)
  ✓ Created: KDF (KES 100.00/packet)

🥖 Seeding Ingredients...
  ✓ Created: Wheat Flour (kg)
  ✓ Created: Sugar (kg)

📋 Seeding Mixes (Recipes)...
  ✓ Created: Bread - Mix 1 (v1)
    → Added 7 ingredients
  ✓ Created: KDF - Mix 1 (v1)
    → Added 7 ingredients

✓ Total Mixes: 3
✓ Total Mix Ingredients: 21

=== Products Data Seeding Complete! ===
```

**Source Code Reference:** [See Full Code](#products-seeding-code)

---

## 🚀 Production Deployment Process

### Step 1: Pre-Deployment Checklist
```bash
# Verify all migrations are created
python manage.py makemigrations --check --dry-run

# Verify no conflicts
python manage.py check

# Test seeding locally first
python manage.py seed_inventory
python manage.py seed_products
```

### Step 2: Railway Deployment

**Add to `railway.json`:**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python manage.py migrate && python manage.py seed_inventory && python manage.py seed_products && gunicorn config.wsgi:application",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Or create a deploy script:**

**File:** `scripts/deploy_seed.sh`
```bash
#!/bin/bash
# Deployment seeding script

echo "🚀 Starting deployment with data seeding..."

# Run migrations
echo "📦 Running migrations..."
python manage.py migrate --noinput

# Seed data in order
echo "🌱 Seeding inventory data..."
python manage.py seed_inventory

echo "🌱 Seeding products data..."
python manage.py seed_products

# Future apps
# echo "🌱 Seeding production data..."
# python manage.py seed_production

# echo "🌱 Seeding sales data..."
# python manage.py seed_sales

echo "✅ Deployment seeding complete!"
```

Make executable:
```bash
chmod +x scripts/deploy_seed.sh
```

### Step 3: Verify Deployment
```bash
# SSH into Railway (if needed)
railway run python manage.py shell

# Verify data
>>> from apps.inventory.models import InventoryItem
>>> InventoryItem.objects.count()
20

>>> from apps.products.models import Product, Mix
>>> Product.objects.count()
3
>>> Mix.objects.count()
3
```

---

## 📝 Seeding Best Practices

### 1. Idempotency Pattern
```python
# ✅ GOOD: Uses get_or_create with unique field
category, created = ExpenseCategory.objects.get_or_create(
    code='RAW_MATERIALS',  # Unique field
    defaults={
        'name': 'Raw Materials',
        'description': '...',
    }
)

# ❌ BAD: Always creates, causes duplicates
category = ExpenseCategory.objects.create(
    name='Raw Materials',
    code='RAW_MATERIALS'
)
```

### 2. Dependency Order
```python
# Seed in dependency order:
# 1. Lookup/Category data (no FKs)
# 2. Main data (depends on categories)
# 3. Related data (depends on main data)

# Example:
self.seed_categories(admin_user)      # ExpenseCategory
self.seed_items(admin_user)           # InventoryItem (FK to ExpenseCategory)
self.seed_purchases(admin_user)       # Purchase (FK to InventoryItem)
```

### 3. User Tracking
```python
# Always set created_by for audit trail
admin_user = User.objects.filter(role='SUPERADMIN').first()
if not admin_user:
    admin_user = User.objects.filter(is_superuser=True).first()

# Use in defaults
category, created = ExpenseCategory.objects.get_or_create(
    code='RAW_MATERIALS',
    defaults={'created_by': admin_user}
)
```

### 4. Decimal Precision
```python
from decimal import Decimal

# ✅ GOOD: Use Decimal for currency/measurements
cost_per_purchase_unit=Decimal('3650.00')  # KES
conversion_factor=Decimal('50.000')        # kg

# ❌ BAD: Floats cause precision issues
cost_per_purchase_unit=3650.0  # May lose precision
```

### 5. Data Source Documentation
```python
# Document where data comes from
"""
Seed inventory items from MILESTONE_2.md
- Wheat Flour: Line 149 (36 kg @ KES 73/kg)
- Sugar: Line 149 (4.5 kg @ KES 144/kg)
- See excel_digest/ for full item list
"""
```

### 6. Error Handling
```python
try:
    category = ExpenseCategory.objects.get(code='RAW_MATERIALS')
except ExpenseCategory.DoesNotExist:
    self.stdout.write(self.style.ERROR('  ✗ Category not found'))
    return  # Exit gracefully
```

### 7. Output Formatting
```python
# Use colored output for clarity
self.stdout.write(self.style.SUCCESS('  ✓ Created: Item'))
self.stdout.write(self.style.WARNING('  ⚠ Warning: Issue'))
self.stdout.write(self.style.ERROR('  ✗ Error: Failed'))
self.stdout.write('  → Already exists: Item')  # Plain text for skipped
```

---

## 🔄 Future Apps Seeding Roadmap

### Phase 2: Production & Sales Apps

**`seed_production.py`** (Week 3)
```python
# To seed:
# - 3 ProductionBatch examples (one per product)
# - 5 DailyProduction records (past 5 days)
# - 10 IndirectCost records (diesel, firewood, electricity)

python manage.py seed_production
```

**`seed_sales.py`** (Week 4)
```python
# To seed:
# - 5 Salespeople (Okiya Depot, Suna, Gongo, Nambale, Butula)
# - 10 Dispatch records (past 10 days)
# - 10 SalesReturn records
# - Commission calculations

python manage.py seed_sales
```

### Phase 3: Reports & Analytics Apps

**`seed_reports.py`** (Week 5)
```python
# To seed:
# - 30 DailyReport records (past 30 days)
# - 4 WeeklyReport records
# - 1 MonthlyReport record

python manage.py seed_reports
```

**Note:** Analytics app uses live data (no seeding needed)

### Phase 4: Payroll App

**`seed_payroll.py`** (Week 7)
```python
# To seed:
# - 20+ Employee records
# - 1 MonthlyPayroll (September 2025)
# - 12 CasualLabor records (156 days, 12 workers)

python manage.py seed_payroll
```

---

## 🎯 Master Seeding Command

**Create a master command to seed all apps:**

**File:** `apps/core/management/commands/seed_all.py`
```python
"""
Master Seeding Command
Seeds all apps in correct dependency order
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Seed all apps with initial data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip seeding if data already exists',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🌱 MASTER SEEDING: All Apps\n'))
        
        # Check if data exists
        if options['skip_existing']:
            from apps.inventory.models import InventoryItem
            from apps.products.models import Product
            
            if InventoryItem.objects.exists() and Product.objects.exists():
                self.stdout.write(self.style.WARNING('⚠️  Data already exists. Skipping seeding.'))
                return
        
        # Seed in dependency order
        commands = [
            ('seed_inventory', 'Inventory'),
            ('seed_products', 'Products'),
            # Future:
            # ('seed_production', 'Production'),
            # ('seed_sales', 'Sales'),
            # ('seed_payroll', 'Payroll'),
        ]
        
        for command, name in commands:
            self.stdout.write(f'\n▶️  Seeding {name}...')
            try:
                call_command(command)
                self.stdout.write(self.style.SUCCESS(f'✅ {name} seeded successfully'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ {name} seeding failed: {str(e)}'))
                # Continue with other commands or exit based on requirements
        
        self.stdout.write(self.style.SUCCESS('\n✅ MASTER SEEDING COMPLETE!\n'))
```

**Usage:**
```bash
# Seed all apps
python manage.py seed_all

# Skip if data exists (production safety)
python manage.py seed_all --skip-existing
```

---

## 📊 Seeding Status Tracker

| App | Command | Status | Records | Dependencies | Phase |
|-----|---------|--------|---------|--------------|-------|
| **Inventory** | `seed_inventory` | ✅ Complete | 5 categories, 6 conversions, 20 items | None | 1 |
| **Products** | `seed_products` | ✅ Complete | 3 products, 10 ingredients, 3 mixes | None | 1 |
| **Production** | `seed_production` | ⏳ Pending | TBD | Inventory, Products | 2 |
| **Sales** | `seed_sales` | ⏳ Pending | TBD | Products | 2 |
| **Reports** | `seed_reports` | ⏳ Pending | TBD | Production, Sales | 3 |
| **Payroll** | `seed_payroll` | ⏳ Pending | TBD | None | 4 |

---

## 🧪 Testing Seeding Commands

### Local Testing
```bash
# Test individual commands
python manage.py seed_inventory
python manage.py seed_products

# Test idempotency (run twice)
python manage.py seed_inventory
python manage.py seed_inventory  # Should show "Already exists"

# Test master command
python manage.py seed_all
```

### Verify Data Integrity
```bash
python manage.py shell

# Check counts
>>> from apps.inventory.models import *
>>> ExpenseCategory.objects.count()  # Should be 5
>>> UnitConversion.objects.count()   # Should be 6
>>> InventoryItem.objects.count()    # Should be 20

>>> from apps.products.models import *
>>> Product.objects.count()          # Should be 3
>>> Ingredient.objects.count()       # Should be 10
>>> Mix.objects.count()              # Should be 3
>>> MixIngredient.objects.count()    # Should be 21

# Check specific data
>>> flour = InventoryItem.objects.get(name='Wheat Flour')
>>> flour.cost_per_recipe_unit  # Should be 73.00 (auto-calculated)
>>> flour.current_stock         # Should be 500.000 kg
```

---

## 📚 Appendix: Full Source Code

### Inventory Seeding Code
<a name="inventory-seeding-code"></a>

**File:** `apps/inventory/management/commands/seed_inventory.py`

See file at: `/Users/joe/Documents/Chesanto-Bakery-Management-System/apps/inventory/management/commands/seed_inventory.py`

**Key Data Points:**
- 5 categories (RAW_MATERIALS, PACKAGING, FUEL_ENERGY, CONSUMABLES, OTHER)
- 6 conversions (bag→kg: 50, jerycan→L: 20, kg→g: 1000, l→ml: 1000, packet→g: 450, dozen→pcs: 12)
- 20 items with costs from MILESTONE_2.md

### Products Seeding Code
<a name="products-seeding-code"></a>

**File:** `apps/products/management/commands/seed_products.py`

See file at: `/Users/joe/Documents/Chesanto-Bakery-Management-System/apps/products/management/commands/seed_products.py`

**Key Data Points:**
- Bread: KES 60/loaf, 132 baseline, 7 ingredients
- KDF: KES 100/packet, 107 variable (98-107), 7 ingredients  
- Scones: KES 50/packet, 102 baseline, 7 ingredients
- All ingredient quantities from MILESTONE_2.md lines 140-210

---

## 🔗 Related Documentation

- **MILESTONE_2.md** - Source of truth for all data values
- **IMPLEMENTATION_LOG.md** - Implementation progress tracking
- **PHASE_1_IMPLEMENTATION_LOG.md** - Detailed Phase 1 notes
- **STEP-BY-STEP IMPLEMENTATION STRATEGY** - Overall strategy

---

**Last Updated:** October 27, 2025  
**Status:** ✅ Production Ready  
**Next Review:** After Phase 2 seeding commands created
