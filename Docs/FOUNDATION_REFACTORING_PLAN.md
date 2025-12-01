# 🔧 FOUNDATION REFACTORING PLAN
**Date:** November 26, 2025  
**Last Updated:** December 1, 2025  
**Status:** ✅ **COMPLETE** - All 4 Foundation Apps Rebuilt  
**Scope:** Fix transactional flaws in Production, Inventory, Products, and Sales apps

**Objective:** Create solid foundation for:
1. Accuracy and Accountability in downstream apps (analytics, reports)
2. Sales app integrity (no orphaned transactions)
3. Data ownership with authenticated cross-app communication

**Approach:** Atomic utility functions with validation, row locking, and standardized responses

---

## 🎉 **IMPLEMENTATION COMPLETE**

| App | Status | Commit Date | Key Achievement |
|-----|--------|-------------|-----------------|
| **Inventory** | ✅ Complete | Nov 29, 2025 | 54 tables, per-item architecture |
| **Products** | ✅ Complete | Nov 30, 2025 | Recipe system with cost calculation |
| **Production** | ✅ Complete | Dec 1, 2025 | Batch creation with stock tracking |
| **Sales** | ✅ Complete | Dec 1, 2025 | Bank ledger dispatches & returns |

---

## 📚 **RELATED TECHNICAL SPECIFICATIONS**

| App | Technical Spec Document | Status |
|-----|-------------------------|--------|
| **Inventory** | `INVENTORY_APP_WORKFLOWS.md` | ✅ Complete |
| **Products** | `PRODUCTS_APP_WORKFLOWS.md` | ✅ Complete |
| **Production** | `PRODUCTION_APP_WORKFLOWS.md` | ✅ Complete |
| **Sales** | `SALES_APP_WORKFLOWS.md` | ✅ Complete |

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

## 📦 **PRODUCTS APP - IMPLEMENTATION SUMMARY**

> **Technical Spec:** `PRODUCTS_APP_WORKFLOWS.md` ✅ **COMPLETE**

### **Architecture:**
- Standard Django models (no per-item table separation)
- Full CRUD operations (only foundation app with edit/delete)
- Recipe system via Mix + MixIngredient models

### **Core Models:**
| Model | Purpose | Mutability |
|-------|---------|------------|
| **Category** | Product grouping | Full CRUD |
| **Product** | Master catalog with pricing | Full CRUD |
| **Mix** | Recipe template per product | Full CRUD |
| **MixIngredient** | Ingredient quantities per mix | Full CRUD |

### **Key Features Implemented:**
- ✅ Product catalog with categories
- ✅ Mix (recipe) system with ingredient quantities  
- ✅ Cost calculation from inventory prices
- ✅ Expected yield per mix
- ✅ Dashboard with product overview
- ✅ ACID-compliant services layer

### **Cross-App Integration:**
- **Inventory:** Reads `InventoryItemDetails.last_purchase_unit_price` for costing
- **Production:** Provides Mix data for batch creation

---

## 🏭 **PRODUCTION APP - IMPLEMENTATION SUMMARY**

> **Technical Spec:** `PRODUCTION_APP_WORKFLOWS.md` ✅ **COMPLETE**

### **Architecture:**
- Bank ledger philosophy: CREATE-ONLY, immutable batches
- Real-time stock tracking via ProductStock model
- ACID-compliant services with `@transaction.atomic`

### **Core Models:**
| Model | Purpose | Mutability |
|-------|---------|------------|
| **ProductionBatch** | Daily production records | CREATE only (immutable) |
| **ProductStock** | Real-time finished product tally | UPDATE via services only |

### **Key Features Implemented:**
- ✅ Batch creation with automatic ingredient deduction
- ✅ Cost snapshot at batch time (from inventory prices)
- ✅ Actual yield tracking with variance calculation
- ✅ Stock dashboard showing available quantities
- ✅ Row locking via `select_for_update()` prevents race conditions
- ✅ Batch detail view with ingredient breakdown

### **Cross-App Integration:**
- **Inventory:** Calls `deduct_for_production()` to deduct ingredients
- **Products:** Reads Mix data for ingredient requirements
- **Sales:** Exposes `deduct_dispatch_from_stock()` and `add_return_to_stock()`

### **Stock Flow:**
```
Production Batch Created → ProductStock.current_stock += yield
Sales Dispatch Created → ProductStock.current_stock -= dispatched
Sales Return Processed → ProductStock.current_stock += returned
```

---

## 📊 **INVENTORY APP - IMPLEMENTATION SUMMARY**

> **Technical Spec:** `INVENTORY_APP_WORKFLOWS.md` ✅ **COMPLETE**

### **Architecture: Per-Item Physical Table Separation**
- 23 pre-defined inventory items (15 ingredients + 8 indirect costs)
- Each item has dedicated tables generated via code factory
- Total: **54 tables** for complete isolation and scalability
- Dynamic model routing via `inventory.routing` module

