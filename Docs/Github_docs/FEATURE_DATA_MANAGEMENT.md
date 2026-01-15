# Feature: Data Management & Reset Capability

## Problem Statement

The Chesanto Bakery Management System has three tightly interconnected apps:
- **Inventory** → tracks raw material purchases and stock
- **Production** → consumes inventory to produce finished goods (bread, KDF, scones, etc.)
- **Sales** → dispatches finished goods to salesmen, processes returns

Currently, there is **no mechanism to correct or delete erroneous data**. Human error during data entry (wrong quantities, prices, etc.) cascades through the system, corrupting:
- Inventory balances
- Production costs
- Finished goods stock
- Sales dispatches
- P&L calculations
- Commission calculations

## Data Flow & Dependencies

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DATA DEPENDENCY CHAIN                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  INVENTORY              PRODUCTION                 SALES                 │
│  ─────────              ──────────                 ─────                 │
│                                                                          │
│  ItemXXPurchases ──────► ProductionBatch ────────► SalesDispatch ──────► SalesReturn
│       │                       │                        │                     │
│       ▼                       ▼                        ▼                     ▼
│  ItemXXDetails           ProductStock            ProductStock          ProductStock
│  .current_stock          .current_stock          .current_stock        .current_stock
│                          (INCREASED)             (DECREASED)           (Leftovers +)
│                               │                        │
│                               ▼                        ▼
│                     ProductStockMovement      ProductStockMovement
│                          (PRODUCTION)              (DISPATCH)
│       │
│       ▼
│  BatchIngredientDeduction ◄── (links batch to inventory items deducted)
│  (reduces ItemXXDetails.current_stock)
│
│  Item16CratesDetails ◄─────────────────────── SalesDispatch.crates_dispatched
│  (crate inventory)                            (deducted on dispatch,
│       │                                        returned on SalesReturn)
│       ▼
│  Item16CratesOutputs (audit record on dispatch)
│  Item16CratesPurchases (audit record on return, price=0)
│
└─────────────────────────────────────────────────────────────────────────┘

