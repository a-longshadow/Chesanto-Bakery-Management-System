# Product Rejects & Waste Management

## Problem
`ReturnService.process_return()` routes returns to main product stock (Bread → Bread).
Should route to Leftovers product instead.

## Principles
- **Bank Ledger Policy**: CREATE-ONLY, no edit, no delete
- **Frontend**: Extend existing BEM classes
- **Validation**: All data validated frontend + backend (positive integers only)

---

## ACID Compliance

| Property | Implementation | Status |
|----------|----------------|--------|
| **Atomicity** | `@transaction.atomic` decorator | ✓ |
| **Consistency** | Validate stock ≥ quantity before deduction | ✓ |
| **Isolation** | `select_for_update()` locks ProductStock row | ✓ |
| **Durability** | `force_insert=True` on WasteLog | ✓ |

**Bank Ledger Enforcement:**
- `WasteLog.save()` raises `ValueError` if `self.pk` exists
- `WasteLog.delete()` raises `ValueError` always
- Sequential `waste_number` generated inside transaction

---

## Validation Rules

### Frontend (JavaScript)
```javascript
// quantity: positive integer, max = stock available
quantityInput.min = 1;
quantityInput.max = stock;
quantityInput.addEventListener('input', function() {
    const val = parseInt(this.value);
    if (isNaN(val) || val < 1) this.value = 1;
    if (val > stock) this.value = stock;
});
```

### Backend (views.py)
```python
# Following batch_create pattern:
from decimal import Decimal, InvalidOperation

try:
    qty_decimal = Decimal(str(quantity))
    qty_int = int(qty_decimal)
    if qty_int < 1:
        raise ValueError("Quantity must be at least 1")
except (InvalidOperation, ValueError):
    messages.error(request, f"Invalid quantity: '{quantity}'. Please enter a whole number.")
    return render(...)
```

### Required Fields
| Field | Type | Validation |
|-------|------|------------|
| product_id | int | Must exist, must have stock > 0 |
| quantity | int | 1 ≤ qty ≤ current_stock |
| source | str | Must be in Source.choices |
| reason | str | Required, max 100 chars |

---

## UI Best Practices (from production app)

1. **Form data preservation**: On error, re-render with `form_data` dict
2. **Helper text**: Gray text below inputs explaining field
3. **Required indicators**: Red asterisk `<span style="color: #dc2626;">*</span>`
4. **Success messages**: Include record number + summary
5. **Live preview**: Calculate P&L value as user types
6. **Pagination helpers**: `get_page_size()`, `PAGINATION_CHOICES`
7. **Filter preservation**: Pass `preserve_params` for pagination links

---

## UI Wireframes

### waste_list.html
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  WASTE HISTORY                                        [+ Dispose Waste]     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐ ┌─────────────┐ ┌───────────┐ ┌───────────┐ ┌────────┐    │
│  │ All Products│ │ All Sources │ │ Start Date│ │ End Date  │ │ Filter │    │
│  └─────────────┘ └─────────────┘ └───────────┘ └───────────┘ └────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────┐  ┌──────────────────────────────┐        │
│  │ Total Units Wasted           │  │ Total Value (P&L)            │        │
│  │ 47                           │  │ KES 2,350.00                 │        │
│  └──────────────────────────────┘  └──────────────────────────────┘        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Waste #     │ Date       │ Product         │ Qty │ Value     │ Reason     │
│  ──────────────────────────────────────────────────────────────────────────│
│  WST-1221-001│ Dec 21     │ Bread Leftovers │ 12  │ KES 600   │ Stale      │
│  WST-1220-003│ Dec 20     │ Scones Leftovers│  8  │ KES 320   │ Mold       │
│  WST-1220-002│ Dec 20     │ Bread Leftovers │ 15  │ KES 750   │ Stale      │
│  WST-1220-001│ Dec 20     │ KDF             │ 12  │ KES 420   │ Expired    │
├─────────────────────────────────────────────────────────────────────────────┤
│                           [< Prev]  Page 1 of 3  [Next >]                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### waste_dispose.html
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [← Back to Waste History]                                                  │
│                                                                             │
│  DISPOSE PRODUCT WASTE                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ ⚠️  WASTE DISPOSAL FORM                                             │   │
│  │     This action is permanent and cannot be undone.                   │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                      │   │
│  │  Product *                                                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ Bread Leftovers - 24 in stock                            ▼ │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │  Only products with stock > 0 are shown                             │   │
│  │                                                                      │   │
│  │  Quantity to Dispose *                                               │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ 12                                                          │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │  Available: 24 units                                                │   │
│  │                                                                      │   │
│  │  Source *                                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ Stale Leftovers                                          ▼ │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │  Stale Leftovers: Returned products that couldn't be resold         │   │
│  │  Expired in Bakery: Stock that went stale before dispatch           │   │
│  │                                                                      │   │
│  │  Reason *                                                            │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ Stale                                                    ▼ │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  Notes (optional)                                                    │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │                                                             │    │   │
│  │  │                                                             │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │ Estimated P&L Impact:                    KES 600.00 (loss) │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │                              [Cancel]    [🗑️ Dispose as Waste]       │   │
│  │                                                (red button)          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Naming (SETTLED)

