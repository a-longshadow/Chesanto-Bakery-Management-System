# 🔧 FOUNDATION REFACTORING PLAN
**Date:** November 26, 2025  
**Last Updated:** November 29, 2025  
**Scope:** Fix transactional flaws in Production, Inventory, and Products apps + Sales integration

**Objective:** Create solid foundation for:
1. Accuracy and Accountability in downstream apps (analytics, reports)
2. Sales app integrity (no orphaned transactions)
3. Data ownership with authenticated cross-app communication

**Approach:** Atomic utility functions with validation, row locking, and standardized responses

---

## 📚 **RELATED TECHNICAL SPECIFICATIONS**

| App | Technical Spec Document | Status |
|-----|-------------------------|--------|
| **Inventory** | `INVENTORY_APP_WORKFLOWS.md` | ✅ Complete |
| **Products** | `PRODUCTS_APP_WORKFLOWS.md` | 🔜 Pending |
| **Production** | `PRODUCTION_APP_WORKFLOWS.md` | 🔜 Pending |
| **Sales** | `SALES_APP_WORKFLOWS.md` | 🔜 Pending |

---

## 🎯 CORE ARCHITECTURAL PRINCIPLES

### ✅ **Foundational Rules:**

1. **App Ownership Principle** - Each app owns its data
2. **Atomic Transactions** - ALL foundation transactions use `@transaction.atomic`
3. **Immutability Rules:**
   - **Products:** CREATE + UPDATE + DELETE allowed (editable recipes/prices)
   - **Production:** CREATE only (no updates/deletes after batch creation)
   - **Inventory:** CREATE only (no updates/deletes after purchase)
   - **Sales:** CREATE only (no updates/deletes after dispatch/return)
   - **Exception:** Sales returns CAN update Production (product stock) and Inventory (crate stock)
4. **Real-time Tallies** - Update totals immediately (prevention-first UX)
5. **Cross-App Communication** - Only via authenticated utility functions

---

## 🔐 **CRITICAL: Authentication & Data Integrity**

### **Problem:** How does data owner authenticate external requests?

**Answer:** Validation layers + transaction boundaries + row locking

### **1. Validation Before Write (Prevention-First)**
- External apps call utility functions (NOT models directly)
- Utilities validate ALL inputs before ANY database writes
- If validation fails → return error immediately (no rollback needed)

### **2. Row Locking (Prevent Race Conditions)**
- `select_for_update()` locks row until transaction commits
- Concurrent requests are queued (wait for lock release)
- Prevents double-deduction and overselling

### **3. Transaction Boundaries (All-or-Nothing)**
- `@transaction.atomic` wraps entire operation
- If ANY step fails → ENTIRE transaction rolls back
- No partial updates possible

### **Race Condition Prevention Example:**
```
Time    Batch A (Bread)              Batch B (Scones)
----    -------------------          -------------------
10:00   Requests 5kg flour         
10:00   ✓ Locks flour row            
10:01                                 Requests 3kg flour
10:01                                 ⏳ WAITING (row locked)
10:02   ✓ Deducts 5kg              
10:02   ✓ Saves & unlocks            
10:03                                 ✓ Gets lock, checks stock
10:03                                 ✓ Deducts 3kg
```

---

## 🛡️ **Data Integrity Guarantees**

### **1. No Orphaned Transactions**
- If Production fails to deduct ingredients → No batch created
- If Dispatch fails to deduct products → No dispatch created
- If Return fails to return crates → No return closure

### **2. No Negative Stock**
- Validation BEFORE deduction
- MinValueValidator(0) on all quantity fields

### **3. No Race Conditions**
- `select_for_update()` on ALL stock-modifying queries
- Locks held until `transaction.atomic` commits

### **4. Audit Trail**
- Every utility logs: `requested_by_app`, `requested_by_user`
- Immutable records with `created_at` timestamps
- `updated_by` field tracks who modified metadata

---

## 🔒 **Utility Function Pattern**

### **Standard Signature:**
```python
@transaction.atomic
def utility_function_atomic(
    data,                    # The actual data to process
    requested_by_app=None,   # Which app is calling? 'production', 'sales', etc.
    requested_by_user=None   # Which user triggered this? (from request.user)
):
    """
    All foundation utility functions follow this pattern:
    1. Validate inputs (data integrity)
    2. Lock rows (prevent race conditions)
    3. Execute logic (all-or-nothing)
    4. Log action (audit trail)
    5. Return standardized response
    """
```