DEPENDENCY RULE:
  - SalesReturn depends on SalesDispatch (FK relationship)
  - SalesDispatch depends on ProductionBatch (temporal: can't dispatch before production)
  - ProductionBatch depends on ItemXXPurchases (temporal: can't produce before purchasing)
  
DELETE ORDER (reverse of creation):
  - SalesReturn → NEVER (immutable financial record)
  - SalesDispatch → only if no SalesReturn exists for it
  - ProductionBatch → only if no SalesDispatch exists after it
  - ItemXXPurchases → only if no ProductionBatch exists after it
```

## Proposed Solution

### Core Principle: Datetime-Strict Dependency Checking

Since the system uses **running balances** (not lot-tracking), we cannot trace which specific purchase was consumed by which batch. Therefore, we use **temporal ordering** as the dependency rule:

> **A record can only be deleted if NO downstream records exist with a timestamp AFTER it.**

This is enforced at the **datetime level** (not just date):
- Precision: seconds matter
- If a batch was created even 1 second after a purchase, that purchase is locked
- **The delete button is HIDDEN** (not disabled) when dependencies exist
- Users cannot even attempt a delete that would be blocked

```
TEMPORAL DEPENDENCY CHAIN
─────────────────────────
Purchase (10:00:00) ──► Batch (10:05:00) ──► Dispatch (11:00:00) ──► Return (14:00:00)

DEPENDENCY TYPE BY RELATIONSHIP:
─────────────────────────────────

┌─────────────────┬────────────────────┬─────────────────────────────────────────┐
│ Source          │ Target             │ Dependency Type                         │
├─────────────────┼────────────────────┼─────────────────────────────────────────┤
│ ItemXXPurchases │ ProductionBatch    │ TEMPORAL (created_at comparison)        │
│                 │                    │ Reason: No FK, running balance system   │
├─────────────────┼────────────────────┼─────────────────────────────────────────┤
│ ProductionBatch │ SalesDispatch      │ TEMPORAL (created_at comparison)        │
│                 │                    │ Reason: No FK, running balance system   │
├─────────────────┼────────────────────┼─────────────────────────────────────────┤
│ SalesDispatch   │ SalesReturn        │ FK (dispatch_id foreign key)            │
│                 │                    │ Reason: OneToOne relationship exists    │
└─────────────────┴────────────────────┴─────────────────────────────────────────┘

TEMPORAL CHECKS (Inventory & Production):
  - Purchase delete: Any ProductionBatch.created_at > purchase.created_at? → BLOCKED
  - Batch delete: Any SalesDispatch.created_at > batch.created_at? → BLOCKED

FK CHECK (Sales):
  - Dispatch delete: Any SalesReturn with dispatch_id = this dispatch? → BLOCKED

To delete the Purchase:
  Query: Any ProductionBatch.created_at > 10:00:00? → YES (10:05:00) → BLOCKED

To delete the Batch:
  Query: Any SalesDispatch.created_at > 10:05:00? → YES (11:00:00) → BLOCKED

To delete the Dispatch:
  Query: Any SalesReturn with dispatch_id = this dispatch? → YES → BLOCKED
  (Note: This is FK check, not temporal - Return has FK to Dispatch)

To delete the Return:
  → NEVER ALLOWED. Returns are immutable financial records.
  → Commission already recorded, P&L already affected, reports already sent.
  → The ONLY way to undo a return is Full System Reset.
```

### Why Temporal Ordering (Not Lot Tracking)?

**Important:** The temporal rule is **intentionally conservative**. We don't track which specific purchase was consumed by which batch (lot tracking would require significant database redesign). Instead:

- If ANY production activity happened after a purchase, we assume it MIGHT have consumed that purchase
- This means some purchases may be "locked" even if they weren't actually consumed
- This is a **safe default** - we'd rather block a valid delete than allow an invalid one

```
EXAMPLE: Conservative Blocking

Purchase P1 (100kg @ 10:00) - locked even if unused
Purchase P2 (100kg @ 10:30) - locked even if unused  
Batch B1 (uses 100kg @ 11:00) - consumed from P1? P2? Both? Unknown.

→ NEITHER P1 nor P2 can be deleted while B1 exists
→ User must delete B1 first, then either purchase
→ Order of purchase deletion doesn't matter once B1 is gone
```

**Implication for users:** To delete a purchase, you must first delete ALL batches created after it. This may feel restrictive, but it guarantees data integrity.

### Part 1: Individual Record Delete (Dependency-Aware)

Delete individual records **only if nothing downstream depends on them**. 

**Enforcement Strategy:**

| Layer | Behavior |
|-------|----------|
| **UI** | Delete button HIDDEN when dependencies exist |
| **Backend** | View validates dependencies before delete |
| **On Block** | See "Blocked Delete UX Options" below |

---

#### Blocked Delete UX Options

When a user somehow reaches a delete endpoint for a record that has dependencies (e.g., direct URL access, stale page), we need to inform them WHY deletion is blocked. Here are the options ranked by implementation complexity:

**Option A: Django Messages + Redirect (Simplest - RECOMMENDED)**
```python
# In delete view
if not can_delete:
    messages.error(
        request, 
        f"❌ Cannot delete this {record_type}. "
        f"{blocking_count} {blocking_type}(s) exist after it. "
        f"Delete those first, then try again."
    )
    return redirect(record.get_absolute_url())  # Back to detail page
```
- **Complexity:** Minimal - uses existing Django messages framework
- **UX:** User sees red banner at top of page
- **Implementation:** 10 minutes per view

**Option B: Inline Error in Delete Confirmation Page**
```html
<!-- delete_confirm.html -->
{% if blocking_records %}
<div class="alert alert-danger">
    <h5>⚠️ Cannot Delete</h5>
    <p>This record has {{ blocking_records|length }} dependent record(s):</p>
    <ul>
    {% for record in blocking_records %}
        <li>{{ record.type }}: {{ record.identifier }} ({{ record.created_at }})</li>
    {% endfor %}
    </ul>
    <p>Delete these first, then return here.</p>
</div>
<a href="{{ back_url }}" class="btn btn-secondary">Go Back</a>
{% else %}
<!-- Normal delete confirmation form -->
{% endif %}
```
- **Complexity:** Low - same template, conditional content
- **UX:** User sees exactly what's blocking + links to blocking records
- **Implementation:** 30 minutes per template

**Option C: JavaScript Modal (Medium Complexity)**
```javascript
// On delete button click (for stale pages)
fetch(`/api/can-delete/${recordType}/${recordId}/`)
    .then(r => r.json())
    .then(data => {
        if (!data.can_delete) {
            showModal({
                title: 'Cannot Delete',
                body: data.reason,
                buttons: [{text: 'OK', action: 'close'}]
            });
        } else {
            // Proceed to delete confirmation
        }
    });
```
- **Complexity:** Medium - requires API endpoint + JS handler
- **UX:** Clean modal without page reload
- **Implementation:** 2 hours total (API + JS + modal HTML)

**RECOMMENDATION:** Start with **Option A** (Django messages). If users complain about UX, upgrade to **Option B**. Option C is overkill for this use case.

---

**Storage:** Hard delete. Record snapshot saved to AuditLog before deletion. (See "What is Hard Delete" below)

---

#### What is "Hard Delete with AuditLog Snapshot"?

**Hard Delete:** The record is PERMANENTLY removed from the database. Unlike "soft delete" where a record is marked `is_deleted=True` but still exists, hard delete uses `DELETE FROM table WHERE id=X`. The row is gone.

**AuditLog Snapshot:** BEFORE we delete, we serialize the entire record to JSON and save it to the `AuditLog` table. This means:
- We can see WHAT was deleted
- We can see WHO deleted it
- We can see WHEN it was deleted
- We can (theoretically) reconstruct the data if needed

**AuditLog Location:** `apps/audit/models.py` → database table `audit_auditlog`

```python
# Example AuditLog entry for a deleted purchase
# Mapping to actual AuditLog model fields:

AuditLog.objects.create(
    # auto: timestamp = 2026-01-15T10:30:00Z
    user = User.objects.get(email="joe@coophive.network"),
    app_label = "inventory",
    model_name = "Item01FlourType1Purchases",
    object_pk = "47",
    action = "DELETE",  # Uses existing ACTION_CHOICES
    changes = {  # JSONField - stores the full record snapshot
        "purchase_number": "PUR-FLOUR_TYPE1-2026-01-10-001",
        "supplier_name": "Unga Mills",
        "quantity_purchased": "100.0000",
        "unit_price": "85.0000",
        "total_cost": "8500.00",
        "purchase_date": "2026-01-10",
        "purchased_by": 3,
        "notes": ""
    },
    message = "Wrong quantity entered"  # User's reason for deletion
)
```

**Note:** The existing `AuditLog` model is sufficient. We use:
- `changes` (JSONField) → stores the full record snapshot
- `message` (TextField) → stores the user's reason for deletion
- `action` → uses existing "DELETE" choice

**Why Hard Delete (not Soft Delete)?**

1. **Simpler queries:** No need for `.filter(is_deleted=False)` everywhere
2. **Cleaner stock calculations:** Deleted records don't accidentally affect balances
3. **Audit trail is separate:** AuditLog is purpose-built for historical records
4. **Database stays small:** Old deleted records don't bloat tables

---

All delete operations use `@transaction.atomic`.

#### 1.1 Delete Purchase

**URL:** `/inventory/item/<item_id>/purchase/<purchase_id>/delete/`

**Can delete if:** No `ProductionBatch` exists with `created_at > purchase.created_at`

**On delete:**
1. **Stock recalculation:** Subtract `quantity_purchased` from `ItemXXDetails.current_stock`
2. **Price handling:** **DO NOTHING** - keep `last_purchase_unit_price` unchanged
3. **Value recalculation:** Recalculate `current_value = current_stock × last_purchase_unit_price`

**Why keep the price unchanged?**
- If deletion is valid, no production happened after this purchase
- Therefore, no batch snapshot depends on this specific price being "correct"
- The price is just a reference for future use - stale is better than zero
- If it's truly wrong, the next purchase will update it anyway

**Simple rule:** If delete is allowed → delete the record, adjust stock, **leave price alone**.

```python
def delete_purchase(purchase, user):
    item_id = purchase.inventory_item_id
    DetailsModel = get_details_model(item_id)
    PurchasesModel = get_purchases_model(item_id)
    
    with transaction.atomic():
        # Lock item row
        item = DetailsModel.objects.select_for_update().get(pk=1)
        
        # Reduce stock
        item.current_stock -= purchase.quantity_purchased
        
        # DO NOT TOUCH last_purchase_unit_price or last_purchase_date
        # The existing values are fine - no production depended on this purchase
        
        item.save()  # current_value auto-calculated
        
        # Delete purchase (bypassing guard)
        _force_delete(purchase, user, 'DELETE_PURCHASE')
```

**Note on Production Costs:** Deleting a purchase does NOT retroactively change `ProductionBatch.cost_per_unit` or `BatchIngredientDeduction.unit_price_at_deduction`. Those are **snapshots** frozen at batch time. If the production cost was wrong because of a bad purchase price, you must delete the batch too.

#### 1.2 Delete Production Batch

**URL:** `/production/batch/<batch_id>/delete/`

**Can delete if:** No `SalesDispatch` exists with `created_at > batch.created_at`

---

### WHAT HAPPENS TO THE PRODUCTS (Bread, KDF, Scones, etc.)?

This is **critical to understand**. A ProductionBatch creates PRODUCTS - the finished goods that get dispatched and sold.

**When a ProductionBatch is CREATED (via `ProductionService.create_production_batch`):**

| Step | Action | Records Created/Modified |
|------|--------|--------------------------|
| 1 | Validate mix ingredients available | - |
| 2 | Deduct ingredients from inventory | `ItemXXDetails.current_stock` DECREASED for each ingredient |
| 3 | Create batch record | `ProductionBatch` record created |
| 4 | Record ingredient deductions | `BatchIngredientDeduction` records created (one per ingredient) |
| 5 | **INCREASE finished goods stock** | `ProductStock.current_stock` += `quantity_produced` |
| 6 | **Record stock movement** | `ProductStockMovement` created with `movement_type='PRODUCTION'`, `quantity=+quantity_produced`, `reference_type='ProductionBatch'`, `reference_id=batch.id` |
| 7 | Update production tracking | `ProductStock.last_production_date`, `last_production_batch` updated |

**Example:** Creating a batch of 132 loaves of White Bread
- `ProductStock` for White Bread: `current_stock` goes from 400 → 532
- `ProductStockMovement` created: `movement_type='PRODUCTION'`, `quantity=132`, `reference_id=batch.id`

---

**When a ProductionBatch is DELETED (reverse of creation):**

| Step | Action | Records Modified/Deleted |
|------|--------|--------------------------|
| 1 | **Restore ALL ingredients to inventory** | For each `BatchIngredientDeduction`: add `quantity_deducted` back to `ItemXXDetails.current_stock` |
| 2 | **DECREASE finished goods stock** | `ProductStock.current_stock` -= `batch.quantity_produced` |
| 3 | **Update production tracking** | `ProductStock.last_production_batch` updated to previous batch (or NULL) |
| 4 | **DELETE stock movement audit record** | `ProductStockMovement` where `reference_type='ProductionBatch'` AND `reference_id=batch.id` is DELETED |
| 5 | **DELETE ingredient deduction records** | All `BatchIngredientDeduction` records for this batch are DELETED (via CASCADE) |
| 6 | **DELETE batch record** | `ProductionBatch` record is DELETED |

**Example:** Deleting that batch of 132 loaves of White Bread
- `ProductStock` for White Bread: `current_stock` goes from 532 → 400
- The `ProductStockMovement` record is DELETED (not just zeroed)
- All `BatchIngredientDeduction` records are DELETED
- Flour, sugar, yeast, etc. stock is RESTORED to what it was before

---

**CRITICAL: The Product Record Itself Is NOT Deleted**

The `Product` model (e.g., "White Bread", "KDF Regular") is a **configuration item** defined in the Products app. It has:
- `name`, `category`, `selling_price`, `is_active`
- Relationship to `Mix` (recipe)
- Sub-products (e.g., "White Bread Leftovers")

**Deleting a batch does NOT delete the Product.** It only:
- Reduces `ProductStock.current_stock` for that product
- Deletes the production history for that specific batch

The Product continues to exist and can have new batches created for it.

---

**SAFETY GUARANTEE: Why ProductStock Won't Go Negative**

The temporal dependency rule ensures safety:

```
Timeline Example:
- 10:00 - Batch B1 creates 100 units → ProductStock = 100
- 11:00 - Dispatch D1 sends out 60 units → ProductStock = 40
- 12:00 - User tries to delete B1

Check: Any SalesDispatch with created_at > 10:00?
→ YES: D1 at 11:00
→ BLOCKED: Delete button is HIDDEN
```

If no dispatch exists after the batch, deletion is safe:
```
- 10:00 - Batch B1 creates 100 units → ProductStock = 100
- 11:00 - (no dispatches)
- 12:00 - User deletes B1 → ProductStock = 0

This is VALID because no products from B1 were ever dispatched.
```

---

**On delete (detailed implementation):**

**Key Insight:** We don't need the `Mix` (recipe) to reverse the batch. The `BatchIngredientDeduction` records already contain EXACTLY what was deducted - including the `inventory_item_id`, `quantity_deducted`, and `unit_price_at_deduction`. This is the "snapshot" that was captured during batch creation.

**Why BatchIngredientDeduction is sufficient:**
```
During CREATE (via ProductionService.create_production_batch):
  - Mix says: "Use 50kg flour, 5kg sugar, 0.5kg yeast"
  - Service looks up current stock prices
  - Service creates BatchIngredientDeduction records with ACTUAL quantities used

During DELETE (reverse):
  - We READ the BatchIngredientDeduction records
  - We ADD BACK the exact quantities that were deducted
  - We don't need the Mix - deductions tell us everything
```

**Implementation Steps:**

| Step | Action | Details |
|------|--------|---------|
| 1 | **Validate** | Check no SalesDispatch exists after batch.created_at |
| 2 | **Lock ProductStock** | `select_for_update()` to prevent race conditions |
| 3 | **Restore ingredients** | Loop through `batch.ingredient_deductions.all()` |
| 4 | **Reduce finished goods** | `ProductStock.current_stock -= batch.quantity_produced` |
| 5 | **Update tracking refs** | Set `last_production_batch` to previous batch or NULL |
| 6 | **Delete movements** | `ProductStockMovement.filter(reference_type='ProductionBatch', reference_id=batch.id).delete()` |
| 7 | **Audit log** | Snapshot batch to AuditLog via `_force_delete()` |
| 8 | **Delete batch** | CASCADE deletes BatchIngredientDeduction records |

```python
# apps/production/services/delete.py

from django.db import transaction
from apps.inventory.routing import get_details_model
from apps.production.models import ProductionBatch, ProductStock, ProductStockMovement
from apps.core.services.data_management import _force_delete, DataManagementError
from apps.core.services.dependency_checker import can_delete_batch


@transaction.atomic
def delete_batch_atomic(batch: ProductionBatch, user, reason: str = '') -> dict:
    """
    Delete a ProductionBatch and reverse all its effects.
    
    This is the INVERSE of ProductionService.create_production_batch().
    
    Args:
        batch: The ProductionBatch instance to delete
        user: User performing the deletion (must be SUPERADMIN)
        reason: Optional reason for audit log
    
    Returns:
        dict with 'success', 'data' or 'error'
    
    Raises:
        DataManagementError: If batch cannot be deleted (dependencies exist)
    """
    # Step 1: Validate dependencies
    can_delete, blocking_reason = can_delete_batch(batch)
    if not can_delete:
        raise DataManagementError(blocking_reason)
    
    # Step 2: Lock ProductStock row first (prevents dispatch racing us)
    stock = ProductStock.objects.select_for_update().get(product=batch.product)
    
    # Step 3: Restore ALL ingredients to inventory
    # BatchIngredientDeduction contains everything we need - no Mix lookup required
    restored_ingredients = []
    for deduction in batch.ingredient_deductions.select_for_update().all():
        DetailsModel = get_details_model(deduction.inventory_item_id)
        item = DetailsModel.objects.select_for_update().get(pk=1)
        
        # Record before state for audit
        stock_before = item.current_stock
        
        # Restore the exact quantity that was deducted
        item.current_stock += deduction.quantity_deducted
        item.updated_by = user
        item.save()  # current_value auto-calculated
        
        restored_ingredients.append({
            'inventory_item_id': deduction.inventory_item_id,
            'item_name': item.name,
            'quantity_restored': str(deduction.quantity_deducted),
            'stock_before': str(stock_before),
            'stock_after': str(item.current_stock),
        })
    
    # Step 4: Reduce finished goods stock
    stock_before = stock.current_stock
    stock.current_stock -= batch.quantity_produced
    
    # Step 5: Update tracking references
    if stock.last_production_batch == batch:
        prev_batch = ProductionBatch.objects.filter(
            product=batch.product,
            created_at__lt=batch.created_at
        ).order_by('-created_at').first()
        stock.last_production_batch = prev_batch
        stock.last_production_date = prev_batch.production_date if prev_batch else None
    stock.save()
    
    # Step 6: Delete related stock movements
    deleted_movements = ProductStockMovement.objects.filter(
        reference_type='ProductionBatch',
        reference_id=batch.id
    ).delete()[0]  # Returns (count, {model: count})
    
    # Step 7 & 8: Audit log + Delete batch (CASCADE deletes BatchIngredientDeduction)
    batch_info = {
        'batch_number': batch.batch_number,
        'product_name': batch.product.name,
        'quantity_produced': batch.quantity_produced,
    }
    _force_delete(batch, user, 'DELETE_BATCH', reason)
    
    return {
        'success': True,
        'data': {
            'batch': batch_info,
            'ingredients_restored': restored_ingredients,
            'product_stock_before': stock_before,
            'product_stock_after': stock.current_stock,
            'movements_deleted': deleted_movements,
        }
    }
```

**Note on Inventory Prices:** Deleting a batch does NOT change `last_purchase_unit_price` in inventory. Purchases are independent of production.

#### 1.3 Delete Dispatch

**URL:** `/sales/dispatch/<dispatch_id>/delete/`

**Can delete if:** No `SalesReturn` exists with `dispatch_id = dispatch.id`

**Note:** Unlike purchases and batches which use temporal ordering, dispatches are checked for **direct FK relationship** since returns have `dispatch` as foreign key.

**On delete:**
1. **Restore product stock:** For each `SalesDispatchItem`:
   - Add `quantity` back to `ProductStock.current_stock`
   - Delete the corresponding `ProductStockMovement(DISPATCH, -qty)` record
2. **Restore crates:** Add `crates_dispatched` back to `Item16CratesDetails.current_stock`
   - Delete the corresponding `Item16CratesOutputs` record created on dispatch

**Crate Restoration - Design Decision:**

**Why NOT reuse `return_crates_atomic()`:**
- `return_crates_atomic()` **creates a new Purchase record** (with unit_price=0) as audit trail
- For DELETE, we want to **remove** audit records, not create new ones
- If we used `return_crates_atomic()`, we'd have a dangling Purchase record referencing a deleted Dispatch

**Correct approach - direct reversal with integrity checks:**
```python
def _restore_crates_on_delete(dispatch, user):
    """
    Restore crates to inventory when deleting a dispatch.
    
    INTEGRITY GUARANTEES:
    1. Finds the EXACT output record via unique dispatch_number
    2. Validates quantity matches before proceeding
    3. Uses OUTPUT's quantity for restoration (not dispatch's) for ledger accuracy
    4. Raises DataManagementError on ANY inconsistency
    5. Handles edge case where crates weren't deducted on creation
    
    Unlike return_crates_atomic(), this DELETES the output record (no new purchase).
    """
    CRATES_ITEM_ID = 16
    CratesDetails = get_details_model(CRATES_ITEM_ID)
    CratesOutputs = get_outputs_model(CRATES_ITEM_ID)
    
    # Find the EXACT output record using unique dispatch_number
    search_ref = f"Ref: {dispatch.dispatch_number}"
    
    try:
        output = CratesOutputs.objects.get(description__contains=search_ref)
    except CratesOutputs.DoesNotExist:
        # No output exists - dispatch was created before crates were initialized
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"No crate output found for dispatch {dispatch.dispatch_number}. "
            f"Crates were likely not deducted on creation."
        )
        return {'success': True, 'restored': Decimal('0'), 'warning': 'No output record found'}
    except CratesOutputs.MultipleObjectsReturned:
        # Should NEVER happen - dispatch_number is unique
        raise DataManagementError(
            f"Data integrity error: Multiple crate outputs found for {dispatch.dispatch_number}. "
            f"Manual intervention required."
        )
    
    # INTEGRITY CHECK: Quantity MUST match
    if output.quantity_consumed != Decimal(str(dispatch.crates_dispatched)):
        raise DataManagementError(
            f"Data integrity error: Output quantity ({output.quantity_consumed}) "
            f"does not match dispatch crates ({dispatch.crates_dispatched}). "
            f"Manual intervention required."
        )
    
    # Restore stock (use OUTPUT's quantity for ledger accuracy)
    crates = CratesDetails.objects.select_for_update().get(pk=1)
    crates.current_stock += output.quantity_consumed
    crates.updated_by = user
    crates.save()
    
    # Delete the output record (QuerySet.delete() bypasses model guard)
    deleted_output_number = output.output_number
    CratesOutputs.objects.filter(pk=output.pk).delete()
    
    return {
        'success': True,
        'restored': output.quantity_consumed,
        'output_deleted': deleted_output_number
    }
```

**Full delete_dispatch implementation:**
```python
def delete_dispatch(dispatch, user):
    with transaction.atomic():
        # Restore product stock for each item
        for item in dispatch.items.all():
            stock = ProductStock.objects.select_for_update().get(product=item.product)
            stock.current_stock += item.quantity
            stock.save()
        
        # Delete the stock movement that was created on dispatch
        ProductStockMovement.objects.filter(
            reference_type='SalesDispatch',
            reference_id=dispatch.id
        ).delete()
        
        # Restore crates to inventory (if any were dispatched)
        if dispatch.crates_dispatched > 0:
            result = _restore_crates_on_delete(dispatch, user)
            if not result['success']:
                raise DataManagementError(f"Crate restoration failed: {result.get('error')}")
        
        # Delete dispatch (cascades to SalesDispatchItem)
        _force_delete(dispatch, user, 'DELETE_DISPATCH')
```

**Comparison: Return vs Delete**

| Aspect | Return (existing) | Delete (new) |
|--------|-------------------|--------------|
| **Product stock** | `add_return_to_stock()` → adds to Leftovers sub-product | Adds back to ORIGINAL product |
| **ProductStockMovement** | Creates RETURN (+qty) record | DELETEs original DISPATCH (-qty) record |
| **Crates stock** | `return_crates_atomic()` → adds to stock | `_restore_crates_on_delete()` → adds to stock |
| **Crates audit** | Creates Item16CratesPurchases (price=0) | DELETEs original Item16CratesOutputs |
| **Result** | Two records exist (dispatch + return) | Zero records exist (both gone) |

**Note on Production:** Deleting a dispatch does NOT affect `ProductionBatch` records. Production batches are independent - they recorded what was made, dispatches recorded what was sent out.

---

#### 1.4 Delete Return — ABSOLUTELY NEVER ALLOWED

## ⛔ RETURNS CAN NEVER, EVER BE DELETED ⛔

**This is not a technical limitation we might overcome later. It is a deliberate, permanent design decision. Returns are the financial endpoint of the sales cycle and are IMMUTABLE in perpetuity.**

---

### THE FULL ROLLBACK CASCADE (Why It's Impossible)

To "delete" a SalesReturn, we would have to reverse ALL of the following operations atomically:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SALESRETURN CREATION - WHAT HAPPENS (via ReturnService.process_return)     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. SalesReturn record created:                                              │
│     ├── total_revenue → FINANCIAL (affects P&L)                              │
│     ├── commission_amount → PAYROLL (affects salesperson pay)                │
│     ├── crates_returned, crates_lost, crates_damaged → ACCOUNTABILITY        │
│     └── return_date, notes, created_by → AUDIT                               │
│                                                                              │
│  2. SalesReturnItem records created (one per product):                       │
│     ├── qty_dispatched, qty_sold, qty_returned                               │
│     └── unit_price (snapshot from dispatch time)                             │
│                                                                              │
│  3. ProductStock MODIFIED (per returned product):                            │
│     ├── Leftovers sub-product stock INCREASED                                │
│     │   └── via ProductionService.add_return_to_stock()                      │
│     └── ProductStockMovement created:                                        │
│         ├── movement_type = 'RETURN'                                         │
│         ├── quantity = +qty_returned                                         │
│         └── reference_type = 'SalesReturn', reference_id = return.id         │
│                                                                              │
│  4. Crates inventory MODIFIED:                                               │
│     ├── Item16CratesDetails.current_stock INCREASED (crates returned)        │
│     └── Item16CratesPurchases record CREATED:                                │
│         ├── quantity_purchased = crates_returned                             │
│         ├── unit_price = 0.00 (no cost - these are returns)                  │
│         └── notes = "[CRATE RETURN - SALES] Ref: RET-xxx"                    │
│                                                                              │
│  5. SalesDispatch MODIFIED:                                                  │
│     ├── is_returned = True (was False)                                       │
│     ├── status = 'RETURNED' (was 'DISPATCHED')                               │
│     └── returned_at = timestamp                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### WHY EACH STEP CANNOT BE REVERSED

**Step 1 - SalesReturn record:** This contains `total_revenue` and `commission_amount`. These are:
- Used in daily P&L calculations (`SalesReportService.get_sales_report()`)
- Used in commission reports (`CommissionService.get_monthly_report()`)
- Possibly already emailed to stakeholders
- Possibly already used for payroll calculations

**Step 2 - SalesReturnItem records:** These record what was actually sold vs returned for each product. Deleting them would lose critical accountability data.

**Step 3 - ProductStock for Leftovers:** The returned products were added to the **Leftovers sub-product** (not the original product). For example:
- White Bread returned → goes to "White Bread Leftovers" stock
- Those leftovers might have ALREADY been dispatched in a subsequent dispatch
- You cannot reduce stock that has already been sent out

```
Timeline showing the problem:
- 10:00 - Dispatch D1: 100 loaves White Bread
- 14:00 - Return R1: 20 loaves returned → White Bread Leftovers stock = 20
- 15:00 - Dispatch D2: 15 loaves of White Bread Leftovers sent out → stock = 5
- 16:00 - User tries to delete R1

To delete R1, we need to:
- Reduce White Bread Leftovers stock by 20
- But current stock is only 5!
- IMPOSSIBLE: Would create negative stock
```

**Step 4 - Crates inventory:** Same problem. The returned crates were added to `Item16CratesDetails.current_stock`. Those crates might have been dispatched again:

```
Timeline showing the problem:
- 10:00 - Dispatch D1: 10 crates sent out
- 14:00 - Return R1: 8 crates returned → crate stock increased by 8
- 15:00 - Dispatch D2: 6 crates sent out (from the returned crates)
- 16:00 - User tries to delete R1

To delete R1, we need to:
- Reduce crate stock by 8
- But we'd have to also trace D2 which used those crates
- CASCADING INCONSISTENCY
```

Additionally, `return_crates_atomic()` created an `Item16CratesPurchases` record. Deleting this record violates the "no orphan records" principle - we'd have unexplained stock increases.

**Step 5 - SalesDispatch.is_returned:** This flag can only transition `False → True`. The reverse transition (`True → False`) is not allowed because:
- The dispatch might be referenced in reports as "RETURNED"
- The salesperson's accountability has been settled
- Commission has been recorded

---

### BUT WHAT IF THE RETURN DATA WAS ENTERED WRONG?

**Scenario:** User accidentally entered wrong quantities (e.g., 50 sold instead of 80 sold).

**Answer:** TOUGH LUCK. This is a business process problem, not a technical one.

**Prevention measures (what SHOULD happen):**
1. Return form should show dispatch details clearly
2. Return form should validate: `qty_sold + qty_returned = qty_dispatched`
3. User should review before submitting
4. Accountant should verify returns daily

**If a mistake was made:**
- Document it in the notes
- Create an adjustment entry (if the business process allows)
- Accept the discrepancy for this reporting period
- Use **Full System Reset** if the error is catastrophic

---

### WHAT ABOUT A "VOID" MECHANISM?

**Alternative Considered:** Instead of deleting, create a "void" or "reversal" entry.

**Why We Don't Do This:**
1. Void would still need to reverse stock movements → same cascade problem
2. Void would create phantom entries (original + void = net zero) → confuses reports
3. Void doesn't fix the "leftovers already dispatched" problem
4. Adds complexity without solving the core issue

**Simple Rule:** Once a return is processed, the sales cycle for that dispatch is CLOSED. Forever.

---

### IMPLEMENTATION: NO ESCAPE HATCHES

```python
# apps/sales/models.py - SalesReturn

def delete(self, *args, **kwargs):
    """Returns are immutable financial records and cannot be deleted."""
    raise ValueError(
        "SalesReturn records cannot be deleted. "
        "They represent completed financial transactions that may have "
        "already affected P&L calculations, commission payouts, "
        "and subsequent stock movements."
    )
```

**In the UI:**
- No delete button exists on return detail page
- No delete button exists in return list view
- No confirmation modal for return deletion (because there's no button)

**In the URLs:**
- No `/sales/return/<id>/delete/` route exists
- Any attempt to access such a URL returns 404

**In the Services:**
- No `delete_return()` function exists
- No `_force_delete()` is ever called for SalesReturn

**In Audit:**
- AuditLog will never have `action='DELETE_RETURN'` entries
- If such an entry appears, the system has been compromised

---

### THE ONLY WAY OUT: FULL SYSTEM RESET

If return data is so wrong that the business cannot function:
1. Primary Superadmin uses **Full System Reset**
2. ALL factory data is wiped (Inventory, Production, Sales)
3. System returns to "day zero"
4. User re-enters everything correctly

This is the nuclear option. It should almost never be used.

---

### Part 1.5: Safe Bypass of Immutability Guards

#### What is this section about?

Our models (Purchases, Batches, Dispatches, etc.) have **immutability guards** - code that prevents any modification or deletion after creation. This is the "bank ledger" design philosophy: once a transaction is recorded, it cannot be changed.

```python
# Current guards in models (e.g., BaseItemPurchases, ProductionBatch, SalesDispatch)
def save(self, *args, **kwargs):
    if self.pk:
        raise ValidationError("Cannot be modified after creation.")

def delete(self, *args, **kwargs):
    raise ValidationError("Cannot be deleted.")
```

#### Why do these guards exist?

1. **Data integrity:** Prevents accidental changes that would corrupt balances
2. **Audit trail:** Every record is permanent, matching the bank ledger approach
3. **Simplicity:** No complex "undo" logic in normal operations
4. **Trust:** Reports can rely on historical data being unchanged

#### The Problem

For the Data Management feature, we **intentionally** need to delete records. But if we call `batch.delete()`, Django raises `ValidationError("Cannot be deleted.")`. The guard blocks us.

#### When do we use the bypass?

The bypass (`_force_delete()`) is used **ONLY** in these specific scenarios:

| Scenario | Called From | Model Deleted |
|----------|-------------|---------------|
| Delete a purchase | `delete_purchase_atomic()` | `ItemXXPurchases` |
| Delete a batch | `delete_batch_atomic()` | `ProductionBatch` |
| Delete a dispatch | `delete_dispatch_atomic()` | `SalesDispatch` |
| Delete crate output (during dispatch delete) | `_restore_crates_on_delete()` | `Item16CratesOutputs` |
| Full system reset | `execute_full_reset()` | Everything |

**Never used for:**
- Normal CRUD operations
- SalesReturn (never deleted)
- Any code outside of data management services

#### The Solution: `_force_delete()` Function

Instead of modifying the model guards (risky), we use `QuerySet.delete()` which **bypasses** the model's `delete()` method. This is wrapped in a controlled function with:
1. Permission validation (SUPERADMIN only)
2. Audit log creation BEFORE deletion
3. Single point of control for all bypass operations

```python
# apps/core/services/data_management.py

from django.db import transaction
from apps.audit.models import AuditLog
from django.utils import timezone
import json

class DataManagementError(Exception):
    """Raised when delete operation cannot proceed safely."""
    pass


def _force_delete(instance, user, action_type, reason=''):
    """
    Safely delete an immutable record with full audit trail.
    
    INTERNAL USE ONLY - not exposed to views directly.
    Called only from delete service functions after validation passes.
    
    Args:
        instance: Model instance to delete
        user: User performing the deletion
        action_type: String like 'DELETE_PURCHASE', 'DELETE_BATCH', etc.
        reason: Optional reason for deletion
    
    Raises:
        DataManagementError: If deletion cannot proceed safely
    """
    # Verify user has permission
    if not user.role == 'SUPERADMIN':
        raise DataManagementError("Only SUPERADMIN can delete records")
    
    # Serialize record BEFORE deletion
    record_snapshot = _serialize_instance(instance)
    
    # Create audit log entry BEFORE deletion
    # Uses the actual AuditLog model from apps/audit/models.py
    audit_entry = AuditLog.objects.create(
        action='DELETE',  # AuditLog.ACTION_CHOICES: CREATE, UPDATE, DELETE, INFO, ERROR
        user=user,
        app_label=instance._meta.app_label,  # e.g., 'inventory', 'production', 'sales'
        model_name=instance.__class__.__name__,  # e.g., 'SugarPurchases', 'ProductionBatch'
        object_pk=str(instance.pk),  # Primary key as string
        changes=record_snapshot,  # JSONField - stores the full record snapshot
        message=f"{action_type}: {reason}" if reason else action_type  # Human-readable message
        # Note: timestamp is auto_now_add, no need to set
    )
    
    # Use QuerySet.delete() to bypass model's delete() method
    # This is the ONLY place in the codebase where this is allowed
    instance.__class__.objects.filter(pk=instance.pk).delete()
    
    return audit_entry


def _serialize_instance(instance):
    """
    Serialize a model instance to JSON-safe dict for audit logging.
    Handles ForeignKeys, Decimals, Dates, etc.
    """
    from django.forms.models import model_to_dict
    from decimal import Decimal
    from datetime import date, datetime
    
    data = model_to_dict(instance)
    
    # Convert non-JSON-serializable types
    for key, value in data.items():
        if isinstance(value, Decimal):
            data[key] = str(value)
        elif isinstance(value, (date, datetime)):
            data[key] = value.isoformat()
        elif hasattr(value, 'pk'):  # FK reference
            data[key] = value.pk
    
    return data
```

**Why QuerySet.delete() is Safe Here:**

1. **Single point of use:** `_force_delete()` is the ONLY function that uses this bypass
2. **Validation happens BEFORE:** Dependency checks are done in the calling function
3. **Audit BEFORE delete:** Snapshot captured before record is gone
4. **Transaction-wrapped:** Called within `@transaction.atomic` from parent function
5. **Permission-checked:** SUPERADMIN only

**Why NOT Modify Model Guards:**

We do NOT add `allow_delete=True` flags or conditional bypasses to models because:
- Models should remain simple and strict
- "Authorized delete" logic belongs in service layer
- No risk of accidentally passing wrong flag
- Immutability is preserved for normal operations

---

### Part 1.6: Edge Cases & Integrity Scenarios

#### Scenario A: Deleting a batch when purchase was used by multiple batches

```
Timeline:
- 10:00 - Purchase A (100kg flour)
- 10:30 - Batch 1 (uses 50kg)
- 11:00 - Batch 2 (uses 50kg)
- 11:30 - Dispatch 1 (from Batch 1)
- 12:00 - Dispatch 2 (from Batch 2)
```

**To delete Batch 2:**
1. Check: Any dispatch with `created_at > 11:00`? YES - Dispatch 1 (11:30), Dispatch 2 (12:00)
2. Result: BLOCKED - delete button hidden
3. User must delete Dispatch 2 first, then Dispatch 1, then Batch 2

**Note:** Even though Dispatch 1 is from Batch 1 (not Batch 2), the temporal rule blocks it. This is conservative but safe.

#### Scenario B: Deleting a purchase doesn't fix batch costs

```
Timeline:
- 10:00 - Purchase (100kg @ 100 KES/kg) ← WRONG PRICE (should be 80)
- 11:00 - Batch (uses 50kg @ 100 KES = 5000 KES cost)
```

**User realizes price was wrong. Options:**

1. **Delete Batch first, then Purchase:**
   - Delete Batch → restores 50kg to inventory
   - Delete Purchase → reduces stock by 100kg (now -50kg!)
   - Re-enter Purchase with correct price
   - Re-enter Batch → uses correct price
   - ✓ Full fix, but requires re-entry

2. **Use Full Reset (if too messy):**
   - Reset all data
   - Re-enter everything correctly
   - ✓ Clean slate

**What does NOT work:**
- Deleting just the Purchase doesn't fix the Batch's `cost_per_unit`
- The Batch has a SNAPSHOT of the price at creation time
- Batches don't "look up" current prices - they're immutable records

#### Scenario C: Negative stock after deletion

```
Timeline:
- 10:00 - Purchase (100kg)  → stock = 100kg
- 11:00 - Batch (uses 80kg) → stock = 20kg
- 12:00 - No more batches
```

**User tries to delete the Purchase:**
1. Check: Any batch after 10:00? YES - Batch at 11:00
2. Result: BLOCKED

**If there were no batches (edge case):**
1. Check: Any batch after 10:00? NO
2. Delete Purchase → stock = 100 - 100 = 0kg
3. ✓ Valid

**Validation rule:** `delete_purchase()` must check `current_stock >= quantity_purchased` before proceeding, or the delete will cause negative stock.

```python
# In delete_purchase()
if item.current_stock < purchase.quantity_purchased:
    raise DataManagementError(
        f"Cannot delete: Would result in negative stock. "
        f"Current: {item.current_stock}, Purchase: {purchase.quantity_purchased}"
    )
```

#### Scenario D: Deleting a dispatch after return was processed

```
Timeline:
- 10:00 - Dispatch (100 units)
- 14:00 - Return processed (80 sold, 20 returned)
```

**User tries to delete Dispatch:**
1. Check: Any return with `dispatch_id = this dispatch`? YES
2. Result: BLOCKED
3. Returns are IMMUTABLE - cannot delete

**User's only option:** Full Reset (wipes everything)

#### Scenario E: What happens to ProductStock when deleting a batch?

```
Before:
- ProductStock (Bread): 500 units
- Batch to delete: produced 100 units

After delete:
- ProductStock (Bread): 400 units
- BatchIngredientDeduction records: deleted (CASCADE)
- ProductStockMovement for batch: deleted
- Ingredients: restored to inventory
```

**Edge case:** What if ProductStock is 50 (some were dispatched)?
```
ProductStock: 50 units
Batch produced: 100 units
Difference: 50 units were dispatched

User tries to delete batch:
1. Check: Any dispatch after batch? 
   - If YES → BLOCKED (temporal rule)
   - If NO → Can delete, stock becomes 50 - 100 = -50??? 
   
This shouldn't happen because:
- If units were dispatched, there's a Dispatch record
- Dispatch record has created_at > batch.created_at
- Therefore batch is BLOCKED from deletion
```

**Conclusion:** The temporal rule naturally prevents this scenario.

---

### Part 2: Combined Reset (All Three Apps)

A single reset operation that wipes **all transaction data** from Inventory, Production, and Sales together.

**Location:** `/admin/data-management/reset/`

**Access:** Primary Superadmin only (`is_primary_superadmin=True`)

#### 2.1 Full Reset (Wipe Everything)

Deletes ALL transaction data from the three factory apps (Inventory, Production, Sales), returns system to "day zero" state.

**Dependencies:** NONE - Full reset has no dependencies because everything is deleted.

**Scope:** Only affects Inventory, Production, and Sales apps. Other apps (Payroll, Accounts, Analytics, Audit, Communications) are NOT affected.

**What gets deleted:**
```
Sales:
  - SalesReturnItem (CASCADE from SalesReturn)
  - SalesReturn
  - SalesDispatchItem (CASCADE from SalesDispatch)
  - SalesDispatch
  - ProductStockMovement (where movement_type in ['DISPATCH', 'RETURN'])

Production:
  - BatchIngredientDeduction (MUST delete BEFORE ProductionBatch - uses PROTECT, not CASCADE)
  - ProductionBatch
  - WasteLog
  - ProductStockMovement (where movement_type = 'PRODUCTION')

Inventory:
  - Item01FlourType1Purchases (and all 22 other purchase tables)
  - Item16CratesOutputs (and all 7 other output tables)
  - StockAlert (all alerts)
```

**Important FK relationships:**
```
SalesReturnItem → SalesReturn (CASCADE) ✓ Auto-deleted
SalesReturn → SalesDispatch (PROTECT) → Must delete returns BEFORE dispatches
SalesDispatchItem → SalesDispatch (CASCADE) ✓ Auto-deleted
BatchIngredientDeduction → ProductionBatch (PROTECT) → Must delete deductions BEFORE batches
ProductStockMovement → Product (PROTECT) → Must delete movements BEFORE... (but we keep products)
```

**What gets reset:**
```
Inventory:
  - All ItemXXDetails.current_stock = 0
  - All ItemXXDetails.last_purchase_unit_price = 0
  - All ItemXXDetails.last_purchase_date = NULL

Production:
  - All ProductStock.current_stock = 0
  - All ProductStock.last_production_date = NULL
  - All ProductStock.last_production_batch = NULL
```

**Note:** `last_purchase_unit_price = 0` is acceptable in Full Reset because:
1. ALL production batches are deleted first (no orphaned batch costs)
2. Full Reset returns the system to "day zero" - ready for fresh data entry
3. The first new purchase will set the correct price

**What is preserved:**
```
- User accounts
- Products & Mixes (recipes)
- Inventory item definitions
- Report schedules & recipients
- System configuration
```

**Process:**
```python
from django.db import transaction
from decimal import Decimal
from apps.sales.models import SalesReturn, SalesDispatch
from apps.production.models import (
    ProductionBatch, BatchIngredientDeduction, 
    ProductStock, ProductStockMovement, WasteLog
)
from apps.inventory.models import StockAlert
from apps.inventory.routing import (
    ITEM_PURCHASES_MODELS, ITEM_OUTPUTS_MODELS, ITEM_DETAILS_MODELS
)
from apps.audit.models import AuditLog


@transaction.atomic
def execute_full_reset(user, reason: str = ''):
    """
    Wipe all transaction data from Inventory, Production, and Sales.
    
    CRITICAL: Uses QuerySet._raw_delete() to bypass model delete() guards.
    All models have immutability guards that raise ValueError on delete().
    
    Args:
        user: Must be Primary Superadmin (is_primary_superadmin=True)
        reason: Required explanation for audit log
    
    Order matters - delete in reverse dependency order:
    1. Sales movements (no FK protection)
    2. SalesReturn (PROTECTS SalesDispatch)
    3. SalesDispatch (CASCADE deletes SalesDispatchItem)
    4. Production movements (no FK protection)
    5. BatchIngredientDeduction (PROTECTS ProductionBatch)
    6. ProductionBatch
    7. WasteLog
    8. Inventory purchases & outputs
    9. StockAlert
    10. Reset balances (UPDATE, not DELETE)
    """
    
    if not user.is_primary_superadmin:
        raise PermissionError("Only Primary Superadmin can perform full reset")
    
    if not reason:
        raise ValueError("Reason is required for audit trail")
    
    # Count records before deletion (for audit and UI display)
    counts = {
        'sales_returns': SalesReturn.objects.count(),
        'sales_dispatches': SalesDispatch.objects.count(),
        'sales_movements': ProductStockMovement.objects.filter(
            movement_type__in=['DISPATCH', 'RETURN']
        ).count(),
        'production_batches': ProductionBatch.objects.count(),
        'batch_ingredient_deductions': BatchIngredientDeduction.objects.count(),
        'waste_logs': WasteLog.objects.count(),
        'production_movements': ProductStockMovement.objects.filter(
            movement_type='PRODUCTION'
        ).count(),
        'stock_alerts': StockAlert.objects.count(),
        # Sum across all purchase tables
        'purchases': sum(
            Model.objects.count() 
            for Model in ITEM_PURCHASES_MODELS.values()
        ),
        # Sum across all output tables
        'outputs': sum(
            Model.objects.count() 
            for Model in ITEM_OUTPUTS_MODELS.values()
        ),
    }
    
    # =========================================================================
    # SALES - Delete movements first, then returns, then dispatches
    # =========================================================================
    
    # ProductStockMovement for sales (DISPATCH, RETURN types)
    # Uses _raw_delete() to bypass model's save/delete guards
    ProductStockMovement.objects.filter(
        movement_type__in=['DISPATCH', 'RETURN']
    )._raw_delete(using='default')
    
    # SalesReturn - must delete BEFORE SalesDispatch (PROTECT relationship)
    # Cascades to SalesReturnItem
    SalesReturn.objects.all()._raw_delete(using='default')
    
    # SalesDispatch - Cascades to SalesDispatchItem
    SalesDispatch.objects.all()._raw_delete(using='default')
    
    # =========================================================================
    # PRODUCTION - Delete movements, then deductions, then batches
    # =========================================================================
    
    # ProductStockMovement for production (PRODUCTION type)
    ProductStockMovement.objects.filter(
        movement_type='PRODUCTION'
    )._raw_delete(using='default')
    
    # BatchIngredientDeduction - must delete BEFORE ProductionBatch (PROTECT)
    BatchIngredientDeduction.objects.all()._raw_delete(using='default')
    
    # ProductionBatch
    ProductionBatch.objects.all()._raw_delete(using='default')
    
    # WasteLog
    WasteLog.objects.all()._raw_delete(using='default')
    
    # =========================================================================
    # INVENTORY - All 23 purchase tables + 8 output tables
    # =========================================================================
    
    # Purchases (all 23 tables)
    for item_id, PurchaseModel in ITEM_PURCHASES_MODELS.items():
        PurchaseModel.objects.all()._raw_delete(using='default')
    
    # Outputs (items 16-23 only, 8 tables)
    for item_id, OutputModel in ITEM_OUTPUTS_MODELS.items():
        OutputModel.objects.all()._raw_delete(using='default')
    
    # StockAlert
    StockAlert.objects.all()._raw_delete(using='default')
    
    # =========================================================================
    # RESET BALANCES TO ZERO (UPDATE, not DELETE)
    # =========================================================================
    
    # Inventory item balances (all 23 Details tables)
    for item_id, DetailsModel in ITEM_DETAILS_MODELS.items():
        DetailsModel.objects.all().update(
            current_stock=Decimal('0'),
            last_purchase_unit_price=Decimal('0'),
            last_purchase_date=None
        )
    
    # Product stock balances
    ProductStock.objects.all().update(
        current_stock=0,
        last_production_date=None,
        last_production_batch=None
    )
    
    # =========================================================================
    # AUDIT LOG - Record the reset action
    # =========================================================================
    
    AuditLog.objects.create(
        action='DELETE',
        user=user,
        app_label='core',
        model_name='FULL_SYSTEM_RESET',
        object_pk='ALL',
        changes={
            'records_deleted': counts,
            'inventory_items_reset': len(ITEM_DETAILS_MODELS),
            'product_stocks_reset': ProductStock.objects.count(),
        },
        message=f"FULL_SYSTEM_RESET: {reason}"
    )
    
    return counts
```

**Why `_raw_delete()` instead of `.delete()`?**

All transaction models (SalesReturn, SalesDispatch, ProductionBatch, etc.) have immutability guards:
```python
def delete(self, *args, **kwargs):
    raise ValueError("Cannot be deleted. Bank ledger policy.")
```

Django's `QuerySet.delete()` calls each model's `delete()` method, which triggers these guards. 

`QuerySet._raw_delete()` bypasses the model layer entirely and executes raw SQL DELETE. This is appropriate for Full Reset because:
1. We've already validated permissions (Primary Superadmin only)
2. We're deleting ALL records (no partial state)
3. We've captured audit information BEFORE deletion
4. The operation is atomic (all-or-nothing)

**UI:**
```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠️  FULL SYSTEM RESET - Primary Superadmin Only                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  This will permanently delete ALL transaction data from:        │
│  • Inventory (all purchases, outputs, stock alerts)             │
│  • Production (all batches, ingredient deductions, waste logs)  │
│  • Sales (all dispatches, returns, stock movements)             │
│                                                                  │
│  All stock balances will be set to ZERO.                        │
│  This action CANNOT be undone.                                   │
│                                                                  │
│  ─────────────────────────────────────────────────────────────   │
│  RECORDS TO BE DELETED:                                          │
│                                                                  │
│  Sales:                                                          │
│    • SalesDispatch: 47                                           │
│    • SalesReturn: 12                                             │
│    • ProductStockMovement (DISPATCH/RETURN): 94                  │
│                                                                  │
│  Production:                                                     │
│    • ProductionBatch: 31                                         │
│    • BatchIngredientDeduction: 248                               │
│    • WasteLog: 3                                                 │
│    • ProductStockMovement (PRODUCTION): 31                       │
│                                                                  │
│  Inventory:                                                      │
│    • Purchases (23 tables): 89                                   │
│    • Outputs (8 tables): 15                                      │
│    • StockAlert: 7                                               │
│  ─────────────────────────────────────────────────────────────   │
│                                                                  │
│  After reset, you will need to:                                  │
│  1. Perform physical stock count of raw materials                │
│  2. Enter opening balances for inventory items                   │
│     (Production and Sales start at zero - no opening balances)   │
│                                                                  │
│  [  ] I understand ALL transaction data will be deleted          │
│  [  ] I am prepared to enter inventory opening balances          │
│                                                                  │
│  Reason for reset: [___________________________________]         │
│                                                                  │
│  [Cancel]                              [🗑️ Execute Full Reset]   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Note on counts:** The UI shows record counts by querying each model before deletion. The counts dictionary in the code should be expanded to include:
- `batch_ingredient_deductions`: `BatchIngredientDeduction.objects.count()`
- Purchase counts per table (summed)
- Output counts per table (summed)

---

## Implementation Plan

**Branch:** `feature/data-management`

### Phase 1: Core Infrastructure

**File:** `apps/core/services/data_management.py`

- `DataManagementError` exception class
- `_force_delete(instance, user, action_type, reason)` - Internal delete with audit
- `_serialize_instance(instance)` - Convert model to JSON-safe dict

### Phase 2: Dependency Checkers

**File:** `apps/core/services/dependency_checker.py`

- `can_delete_purchase(purchase) -> (bool, str)` - Check for batches after
- `can_delete_batch(batch) -> (bool, str)` - Check for dispatches after
- `can_delete_dispatch(dispatch) -> (bool, str)` - Check for return (FK, not temporal)
- `get_blocking_records(record_type, record_id) -> list` - For UI display

### Phase 3: Delete Service Functions

**File:** `apps/inventory/services/delete.py`
- `delete_purchase_atomic(purchase, user, reason)` - Full purchase deletion

**File:** `apps/production/services/delete.py`
- `delete_batch_atomic(batch, user, reason)` - Full batch deletion

**File:** `apps/sales/services/delete.py`
- `delete_dispatch_atomic(dispatch, user, reason)` - Full dispatch deletion

### Phase 4: Delete Views

**File:** `apps/inventory/views/delete.py`
- `purchase_delete(request, item_id, purchase_id)` - Confirm + execute

**File:** `apps/production/views/delete.py`
- `batch_delete(request, batch_id)` - Confirm + execute

**File:** `apps/sales/views/delete.py`
- `dispatch_delete(request, dispatch_id)` - Confirm + execute

### Phase 5: Reset Page

**File:** `apps/core/views/data_management.py`
- `full_reset(request)` - Primary SUPERADMIN only

**File:** `apps/core/services/system_reset.py`
- `execute_full_reset(user, reason)` - The reset logic

### Phase 6: Templates & URLs

- Add delete buttons to existing detail templates (conditional on `can_delete`)
- Add delete confirmation templates
- Add reset page template
- Add URLs to each app's `urls.py`

### Phase 7: Access Control & Testing

- Verify decorators are applied correctly
- Write unit tests for each scenario
- Write integration tests for edge cases

---

## Security & Audit

### Access Control Matrix

| Action | Staff | Salesman | Admin | Superadmin | Primary Superadmin |
|--------|-------|----------|-------|------------|-------------------|
| View Records | ✓ | ✓ | ✓ | ✓ | ✓ |
| Delete Records | ✗ | ✗ | ✗ | ✓ | ✓ |
| Full Reset | ✗ | ✗ | ✗ | ✗ | ✓ |

### Audit Logging

All delete/reset operations logged to `AuditLog` (table: `audit_auditlog`):
```python
{
    "action": "DELETE",  # From ACTION_CHOICES
    "user": "joe@coophive.network",  # FK to CustomUser
    "app_label": "sales",  # e.g., 'inventory', 'production', 'sales'
    "model_name": "SalesDispatch",  # Model class name
    "object_pk": "45",  # Primary key as string
    "changes": { ... },  # JSONField - full record snapshot before deletion
    "message": "DELETE_DISPATCH: Incorrect quantities entered",  # Human-readable reason
    "timestamp": "2026-01-08T14:30:00Z"  # auto_now_add
}
```

---

## Testing Checklist

### Purchase Deletion
- [ ] Delete purchase (button hidden when batches exist after it)
- [ ] Delete purchase returns 403 if dependency check bypassed
- [ ] Delete purchase recalculates `current_stock` correctly
- [ ] Delete purchase **DOES NOT TOUCH** `last_purchase_unit_price` (leave as-is)
- [ ] Delete purchase **DOES NOT TOUCH** `last_purchase_date` (leave as-is)
- [ ] Delete purchase recalculates `current_value` correctly (stock × unchanged price)
- [ ] Delete purchase blocked if would result in negative stock
- [ ] Delete purchase creates AuditLog with snapshot

### Batch Deletion
- [ ] Delete batch (button hidden when dispatches exist after it)
- [ ] Delete batch returns 403 if dependency check bypassed
- [ ] Delete batch restores ALL ingredients correctly to ItemXXDetails.current_stock
- [ ] Delete batch reduces `ProductStock.current_stock` by exactly `batch.quantity_produced`
- [ ] Delete batch does NOT delete the Product record itself (only adjusts stock)
- [ ] Delete batch updates `last_production_batch` reference to previous batch (or NULL)
- [ ] Delete batch updates `last_production_date` to previous batch's date (or NULL)
- [ ] Delete batch deletes `ProductStockMovement` where `reference_type='ProductionBatch'` AND `reference_id=batch.id`
- [ ] Delete batch does NOT change `ItemXXDetails.last_purchase_unit_price` (inventory prices unchanged)
- [ ] Delete batch deletes all `BatchIngredientDeduction` records for this batch (via CASCADE)
- [ ] Delete batch creates AuditLog with full batch snapshot before deletion
- [ ] Temporal rule prevents batch deletion if ANY dispatch exists after batch.created_at

### Dispatch Deletion
- [ ] Delete dispatch (button hidden when return exists for it)
- [ ] Delete dispatch returns 403 if dependency check bypassed (FK check, not temporal)
- [ ] Delete dispatch restores ALL product stock correctly (to original product, NOT leftovers)
- [ ] Delete dispatch restores crates using OUTPUT's quantity (not dispatch's)
- [ ] Delete dispatch validates output quantity matches dispatch crates
- [ ] Delete dispatch raises DataManagementError if quantities don't match
- [ ] Delete dispatch handles missing output gracefully (logs warning)
- [ ] Delete dispatch DELETES original `Item16CratesOutputs` record (not creates new purchase)
- [ ] Delete dispatch DELETES related `ProductStockMovement(DISPATCH)` records
- [ ] Delete dispatch does NOT affect production batches
- [ ] Delete dispatch creates AuditLog with snapshot

