# 🔧 FOUNDATION REFACTORING PLAN
**Date:** November 26, 2025  
**Scope:** Fix transactional flaws in Production, Inventory, and Products apps + Sales integration

**Objective:** Create solid foundation for:
1. Accuracy and Accountability in downstream apps (analytics, reports)
2. Sales app integrity (no orphaned transactions)
3. Data ownership with authenticated cross-app communication

**Approach:** Atomic utility functions with validation, row locking, and standardized responses

---

## 🎯 CORE ARCHITECTURAL PRINCIPLES

### ✅ **Foundational Rules:**

1. **App Ownership Principle** - Each app owns its data (✓ Correct)
2. **Atomic Transactions** - ALL foundation transactions use @transaction.atomic (✓ Essential)
3. **Immutability Rules:**
   - **Products:** CREATE + UPDATE + DELETE allowed (editable recipes/prices)
   - **Production:** CREATE only (no updates/deletes after batch creation)
   - **Inventory:** CREATE only (no updates/deletes after purchase/adjustment)
   - **Sales:** CREATE only (no updates/deletes after dispatch/return)
   - **Exception:** Sales returns CAN update Production (product stock) and Inventory (crate stock)
4. **Real-time Tallies** - Update totals immediately (✓ Prevention-first UX)
5. **Cross-App Communication** - Only via authenticated utility functions

---

## 🔐 **CRITICAL: Authentication & Data Integrity**

### **Problem:** How does data owner authenticate external requests?

**Answer:** Validation layers + transaction boundaries + row locking

#### **1. Validation Before Write (Prevention-First)**
```python
# External app calls inventory utility
from apps.inventory.utils import deduct_ingredients_atomic

# Utility validates BEFORE any DB writes
@transaction.atomic
def deduct_ingredients_atomic(ingredients_list, requested_by_app):
    # Step 1: VALIDATE - no writes yet
    for ingredient in ingredients_list:
        item = InventoryItem.objects.select_for_update().get(id=ingredient['id'])
        
        if item.current_stock < ingredient['quantity']:
            return {
                'success': False,
                'errors': [f"Insufficient {item.name}: need {ingredient['quantity']}g, have {item.current_stock}g"],
                'message': 'Inventory check failed'
            }
    
    # Step 2: DEDUCT - only if all validations passed
    for ingredient in ingredients_list:
        item = InventoryItem.objects.select_for_update().get(id=ingredient['id'])
        item.current_stock -= ingredient['quantity']
        item.save()
    
    return {
        'success': True,
        'data': {'updated_items': len(ingredients_list)},
        'message': 'Ingredients deducted successfully'
    }
```

#### **2. Row Locking (Prevent Race Conditions)**
- **Problem:** Two production batches request same flour simultaneously
- **Solution:** `select_for_update()` locks row until transaction commits
```python
# Production Batch #1 requests 5000g flour
item = InventoryItem.objects.select_for_update().get(name='Flour')
# Row LOCKED - Batch #2 must wait

# Batch #1 deducts, saves, commits
item.current_stock -= 5000
item.save()
# Row UNLOCKED - Batch #2 can now proceed
```

#### **3. Transaction Boundaries (All-or-Nothing)**
```python
@transaction.atomic
def create_production_batch_atomic(mix_id, quantity):
    # Step 1: Get ingredients from inventory (cross-app call)
    result = inventory_utils.deduct_ingredients_atomic(ingredients)
    
    if not result['success']:
        # Inventory validation failed - transaction auto-rollbacks
        return result
    
    # Step 2: Create production record (only if inventory succeeded)
    batch = ProductionBatch.objects.create(...)
    
    # Step 3: Add products to stock
    product_stock, created = ProductStock.objects.get_or_create(product=batch.product)
    product_stock.current_stock += batch.actual_yield
    product_stock.save()
    
    # If ANY step fails, ENTIRE transaction rolls back (atomic)
    return {'success': True, 'data': {'batch_id': batch.id}}
```

### **Race Condition Prevention Strategy**

#### **Scenario 1: Concurrent Production Batches**
```
Time    Batch A (Bread)              Batch B (Scones)
----    -------------------          -------------------
10:00   Requests 5000g flour         
10:00   ✓ Locks flour row            
10:01                                 Requests 3000g flour
10:01                                 ⏳ WAITING (row locked)
10:02   ✓ Deducts 5000g              
10:02   ✓ Saves & unlocks            
10:03                                 ✓ Gets lock, checks stock
10:03                                 ✓ Deducts 3000g
```

#### **Scenario 2: Dispatch During Production**
```
Time    Production                   Sales Dispatch
----    -------------------          -------------------
14:00   Creates batch (132 bread)    
14:00   ✓ Locks ProductStock         
14:01                                 Requests 50 bread
14:01                                 ⏳ WAITING (row locked)
14:02   ✓ Adds 132 to stock          
14:02   ✓ Saves & unlocks            
14:03                                 ✓ Gets lock (182 available)
14:03                                 ✓ Deducts 50 (132 remain)
```

---

## 🛡️ **Data Integrity Guarantees**

### **1. No Orphaned Transactions**
- If Production fails to deduct ingredients → No batch created
- If Dispatch fails to deduct products → No dispatch created
- If Return fails to return crates → No return closure

### **2. No Negative Stock**
```python
# Validation BEFORE deduction
if item.current_stock < requested_quantity:
    raise InsufficientStockError  # Transaction rollback
```

### **3. No Race Conditions**
- `select_for_update()` on ALL stock-modifying queries
- Locks held until `transaction.atomic` commits
- Queued requests processed sequentially

### **4. Audit Trail**
```python
# Every utility logs the caller
@transaction.atomic
def deduct_ingredients_atomic(ingredients_list, requested_by_app, requested_by_user):
    # Log who requested what
    InventoryLog.objects.create(
        action='DEDUCT',
        requested_by_app=requested_by_app,  # 'production'
        requested_by_user=requested_by_user,  # User object
        items=ingredients_list,
        timestamp=timezone.now()
    )
    # Proceed with deduction...
```

---

## 🔒 **Utility Function Authentication Pattern**

### **Standard Signature:**
```python
def utility_function_atomic(
    data,                    # The actual data to process
    requested_by_app=None,   # Which app is calling? 'production', 'sales', etc.
    requested_by_user=None   # Which user triggered this? (from request.user)
):
    """
    All foundation utility functions follow this pattern:
    1. Validate inputs (data integrity)
    2. Check permissions (optional: role-based)
    3. Lock rows (prevent race conditions)
    4. Execute logic (all-or-nothing)
    5. Log action (audit trail)
    6. Return standardized response
    """
```

### **Example: Inventory → Production**
```python
# apps/production/views.py
@login_required
def create_batch_view(request):
    # View collects data, calls production utility
    result = production_utils.create_production_batch_atomic(
        mix_id=request.POST['mix_id'],
        requested_by_app='production',
        requested_by_user=request.user  # Pass user context
    )
    
    if result['success']:
        messages.success(request, result['message'])
    else:
        messages.error(request, '; '.join(result['errors']))

# apps/production/utils.py
@transaction.atomic
def create_production_batch_atomic(mix_id, requested_by_app, requested_by_user):
    # This utility calls inventory utility
    inventory_result = inventory_utils.deduct_ingredients_atomic(
        ingredients_list=mix.ingredients,
        requested_by_app='production',  # Identify caller
        requested_by_user=requested_by_user  # Pass through
    )
    
    # Inventory validates request and logs who made it
```

---

---

## 💡 **WEIGHTED AVERAGE COSTING: DETAILED FLOW**

### **How It Works Across All Three Apps**

#### **1. INVENTORY APP: Source of Truth for Current Costs**

**Storage:**
- `InventoryItem.weighted_avg_cost` = **LIVE current average cost per unit**
- `InventoryItem.updated_at` = **Timestamp of last cost change**
- `InventoryItem.updated_by` = **User who triggered the cost change (via purchase)**

**Calculation Trigger:** Every time a purchase is created

**Formula:**
```python
new_weighted_avg = (
    (current_stock × current_weighted_avg) + (purchase_qty × purchase_unit_price)
) / (current_stock + purchase_qty)
```

**Example Flow:**
```
BEFORE PURCHASE (Nov 20, 2025):
  Flour: 10.0000 kg @ KES 90.0000/kg = KES 900.00 total value
  
PURCHASE #1 (Nov 26, 2025 @ 8:30 AM):
  Buy: 50.0000 kg @ KES 80.0000/kg = KES 4,000.00
  
  Atomic Calculation:
    Old value: 10.0000 × 90.0000 = KES 900.00
    New value: 50.0000 × 80.0000 = KES 4,000.00
    Total: KES 4,900.00 / 60.0000 kg = KES 81.6667/kg
  
  Updated Fields:
    InventoryItem.current_stock = 60.0000 kg
    InventoryItem.weighted_avg_cost = 81.6667
    InventoryItem.current_value = 4,900.00
    InventoryItem.updated_at = 2025-11-26 08:30:15
    InventoryItem.updated_by = User #5 (Accountant)

PURCHASE #2 (Nov 28, 2025 @ 2:00 PM):
  Buy: 50.0000 kg @ KES 95.0000/kg = KES 4,750.00
  
  Atomic Calculation:
    Old value: 60.0000 × 81.6667 = KES 4,900.00
    New value: 50.0000 × 95.0000 = KES 4,750.00
    Total: KES 9,650.00 / 110.0000 kg = KES 87.7273/kg
  
  Updated Fields:
    InventoryItem.current_stock = 110.0000 kg
    InventoryItem.weighted_avg_cost = 87.7273
    InventoryItem.current_value = 9,650.00
    InventoryItem.updated_at = 2025-11-28 14:00:20
    InventoryItem.updated_by = User #5 (Accountant)
```

**Historical Tracking:**
- Each `Purchase` record is immutable (timestamped with `created_at`)
- Each `PurchaseItem` preserves the exact `unit_price` at purchase time
- Query purchase history to see price trends over time

---

#### **2. PRODUCTION APP: Captures Cost Snapshot at Batch Creation**

**Storage:**
- `ProductionBatch.total_cost` = **Sum of ingredient costs at batch creation time**
- `ProductionBatch.unit_cost` = **total_cost ÷ actual_yield**
- `ProductionBatch.created_at` = **Immutable timestamp**
- `ProductionBatch.produced_by` = **User who created the batch**