**Database products (current state after implementation):**
| ID | Name | Parent | Active |
|----|------|--------|--------|
| 1 | Bread | - | ✓ |
| 4 | Bread Rejects | Bread | ✓ |
| 2 | Scones | - | ✓ |
| 5 | Scones Leftovers | Scones | ✓ |
| 3 | KDF | - | ✓ |
| 6 | KDF Leftovers | KDF | ✓ |
| 8 | Family Bread 800g | - | ✓ |
| 9 | Family Bread 800g Rejects | Family Bread 800g | ✓ |

**Naming convention:** Code doesn't care - uses `sub_products.filter(is_active=True).first()`. Display names can be "Rejects" or "Leftovers" - just be consistent when creating new products.

**Field names:**
- `Product.parent_product` - FK to parent
- `Product.sub_products` - reverse relation (related_name)

---

## Storage: Where is data stored?

| Data | Table | Model |
|------|-------|-------|
| Sub-product definitions | `products_product` | `Product` (with `parent_product` FK) |
| Current stock per product | `production_productstock` | `ProductStock` |
| Stock movement history | `production_productstockmovement` | `ProductStockMovement` |
| Waste disposal records | `waste_log` | `WasteLog` (NEW) |

**Flow:**
```
Return processed → ProductStock for "Bread Rejects" updated (+qty)
                 → ProductStockMovement created (type=RETURN)

Waste disposed  → ProductStock for "Bread Rejects" updated (-qty)
                → ProductStockMovement created (type=WASTE)
                → WasteLog created (immutable P&L record)
```

**Waste is NOT a separate storage location** - it's a deduction from ProductStock with an audit record in WasteLog.

---

## Integration Points

### 1. Sales Returns → Leftovers Stock (CRITICAL)

**This is the primary fix.** Every sales return currently routes back to main product. Must route to Leftovers instead.

**File:** `apps/sales/services.py`  
**Class:** `ReturnService`  
**Method:** `process_return()`  
**Lines:** ~625-638

**CURRENT CODE (BROKEN):**
```python
# Step 5: Create return items and restore stock for returned products
for item in items:
    product_id = item['product_id']
    qty_sold = item.get('qty_sold', 0)
    qty_returned = item.get('qty_returned', 0)
    
    dispatch_item = dispatch_items_map[product_id]
    
    # Create return item
    return_item = SalesReturnItem(
        sales_return=sales_return,
        product_id=product_id,
        qty_dispatched=dispatch_item.quantity,
        qty_sold=qty_sold,
        qty_returned=qty_returned,
        unit_price=dispatch_item.unit_price
    )
    return_item.save()
    
    # Restore stock for returned units
    if qty_returned > 0:
        stock_result = ProductionService.add_return_to_stock(
            product_id=product_id,  # ← BUG: Routes to main product (Bread)
            quantity=qty_returned,
            return_id=sales_return.id,
            user=user
        )
```

**NEW CODE (FIXED):**
```python
# Step 5: Create return items and restore stock for returned products
for item in items:
    product_id = item['product_id']
    qty_sold = item.get('qty_sold', 0)
    qty_returned = item.get('qty_returned', 0)
    
    dispatch_item = dispatch_items_map[product_id]
    
    # Create return item (still references original product for audit)
    return_item = SalesReturnItem(
        sales_return=sales_return,
        product_id=product_id,
        qty_dispatched=dispatch_item.quantity,
        qty_sold=qty_sold,
        qty_returned=qty_returned,
        unit_price=dispatch_item.unit_price
    )
    return_item.save()
    
    # Restore stock for returned units → route to Leftovers product
    if qty_returned > 0:
        # Get the Leftovers sub-product for this main product
        main_product = dispatch_item.product
        leftovers_product = main_product.sub_products.filter(is_active=True).first()
        
        if leftovers_product:
            target_product_id = leftovers_product.id
        else:
            # Warn but continue - don't break sales flow
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"No active Leftovers product for {main_product.name} (ID={product_id}). "
                f"Routing return to main product stock."
            )
            target_product_id = product_id
        
        stock_result = ProductionService.add_return_to_stock(
            product_id=target_product_id,
            quantity=qty_returned,
            return_id=sales_return.id,
            user=user
        )
        
        if not stock_result.get('success'):
            raise ValueError(
                f"Stock restoration failed for {main_product.name}: "
                f"{stock_result.get('error', 'Unknown error')}"
            )
```

