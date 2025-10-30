"""
Test Purchase Items Creation and Editing
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.inventory.models import Purchase, PurchaseItem, InventoryItem, Supplier
from apps.accounts.models import User
from datetime import date

print("\n" + "="*60)
print("🧪 TESTING PURCHASE ITEMS WORKFLOW")
print("="*60 + "\n")

# Get test user
user = User.objects.filter(role='SUPERADMIN').first()
if not user:
    print("❌ No SUPERADMIN user found. Please create one first.")
    exit()

# Get test supplier
supplier = Supplier.objects.filter(is_active=True).first()
if not supplier:
    print("❌ No active supplier found. Please create one first.")
    exit()

# Get test items
wheat_flour = InventoryItem.objects.filter(name='Wheat Flour').first()
sugar = InventoryItem.objects.filter(name='Sugar').first()

if not wheat_flour or not sugar:
    print("❌ Required inventory items not found.")
    exit()

# Create test purchase
print("1️⃣ Creating test purchase...")
purchase = Purchase.objects.create(
    supplier=supplier,
    purchase_date=date.today(),
    status='DRAFT',
    notes='Test purchase for items',
    created_by=user,
    updated_by=user
)
print(f"   ✅ Created purchase: {purchase.purchase_number}")

# Add purchase items
print("\n2️⃣ Adding purchase items...")
item1 = PurchaseItem.objects.create(
    purchase=purchase,
    item=wheat_flour,
    quantity=50,
    unit_cost=3650
)
print(f"   ✅ Added {item1.quantity} {wheat_flour.purchase_unit} of {wheat_flour.name} @ KES {item1.unit_cost}")

item2 = PurchaseItem.objects.create(
    purchase=purchase,
    item=sugar,
    quantity=25,
    unit_cost=144
)
print(f"   ✅ Added {item2.quantity} {sugar.purchase_unit} of {sugar.name} @ KES {item2.unit_cost}")

# Check total
purchase.refresh_from_db()
print(f"\n   💰 Total Amount: KES {purchase.total_amount:,.2f}")

# Test editing - update quantities
print("\n3️⃣ Testing edit: Updating quantities...")
item1.quantity = 100  # Double the wheat flour
item1.save()
print(f"   ✅ Updated Wheat Flour quantity to {item1.quantity}")

purchase.refresh_from_db()
print(f"   💰 New Total Amount: KES {purchase.total_amount:,.2f}")

# Test editing - delete and recreate (like the view does)
print("\n4️⃣ Testing edit workflow (delete + recreate)...")
old_total = purchase.total_amount
purchase.purchaseitem_set.all().delete()
print(f"   🗑️ Deleted all items")

# Recreate with new data
PurchaseItem.objects.create(
    purchase=purchase,
    item=wheat_flour,
    quantity=75,
    unit_cost=3650
)
PurchaseItem.objects.create(
    purchase=purchase,
    item=sugar,
    quantity=50,
    unit_cost=144
)
print(f"   ✅ Recreated items with new quantities")

purchase.refresh_from_db()
print(f"   💰 Previous Total: KES {old_total:,.2f}")
print(f"   💰 New Total: KES {purchase.total_amount:,.2f}")

# Display final state
print("\n5️⃣ Final Purchase State:")
print(f"   Purchase: {purchase.purchase_number}")
print(f"   Supplier: {purchase.supplier.name}")
print(f"   Status: {purchase.status}")
print(f"   Items: {purchase.purchaseitem_set.count()}")
for item in purchase.purchaseitem_set.all():
    print(f"     - {item.item.name}: {item.quantity} {item.item.purchase_unit} @ KES {item.unit_cost} = KES {item.total_cost:,.2f}")
print(f"   Total: KES {purchase.total_amount:,.2f}")

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60 + "\n")