**Cost Calculation Logic:**
```python
@transaction.atomic
def create_production_batch_atomic(mix_id, actual_yield, requested_by_user):
    # Step 1: Get recipe ingredients
    mix = Mix.objects.get(id=mix_id)
    ingredients = mix.mixingredient_set.all()
    
    # Step 2: Calculate total cost using CURRENT weighted averages
    total_cost = Decimal('0.00')
    for ingredient in ingredients:
        item = InventoryItem.objects.get(id=ingredient.inventory_item_id)
        cost_for_this_ingredient = ingredient.quantity_required * item.weighted_avg_cost
        total_cost += cost_for_this_ingredient
    
    # Step 3: Deduct ingredients from inventory
    result = inventory_utils.deduct_ingredients_atomic(...)
    
    # Step 4: Create batch with FROZEN cost
    batch = ProductionBatch.objects.create(
        product=mix.product,
        mix=mix,
        expected_yield=mix.expected_yield,
        actual_yield=actual_yield,
        total_cost=total_cost,  # ← FROZEN at creation time
        unit_cost=total_cost / actual_yield,  # ← Cost per packet
        produced_by=requested_by_user,
        batch_date=date.today()
    )
    
    # Even if flour price changes tomorrow, this batch cost NEVER changes
    return {'success': True, 'data': {'batch_id': batch.id}}
```

**Example:**
```
Nov 26, 2025 @ 10:00 AM (Flour = KES 81.6667/kg):
  Production Batch #42:
    - Product: Bread
    - Mix: Bread Mix Standard
      → Flour: 5.0000 kg × KES 81.6667 = KES 408.33
      → Sugar: 0.5000 kg × KES 140.00 = KES 70.00
      → Yeast: 0.0500 kg × KES 300.00 = KES 15.00
      → Salt: 0.1000 kg × KES 50.00 = KES 5.00
      → Wrapper: 132 units × KES 2.00 = KES 264.00
    - Total Cost: KES 762.33
    - Actual Yield: 132 packets
    - Unit Cost: KES 762.33 / 132 = KES 5.7752/packet
    - Created at: 2025-11-26 10:15:30
    - Produced by: User #8 (Production Manager)

Nov 28, 2025 @ 3:00 PM (Flour = KES 87.7273/kg NOW):
  Production Batch #44:
    - Product: Bread
    - Mix: Bread Mix Standard (same recipe)
      → Flour: 5.0000 kg × KES 87.7273 = KES 438.64 ← NEW weighted avg
      → Sugar: 0.5000 kg × KES 140.00 = KES 70.00
      → Yeast: 0.0500 kg × KES 300.00 = KES 15.00
      → Salt: 0.1000 kg × KES 50.00 = KES 5.00
      → Wrapper: 132 units × KES 2.00 = KES 264.00
    - Total Cost: KES 792.64 ← HIGHER due to flour price increase
    - Actual Yield: 132 packets
    - Unit Cost: KES 792.64 / 132 = KES 6.0048/packet
    - Created at: 2025-11-28 15:20:45
    - Produced by: User #8 (Production Manager)

Batch #42 cost NEVER changes (frozen at KES 5.7752/packet)
Batch #44 reflects NEW cost (KES 6.0048/packet)
```

**Why This Matters:**
- ✅ **Historical accuracy:** Reports show "On Nov 26, we produced at KES 5.78/packet"
- ✅ **Trend analysis:** Compare batch costs over time to see inflation impact
- ✅ **Profit tracking:** Each batch has its own cost vs selling price

---

#### **3. SALES APP: Compares Selling Price vs Unit Cost**

**No Direct Interaction with Inventory Costs**

**Storage:**
- `DispatchItem.selling_price_at_dispatch` = **Price snapshot from Product model**
- Production batch cost is NOT stored in dispatch/return (lookup via batch for reports)

**Profit Calculation:**
```
Selling Price (from Product) - Unit Cost (from ProductionBatch) = Profit per Unit

Example:
  Batch #42 (Nov 26):
    - Bread unit cost: KES 5.7752/packet (from batch)
    - Bread selling price: KES 60.00/packet (from Product)
    - Profit: KES 60.00 - KES 5.7752 = KES 54.2248/packet (940% margin)
  
  Batch #44 (Nov 28):
    - Bread unit cost: KES 6.0048/packet (from batch)
    - Bread selling price: KES 60.00/packet (from Product, unchanged)
    - Profit: KES 60.00 - KES 6.0048 = KES 53.9952/packet (900% margin)
```

**Dispatch Flow:**
```
1. Accountant creates dispatch:
   - Salesperson: John
   - Products: 100 bread packets
   
2. System looks up current selling price:
   - Product.selling_price = KES 60.00
   
3. Create DispatchItem:
   - quantity_dispatched = 100
   - selling_price_at_dispatch = 60.00 (frozen snapshot)
   - expected_revenue = 100 × 60.00 = KES 6,000.00
   
4. Deduct from ProductStock (no cost calculation here)

5. When return is processed:
   - Calculate profit by linking dispatch to production batches
   - Query: "Which batches were sold in this dispatch?"
   - Aggregate unit costs from those batches
   - Compare: Total revenue - Total cost = Total profit
```

---

### **Summary: Cost Flow Timeline**

```
┌─────────────────────────────────────────────────────────────────┐
│ INVENTORY APP (Source of Truth)                                 │
├─────────────────────────────────────────────────────────────────┤
│ Nov 20: Purchase flour @ KES 90/kg                               │
│   → InventoryItem.weighted_avg_cost = 90.0000                   │
│   → InventoryItem.updated_at = 2025-11-20 09:00:00              │
│   → InventoryItem.updated_by = User #5                          │
│                                                                  │
│ Nov 26: Purchase flour @ KES 80/kg                               │
│   → InventoryItem.weighted_avg_cost = 81.6667 (recalculated)    │
│   → InventoryItem.updated_at = 2025-11-26 08:30:15              │
│   → InventoryItem.updated_by = User #5                          │
│                                                                  │
│ Nov 28: Purchase flour @ KES 95/kg                               │
│   → InventoryItem.weighted_avg_cost = 87.7273 (recalculated)    │
│   → InventoryItem.updated_at = 2025-11-28 14:00:20              │
│   → InventoryItem.updated_by = User #5                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PRODUCTION APP (Cost Snapshot)                                   │
├─────────────────────────────────────────────────────────────────┤
│ Nov 26 @ 10:00 AM: Create Batch #42                             │
│   → Looks up weighted_avg_cost = 81.6667/kg                     │
│   → Calculates total_cost = KES 762.33                          │
│   → Stores unit_cost = KES 5.7752/packet                        │
│   → FROZEN FOREVER (immutable)                                  │
│   → created_at = 2025-11-26 10:15:30                            │
│   → produced_by = User #8                                       │
│                                                                  │
│ Nov 28 @ 3:00 PM: Create Batch #44                              │
│   → Looks up weighted_avg_cost = 87.7273/kg (NEW price)         │
│   → Calculates total_cost = KES 792.64                          │
│   → Stores unit_cost = KES 6.0048/packet                        │
│   → FROZEN FOREVER (immutable)                                  │
│   → created_at = 2025-11-28 15:20:45                            │
│   → produced_by = User #8                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ SALES APP (Profit Calculation)                                   │
├─────────────────────────────────────────────────────────────────┤
│ Nov 26 @ 2:00 PM: Dispatch 100 bread (from Batch #42)           │
│   → Selling price: KES 60.00/packet (from Product)              │
│   → Expected revenue: KES 6,000.00                              │
│   → dispatched_by = User #5                                     │
│                                                                  │
│ Nov 27 @ 9:00 AM: Return processed                              │
│   → Sold: 70 packets × KES 60.00 = KES 4,200.00 revenue         │
│   → Lookup Batch #42 unit_cost = KES 5.7752/packet              │
│   → Profit: (60.00 - 5.7752) × 70 = KES 3,795.74                │
│   → Margin: 940%                                                 │
│   → processed_by = User #5                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚨 **STOCK ALERTS: IMPLEMENTATION STRATEGY**

### **Where Alerts Are Handled: INVENTORY APP ONLY**

**Storage:**
- `InventoryItem.minimum_stock_level` = **Alert threshold for raw materials (ingredients + indirect costs)**

**Why NOT ProductStock?**
- Finished products are meant to be sold, not stockpiled
- Alerts for raw materials prevent production disruption
- Production creates products, sales depletes them (natural flow)

**Alert Logic:**
```python
# Check if stock is low
def is_stock_low(inventory_item):
    return inventory_item.current_stock < inventory_item.minimum_stock_level

def get_low_stock_items():
    from django.db.models import F
    return InventoryItem.objects.filter(
        current_stock__lt=F('minimum_stock_level'),
        is_active=True
    ).order_by('current_stock')
```

**Implementation Options:**

#### **Option 1: Dashboard Widget (Recommended for Phase 1)**
```python
# apps/inventory/views.py
from django.db.models import F

@login_required
def inventory_dashboard(request):
    low_stock_items = InventoryItem.objects.filter(
        current_stock__lt=F('minimum_stock_level'),
        is_active=True
    ).order_by('current_stock')
    
    context = {
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_items.count()
    }
    return render(request, 'inventory/dashboard.html', context)
```

**Template Example:**
```html
{% if low_stock_count > 0 %}
<div class="alert alert-warning">
    <strong>⚠️ Low Stock Alert:</strong> {{ low_stock_count }} items below minimum level
    <ul>
    {% for item in low_stock_items %}
        <li>
            {{ item.name }}: {{ item.current_stock|floatformat:4 }} {{ item.unit_of_measure }}
            (Minimum: {{ item.minimum_stock_level|floatformat:4 }})
            - <a href="{% url 'inventory:create_purchase' %}?item={{ item.id }}">Restock Now</a>
        </li>
    {% endfor %}
    </ul>
</div>
{% endif %}
```

---

#### **Option 2: Email Notifications (Background Task - Phase 2)**
```python
# apps/inventory/management/commands/check_low_stock.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.db.models import F
from apps.inventory.models import InventoryItem