**Edge case handling:**
| Scenario | Behavior |
|----------|----------|
| Leftovers product exists & active | Route to Leftovers ✓ |
| Leftovers product inactive | Log warning, route to main product |
| No Leftovers product defined | Log warning, route to main product |

---
| Aspect | Before | After |
|--------|--------|-------|
| Stock destination | `Bread` ProductStock | `Bread Leftovers` ProductStock |
| ProductStockMovement.product | Bread | Bread Leftovers |
| SalesReturnItem.product | Bread | Bread (unchanged - for audit) |

**Audit trail preserved:**
- `SalesReturnItem` still records original `product_id` (Bread)
- `ProductStockMovement` records movement to Leftovers product
- Clear chain: Dispatch(Bread) → Return(Bread) → Stock(Bread Leftovers)

---

### 2. Production Stock Expiry (Manual Waste Disposal)

**Entry point:** Accountant navigates to `/production/waste/dispose/`
**Flow:** Select any product with stock > 0, enter quantity, submit
**Source choices:**
- `SALES_RETURN` - disposing Leftovers stock
- `BAKERY_STOCK` - disposing main product that expired before dispatch

---

## Service Pattern (from production app)

**No signals, no DB rush. Explicit steps inside `@transaction.atomic`:**

```python
@classmethod
@transaction.atomic
def dispose_waste(
    cls,
    product_id: int,
    quantity: int,
    source: str,
    reason: str,
    user,
    notes: str = '',
    disposal_date: date = None
) -> Dict[str, Any]:
    """
    Dispose product stock as waste. CREATE-ONLY, ACID compliant.
    
    Pattern follows create_production_batch() and add_return_to_stock().
    """
    if disposal_date is None:
        disposal_date = timezone.now().date()
    
    try:
        # STEP 1: Validate product
        product = Product.objects.get(id=product_id, is_active=True)
        
        # STEP 2: Lock and validate stock
        stock = ProductStock.objects.select_for_update().get(product=product)
        
        if stock.current_stock < quantity:
            return {
                'success': False,
                'error': f"Insufficient stock: {stock.current_stock} available, {quantity} requested"
            }
        
        # STEP 3: Generate waste number
        waste_number = cls.generate_waste_number(disposal_date)
        
        # STEP 4: Calculate value
        unit_value = product.selling_price
        total_value = unit_value * Decimal(str(quantity))
        
        # STEP 5: Deduct from stock
        stock_before = stock.current_stock
        stock.current_stock -= quantity
        stock.save()
        
        # STEP 6: Create WasteLog (immutable)
        waste_log = WasteLog(
            waste_number=waste_number,
            product=product,
            quantity=quantity,
            unit_value=unit_value,
            total_value=total_value,
            source=source,
            reason=reason,
            notes=notes,
            disposal_date=disposal_date,
            disposed_by=user
        )
        waste_log.save(force_insert=True)
        
        # STEP 7: Create ProductStockMovement
        ProductStockMovement.objects.create(
            product=product,
            movement_type=ProductStockMovement.MovementType.WASTE,
            quantity=-quantity,
            stock_before=stock_before,
            stock_after=stock.current_stock,
            reference_type='WasteLog',
            reference_id=waste_log.id,
            recorded_by=user,
            notes=f"Waste disposal: {reason}"
        )
        
        return {
            'success': True,
            'data': {
                'waste_log': waste_log,
                'waste_number': waste_number,
                'product_name': product.name,
                'quantity': quantity,
                'total_value': total_value,
                'stock_before': stock_before,
                'stock_after': stock.current_stock
            }
        }
        
    except Product.DoesNotExist:
        return {'success': False, 'error': 'Product not found or inactive'}
    except ProductStock.DoesNotExist:
        return {'success': False, 'error': 'No stock record for this product'}
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Error disposing waste: {e}")
        return {'success': False, 'error': str(e)}


@staticmethod
def generate_waste_number(disposal_date: date) -> str:
    """Generate unique waste number: WST-YYYYMMDD-XXX"""
    date_str = disposal_date.strftime('%Y%m%d')
    prefix = f"WST-{date_str}-"
    
    last_waste = WasteLog.objects.filter(
        waste_number__startswith=prefix
    ).order_by('-waste_number').first()
    
    if last_waste:
        last_seq = int(last_waste.waste_number.split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1
    
    return f"{prefix}{next_seq:03d}"
```

---

## Model: WasteLog
**File:** `apps/production/models.py`