### **Core Model Patterns (Per Item):**
| Model Pattern | Purpose | Items |
|---------------|---------|-------|
| **ItemXXDetails** | Metadata + running totals (singleton) | All 23 |
| **ItemXXPurchases** | Immutable purchase ledger | All 23 |
| **ItemXXOutputs** | Manual consumption tracking | Items 16-23 only |
| **StockAlert** | Alert event log (shared) | All 23 |

### **Key Features Implemented:**
- ✅ Bank ledger: Immutable purchase records (no edit/delete)
- ✅ Last Purchase Price costing strategy
- ✅ Separate dashboards for ingredients vs indirect costs
- ✅ Stock alerts via communications.EmailService
- ✅ Purchase history with running balance display
- ✅ Dynamic model access via `get_details_model()`, `get_purchases_model()`

### **Cross-App Utilities Exposed:**
| Utility | Caller | Purpose |
|---------|--------|---------|
| `deduct_for_production()` | Production | Deduct ingredients for batch |
| `get_item_stock_level()` | Products, Production | Check available stock |
| `get_last_purchase_price()` | Products | Get unit price for costing |

---

## 💰 **SALES APP - IMPLEMENTATION SUMMARY**

> **Technical Spec:** `SALES_APP_WORKFLOWS.md` ✅ **COMPLETE**

### **Architecture:**
- Bank ledger philosophy: CREATE-ONLY, immutable records
- No edit/delete views (dispatches and returns are permanent)
- Salesperson = `accounts.User` with `role=SALESMAN` (not separate model)

### **Core Models:**
| Model | Purpose | Mutability |
|-------|---------|------------|
| **SalesDispatch** | Products sent to salesperson | CREATE only (immutable) |
| **SalesDispatchItem** | Line items with price snapshots | CREATE only (immutable) |
| **SalesReturn** | Settlement record with commission | CREATE only (immutable) |
| **SalesReturnItem** | Sold/returned per product | CREATE only (immutable) |

### **Key Features Implemented:**
- ✅ Dispatch creation with automatic stock deduction
- ✅ Return processing with stock restoration
- ✅ Product accountability: `qty_sold + qty_returned == qty_dispatched`
- ✅ Crate tracking: returned, lost, damaged
- ✅ Commission calculation with 20% max cap
- ✅ Sales and commission reports with filters
- ✅ Dashboard with today's activity overview

### **Cross-App Integration:**
- **Accounts:** FK to `User` for salesperson (role=SALESMAN)
- **Products:** FK to Product for dispatch items
- **Production:** Calls `deduct_dispatch_from_stock()` on dispatch
- **Production:** Calls `add_return_to_stock()` on return

### **Business Rules Enforced:**
- One dispatch per salesperson per day
- One return per dispatch (closes the transaction)
- Returns must account for all dispatched products
- Commission cannot exceed 20% of revenue

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

### **Phase 1: Inventory App** ✅ Complete (Nov 29, 2025)
- [x] Complete technical specification
- [x] Implement models (54 tables via code generation)
- [x] Implement services with ACID compliance
- [x] Implement views and templates
- [x] Test immutability enforcement

### **Phase 2: Products App** ✅ Complete (Nov 30, 2025)
- [x] Create technical specification
- [x] Implement models (Category, Product, Mix, MixIngredient)
- [x] Implement services with cost calculation
- [x] Implement views and templates
- [x] Test recipe/mix system

### **Phase 3: Production App** ✅ Complete (Dec 1, 2025)
- [x] Create technical specification
- [x] Implement models (ProductionBatch, ProductStock)
- [x] Implement services with stock management
- [x] Implement views and templates
- [x] Test batch creation and stock flow

### **Phase 4: Sales App** ✅ Complete (Dec 1, 2025)
- [x] Create technical specification
- [x] Implement models (Dispatch, Return, line items)
- [x] Implement services with accountability checks
- [x] Implement views and templates
- [x] Test dispatch/return workflow

### **Phase 5: Integration & UI** ✅ Complete (Dec 1, 2025)
- [x] Update main navbar with all 4 apps
- [x] Update homepage (5/8 apps complete)
- [x] Cross-app flow verification
- [x] URL routing and template fixes

---

## 📈 **NEXT STEPS (Post-Foundation)**

The foundation is complete. Remaining apps to build:

| App | Purpose | Dependencies |
|-----|---------|--------------|
| **Reports** | Daily/weekly/monthly automated reports | All foundation apps |
| **Analytics** | Dashboard with charts | All foundation apps |
| **Payroll** | Employee payroll & deductions | Accounts |

---

**Status:** ✅ **FOUNDATION COMPLETE** | All 4 apps rebuilt with ACID compliance | Ready for Reports/Analytics phase