class Command(BaseCommand):
    help = 'Check for low stock and send email alerts'

    def handle(self, *args, **kwargs):
        low_stock_items = InventoryItem.objects.filter(
            current_stock__lt=F('minimum_stock_level'),
            is_active=True
        )
        
        if low_stock_items.exists():
            message = "The following items are below minimum stock level:\n\n"
            for item in low_stock_items:
                message += f"- {item.name}: {item.current_stock} {item.unit_of_measure} "
                message += f"(Min: {item.minimum_stock_level})\n"
            
            send_mail(
                subject='🚨 Daily Low Stock Alert - Chesanto Bakery',
                message=message,
                from_email='alerts@chesanto.com',
                recipient_list=['accountant@chesanto.com', 'manager@chesanto.com'],
            )
            
            self.stdout.write(self.style.WARNING(
                f'Sent low stock alert for {low_stock_items.count()} items'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('All inventory levels are adequate'))
```

**Cron Schedule (Railway.json):**
```json
{
  "cron": [
    {
      "schedule": "0 8 * * *",
      "command": "python manage.py check_low_stock"
    }
  ]
}
```

---

#### **Option 3: Real-Time Alerts (On Deduction - Phase 3)**
```python
# apps/inventory/utils.py
@transaction.atomic
def deduct_ingredients_atomic(ingredients_list, requested_by_app, requested_by_user):
    from django.contrib import messages
    
    deducted_items = []
    
    for ingredient in ingredients_list:
        item = InventoryItem.objects.select_for_update().get(id=ingredient['id'])
        
        # Deduct stock
        item.current_stock -= ingredient['quantity']
        item.updated_by = requested_by_user
        item.save()
        
        deducted_items.append(item)
        
        # Check if now below minimum
        if item.current_stock < item.minimum_stock_level:
            # Optional: Create alert record
            StockAlert.objects.create(
                inventory_item=item,
                triggered_at=timezone.now(),
                triggered_by_app=requested_by_app,
                triggered_by_user=requested_by_user,
                current_stock=item.current_stock,
                minimum_stock=item.minimum_stock_level,
                alert_level='WARNING' if item.current_stock > 0 else 'CRITICAL'
            )
    
    return {
        'success': True,
        'data': {'deducted_items': len(deducted_items)}
    }
```

---

---

### **Recommended Approach: HYBRID (Dashboard + Real-Time Alerts on Production)**

**Why This Works Best:**
- ✅ **Production batch creation** = natural trigger point (ingredients just deducted)
- ✅ **Immediate notification** = accountant/manager knows to restock ASAP
- ✅ **No cron jobs needed** = simpler deployment (no background tasks)
- ✅ **Dashboard** = always-visible status check for manual review
- ✅ **Contextual alerts** = sent when stock actually changes, not arbitrary schedule
- ✅ **Actionable emails** = "Flour is low BECAUSE we just made Batch #45"

---

### **Implementation: Two Components Working Together**

#### **Component 1: Dashboard Widget (Always Visible - Manual Review)**

```python
# apps/inventory/views.py
from django.db.models import F
from django.contrib.auth.decorators import login_required

@login_required
def inventory_dashboard(request):
    # Get all low stock items
    low_stock_items = InventoryItem.objects.filter(
        current_stock__lt=F('minimum_stock_level'),
        is_active=True
    ).order_by('current_stock')
    
    # Separate by severity
    critical_items = low_stock_items.filter(current_stock__lte=0)
    warning_items = low_stock_items.filter(current_stock__gt=0)
    
    context = {
        'critical_items': critical_items,
        'warning_items': warning_items,
        'total_low_stock': low_stock_items.count()
    }
    return render(request, 'inventory/dashboard.html', context)
```

**Template:**
```html
<!-- Critical (Out of Stock) -->
{% if critical_items %}
<div class="alert alert-danger">
    <h4>🚨 CRITICAL: Out of Stock ({{ critical_items.count }})</h4>
    <ul>
    {% for item in critical_items %}
        <li>
            <strong>{{ item.name }}</strong>: {{ item.current_stock|floatformat:4 }} {{ item.unit_of_measure }}
            <span class="badge badge-danger">EMPTY</span>
            <a href="{% url 'inventory:create_purchase' %}?item={{ item.id }}" class="btn btn-sm btn-danger">
                Restock Now
            </a>
        </li>
    {% endfor %}
    </ul>
</div>
{% endif %}

<!-- Warning (Low Stock) -->
{% if warning_items %}
<div class="alert alert-warning">
    <h4>⚠️ WARNING: Low Stock ({{ warning_items.count }})</h4>
    <ul>
    {% for item in warning_items %}
        <li>
            {{ item.name }}: {{ item.current_stock|floatformat:4 }} {{ item.unit_of_measure }}
            (Min: {{ item.minimum_stock_level|floatformat:4 }})
            <a href="{% url 'inventory:create_purchase' %}?item={{ item.id }}">Restock</a>
        </li>
    {% endfor %}
    </ul>
</div>
{% endif %}

<!-- All Good -->
{% if not critical_items and not warning_items %}
<div class="alert alert-success">
    ✅ All inventory levels are adequate
</div>
{% endif %}
```

---

#### **Component 2: Real-Time Alerts (Tied to Production Batch Creation)**

**Updated Production Utility:**
```python
# apps/production/utils.py
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import F
from decimal import Decimal

@transaction.atomic
def create_production_batch_atomic(mix_id, actual_yield, requested_by_user):
    """
    Create production batch and check for low stock alerts
    """
    # Step 1: Get recipe ingredients
    mix = Mix.objects.get(id=mix_id)
    ingredients = mix.mixingredient_set.all()
    
    # Step 2: Calculate costs and deduct ingredients
    total_cost = Decimal('0.00')
    deducted_items = []
    
    for ingredient in ingredients:
        item = InventoryItem.objects.select_for_update().get(
            id=ingredient.inventory_item_id
        )
        
        # Validate sufficient stock
        if item.current_stock < ingredient.quantity_required:
            return {
                'success': False,
                'errors': [f"Insufficient {item.name}: need {ingredient.quantity_required} {item.unit_of_measure}, have {item.current_stock}"],
                'message': 'Inventory check failed'
            }
        
        # Calculate cost
        cost = ingredient.quantity_required * item.weighted_avg_cost
        total_cost += cost
        
        # Deduct from stock
        old_stock = item.current_stock
        item.current_stock -= ingredient.quantity_required
        item.updated_by = requested_by_user
        item.save()
        
        deducted_items.append({
            'item': item,
            'deducted': ingredient.quantity_required,
            'old_stock': old_stock,
            'new_stock': item.current_stock
        })
    
    # Step 3: Create production batch
    batch = ProductionBatch.objects.create(
        product=mix.product,
        mix=mix,
        expected_yield=mix.expected_yield,
        actual_yield=actual_yield,
        total_cost=total_cost,
        unit_cost=total_cost / actual_yield,
        produced_by=requested_by_user,
        batch_date=date.today()
    )
    
    # Step 4: Update ProductStock
    product_stock, created = ProductStock.objects.get_or_create(
        product=mix.product
    )
    product_stock.current_stock += actual_yield
    product_stock.save()
    
    # Step 5: CHECK FOR LOW STOCK ALERTS (Real-time)
    low_stock_alerts = []
    for deducted in deducted_items:
        item = deducted['item']
        
        # Check if now below minimum
        if item.current_stock < item.minimum_stock_level:
            low_stock_alerts.append({
                'name': item.name,
                'current': float(item.current_stock),
                'minimum': float(item.minimum_stock_level),
                'unit': item.unit_of_measure,
                'deducted_now': float(deducted['deducted']),
                'old_stock': float(deducted['old_stock']),
                'status': 'CRITICAL' if item.current_stock <= 0 else 'WARNING'
            })
    
    # Step 6: Send email alert if any items are low
    if low_stock_alerts:
        send_low_stock_email(
            batch=batch,
            low_stock_items=low_stock_alerts,
            triggered_by=requested_by_user
        )
    
    return {
        'success': True,
        'data': {
            'batch_id': batch.id,
            'batch_number': batch.batch_number,
            'low_stock_alerts': low_stock_alerts  # Return to view for UI display
        },
        'message': f'Batch {batch.batch_number} created successfully'
    }


def send_low_stock_email(batch, low_stock_items, triggered_by):
    """
    Send email alert for low stock items after production
    """
    # Build email content
    subject = f"🚨 Low Stock Alert - After Batch {batch.batch_number}"
    
    message = f"""
Production Batch Created:
{'='*60}
- Batch: {batch.batch_number}
- Product: {batch.product.name}
- Yield: {batch.actual_yield} units
- Created by: {triggered_by.get_full_name() or triggered_by.email}
- Time: {batch.created_at.strftime('%Y-%m-%d %H:%M')}

LOW STOCK DETECTED:
{'='*60}
"""
    
    critical_items = [item for item in low_stock_items if item['status'] == 'CRITICAL']
    warning_items = [item for item in low_stock_items if item['status'] == 'WARNING']
    
    if critical_items:
        message += f"\n🚨 CRITICAL - OUT OF STOCK ({len(critical_items)} items):\n"
        for item in critical_items:
            message += f"  - {item['name']}: {item['current']} {item['unit']} "
            message += f"(Was {item['old_stock']}, Used {item['deducted_now']} in this batch)\n"
            message += f"    ⚠️ CANNOT PRODUCE MORE WITHOUT RESTOCKING!\n"
    
    if warning_items:
        message += f"\n⚠️ WARNING - LOW STOCK ({len(warning_items)} items):\n"
        for item in warning_items:
            message += f"  - {item['name']}: {item['current']} {item['unit']} "
            message += f"(Min: {item['minimum']}, Used {item['deducted_now']} in this batch)\n"
    
    message += f"\n{'='*60}\n"
    message += "ACTION REQUIRED: Restock these items before next production batch.\n"
    message += f"Dashboard: {settings.SITE_URL}/inventory/dashboard/\n"
    
    # Send to configured recipients
    recipient_list = getattr(settings, 'STOCK_ALERT_RECIPIENTS', [
        'accountant@chesanto.com',
        'manager@chesanto.com',
    ])
    
    # Optional: Also notify the person who created the batch
    if triggered_by.email and triggered_by.email not in recipient_list:
        recipient_list.append(triggered_by.email)
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=True  # Don't break production if email fails
        )
    except Exception as e:
        # Log error but don't fail the batch creation
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send low stock email: {e}")
```

---

#### **Component 3: View Integration (Show Alerts to User)**

```python
# apps/production/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal

@login_required
def create_batch_view(request):
    if request.method == 'POST':
        # Get form data
        mix_id = request.POST.get('mix_id')
        actual_yield = request.POST.get('actual_yield')
        
        # Call utility function
        result = create_production_batch_atomic(
            mix_id=mix_id,
            actual_yield=Decimal(actual_yield),
            requested_by_user=request.user
        )
        
        if result['success']:
            # Show success message
            messages.success(
                request,
                f"✅ Production batch {result['data']['batch_number']} created successfully! "
                f"Added {actual_yield} units to stock."
            )
            
            # Show low stock warnings in UI
            low_stock = result['data'].get('low_stock_alerts', [])
            if low_stock:
                critical = [i for i in low_stock if i['status'] == 'CRITICAL']
                warning = [i for i in low_stock if i['status'] == 'WARNING']
                
                if critical:
                    critical_names = ', '.join([i['name'] for i in critical])
                    messages.error(
                        request,
                        f"🚨 CRITICAL: {len(critical)} items are OUT OF STOCK ({critical_names})! "
                        f"Email sent to management. Restock immediately!"
                    )
                
                if warning:
                    warning_names = ', '.join([i['name'] for i in warning])
                    messages.warning(
                        request,
                        f"⚠️ WARNING: {len(warning)} items are LOW on stock ({warning_names}). "
                        f"Email sent to management. Consider restocking soon."
                    )
            
            return redirect('production:batch_detail', pk=result['data']['batch_id'])
        else:
            for error in result['errors']:
                messages.error(request, error)
    
    # GET request - show form
    mixes = Mix.objects.filter(is_active=True)
    context = {'mixes': mixes}
    return render(request, 'production/create_batch.html', context)
```

---

### **Settings Configuration**

```python
# config/settings/base.py

# Email recipients for stock alerts
STOCK_ALERT_RECIPIENTS = [
    'accountant@chesanto.com',
    'manager@chesanto.com',
    # Add more as needed
]

# Site URL for dashboard links in emails
SITE_URL = env('SITE_URL', default='http://127.0.0.1:8000')
```

```python
# config/settings/production.py

SITE_URL = 'https://chesanto.railway.app'
```

---

### **Alert Flow Example**

```
TIME: Nov 28, 2025 @ 10:00 AM
ACTION: Production Manager creates Batch #45 (Bread)

BEFORE BATCH:
  - Flour: 12.0000 kg (Minimum: 10.0000 kg) ✅ OK

BATCH CREATION PROCESS:
  1. Validate ingredients available ✅
  2. Deduct 5.0000 kg flour
  3. Create ProductionBatch #45
  4. Add 132 bread to ProductStock
  5. Check stock levels:
     - Flour: 7.0000 kg < 10.0000 kg ⚠️ LOW STOCK DETECTED
  
IMMEDIATE ACTIONS:
  ✅ Email sent to: accountant@chesanto.com, manager@chesanto.com
  ✅ Warning shown in production view UI:
      "⚠️ WARNING: 1 item is LOW on stock (Flour). Email sent to management."
  ✅ Dashboard updated (yellow badge on Flour)

EMAIL RECEIVED:
  Subject: 🚨 Low Stock Alert - After Batch PB-2025-11-28-001
  
  Production Batch Created:
  ============================================================
  - Batch: PB-2025-11-28-001
  - Product: Bread
  - Yield: 132 units
  - Created by: John Doe
  - Time: 2025-11-28 10:15
  
  ⚠️ WARNING - LOW STOCK (1 item):
    - Flour: 7.0000 kg (Min: 10.0000, Used 5.0000 in this batch)
  
  ============================================================
  ACTION REQUIRED: Restock before next production batch.
  Dashboard: https://chesanto.railway.app/inventory/dashboard/
```

---

### **Why This Hybrid Approach is Superior**

| Aspect | Scheduled Cron (8 AM) | Hybrid (Dashboard + Real-Time) |
|--------|----------------------|--------------------------------|
| **Timing** | Arbitrary (8 AM) | Contextual (when stock changes) |
| **Relevance** | May alert when nothing changed | Only alerts when stock actually drops |
| **Actionability** | "Flour is low" (no context) | "Flour is low BECAUSE we just made Batch #45" |
| **Deployment** | Requires cron job setup | No external dependencies |
| **Complexity** | Extra infrastructure | Built into core workflow |
| **Testing** | Hard to test cron locally | Easy to test (just create batch) |
| **User Experience** | Passive notification | Active notification at point of action |
| **Visibility** | Email only (can be missed) | Dashboard + Email + UI messages |

---

### **Optional Enhancement: Alert History (Future Phase)**

```python
# apps/inventory/models.py
class StockAlert(models.Model):
    """Track stock alert history for analytics"""
    inventory_item = models.ForeignKey('InventoryItem', on_delete=models.CASCADE, related_name='stock_alerts')
    alert_level = models.CharField(max_length=10, choices=[
        ('WARNING', 'Low Stock'),
        ('CRITICAL', 'Out of Stock')
    ])
    triggered_at = models.DateTimeField(auto_now_add=True)
    triggered_by_batch = models.ForeignKey(
        'production.ProductionBatch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Production batch that triggered this alert"
    )
    current_stock = models.DecimalField(max_digits=10, decimal_places=4)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=4)
    email_sent = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-triggered_at']
    
    def __str__(self):
        return f"{self.alert_level}: {self.inventory_item.name} @ {self.triggered_at}"
```

**Benefits of Alert History:**
- 📊 **Analytics:** How often does each item go low?
- 📈 **Trends:** Are we restocking frequently enough?
- 🎯 **Optimization:** Adjust minimum_stock_level based on actual patterns
- ✅ **Accountability:** Who acknowledged the alert? When did they restock?

---

## ✅ **FINAL RECOMMENDATION: HYBRID APPROACH**

**Phase 1 (Immediate Implementation):**
1. ✅ **Dashboard widget** - Always visible status check
2. ✅ **Real-time alerts on batch creation** - Email + UI messages
3. ✅ **Settings-based recipient list** - Easy to configure

**Phase 2 (Future Enhancement):**
1. ⏳ **Alert history model** - Track patterns and trends
2. ⏳ **Acknowledgment workflow** - "I've seen this, I'm handling it"
3. ⏳ **Predictive alerts** - "At current usage rate, you'll run out in 3 days"

**No cron jobs, no background tasks, no external dependencies** - just clean, contextual alerts tied to the natural production workflow! 🚀

---

### **Recommended Approach: PHASED ROLLOUT**

**Phase 1 (Immediate):**
- ✅ **Dashboard Widget** on Inventory app homepage
- ✅ **View-level warnings** when viewing item details
- ✅ **Color-coded badges** (green = OK, yellow = low, red = critical)

**Phase 2 (After 1 month):**
- ✅ **Daily email alerts** (8 AM summary)
- ✅ **Weekly trend reports** (stock consumption rates)

**Phase 3 (Future Enhancement):**
- ✅ **Real-time push notifications** (browser/mobile)
- ✅ **Predictive alerts** (based on consumption trends)
- ✅ **Auto-purchase suggestions** (integrate with supplier system)

**Optional Model (For Alert History):**
```python
StockAlert:
  - inventory_item (ForeignKey: InventoryItem, related_name='stock_alerts')
  - alert_type (CharField: choices=['LOW_STOCK', 'CRITICAL_STOCK', 'RESTOCK_NEEDED'])
  - alert_level (CharField: choices=['WARNING', 'CRITICAL'])
  - triggered_at (DateTimeField: auto_now_add)
  - triggered_by_app (CharField: 'production', 'sales', 'manual_check')
  - triggered_by_user (ForeignKey: User, null=True)
  - current_stock (DecimalField: snapshot of stock at alert time)
  - minimum_stock (DecimalField: snapshot of threshold)
  - acknowledged_by (ForeignKey: User, null=True, blank=True)
  - acknowledged_at (DateTimeField: null=True, blank=True)
  - notes (TextField: blank=True)
```

---

## 🏗️ **Cross-App Communication Flow**

```
View/Form (User Action)
    ↓
App Utility (Orchestrator)
    ↓
    ├─→ Own Models (Create records)
    ├─→ Other App Utility #1 (Deduct stock)
    ├─→ Other App Utility #2 (Update tallies)
    └─→ Audit Log (Record action)
    ↓
Standardized Response
    ↓
View (Show success/error to user)
```

**Example: Create Production Batch**
```
production/views.py (User submits form)
    ↓
production/utils.create_production_batch_atomic()
    ├─→ ProductionBatch.objects.create()
    ├─→ inventory/utils.deduct_ingredients_atomic()  ✓ Cross-app
    ├─→ production/models.ProductStock (update tally)
    └─→ audit/utils.log_production_event()
    ↓
{'success': True, 'data': {...}, 'message': '...'}
    ↓
View shows success message
```

---

## 📦 **PRODUCTS APP - FINAL SPECIFICATION**

### **Model: Product**
**Purpose:** Master catalog of all bakery products (bread, scones, KDF, sub-products)

**Key Features:**
- ✅ **Sub-products support** (quality tiers via self-referential FK)
- ✅ **Adjustable pricing** (accountant can change selling_price)
- ✅ **Only foundation app with UPDATE/DELETE** (recipes can be edited)

**Fields:**
```python
Product:
  - name (CharField: "Bread", "Scones", "KDF", "Bread Leftovers")
  - parent_product (ForeignKey: nullable, self-reference for sub-products)
  - selling_price (DecimalField: max_digits=10, decimal_places=2)
  - description (TextField: optional details)
  - is_active (Boolean: can be disabled without deletion)
  - created_at (DateTimeField: auto_now_add)
  - updated_at (DateTimeField: auto_now)
  - created_by (ForeignKey: User, related_name='products_created')
  - updated_by (ForeignKey: User, related_name='products_updated', null=True)
```

**Example:**
```
Product #1: "Bread" (parent=None, price=60)
  ↓