### Returns (IMMUTABLE - NO DELETION)
- [ ] Return delete button does NOT exist on return detail page
- [ ] Return delete button does NOT exist in return list view
- [ ] No `/sales/return/<id>/delete/` URL route exists (returns 404)
- [ ] No `delete_return()` or `delete_return_atomic()` function exists in services
- [ ] SalesReturn.delete() raises ValueError with message about immutability
- [ ] AuditLog NEVER contains `action='DELETE_RETURN'` entries
- [ ] QuerySet.delete() is NEVER called on SalesReturn in any service
- [ ] `_force_delete()` is NEVER called with SalesReturn instances
- [ ] Documentation clearly states returns cannot be deleted (this spec)

### Full Reset
- [ ] Only Primary Superadmin (`is_primary_superadmin=True`) can execute
- [ ] Reason field is required (non-empty)
- [ ] Full reset deletes in correct FK order (returns before dispatches, deductions before batches)
- [ ] Full reset uses `_raw_delete()` to bypass model guards
- [ ] Full reset wipes all Sales data (dispatches, returns, items)
- [ ] Full reset wipes all Production data (batches, deductions, waste logs)
- [ ] Full reset wipes all Inventory transactions (purchases, outputs, alerts)
- [ ] Full reset wipes all ProductStockMovement records
- [ ] Full reset preserves: users, products, mixes, inventory item definitions
- [ ] Full reset sets all `ItemXXDetails.current_stock` to 0
- [ ] Full reset sets all `ItemXXDetails.last_purchase_unit_price` to 0
- [ ] Full reset sets all `ItemXXDetails.last_purchase_date` to NULL
- [ ] Full reset sets all `ProductStock.current_stock` to 0
- [ ] Full reset sets all `ProductStock.last_production_date` to NULL
- [ ] Full reset sets all `ProductStock.last_production_batch` to NULL
- [ ] Full reset creates AuditLog with app_label='core', model_name='FULL_SYSTEM_RESET'
- [ ] Full reset is atomic (all-or-nothing on failure)