```python
class WasteLog(TimeStampedModel):
    """
    Immutable record of product waste for P&L tracking.
    CREATE-ONLY - follows bank ledger philosophy.
    """
    
    class Source(models.TextChoices):
        SALES_RETURN = 'SALES_RETURN', 'Stale Leftovers'
        BAKERY_STOCK = 'BAKERY_STOCK', 'Expired in Bakery'
    
    waste_number = models.CharField(max_length=20, unique=True, db_index=True)
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.PROTECT,
        related_name='waste_records'
    )
    quantity = models.PositiveIntegerField()
    unit_value = models.DecimalField(max_digits=10, decimal_places=2)
    total_value = models.DecimalField(max_digits=12, decimal_places=2)
    source = models.CharField(max_length=20, choices=Source.choices, db_index=True)
    reason = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    disposal_date = models.DateField(db_index=True)
    disposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='waste_disposed'
    )
    
    class Meta:
        db_table = 'waste_log'
        ordering = ['-disposal_date', '-created_at']
        indexes = [
            models.Index(fields=['disposal_date', 'product']),
        ]
    
    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("WasteLog records are immutable.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise ValueError("WasteLog records cannot be deleted.")
```

---

## Model: Add WASTE to MovementType
**File:** `apps/production/models.py`

```python
class MovementType(models.TextChoices):
    PRODUCTION = 'PRODUCTION', 'Production (batch added)'
    DISPATCH = 'DISPATCH', 'Dispatch (sent to sales)'
    RETURN = 'RETURN', 'Return (unsold from dispatch)'
    ADJUSTMENT = 'ADJUSTMENT', 'Manual adjustment'
    WASTE = 'WASTE', 'Waste disposal'  # ADD THIS
```

---

## Routes
**File:** `apps/production/urls.py`

```python
path('waste/', views.waste_list, name='waste_list'),
path('waste/dispose/', views.waste_dispose, name='waste_dispose'),
```

---

## Views
**File:** `apps/production/views.py`
- `waste_list` - GET - history with filters
- `waste_dispose` - GET/POST - disposal form

---

## Templates
- `production/waste_list.html`
- `production/waste_dispose.html`

---

## Checklist

### Pre-Implementation
- [x] Activate inactive sub-products: `Product.objects.filter(id__in=[5, 6]).update(is_active=True)`

### Implementation
- [x] Modify `ReturnService.process_return()` → route to Leftovers
- [x] Add `WasteLog` model to `apps/production/models.py`
- [x] Add `WASTE` to `ProductStockMovement.MovementType` choices
- [x] Add `generate_waste_number()` to `ProductionService`
- [x] Add `dispose_waste()` to `ProductionService`
- [x] Add `waste_list` view to `apps/production/views.py`
- [x] Add `waste_dispose` view to `apps/production/views.py`
- [x] Add URLs to `apps/production/urls.py`
- [x] Create `production/waste_list.html` template
- [x] Create `production/waste_dispose.html` template
- [x] Run `python manage.py makemigrations production`
- [x] Run `python manage.py migrate`
- [x] Add `btn--danger` CSS class to base.html
- [x] Add Waste Log to Production dropdown nav
- [x] Add Waste Management section to Production sidebar
- [x] Fix `ProductStock.get()` → `get_or_create()` for new Leftovers products

### Testing
- [x] Process a sales return → verify stock goes to Leftovers product
- [x] Dispose waste → verify stock deducted, WasteLog created
- [x] View waste list → verify records display correctly
- [ ] Check closed loop: Production + Returns = Sold + Wasted

---

## Closed Loop Accountability

**Example: 132 Bread produced**

```
Production: 132 Bread
    └→ ProductStock(Bread) = 132

Dispatch: 132 Bread
    └→ ProductStock(Bread) = 0

Sales: 100 sold, 32 returned
    └→ SalesReturnItem: product=Bread, qty_returned=32
    └→ ProductStock(Bread Rejects) = 32  ← NEW ROUTING

Next Day Dispatch: 20 Bread Rejects
    └→ ProductStock(Bread Rejects) = 12

Sales: 18 sold, 2 returned
    └→ ProductStock(Bread Rejects) = 14

Waste Disposal: 14 stale
    └→ ProductStock(Bread Rejects) = 0
    └→ WasteLog: 14 units @ KES 50 = KES 700

ACCOUNTABILITY CHECK:
  Sold:   100 + 20 - 2 + 18 - 2 = 118? 
  
  Actually simpler:
  - First dispatch sold: 100
  - Second dispatch sold: 18
  - Wasted: 14
  - Total: 100 + 18 + 14 = 132 ✓
```

**Query to verify:**
```python
# All units accounted for
produced = ProductionBatch.objects.filter(product__name='Bread').aggregate(Sum('quantity_produced'))
sold = SalesReturnItem.objects.filter(product__name='Bread').aggregate(Sum('qty_sold'))
wasted = WasteLog.objects.filter(product__parent_product__name='Bread').aggregate(Sum('quantity'))
current_stock = ProductStock.objects.filter(product__name__in=['Bread', 'Bread Rejects']).aggregate(Sum('current_stock'))

# produced = sold + wasted + current_stock
```

---

**End of Specification**
