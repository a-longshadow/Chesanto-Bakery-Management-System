# 🎯 STOCK CALCULATION ARCHITECTURE
**Date:** November 12, 2025  
**Purpose:** Complete explanation of real-time stock calculation  
**Principle:** CALCULATED QUERIES (not stored counters)

---

## 📊 THE FUNDAMENTAL PRINCIPLE

### **NEVER Store Aggregated Stock - ALWAYS Calculate It**

```python
# ❌ BAD: Stored counter (gets out of sync)
Product.available_stock = 500  # What if someone forgot to update this?

# ✅ GOOD: Calculated query (always accurate)
available_stock = (
    DailyProduction.objects.aggregate(Sum('bread_produced'))['bread_produced__sum'] -
    Dispatch.objects.filter(deleted_at__isnull=True).aggregate(Sum('bread_qty'))['bread_qty__sum'] +
    DailyProduction.objects.aggregate(Sum('bread_returned'))['bread_returned__sum']
)
```

**Why This Works:**
- ✅ Single source of truth (actual transactions)
- ✅ No sync issues (calculation is real-time)
- ✅ Audit trail preserved (every transaction recorded)
- ✅ No race conditions (SELECT queries don't lock)
- ✅ Handles all scenarios automatically

---

## 🍞 PRODUCT STOCK FLOW (Bread Example)

### **Scenario Timeline:**

```
NOV 10: Production makes 500 bread
NOV 11: Production makes 300 bread
NOV 11: Sales dispatches 400 bread to John
NOV 12: John returns 50 bread unsold
NOV 12: Production makes 200 bread
NOV 12: Sales dispatches 450 bread to Mary
NOV 12: Mary returns 100 bread unsold
```

### **Database State:**

#### **Table: `production.DailyProduction`**
```sql
| id | date       | bread_produced | bread_returned |
|----|------------|----------------|----------------|
| 1  | 2025-11-10 | 500            | 0              |
| 2  | 2025-11-11 | 300            | 0              |
| 3  | 2025-11-12 | 200            | 150            | ← 50 + 100 from returns
```

#### **Table: `sales.Dispatch`**
```sql
| id | dispatch_number       | salesperson | date       | bread_qty | is_returned | deleted_at |
|----|-----------------------|-------------|------------|-----------|-------------|------------|
| 1  | DSP-20251111-JOHN-001 | John        | 2025-11-11 | 400       | TRUE        | NULL       |
| 2  | DSP-20251112-MARY-001 | Mary        | 2025-11-12 | 450       | TRUE        | NULL       |
```

#### **Table: `sales.SalesReturn`** (Records the SOLD amounts)
```sql
| id | dispatch_id | bread_sold | bread_returned | bread_revenue |
|----|-------------|------------|----------------|---------------|
| 1  | 1           | 350        | 50             | 17500.00      |
| 2  | 2           | 350        | 100            | 17500.00      |
```

---

### **QUERY: Available Stock for Dispatch (Nov 12, 10 PM)**

```python
from django.db.models import Sum
from datetime import date

def get_available_stock(product_field='bread', up_to_date=None):
    """
    Calculate available stock using REAL-TIME query.
    
    Formula:
        Available = PRODUCED - DISPATCHED + RETURNED
    
    Where:
        PRODUCED = Sum of all DailyProduction.{product}_produced up to date
        DISPATCHED = Sum of active Dispatch.{product}_qty up to date
        RETURNED = Sum of all DailyProduction.{product}_returned up to date
    """
    if up_to_date is None:
        up_to_date = date.today()
    
    # STEP 1: Total produced up to date
    produced = DailyProduction.objects.filter(
        date__lte=up_to_date
    ).aggregate(
        total=Sum(f'{product_field}_produced')
    )['total'] or 0
    
    # STEP 2: Total dispatched (active only, not deleted or soft-deleted)
    dispatched = Dispatch.objects.filter(
        dispatch_date__lte=up_to_date,
        deleted_at__isnull=True  # ← Excludes soft-deleted dispatches
    ).aggregate(
        total=Sum(f'{product_field}_qty')
    )['total'] or 0
    
    # STEP 3: Total returned from sales
    returned = DailyProduction.objects.filter(
        date__lte=up_to_date
    ).aggregate(
        total=Sum(f'{product_field}_returned')
    )['total'] or 0
    
    # STEP 4: Calculate available
    available = produced - dispatched + returned
    
    return available


# USAGE IN CREATE DISPATCH VIEW:
available_bread = get_available_stock('bread', up_to_date=request.POST.get('dispatch_date'))
# Result: 500 + 300 + 200 - 400 - 450 + 150 = 300 bread available
```

---

### **STEP-BY-STEP WALKTHROUGH:**

#### **1️⃣ NOV 10: Production Makes 500 Bread**

```python
# Production creates batch
daily_prod = DailyProduction.objects.create(
    date='2025-11-10',
    bread_produced=500
)

# Query available stock
available = get_available_stock('bread', up_to_date='2025-11-10')
# Calculation:
#   Produced: 500
#   Dispatched: 0
#   Returned: 0
#   Available: 500 - 0 + 0 = 500 ✅
```

---

#### **2️⃣ NOV 11: Production Makes 300 More**

```python
daily_prod = DailyProduction.objects.create(
    date='2025-11-11',
    bread_produced=300
)

available = get_available_stock('bread', up_to_date='2025-11-11')
# Calculation:
#   Produced: 500 + 300 = 800
#   Dispatched: 0
#   Returned: 0
#   Available: 800 - 0 + 0 = 800 ✅
```

---

#### **3️⃣ NOV 11: Sales Dispatches 400 to John**

```python
dispatch = Dispatch.objects.create(
    dispatch_number='DSP-20251111-JOHN-001',
    salesperson=john,
    dispatch_date='2025-11-11',
    bread_qty=400
)

# NO UPDATE TO PRODUCTION TABLE!
# Query automatically adjusts:

available = get_available_stock('bread', up_to_date='2025-11-11')
# Calculation:
#   Produced: 800
#   Dispatched: 400  ← New dispatch counted
#   Returned: 0
#   Available: 800 - 400 + 0 = 400 ✅
```

---

#### **4️⃣ NOV 12: John Returns 50 Bread Unsold**

```python
# ATOMIC TRANSACTION:
with transaction.atomic():
    # Step 1: Record the return in SalesReturn
    sales_return = SalesReturn.objects.create(
        dispatch=dispatch,
        bread_sold=350,
        bread_returned=50,
        bread_revenue=Decimal('17500.00')
    )
    
    # Step 2: Mark dispatch as returned
    dispatch.is_returned = True
    dispatch.save()
    
    # Step 3: ADD returned products to DailyProduction
    daily_prod, created = DailyProduction.objects.select_for_update().get_or_create(
        date='2025-11-12',
        defaults={'bread_produced': 0, 'bread_returned': 0}
    )
    daily_prod.bread_returned += 50  # ← This is the KEY!
    daily_prod.save()

# Query available stock (Nov 12):
available = get_available_stock('bread', up_to_date='2025-11-12')
# Calculation:
#   Produced: 800 (Nov 10 + Nov 11)
#   Dispatched: 400 (John's dispatch still counts)
#   Returned: 50  ← NEW! Added to calculation
#   Available: 800 - 400 + 50 = 450 ✅
```

**🔑 KEY INSIGHT:** 
- Dispatch stays at 400 (historical record)
- Return adds to `bread_returned` field
- Query calculates: Available = Produced - Dispatched + **Returned**
- No double-counting because we're tracking FLOWS not STOCK!

---

#### **5️⃣ NOV 12: Production Makes 200 More**

```python
# Add to existing Nov 12 DailyProduction
daily_prod = DailyProduction.objects.get(date='2025-11-12')
daily_prod.bread_produced += 200  # Now: 0 + 200 = 200
daily_prod.save()

available = get_available_stock('bread', up_to_date='2025-11-12')
# Calculation:
#   Produced: 800 + 200 = 1000  ← Includes new batch!
#   Dispatched: 400
#   Returned: 50
#   Available: 1000 - 400 + 50 = 650 ✅
```

---

#### **6️⃣ NOV 12: Sales Dispatches 450 to Mary**

```python
dispatch2 = Dispatch.objects.create(
    dispatch_number='DSP-20251112-MARY-001',
    salesperson=mary,
    dispatch_date='2025-11-12',
    bread_qty=450
)

available = get_available_stock('bread', up_to_date='2025-11-12')
# Calculation:
#   Produced: 1000
#   Dispatched: 400 + 450 = 850  ← Mary's dispatch added
#   Returned: 50
#   Available: 1000 - 850 + 50 = 200 ✅
```

---

#### **7️⃣ NOV 12: Mary Returns 100 Bread**

```python
with transaction.atomic():
    SalesReturn.objects.create(
        dispatch=dispatch2,
        bread_sold=350,
        bread_returned=100,
        bread_revenue=Decimal('17500.00')
    )
    
    dispatch2.is_returned = True
    dispatch2.save()
    
    # Add to SAME DailyProduction record
    daily_prod = DailyProduction.objects.select_for_update().get(date='2025-11-12')
    daily_prod.bread_returned += 100  # Was 50, now 150
    daily_prod.save()

available = get_available_stock('bread', up_to_date='2025-11-12')
# Calculation:
#   Produced: 1000
#   Dispatched: 850
#   Returned: 50 + 100 = 150  ← Both returns counted!
#   Available: 1000 - 850 + 150 = 300 ✅
```

---

## 🎯 PREVENTING DOUBLE-COUNTING

### **Problem Scenario:**
```
What if we accidentally process John's return twice?
```

### **Solution 1: `is_returned` Flag (Simple)**
```python
# In return view:
if dispatch.is_returned:
    return JsonResponse({
        'error': 'Dispatch already returned on {dispatch.return_date}'
    }, status=400)

# Only allow return if is_returned == False
dispatch.is_returned = True  # ← Locks the dispatch
dispatch.return_date = date.today()
dispatch.save()
```

### **Solution 2: Check SalesReturn Existence (Robust)**
```python
# In return view:
if SalesReturn.objects.filter(dispatch=dispatch).exists():
    return JsonResponse({
        'error': 'Sales return record already exists for this dispatch'
    }, status=400)

# Only create if doesn't exist
SalesReturn.objects.create(dispatch=dispatch, ...)
```

### **Solution 3: Database Constraint (Bulletproof)**
```python
# In SalesReturn model:
class SalesReturn(models.Model):
    dispatch = models.OneToOneField(
        Dispatch,
        on_delete=models.CASCADE,
        related_name='sales_return'  # ← OneToOne enforces single return
    )
    # ... other fields

# Attempting second return:
try:
    SalesReturn.objects.create(dispatch=dispatch, ...)
except IntegrityError:
    # Database rejects duplicate!
    return JsonResponse({'error': 'Return already processed'}, status=400)
```

**✅ RECOMMENDED: Use all three layers (belt + suspenders + duct tape)**

---

## 📦 CRATE STOCK FLOW

### **Same Principle: FLOWS not COUNTERS**

#### **Database State:**

**Table: `inventory.CrateStock`** (Single row - this is a COUNTER model)
```sql
| id | available_crates | dispatched_crates | damaged_crates |
|----|------------------|-------------------|----------------|
| 1  | 50               | 30                | 5              |
```

**Table: `inventory.CrateMovement`** (Audit trail)
```sql
| id | movement_type     | quantity | reference_id | created_at |
|----|-------------------|----------|--------------|------------|
| 1  | PURCHASE_IN       | 100      | NULL         | Nov 1      |
| 2  | DISPATCH_OUT      | 25       | dispatch_1   | Nov 11     |
| 3  | DISPATCH_OUT      | 5        | dispatch_2   | Nov 12     |
| 4  | DISPATCH_RETURN   | 10       | dispatch_1   | Nov 12     |
```

---

### **CRATE OPERATIONS:**

#### **1️⃣ Dispatch Crates (Lock + Deduct)**
```python
@transaction.atomic
def dispatch_crates_atomic(quantity, dispatch_id, user=None):
    """
    Dispatch crates with row locking to prevent race conditions.
    """
    # CRITICAL: select_for_update() locks the row
    crate_stock = CrateStock.objects.select_for_update().get(pk=1)
    
    # Validate
    if quantity > crate_stock.available_crates:
        return None, f"Insufficient crates: need {quantity}, have {crate_stock.available_crates}"
    
    # Update (atomic within transaction)
    crate_stock.available_crates -= quantity
    crate_stock.dispatched_crates += quantity
    crate_stock.save()
    
    # Audit trail
    CrateMovement.objects.create(
        crate_stock=crate_stock,
        movement_type='DISPATCH_OUT',
        quantity=quantity,
        reference_id=dispatch_id,
        created_by=user
    )
    
    return crate_stock, None


# USAGE IN SALES VIEW:
crate_stock, error = dispatch_crates_atomic(
    quantity=25,
    dispatch_id=dispatch.id,
    user=request.user
)

if error:
    # Rollback entire transaction
    raise ValidationError(error)
```

---

#### **2️⃣ Return Crates (Lock + Add)**
```python
@transaction.atomic
def return_crates_atomic(quantity, dispatch_id, user=None):
    """
    Return crates from sales.
    """
    crate_stock = CrateStock.objects.select_for_update().get(pk=1)
    
    # Validate
    if quantity > crate_stock.dispatched_crates:
        return None, f"Cannot return {quantity}: only {crate_stock.dispatched_crates} dispatched"
    
    # Update
    crate_stock.dispatched_crates -= quantity
    crate_stock.available_crates += quantity
    crate_stock.save()
    
    # Audit trail
    CrateMovement.objects.create(
        crate_stock=crate_stock,
        movement_type='DISPATCH_RETURN',
        quantity=quantity,
        reference_id=dispatch_id,
        created_by=user
    )
    
    return crate_stock, None
```

---

#### **3️⃣ Prevent Crate Double-Return**

**Same as Products: Multiple Safety Layers**

```python
# In return view:

# Layer 1: Check if already returned
dispatch = get_object_or_404(Dispatch, pk=dispatch_id)
if dispatch.is_returned:
    return JsonResponse({'error': 'Crates already returned'}, status=400)

# Layer 2: Check audit trail
existing_return = CrateMovement.objects.filter(
    movement_type='DISPATCH_RETURN',
    reference_id=dispatch.id
).exists()

if existing_return:
    return JsonResponse({'error': 'Crate return already recorded'}, status=400)

# Layer 3: Atomic transaction with validation
with transaction.atomic():
    crate_stock, error = return_crates_atomic(
        quantity=dispatch.crates_dispatched,
        dispatch_id=dispatch.id,
        user=request.user
    )
    
    if error:
        # Transaction rolls back
        return JsonResponse({'error': error}, status=400)
    
    # Mark dispatch as returned (locks it)
    dispatch.is_returned = True
    dispatch.crates_returned = dispatch.crates_dispatched
    dispatch.save()
```

---

## 🔄 AFTER ADDING NEW PRODUCTION MIX

### **Question:** How do we update available stock when new batch is produced?

### **Answer:** WE DON'T! The query does it automatically.

#### **Example:**

**Before New Batch (Nov 13, 9 AM):**
```python
available = get_available_stock('bread', up_to_date='2025-11-13')
# Produced: 1000 (Nov 10-12)
# Dispatched: 850
# Returned: 150
# Available: 300
```

**Production Creates New Batch (Nov 13, 10 AM):**
```python
# Create new batch (uses utility function from refactored Production)
batch, error = create_production_batch_atomic(
    daily_production=daily_prod_nov13,
    mix=bread_mix,
    quantity_produced=500,
    user=baker_user
)

# Internally, this does:
# 1. Deduct ingredients from inventory (atomic)
# 2. Create ProductionBatch record
# 3. UPDATE DailyProduction.bread_produced += 500
```

**After New Batch (Nov 13, 10:01 AM):**
```python
available = get_available_stock('bread', up_to_date='2025-11-13')
# Produced: 1000 + 500 = 1500  ← Query sees new batch!
# Dispatched: 850
# Returned: 150
# Available: 1500 - 850 + 150 = 800  ✅ Automatically updated!
```

**🔑 KEY:** No manual stock update needed. The query aggregates ALL `DailyProduction.bread_produced` records, so new batches are automatically included.

---

## 🛡️ RACE CONDITION PREVENTION

### **Scenario: Two Users Dispatch Simultaneously**

**WITHOUT Locking (BAD):**
```python
# User A reads available: 300
available = get_available_stock('bread')  # 300

# User B reads available: 300 (same time)
available = get_available_stock('bread')  # 300

# User A dispatches 200
Dispatch.objects.create(bread_qty=200)  # OK

# User B dispatches 200
Dispatch.objects.create(bread_qty=200)  # OK (but shouldn't be!)

# Result: 400 dispatched, only 300 available! ❌
```

**WITH Locking (GOOD):**
```python
# In dispatch view:
@transaction.atomic
def create_dispatch(request):
    # ... form validation ...
    
    # CRITICAL: Lock stock calculation
    # Lock DailyProduction rows (prevents concurrent production)
    DailyProduction.objects.select_for_update().filter(
        date__lte=dispatch_date
    ).exists()
    
    # Lock Dispatch rows (prevents concurrent dispatches)
    Dispatch.objects.select_for_update().filter(
        dispatch_date__lte=dispatch_date,
        deleted_at__isnull=True
    ).exists()
    
    # NOW calculate (rows locked, accurate count)
    available = get_available_stock('bread', up_to_date=dispatch_date)
    
    # Validate
    if bread_qty > available:
        raise ValidationError(f"Insufficient stock: need {bread_qty}, have {available}")
    
    # Create (still in transaction, locks held)
    dispatch = Dispatch.objects.create(
        bread_qty=bread_qty,
        # ...
    )
    
    # Transaction commits, locks released
    return JsonResponse({'success': True, 'dispatch_id': dispatch.id})
```

**Timeline:**
```
10:00:00.000 - User A starts transaction (locks acquired)
10:00:00.005 - User A calculates available: 300
10:00:00.010 - User B starts transaction (WAITS for User A's locks)
10:00:00.015 - User A validates bread_qty=200 <= 300 ✅
10:00:00.020 - User A creates dispatch
10:00:00.025 - User A commits (locks released)
10:00:00.030 - User B's locks acquired
10:00:00.035 - User B calculates available: 100 (sees User A's dispatch!)
10:00:00.040 - User B validates bread_qty=200 <= 100 ❌
10:00:00.045 - User B gets error: "Insufficient stock"
10:00:00.050 - User B transaction rolls back

Result: Only 200 dispatched ✅
```

---

## 📋 COMPLETE UTILITY FUNCTION (Production)

```python
# apps/production/utils.py

from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
from datetime import date


def get_available_stock(product_field, up_to_date=None):
    """
    Calculate available stock for a product using real-time query.
    
    Args:
        product_field: 'bread', 'kdf', or 'scones'
        up_to_date: Calculate up to this date (default: today)
    
    Returns:
        Decimal: Available quantity (can be negative if oversold)
    
    Formula:
        Available = PRODUCED - DISPATCHED + RETURNED
    
    Example:
        >>> get_available_stock('bread', up_to_date=date(2025, 11, 12))
        Decimal('300')
    """
    from .models import DailyProduction
    from apps.sales.models import Dispatch
    
    if up_to_date is None:
        up_to_date = date.today()
    
    # Total produced
    produced = DailyProduction.objects.filter(
        date__lte=up_to_date
    ).aggregate(
        total=Sum(f'{product_field}_produced')
    )['total'] or 0
    
    # Total dispatched (active only)
    dispatched = Dispatch.objects.filter(
        dispatch_date__lte=up_to_date,
        deleted_at__isnull=True  # Exclude soft-deleted
    ).aggregate(
        total=Sum(f'{product_field}_qty')
    )['total'] or 0
    
    # Total returned
    returned = DailyProduction.objects.filter(
        date__lte=up_to_date
    ).aggregate(
        total=Sum(f'{product_field}_returned')
    )['total'] or 0
    
    available = Decimal(str(produced)) - Decimal(str(dispatched)) + Decimal(str(returned))
    
    return available


@transaction.atomic
def add_returned_products(return_date, bread=0, kdf=0, scones=0, user=None):
    """
    Add returned products from sales to DailyProduction.
    
    This is the ONLY place Sales writes to Production.
    Uses F() expressions to prevent race conditions.
    
    Args:
        return_date: Date of the return
        bread: Quantity of bread returned
        kdf: Quantity of KDF returned
        scones: Quantity of scones returned
        user: User performing the return
    
    Returns:
        DailyProduction instance (refreshed with actual values)
    
    Example:
        >>> daily_prod = add_returned_products(
        ...     return_date=date.today(),
        ...     bread=50,
        ...     kdf=10,
        ...     scones=20,
        ...     user=request.user
        ... )
        >>> print(daily_prod.bread_returned)
        150  # Was 100, now 150
    """
    from django.db.models import F
    from .models import DailyProduction
    
    # Get or create DailyProduction for return date (with lock)
    daily_prod, created = DailyProduction.objects.select_for_update().get_or_create(
        date=return_date,
        defaults={
            'created_by': user,
            'bread_produced': 0,
            'kdf_produced': 0,
            'scones_produced': 0,
            'bread_returned': 0,
            'kdf_returned': 0,
            'scones_returned': 0
        }
    )
    
    # Use F() expressions to avoid read-modify-write race conditions
    if bread > 0:
        daily_prod.bread_returned = F('bread_returned') + bread
    if kdf > 0:
        daily_prod.kdf_returned = F('kdf_returned') + kdf
    if scones > 0:
        daily_prod.scones_returned = F('scones_returned') + scones
    
    daily_prod.updated_by = user
    daily_prod.save()
    
    # Refresh to get actual values (F() expressions need refresh)
    daily_prod.refresh_from_db()
    
    return daily_prod
```

---

## 🔌 API ARCHITECTURE

### **Production App Utility Functions** (`apps/production/utils.py`)

```python
def get_available_stock(product_field, up_to_date=None):
    """
    Read-only query. No side effects.
    Returns: Decimal (available quantity)
    """

@transaction.atomic
def add_returned_products(return_date, bread=0, kdf=0, scones=0, user=None):
    """
    Write API for Sales returns.
    Returns: DailyProduction instance
    Raises: ValidationError on failure
    """
```

### **Inventory App Utility Functions** (`apps/inventory/utils.py`)

```python
@transaction.atomic
def dispatch_crates_atomic(quantity, dispatch_id, user=None):
    """
    Dispatch crates with locking.
    Returns: (CrateStock, error_msg) or (None, error_msg)
    """

@transaction.atomic
def return_crates_atomic(quantity, dispatch_id, user=None):
    """
    Return crates with locking.
    Returns: (CrateStock, error_msg) or (None, error_msg)
    """

def get_available_crates():
    """
    Read-only query.
    Returns: int (available crates)
    """
```

### **Error Handling Pattern**

```python
# In Sales views:
try:
    with transaction.atomic():
        # Call Production API
        daily_prod = add_returned_products(
            return_date=date.today(),
            bread=50,
            user=request.user
        )
        
        # Call Inventory API
        crate_stock, error = return_crates_atomic(
            quantity=20,
            dispatch_id=dispatch.id,
            user=request.user
        )
        
        if error:
            raise ValidationError(error)
        
        # Update Sales records
        dispatch.is_returned = True
        dispatch.save()
        
except ValidationError as e:
    return JsonResponse({'success': False, 'error': str(e)}, status=400)
except IntegrityError:
    return JsonResponse({'success': False, 'error': 'Duplicate return detected'}, status=400)
except Exception as e:
    logger.error(f"Return failed: {e}", exc_info=True)
    return JsonResponse({'success': False, 'error': 'System error'}, status=500)
```

---

## ✅ SUMMARY

### **API Boundaries:**
- ✅ **Production exposes:** `get_available_stock()`, `add_returned_products()`
- ✅ **Inventory exposes:** `dispatch_crates_atomic()`, `return_crates_atomic()`, `get_available_crates()`
- ✅ **Sales calls:** APIs only (no direct model writes to other apps)
- ✅ **Error handling:** Try-catch blocks, atomic transactions, detailed logging
- ✅ **Validation:** Inside utility functions (centralized control)

### **Products:**
1. ✅ **Formula:** `Available = Produced - Dispatched + Returned`
2. ✅ **Production writes:** `bread_produced`, `bread_returned`
3. ✅ **Sales writes:** `bread_qty` in Dispatch
4. ✅ **Returns:** Via `add_returned_products()` API
5. ✅ **Prevent double-return:** `is_returned` flag + OneToOne constraint
6. ✅ **New production auto-available:** Query aggregates all records
7. ✅ **Race prevention:** `select_for_update()` in dispatch view

### **Crates:**
1. ✅ **Single row:** `CrateStock`
2. ✅ **Dispatch:** Via `dispatch_crates_atomic()` API
3. ✅ **Return:** Via `return_crates_atomic()` API
4. ✅ **Prevent double-return:** Flag + audit trail
5. ✅ **Row locking:** All operations use `select_for_update()`
6. ✅ **Audit trail:** `CrateMovement` records every change

### **Guarantees:**
- 🎯 Single source of truth (transaction records)
- 🔒 No race conditions (row locking)
- 🚫 No double-counting (validation + constraints)
- 📊 Always accurate (calculated queries)
- 🔍 Complete audit trail (every transaction logged)
- ⚡ Automatic updates (no manual sync)
- 🛡️ Loose coupling (clear API boundaries)