### **Standardized Response Format:**
```python
{
    'success': bool,
    'data': {},      # Result data if success
    'errors': [],    # Error messages if failed
    'message': str   # Human-readable status
}
```

---

## 🏗️ **Cross-App Communication Flow**

```
View/Form (User Action)
    ↓
App Utility (Orchestrator)
    ├─→ Own Models (Create records)
    ├─→ Other App Utility #1 (Deduct stock)
    ├─→ Other App Utility #2 (Update tallies)
    └─→ Audit Log (Record action)
    ↓
Standardized Response
    ↓
View (Show success/error to user)
```

### **Cross-App Import Rules:**
- ❌ **NEVER import models** across apps
- ✅ **ONLY import utils** across apps
- ✅ **Return dicts, not instances** (loose coupling)

---

## 📦 **PRODUCTS APP - SUMMARY**

> **Technical Spec:** `PRODUCTS_APP_WORKFLOWS.md` (pending)

### **Core Models:**
| Model | Purpose | Mutability |
|-------|---------|------------|
| **Product** | Master catalog (bread, scones, KDF, sub-products) | CREATE + UPDATE + DELETE |
| **Mix** | Recipe lookup (ingredients + quantities per product) | CREATE + UPDATE |
| **MixIngredient** | Through-table (Mix → InventoryItem) | CREATE + UPDATE |

### **Key Decisions:**
- ✅ **Sub-products support** via self-referential FK (`parent_product`)
- ✅ **Adjustable pricing** (accountant can change `selling_price`)
- ✅ **Only foundation app with full CRUD** (recipes can be edited)
- ❌ **No Mix versioning** (simple lookup, edit in place)

### **Mix Output Logic:**
- Bread: Fixed 132 packets (machine-weighed)
- Scones: Fixed 102 packets (machine-weighed)
- KDF: Variable 97-107 packets (hand-cut, allow variance)

---

## 🏭 **PRODUCTION APP - SUMMARY**

> **Technical Spec:** `PRODUCTION_APP_WORKFLOWS.md` (pending)

### **Core Models:**
| Model | Purpose | Mutability |
|-------|---------|------------|
| **ProductionBatch** | Daily production records | CREATE only |
| **ProductStock** | Real-time tally of finished products | UPDATE (via utilities) |

### **Key Decisions:**
- ❌ **No batch state complexity** (atomic = success or rollback)
- ✅ **One product per batch** (each batch = one mix = one product type)
- ✅ **Cost snapshot at creation** (from Inventory last_purchase_unit_price)
- ✅ **Actual yield tracking** (for KDF variance)

### **Cross-App Dependencies:**
- **Inventory:** Calls `deduct_ingredients_atomic()` for raw materials
- **Sales:** Exposes `deduct_products_atomic()` and `return_products_atomic()`

---

## 📊 **INVENTORY APP - SUMMARY**

> **Technical Spec:** `INVENTORY_APP_WORKFLOWS.md` ✅ **COMPLETE**

### **Architecture: Per-Item Physical Table Separation**
- 23 pre-defined inventory items
- Each item has dedicated tables (no shared monolithic tables)
- Total: 54 tables (15 ingredients × 2 + 8 indirect costs × 3 + 1 shared alerts)

### **Core Models (Per Item):**
| Model Pattern | Purpose | Items |
|---------------|---------|-------|
| **ItemXXDetails** | Metadata + running totals (singleton) | All 23 |
| **ItemXXPurchases** | Immutable purchase ledger | All 23 |
| **ItemXXOutputs** | Manual consumption tracking | Items 16-23 only |
| **StockAlert** | Alert event log (shared) | All 23 |

### **Key Decisions:**
- ✅ **Last Purchase Price** for costing (simple overwrite, no averaging)
- ✅ **Pre-defined items** via code generation (no runtime creation)
- ✅ **No InventoryAdjustment model** (bank ledger - no corrections)
- ✅ **Separate dashboards** for ingredients vs indirect costs
- ✅ **Single-item purchases** (not multi-item forms)
- ✅ **Stock alerts** via `communications.EmailService` (DRY)