### Access Control
- [ ] Only SUPERADMIN sees delete buttons
- [ ] Only Primary SUPERADMIN can access reset page
- [ ] Non-SUPERADMIN attempting delete returns 403

### Edge Cases
- [ ] Cannot delete purchase that would cause negative stock
- [ ] Temporal blocking is conservative (blocks even unrelated downstream records)
- [ ] Deleting purchase doesn't fix already-recorded batch costs
- [ ] CASCADE deletes work correctly: SalesDispatch → SalesDispatchItem, SalesReturn → SalesReturnItem
- [ ] PROTECT relationships handled correctly: BatchIngredientDeduction (delete BEFORE batch), SalesReturn (delete BEFORE dispatch)

---

## Related Files

```
apps/
├── core/
│   ├── services/
│   │   ├── data_management.py     # _force_delete, _serialize_instance
│   │   ├── dependency_checker.py  # can_delete_* functions
│   │   └── system_reset.py        # execute_full_reset
│   ├── views/
│   │   └── data_management.py     # full_reset view
│   └── templates/core/
│       └── full_reset.html        # Reset confirmation page
│
├── inventory/
│   ├── services/
│   │   └── delete.py              # delete_purchase_atomic
│   ├── views/
│   │   └── delete.py              # purchase_delete view
│   └── templates/inventory/
│       └── purchase_delete.html   # Confirm deletion
│
├── production/
│   ├── services/
│   │   └── delete.py              # delete_batch_atomic
│   ├── views/
│   │   └── delete.py              # batch_delete view
│   └── templates/production/
│       └── batch_delete.html      # Confirm deletion
│
└── sales/
    ├── services/
    │   └── delete.py              # delete_dispatch_atomic
    ├── views/
    │   └── delete.py              # dispatch_delete view
    └── templates/sales/
        └── dispatch_delete.html   # Confirm deletion
```

