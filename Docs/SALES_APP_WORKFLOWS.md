# SALES APP - COMPLETE TECHNICAL SPECIFICATION

**Document Version:** 2.2 (Foundation Rebuild)  
**Created:** November 30, 2025  
**Last Updated:** December 2, 2025  
**App:** `apps/sales/`  
**Purpose:** Dispatch finished goods to salespeople, track returns, record commissions

---

## TABLE OF CONTENTS

1. [Overview & Position in System](#1-overview--position-in-system)
2. [Key Architectural Decisions](#2-key-architectural-decisions)
3. [Data Models](#3-data-models)
4. [Workflows & State Machines](#4-workflows--state-machines)
5. [Service Layer](#5-service-layer)
6. [Cross-App Integration](#6-cross-app-integration)
7. [Views & URL Routing](#7-views--url-routing)
8. [Forms & Validation](#8-forms--validation)
9. [Admin Configuration](#9-admin-configuration)
10. [Templates Reference](#10-templates-reference)
11. [Seeding & Initial Data](#11-seeding--initial-data)
12. [Testing Strategy](#12-testing-strategy)

---

## 1. OVERVIEW & POSITION IN SYSTEM

### 1.1 App Purpose

The Sales App manages the **dispatch-return cycle** for finished goods:

1. **Dispatch:** Allocate products from Production stock to salespeople
2. **Return:** Process end-of-day returns with full accountability (sold + returned = dispatched)
3. **Commission:** Record salesperson earnings (manually entered by Accountant)

### 1.2 Position in App Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHESANTO BAKERY SYSTEM                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐   ┌───────────┐   ┌────────────┐   ┌─────────┐  │
│   │ PRODUCTS │ → │ INVENTORY │ → │ PRODUCTION │ → │  SALES  │  │
│   │ (Catalog)│   │  (Stock)  │   │ (Batches)  │   │(Dispatch)│  │
│   └──────────┘   └───────────┘   └────────────┘   └─────────┘  │
│                                                                 │
│   Data Flow: LEFT to RIGHT                                      │
│   Dependency: Each app depends on apps to its LEFT              │
│                                                                 │
│   Products  → Defines Mix recipes (what products exist)         │
│   Inventory → Tracks raw materials (ingredients, packaging)     │
│   Production → Creates finished goods (uses Products+Inventory) │
│   Sales     → Dispatches finished goods (uses Production)       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 What Sales OWNS

| Entity | Description |
|--------|-------------|
| `SalesDispatch` | Daily dispatch record per salesperson (FK to `accounts.User`) |
| `SalesDispatchItem` | Line items (product quantities) per dispatch |
| `SalesReturn` | End-of-day return/settlement record (includes commission fields) |
| `SalesReturnItem` | Line items with sold/returned breakdown |

### 1.4 What Sales READS (Does Not Modify Directly)

| Entity | Source App | Purpose |
|--------|------------|---------|
| `User` | Accounts | Get salesperson (role=SALESMAN) for dispatch |
| `Product` | Products | Get product names, prices |
| `ProductStock` | Production | Check available stock before dispatch |

### 1.5 What Sales CALLS (Via Utility Functions)

| Utility | Source App | Purpose |
|---------|------------|---------|
| `deduct_dispatch_from_stock()` | Production | Deduct dispatched units |
| `add_return_to_stock()` | Production | Add returned units back |
| `deduct_crates_atomic()` | Inventory | Dispatch crates to salesperson |
| `return_crates_atomic()` | Inventory | Process crate returns |

### 1.6 Key Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Models | 4 | Dispatch, DispatchItem, Return, ReturnItem |
| Views | 12 | CRUD + reports |
| Templates | 7 | Preserved from existing app |
| Atomic Operations | 2 | create_dispatch, process_return |

---

## 2. KEY ARCHITECTURAL DECISIONS

### 2.1 Design Principles

| # | Principle | Implementation |
|---|-----------|----------------|
| 1 | **ACID Compliance** | All dispatch/return operations use `@transaction.atomic` |
| 2 | **Immutable Returns** | Once created, SalesReturn is PERMANENT (no edit/delete) |
| 3 | **Row Locking** | Use `select_for_update()` for ProductStock during creation |
| 4 | **FK to Product** | DispatchItem/ReturnItem link to Product model (not hardcoded fields) |
| 5 | **Server-Side Validation** | Commission max (20% of revenue) validated in Python |
| 6 | **Accountability Validation** | `sold + returned = dispatched` enforced at database level |
| 7 | **NO DELETE** | Dispatches and Returns are permanent records (bank ledger) |
| 8 | **NO EDIT** | Once created, records are immutable (except crate lost/damaged booleans) |
| 9 | **Audit Trail** | All records track `created_by`, timestamps |

### 2.2 Bank Ledger Philosophy

> **CRITICAL: Sales operates like a BANK LEDGER**
>
> - **NO DELETE** - Dispatches and Returns are permanent records
> - **NO EDIT** - Once created, records cannot be modified
> - **NO ADJUSTMENTS** - No "correction" or "reversal" records
> - **NO CANCELLATIONS** - A dispatch cannot be cancelled
>
> **Why?** Because you can't walk into a bank and say "that $10 withdrawal I made yesterday, can you change it to $8?"
>
> **How to prevent errors:**
> - Comprehensive validation before creation
> - Preview/confirmation screens
> - AJAX real-time feedback
> - Helper text and warnings
> - Once submitted = PERMANENT

### 2.3 Critical Decisions Table

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|---------------------|
| 1 | **Separate Dispatch and Return models** | Clear state machine, easier auditing | Unified model with phases |
| 2 | **DispatchItem with FK to Product** | Flexible for any number of products | Hardcoded product fields |
| 3 | **Commission fields on SalesReturn** | Simple, no extra model needed | Separate Commission model |
| 4 | **ProductStock integration via Production utilities** | Single source of truth for stock | Direct writes to ProductStock |
| 5 | **One dispatch per salesperson per day** | Prevents confusion, matches business reality | Multiple dispatches allowed |
| 6 | **Return required to close dispatch** | Complete accountability chain | Open-ended dispatches |
| 7 | **Immutable records (bank ledger)** | Data integrity, audit compliance | Edit/delete allowed |

### 2.4 State Machine: Dispatch Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                  DISPATCH STATE MACHINE (BANK LEDGER)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐                                                  │
│   │  START   │                                                  │
│   └────┬─────┘                                                  │
│        │ User submits dispatch form                             │
│        │ (validated, confirmed, PERMANENT)                      │
│        ▼                                                        │
│   ┌────────────┐                                                │
│   │ DISPATCHED │ ◄── Stock deducted, record created            │
│   │ (PERMANENT)│     NO EDIT, NO DELETE, NO CANCEL              │
│   └─────┬──────┘                                                │
│         │                                                       │
│         │ Process Return (end of day)                           │
│         ▼                                                       │
│   ┌────────────┐                                                │
│   │  RETURNED  │ ◄── Return processed, commission recorded     │
│   │ (PERMANENT)│     NO EDIT, NO DELETE                         │
│   └────────────┘                                                │
│                                                                 │
│   🔒 BOTH STATES ARE PERMANENT AND IMMUTABLE                   │
│   📌 No PENDING, CANCELLED, or DELETED states exist            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 Immutability Rules

```python
# ALL Sales records are immutable (bank ledger)

class SalesDispatch(TimeStampedModel):
    def save(self, *args, **kwargs):
        if self.pk:  # Existing record - only return status allowed
            original = SalesDispatch.objects.get(pk=self.pk)
            allowed_changes = {'is_returned', 'returned_at', 'status'}
            for field in self._meta.fields:
                if field.name in allowed_changes:
                    continue  # Skip - these ARE allowed to change (once, via SalesReturn creation)
                if getattr(self, field.name) != getattr(original, field.name):
                    raise ValueError(f"SalesDispatch.{field.name} is immutable. Bank ledger policy.")
            # Additional validation: is_returned can only go False → True (never reversed)
            if original.is_returned and not self.is_returned:
                raise ValueError("Cannot un-return a dispatch. Bank ledger policy.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise ValueError("SalesDispatch records cannot be deleted. Bank ledger policy.")

class SalesReturn(TimeStampedModel):
    def save(self, *args, **kwargs):
        if self.pk:  # Existing record - only crate booleans allowed
            original = SalesReturn.objects.get(pk=self.pk)
            allowed_changes = {'crates_marked_lost', 'crates_marked_damaged'}
            for field in self._meta.fields:
                if field.name in allowed_changes:
                    continue  # Skip - these ARE allowed to change
                if getattr(self, field.name) != getattr(original, field.name):
                    raise ValueError(f"SalesReturn.{field.name} is immutable. Bank ledger policy.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise ValueError("SalesReturn records cannot be deleted. Bank ledger policy.")

# NOTE: The ONLY exception is crate tracking booleans on SalesReturn
# (crates may be returned/found later - this is a status update, not data edit)

# Item models also immutable (no save override needed - just admin protection)
# SalesDispatchItem and SalesReturnItem inherit same policy via admin controls
```

### 2.6 Commission System (Manual Entry)

```
┌─────────────────────────────────────────────────────────────────┐
│                  COMMISSION SYSTEM                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  COMMISSION IS OPTIONAL & MANUAL                                │
│  ───────────────────────────────                                │
│  • Enabled/disabled per salesperson on accounts.User            │
│  • If user.commission_enabled = False → field hidden            │
│  • If enabled → Accountant enters commission amount manually    │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  HOW IT WORKS                                                   │
│  ─────────────                                                  │
│  1. Accountant processes return                                 │
│  2. If salesperson.commission_enabled = True:                   │
│     → Show commission input field                               │
│     → Accountant enters amount: [ KES _______ ]                 │
│  3. System validates: 0 ≤ amount ≤ 20% of revenue               │
│  4. Store in SalesReturn.commission_amount                      │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  VALIDATION                                                     │
│  ──────────                                                     │
│  • Minimum: KES 0                                               │
│  • Maximum: 20% of total_revenue (configurable cap)             │
│  • Example: Revenue = KES 10,000 → Max commission = KES 2,000   │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  STORAGE                                                        │
│  ───────                                                        │
│  • SalesReturn.commission_amount = Decimal (nullable)           │
│  • NULL if commission not enabled for salesperson               │
│  • NO rate/type fields needed - just the final amount           │
│                                                                 │
│  NOTE: Bonus structures and performance incentives are          │
│  handled by the Payroll App, not Sales.                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.6 Accountability Rule (No Deficits)

> 🔒 **CORE BUSINESS RULE:** For every product dispatched:
> 
> **`qty_sold + qty_returned = qty_dispatched`**
> 
> - Accountant enters `qty_sold` and `qty_returned` per product (from salesperson report)
> - System VALIDATES the sum equals dispatched quantity
> - System AUTO-CALCULATES revenue from `qty_sold × unit_price`
> - **NO manual cash entry** → NO deficit possible

### 2.7 Crate Accountability Rule

> 🔒 **CRATE BUSINESS RULE:**
> 
> **`crates_returned + crates_lost + crates_damaged = crates_dispatched`**
> 
> - Accountant enters `crates_returned`, `crates_lost`, `crates_damaged` at return time
> - System VALIDATES the sum equals crates dispatched
> - Lost/damaged records are **PERMANENT** (bank ledger)
> - `crates_marked_lost` / `crates_marked_damaged` booleans can be updated later (when salesperson resolves)
> - Actual crate replacement happens via **Inventory purchase**, not Sales adjustment

### 2.8 Permission Model

| Action | Minimum Role | Notes |
|--------|--------------|-------|
| Create Dispatch | ACCOUNTANT | Accountant allocates stock to salesperson |
| Process Return | ACCOUNTANT | Accountant records sold/returned quantities |
| View Dispatches | ACCOUNTANT | Read access to dispatch list |
| View Reports | ACCOUNTANT | Sales reports, commission reports |
| Admin Access | SUPERADMIN | Full admin panel access |

> **NOTE:** Salespeople do NOT access this app directly. They report to the Accountant who enters the data.

---

## 3. DATA MODELS

### 3.1 Model Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    SALES APP MODELS                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   accounts.User (role=SALESMAN) ◄──────── FK ──────────────┐   │
│   (Commission config lives in Accounts, NOT Sales)          │   │
│                                                              │   │
│   SalesDispatch ──────1:N────────▶ SalesDispatchItem        │   │
│        │                                │                    │   │
│        │ 1:1                            └──▶ Product (FK)    │   │
│        ▼                                                     │   │
│   SalesReturn ───────1:N────────▶ SalesReturnItem           │   │
│   (includes commission fields)          │                    │   │
│                                         └──▶ Product (FK)    │   │
│                                                              │   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Salesperson Design Note

> **IMPORTANT:** Salesperson = `accounts.User` with `role=SALESMAN`
> 
> - NOT a separate model in Sales App
> - `commission_enabled` boolean lives on User (only field needed)
> - `SalesDispatch.salesperson` = FK to `accounts.User`
> - Forms filter to `role=SALESMAN` users

### 3.3 Model: SalesDispatch

**Table:** `sales_dispatch`

| Field | Type | Rules |
|-------|------|-------|
| `dispatch_number` | CharField(20) | Auto: DSP-YYYYMMDD-XXX |
| `salesperson` | FK(User) | `limit_choices_to={'role': 'SALESMAN'}` |
| `dispatch_date` | DateField | Required |
| `status` | CharField | DISPATCHED / RETURNED (only 2 states) |
| `crates_dispatched` | PositiveInt | Default 0 |
| `is_returned` | Boolean | Default False, set True when return processed |
| `returned_at` | DateTimeField | Nullable, set when return processed |
| `created_by` | FK(User) | Audit |
| `created_at` | DateTimeField | Auto |

**Constraints:**
- `unique_together = ['salesperson', 'dispatch_date']`
- **IMMUTABLE** except `is_returned`, `returned_at`, `status` (set once when return processed)

**Properties:** `total_units`, `expected_revenue`

### 3.4 Model: SalesDispatchItem

**Table:** `sales_dispatch_item`

| Field | Type | Rules |
|-------|------|-------|
| `dispatch` | FK(SalesDispatch) | CASCADE |
| `product` | FK(Product) | PROTECT |
| `quantity` | PositiveInt | Required |
| `unit_price` | Decimal(10,2) | Snapshot at dispatch |

**Constraints:**
- `unique_together = ['dispatch', 'product']`
- **IMMUTABLE** - no edits, no deletes (bank ledger)

### 3.5 Model: SalesReturn

**Table:** `sales_return`

| Field | Type | Rules |
|-------|------|-------|
| `dispatch` | OneToOne(SalesDispatch) | PROTECT |
| `return_date` | DateField | Required |
| `total_units_sold` | PositiveInt | Calculated from items |
| `total_revenue` | Decimal(12,2) | Calculated: sum(qty_sold × unit_price) |
| **Crate Fields** | | |
| `crates_returned` | PositiveInt | Required |
| `crates_lost` | PositiveInt | Default 0 |
| `crates_damaged` | PositiveInt | Default 0 |
| **Crate Resolution Status (only mutable fields)** | | |
| `crates_marked_lost` | Boolean | Default False, set True when lost crates resolved |
| `crates_marked_damaged` | Boolean | Default False, set True when damaged crates resolved |
| **Commission (manual entry)** | | |
| `commission_amount` | Decimal(12,2) | NULL if not enabled, manually entered by Accountant |
| **Audit** | | |
| `created_by` | FK(User) | Audit |
| `created_at` | DateTimeField | Auto |

**Constraints:**
- `crates_returned + crates_lost + crates_damaged == dispatch.crates_dispatched` (enforced on save)

**Notes:**
- **IMMUTABLE** except `crates_marked_lost`, `crates_marked_damaged` (can be marked True later when resolved)
- No deficit fields - system enforces sold + returned = dispatched
- Revenue is calculated, not manually entered
- Commission is manually entered (not calculated)
- Lost/damaged crates are NOT adjusted here - replacement is via Inventory purchase

### 3.6 Model: SalesReturnItem

**Table:** `sales_return_item`

| Field | Type | Rules |
|-------|------|-------|
| `sales_return` | FK(SalesReturn) | CASCADE |
| `product` | FK(Product) | PROTECT |
| `qty_dispatched` | PositiveInt | Snapshot |
| `qty_sold` | PositiveInt | Required |
| `qty_returned` | PositiveInt | Required |
| `unit_price` | Decimal(10,2) | From dispatch |
| `revenue` | Decimal(12,2) | Auto: qty_sold × unit_price |

**Constraints:**
- `unique_together = ['sales_return', 'product']`
- **VALIDATION:** `qty_sold + qty_returned == qty_dispatched` (enforced on save)
- **IMMUTABLE** - no edits, no deletes (bank ledger)

### 3.7 Commission Design Note

> **Commission = single optional field on SalesReturn**
> - Manually entered by Accountant at return time
> - If `salesperson.commission_enabled = False` → field hidden, stored as NULL
> - If enabled → Accountant enters amount, validated against 20% cap
> - Does NOT affect sales workflow or settlement

### 3.8 Models Summary Table (Bank Ledger)

| Model | Table | Mutable? |
|-------|-------|----------|
| SalesDispatch | `sales_dispatch` | **ONCE:** `is_returned`, `returned_at`, `status` (via return) |
| SalesDispatchItem | `sales_dispatch_item` | **NEVER** (immutable from creation) |
| SalesReturn | `sales_return` | **ONLY:** `crates_marked_lost`, `crates_marked_damaged` |
| SalesReturnItem | `sales_return_item` | **NEVER** (immutable from creation) |

**Total: 4 models** (Salesperson = accounts.User, Commission = fields on SalesReturn)

> 🏦 **BANK LEDGER POLICY:** No edits, no deletes, no adjustments, no reversals.

---

## 4. WORKFLOWS & STATE MACHINES

### 4.1 Workflow Overview

> **All workflows require ACCOUNTANT role or higher**

```
┌─────────────────────────────────────────────────────────────────┐
│                    SALES APP WORKFLOWS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  WORKFLOW 1: Create Dispatch (Accountant)                       │
│  ─────────────────────────────────────────                      │
│  Accountant selects salesperson + products → Stock deducted →  │
│  Dispatch created → ProductStockMovement records created       │
│                                                                 │
│  WORKFLOW 2: Process Return (Accountant)                        │
│  ────────────────────────────────────────                       │
│  Accountant enters sold/returned quantities → System validates │
│  sold + returned = dispatched → Stock restored → Commission    │
│  calculated → Return complete                                   │
│                                                                 │
│  WORKFLOW 3: View Sales Report (Accountant)                     │
│  ───────────────────────────────────────────                    │
│  Date range filter → Daily sales by salesperson →              │
│  Revenue totals displayed                                       │
│                                                                 │
│  WORKFLOW 4: View Commission Report (Accountant)                │
│  ───────────────────────────────────────────────                │
│  Month filter → Monthly commissions per salesperson →          │
│  Grand totals displayed                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Workflow 1: Create Dispatch

**Trigger:** Accountant clicks "New Dispatch" button  
**Permission:** ACCOUNTANT or higher  
**Owner:** Sales App  
**Integration:** Production App (stock deduction)

#### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                 CREATE DISPATCH WORKFLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STEP 1: Display Form                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Load active salespeople dropdown                      │   │
│  │ • Load available products from ProductStock             │   │
│  │ • Display current stock levels                          │   │
│  │ • Pre-fill dispatch_date with today                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  STEP 2: Accountant Input                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Select salesperson                                    │   │
│  │ • Enter quantities for each product                     │   │
│  │ • Enter crates count                                    │   │
│  │ • Submit form                                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  STEP 3: Validation (Pre-Transaction)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Check salesperson is active                           │   │
│  │ • Check no existing dispatch for salesperson+date       │   │
│  │ • Check stock availability for each product             │   │
│  │ • Check crate availability                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│              ┌───────────┴───────────┐                          │
│              ▼                       ▼                          │
│         VALID                    INVALID                        │
│              │                       │                          │
│              │                       ▼                          │
│              │              ┌─────────────────┐                 │
│              │              │ Show Errors     │                 │
│              │              │ Return to Form  │                 │
│              │              └─────────────────┘                 │
│              ▼                                                  │
│  STEP 4: Atomic Transaction                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ BEGIN TRANSACTION                                       │   │
│  │                                                         │   │
│  │ 4a. Lock ProductStock rows (select_for_update)          │   │
│  │                                                         │   │
│  │ 4b. Re-validate stock availability (inside transaction) │   │
│  │                                                         │   │
│  │ 4c. Create SalesDispatch record                         │   │
│  │                                                         │   │
│  │ 4d. For each product:                                   │   │
│  │     • Create SalesDispatchItem                          │   │
│  │     • Call Production.deduct_dispatch_from_stock()      │   │
│  │       (creates ProductStockMovement record)             │   │
│  │                                                         │   │
│  │ 4e. Dispatch crates via Inventory utility               │   │
│  │                                                         │   │
│  │ COMMIT                                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  STEP 5: Success Response                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Flash success message                                 │   │
│  │ • Display any warnings (low stock alerts)               │   │
│  │ • Redirect to dispatch detail page                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Create Dispatch Form UI

```
┌─────────────────────────────────────────────────────────────────┐
│              NEW DISPATCH                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DISPATCH INFORMATION                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Salesperson:  [▼ Select Salesperson ───────────────── ] │   │
│  │ Dispatch Date: [2025-11-30] (📅)                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  PRODUCTS                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Product        │ Available │ Dispatch Qty │ Unit Price │   │
│  │────────────────┼───────────┼──────────────┼────────────│   │
│  │ 🍞 Bread       │    264    │ [    100   ] │ KES 80.00  │   │
│  │ 🥯 KDF         │    156    │ [     50   ] │ KES 50.00  │   │
│  │ 🥮 Scones      │    210    │ [     75   ] │ KES 40.00  │   │
│  │────────────────┴───────────┴──────────────┴────────────│   │
│  │                              Expected Revenue: KES 13,500│   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  CRATES                                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Available Crates: 45                                    │   │
│  │ Crates to Dispatch: [    10   ]                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        [ Cancel ]              [ Create Dispatch ]       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Workflow 2: Process Return

**Trigger:** Accountant clicks "Process Return" on dispatch detail page  
**Permission:** ACCOUNTANT or higher  
**Owner:** Sales App  
**Integration:** Production App (stock restoration), Inventory App (crate return)

#### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                 PROCESS RETURN WORKFLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STEP 1: Load Dispatch Context                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Fetch dispatch with all items                         │   │
│  │ • Verify dispatch is not already returned               │   │
│  │ • Display dispatched quantities for reference           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  STEP 2: Accountant Input (from salesperson's report)           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ For each product:                                       │   │
│  │ • Display qty_dispatched (read-only)                    │   │
│  │ • Enter qty_sold                                        │   │
│  │ • Enter qty_returned                                    │   │
│  │ (JavaScript validates: sold + returned = dispatched)    │   │
│  │                                                         │   │
│  │ Enter crate accountability:                             │   │
│  │ • Crates returned (good condition)                      │   │
│  │ • Crates lost (salesperson lost them)                   │   │
│  │ • Crates damaged (returned damaged)                     │   │
│  │ (JavaScript validates: sum = crates_dispatched)         │   │
│  │                                                         │   │
│  │ Auto-calculated (read-only display):                    │   │
│  │ • Total revenue (sum of qty_sold × unit_price)          │   │
│  │ • Commission amount (if enabled for salesperson)        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  STEP 3: Server-Side Validation                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Verify dispatch exists and not returned               │   │
│  │ • For each product:                                     │   │
│  │   VALIDATE: sold + returned == dispatched               │   │
│  │   (reject if not equal - no exceptions!)                │   │
│  │ • Validate crates:                                      │   │
│  │   returned + lost + damaged == crates_dispatched        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│              ┌───────────┴───────────┐                          │
│              ▼                       ▼                          │
│         VALID                    INVALID                        │
│              │                       │                          │
│              │                       ▼                          │
│              │              ┌─────────────────┐                 │
│              │              │ Show Errors     │                 │
│              │              │ Return to Form  │                 │
│              │              └─────────────────┘                 │
│              ▼                                                  │
│  STEP 4: Atomic Transaction                                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ BEGIN TRANSACTION                                       │   │
│  │                                                         │   │
│  │ 4a. Lock dispatch record (select_for_update)            │   │
│  │                                                         │   │
│  │ 4b. Re-verify dispatch not returned                     │   │
│  │                                                         │   │
│  │ 4c. Create SalesReturn record                           │   │
│  │     (total_revenue calculated from items)               │   │
│  │                                                         │   │
│  │ 4d. For each product:                                   │   │
│  │     • Create SalesReturnItem                            │   │
│  │     • If qty_returned > 0:                              │   │
│  │       Call Production.add_return_to_stock()             │   │
│  │       (creates ProductStockMovement record)             │   │
│  │                                                         │   │
│  │ 4e. Return ONLY good crates via Inventory utility       │   │
│  │     (lost/damaged crates NOT added back to inventory)   │   │
│  │                                                         │   │
│  │ 4f. Calculate commission (if enabled for salesperson)   │   │
│  │                                                         │   │
│  │ 4g. Update dispatch: is_returned=True, returned_at=now  │   │
│  │                                                         │   │
│  │ COMMIT → RECORD IS NOW PERMANENT                        │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│                          ▼                                      │
│  STEP 5: Post-Commit Actions                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • Flash success message with revenue and commission     │   │
│  │ • Redirect to dispatch detail page                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Process Return Form UI

```
┌─────────────────────────────────────────────────────────────────┐
│              PROCESS RETURN - DSP-20251130-001                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  DISPATCH SUMMARY                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Salesperson: John Mutua (👤 Individual)                 │   │
│  │ Dispatch Date: November 30, 2025                        │   │
│  │ Crates Dispatched: 10                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  RETURN QUANTITIES (sold + returned must equal dispatched)     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Product   │ Dispatched │ Sold     │ Returned │ Status  │   │
│  │───────────┼────────────┼──────────┼──────────┼─────────│   │
│  │ 🍞 Bread  │    100     │ [   95 ] │ [    5 ] │ ✅ 100  │   │
│  │ 🥯 KDF    │     50     │ [   48 ] │ [    2 ] │ ✅  50  │   │
│  │ 🥮 Scones │     75     │ [   70 ] │ [    5 ] │ ✅  75  │   │
│  │───────────┴────────────┴──────────┴──────────┴─────────│   │
│  │                        Total Sold: 213 units            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  AUTO-CALCULATED REVENUE (read-only)                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Bread (95 × KES 50):    KES  4,750.00                   │   │
│  │ KDF (48 × KES 30):      KES  1,440.00                   │   │
│  │ Scones (70 × KES 25):   KES  1,750.00                   │   │
│  │ ──────────────────────────────────────                  │   │
│  │ TOTAL REVENUE:          KES  7,940.00                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  CRATES (returned + lost + damaged must equal dispatched)      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Dispatched: 10                                          │   │
│  │ Returned:   [     8     ]                               │   │
│  │ Lost:       [     1     ]                               │   │
│  │ Damaged:    [     1     ]                               │   │
│  │ ───────────────────────────────────                     │   │
│  │ Total: 10 ✅ (matches dispatched)                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  COMMISSION (if enabled for salesperson)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 💰 COMMISSION                                           │   │
│  │                                                         │   │
│  │ Total Revenue: KES 7,940.00                             │   │
│  │ Max Allowed (20%): KES 1,588.00                         │   │
│  │                                                         │   │
│  │ Commission Amount: [    1,065.00    ] KES               │   │
│  │                    ↑ Manual entry by Accountant         │   │
│  │                                                         │   │
│  │ ⚠️ Enter 0 or leave blank for no commission             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  NOTE: If salesperson has commission disabled, this section     │
│        is hidden entirely (field not shown, stored as NULL).    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        [ Cancel ]              [ Process Return ]        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.4 Workflow 3: View Dispatch List

**Trigger:** Accountant navigates to Sales > Dispatches  
**Permission:** ACCOUNTANT or higher  
**Owner:** Sales App

```
┌─────────────────────────────────────────────────────────────────┐
│              DISPATCHES                                    [+]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FILTERS                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Salesperson: [▼ All         ]  Status: [▼ All       ]   │   │
│  │ From: [2025-11-01]  To: [2025-11-30]  [ 🔍 Filter ]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  DISPATCH LIST                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ # │ Date       │ Salesperson   │ Units │ Status    │ ▶ │   │
│  │───┼────────────┼───────────────┼───────┼───────────┼───│   │
│  │ 1 │ 2025-11-30 │ John Mutua    │  225  │ 🟢 Returned│ ▶ │   │
│  │ 2 │ 2025-11-30 │ Mary Wanjiku  │  180  │ 🟡 Pending │ ▶ │   │
│  │ 3 │ 2025-11-30 │ Eastlands Dpt │  500  │ 🟡 Pending │ ▶ │   │
│  │ 4 │ 2025-11-29 │ John Mutua    │  200  │ 🟢 Returned│ ▶ │   │
│  │ 5 │ 2025-11-29 │ Mary Wanjiku  │  175  │ 🟢 Returned│ ▶ │   │
│  │───┴────────────┴───────────────┴───────┴───────────┴───│   │
│  │                        Showing 1-5 of 25  [ < 1 2 3 > ] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.5 Workflow 4: View Sales Report

**Trigger:** Accountant navigates to Sales > Reports  
**Permission:** ACCOUNTANT or higher  
**Owner:** Sales App

```
┌─────────────────────────────────────────────────────────────────┐
│              SALES REPORT                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SUMMARY (Last 30 Days)                                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │   │
│  │  │ TOTAL    │  │  REVENUE │  │  UNITS   │               │   │
│  │  │ RETURNS  │  │          │  │  SOLD    │               │   │
│  │  │    45    │  │KES 85,000│  │   3,250  │               │   │
│  │  └──────────┘  └──────────┘  └──────────┘               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  FILTERS                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Salesperson: [▼ All         ]                           │   │
│  │ From: [2025-11-01]  To: [2025-11-30]  [ 🔍 Filter ]     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  SALES BY DATE                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Date       │ Salesperson   │ Sold    │ Revenue   │  ▶  │   │
│  │────────────┼───────────────┼─────────┼───────────┼─────│   │
│  │ 2025-11-30 │ John Mutua    │   213   │ KES 7,940 │  ▶  │   │
│  │ 2025-11-30 │ Mary Wanjiku  │   185   │ KES 6,750 │  ▶  │   │
│  │ 2025-11-29 │ John Mutua    │   198   │ KES 7,200 │  ▶  │   │
│  │ 2025-11-29 │ Peter Kamau   │   245   │ KES 8,500 │  ▶  │   │
│  │────────────┴───────────────┴─────────┴───────────┴─────│   │
│  │                        Showing 1-5 of 45  [ < 1 2 3 > ] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.6 Workflow 5: View Commission Report

**Trigger:** Accountant navigates to Sales > Commissions  
**Permission:** ACCOUNTANT or higher  
**Owner:** Sales App

```
┌─────────────────────────────────────────────────────────────────┐
│              COMMISSION REPORT - November 2025                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  FILTERS                                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Month: [▼ November  ]  Year: [▼ 2025  ]  [ 🔍 View ]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  COMMISSION BY SALESPERSON                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Salesperson   │ Returns│ Units │ Revenue │ Commission   │   │
│  │───────────────┼────────┼───────┼─────────┼──────────────│   │
│  │ John Mutua    │   22   │ 4,400 │ 352,000 │  22,000      │   │
│  │ Mary Wanjiku  │   20   │ 3,600 │ 288,000 │  10,080      │   │
│  │ Peter Kamau   │   18   │ 3,200 │ 256,000 │       -      │   │
│  │ Eastlands Dpt │   25   │12,500 │1,000,000│  62,500      │   │
│  │───────────────┼────────┼───────┼─────────┼──────────────│   │
│  │ GRAND TOTAL   │   85   │23,700 │1,896,000│  94,580      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  NOTE: Commission is manually entered by Accountant during      │
│  return processing. "-" indicates salesperson has commission    │
│  disabled (commission_enabled=False).                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. SERVICE LAYER

### 5.1 Service Classes Overview

| Service Class | Purpose | Key Methods |
|---------------|---------|-------------|
| `DispatchService` | Dispatch creation & validation | `validate_dispatch_request()`, `create_dispatch()`, `get_available_products()` |
| `ReturnService` | Return processing & accountability | `validate_return_request()`, `process_return()` |
| `CommissionService` | Commission reporting (read-only) | `get_monthly_report()`, `get_salesperson_summary()` |
| `SalesReportService` | Sales reporting & analytics | `get_sales_report()`, `get_salesperson_summary()` |

### 5.2 DispatchService Methods

```python
class DispatchService:
    @staticmethod
    def get_available_products() -> List[Dict]:
        """Returns list of active products with current stock levels."""
    
    @staticmethod
    def validate_dispatch_request(salesperson_id, dispatch_date, items, crates=0) -> Dict:
        """
        Pre-transaction validation. Returns {'valid': bool, 'errors': [], 'warnings': []}.
        - Checks salesperson is active User with role=SALESMAN
        - Checks no existing dispatch for same salesperson+date
        - Checks stock availability for each product
        - Checks crate availability
        """
    
    @staticmethod
    @transaction.atomic
    def create_dispatch(salesperson_id, dispatch_date, items, crates, user) -> Tuple[SalesDispatch, Dict]:
        """
        Atomic dispatch creation. Returns (dispatch, result_dict).
        1. Lock salesperson (User) with select_for_update()
        2. Re-check no existing dispatch
        3. Create SalesDispatch record
        4. For each product: call deduct_dispatch_from_stock(), create SalesDispatchItem
        5. Call deduct_crates_atomic() if crates > 0
        """


class ReturnService:
    @staticmethod
    def validate_return_request(dispatch_id, items, crates_returned, crates_lost, crates_damaged, commission_amount=None) -> Dict:
        """
        Pre-transaction validation. Returns {'valid': bool, 'errors': []}.
        - Checks dispatch exists and not returned
        - Validates accountability: sold + returned == dispatched for each product
        - Validates crates: returned + lost + damaged == dispatch.crates_dispatched
        - Validates commission: 0 <= amount <= 20% of revenue (if salesperson.commission_enabled)
        """
    
    @staticmethod
    @transaction.atomic
    def process_return(dispatch_id, items, crates_returned, crates_lost, crates_damaged, notes, commission_amount, user) -> Tuple[SalesReturn, Dict]:
        """
        Atomic return processing. Returns (return, result_dict).
        1. Lock dispatch with select_for_update()
        2. Verify not already returned
        3. Create SalesReturn (total_revenue calculated, commission_amount stored as-is or NULL)
        4. For each product: create SalesReturnItem, call add_return_to_stock() if qty_returned > 0
        5. Call return_crates_atomic(crates_returned) - only good crates go back to inventory
        6. Mark dispatch returned
        Note: Lost/damaged crates are recorded but NOT returned to inventory.
              Crate replacement happens via Inventory purchase, not Sales App.
              Commission is NULL if salesperson.commission_enabled=False.
        """


class CommissionService:
    """Read-only commission reporting. Commission is manually entered by Accountant."""
    
    @staticmethod
    def get_max_commission(total_revenue) -> Decimal:
        """Returns maximum allowed commission (20% of revenue) for UI validation."""
        return total_revenue * Decimal('0.20')
    
    @staticmethod
    def get_monthly_report(year, month) -> Dict:
        """Monthly commission by salesperson. Queries SalesReturn.commission_amount."""
    
    @staticmethod
    def get_salesperson_summary(salesperson_id, year, month) -> Dict:
        """Monthly summary for one salesperson: total returns, revenue, commission."""


class SalesReportService:
    @staticmethod
    def get_sales_report(start_date=None, end_date=None, salesperson_id=None) -> Dict:
        """
        Returns {'sales': [], 'summary': {total_returns, total_revenue, total_units}}.
        - Queries SalesReturn with date range filters
        """
    
    @staticmethod
    def get_salesperson_summary(salesperson_id, year, month) -> Dict:
        """Monthly summary for a salesperson: returns, units, revenue, commission."""
```

---

## 6. CROSS-APP INTEGRATION

### 6.1 Integration Matrix

```
┌─────────────────────────────────────────────────────────────────┐
│                  SALES APP INTEGRATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  INBOUND DEPENDENCIES (Sales reads from)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Products App                                            │   │
│  │ • Product model: name, selling_price, is_active         │   │
│  │ • Read-only access                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Production App                                          │   │
│  │ • ProductStock model: current_stock                     │   │
│  │ • Read-only access                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  OUTBOUND CALLS (Sales calls utilities in)                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Production App                                          │   │
│  │ • deduct_dispatch_from_stock(product_id, qty, ref, user)│   │
│  │ • add_return_to_stock(product_id, qty, ref, user)       │   │
│  │ → Creates ProductStockMovement records                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Inventory App                                           │   │
│  │ • deduct_crates_atomic(qty, ref_type, ref_id, user)     │   │
│  │ • return_crates_atomic(qty, ref_type, ref_id, user)     │   │
│  │ • get_available_crates()                                │   │
│  │ → Creates Item22Transactions records (Crates)           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Production App Integration

#### Reading Product Stock

```python
# apps/sales/services.py

from apps.production.models import ProductStock

def get_product_stock(product_id: int) -> int:
    """
    Get current available stock for a product.
    
    Args:
        product_id: ID of product
    
    Returns:
        Current stock level (0 if no stock record)
    """
    try:
        stock = ProductStock.objects.get(product_id=product_id)
        return stock.current_stock
    except ProductStock.DoesNotExist:
        return 0


def get_all_product_stocks() -> dict:
    """
    Get stock levels for all products.
    
    Returns:
        Dict mapping product_id to current_stock
    """
    stocks = ProductStock.objects.all().values('product_id', 'current_stock')
    return {s['product_id']: s['current_stock'] for s in stocks}
```

#### Calling Stock Deduction (Dispatch)

```python
# When creating a dispatch, Sales calls Production utility:

from apps.production.services import deduct_dispatch_from_stock

# Inside create_dispatch():
for item in items:
    result = deduct_dispatch_from_stock(
        product_id=item['product_id'],
        quantity=item['quantity'],
        dispatch_id=dispatch.id,  # Reference for audit trail
        user=user
    )
    # Result contains:
    # {
    #     'success': True,
    #     'stock_before': 264,
    #     'stock_after': 164
    # }
```

#### Calling Stock Addition (Return)

```python
# When processing a return, Sales calls Production utility:

from apps.production.services import add_return_to_stock

# Inside process_return():
for item in return_items:
    if item['qty_returned'] > 0:
        result = add_return_to_stock(
            product_id=item['product_id'],
            quantity=item['qty_returned'],
            return_id=sales_return.id,  # Reference for audit trail
            user=user
        )
        # Result contains:
        # {
        #     'success': True,
        #     'stock_before': 164,
        #     'stock_after': 169
        # }
```

### 6.3 Inventory App Integration (Crates)

#### Crate Dispatch

```python
# apps/inventory/utils.py (interface that Sales calls)

@transaction.atomic
def deduct_crates_atomic(
    quantity: int,
    reference_type: str,
    reference_id: int,
    user
) -> dict:
    """
    Deduct crates from inventory (Item 22).
    
    Args:
        quantity: Number of crates to dispatch
        reference_type: 'SalesDispatch'
        reference_id: ID of the dispatch
        user: User performing action
    
    Returns:
        {'success': bool, 'error': str or None}
    """
    # Implementation in Inventory app
    # Creates Item22Transactions record
    pass
```

#### Crate Return

```python
# apps/inventory/utils.py (interface that Sales calls)

@transaction.atomic
def return_crates_atomic(
    quantity: int,
    reference_type: str,
    reference_id: int,
    user
) -> dict:
    """
    Return crates to inventory (Item 22).
    
    Args:
        quantity: Number of crates returned
        reference_type: 'SalesReturn'
        reference_id: ID of the return
        user: User performing action
    
    Returns:
        {'success': bool, 'error': str or None}
    """
    # Implementation in Inventory app
    # Creates Item22Transactions record
    pass
```

### 6.4 Integration Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                DISPATCH CREATION FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SALES APP                        PRODUCTION APP                │
│  ┌──────────────┐                ┌─────────────────────────┐   │
│  │ create_      │   ─────────▶   │ deduct_dispatch_from_   │   │
│  │ dispatch()   │   Calls        │ stock()                 │   │
│  │              │                │                         │   │
│  │ • Validate   │                │ • Lock ProductStock row │   │
│  │ • Create     │                │ • Deduct quantity       │   │
│  │   Dispatch   │                │ • Create Movement       │   │
│  │ • Create     │                │   record                │   │
│  │   Items      │                │ • Return result         │   │
│  └──────────────┘                └─────────────────────────┘   │
│         │                                                       │
│         │                        INVENTORY APP                  │
│         │                        ┌─────────────────────────┐   │
│         └───────────────────────▶│ deduct_crates_atomic()  │   │
│                      Calls       │                         │   │
│                                  │ • Lock Item22Details    │   │
│                                  │ • Deduct crates         │   │
│                                  │ • Create Transaction    │   │
│                                  │   record                │   │
│                                  └─────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                RETURN PROCESSING FLOW                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  SALES APP                        PRODUCTION APP                │
│  ┌──────────────┐                ┌─────────────────────────┐   │
│  │ process_     │   ─────────▶   │ add_return_to_stock()   │   │
│  │ return()     │   Calls        │                         │   │
│  │              │                │ • Lock ProductStock row │   │
│  │ • Validate   │                │ • Add quantity back     │   │
│  │   account-   │                │ • Create Movement       │   │
│  │   ability    │                │   record (RETURN type)  │   │
│  │ • Create     │                │ • Return result         │   │
│  │   Return     │                └─────────────────────────┘   │
│  │ • Create     │                                               │
│  │   Commission │                INVENTORY APP                  │
│  │              │                ┌─────────────────────────┐   │
│  └──────────────┘───────────────▶│ return_crates_atomic()  │   │
│                      Calls       │                         │   │
│                                  │ • Lock Item22Details    │   │
│                                  │ • Add crates back       │   │
│                                  │ • Create Transaction    │   │
│                                  │   record                │   │
│                                  └─────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.5 Integration Error Handling

```python
# apps/sales/services.py

@transaction.atomic
def create_dispatch(...) -> Tuple[Optional[SalesDispatch], Dict]:
    """
    Error handling strategy:
    1. All operations in single atomic transaction
    2. Any failure triggers full rollback
    3. Errors collected and returned to caller
    """
    result = {'success': False, 'errors': [], 'warnings': []}
    
    try:
        # ... dispatch creation logic ...
        
        # Call Production utility
        stock_result = deduct_dispatch_from_stock(
            product_id=product.id,
            quantity=quantity,
            dispatch_id=dispatch.id,
            user=user
        )
        
        # Check for errors
        if not stock_result.get('success'):
            result['errors'].append(
                f"Stock deduction failed: {stock_result.get('error')}"
            )
            raise ValueError("Stock deduction failed")  # Triggers rollback
        
        # ... continue with crates ...
        
    except ValueError as e:
        # Transaction automatically rolled back
        result['errors'].append(str(e))
        return None, result
    
    except Exception as e:
        # Unexpected error
        result['errors'].append(f"Unexpected error: {str(e)}")
        return None, result
    
    result['success'] = True
    return dispatch, result
```

---

## 7. VIEWS & URL ROUTING

### 7.1 URL Configuration

```python
# apps/sales/urls.py
app_name = 'sales'

urlpatterns = [
    # Dispatch (NO DELETE - bank ledger)
    path('', views.dispatch_list, name='dispatch_list'),
    path('dispatch/create/', views.dispatch_create, name='dispatch_create'),
    path('dispatch/<int:pk>/', views.dispatch_detail, name='dispatch_detail'),
    path('dispatch/<int:pk>/return/', views.dispatch_return, name='dispatch_return'),
    
    # Crate Status Update (only mutable action)
    path('return/<int:pk>/crates/', views.update_crate_status, name='update_crate_status'),
    
    # Reports
    path('reports/', views.sales_report, name='sales_report'),
    path('commissions/', views.commission_report, name='commission_report'),
    
    # API (for JavaScript)
    path('api/stock-levels/', views.api_stock_levels, name='api_stock_levels'),
    path('api/commission-preview/', views.api_commission_preview, name='api_commission_preview'),
]
```

### 7.2 View Summary

| View | Method | Purpose | Key Logic |
|------|--------|---------|-----------|
| `dispatch_list` | GET | List dispatches | Filter by salesperson/date/status, paginate |
| `dispatch_create` | GET/POST | Create dispatch | Validate stock, call `DispatchService.create_dispatch()` |
| `dispatch_detail` | GET | View dispatch | Show items + return status + commission |
| `dispatch_return` | GET/POST | Process return | Validate accountability, call `ReturnService.process_return()` |
| `update_crate_status` | POST | Mark crate resolution | Toggle `crates_marked_lost` / `crates_marked_damaged` booleans |
| `sales_report` | GET | Sales report | Call `SalesReportService.get_sales_report()` |
| `commission_report` | GET | Commission report | Call `CommissionService.get_monthly_report()` |
| `api_stock_levels` | GET | JSON stock | Return current ProductStock levels |
| `api_commission_preview` | GET | JSON preview | Calculate commission without saving |

> 🏦 **NOTE:** No edit or delete views exist. Bank ledger policy.

### 7.3 View Logic Notes

**dispatch_create:**
- Preview screen with confirmation before final submit
- Validate via `DispatchService.validate_dispatch_request()`
- Create via `DispatchService.create_dispatch()` (atomic)
- Once created = PERMANENT

**dispatch_return:**
- Preview screen with confirmation before final submit
- Reject if `is_returned=True`
- Validate accountability: `sold + returned == dispatched` (strict equality)
- Validate crates: `crates_returned + crates_lost + crates_damaged == crates_dispatched` (strict equality)
- Only `crates_returned` are added back to inventory; lost/damaged are recorded but not returned
- Once created = PERMANENT

**update_crate_status:**
- Only mutable action: mark crate resolution status
- `crates_marked_lost=True` means salesperson has replaced/resolved lost crates
- `crates_marked_damaged=True` means salesperson has replaced/resolved damaged crates
- Actual crate replacement is tracked via Inventory purchase, not Sales

---

## 8. FORMS & VALIDATION

### 8.1 Salesperson Selection Note

> **Salesperson management is handled by Accounts App**, not Sales.
>
> In Sales forms/views, salesperson is selected via a dropdown that:
> - Filters `accounts.User` to only show `role=SALESMAN`
> - Uses `limit_choices_to={'role': 'SALESMAN'}` on the FK
> - Commission config (rate, type) is set on the User in Accounts

```python
# In SalesDispatch form, salesperson field filtering:
salesperson = forms.ModelChoiceField(
    queryset=User.objects.filter(role='SALESMAN', is_active=True),
    widget=forms.Select(attrs={'class': 'form-control'}),
    help_text="Select salesperson to receive dispatch"
)
```

### 8.2 Form: Dispatch

```python
class DispatchForm(forms.Form):
    """Form for creating dispatches."""
    
    salesperson = forms.ModelChoiceField(
        queryset=User.objects.filter(role='SALESMAN', is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select salesperson (User with role=SALESMAN)"
    )
    dispatch_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    crates = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0'
        })
    )
    
    def __init__(self, *args, products=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dynamically add product quantity fields
        if products:
            for product in products:
                field_name = f"qty_{product['id']}"
                self.fields[field_name] = forms.IntegerField(
                    min_value=0,
                    initial=0,
                    required=False,
                    label=product['name'],
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'min': '0',
                        'max': str(product['current_stock']),
                        'data-stock': str(product['current_stock']),
                        'data-price': str(product['price'])
                    })
                )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure at least one product has quantity
        has_products = False
        for key, value in cleaned_data.items():
            if key.startswith('qty_') and value and value > 0:
                has_products = True
                break
        
        if not has_products:
            raise ValidationError("At least one product must be dispatched.")
        
        return cleaned_data
```

### 8.3 Form: Return

```python
class ReturnForm(forms.Form):
    """Form for processing returns. Accountant enters sold/returned quantities."""
    
    crates_returned = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0'
        })
    )
    crates_lost = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0'
        })
    )
    crates_damaged = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0'
        })
    )
    commission_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
        initial=Decimal('0'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '0.01',
            'placeholder': 'Enter commission amount'
        }),
        help_text="Manual entry. Max allowed = 20% of total revenue."
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '2',
            'placeholder': 'Additional notes (optional)'
        })
    )
    
    def __init__(self, *args, dispatch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatch = dispatch
        
        # Hide commission field if salesperson has commission disabled
        if dispatch and not dispatch.salesperson.commission_enabled:
            del self.fields['commission_amount']
        
        # Dynamically add sold/returned fields for each product
        if dispatch:
            for item in dispatch.items.all():
                # Sold field
                self.fields[f"sold_{item.product_id}"] = forms.IntegerField(
                    min_value=0,
                    initial=0,
                    label=f"{item.product.name} Sold",
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'min': '0',
                        'max': str(item.quantity),
                        'data-dispatched': str(item.quantity),
                        'data-price': str(item.unit_price)
                    })
                )
                
                # Returned field
                self.fields[f"returned_{item.product_id}"] = forms.IntegerField(
                    min_value=0,
                    initial=0,
                    label=f"{item.product.name} Returned",
                    widget=forms.NumberInput(attrs={
                        'class': 'form-control',
                        'min': '0',
                        'max': str(item.quantity)
                    })
                )
    
    def clean(self):
        cleaned_data = super().clean()
        
        if not self.dispatch:
            raise ValidationError("No dispatch context provided.")
        
        # Validate accountability for each product: sold + returned MUST equal dispatched
        errors = []
        for item in self.dispatch.items.all():
            sold = cleaned_data.get(f"sold_{item.product_id}", 0) or 0
            returned = cleaned_data.get(f"returned_{item.product_id}", 0) or 0
            
            total = sold + returned
            if total != item.quantity:
                errors.append(
                    f"{item.product.name}: sold ({sold}) + returned ({returned}) = {total} "
                    f"≠ dispatched ({item.quantity})"
                )
        
        if errors:
            raise ValidationError(errors)
        
        # Validate crates: returned + lost + damaged must equal dispatched
        crates_returned = cleaned_data.get('crates_returned', 0) or 0
        crates_lost = cleaned_data.get('crates_lost', 0) or 0
        crates_damaged = cleaned_data.get('crates_damaged', 0) or 0
        crates_total = crates_returned + crates_lost + crates_damaged
        
        if crates_total != self.dispatch.crates_dispatched:
            raise ValidationError(
                f"Crates: returned ({crates_returned}) + lost ({crates_lost}) + damaged ({crates_damaged}) = {crates_total} "
                f"≠ dispatched ({self.dispatch.crates_dispatched})"
            )
        
        # Validate commission (if salesperson has commission enabled)
        if self.dispatch.salesperson.commission_enabled:
            commission_amount = cleaned_data.get('commission_amount') or Decimal('0')
            
            # Calculate total revenue from sold quantities
            total_revenue = Decimal('0')
            for item in self.dispatch.items.all():
                sold = cleaned_data.get(f"sold_{item.product_id}", 0) or 0
                total_revenue += Decimal(sold) * item.unit_price
            
            # Validate: 0 <= commission <= 20% of revenue
            max_commission = total_revenue * Decimal('0.20')
            if commission_amount > max_commission:
                raise ValidationError(
                    f"Commission ({commission_amount}) exceeds maximum allowed "
                    f"(20% of revenue = {max_commission})"
                )
        
        return cleaned_data
```

### 8.4 Form Validation Summary

| Form | Field | Validation Rules |
|------|-------|------------------|
| DispatchForm | salesperson | Required, must be active User with role=SALESMAN |
| DispatchForm | dispatch_date | Required, valid date |
| DispatchForm | crates | >= 0 |
| DispatchForm | qty_* | >= 0, <= available stock |
| DispatchForm | (overall) | At least one product with qty > 0 |
| ReturnForm | crates_returned | >= 0 |
| ReturnForm | crates_lost | >= 0 |
| ReturnForm | crates_damaged | >= 0 |
| ReturnForm | (crates overall) | returned + lost + damaged must equal crates_dispatched |
| ReturnForm | sold_* + returned_* | Must equal dispatched quantity (strict) |
| ReturnForm | commission_amount | >= 0, <= 20% of total revenue (manual entry) |
| ReturnForm | notes | Optional |

---

## 9. ADMIN CONFIGURATION

### 9.1 Salesperson Admin Note

> **Salesperson management is in Accounts Admin**, not Sales.
>
> In the Accounts app admin, filter Users by `role=SALESMAN` to manage:
> - Commission enabled/disabled toggle (`commission_enabled`)
> - Contact info, status
> - Sales targets
>
> Commission amounts are entered manually during return processing.
> Sales admin only manages Dispatch and Return records.

```python
# apps/sales/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    SalesDispatch, 
    SalesDispatchItem,
    SalesReturn, 
    SalesReturnItem
)
# Note: No Salesperson model - it's accounts.User
```

### 9.2 Dispatch Admin

```python
class SalesDispatchItemInline(admin.TabularInline):
    """Inline for dispatch items."""
    model = SalesDispatchItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'unit_price', 'line_total']
    can_delete = False
    
    def line_total(self, obj):
        return f"KES {obj.line_total:,.2f}"
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SalesDispatch)
class SalesDispatchAdmin(admin.ModelAdmin):
    """Admin configuration for SalesDispatch model."""
    
    list_display = [
        'dispatch_number',
        'salesperson',
        'dispatch_date',
        'total_units',
        'expected_revenue_display',
        'status_badge',
        'created_at'
    ]
    list_filter = ['status', 'is_returned', 'dispatch_date', 'salesperson']
    search_fields = ['dispatch_number', 'salesperson__name']
    date_hierarchy = 'dispatch_date'
    readonly_fields = [
        'dispatch_number', 
        'total_units',
        'expected_revenue_display',
        'created_at', 
        'created_by',
        'returned_at'
    ]
    inlines = [SalesDispatchItemInline]
    ordering = ['-dispatch_date', '-created_at']
    
    fieldsets = (
        ('Dispatch Information', {
            'fields': (
                'dispatch_number', 
                'salesperson', 
                'dispatch_date',
                'status'
            )
        }),
        ('Summary', {
            'fields': ('total_units', 'expected_revenue_display', 'crates_dispatched')
        }),
        ('Return Status', {
            'fields': ('is_returned', 'returned_at')
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'DISPATCHED': '#F59E0B',  # Amber
            'RETURNED': '#10B981',    # Green
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def expected_revenue_display(self, obj):
        return f"KES {obj.expected_revenue:,.2f}"
    expected_revenue_display.short_description = 'Expected Revenue'
    
    # NO save_model override needed - records are immutable
    # NO delete action - bank ledger policy
    
    def has_change_permission(self, request, obj=None):
        return False  # No editing allowed
    
    def has_delete_permission(self, request, obj=None):
        return False  # No deletion allowed
```

### 9.3 Return Admin

```python
class SalesReturnItemInline(admin.TabularInline):
    """Inline for return items."""
    model = SalesReturnItem
    extra = 0
    readonly_fields = [
        'product', 
        'qty_dispatched', 
        'qty_sold', 
        'qty_returned',
        'unit_price',
        'revenue'
    ]
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    """Admin configuration for SalesReturn model."""
    
    list_display = [
        'dispatch_link',
        'return_date',
        'total_units_sold',
        'total_revenue_display',
        'commission_display',
        'crate_status_badge',
        'created_at'
    ]
    list_filter = ['return_date', 'crates_marked_lost', 'crates_marked_damaged']
    search_fields = ['dispatch__dispatch_number', 'dispatch__salesperson__name']
    date_hierarchy = 'return_date'
    readonly_fields = [
        'dispatch',
        'return_date',
        'total_units_sold',
        'total_revenue',
        'crates_returned',
        'crates_lost',
        'crates_damaged',
        'commission_amount',
        'created_at',
        'created_by'
    ]
    inlines = [SalesReturnItemInline]
    ordering = ['-return_date', '-created_at']
    
    fieldsets = (
        ('Return Information', {
            'fields': ('dispatch', 'return_date')
        }),
        ('Sales Totals', {
            'fields': ('total_units_sold', 'total_revenue')
        }),
        ('Crates', {
            'fields': (
                'crates_returned',
                'crates_lost',
                'crates_damaged',
                'crates_marked_lost',      # Only mutable field
                'crates_marked_damaged'    # Only mutable field
            ),
            'description': 'Returned + Lost + Damaged must equal crates dispatched. Boolean fields mark resolution status.'
        }),
        ('Commission (Informational)', {
            'fields': ('commission_amount',),
            'classes': ('collapse',),
            'description': 'Manually entered at return time. NULL if salesperson has commission disabled.'
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit Trail', {
            'fields': ('created_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def has_change_permission(self, request, obj=None):
        # Only allow changing crate status fields
        return True  # But all other fields are readonly
    
    def has_delete_permission(self, request, obj=None):
        return False  # No deletion allowed - bank ledger
    
    def dispatch_link(self, obj):
        return format_html(
            '<a href="/admin/sales/salesdispatch/{}/change/">{}</a>',
            obj.dispatch.id, obj.dispatch.dispatch_number
        )
    dispatch_link.short_description = 'Dispatch'
    
    def total_revenue_display(self, obj):
        return f"KES {obj.total_revenue:,.2f}"
    total_revenue_display.short_description = 'Revenue'
    
    def commission_display(self, obj):
        if obj.commission_amount is None:
            return format_html('<span style="color: #6B7280;">—</span>')
        return format_html(
            '<span style="color: #10B981;">KES {:,.2f}</span>',
            obj.commission_amount
        )
    commission_display.short_description = 'Commission'
    
    def crate_status_badge(self, obj):
        """Badge showing crate accountability status."""
        has_lost = obj.crates_lost > 0
        has_damaged = obj.crates_damaged > 0
        
        if has_lost or has_damaged:
            # Check if issues are resolved (marked for later resolution)
            lost_resolved = not has_lost or obj.crates_marked_lost
            damaged_resolved = not has_damaged or obj.crates_marked_damaged
            
            if lost_resolved and damaged_resolved:
                return format_html(
                    '<span style="color: #F59E0B;">⚠️ Resolved</span>'
                )
            return format_html(
                '<span style="color: #EF4444;">⚠️ {} lost, {} damaged</span>',
                obj.crates_lost, obj.crates_damaged
            )
        return format_html(
            '<span style="color: #10B981;">✓ All returned</span>'
        )
    crate_status_badge.short_description = 'Crates'
```

### 9.4 Bank Ledger Policy in Admin

> **CRITICAL:** Django Admin enforces bank ledger policy:
> - `has_change_permission()` returns False for SalesDispatch (no manual edits)
> - `has_delete_permission()` returns False for all models (no deletes)
> - SalesReturn allows editing ONLY `crates_marked_lost` and `crates_marked_damaged`
> - All other fields are readonly
> - Note: `SalesDispatch.is_returned` is set programmatically by service layer, not Admin

---

## 10. TEMPLATES REFERENCE

### 10.1 Template List

| Template | Purpose |
|----------|---------|
| `dispatch_list.html` | List dispatches with filters |
| `dispatch_form.html` | Create dispatch with product selection |
| `dispatch_detail.html` | View dispatch + return status |
| `sales_return_form.html` | Process return with accountability validation |
| `sales_report.html` | Sales report by date range |
| `commission_report.html` | Monthly commission summary |

### 10.2 Directory Structure

```
apps/sales/templates/sales/
├── dispatch_list.html
├── dispatch_form.html
├── dispatch_detail.html
├── sales_return_form.html
├── sales_report.html
├── commission_report.html
└── partials/
    ├── _dispatch_table.html
    └── _return_items.html
```

### 10.3 Key JavaScript Features

**Return Form Calculator:**
- Real-time accountability validation (`sold + returned = dispatched`)
- Real-time crate accountability (`returned + lost + damaged = dispatched`)
- Revenue auto-calculation from `qty_sold × unit_price`
- Commission preview (if salesperson has commission enabled)
- Submit button disabled until all products balanced and crates equal

**Dispatch Form:**
- Dynamic line totals as quantities entered
- Max quantity validation against available stock
- Grand total calculation

> **Note:** Templates are preserved from existing app with minimal modifications
> to work with the new model structure (FK to User instead of Salesperson model).

---

## 11. SEEDING & INITIAL DATA

### 11.1 Salesperson Seeding Note

> **Salespeople are seeded via Accounts App**, not Sales.
>
> Salespeople are `accounts.User` records with `role='SALESMAN'`.
> The Accounts App is responsible for creating and managing all users,
> including salespeople.
>
> When seeding, use the Accounts seeder to create Users with:
> - `role = 'SALESMAN'`
> - `commission_enabled = True/False`
>
> Commission amounts are manually entered during return processing.

```python
# Example: Seeding salespeople via Accounts App
# apps/accounts/management/commands/seed_users.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed users including salespeople'

    def handle(self, *args, **options):
        
        salespeople_data = [
            {
                'username': 'john_mutua',
                'first_name': 'John',
                'last_name': 'Mutua',
                'role': 'SALESMAN',
                'phone': '0712345678',
                'commission_enabled': True,
            },
            {
                'username': 'mary_wanjiku',
                'first_name': 'Mary',
                'last_name': 'Wanjiku',
                'role': 'SALESMAN',
                'phone': '0723456789',
                'commission_enabled': True,
            },
            {
                'username': 'peter_kamau',
                'first_name': 'Peter',
                'last_name': 'Kamau',
                'role': 'SALESMAN',
                'phone': '0734567890',
                'commission_enabled': False,  # No commission
            },
        ]
        
        for data in salespeople_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults=data
            )
            if created:
                user.set_password('changeme123')
                user.save()
                self.stdout.write(self.style.SUCCESS(f"✓ Created: {user.get_full_name()}"))
```

### 11.2 Running the Seed Command

```bash
# Seed users (including salespeople) via Accounts
python manage.py seed_users

# Output:
# ✓ Created: John Mutua
# ✓ Created: Mary Wanjiku
# ✓ Created: Peter Kamau
# ✓ Created: Chesanto Primary School
# ✓ Created: Kilimani Academy
# ✓ Created: Staff Canteen
#
# Seeding complete: 11 created, 0 skipped
```

### 11.3 Sample Dispatch Seed (For Testing)

```python
# apps/sales/management/commands/seed_sample_dispatches.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from apps.sales.models import SalesDispatch, SalesDispatchItem
from apps.products.models import Product
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed sample dispatches for testing'

    def handle(self, *args, **options):
        system_user = User.objects.filter(is_superuser=True).first()
        today = timezone.now().date()
        
        # Get products
        try:
            bread = Product.objects.get(name__iexact='Bread')
            kdf = Product.objects.get(name__iexact='KDF')
            scones = Product.objects.get(name__iexact='Scones')
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "Products not found. Run product seeding first."
            ))
            return
        
        # Get salespeople (Users with role=SALESMAN)
        salespeople = User.objects.filter(role='SALESMAN', is_active=True)[:3]
        
        if len(salespeople) < 1:
            self.stdout.write(self.style.ERROR(
                "No salespeople found. Run user seeding first."
            ))
            return
        
        # Create sample dispatches
        for i, sp in enumerate(salespeople):
            dispatch, created = SalesDispatch.objects.get_or_create(
                salesperson=sp,
                dispatch_date=today,
                defaults={
                    'crates_dispatched': 5 + i,
                    'status': SalesDispatch.Status.DISPATCHED,
                    'created_by': system_user
                }
            )
            
            if created:
                # Add items
                SalesDispatchItem.objects.create(
                    dispatch=dispatch,
                    product=bread,
                    quantity=100 + (i * 20),
                    unit_price=bread.selling_price
                )
                SalesDispatchItem.objects.create(
                    dispatch=dispatch,
                    product=kdf,
                    quantity=50 + (i * 10),
                    unit_price=kdf.selling_price
                )
                SalesDispatchItem.objects.create(
                    dispatch=dispatch,
                    product=scones,
                    quantity=75 + (i * 15),
                    unit_price=scones.selling_price
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Created dispatch: {dispatch.dispatch_number}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"- Skipped: Dispatch exists for {sp.get_full_name()} on {today}"
                ))
```

---

## 12. TESTING STRATEGY

### 12.1 Test Structure

```
apps/sales/tests/
├── test_models.py          # Model unit tests
├── test_services.py        # Service layer tests
├── test_views.py           # View integration tests
└── test_integration.py     # Cross-app integration tests
```

### 12.2 Model Tests

| Test Class | Test Cases |
|------------|------------|
| `SalesDispatchModelTest` | dispatch_number generation, unique per salesperson/day, immutable after return |
| `SalesReturnCommissionTest` | commission stored when enabled, NULL when disabled, max 20% validation |

### 12.3 Service Tests

| Test Class | Test Cases |
|------------|------------|
| `DispatchServiceTest` | valid request, insufficient stock rejection, duplicate dispatch rejection |
| `ReturnServiceTest` | valid return, accountability validation (sold+returned==dispatched), crates validation, commission validation (max 20% cap) |
| `CommissionServiceTest` | get_max_commission calculation, get_monthly_report aggregation |

### 12.4 Integration Tests

| Test Class | Test Cases |
|------------|------------|
| `DispatchIntegrationTest` | dispatch creates stock movement, dispatch deducts ProductStock |
| `ReturnIntegrationTest` | return restores stock, return creates ProductStockMovement, settlement flow |

### 12.5 Running Tests

```bash
# Run all Sales app tests
python manage.py test apps.sales

# Run with coverage
coverage run --source='apps.sales' manage.py test apps.sales
coverage report
```

---

## APPENDIX: SUMMARY TABLES

### A.1 Model Summary

| Model | Purpose | Mutable? |
|-------|---------|----------|
| SalesDispatch | Daily dispatch (FK to User) | IMMUTABLE (except is_returned flag set once) |
| SalesDispatchItem | Dispatch line items | IMMUTABLE |
| SalesReturn | Settlement + commission + crate accountability | IMMUTABLE (except crates_marked_lost/damaged booleans) |
| SalesReturnItem | Sold/returned breakdown | IMMUTABLE |

### A.2 Core Accountability Rules

| Rule | Formula | Notes |
|------|---------|-------|
| Product Accountability | `qty_sold + qty_returned = qty_dispatched` | Per product, strict equality |
| Crate Accountability | `crates_returned + crates_lost + crates_damaged = crates_dispatched` | Strict equality |
| Revenue | Auto-calculated from `qty_sold × unit_price` | Never manually entered |
| Crate Resolution | Boolean flags mark when lost/damaged resolved | Actual replacement via Inventory purchase |

### A.3 Cross-App Integration

| Direction | Target App | Utility | Notes |
|-----------|------------|---------|-------|
| Outbound | Production | `deduct_dispatch_from_stock()` | Dispatch creation |
| Outbound | Production | `add_return_to_stock()` | Only for `qty_returned > 0` |
| Outbound | Inventory | `deduct_crates_atomic()` | Dispatch creation |
| Outbound | Inventory | `return_crates_atomic()` | Only for `crates_returned` (not lost/damaged) |
| Inbound | Products | Read `Product` | Selling price snapshot |
| Inbound | Accounts | FK to `User` (role=SALESMAN) | Commission config on User |

---

**Document Complete**

*SALES_APP_WORKFLOWS.md - Version 2.2 (Date Standardization)*

---

## 🆕 DECEMBER 2025 UPDATES

### Date/Time Standardization (Dec 2, 2025)
Sales templates now use consistent date/time formatting:

| Field Type | Django Filter | Example Output |
|------------|---------------|----------------|
| DateField | `\|date:"M d, Y"` | Dec 02, 2025 |
| DateTimeField | `\|date:"M d, Y, g:i A"` | Dec 02, 2025, 3:22 PM |

**Templates Updated:**
- `dispatch_detail.html` - dispatch_date, returned_at, created_at (5 instances)