### **Cross-App Utilities Exposed:**
| Utility | Caller | Purpose |
|---------|--------|---------|
| `deduct_ingredients_atomic()` | Production | Deduct for batch creation |
| `deduct_crates_atomic()` | Sales | Deduct for dispatch |
| `return_crates_atomic()` | Sales | Return from sales |

---

## 💰 **SALES APP - SUMMARY**

> **Technical Spec:** `SALES_APP_WORKFLOWS.md` (complete)

### **Core Models:**
| Model | Purpose | Mutability |
|-------|---------|------------|
| **SalesDispatch** | Products sent to salesperson (FK to `accounts.User`) | CREATE only |
| **SalesDispatchItem** | Line items per dispatch | CREATE only |
| **SalesReturn** | Products returned + settlement + optional commission | CREATE only |
| **SalesReturnItem** | Sold/returned per product | CREATE only |

### **Key Decisions:**
- ✅ **Salesperson = `accounts.User`** (FK, not separate model - Accounts owns all users)
- ✅ **Value equivalence validation** (`sold + returned = dispatched`)
- ✅ **Accountant-only returns** (prevents salesperson fraud)
- ✅ **One return per dispatch** (transaction close)
- ✅ **Cash variance tracking** (expected vs actual)
- ✅ **Commission fields on SalesReturn** (optional, doesn't affect workflow)

### **Cross-App Dependencies:**
- **Accounts:** FK to `User` for salesperson (role=SALESMAN)
- **Production:** Calls `deduct_products_atomic()` and `return_products_atomic()`
- **Inventory:** Calls `deduct_crates_atomic()` and `return_crates_atomic()`

---

## 📋 **SUMMARY: KEY ARCHITECTURAL DECISIONS**

### **Data Mutability Rules:**
| App | CREATE | UPDATE | DELETE | Notes |
|-----|--------|--------|--------|-------|
| **Products** | ✅ | ✅ | ✅ | Only app with full CRUD |
| **Production** | ✅ | ❌ | ❌ | Immutable after batch creation |
| **Inventory** | ✅ | ❌ | ❌ | Immutable after purchase (bank ledger) |
| **Sales** | ✅ | ❌ | ❌ | Immutable after dispatch/return |

### **Costing Strategy:**
| App | Strategy | Details |
|-----|----------|---------|
| **Inventory** | Last Purchase Price | Simple overwrite on each purchase |
| **Production** | Cost Snapshot | Uses Inventory `last_purchase_unit_price` at batch time |
| **Sales** | Price Snapshot | Stores `selling_price_at_dispatch` from Product |

### **Unit Standardization:**
- ✅ **Standard units:** Kilograms (kg), Liters (L), units, tokens
- ✅ **Decimal precision:** 4 decimal places for quantities, 2 for currency
- ✅ **No negatives:** MinValueValidator(0) on all quantity fields
- ✅ **Rounding:** ROUND_HALF_UP for currency calculations

### **Security & Validation:**
| Action | Role Required | Validation |
|--------|---------------|------------|
| Create Product | PRODUCT_MANAGER+ | Name unique, price > 0 |
| Update Price | ACCOUNTANT+ | Price > 0, logged |
| Create Purchase | ACCOUNTANT+ | Quantities > 0 |
| Create Dispatch | ACCOUNTANT+ | Products available |
| Process Return | ACCOUNTANT+ | Value equivalence |

---

## 🚀 **IMPLEMENTATION ROADMAP**

### **Phase 1: Inventory App** ✅
- [x] Complete technical specification
- [ ] Implement models (code generation)
- [ ] Implement utilities
- [ ] Implement views
- [ ] Test

### **Phase 2: Products App**
- [ ] Create technical specification
- [ ] Implement models
- [ ] Implement utilities
- [ ] Implement views
- [ ] Test

### **Phase 3: Production App**
- [ ] Create technical specification
- [ ] Implement models
- [ ] Implement utilities
- [ ] Implement views
- [ ] Test

### **Phase 4: Sales App**
- [ ] Create technical specification
- [ ] Implement models
- [ ] Implement utilities
- [ ] Implement views
- [ ] Test

### **Phase 5: Integration Testing**
- [ ] Cross-app flow tests
- [ ] Race condition tests
- [ ] Edge case tests

---

**Status:** ✅ High-level plan complete | Inventory spec complete | Ready for implementation