---

## Timeline Estimate

| Phase | Description | Effort |
|-------|-------------|--------|
| Phase 1 | Core infrastructure (`_force_delete`, exceptions) | 2 hours |
| Phase 2 | Dependency checkers | 2 hours |
| Phase 3 | Delete service functions (3 apps) | 4 hours |
| Phase 4 | Delete views (3 apps) | 2 hours |
| Phase 5 | Reset page (view + service) | 2 hours |
| Phase 6 | Templates & URLs | 2 hours |
| Phase 7 | Access control & Testing | 4 hours |
| Phase 8 | CSV attachments for scheduled emails (Part 3) | 3 hours |
| **Total** | | **21 hours** |

---

## Part 3: Backup & Archive Strategy

### Problem

If Railway data is nuked or corrupted, we need historical records independent of the cloud database.

### Solution: Excel (.xlsx) Attachments in Scheduled Emails

The Reports app already generates scheduled reports and emails them as PDF via Django-Q. **Add formatted Excel (.xlsx) attachments to those same emails.**

**Why Excel instead of CSV?**
- **Formatted like PDFs** - Headers, bold, colors, column widths, number formatting
- **Google Drive native** - Opens directly in Google Sheets with formatting preserved
- **Data is extractable** - Unlike PDF, you can copy/filter/sort the data
- **Professional appearance** - Matches your PDF look and feel
- **Single dependency** - `openpyxl` (pure Python, well-maintained)

