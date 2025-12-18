# Sales App Implementation - FINAL ARCHITECTURE

## 📋 **SALES APP REQUIREMENTS ANALYSIS**

### **Core Principles:**
1. ✅ **Real-time DB operations** - No caching, calculated queries only
2. ✅ **Explicit updates** - No signals, all stock changes in views with transactions
3. ✅ **Atomic operations** - Each product/crate processed individually in loops
4. ✅ **Separate records** - Production owns truth, Sales consumes independently
5. ✅ **Soft delete with audit** - Mark deleted but preserve records
6. ✅ **One-way flow** - Once returned → no going back to production
7. ✅ **No coupling** - Production doesn't know Sales exists

---

## 🎯 **THREE MAIN FOCUS AREAS**

### **1. CRATES** (Real-time tracking)
- Source: `inventory.CrateStock` model (already exists)
- Fields: `available_crates`, `dispatched_crates`
- Operations: Deduct on dispatch, restore on return/delete

### **2. PRODUCTS** (Real-time calculated stock)
- **Production Side (Owner):** `production.DailyProduction`
  - Fields: `bread_produced`, `bread_returned`, `bread_damaged`
  - Production ONLY records: what's made + what came back
  
- **Sales Side (Consumer):** `sales.Dispatch`  
  - Fields: `bread_qty`, `kdf_qty`, `scones_qty`
  - Sales ONLY records: what left the building
  
- **Available Stock = CALCULATED QUERY (not stored):**
  ```
  SUM(DailyProduction.bread_produced) 
  - SUM(Dispatch.bread_qty WHERE deleted_at IS NULL)
  + SUM(DailyProduction.bread_returned)
  ```

### **3. SALES FIGURES** (Revenue tracking)
- Auto-calculated: `units_sold × price_per_packet`
- Recorded in `SalesReturn` model
- Immutable after return (locked transaction)

---

## 🔄 **WORKFLOW BREAKDOWN**

### **URL 1: CREATE DISPATCH** (`/sales/dispatch/create/`)

**PREVENTION STRATEGY: Make Errors Impossible**