Product #2: "Bread Leftovers" (parent=Product#1, price=50)
```

---

### **Model: Mix**
**Purpose:** Recipe lookup - ingredients + quantities required per product

**Key Features:**
- ❌ **NO versioning** (static reference, edit in place)
- ✅ **Fixed yield for bread/scones** (132/102 packets)
- ✅ **Variable yield for KDF** (97-107 packets, hand-cut)
- ✅ **Direct vs Indirect ingredients** (all deducted from inventory)

**Fields:**
```python
Mix:
  - product (ForeignKey: which product this recipe produces)
  - name (CharField: "Bread Mix Standard", "Scones Mix v1")
  - expected_yield (DecimalField: max_digits=10, decimal_places=4)
  - is_fixed_yield (Boolean: True for machine-weighed, False for hand-cut)
  - is_active (Boolean: only one active mix per product)
  - created_at (DateTimeField: auto_now_add)
  - updated_at (DateTimeField: auto_now)
  - created_by (ForeignKey: User, related_name='mixes_created')
  - updated_by (ForeignKey: User, related_name='mixes_updated', null=True)
```

---

### **Model: MixIngredient**
**Purpose:** Through-table linking Mix to InventoryItems with quantities

**Key Features:**
- ✅ **Base units only** (grams, milliliters)
- ✅ **Direct vs Indirect** (flour is direct, packaging is indirect)
- ✅ **Both types deducted** during production

**Fields:**
```python
MixIngredient:
  - mix (ForeignKey: which recipe)
  - inventory_item (ForeignKey: Inventory.InventoryItem)
  - quantity_required (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - ingredient_type (CharField: choices=['INGREDIENT', 'INDIRECT_COST'])
  - unit_of_measure (CharField: 'kg', 'L', 'units' - standard units)
  - notes (TextField: optional, e.g., "sifted flour")
  - created_at (DateTimeField: auto_now_add)
```

**Example:**
```
Mix: "Bread Mix Standard"
  - Flour (5000g, DIRECT)
  - Sugar (500g, DIRECT)
  - Yeast (50g, DIRECT)
  - Salt (100g, DIRECT)
  - Bread Wrapper (132 units, INDIRECT)
  → Produces: 132 bread packets
```

---

### **Utility Functions:**
```python
# apps/products/utils.py

@transaction.atomic
def create_product_atomic(name, selling_price, parent_product=None, requested_by_user=None):
    """Create new product with validation"""
    
@transaction.atomic  
def update_product_price_atomic(product_id, new_price, requested_by_user=None):
    """Update selling price (logged for audit)"""
    
@transaction.atomic
def create_mix_atomic(product_id, expected_yield, ingredients_list, requested_by_user=None):
    """Create recipe with ingredients"""
    
@transaction.atomic
def update_mix_atomic(mix_id, ingredients_list, requested_by_user=None):
    """Update recipe (only if no active production batches using it)"""
```

---

## 🏭 **PRODUCTION APP - FINAL SPECIFICATION**

### **Model: ProductionBatch**
**Purpose:** Daily production records (CREATE ONLY - immutable after creation)

**Key Features:**
- ❌ **NO batch states** (atomic = success or rollback)
- ✅ **One product per batch** (simpler logic)
- ✅ **Cost calculated at creation** (from Inventory weighted avg)
- ✅ **Actual yield tracking** (especially for KDF variance)

**Fields:**
```python
ProductionBatch:
  - batch_number (CharField: auto-generated, e.g., "PB-2025-11-26-001")
  - product (ForeignKey: Product)
  - mix (ForeignKey: Mix - snapshot which recipe was used)
  - expected_yield (DecimalField: max_digits=10, decimal_places=4)
  - actual_yield (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - total_cost (DecimalField: max_digits=12, decimal_places=2)
  - unit_cost (DecimalField: max_digits=10, decimal_places=4, auto-calc)
  - batch_date (DateField: production date)
  - produced_by (ForeignKey: User, related_name='batches_produced')
  - created_at (DateTimeField: auto_now_add)
  - notes (TextField: optional)
```

**Example:**
```
ProductionBatch #42:
  - Product: Bread
  - Mix: "Bread Mix Standard"
  - Expected: 132 packets
  - Actual: 132 packets (machine-weighed, exact)
  - Total Cost: KES 3,960 (ingredients at weighted avg)
  - Unit Cost: KES 30/packet
  - Selling Price: KES 60/packet
  - Profit Margin: KES 30/packet (50%)
```

---

### **Model: ProductStock**
**Purpose:** Real-time tally of available finished products

**Key Features:**
- ✅ **Updated by Production** (adds products)
- ✅ **Updated by Sales** (deducts on dispatch, adds on return)
- ✅ **Row locking** on all updates (prevent race conditions)

**Fields:**
```python
ProductStock:
  - product (OneToOneField: Product)
  - current_stock (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - last_updated (DateTimeField: auto_now)
```

**Note:** No `minimum_stock_level` for finished products - they are meant to be sold, not stockpiled. Stock alerts only apply to raw materials (InventoryItem).

---

### **Utility Functions:**
```python
# apps/production/utils.py

@transaction.atomic
def create_production_batch_atomic(
    mix_id, 
    actual_yield, 
    batch_date,
    requested_by_app='production',
    requested_by_user=None
):
    """
    Creates production batch and updates stock
    
    Steps:
    1. Get Mix and ingredients
    2. Call inventory_utils.deduct_ingredients_atomic()
    3. If success, create ProductionBatch
    4. Update ProductStock (add actual_yield)
    5. Return success/error
    """
    
@transaction.atomic
def deduct_products_atomic(
    product_id, 
    quantity, 
    requested_by_app='sales',
    requested_by_user=None
):
    """
    Deduct products for dispatch (called by Sales)
    
    Uses select_for_update() to prevent race conditions
    """
    
@transaction.atomic
def return_products_atomic(
    product_id, 
    quantity, 
    requested_by_app='sales',
    requested_by_user=None
):
    """
    Return unsold products (called by Sales)
    
    Adds back to ProductStock
    """
```

---

## 📊 **INVENTORY APP - FINAL SPECIFICATION**

### **Model: InventoryItem**
**Purpose:** Track all ingredients and indirect costs (CREATE ONLY after purchase)

**Key Features:**
- ✅ **Two categories:** Ingredients (direct) vs Indirect Costs (packaging, fuel, electricity, crates)
- ✅ **Standard units:** Kilograms (kg) and Liters (L) - NO base unit conversions needed
- ✅ **Decimal precision:** Up to 4 decimal places (0.0000) for accuracy
- ✅ **Weighted average costing** (auto-recalculated on each purchase)
- ✅ **Stock alerts** (minimum_stock_level triggers warnings in Inventory app views/dashboard)
- ❌ **No negative quantities** (validation enforced via MinValueValidator)

**Fields:**
```python
InventoryItem:
  - name (CharField: max_length=200, unique=True)
  - category (BooleanField: True='INGREDIENT', False='INDIRECT_COST')
  - unit_of_measure (CharField: choices=['kg', 'L', 'units'])
  - current_stock (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - weighted_avg_cost (DecimalField: max_digits=10, decimal_places=4, default=0, auto-calculated)
  - minimum_stock_level (DecimalField: max_digits=10, decimal_places=4, default=0)
  - current_value (DecimalField: max_digits=12, decimal_places=2, auto-calc: stock × weighted_avg)
  - is_active (Boolean: default=True)
  - created_at (DateTimeField: auto_now_add)
  - updated_at (DateTimeField: auto_now)
  - created_by (ForeignKey: User, related_name='inventory_items_created')
  - updated_by (ForeignKey: User, related_name='inventory_items_updated', null=True)
```

**Category Breakdown:**
```
INGREDIENT (category=True):
  - Goes directly into product
  - Examples: Flour, Sugar, Salt, Yeast, Baking Powder, Water
  - Units: kg, L
  - Tracked for production cost calculation

INDIRECT_COST (category=False):
  - Used in production but not IN the product
  - Examples: Bread Crate, Packaging Material, Diesel Fuel, Electricity (kWh as units)
  - Units: kg, L, units (for countable items like crates)
  - Tracked for operational cost analysis
```

**Example:**
```
InventoryItem: "Flour"
  - category: INGREDIENT (True)
  - unit: kg
  - current_stock: 25.5000 kg
  - weighted_avg_cost: KES 85.0000/kg
  - minimum_stock: 10.0000 kg
  - current_value: KES 2,167.50
  - created_by: User #5 (Accountant)
  - created_at: 2025-11-20 09:00:00
  
InventoryItem: "Bread Crate"
  - category: INDIRECT_COST (False)
  - unit: units
  - current_stock: 150.0000 units
  - weighted_avg_cost: KES 250.0000/unit
  - minimum_stock: 50.0000 units
  - current_value: KES 37,500.00
  - created_by: User #5 (Accountant)
  - created_at: 2025-11-15 14:30:00

InventoryItem: "Diesel Fuel"
  - category: INDIRECT_COST (False)
  - unit: L
  - current_stock: 45.7500 L
  - weighted_avg_cost: KES 180.0000/L
  - minimum_stock: 20.0000 L
  - current_value: KES 8,235.00
  - created_by: User #5 (Accountant)
  - created_at: 2025-11-10 11:15:00
```

---

### **Model: Purchase**
**Purpose:** Immutable purchase records (like bank statements)

**Key Features:**
- ❌ **NO updates/deletes** after creation
- ✅ **Historical price tracking** (query for trends)
- ✅ **Updates InventoryItem weighted_avg_cost** on save

**Fields:**
```python
Purchase:
  - purchase_number (CharField: auto-generated, "PUR-2025-11-26-001")
  - supplier_name (CharField: max_length=200, optional for now)
  - purchase_date (DateField)
  - total_amount (DecimalField: max_digits=12, decimal_places=2, sum of all line items)
  - purchased_by (ForeignKey: User, related_name='purchases_made')
  - created_at (DateTimeField: auto_now_add)
  - notes (TextField: optional, blank=True)
```

---

### **Model: PurchaseItem**
**Purpose:** Line items for each purchase (through-table)

**Key Features:**
- ✅ **Stores purchase price at that moment** (historical record)
- ✅ **Auto-converts units to base** (kg → g, L → ml)
- ✅ **Triggers weighted avg recalculation**

**Fields:**
```python
PurchaseItem:
  - purchase (ForeignKey: Purchase, related_name='items')
  - inventory_item (ForeignKey: InventoryItem, related_name='purchase_history')
  - quantity_purchased (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - unit_price (DecimalField: max_digits=10, decimal_places=4, price per unit at purchase time)
  - total_cost (DecimalField: max_digits=12, decimal_places=2, auto-calc: quantity × unit_price)
  - created_at (DateTimeField: auto_now_add)
```

**Example:**
```
Purchase #15 (Nov 26, 2025):
  - Supplier: "ABC Suppliers"
  - Total: KES 12,000
  - Purchased by: User #5 (Accountant John)
  - Created at: 2025-11-26 08:30:00
  
  Line Item 1:
    - InventoryItem: Flour
    - Quantity: 50.0000 kg (stored in standard units)
    - Unit price: KES 80.0000/kg
    - Total cost: KES 4,000.00
    
  Line Item 2:
    - InventoryItem: Sugar
    - Quantity: 25.0000 kg
    - Unit price: KES 140.0000/kg
    - Total cost: KES 3,500.00
```

**Weighted Average Calculation:**
```
Before Purchase:
  Flour stock: 10.0000 kg @ KES 90.0000/kg = KES 900.00 value
  
Purchase adds:
  50.0000 kg @ KES 80.0000/kg = KES 4,000.00 value
  
After Purchase (ATOMIC CALCULATION):
  Total stock: 60.0000 kg
  Total value: KES 4,900.00
  New weighted avg: KES 4,900.00 / 60.0000 kg = KES 81.6667/kg
  
  InventoryItem.weighted_avg_cost = 81.6667 (updated)
  InventoryItem.updated_at = 2025-11-26 08:30:15 (auto-timestamp)
  InventoryItem.updated_by = User #5 (who created the purchase)
```

---

### **Model: InventoryAdjustment**
**Purpose:** Manual corrections for found/lost/damaged items

**Key Features:**
- ✅ **Audit trail** (who, when, why)
- ✅ **Positive or negative** quantities
- ✅ **Used for lost crate recovery**

**Fields:**
```python
InventoryAdjustment:
  - adjustment_number (CharField: auto, "ADJ-2025-11-26-001")
  - inventory_item (ForeignKey: InventoryItem, related_name='adjustments')
  - adjustment_type (CharField: choices=['FOUND', 'LOST', 'DAMAGED', 'STOLEN', 'CORRECTION'])
  - quantity (DecimalField: max_digits=10, decimal_places=4, can be +/-)
  - reason (TextField: required explanation)
  - adjusted_by (ForeignKey: User, related_name='inventory_adjustments')
  - adjustment_date (DateField)
  - created_at (DateTimeField: auto_now_add)
```

---

### **Utility Functions:**
```python
# apps/inventory/utils.py

@transaction.atomic
def create_purchase_atomic(
    supplier_name,
    purchase_items_list,  # [{'item_id': 1, 'quantity': 50, 'unit': 'kg', 'price': 4000}, ...]
    requested_by_user=None
):
    """
    Creates purchase and updates inventory stock + weighted avg
    
    Steps:
    1. Create Purchase record
    2. For each item:
       a. Convert to base units (kg → g)
       b. Create PurchaseItem
       c. Update InventoryItem.current_stock
       d. Recalculate weighted_avg_cost
    3. Return success/error
    """

@transaction.atomic
def deduct_ingredients_atomic(
    ingredients_list,  # [{'item_id': 1, 'quantity': 5000}, ...]
    requested_by_app='production',
    requested_by_user=None
):
    """
    Deduct ingredients for production (called by Production app)
    
    Validation:
    - Check stock availability
    - Lock rows with select_for_update()
    - Deduct and update current_stock
    - Return success/error with current weighted_avg_cost
    """

@transaction.atomic
def deduct_crates_atomic(
    crate_item_id,
    quantity,
    requested_by_app='sales',
    requested_by_user=None
):
    """
    Deduct crates for dispatch (called by Sales app)
    
    Uses select_for_update() to prevent race conditions
    """

@transaction.atomic
def return_crates_atomic(
    crate_item_id,
    quantity,
    requested_by_app='sales',
    requested_by_user=None
):
    """
    Return crates from sales (called by Sales app)
    
    Adds back to stock
    """

@transaction.atomic
def create_adjustment_atomic(
    inventory_item_id,
    adjustment_type,
    quantity,
    reason,
    requested_by_user=None
):
    """
    Manual inventory adjustment
    
    Logs adjustment and updates stock
    """
```

---

## 💰 **SALES APP - FINAL SPECIFICATION**

### **Model: Dispatch**
**Purpose:** Record of products sent to salesperson (CREATE ONLY - immutable)

**Key Features:**
- ✅ **Two-step process** (products first, crates optional/later)
- ✅ **Crates can be added later** (before return)
- ✅ **Immutable after return processed**

**Fields:**
```python
Dispatch:
  - dispatch_number (CharField: auto, "DISP-2025-11-26-001")
  - salesperson (ForeignKey: User, limit_choices_to={'role': 'SALESMAN'})
  - dispatch_date (DateField)
  - dispatched_by (ForeignKey: User, related_name='dispatches_created')
  - is_closed (Boolean: default=False, True after return processed)
  - created_at (DateTimeField: auto_now_add)
  - notes (TextField: optional, blank=True)
```

---

### **Model: DispatchItem**
**Purpose:** Line items - which products and quantities dispatched

**Fields:**
```python
DispatchItem:
  - dispatch (ForeignKey: Dispatch, related_name='items')
  - product (ForeignKey: Product)
  - quantity_dispatched (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - selling_price_at_dispatch (DecimalField: max_digits=10, decimal_places=2, price snapshot)
  - expected_revenue (DecimalField: max_digits=12, decimal_places=2, auto-calc: quantity × price)
```

**Example:**
```
Dispatch #42 to John (Salesman):
  - Date: Nov 26, 2025
  
  Line Item 1:
    - Product: Bread
    - Quantity: 100 packets
    - Price: KES 60/packet
    - Expected Revenue: KES 6,000
    
  Line Item 2:
    - Product: Scones
    - Quantity: 50 packets
    - Price: KES 40/packet
    - Expected Revenue: KES 2,000
    
  Total Expected: KES 8,000
```

---

### **Model: DispatchCrate**
**Purpose:** Crates assigned to dispatch (optional, can be added later)

**Fields:**
```python
DispatchCrate:
  - dispatch (ForeignKey: Dispatch, related_name='crates')
  - inventory_item (ForeignKey: InventoryItem, limit_choices_to={'category': False})
  - quantity_dispatched (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - assigned_at (DateTimeField: auto_now_add)
  - assigned_by (ForeignKey: User, related_name='crates_assigned')
```

---

### **Model: ProductReturn**
**Purpose:** Products returned from salesperson (CREATE ONLY - immutable)

**Key Features:**
- ✅ **Value equivalence validation** (sold + returned = dispatched)
- ✅ **Accountant-only access** (security)
- ✅ **One return per dispatch** (transaction close)
- ✅ **Auto-calculate missing quantities**

**Fields:**
```python
ProductReturn:
  - return_number (CharField: auto, "RET-2025-11-26-001")
  - dispatch (OneToOneField: Dispatch, related_name='return_record')
  - return_date (DateField)
  - processed_by (ForeignKey: User, limit_choices_to={'role__gte': 'ACCOUNTANT'})
  - created_at (DateTimeField: auto_now_add)
```

---

### **Model: ProductReturnItem**
**Purpose:** Line items - sold/returned quantities per product

**Fields:**
```python
ProductReturnItem:
  - product_return (ForeignKey: ProductReturn, related_name='items')
  - dispatch_item (ForeignKey: DispatchItem)
  - quantity_sold (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - quantity_returned (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - quantity_missing (DecimalField: max_digits=10, decimal_places=4, auto-calc)
  - cash_collected (DecimalField: max_digits=12, decimal_places=2)
  - expected_cash (DecimalField: max_digits=12, decimal_places=2, auto-calc)
  - cash_variance (DecimalField: max_digits=12, decimal_places=2, auto-calc)
  - variance_reason (TextField: required if variance != 0)
```

**Validation:**
```python
# Must pass before save:
sold + returned = dispatched  # Value equivalence
cash_collected ≈ (sold × selling_price)  # Cash verification
```

---

### **Model: CrateReturn**
**Purpose:** Crates returned from salesperson (CREATE ONLY - immutable)

**Fields:**
```python
CrateReturn:
  - product_return (OneToOneField: ProductReturn, related_name='crate_return')
  - dispatch_crate (ForeignKey: DispatchCrate)
  - crates_returned (DecimalField: max_digits=10, decimal_places=4, validators=[MinValueValidator(0)])
  - crates_missing (DecimalField: max_digits=10, decimal_places=4, auto-calc)
  - is_closed (Boolean: default=False)
  - closed_at (DateTimeField: null=True, blank=True)
  - closed_by (ForeignKey: User, null=True, blank=True, related_name='crate_returns_closed')
```

**Lost Crate Handling:**
```
If 10 crates dispatched, 5 returned:
  - crates_returned: 5
  - crates_missing: 5 (marked, not recovered via this transaction)
  
If lost crates found later:
  - Use InventoryAdjustment (type='FOUND', quantity=5)
  - Cannot reopen closed CrateReturn
```

---

### **Utility Functions:**
```python
# apps/sales/utils.py

@transaction.atomic
def create_dispatch_atomic(
    salesperson_id,
    products_list,  # [{'product_id': 1, 'quantity': 100}, ...]
    requested_by_user=None
):
    """
    Step 1: Dispatch products (crates added later)
    
    Steps:
    1. Validate salesperson exists and is active
    2. Call production_utils.deduct_products_atomic()
    3. If success, create Dispatch + DispatchItems
    4. Return dispatch_id for Step 2
    """

@transaction.atomic
def assign_crates_to_dispatch_atomic(
    dispatch_id,
    crate_item_id,
    quantity,
    requested_by_user=None
):
    """
    Step 2: Assign crates (optional, before return)
    
    Steps:
    1. Get Dispatch (must not be closed)
    2. Call inventory_utils.deduct_crates_atomic()
    3. Create DispatchCrate record
    """

@transaction.atomic
def process_return_atomic(
    dispatch_id,
    return_items_list,  # [{'dispatch_item_id': 1, 'sold': 70, 'returned': 30, 'cash': 4200}, ...]
    crates_returned=0,
    requested_by_user=None
):
    """
    Process product and crate returns
    
    Steps:
    1. Validate value equivalence (sold + returned = dispatched)
    2. Call production_utils.return_products_atomic()
    3. Call inventory_utils.return_crates_atomic()
    4. Create ProductReturn + ProductReturnItems
    5. Create CrateReturn
    6. Mark Dispatch as closed
    7. Return success/error
    """
```

---

## 🏗️ **CROSS-APP UTILITY FLOW (FINAL)**

### **Production Batch Creation:**
```
View: production/create_batch/
    ↓
production/utils.create_production_batch_atomic()
    ├─→ inventory/utils.deduct_ingredients_atomic()  ✓ Locks ingredient rows
    ├─→ ProductionBatch.objects.create()
    ├─→ ProductStock update (add products)
    └─→ audit/utils.log_production()
    ↓
Return: {'success': True, 'data': {'batch_id': 42}}
```

### **Dispatch Creation:**
```
View: sales/create_dispatch/
    ↓
sales/utils.create_dispatch_atomic()
    ├─→ production/utils.deduct_products_atomic()  ✓ Locks product stock
    ├─→ Dispatch.objects.create()
    ├─→ DispatchItem.objects.bulk_create()
    └─→ audit/utils.log_dispatch()
    ↓
Return: {'success': True, 'data': {'dispatch_id': 15}}
    ↓
sales/utils.assign_crates_to_dispatch_atomic()
    ├─→ inventory/utils.deduct_crates_atomic()  ✓ Locks crate stock
    └─→ DispatchCrate.objects.create()
```

### **Return Processing:**
```
View: sales/process_return/
    ↓
sales/utils.process_return_atomic()
    ├─→ Validate value equivalence
    ├─→ production/utils.return_products_atomic()  ✓ Locks product stock
    ├─→ inventory/utils.return_crates_atomic()  ✓ Locks crate stock
    ├─→ ProductReturn.objects.create()
    ├─→ ProductReturnItem.objects.bulk_create()
    ├─→ CrateReturn.objects.create()
    ├─→ Dispatch.is_closed = True
    └─→ audit/utils.log_return()
```

#### **Decision 1: Sub-Products (Quality Tiers)**
- **Requirement:** Products have quality variants with different prices
- **Example:** 
  - High-quality bread → KES 60/packet
  - Leftovers/seconds → KES 50/packet
- **Implementation:** `Product.parent_product` (nullable FK to self)
- **Pricing:** Each product has its own `selling_price` field (adjustable)

#### **Decision 2: NO Mix Versioning**
- ❌ **REJECTED:** Version tracking complexity
- ✅ **ADOPTED:** Mix is simple **lookup/reference** with name + quantities
- **Rationale:** Avoid over-engineering. Mix = static recipe reference.
- **Cost Tracking:** Prices live in Inventory, production costs calculated in Production app

#### **Decision 3: Standard Units (Kilograms/Liters)**
- ✅ **Store everything in standard units:** kilograms (kg), liters (L), units (countable items)
- ✅ **Decimal precision:** Up to 4 decimal places (0.0000) for accuracy
- ✅ **No conversions needed:** Purchases, storage, and production all use same units
- ✅ **Supplier units match:** Most suppliers sell in kg/L anyway
- ❌ **No negative quantities:** MinValueValidator(0) enforced

**Example:**
```
Purchase: 50.0000 kg flour @ KES 80/kg
Storage: 50.0000 kg (no conversion)
Mix requirement: 5.0000 kg (same unit)
Production: Uses 5.0000 kg (direct deduction)
```

#### **Decision 4: NO Waste Factor**
- ❌ **REJECTED:** Complexity for minimal value
- **Rationale:** Keep it simple. Waste is business reality, not app concern.

#### **Decision 5: Mix Output Logic**
```
Product: Bread
  - Mix produces: 132 packets (FIXED, machine-weighed)
  
Product: Scones
  - Mix produces: 102 packets (FIXED, machine-weighed)
  
Product: KDF (Queen Cakes)
  - Mix produces: 97-107 packets (VARIABLE, hand-cut)
  - Store as: expected_yield=102, allow actual_yield variance
```

**Implementation:**
```python
Mix:
  - product (FK)
  - expected_yield (Decimal, e.g., 132 for bread)
  - is_fixed_yield (Boolean: True for bread/scones, False for KDF)
  
ProductionBatch:
  - expected_yield (from Mix)
  - actual_yield (manual entry, can vary for KDF)
```

#### **Decision 6: Direct vs Indirect Ingredients**
- **Direct ingredients:** Flour, salt, sugar (goes INTO product)
- **Indirect ingredients:** Packaging materials (wraps product)
- **Implementation:** `MixIngredient.ingredient_type` → 'DIRECT' or 'INDIRECT'
- **Deduction logic:** Both types deducted from Inventory during production

---

### 🏭 **PRODUCTION APP - FINAL SPEC**

#### **Decision 1: NO Batch State Complexity**
- ❌ **REJECTED:** PLANNED/IN_PROGRESS/COMPLETED/FAILED states
- ✅ **ADOPTED:** Simple atomic transaction
  - Either production succeeds (ingredients deducted, products added)
  - Or fails (rollback, nothing changes)
- **Rationale:** Atomic transactions solve batch failures. No manual state tracking.

#### **Decision 2: NO Partial Batch Tracking**
- ❌ **REJECTED:** Expected vs actual yield variance tracking
- ✅ **EXCEPTION:** Only for KDF (hand-cut variability)
  - KDF: Allow actual_yield between 97-107
  - Bread/Scones: Fixed yield (132/102), no variance
- **Implementation:** `ProductionBatch.actual_yield` (manual entry)

#### **Decision 3: One Product Per Batch**
- ✅ **ADOPTED:** Option A - One product only
- **Rationale:** Simpler, cleaner. Each batch = one mix = one product type
- **Morning Batch Example:**
  - Batch #1: 132 bread
  - Batch #2: 102 scones
  - Batch #3: ~102 KDF

#### **Decision 4: Cost Calculation Strategy**
- **Mix cost:** NOT stored in Mix (it's just a lookup)
- **Production cost:** Calculated at batch creation time
  - Sum of ingredient costs × quantities (from Inventory weighted avg)
  - Stored in `ProductionBatch.total_cost`
- **Unit cost:** `total_cost / actual_yield` = cost per packet
- **Pricing independence:** Production cost ≠ selling price
  - Selling price in Product model (adjustable by accountant)
  - Profit = selling_price - unit_cost

---

### 📊 **INVENTORY APP - FINAL SPEC**

#### **Decision 1: Weighted Average Costing**
- ✅ **ADOPTED:** Weighted average method
- **Rationale:** Handles price fluctuations without FIFO/LIFO complexity
- **Example:**
  ```
  Week 1: Buy 50kg flour @ KES 4,000/50kg = KES 80/kg
  Week 2: Buy 50kg flour @ KES 4,500/50kg = KES 90/kg
  
  Weighted Avg = (4,000 + 4,500) / 100kg = KES 85/kg
  
  Production uses: KES 85/kg for cost calculation
  ```

#### **Decision 2: Purchase Record Immutability**
- ✅ **Record each purchase AS-IS** (date, quantity, unit_price, total_cost)
- **No modification:** Purchases are historical records (like bank statements)
- **Reporting:** Query purchases to see price trends over time
- **Production costing:** Use current weighted average, not specific purchase price

#### **Decision 3: InventoryItem Fields**
```python
InventoryItem:
  - name (e.g., "Flour", "Sugar", "Baking Powder")
  - unit_of_measure ('g', 'ml' - base units only)
  - item_type ('INGREDIENT', 'PACKAGING')
  - current_stock (Decimal, real-time quantity in grams/ml)
  - weighted_avg_cost (Decimal, auto-calculated on purchase)
  - minimum_stock_level (Decimal, for alerts)
  - current_value (Decimal: stock × weighted_avg_cost)
```

#### **Decision 4: Stock Alerts**
- ✅ **minimum_stock_level** field
- ✅ **Auto-alert** when `current_stock < minimum_stock_level`
- **Implementation:** Background task or view helper shows low-stock warnings

#### **Decision 5: Crates = Inventory Items**
- ✅ **ADOPTED:** Crates are `InventoryItem` (type='PACKAGING')
- ❌ **REJECTED:** Separate Crate model
- **Rationale:** Simpler. Unified stock tracking.
- **Example:**
  ```
  InventoryItem: "Bread Crate"
    - item_type: 'PACKAGING'
    - current_stock: 150 (units)
    - minimum_stock_level: 50
  ```

---

### 💰 **SALES APP - FINAL SPEC**

#### **Decision 1: Two-Step Dispatch (Products → Crates)**
- ✅ **Step 1:** Dispatch products
  1. Select salesperson + product quantities
  2. Call `production_utils.reserve_products_atomic()`
  3. If success, create Dispatch record
  4. Proceed to Step 2

- ✅ **Step 2:** Assign crates (optional, can be added later)
  1. Use Dispatch ID (FK from Step 1)
  2. Call `inventory_utils.reserve_crates_atomic()`
  3. If success, update Dispatch with crate details
  4. If salesperson has own crates, skip this step

- **Atomicity preserved:** Step 2 requires Step 1 success. If Step 1 fails, Step 2 never executes.
- **Flexibility:** Crates can be assigned later (before return is processed)

#### **Decision 2: Return Validation - Value Equivalence**
- ✅ **Formula:** `(quantity_sold × selling_price) + (quantity_returned × selling_price) = total_dispatched × selling_price`
- **Example:**
  ```
  Dispatched: 100 bread @ KES 60 = KES 6,000 total value
  
  Valid Return:
    - Sold: 70 (KES 4,200)
    - Returned: 30 (KES 1,800)
    - Total: KES 6,000 ✅
  
  Invalid Return:
    - Sold: 70 (KES 4,200)
    - Returned: 25 (KES 1,500)
    - Total: KES 5,700 ❌ (Missing 5 bread!)
  ```

#### **Decision 3: Return Access Control**
- **Who can process returns:** Accountant or higher privilege only
- **Salespeople:** View-only access to their dispatch/return records
- **Security:** Prevents salesperson from fudging numbers

#### **Decision 4: Two-Step Returns (Products → Crates)**
- ✅ **Step 1:** Return products
  1. Enter quantity_sold + quantity_returned
  2. Validate: sold + returned = dispatched (value equivalence)
  3. Call `production_utils.return_products_atomic()`
  4. Update ProductReturn record
  5. Products now available for next dispatch

- ✅ **Step 2:** Return crates
  1. Enter crates_returned
  2. Calculate crates_missing (dispatched - returned)
  3. Call `inventory_utils.return_crates_atomic(returned_count)`
  4. Mark missing crates with `is_lost=True`
  5. Close CrateReturn transaction (immutable)

#### **Decision 5: Lost Crate Recovery**
- ❌ **Cannot update closed CrateReturn** (atomicity rule)
- ✅ **Use InventoryAdjustment model** for found crates
  ```python
  InventoryAdjustment:
    - adjustment_type ('FOUND_CRATE', 'DAMAGED', 'STOLEN', 'CORRECTION')
    - inventory_item (FK to crates)
    - quantity (can be positive or negative)
    - reason (TextField)
    - adjusted_by (User FK)
    - created_at
  ```

#### **Decision 6: One Return Per Dispatch**
- ✅ **ADOPTED:** One-time return when dispatch closes
- ❌ **REJECTED:** Multiple partial returns
- **Rationale:** Simpler accounting. Return = transaction close.

#### **Decision 7: Auto-Calculate Missing Quantities**
- ✅ **Products:** `quantity_missing = dispatched - sold - returned`
- ✅ **Crates:** `crates_missing = dispatched - returned`
- **Validation:** Ensures accountability (nothing "disappears")

#### **Decision 8: Cash Variance Tracking**
- ✅ **Track expected vs actual cash**
  ```python
  ProductReturn:
    - cash_collected (manual entry)
    - expected_cash (auto: quantity_sold × selling_price)
    - cash_variance (auto: collected - expected)
    - variance_reason (required if variance != 0)
  ```

---

### 🔧 **GENERAL DECISIONS**

#### **Decision 1: InventoryAdjustment Model**
- ✅ **YES** - Create for manual corrections
- **Use cases:**
  - Found lost crates
  - Damaged inventory write-off
  - Theft reporting
  - Manual stock corrections
- **Audit trail:** Every adjustment logged with user + reason

#### **Decision 2: Utility Function Return Format**
- ✅ **Standardized response:**
  ```python
  {
      'success': bool,
      'data': {},      # Result data if success
      'errors': [],    # Error messages if failed
      'message': str   # Human-readable status
  }
  ```

#### **Decision 3: Cross-App Import Rules**
- ❌ **NEVER import models across apps**
- ✅ **ONLY import utils across apps**
- ✅ **All utils use @transaction.atomic**
- ✅ **All utils use select_for_update()** for row locking
- ✅ **Return dicts, not model instances** (loose coupling)

---

---

## 📋 **SUMMARY: KEY ARCHITECTURAL DECISIONS**

### **Data Mutability Rules:**
| App | CREATE | UPDATE | DELETE | Notes |
|-----|--------|--------|--------|-------|
| **Products** | ✅ | ✅ | ✅ | Only app with full CRUD (recipes/prices adjustable) |
| **Production** | ✅ | ❌ | ❌ | Immutable after batch creation |
| **Inventory** | ✅ | ❌ | ❌ | Immutable after purchase/adjustment |
| **Sales** | ✅ | ❌ | ❌ | Immutable after dispatch/return |
| **Exception** | Returns can UPDATE Production stock & Inventory crates |

---

### **Transaction Atomicity:**
- ✅ **ALL foundation operations** use `@transaction.atomic`
- ✅ **ALL stock updates** use `select_for_update()` (row locking)
- ✅ **Standardized responses:** `{'success': bool, 'data': {}, 'errors': [], 'message': str}`
- ✅ **Audit logging:** Every utility logs `requested_by_app` and `requested_by_user`

---

### **Cross-App Communication:**
- ❌ **NEVER import models** across apps
- ✅ **ONLY import utils** across apps
- ✅ **Validate before write** (prevention-first)
- ✅ **Return dicts, not instances** (loose coupling)

**Example:**
```python
# ✅ CORRECT
from apps.inventory import utils as inventory_utils
result = inventory_utils.deduct_ingredients_atomic(...)

# ❌ WRONG
from apps.inventory.models import InventoryItem
item = InventoryItem.objects.get(...)
```

---

### **Unit Standardization:**
- ✅ **Standard units:** Kilograms (kg), Liters (L), units (countable items)
- ✅ **Decimal precision:** 4 decimal places (max_digits=10, decimal_places=4)
- ✅ **No conversions:** Purchases, storage, production, sales all use same units
- ✅ **No negatives:** MinValueValidator(0) on all quantity fields
- ✅ **User tracking:** created_by, updated_by (where applicable) on all mutable models

---

### **Costing Strategy:**
- ✅ **Weighted Average:** Handles price fluctuations
- ✅ **Purchase immutability:** Historical records never modified
- ✅ **Production cost:** Calculated at batch time (from current weighted avg)
- ✅ **Selling price:** Independent, adjustable by accountant
- ✅ **Profit tracking:** `selling_price - unit_cost = profit_per_unit`

---

### **Security & Validation:**

**Who Can Do What:**
| Action | Role Required | Validation |
|--------|---------------|------------|
| Create Product | PRODUCT_MANAGER+ | Name unique, price > 0 |
| Update Price | ACCOUNTANT+ | Price > 0, logged |
| Create Mix | PRODUCT_MANAGER+ | Ingredients exist in Inventory |
| Create Batch | PRODUCT_MANAGER+ | Ingredients available, row locks |
| Create Purchase | ACCOUNTANT+ | Quantities > 0, weighted avg recalc |
| Create Dispatch | ACCOUNTANT+ | Products available, row locks |
| Assign Crates | ACCOUNTANT+ | Crates available, dispatch not closed |
| Process Return | ACCOUNTANT+ | Value equivalence, cash variance check |
| Adjust Inventory | ADMIN+ | Reason required, logged |

**Value Equivalence Formula:**
```
(quantity_sold × selling_price) + (quantity_returned × selling_price) = (quantity_dispatched × selling_price)

Example:
  Dispatched: 100 bread @ KES 60 = KES 6,000
  Sold: 70 @ KES 60 = KES 4,200
  Returned: 30 @ KES 60 = KES 1,800
  Total: KES 6,000 ✅
  
  If sold=70, returned=25:
  Total: KES 5,700 ❌ (Missing 5 bread!)
```

---

### **Race Condition Prevention:**

**Pattern:**
```python
@transaction.atomic
def modify_stock_atomic(...):
    # Lock row FIRST (blocks other transactions)
    item = InventoryItem.objects.select_for_update().get(id=item_id)
    
    # Validate SECOND (check constraints)
    if item.current_stock < requested_quantity:
        raise InsufficientStockError
    
    # Modify THIRD (all-or-nothing)
    item.current_stock -= requested_quantity
    item.save()
    
    # Transaction commits → row unlocked
```

**Queued Requests:**
```
Request A: Locks Flour → Deducts 5000g → Unlocks
Request B: Waits... → Gets lock → Deducts 3000g → Unlocks
Request C: Waits... → Gets lock → Validates → ERROR (insufficient) → Rollback
```

---

## 🚀 **NEXT STEPS: IMPLEMENTATION ROADMAP**

### **Phase 1: Models & Migrations** (No Code Yet)
1. Review this document one final time
2. Address any remaining questions/concerns
3. Create detailed field specifications (next document)
4. Define migration sequence

### **Phase 2: Foundation Apps (Sequential)**
1. **Products** (standalone, no dependencies)
2. **Inventory** (standalone, no dependencies)
3. **Production** (depends on Products + Inventory utils)
4. **Sales** (depends on Production + Inventory utils)

### **Phase 3: Utility Functions**
1. Products utils (create/update product, mix)
2. Inventory utils (purchase, deduct, return, adjust)
3. Production utils (create batch, deduct products, return products)
4. Sales utils (dispatch, assign crates, process return)

### **Phase 4: Views & Forms**
1. Product management (CRUD)
2. Purchase entry (immutable)
3. Production batch creation (atomic)
4. Dispatch/return processing (atomic)

### **Phase 5: Testing & Validation**
1. Unit tests (each utility function)
2. Integration tests (cross-app flows)
3. Race condition tests (concurrent requests)
4. Edge case tests (insufficient stock, invalid data)

---

## ❓ **FINAL CHECKLIST - READY FOR BLUEPRINT?**

**Answer YES/NO to proceed:**

### **Architecture:**
- [ ] App ownership principle clear?
- [ ] Atomic transaction strategy understood?
- [ ] Immutability rules accepted? (Products editable, rest CREATE-only)
- [ ] Cross-app communication via utils only?

### **Models:**
- [ ] Product sub-product structure makes sense?
- [ ] Mix without versioning acceptable?
- [ ] Production batch fields sufficient?
- [ ] Inventory weighted average costing clear?
- [ ] Sales two-step dispatch/return logical?

### **Security:**
- [ ] Row locking strategy prevents race conditions?
- [ ] Value equivalence prevents salesperson fraud?
- [ ] Accountant-only return processing sufficient?
- [ ] Audit logging captures enough detail?

### **Edge Cases:**
- [ ] Lost crates recovery via InventoryAdjustment acceptable?
- [ ] KDF variable yield (97-107) handled correctly?
- [ ] Concurrent production batches won't conflict?
- [ ] Dispatch without crates (added later) makes sense?

---

**If all YES → I will create the detailed technical blueprint with:**
1. Exact model field definitions (types, constraints, indexes)
2. Full utility function specifications (parameters, logic, errors)
3. Database migration sequence
4. View/form requirements
5. Test cases

**If any NO → Let's discuss and refine before proceeding.**

---

**Status:** ⏳ Awaiting your final confirmation to proceed to Blueprint Phase