**No new infrastructure needed:**
- No Windows service
- No separate scheduler
- No API endpoints
- No credentials management
- No URL configuration

### New Dependency: openpyxl

```bash
pip install openpyxl
```

**Why openpyxl?**
- Pure Python (no system dependencies like WeasyPrint needs)
- Actively maintained, stable API
- ~18M downloads/month on PyPI
- Already used by pandas, Django import-export, etc.
- ~3MB installed size
- Supports all Excel formatting features we need

**Add to `requirements/base.txt`:**
```
openpyxl>=3.1.0
```

### Reports App Structure (Existing)

```
apps/reports/
├── models.py           # ReportSchedule, ReportType, ScheduleReport, ReportRecipient
├── tasks.py            # Django-Q async tasks (send_daily_report, send_weekly_report, etc.)
├── services.py         # SalesReportService, InventoryReportService, ProductionReportService
├── pdf_views.py        # PDF generation via WeasyPrint
├── views.py            # Frontend views
└── templates/
    └── reports/
        ├── pdf/                              # ← PDF templates (REFERENCE FOR EXCEL STYLING)
        │   ├── base_pdf.html                 # Base template with all CSS styles
        │   ├── sales_daily.html              # Daily sales layout
        │   ├── sales_weekly.html             
        │   ├── sales_monthly.html            
        │   ├── pnl_daily.html                # P&L layouts
        │   ├── pnl_weekly.html               
        │   ├── pnl_monthly.html              
        │   ├── inventory_valuation.html      # Inventory layouts
        │   ├── low_stock_alerts.html         
        │   ├── production_daily.html         # Production layouts
        │   ├── production_weekly.html        
        │   ├── production_monthly.html       
        │   ├── payroll_monthly.html          # Payroll layout
        │   └── ... (30 templates total)      
        └── email/                            # Email templates
```

### PDF Template Styling Reference

**Location:** `apps/reports/templates/reports/pdf/base_pdf.html` (423 lines)

The PDF templates define the visual styling that Excel must mirror. Key elements from `base_pdf.html`:

| CSS Class/Element | Description | Hex Color |
|------------------|-------------|-----------|
| `.pdf-header h1` | Report title | `#8B4513` (SaddleBrown) |
| `th` (table headers) | Brown background, white text | bg: `#8B4513`, text: `#FFFFFF` |
| `.kpi-card.success` | Green success indicators | `#28a745` |
| `.kpi-card.danger` | Red danger indicators | `#dc3545` |
| `.kpi-card.warning` | Yellow warning indicators | `#ffc107` |
| `.kpi-card.info` | Blue info indicators | `#17a2b8` |
| `.text-success` | Green text | `#28a745` |
| `.text-danger` | Red text | `#dc3545` |
| `.text-muted` | Gray text | `#888888` |
| `tbody tr:nth-child(even)` | Alternate row shading | `#f9f9f9` |
| `.watermark` | Diagonal "CHESANTO BAKERY" | `rgba(139,69,19,0.06)` |

**Watermark:** PDFs have a fixed diagonal watermark "CHESANTO BAKERY" at 72pt with very light brown color. Excel doesn't support true watermarks, but we can add a header row or footer text as a branding alternative.

**Page Elements:**
- Running header: "CHESANTO BAKERY" (top center)
- Running footer: "Confidential" (left), "Page X of Y" (center), "Generated: date" (right)

### Current Scheduled Report Flow

```
1. Django-Q Scheduler calls: send_daily_report() at 9 PM daily
                              send_weekly_report() at 9 PM Sunday
                              send_monthly_report() at 9 PM last day of month
                              send_annual_report() at 9 PM Dec 31

2. send_scheduled_reports(schedule_type, mode) in tasks.py:
   └── Gets ReportSchedule from DB (DAILY, WEEKLY, MONTHLY, ANNUAL)
   └── Gets ReportRecipient list (from report_recipient table)
   └── Gets ScheduleReport list (which report types to include)
   └── For each report code:
       └── generate_report_pdf(report_code, dates) → PDF bytes
   └── Attaches all PDFs to EmailMessage
   └── Sends via Django EmailMessage

3. Recipient receives email with PDF attachments
```

### New Flow (PDF + Excel)

```
NEW STATE
─────────
Django-Q Schedule → Generate PDF + Excel → Email to Recipients

Each scheduled email will contain:
- PDF attachments (for viewing/printing - already implemented)
- Excel attachments (for data backup/analysis - NEW)
```

### Implementation

**Step 1: Add Excel style constants to `apps/reports/tasks.py`**

These colors and styles are derived from `apps/reports/templates/reports/pdf/base_pdf.html`:

```python
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEL STYLE CONSTANTS
# Mirrors: apps/reports/templates/reports/pdf/base_pdf.html
# ═══════════════════════════════════════════════════════════════════════════════

# Chesanto brand color (SaddleBrown) - used for headers in PDF
CHESANTO_BROWN = '8B4513'

EXCEL_STYLES = {
    # Report title - matches .pdf-header h1 (brown text) but inverted for Excel visibility
    'title_font': Font(bold=True, size=18, color='FFFFFF'),
    'title_fill': PatternFill(start_color=CHESANTO_BROWN, end_color=CHESANTO_BROWN, fill_type='solid'),
    
    # Section headers - matches h3.section-header (brown text, border-bottom)
    'section_font': Font(bold=True, size=12, color=CHESANTO_BROWN),
    
    # Table headers - matches th (brown background, white text, uppercase)
    # From base_pdf.html: th { background: #8B4513; color: white; }
    'header_font': Font(bold=True, size=8, color='FFFFFF'),
    'header_fill': PatternFill(start_color=CHESANTO_BROWN, end_color=CHESANTO_BROWN, fill_type='solid'),
    'header_alignment': Alignment(horizontal='center', vertical='center'),
    
    # Alternate row shading - matches tbody tr:nth-child(even) { background: #f9f9f9; }
    'alt_row_fill': PatternFill(start_color='F9F9F9', end_color='F9F9F9', fill_type='solid'),
    
    # Footer/total row - matches tfoot td { background: #f5f5f5; border-top: 2px solid #8B4513; }
    'footer_fill': PatternFill(start_color='F5F5F5', end_color='F5F5F5', fill_type='solid'),
    'footer_font': Font(bold=True),
    
    # Number formats
    'currency_format': '"KES "#,##0',      # Matches KES {{ value|intcomma }} in templates
    'currency_decimal': '"KES "#,##0.00',
    'integer_format': '#,##0',
    'percent_format': '0.0%',
    'date_format': 'YYYY-MM-DD',
    
    # Status colors - from base_pdf.html KPI cards and text classes
    'success_font': Font(color='28A745'),  # .text-success, .kpi-card.success
    'danger_font': Font(color='DC3545'),   # .text-danger, .kpi-card.danger
    'warning_font': Font(color='C58D00'),  # .text-warning (darker for visibility)
    'info_font': Font(color='17A2B8'),     # .text-info, .kpi-card.info
    'muted_font': Font(color='888888', italic=True),  # .text-muted, .pdf-generated
    
    # KPI card backgrounds (for summary cells)
    'success_fill': PatternFill(start_color='D4EDDA', end_color='D4EDDA', fill_type='solid'),
    'danger_fill': PatternFill(start_color='F8D7DA', end_color='F8D7DA', fill_type='solid'),
    'warning_fill': PatternFill(start_color='FFF3CD', end_color='FFF3CD', fill_type='solid'),
    'info_fill': PatternFill(start_color='D1ECF1', end_color='D1ECF1', fill_type='solid'),
    
    # Borders - matches th, td { border-bottom: 1px solid #ddd; }
    'border': Border(
        left=Side(style='thin', color='DDDDDD'),
        right=Side(style='thin', color='DDDDDD'),
        top=Side(style='thin', color='DDDDDD'),
        bottom=Side(style='thin', color='DDDDDD')
    ),
    'border_bottom_only': Border(
        bottom=Side(style='thin', color='DDDDDD')
    ),
    # Footer border - matches tfoot { border-top: 2px solid #8B4513; }
    'footer_border': Border(
        top=Side(style='medium', color=CHESANTO_BROWN),
        bottom=Side(style='thin', color='DDDDDD')
    ),
}


def _apply_header_style(cell):
    """
    Apply table header styling to a cell.
    Mirrors: th { background: #8B4513; color: white; font-weight: 600; }
    """
    cell.font = EXCEL_STYLES['header_font']
    cell.fill = EXCEL_STYLES['header_fill']
    cell.alignment = EXCEL_STYLES['header_alignment']
    cell.border = EXCEL_STYLES['border']


def _apply_data_style(cell, is_currency=False, is_percent=False, row_num=0):
    """
    Apply standard data cell styling.
    Optionally applies alternate row shading for even rows.
    """
    cell.border = EXCEL_STYLES['border_bottom_only']
    cell.alignment = Alignment(horizontal='right' if is_currency or is_percent else 'left')
    
    if is_currency:
        cell.number_format = EXCEL_STYLES['currency_format']
    elif is_percent:
        cell.number_format = EXCEL_STYLES['percent_format']
    
    # Alternate row shading (even rows)
    if row_num % 2 == 0:
        cell.fill = EXCEL_STYLES['alt_row_fill']


def _apply_footer_style(cell, is_currency=False):
    """
    Apply footer/total row styling.
    Mirrors: tfoot td { background: #f5f5f5; font-weight: bold; border-top: 2px solid #8B4513; }
    """
    cell.font = EXCEL_STYLES['footer_font']
    cell.fill = EXCEL_STYLES['footer_fill']
    cell.border = EXCEL_STYLES['footer_border']
    if is_currency:
        cell.number_format = EXCEL_STYLES['currency_format']


def _add_branding_footer(ws, row):
    """
    Add Chesanto branding footer to worksheet (Excel alternative to PDF watermark).
    Mirrors the PDF running footer: "Confidential" | "CHESANTO BAKERY"
    """
    ws.cell(row=row, column=1, value="Confidential - CHESANTO BAKERY")
    ws.cell(row=row, column=1).font = EXCEL_STYLES['muted_font']
    cell.border = EXCEL_STYLES['border']
    cell.alignment = Alignment(horizontal='right' if is_currency or is_percent else 'left')
    if is_currency:
        cell.number_format = EXCEL_STYLES['currency_format']
    elif is_percent:
        cell.number_format = EXCEL_STYLES['percent_format']
```

