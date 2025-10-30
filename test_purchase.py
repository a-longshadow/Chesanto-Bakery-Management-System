"""
Test script to manually create a purchase order and verify stock updates
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from datetime import date, timedelta
from apps.inventory.models import Supplier, InventoryItem, Purchase, PurchaseItem
from apps.accounts.models import User

# Get or create test user
user = User.objects.filter(role='SUPERADMIN').first()

# Get supplier
supplier = Supplier.objects.filter(name__icontains='Pembe').first()
if not supplier:
    print("❌ No supplier found. Run: python manage.py seed_suppliers")
    exit(1)

print(f"\n✅ Using supplier: {supplier.name}")

# Get some inventory items
flour = InventoryItem.objects.filter(name__icontains='Wheat Flour').first()
sugar = InventoryItem.objects.filter(name__icontains='Sugar').first()
yeast = InventoryItem.objects.filter(name__icontains='Yeast').first()

if not flour or not sugar or not yeast:
    print("❌ Inventory items not found. Check your database.")
    exit(1)

print(f"\n📦 Stock BEFORE purchase:")
print(f"  {flour.name}: {flour.current_stock:.2f} {flour.recipe_unit}")
print(f"  {sugar.name}: {sugar.current_stock:.2f} {sugar.recipe_unit}")
print(f"  {yeast.name}: {yeast.current_stock:.2f} {yeast.recipe_unit}")

# Create purchase order
purchase = Purchase.objects.create(
    purchase_number=f"PUR-TEST-{date.today().strftime('%Y%m%d')}",
    supplier=supplier,
    purchase_date=date.today(),
    expected_delivery_date=date.today() + timedelta(days=2),
    status='ORDERED',
    created_by=user,
    updated_by=user
)

print(f"\n✅ Created purchase: {purchase.purchase_number}")

# Add purchase items
PurchaseItem.objects.create(
    purchase=purchase,
    item=flour,
    quantity=100,  # 100 kg
    unit_cost=73.00
)

PurchaseItem.objects.create(
    purchase=purchase,
    item=sugar,
    quantity=50,  # 50 kg
    unit_cost=144.00
)

PurchaseItem.objects.create(
    purchase=purchase,
    item=yeast,
    quantity=5,  # 5 kg
    unit_cost=600.00
)

print(f"✅ Added 3 items to purchase")
print(f"   Total: KES {purchase.total_amount:,.2f}")

# Mark as RECEIVED to trigger stock update
print(f"\n🔄 Marking purchase as RECEIVED...")
purchase.status = 'RECEIVED'
purchase.actual_delivery_date = date.today()
purchase.save()

# Refresh items from database
flour.refresh_from_db()
sugar.refresh_from_db()
yeast.refresh_from_db()

print(f"\n📦 Stock AFTER purchase:")
print(f"  {flour.name}: {flour.current_stock:.2f} {flour.recipe_unit}")
print(f"  {sugar.name}: {sugar.current_stock:.2f} {sugar.recipe_unit}")
print(f"  {yeast.name}: {yeast.current_stock:.2f} {yeast.recipe_unit}")

print(f"\n✅ Purchase order test complete!")
print(f"\nYou can now:")
print(f"1. Go to Admin → Inventory → Stock Movements to see audit trail")
print(f"2. Create production batches with the new stock")
print(f"3. Delete this test purchase if needed: Purchase #{purchase.id}")