**Form Layout - Product Table in ROWS:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ CREATE DISPATCH                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│ Salesperson: [Search by ID or Name ▼]  <- Typeahead, shows ID + Name    │
│              [#42 - John Doe - Depot] ← Selected (clear display)        │
│                                                                           │
│ Date: Nov 12, 2025 ⚠️ (Can change to: Nov 11, 10, 9 only)              │
│       └─ Future dates BLOCKED in calendar picker                        │
├─────────────────────────────────────────────────────────────────────────┤
│ Product │ Available │ Dispatch Qty │ Remaining │ Status                 │
├─────────┼───────────┼──────────────┼───────────┼────────────────────────┤
│ Bread   │ 500 ✅    │ [____] max   │ 500       │ ✓ Valid                │
│ KDF     │ 50 ⚠️     │ [____] max   │ 50        │ ⚠️ Low stock           │
│ Scones  │ 0 ❌      │ [DISABLED]   │ 0         │ ❌ Out of stock        │
├─────────┴───────────┴──────────────┴───────────┴────────────────────────┤
│ ⚠️ Warning: KDF stock is low (50 packets remaining)                     │
│                                                                           │
│ Crates Available: 25 ✅                                                  │
│ ⚠️ You'll assign crates on the next screen                              │
└─────────────────────────────────────────────────────────────────────────┘
      [Review Dispatch ↓] [Cancel]  ← Button disabled until valid
```

**Real-Time Validation (Client-Side JS):**
```javascript
// 1. SALESPERSON VALIDATION
- Typeahead search (min 2 characters)
- Show: "#42 - John Doe - Depot" (ID, name, type)
- Check existing dispatch:
  ⚠️ "John Doe already has dispatch for Nov 12. Choose different date?"
  
// 2. DATE VALIDATION
- Default: TODAY (auto-set on page load)
- Allowed: today, today-1, today-2, today-3
- Calendar picker: Future dates greyed out (disabled)
- Warning: "Selected date is 3 days ago. Confirm this is correct?"

// 3. STOCK VALIDATION (Real-time)
On quantity change:
  a. Fetch current available stock (AJAX call)
  b. Calculate: remaining = available - entered_qty
  c. Show remaining in real-time
  d. Status indicators:
     ✅ Green: remaining > 100
     ⚠️ Yellow: remaining 1-100
     ❌ Red: remaining < 0 (BLOCK SUBMISSION)
  e. Input max attribute: max={available}
  f. If stock = 0: Disable input field entirely

// 4. COMPREHENSIVE VALIDATION
At least ONE product > 0:
  - Button disabled until valid entry
  - Error: "Enter quantity for at least one product"

All quantities <= available:
  - Real-time validation per product
  - Cannot type beyond max value
  - Error: "Bread quantity exceeds available stock (500)"

// 5. WARNINGS (not errors, proceed with caution)
⚠️ Large dispatch: qty > 80% of available
⚠️ Low remaining: remaining < 50 after dispatch
⚠️ Old date: dispatch_date < today-1
⚠️ New salesperson: created in last 7 days
```

**Confirmation Modal (Before Submit):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ CONFIRM DISPATCH                                             │
├─────────────────────────────────────────────────────────────────┤
│ Salesperson: #42 - John Doe (Depot)                             │
│ Date: Nov 12, 2025                                              │
│                                                                  │
│ Products:                                                        │
│   • Bread: 450 loaves (50 remaining) ⚠️                         │
│   • KDF: 45 packets (5 remaining) ⚠️ CRITICALLY LOW             │
│   • Scones: 0 (skipped)                                         │
│                                                                  │
│ ⚠️ WARNINGS:                                                    │
│   • KDF will have only 5 packets left                           │
│   • Bread dispatch is 90% of available stock                    │
│                                                                  │
│ ✓ This dispatch cannot be edited after creation                │
│ ✓ You'll assign crates on the next screen                      │
│                                                                  │
│ Are you sure these quantities are correct?                      │
├─────────────────────────────────────────────────────────────────┤
│  [Yes, Create Dispatch]  [No, Go Back]                          │
└─────────────────────────────────────────────────────────────────┘
```

**Server-Side Validation (Belt + Suspenders):**
```python
# NEVER trust client-side validation alone!

# 1. Re-validate EVERYTHING server-side
errors = []

# Date validation
if dispatch_date > today:
    errors.append("Future dates not allowed")
if dispatch_date < today - timedelta(days=3):
    errors.append("Date too old (max 3 days back)")

# Salesperson validation
if not salesperson.is_active:
    errors.append("Salesperson is inactive")
existing = Dispatch.objects.filter(
    salesperson=salesperson,
    dispatch_date=dispatch_date,
    deleted_at__isnull=True
).exists()
if existing:
    errors.append(f"{salesperson.name} already has dispatch for {dispatch_date}")

# Stock validation (CRITICAL - use select_for_update)
with transaction.atomic():
    # Lock rows to prevent race condition
    available_bread = get_available_stock('bread', up_to_date=dispatch_date)
    
    if bread_qty > available_bread:
        errors.append(f"Bread: requested {bread_qty}, available {available_bread}")
    
    # Repeat for KDF, Scones

# At least one product
if bread_qty == 0 and kdf_qty == 0 and scones_qty == 0:
    errors.append("At least one product quantity required")

# If errors, return with detailed messages
if errors:
    return JsonResponse({'success': False, 'errors': errors}, status=400)

# All valid → Create dispatch
dispatch = Dispatch.objects.create(...)
return JsonResponse({'success': True, 'dispatch_id': dispatch.id})
```

**Error Handling:**
```python
# Wrap in try-except for database errors
try:
    with transaction.atomic():
        dispatch = Dispatch.objects.create(...)
except IntegrityError as e:
    # Unique constraint violation (salesperson + date)
    return JsonResponse({
        'success': False,
        'errors': ['Dispatch already exists for this salesperson and date']
    }, status=400)
except DatabaseError as e:
    # Log error for admin investigation
    logger.error(f"Dispatch creation failed: {e}", exc_info=True)
    return JsonResponse({
        'success': False,
        'errors': ['System error. Please try again or contact support.']
    }, status=500)
```

**User Experience Flow:**
```
1. Page loads → Date auto-set to TODAY
2. User searches salesperson → Typeahead shows matches
3. User selects → Check existing dispatch (warn if exists)
4. Stock displays → Real-time available quantities
5. User enters qtys → Real-time validation + remaining stock
6. Warnings appear → Low stock, large dispatch, etc.
7. Click "Review" → Confirmation modal with summary
8. Click "Confirm" → Server validates + creates
9. Success → Redirect to assign crates
10. Error → Show errors, keep form data, allow correction
```

**REQUIRED Fields:**
1. ✅ Salesperson (searchable dropdown with ID/name)
2. ✅ At least ONE product quantity > 0

**OPTIONAL Fields:**
- Date (defaults to today, can select up to 3 days back)
- Any combination of products (can dispatch only Bread, or only KDF, or all 3)

**Flow:**
```
1. Page loads with date = TODAY (auto-set, optional manual change)
2. User searches/selects salesperson (typeahead search - handles 50+ salespeople)
3. System calculates available stock for EACH product (real-time query):
   - Query cumulative production up to selected date
   - Subtract cumulative dispatches up to selected date
   - Add cumulative returns up to selected date
4. User enters quantities (0 to available stock per product)
5. Validation:
   a. Date: must be within (today-3) to (today) range
   b. At least one product qty > 0
   c. Each product_qty <= available_stock for that product
   d. NO future dates allowed
6. Click "Create Dispatch":
   a. ATOMIC TRANSACTION #1 (Product Dispatch):
      - Create Dispatch record (bread_qty, kdf_qty, scones_qty, date, salesperson)
      - Auto-capture: created_at = now(), created_by = current_user
      - Commit or rollback (independent of crates)
   b. Redirect to → Assign Crates page (even if crates fail later)
```

**DB Updates (ATOMIC #1 - Product Dispatch):**
```
PRODUCTION SIDE: No changes

SALES SIDE (Transaction wraps this only):
- Create Dispatch(
    salesperson_id=123,
    dispatch_date='2025-11-12',  # Auto TODAY or manual entry
    bread_qty=100,
    kdf_qty=0,      # Can be zero (not required)
    scones_qty=75,
    crates_dispatched=0,  # Not assigned yet
    created_at=now()
  )
- Available stock query automatically excludes this dispatch
- SUCCESS → Redirect to crates
- FAILURE → Rollback, show error (crates unaffected)
```

**One Dispatch Per Salesperson Per Day:**
- Validation: Check if salesperson already has dispatch for selected date
- If exists: Show error "John Doe already has a dispatch for Nov 12"
- Must edit existing dispatch instead

---

### **URL 2: ASSIGN CRATES** (`/sales/dispatch/<id>/assign-crates/`)

**Page Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ASSIGN CRATES - Dispatch #4567                                   │
├─────────────────────────────────────────────────────────────────┤
│ Salesperson: John Doe                                            │
│ Date: Nov 12, 2025                                               │
├─────────────────────────────────────────────────────────────────┤
│ Products Dispatched:                                             │
│   • Bread: 100 loaves                                            │
│   • KDF: 0 packets                                               │
│   • Scones: 75 packets                                           │
├─────────────────────────────────────────────────────────────────┤
│ Available Crates: 25                                             │
│ Assign Crates: [____] (0-25)  <- One total figure               │
└─────────────────────────────────────────────────────────────────┘
                       [Assign Crates] [Skip - No Crates]
```

**Flow:**
```
1. Auto-redirected from Create Dispatch with dispatch_id
2. Display dispatch summary (read-only)
3. Show available crates from inventory.CrateStock
4. User enters ONE total figure: 0 to available_crates
5. Validation:
   a. crates_dispatched >= 0
   b. crates_dispatched <= CrateStock.available_crates
6. Click "Assign Crates":
   a. ATOMIC TRANSACTION #2 (Crate Assignment ONLY):
      - Update inventory.CrateStock:
        * CrateStock.available_crates -= crates_dispatched
        * CrateStock.dispatched_crates += crates_dispatched
      - Update sales.Dispatch:
        * Dispatch.crates_dispatched = crates_dispatched
      - Commit or rollback (does NOT affect product dispatch from step 1)
   b. SUCCESS → Redirect to Dispatch List
   c. FAILURE → Rollback crates only, dispatch still exists with 0 crates
```

**Crate Inventory Interaction:**
- ✅ Same model as production: `inventory.CrateStock`
- ✅ Same fields: `available_crates`, `dispatched_crates`
- ✅ Same logic: Deduct from available, add to dispatched
- ✅ Sales reads/writes directly to CrateStock (no separation here)

**DB Updates (ATOMIC #2 - Crate Assignment):**
```
INVENTORY (shared):
- CrateStock.available_crates: 25 → 20
- CrateStock.dispatched_crates: 75 → 80

SALES:
- Dispatch.crates_dispatched: 0 → 5

SUCCESS: Both updates committed
FAILURE: Both rollback (dispatch exists with 0 crates, can retry crate assignment)

DECOUPLED: Product dispatch (Transaction #1) already committed and unaffected
```

**DB Updates:**
```python
crate_stock = CrateStock.objects.select_for_update().first()
crate_stock.available_crates -= crates_to_assign
crate_stock.dispatched_crates += crates_to_assign
crate_stock.save()

dispatch.crates_dispatched = crates_to_assign
dispatch.save()
```

---

### **URL 3: EDIT DISPATCH** - **DISABLED (Immutability Principle)**

**Philosophy:** Atomic transactions guarantee data consistency. Edit/Delete break that guarantee.

**Solution:** Prevention > Correction
- ✅ Make it impossible to create bad data (robust validation)
- ✅ Clear warnings and confirmations before commit
- ✅ Comprehensive error handling
- ❌ No edit/delete needed (transactions immutable after commit)

**See CREATE and RETURN sections for complete prevention strategies.**

---

### **URL 4: DELETE DISPATCH** - **DISABLED (Immutability Principle)**

**Why Disabled:**
```
Problem: Breaks atomicity and data consistency
- Stock calculation becomes unreliable
- Audit trail becomes confusing
- Race conditions between delete and new dispatch
- Creates opportunity for data manipulation

Solution: Immutable transactions
- Once committed → permanent record
- Focus on getting it right during creation
- Prevention through validation, not correction through deletion
```

**Emergency Override (SuperAdmin Only):**
```
IF absolutely necessary (e.g., test data, duplicate entry):
  - Require SuperAdmin authentication
  - Log reason for deletion
  - Send notification to management
  - Mark as "ADMIN_DELETED" (not soft delete)
  - Preserve full audit trail
```

---

### **URL 4: DELETE DISPATCH** (`/sales/dispatch/<id>/delete/`)
**Flow:**
```
1. Load Dispatch by ID
2. CHECK: Has this been returned? 
   - If YES → Block deletion, show error
   - If NO → Proceed
3. Restore crates:
   a. CrateStock.available_crates += dispatch.crates_dispatched
   b. CrateStock.dispatched_crates -= dispatch.crates_dispatched
4. SOFT DELETE:
   - dispatch.deleted_at = now()
   - dispatch.deleted_by = current_user
   - dispatch.save()
5. NO UPDATES TO PRODUCTION (separation maintained)
6. Available stock automatically increases (query excludes soft-deleted)
```

**Stock Restoration (Automatic via Query):**
```
BEFORE DELETE:
Produced: 500
Active dispatches (including this): 300
Available: 200

AFTER SOFT DELETE (dispatch.deleted_at = now):
Produced: 500
Active dispatches (WHERE deleted_at IS NULL): 250
Available: 250 ✅ (Query automatically excludes deleted dispatch!)

NO manual restoration needed - calculation is real-time!
```

---

### **URL 5: RETURN** (`/sales/dispatch/<dispatch_number>/return/`)

**PREVENTION STRATEGY: Make Errors Impossible**

**Step 1: Return Products**

**Page Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ RETURN DISPATCH: DSP-20251112-JOHN-001                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ Salesperson: John Doe (Depot)                                            │
│ Dispatch Date: Nov 12, 2025                                              │
│ Days Outstanding: 0 days ✅ (Same day return)                           │
├─────────────────────────────────────────────────────────────────────────┤
│ Product │ Dispatched │ Sold   │ Returned │ Total │ Revenue   │ Status   │
├─────────┼────────────┼────────┼──────────┼───────┼───────────┼──────────┤
│ Bread   │ 100        │ [___]  │ [___]    │ 0/100 │ Ksh 0.00  │ ❌       │
│ KDF     │ 50         │ [___]  │ [___]    │ 0/50  │ Ksh 0.00  │ ❌       │
│ Scones  │ 75         │ [___]  │ [___]    │ 0/75  │ Ksh 0.00  │ ❌       │
├─────────┴────────────┴────────┴──────────┴───────┴───────────┴──────────┤
│ Total Revenue: Ksh 0.00                                                  │
│                                                                           │
│ ⚠️ All products must be accounted for (Sold + Returned = Dispatched)    │
│ ⚠️ This action cannot be undone                                         │
└─────────────────────────────────────────────────────────────────────────┘
      [Review Return ↓] [Cancel]  ← Disabled until all valid
```

**Real-Time Validation (Client-Side JS):**
```javascript
// 1. ACCOUNTABILITY VALIDATION (Per Product)
On sold/returned input change:
  a. Calculate: total = sold + returned
  b. Calculate: deficit = dispatched - total
  c. Update "Total" column: "95/100" (95 accounted, 100 dispatched)
  d. Status indicator:
     ❌ Red: total != dispatched (MUST FIX)
     ✅ Green: total == dispatched (Valid)
  e. Show deficit: 
     deficit > 0: "⚠️ 5 units unaccounted"
     deficit < 0: "❌ Cannot exceed dispatched qty"
     deficit == 0: "✅ Fully accounted"

// 2. REVENUE CALCULATION (Real-time)
On sold input:
  a. Fetch price from Product model (AJAX)
  b. revenue = sold × price_per_packet
  c. Update revenue column immediately
  d. Update total revenue (sum all products)
  e. Show: "Ksh 4,750.00" (formatted currency)

// 3. NUMERIC VALIDATION
- Only positive integers allowed
- sold >= 0, returned >= 0
- sold + returned <= dispatched (hard limit)
- Input max: max={dispatched}

// 4. WARNINGS
⚠️ All sold, nothing returned: "No returns for {product}?"
⚠️ High returns (>20%): "30% return rate is high"
⚠️ Same day return: "Returning on same day?"
⚠️ Late return (>3 days): "5 days outstanding - verify counts"

// 5. ENABLE/DISABLE BUTTON
Button enabled ONLY when:
  ✅ All products: sold + returned == dispatched
  ✅ All revenues calculated
  ✅ No deficits
```

**Confirmation Modal (Step 1 → Step 2):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ CONFIRM PRODUCT RETURN                                       │
├─────────────────────────────────────────────────────────────────┤
│ Dispatch: DSP-20251112-JOHN-001                                 │
│ Salesperson: John Doe                                            │
│                                                                  │
│ Product Returns:                                                 │
│   • Bread: 95 sold, 5 returned → Ksh 4,750.00                  │
│   • KDF: 48 sold, 2 returned → Ksh 2,400.00                    │
│   • Scones: 70 sold, 5 returned → Ksh 3,500.00                 │
│                                                                  │
│ Total Revenue: Ksh 10,650.00                                    │
│                                                                  │
│ ✓ All products fully accounted (no deficits)                   │
│ ✓ 12 total units returned to production                        │
│                                                                  │
│ ⚠️ This will update production stock immediately                │
│ ⚠️ You'll assign returned crates on the next screen            │
│                                                                  │
│ Proceed to crate return?                                        │
├─────────────────────────────────────────────────────────────────┤
│  [Yes, Continue →]  [No, Review Again]                          │
└─────────────────────────────────────────────────────────────────┘
```

**Server-Side Validation (Step 1):**
```python
errors = []

# 1. Dispatch validation
if dispatch.is_returned:
    errors.append("Dispatch already returned")
    
if dispatch.deleted_at:
    errors.append("Dispatch has been deleted")

# 2. Accountability validation (CRITICAL)
for product in ['bread', 'kdf', 'scones']:
    dispatched = getattr(dispatch, f'{product}_qty')
    sold = request.POST.get(f'{product}_sold', 0)
    returned = request.POST.get(f'{product}_returned', 0)
    
    total = sold + returned
    deficit = dispatched - total
    
    if deficit != 0:
        errors.append(
            f"{product.title()}: {sold} sold + {returned} returned = {total}, "
            f"but {dispatched} dispatched. Deficit: {deficit}"
        )
    
    if sold < 0 or returned < 0:
        errors.append(f"{product.title()}: Negative values not allowed")

# 3. Revenue validation
bread_price = Product.objects.get(name='Bread').price_per_packet
calculated_bread_revenue = bread_sold * bread_price
submitted_bread_revenue = request.POST.get('bread_revenue')

if abs(calculated_bread_revenue - submitted_bread_revenue) > 0.01:
    errors.append("Revenue calculation mismatch (possible tampering)")

# If errors, reject
if errors:
    return JsonResponse({'success': False, 'errors': errors}, status=400)

# Save Step 1 data (NOT committed yet, just session storage)
request.session['return_data'] = {
    'bread_sold': bread_sold,
    'bread_returned': bread_returned,
    # ... etc
}
return redirect('assign_crates_return', dispatch_number=dispatch.dispatch_number)
```

---

**Step 2: Return Crates**

**Page Layout:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│ RETURN CRATES: DSP-20251112-JOHN-001                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ Product Return Summary: ✅ Completed                                    │
│   • Total Revenue: Ksh 10,650.00                                        │
│   • 12 units returned to production                                     │
├─────────────────────────────────────────────────────────────────────────┤
│ Crates Dispatched: 25                                                    │
│ Crates Returned: [___] (max 25)                                         │
│                                                                           │
│ Remaining: -- │ Deficit: -- │ Status: ❌ Required                       │
│                                                                           │
│ ⚠️ Deficit tracking: Salesperson owes unreturned crates                │
│ ⚠️ Final step: This will lock the dispatch permanently                 │
└─────────────────────────────────────────────────────────────────────────┘
      [Complete Return ✓] [Back to Products]  ← Disabled until valid
```

**Real-Time Validation (Client-Side JS):**
```javascript
// 1. CRATE VALIDATION
On crates_returned input:
  a. Validate: 0 <= crates_returned <= crates_dispatched
  b. Calculate: remaining = crates_dispatched - crates_returned
  c. Calculate: deficit = crates_dispatched - crates_returned
  d. Update display:
     - Remaining: 0 (all returned) ✅
     - Deficit: 5 (salesperson owes 5 crates) ⚠️
  e. Status indicator:
     ✅ Green: deficit == 0 (all returned)
     ⚠️ Yellow: deficit > 0 (owes crates, but allowed)
     ❌ Red: crates_returned > dispatched (BLOCK)

// 2. WARNINGS
⚠️ No crates returned: "0 crates returned - confirm?"
⚠️ High deficit (>50%): "13 crates not returned (52% deficit)"
⚠️ All crates returned: "Perfect! All 25 crates accounted for ✅"

// 3. ENABLE BUTTON
Button enabled when:
  ✅ Valid numeric input (0 to dispatched)
  ✅ No negative values
  ✅ Confirmation acknowledged
```

**Final Confirmation Modal:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚠️ FINAL CONFIRMATION - RETURN DISPATCH                         │
├─────────────────────────────────────────────────────────────────┤
│ This action is PERMANENT and cannot be undone.                  │
│                                                                  │
│ Product Returns:                                                 │
│   • Bread: 95 sold, 5 returned (Ksh 4,750.00)                  │
│   • KDF: 48 sold, 2 returned (Ksh 2,400.00)                    │
│   • Scones: 70 sold, 5 returned (Ksh 3,500.00)                 │
│   • Total Revenue: Ksh 10,650.00 ✅                             │
│                                                                  │
│ Crate Returns:                                                   │
│   • Dispatched: 25 crates                                       │
│   • Returned: 20 crates                                         │
│   • Deficit: 5 crates ⚠️ (Salesperson owes)                    │
│                                                                  │
│ System Updates:                                                  │
│   ✓ Production stock will increase by 12 units                 │
│   ✓ Inventory will receive 20 crates                           │
│   ✓ Dispatch will be LOCKED (read-only forever)                │
│   ✓ Revenue recorded: Ksh 10,650.00                            │
│                                                                  │
│ ⚠️ Deficits will be flagged for management review              │
│                                                                  │
│ Type "CONFIRM" to proceed: [__________]                         │
├─────────────────────────────────────────────────────────────────┤
│  [Complete Return] (disabled until typed) [Cancel]              │
└─────────────────────────────────────────────────────────────────┘
```

**Server-Side Validation + Atomic Transaction (Step 2):**
```python
errors = []

# 1. Retrieve Step 1 data from session
return_data = request.session.get('return_data')
if not return_data:
    return HttpResponse("Session expired. Please start over.", status=400)

# 2. Validate crates
crates_dispatched = dispatch.crates_dispatched
crates_returned = request.POST.get('crates_returned', 0)

if crates_returned < 0:
    errors.append("Negative crates not allowed")
    
if crates_returned > crates_dispatched:
    errors.append(f"Cannot return more than dispatched ({crates_dispatched})")

# 3. Calculate deficit
crate_deficit = crates_dispatched - crates_returned

# 4. Confirmation validation
confirmation = request.POST.get('confirmation', '')
if confirmation != 'CONFIRM':
    errors.append("Type CONFIRM to proceed")

if errors:
    return JsonResponse({'success': False, 'errors': errors}, status=400)

# 5. ATOMIC TRANSACTION (All or Nothing)
try:
    with transaction.atomic():
        # Get current date's DailyProduction (or create if not exists)
        daily_prod, created = DailyProduction.objects.get_or_create(
            date=timezone.now().date(),
            defaults={'bread_produced': 0, 'kdf_produced': 0, 'scones_produced': 0}
        )
        
        # Lock rows to prevent race conditions
        daily_prod = DailyProduction.objects.select_for_update().get(pk=daily_prod.pk)
        crate_stock = CrateStock.objects.select_for_update().first()
        dispatch = Dispatch.objects.select_for_update().get(pk=dispatch.pk)
        
        # Update Production (returned products)
        daily_prod.bread_returned += return_data['bread_returned']
        daily_prod.kdf_returned += return_data['kdf_returned']
        daily_prod.scones_returned += return_data['scones_returned']
        daily_prod.save()
        
        # Update Inventory (returned crates)
        crate_stock.available_crates += crates_returned
        crate_stock.dispatched_crates -= crates_returned
        crate_stock.save()
        
        # Update Dispatch (lock it!)
        dispatch.bread_sold = return_data['bread_sold']
        dispatch.bread_returned = return_data['bread_returned']
        dispatch.bread_revenue = return_data['bread_revenue']
        dispatch.bread_deficit = 0  # Already validated
        # ... repeat for KDF, Scones
        
        dispatch.crates_returned = crates_returned
        dispatch.crate_deficit = crate_deficit
        
        dispatch.is_returned = True
        dispatch.returned_at = timezone.now()
        dispatch.total_revenue = (
            return_data['bread_revenue'] + 
            return_data['kdf_revenue'] + 
            return_data['scones_revenue']
        )
        dispatch.save()
        
        # Clear session data
        del request.session['return_data']
        
        # Log success for audit
        logger.info(
            f"Dispatch {dispatch.dispatch_number} returned successfully. "
            f"Revenue: {dispatch.total_revenue}, Crate deficit: {crate_deficit}"
        )
        
        return JsonResponse({
            'success': True,
            'dispatch_number': dispatch.dispatch_number,
            'total_revenue': str(dispatch.total_revenue),
            'crate_deficit': crate_deficit
        })
        
except IntegrityError as e:
    logger.error(f"Return failed - IntegrityError: {e}", exc_info=True)
    return JsonResponse({
        'success': False,
        'errors': ['Data integrity error. Transaction rolled back. Please try again.']
    }, status=500)
    
except Exception as e:
    logger.error(f"Return failed - Unexpected error: {e}", exc_info=True)
    return JsonResponse({
        'success': False,
        'errors': ['System error. Transaction rolled back. Please contact support.']
    }, status=500)
```

**Success Response:**
```
┌─────────────────────────────────────────────────────────────────┐
│ ✅ DISPATCH RETURNED SUCCESSFULLY                               │
├─────────────────────────────────────────────────────────────────┤
│ Dispatch: DSP-20251112-JOHN-001                                 │
│ Total Revenue: Ksh 10,650.00                                    │
│                                                                  │
│ Updates Complete:                                                │
│   ✓ Production stock increased by 12 units                     │
│   ✓ 20 crates returned to inventory                            │
│   ✓ Dispatch locked (read-only)                                │
│                                                                  │
│ ⚠️ Crate Deficit: 5 crates                                     │
│   (Flagged for management review)                              │
│                                                                  │
│ [View Dispatch Details] [Return Another Dispatch] [Dashboard]   │
└─────────────────────────────────────────────────────────────────┘
```

---

## �️ **DATABASE MODELS**

### **Model 1: Salesperson**
```python
class Salesperson(models.Model):
    """
    Represents a salesperson, depot, or school.
    Used for searchable dropdown (handles 50+ entries).
    """
    id = AutoField(primary_key=True)  # For ID-based search
    name = CharField(max_length=200, unique=True)
    salesperson_type = CharField(
        max_length=20,
        choices=[
            ('PERSON', 'Individual Salesperson'),
            ('DEPOT', 'Depot'),
            ('SCHOOL', 'School'),
            ('OTHER', 'Other')
        ],
        default='PERSON'
    )
    phone = CharField(max_length=15, blank=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    
    # Audit fields
    created_by = ForeignKey(User, on_delete=PROTECT)
    updated_by = ForeignKey(User, on_delete=PROTECT, null=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            Index(fields=['name']),  # For typeahead search
            Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"#{self.id} - {self.name}"  # Display format for dropdown
```

### **Model 2: Dispatch (UNIFIED - Handles Dispatch + Return)**
```python
class Dispatch(models.Model):
    """
    UNIFIED model: Records dispatch AND return in ONE place.
    Lifecycle: Created → Crates Assigned → Returned (locked)
    """
    # ============ DISPATCH PHASE ============
    # Unique, user-friendly ID
    dispatch_number = CharField(max_length=50, unique=True, editable=False)
    # Format: "DSP-20251112-JOHN-001" (Date-Name-Sequence)
    
    salesperson = ForeignKey(Salesperson, on_delete=PROTECT)
    dispatch_date = DateField()  # User can select (today to today-3)
    
    # Product quantities dispatched
    bread_qty = PositiveIntegerField(default=0)  # Loaves
    kdf_qty = PositiveIntegerField(default=0)    # Packets
    scones_qty = PositiveIntegerField(default=0) # Packets
    
    # Crates dispatched
    crates_dispatched = PositiveIntegerField(default=0)
    
    # ============ RETURN PHASE (NULL until returned) ============
    # Products sold & returned
    bread_sold = PositiveIntegerField(null=True, blank=True)
    bread_returned = PositiveIntegerField(null=True, blank=True)
    kdf_sold = PositiveIntegerField(null=True, blank=True)
    kdf_returned = PositiveIntegerField(null=True, blank=True)
    scones_sold = PositiveIntegerField(null=True, blank=True)
    scones_returned = PositiveIntegerField(null=True, blank=True)
    
    # Revenue (calculated from sold × price)
    bread_revenue = DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    kdf_revenue = DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    scones_revenue = DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_revenue = DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Product deficits (accountability tracking)
    bread_deficit = IntegerField(null=True, blank=True)  # Can be negative (overage)
    kdf_deficit = IntegerField(null=True, blank=True)
    scones_deficit = IntegerField(null=True, blank=True)
    # Deficit = Dispatched - (Sold + Returned) → Should be 0, else accountability issue
    
    # Crates returned
    crates_returned = PositiveIntegerField(null=True, blank=True)
    crate_deficit = IntegerField(null=True, blank=True)
    # Crate Deficit = Dispatched - Returned → Salesperson owes crates
    
    # ============ STATUS TRACKING ============
    is_returned = BooleanField(default=False)  # Locks entire record
    returned_at = DateTimeField(null=True, blank=True)
    
    # Soft delete (only if NOT returned)
    deleted_at = DateTimeField(null=True, blank=True)
    deleted_by = ForeignKey(User, on_delete=PROTECT, null=True, related_name='deleted_dispatches')
    
    # ============ AUDIT ============
    created_at = DateTimeField(auto_now_add=True)
    created_by = ForeignKey(User, on_delete=PROTECT, related_name='created_dispatches')
    updated_at = DateTimeField(auto_now=True)
    updated_by = ForeignKey(User, on_delete=PROTECT, null=True, related_name='updated_dispatches')
    
    class Meta:
        ordering = ['-dispatch_date', '-created_at']
        unique_together = [['salesperson', 'dispatch_date']]  # One per day
        indexes = [
            Index(fields=['dispatch_number']),  # For search
            Index(fields=['dispatch_date']),
            Index(fields=['salesperson', 'dispatch_date']),
            Index(fields=['is_returned']),
            Index(fields=['deleted_at']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-generate dispatch_number on creation"""
        if not self.dispatch_number:
            date_str = self.dispatch_date.strftime('%Y%m%d')
            name_abbr = self.salesperson.name[:4].upper()
            # Get sequence for this salesperson + date
            existing = Dispatch.objects.filter(
                salesperson=self.salesperson,
                dispatch_date=self.dispatch_date
            ).count()
            seq = str(existing + 1).zfill(3)
            self.dispatch_number = f"DSP-{date_str}-{name_abbr}-{seq}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.dispatch_number} - {self.salesperson.name}"
```


- kdf_revenue (auto-calc)
- scones_revenue (auto-calc)
- total_revenue (auto-calc)
- crates_returned
```

**NO DispatchItem, NO SalesReturnItem** - We don't need separate tables since we only have 3 products!

---

## ✅ **ARCHITECTURE DECISIONS - CONFIRMED**

### **Unified Dispatch Model:**
- ✅ **ONE model handles everything:** Dispatch + Return data in single record
- ✅ **User-friendly IDs:** `DSP-20251112-JOHN-001` (searchable, readable in reports)
- ✅ **Lifecycle:** Created → Crates Assigned → Returned (locked)
- ✅ **Return fields nullable:** Only populated when dispatch is returned
- ✅ **Comprehensive deficits:** Product deficits + crate deficit tracked for accountability

### **Stock Calculation:**
- ✅ **Available Stock = QUERY (not stored field)**
  ```python
  # Calculate available stock up to specific date
  from django.db.models import Sum, Q
  from datetime import date
  
  def get_available_stock(product_field, up_to_date=None):
      if up_to_date is None:
          up_to_date = date.today()
      
      # Total produced up to date
      produced = DailyProduction.objects.filter(
          date__lte=up_to_date
      ).aggregate(
          total=Sum(f'{product_field}_produced')
      )['total'] or 0
      
      # Total dispatched (active only) up to date
      dispatched = Dispatch.objects.filter(
          dispatch_date__lte=up_to_date,
          deleted_at__isnull=True  # Exclude soft-deleted
      ).aggregate(
          total=Sum(f'{product_field}_qty')
      )['total'] or 0
      
      # Total returned up to date
      returned = DailyProduction.objects.filter(
          date__lte=up_to_date
      ).aggregate(
          total=Sum(f'{product_field}_returned')
      )['total'] or 0
      
      return produced - dispatched + returned
  
  # Usage:
  available_bread = get_available_stock('bread', up_to_date='2025-11-12')
  available_kdf = get_available_stock('kdf')
  available_scones = get_available_stock('scones')
  ```
- ✅ Calculated in real-time, cumulative across ALL days up to selected date
- ✅ NOT using `Product.available_stock` (removed)
- ✅ NOT using `DailyProduction.bread_dispatched` (removed concept)

### **App Separation:**
- ✅ **Production owns:** `DailyProduction` table (produced, returned, damaged)
- ✅ **Sales owns:** `Dispatch`, `SalesReturn`, `Salesperson` tables
- ✅ **One exception:** Sales WRITES to `DailyProduction.{product}_returned` on return
- ✅ **No signals:** All updates explicit in view transactions

### **Soft Delete Behavior:**
- ✅ Deleted dispatches: `dispatch.deleted_at = now()`
- ✅ Query excludes soft-deleted: `WHERE deleted_at IS NULL`
- ✅ Stock automatically restores (query-based, no manual updates)
- ✅ Audit trail preserved forever

### **Return Flow (Two-Step):**
- ✅ **Step 1:** Products (sold + returned, auto-calc revenue + deficit)
- ✅ **Step 2:** Crates (returned count, auto-calc crate deficit)
- ✅ **No damaged field:** Salesperson liability, not tracked in system
- ✅ **Validation:** sold + returned MUST equal dispatched (full accountability)
- ✅ **Atomic transaction:** Updates Dispatch + DailyProduction + CrateStock (all or nothing)
- ✅ **Post-return:** Dispatch locked forever (cannot edit/delete)

### **Edit Flow:**
- ❌ **DISABLED:** Breaks atomicity and data consistency
- ✅ **Philosophy:** Immutable transactions (prevention > correction)
- ✅ **Alternative:** Emergency SuperAdmin override only (with full audit)
- ✅ **Focus:** Comprehensive validation on CREATE and RETURN to eliminate errors

### **Deficit Tracking (Accountability):**
- ✅ **Product deficits:** `dispatched - (sold + returned)` per product
  - 0 = Perfect accountability ✅
  - \> 0 = Missing units (salesperson owes) ⚠️
  - < 0 = Impossible (validation error) ❌
- ✅ **Crate deficit:** `crates_dispatched - crates_returned`
  - 0 = All crates returned ✅
  - \> 0 = Salesperson owes crates ⚠️
  - < 0 = Impossible (validation error) ❌
- ✅ **Stored in Dispatch model:** Single source of truth for reports

### **Pricing & Revenue:**
- ✅ Get `price_per_packet` from `Product` model (current price at time of return)
- ✅ Revenue = `units_sold × price_per_packet` (auto-calculated, real-time)
- ✅ Stored per product in Dispatch: `bread_revenue`, `kdf_revenue`, `scones_revenue`
- ✅ Total revenue = sum of all three (stored in `total_revenue`)
- ✅ Immutable after return (dispatch locked)

### **Date Handling:**
- ✅ Dispatches auto-set to TODAY (optional manual change)
- ✅ Valid range: (today-3) to (today) - 4 days total window
- ✅ NO future dates allowed
- ✅ Available stock calculated up to selected date (cumulative)
- ✅ No requirement for `DailyProduction` to exist on dispatch date (query handles missing data)

### **Salesperson Selection:**
- ✅ Searchable dropdown (handles 50+ salespeople)
- ✅ Search by ID or Name (typeahead)
- ✅ Can be person, depot, school, or other
- ✅ One dispatch per salesperson per day (unique constraint)

### **Product Dispatch:**
- ✅ Table layout with products in ROWS (Bread, KDF, Scones)
- ✅ Display available stock per product (real-time query)
- ✅ Any combination allowed (can dispatch 0, 1, 2, or all 3 products)
- ✅ At least ONE product must have qty > 0
- ✅ Individual validation per product (qty <= available)

### **Prevention > Correction:**
- ✅ **CREATE:** Real-time validation, warnings, confirmation modal, server-side double-check
- ✅ **RETURN:** Accountability validation, revenue verification, deficit tracking, typed confirmation
- ✅ **User Experience:** Clear error messages, visual indicators (✅⚠️❌), disabled states
- ✅ **Error Handling:** Try-catch blocks, atomic transactions, rollback on failure, detailed logging
- ✅ **Immutability:** Once committed → permanent (forces careful entry)
- ✅ **No Edit/Delete:** Atomic transactions guarantee consistency (prevention eliminates need for correction)

---

## 🚀 **READY FOR IMPLEMENTATION**

Architecture finalized with refined dispatch flow. Awaiting explicit instruction to begin coding.