**Step 2: Add Excel generator dispatcher function**

```python
def generate_report_excel(report_code: str, dates: dict) -> Tuple[Optional[bytes], str]:
    """
    Generate Excel bytes for a specific report type.
    
    Returns tuple of (excel_bytes, filename) or (None, error_message) on failure.
    Mirrors generate_report_pdf() but outputs formatted Excel instead.
    """
    try:
        excel_generators = {
            'pnl_daily': lambda: _generate_pnl_daily_excel(dates),
            'pnl_weekly': lambda: _generate_pnl_weekly_excel(dates),
            'pnl_monthly': lambda: _generate_pnl_monthly_excel(dates),
            'sales_daily': lambda: _generate_sales_daily_excel(dates),
            'sales_weekly': lambda: _generate_sales_weekly_excel(dates),
            'sales_monthly': lambda: _generate_sales_monthly_excel(dates),
            'stock_levels': lambda: _generate_stock_levels_excel(dates),
            'inventory_valuation': lambda: _generate_inventory_valuation_excel(dates),
            'production_daily': lambda: _generate_production_daily_excel(dates),
            'production_weekly': lambda: _generate_production_weekly_excel(dates),
            'production_monthly': lambda: _generate_production_monthly_excel(dates),
            'payroll_monthly': lambda: _generate_payroll_monthly_excel(dates),
        }
        
        if report_code not in excel_generators:
            return None, f"No Excel generator for: {report_code}"
        
        return excel_generators[report_code]()
        
    except Exception as e:
        logger.exception(f"Error generating Excel for {report_code}: {e}")
        return None, str(e)
```

**Step 3: Add individual Excel generator functions**

```python
def _generate_sales_daily_excel(dates: dict) -> Tuple[bytes, str]:
    """
    Generate formatted Excel for daily sales report.
    
    Mirrors: apps/reports/templates/reports/pdf/sales_daily.html
    
    Structure:
    1. Title (merged, brown background)
    2. Generated timestamp (italic, gray)
    3. KPI cards row (4 summary values with colored backgrounds)
    4. Net Sales calculation box
    5. "Sales by Product" table with headers, data, totals
    6. "Sales by Salesperson" table
    7. Branding footer
    """
    from apps.reports.services import SalesReportService
    
    report_date = dates['daily_date']
    data = SalesReportService.get_daily_summary(report_date)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Sales"
    
    # ─────────────────────────────────────────────────────────────
    # TITLE SECTION (mirrors .pdf-header h1)
    # ─────────────────────────────────────────────────────────────
    ws.merge_cells('A1:F1')
    title_cell = ws['A1']
    title_cell.value = f"Daily Sales Report - {report_date.strftime('%A, %B %d, %Y')}"
    title_cell.font = EXCEL_STYLES['title_font']
    title_cell.fill = EXCEL_STYLES['title_fill']
    title_cell.alignment = Alignment(horizontal='center')
    ws.row_dimensions[1].height = 28
    
    # Subtitle (mirrors .pdf-header .subtitle)
    ws.merge_cells('A2:F2')
    ws['A2'] = "Sales Summary"
    ws['A2'].font = Font(size=10, color='666666')
    ws['A2'].alignment = Alignment(horizontal='center')
    
    # Generated timestamp (mirrors .pdf-generated)
    ws['A3'] = f"Generated: {timezone.now().strftime('%B %d, %Y at %I:%M %p')}"
    ws['A3'].font = EXCEL_STYLES['muted_font']
    
    # ─────────────────────────────────────────────────────────────
    # KPI CARDS ROW (mirrors .kpi-grid with 4 .kpi-card elements)
    # ─────────────────────────────────────────────────────────────
    row = 5
    
    # KPI Card 1: Total Revenue (success - green)
    ws.cell(row=row, column=1, value="Total Revenue")
    ws.cell(row=row, column=1).font = Font(size=8, color='666666')
    ws.cell(row=row+1, column=1, value=float(data.get('total_revenue', 0)))
    ws.cell(row=row+1, column=1).font = Font(bold=True, size=14)
    ws.cell(row=row+1, column=1).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row+1, column=1).fill = EXCEL_STYLES['success_fill']
    ws.cell(row=row+2, column=1, value=f"{data.get('dispatch_count', 0)} dispatches")
    ws.cell(row=row+2, column=1).font = Font(size=7, color='888888')
    
    # KPI Card 2: Cash Collected (primary - blue)
    ws.cell(row=row, column=2, value="Cash Collected")
    ws.cell(row=row, column=2).font = Font(size=8, color='666666')
    ws.cell(row=row+1, column=2, value=float(data.get('cash_collected', 0)))
    ws.cell(row=row+1, column=2).font = Font(bold=True, size=14)
    ws.cell(row=row+1, column=2).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row+1, column=2).fill = EXCEL_STYLES['info_fill']
    
    # KPI Card 3: Deficit (danger if > 0)
    ws.cell(row=row, column=3, value="Deficit Amount")
    ws.cell(row=row, column=3).font = Font(size=8, color='666666')
    deficit = float(data.get('deficit_amount', 0))
    ws.cell(row=row+1, column=3, value=deficit)
    ws.cell(row=row+1, column=3).font = Font(bold=True, size=14)
    ws.cell(row=row+1, column=3).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row+1, column=3).fill = EXCEL_STYLES['danger_fill'] if deficit > 0 else EXCEL_STYLES['info_fill']
    
    # KPI Card 4: Returns Value (warning if > 0)
    ws.cell(row=row, column=4, value="Returns Value")
    ws.cell(row=row, column=4).font = Font(size=8, color='666666')
    returns_val = float(data.get('returns_value', 0))
    ws.cell(row=row+1, column=4, value=returns_val)
    ws.cell(row=row+1, column=4).font = Font(bold=True, size=14)
    ws.cell(row=row+1, column=4).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row+1, column=4).fill = EXCEL_STYLES['warning_fill'] if returns_val > 0 else EXCEL_STYLES['info_fill']
    
    row = 9
    
    # ─────────────────────────────────────────────────────────────
    # NET SALES BOX (mirrors .summary-box)
    # ─────────────────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="Total Revenue")
    ws.cell(row=row, column=2, value=float(data.get('total_revenue', 0)))
    ws.cell(row=row, column=2).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right')
    
    row += 1
    ws.cell(row=row, column=1, value="Less: Returns")
    ws.cell(row=row, column=2, value=-float(data.get('returns_value', 0)))
    ws.cell(row=row, column=2).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right')
    
    row += 1
    ws.cell(row=row, column=1, value="Net Sales")
    ws.cell(row=row, column=1).font = Font(bold=True)
    ws.cell(row=row, column=2, value=float(data.get('net_sales', 0)))
    ws.cell(row=row, column=2).font = Font(bold=True)
    ws.cell(row=row, column=2).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='right')
    _apply_footer_style(ws.cell(row=row, column=1))
    _apply_footer_style(ws.cell(row=row, column=2), is_currency=True)
    
    row += 2
    
    # ─────────────────────────────────────────────────────────────
    # SALES BY PRODUCT TABLE (mirrors h3.section-header + table)
    # ─────────────────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="Sales by Product")
    ws.cell(row=row, column=1).font = EXCEL_STYLES['section_font']
    row += 1
    
    # Headers (mirrors th styling)
    headers = ['Product', 'Qty Dispatched', 'Qty Returned', 'Qty Sold', 'Revenue']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        _apply_header_style(cell)
    row += 1
    
    # Data rows (with alternate shading)
    data_start_row = row
    for idx, product in enumerate(data.get('product_breakdown', [])):
        ws.cell(row=row, column=1, value=product.get('product_name', ''))
        ws.cell(row=row, column=1).font = Font(bold=True)
        ws.cell(row=row, column=2, value=product.get('qty_dispatched', 0))
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=product.get('qty_returned', 0))
        ws.cell(row=row, column=3).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=4, value=product.get('qty_sold', 0))
        ws.cell(row=row, column=4).font = Font(bold=True)
        ws.cell(row=row, column=4).alignment = Alignment(horizontal='center')
        revenue_cell = ws.cell(row=row, column=5, value=float(product.get('revenue', 0)))
        revenue_cell.number_format = EXCEL_STYLES['currency_format']
        revenue_cell.alignment = Alignment(horizontal='right')
        
        # Apply alternate row shading and borders
        for col in range(1, 6):
            _apply_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Footer row (mirrors tfoot)
    ws.cell(row=row, column=1, value="TOTAL")
    for col in range(1, 6):
        _apply_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=2, value=data.get('total_qty_dispatched', 0))
    ws.cell(row=row, column=2).alignment = Alignment(horizontal='center')
    ws.cell(row=row, column=3, value=data.get('total_qty_returned', 0))
    ws.cell(row=row, column=3).alignment = Alignment(horizontal='center')
    ws.cell(row=row, column=4, value=data.get('total_qty_sold', 0))
    ws.cell(row=row, column=4).alignment = Alignment(horizontal='center')
    ws.cell(row=row, column=5, value=float(data.get('net_sales', 0)))
    ws.cell(row=row, column=5).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=5).alignment = Alignment(horizontal='right')
    row += 2
    
    # ─────────────────────────────────────────────────────────────
    # SALES BY SALESPERSON TABLE
    # ─────────────────────────────────────────────────────────────
    ws.cell(row=row, column=1, value="Sales by Salesperson")
    ws.cell(row=row, column=1).font = EXCEL_STYLES['section_font']
    row += 1
    
    headers = ['Salesperson', 'Dispatches', 'Revenue', 'Cash Collected', 'Deficit', 'Returns']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        _apply_header_style(cell)
    row += 1
    
    for idx, sp in enumerate(data.get('salesperson_breakdown', [])):
        ws.cell(row=row, column=1, value=sp.get('salesperson_name', ''))
        ws.cell(row=row, column=1).font = Font(bold=True)
        ws.cell(row=row, column=2, value=sp.get('dispatch_count', 0))
        ws.cell(row=row, column=2).alignment = Alignment(horizontal='center')
        ws.cell(row=row, column=3, value=float(sp.get('revenue', 0)))
        ws.cell(row=row, column=3).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=4, value=float(sp.get('cash_collected', 0)))
        ws.cell(row=row, column=4).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=5, value=float(sp.get('deficit', 0)))
        ws.cell(row=row, column=5).number_format = EXCEL_STYLES['currency_format']
        ws.cell(row=row, column=6, value=float(sp.get('returns_value', 0)))
        ws.cell(row=row, column=6).number_format = EXCEL_STYLES['currency_format']
        
        for col in range(1, 7):
            _apply_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    row += 1
    
    # ─────────────────────────────────────────────────────────────
    # BRANDING FOOTER (alternative to PDF watermark)
    # ─────────────────────────────────────────────────────────────
    _add_branding_footer(ws, row)
    
    # ─────────────────────────────────────────────────────────────
    # COLUMN WIDTHS
    # ─────────────────────────────────────────────────────────────
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 14
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 12
    
    # Save to bytes
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"sales_daily_{report_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


def _generate_stock_levels_excel(dates: dict) -> Tuple[bytes, str]:
    """
    Generate formatted Excel for current stock levels.
    
    Mirrors: apps/reports/templates/reports/pdf/low_stock_alerts.html
             apps/reports/templates/reports/pdf/inventory_valuation.html
    
    Shows all 23 inventory items with current stock, unit price, and total value.
    Low stock items are highlighted in red (matching .text-danger in PDF).
    """
    from apps.reports.services import InventoryReportService
    
    report_date = dates['today']
    data = InventoryReportService.get_current_stock_levels()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock Levels"
    
    # Title (mirrors .pdf-header h1)
    ws.merge_cells('A1:F1')
    title_cell = ws['A1']
    title_cell.value = f"Inventory Stock Levels - {report_date.strftime('%A, %B %d, %Y')}"
    title_cell.font = EXCEL_STYLES['title_font']
    title_cell.fill = EXCEL_STYLES['title_fill']
    title_cell.alignment = Alignment(horizontal='center')
    ws.row_dimensions[1].height = 28
    
    # Subtitle
    ws.merge_cells('A2:F2')
    ws['A2'] = "Raw Materials & Indirect Costs"
    ws['A2'].font = Font(size=10, color='666666')
    ws['A2'].alignment = Alignment(horizontal='center')
    
    # Generated timestamp (mirrors .pdf-generated)
    ws['A3'] = f"Generated: {timezone.now().strftime('%B %d, %Y at %I:%M %p')}"
    ws['A3'].font = EXCEL_STYLES['muted_font']
    
    # Headers (mirrors th styling)
    row = 5
    headers = ['Item', 'Category', 'Current Stock', 'Unit', 'Unit Price', 'Total Value']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=header)
        _apply_header_style(cell)
    row += 1
    
    # Data rows (with alternate shading)
    total_value = 0
    for idx, item in enumerate(data):
        ws.cell(row=row, column=1, value=item.get('name', ''))
        ws.cell(row=row, column=2, value='Ingredient' if item.get('is_ingredient') else 'Indirect Cost')
        
        stock_cell = ws.cell(row=row, column=3, value=float(item.get('current_stock', 0)))
        stock_cell.number_format = EXCEL_STYLES['integer_format']
        stock_cell.alignment = Alignment(horizontal='right')
        
        # Color code low stock (mirrors .text-danger)
        if item.get('is_low', False):
            stock_cell.font = EXCEL_STYLES['danger_font']
        
        ws.cell(row=row, column=4, value=item.get('unit', ''))
        
        price_cell = ws.cell(row=row, column=5, value=float(item.get('unit_price', 0)))
        price_cell.number_format = EXCEL_STYLES['currency_format']
        price_cell.alignment = Alignment(horizontal='right')
        
        value = float(item.get('value', 0))
        value_cell = ws.cell(row=row, column=6, value=value)
        value_cell.number_format = EXCEL_STYLES['currency_format']
        value_cell.alignment = Alignment(horizontal='right')
        total_value += value
        
        # Apply alternate row shading
        for col in range(1, 7):
            _apply_data_style(ws.cell(row=row, column=col), row_num=idx)
        row += 1
    
    # Footer/Total row (mirrors tfoot)
    row += 1
    for col in range(1, 7):
        _apply_footer_style(ws.cell(row=row, column=col))
    ws.cell(row=row, column=5, value="TOTAL:")
    ws.cell(row=row, column=5).alignment = Alignment(horizontal='right')
    ws.cell(row=row, column=6, value=total_value)
    ws.cell(row=row, column=6).number_format = EXCEL_STYLES['currency_format']
    ws.cell(row=row, column=6).alignment = Alignment(horizontal='right')
    
    row += 2
    
    # Branding footer
    _add_branding_footer(ws, row)
    
    # Column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 15
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    filename = f"stock_levels_{report_date.strftime('%Y%m%d')}.xlsx"
    return buffer.getvalue(), filename


# Similar functions needed for remaining report types:
# _generate_pnl_daily_excel(), _generate_pnl_weekly_excel(), _generate_pnl_monthly_excel()
# _generate_sales_weekly_excel(), _generate_sales_monthly_excel()
# _generate_inventory_valuation_excel()
# _generate_production_daily_excel(), _generate_production_weekly_excel(), _generate_production_monthly_excel()
# _generate_payroll_monthly_excel()
```

**Step 4: Modify `send_scheduled_reports()` to include Excel**

```python
def send_scheduled_reports(schedule_type: str, mode: str = 'scheduled') -> dict:
    # ... existing code to get schedule, recipients, report codes ...
    
    # Generate PDFs AND Excel files
    attachments = []
    for report_code in reports_to_generate:
        # PDF (existing)
        pdf_bytes, pdf_filename = generate_report_pdf(report_code, dates)
        if pdf_bytes:
            attachments.append((pdf_filename, pdf_bytes, 'application/pdf'))
            result['reports_generated'].append(report_code)
        else:
            result['reports_failed'].append(f"{report_code}: {pdf_filename}")
        
        # Excel (NEW) - silently skip if no Excel generator exists
        excel_bytes, excel_filename = generate_report_excel(report_code, dates)
        if excel_bytes:
            attachments.append((
                excel_filename, 
                excel_bytes, 
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ))
        # Note: Excel failure is not critical, don't block email
    
    # ... rest of email sending code unchanged ...
```

### PDF to Excel Style Mapping

Reference: `apps/reports/templates/reports/pdf/base_pdf.html`

| PDF Template Element (CSS) | Description | Excel Equivalent (openpyxl) |
|---------------------------|-------------|----------------------------|
| `.pdf-header h1` | Report title (18pt, brown) | Merged cells + `Font(size=18, bold=True, color='FFFFFF')` + `#8B4513` fill |
| `h3.section-header` | Section headers (12pt, brown, border) | `Font(size=12, bold=True, color='8B4513')` |
| `th` | Table headers (brown bg, white text) | `Font(bold=True, size=8, color='FFFFFF')` + `#8B4513` fill |
| `tbody tr:nth-child(even)` | Alternate row shading | `PatternFill(start_color='F9F9F9')` on even rows |
| `tfoot td` | Footer/total rows (gray bg, brown border) | `PatternFill(start_color='F5F5F5')` + `Border(top=medium, color='8B4513')` |
| `.pdf-generated` | Timestamp (8pt, gray, italic) | `Font(italic=True, size=9, color='888888')` |
| `.text-end` | Right-align numbers | `Alignment(horizontal='right')` |
| `.text-success` | Green text (positive values) | `Font(color='28A745')` |
| `.text-danger` | Red text (negative/low stock) | `Font(color='DC3545')` |
| `.text-warning` | Yellow/orange text | `Font(color='C58D00')` |
| `.text-muted` | Gray text (secondary info) | `Font(color='888888')` |
| `.kpi-card.success` | Green KPI card background | `PatternFill(start_color='D4EDDA')` |
| `.kpi-card.danger` | Red KPI card background | `PatternFill(start_color='F8D7DA')` |
| `.kpi-card.warning` | Yellow KPI card background | `PatternFill(start_color='FFF3CD')` |
| `.kpi-card.info` | Blue KPI card background | `PatternFill(start_color='D1ECF1')` |
| `KES {{ value\|intcomma }}` | Currency formatting | `number_format='"KES "#,##0'` |
| `.watermark` | Diagonal "CHESANTO BAKERY" | Footer row: "Confidential - CHESANTO BAKERY" (italic, gray) |

### PDF Template → Excel Generator Reference

Each Excel generator should mirror the structure of its corresponding PDF template:

| PDF Template | Excel Generator | Key Sections to Mirror |
|-------------|-----------------|----------------------|
| `pdf/sales_daily.html` | `_generate_sales_daily_excel()` | KPI grid (4 cards), Net Sales box, Product table, Salesperson table |
| `pdf/sales_weekly.html` | `_generate_sales_weekly_excel()` | Daily breakdown table, Weekly totals |
| `pdf/sales_monthly.html` | `_generate_sales_monthly_excel()` | Weekly breakdown, Product rankings |
| `pdf/pnl_daily.html` | `_generate_pnl_daily_excel()` | Revenue section, Expenses section, Net Profit |
| `pdf/pnl_weekly.html` | `_generate_pnl_weekly_excel()` | Daily P&L rows, Week summary |
| `pdf/pnl_monthly.html` | `_generate_pnl_monthly_excel()` | Weekly P&L summary, Monthly totals |
| `pdf/inventory_valuation.html` | `_generate_inventory_valuation_excel()` | 23 inventory items, Category totals |
| `pdf/low_stock_alerts.html` | `_generate_stock_levels_excel()` | Items with current stock, low stock highlighting |
| `pdf/production_daily.html` | `_generate_production_daily_excel()` | Batches table, Ingredients used |
| `pdf/production_weekly.html` | `_generate_production_weekly_excel()` | Daily production rows |
| `pdf/production_monthly.html` | `_generate_production_monthly_excel()` | Product summary, Weekly breakdown |
| `pdf/payroll_monthly.html` | `_generate_payroll_monthly_excel()` | Employee table, Hours, Salaries, Deductions |

### Reports to Include Excel Versions

| Report Code | Schedule | Excel Data Included |
|-------------|----------|-------------------|
| `pnl_daily` | DAILY | Revenue, expenses, profit breakdown (formatted) |
| `pnl_weekly` | WEEKLY | Daily P&L rows for the week |
| `pnl_monthly` | MONTHLY | Weekly P&L summary + monthly totals |
| `sales_daily` | DAILY | Product sales, salesperson performance tables |
| `sales_weekly` | WEEKLY | Daily sales totals with week summary |
| `sales_monthly` | MONTHLY | Product totals, salesperson ranking |
| `stock_levels` | DAILY | All 23 inventory items with stock & value |
| `inventory_valuation` | MONTHLY | Complete inventory valuation |
| `production_daily` | DAILY | Batches produced, ingredients used |
| `production_weekly` | WEEKLY | Daily production totals |
| `production_monthly` | MONTHLY | Product production summary |
| `payroll_monthly` | MONTHLY | Employee hours, salaries, deductions |

### Why This Works

| Concern | Solution |
|---------|----------|
| **Local backup** | Email attachments ARE the backup (stored in inbox) |
| **Survives Railway issues** | Email already sent, lives in Gmail/Outlook forever |
| **Professional formatting** | Excel mirrors PDF styling (headers, colors, borders) |
| **Google Drive compatible** | Opens natively in Google Sheets with formatting |
| **Data extractable** | Unlike PDF, can copy/paste, filter, sort |
| **No extra infrastructure** | Already have Django-Q, already sending emails |
| **Single dependency** | Just `openpyxl` (pure Python, no system deps) |

### SQL Database Backups

Railway handles automatic database backups. For manual backups:
- Railway Dashboard → Database → Backups → Download

No custom solution needed - Railway provides point-in-time recovery.

### Phase 8: Add Excel to Scheduled Emails

| Task | Effort |
|------|--------|
| Add `openpyxl` to requirements | 5 min |
| Add Excel style constants | 15 min |
| Add `generate_report_excel()` dispatcher | 15 min |
| Add Excel generator for `sales_daily` (template) | 30 min |
| Add Excel generators for remaining 11 report types | 2.5 hours |
| Modify `send_scheduled_reports()` | 15 min |
| Test with DAILY schedule | 15 min |
| Test with WEEKLY, MONTHLY schedules | 15 min |
| **Total** | **~4 hours** |

**Note:** This is Phase 8 (after Phases 1-7 in the main Implementation Plan).
