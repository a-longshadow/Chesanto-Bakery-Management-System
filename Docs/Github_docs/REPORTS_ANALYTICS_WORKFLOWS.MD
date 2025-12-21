# 📊 REPORTS & ANALYTICS APPS - COMPREHENSIVE PLANNING DOCUMENT

> **Purpose:** Complete context handoff for new chat session to implement Reports & Analytics apps  
> **Created:** December 4, 2025  
> **Last Updated:** December 6, 2025  
> **Status:** Planning Phase - Ready for Implementation  
> **Document Version:** 2.1 (Updated with Planning Decisions)

---

## CRITICAL CLARIFICATIONS

### Task Functions vs Frontend Reports

| Component | Purpose | User Interaction | Location |
|-----------|---------|------------------|----------|
| **Task Functions** (`tasks.py`) | Background jobs that run on a schedule, auto-email reports | SUPERADMIN manages schedules via Django Admin only | Backend |
| **Report Views** (`views.py`) | Frontend pages users can view, filter, export, email | All authorized users via `/reports/` URLs | Frontend |

**Key Point:** Task Functions reuse the same service logic as frontend views. The frontend has 35+ report views. Task Functions just automate emailing those same reports on a schedule.

```
Frontend View:        /reports/sales/daily/  →  User views, exports, emails manually
Task Function:        daily_sales_summary()  →  Runs at 6 AM, auto-emails to SUPERADMIN

Both use:             services/sales.py → get_daily_summary()
```

### Access Control: ACCOUNTANT+ Required

**All report routes (`/reports/*`) require ACCOUNTANT role or higher.**

Roles with access (hierarchy):
1. SUPERADMIN ✅
2. ADMIN ✅
3. ACCOUNTANT ✅
4. All others ❌ (redirected to dashboard)

```python
# Default decorator for all report views
@login_required
@report_access_required(['SUPERADMIN', 'ADMIN', 'ACCOUNTANT'])
def any_report_view(request):
    ...
```

---

## TABLE OF CONTENTS

0. [Critical Clarifications](#critical-clarifications)
1. [Project Context & Technical Foundation](#1-project-context--technical-foundation)
2. [Complete Model Reference](#2-complete-model-reference)
3. [Cross-App Data Relationships](#3-cross-app-data-relationships)
4. [Reports App Specification](#4-reports-app-specification)
5. [Analytics App Specification](#5-analytics-app-specification)
6. [UI/Styling Patterns](#6-uistyling-patterns)
7. [Chart.js Integration](#7-chartjs-integration)
8. [Implementation Workflows](#8-implementation-workflows)
9. [Query Patterns & Examples](#9-query-patterns--examples)
10. [Task Functions Reference](#10-task-functions-reference)
11. [Starting Prompt for New Chat](#11-starting-prompt-for-new-chat)

---

# 1. PROJECT CONTEXT & TECHNICAL FOUNDATION

## 1.1 System Overview

**Chesanto Bakery Management System** - A Django 5.2.7 multi-app monolith managing a Kenyan bakery's complete operations from raw materials to sales.

## 1.2 Technical Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| **Framework** | Django 5.2.7 | Latest stable release |
| **Database** | PostgreSQL (prod) / SQLite (dev) | ACID-compliant |
| **Frontend** | Django Templates + Vanilla CSS/JS | NO React/Vue/etc |
| **Charting** | Chart.js | Lightweight, Django-friendly |
| **Timezone** | `Africa/Nairobi` | `USE_TZ = True` |
| **Pagination** | Django Paginator | `DEFAULT_PAGE_SIZE = 50` |
| **Currency** | KES (Kenyan Shillings) | All monetary values |

## 1.3 Core Architectural Principles

### Bank Ledger Model (CRITICAL)
All financial/operational records follow banking principles:

```
┌─────────────────────────────────────────────────────────────────┐
│                    BANK LEDGER PHILOSOPHY                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ❌ NO DELETE   - Records are permanent                        │
│  ❌ NO UPDATE   - Once created, values cannot change           │
│  ❌ NO REVERSAL - No "undo" or "cancel" transactions           │
│  ✅ CREATE ONLY - All changes via NEW records                  │
│  ✅ POSITIVE ONLY - All quantities/amounts are positive        │
│  ✅ ACID COMPLIANT - All operations use @transaction.atomic    │
│                                                                 │
│  WHY: "You can't walk into a bank and say 'that $10           │
│        withdrawal yesterday, can you change it to $8?'"        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### App Hierarchy & Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    APP DEPENDENCY CHAIN                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────┐   ┌───────────┐   ┌────────────┐   ┌─────────┐  │
│   │ PRODUCTS │ → │ INVENTORY │ → │ PRODUCTION │ → │  SALES  │  │
│   │ (Catalog)│   │  (Stock)  │   │ (Batches)  │   │(Dispatch)│  │
│   └──────────┘   └───────────┘   └────────────┘   └─────────┘  │
│                                                       ↓         │
│                                                 ┌───────────┐   │
│                                                 │ REPORTS & │   │
│                                                 │ ANALYTICS │   │
│                                                 └───────────┘   │
│                                                                 │
│   Direction: LEFT → RIGHT (each app depends on apps to left)   │
│   Reports/Analytics: READ-ONLY access to ALL apps              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 1.4 Foundation Apps Status (All Complete ✅)

| App | Status | Models | Key Features |
|-----|--------|--------|--------------|
| **Accounts** | ✅ Complete | User, UserInvitation, EmailOTP | 8 roles, payroll fields, commission tracking |
| **Products** | ✅ Complete | Product, Mix, MixIngredient | Recipe management, quality tiers |
| **Inventory** | ✅ Complete | 23 per-item tables | ACID utilities, stock alerts |
| **Production** | ✅ Complete | ProductionBatch, ProductStock | Mix snapshots, ingredient deductions |
| **Sales** | ✅ Complete | SalesDispatch, SalesReturn | Crate tracking, commission entry |

---

# 2. COMPLETE MODEL REFERENCE

## 2.1 Accounts App Models

### User Model (Extended AbstractUser)
**File:** `apps/accounts/models.py` (455 lines)

```python
class User(AbstractUser):
    """
    Extended User model with role-based access and payroll integration.
    """
    
    # ROLE CHOICES
    class Role(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'Super Admin'
        ADMIN = 'ADMIN', 'Admin'
        PRODUCT_MANAGER = 'PRODUCT_MANAGER', 'Product Manager'
        DEPT_HEAD = 'DEPT_HEAD', 'Department Head'
        DISPATCH = 'DISPATCH', 'Dispatch'
        SALESMAN = 'SALESMAN', 'Salesman'
        SECURITY = 'SECURITY', 'Security'
        BASIC_USER = 'BASIC_USER', 'Basic User'
    
    # EMPLOYMENT STATUS
    class EmploymentStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
        TERMINATED = 'TERMINATED', 'Terminated'
    
    # Core Fields
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BASIC_USER)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Payroll Fields
    employee_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    national_id = models.CharField(max_length=20, null=True, blank=True)
    position = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pay_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Commission Fields (for SALESMAN role)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=7.00)  # 7%
    sales_target = models.DecimalField(max_digits=10, decimal_places=2, default=35000)   # KES 35,000
    
    # Loan Tracking (live balances, deducted via Payroll)
    current_loan_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    current_advance_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Employment Dates
    date_hired = models.DateField(null=True, blank=True)
    date_terminated = models.DateField(null=True, blank=True)
    employment_status = models.CharField(max_length=20, choices=EmploymentStatus.choices, 
                                          default=EmploymentStatus.ACTIVE)
    
    # Profile Photo with cropping
    profile_photo = models.ImageField(upload_to='profiles/', null=True, blank=True)
    photo_center_x = models.FloatField(default=0.5)  # 0-1 horizontal position
    photo_center_y = models.FloatField(default=0.5)  # 0-1 vertical position
```

**Key Properties:**
```python
@property
def is_salesman(self) -> bool:
    return self.role == self.Role.SALESMAN

@property  
def commission_enabled(self) -> bool:
    return self.role == self.Role.SALESMAN and self.commission_rate > 0

@property
def initials(self) -> str:
    """For avatar display when no photo"""
    first = self.first_name[0].upper() if self.first_name else ''
    last = self.last_name[0].upper() if self.last_name else ''
    return f"{first}{last}" or self.username[0:2].upper()
```

### Supporting Models
```python
class UserInvitation(models.Model):
    """Temporary password invitations with 7-day expiry"""
    user = models.ForeignKey(User)
    temporary_password = models.CharField(max_length=128)
    expires_at = models.DateTimeField()  # 7 days from creation
    is_used = models.BooleanField(default=False)

class EmailOTP(models.Model):
    """One-time codes for login/password reset"""
    user = models.ForeignKey(User)
    otp_code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()  # 10 minutes
    is_used = models.BooleanField(default=False)

class UserProfileChange(models.Model):
    """Audit trail of profile modifications"""
    user = models.ForeignKey(User)
    changed_by = models.ForeignKey(User)
    field_changed = models.CharField(max_length=100)
    old_value = models.TextField(null=True)
    new_value = models.TextField(null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
```

## 2.2 Products App Models

### Product Model
**File:** `apps/products/models.py` (271 lines)

```python
class Product(TimeStampedModel):
    """
    Product catalog - finished goods that can be sold.
    Supports parent-child relationships for quality tiers.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Quality tier support (e.g., "Bread Premium" → parent "Bread")
    parent_product = models.ForeignKey('self', null=True, blank=True, 
                                        on_delete=models.SET_NULL,
                                        related_name='variants')
    
    # Soft delete (never hard delete)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
```

### Mix (Recipe) Model
```python
class Mix(TimeStampedModel):
    """
    Recipe for producing a product. Only ONE active mix per product.
    """
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='mixes')
    name = models.CharField(max_length=200)  # e.g., "Standard Bread Mix"
    
    # Yield tracking
    expected_yield = models.PositiveIntegerField(help_text="Expected units per batch")
    is_fixed_yield = models.BooleanField(default=False)  # True = exact, False = range
    yield_variance_min = models.DecimalField(max_digits=5, decimal_places=2, default=0.95)  # 95%
    yield_variance_max = models.DecimalField(max_digits=5, decimal_places=2, default=1.05)  # 105%
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['product'],
                condition=Q(is_active=True),
                name='unique_active_mix_per_product'
            )
        ]
    
    def get_snapshot_data(self) -> dict:
        """
        Returns complete recipe data for freezing in ProductionBatch.
        Called at batch creation to preserve recipe even if mix changes later.
        """
        return {
            'mix_id': self.id,
            'mix_name': self.name,
            'expected_yield': self.expected_yield,
            'ingredients': [
                {
                    'inventory_item_id': ing.inventory_item_id,
                    'item_name': get_item_name(ing.inventory_item_id),
                    'quantity': str(ing.quantity_required),
                    'unit': ing.unit_of_measure,
                    'unit_price': str(get_last_purchase_price(ing.inventory_item_id)),
                }
                for ing in self.ingredients.all()
            ],
            'total_ingredient_cost': str(self.calculate_total_cost()),
        }
```

### MixIngredient Model
```python
class MixIngredient(models.Model):
    """
    Links a Mix to inventory items (ingredients).
    Uses inventory_item_id (1-23) to reference inventory tables.
    """
    mix = models.ForeignKey(Mix, on_delete=models.CASCADE, related_name='ingredients')
    
    # Reference to inventory (1-15 are ingredients, 16-23 are indirect costs)
    inventory_item_id = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(23)]
    )
    
    quantity_required = models.DecimalField(max_digits=10, decimal_places=4)
    unit_of_measure = models.CharField(max_length=20)  # kg, liters, pieces, etc.
    
    class Meta:
        unique_together = ['mix', 'inventory_item_id']
```

## 2.3 Inventory App Structure

### Master Item List (23 Pre-defined Items)
**File:** `apps/inventory/routing.py` (250 lines)

```python
INVENTORY_ITEMS = {
    # INGREDIENTS (Items 1-15) - Used in production
    1: {'name': 'Flour Type 1', 'unit': 'kg'},
    2: {'name': 'Flour Type 2', 'unit': 'kg'},
    3: {'name': 'Sugar', 'unit': 'kg'},
    4: {'name': 'Bread Improver', 'unit': 'kg'},
    5: {'name': 'Salt', 'unit': 'kg'},
    6: {'name': 'Calcium', 'unit': 'kg'},
    7: {'name': 'Yeast', 'unit': 'kg'},
    8: {'name': 'Yeast 2-in-1', 'unit': 'kg'},
    9: {'name': 'Baking Powder', 'unit': 'kg'},
    10: {'name': 'Margarine', 'unit': 'kg'},
    11: {'name': 'Milk', 'unit': 'liters'},
    12: {'name': 'Eggs', 'unit': 'pieces'},
    13: {'name': 'Cooking Fat', 'unit': 'kg'},
    14: {'name': 'Cooking Oil', 'unit': 'liters'},
    15: {'name': 'Food Colour', 'unit': 'grams'},
    
    # INDIRECT COSTS (Items 16-23) - Consumed but not in recipes
    16: {'name': 'Crates', 'unit': 'pieces'},          # Special: tracked in Sales
    17: {'name': 'Packaging', 'unit': 'pieces'},
    18: {'name': 'Diesel', 'unit': 'liters'},
    19: {'name': 'Firewood', 'unit': 'bundles'},
    20: {'name': 'Fuel Bolero', 'unit': 'liters'},
    21: {'name': 'Electricity', 'unit': 'units'},
    22: {'name': 'Fuel Transport Trucks', 'unit': 'liters'},
    23: {'name': 'Hair Nets', 'unit': 'pieces'},
}

# Model routing dictionaries
ITEM_DETAILS_MODELS = {1: Item01FlourType1Details, 2: Item02FlourType2Details, ...}
ITEM_PURCHASES_MODELS = {1: Item01FlourType1Purchases, 2: Item02FlourType2Purchases, ...}
ITEM_OUTPUTS_MODELS = {16: Item16CratesOutputs, 17: Item17PackagingOutputs, ...}  # Only 16-23

# Helper functions
def get_details_model(item_id: int): ...
def get_purchases_model(item_id: int): ...
def get_outputs_model(item_id: int): ...  # Raises ValueError for items 1-15
def is_ingredient(item_id: int) -> bool: return 1 <= item_id <= 15
def is_indirect_cost(item_id: int) -> bool: return 16 <= item_id <= 23
def get_item_name(item_id: int) -> str: ...
def get_item_unit(item_id: int) -> str: ...
```

### Per-Item Table Structure
Each of the 23 items has its own Details table, and its own Purchases table.
Items 16-23 (indirect costs) also have an Outputs table.

```python
# Example: Item 1 (Flour Type 1)
class Item01FlourType1Details(models.Model):
    """Current state of Flour Type 1 inventory"""
    name = models.CharField(max_length=100, default="Flour Type 1")
    unit = models.CharField(max_length=20, default="kg")
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_stock_level = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    last_purchase_unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_purchase_date = models.DateField(null=True, blank=True)
    
    @property
    def current_value(self) -> Decimal:
        return self.current_stock * self.last_purchase_unit_price
    
    @property
    def is_low_stock(self) -> bool:
        return self.current_stock <= self.minimum_stock_level

class Item01FlourType1Purchases(models.Model):
    """Immutable purchase records for Flour Type 1"""
    purchase_number = models.CharField(max_length=50, unique=True)  # PUR-01-YYYYMMDD-XXX
    purchase_date = models.DateField()
    supplier_name = models.CharField(max_length=200, blank=True)
    quantity_purchased = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Audit fields
    purchased_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Stock snapshot at time of purchase
    stock_before = models.DecimalField(max_digits=10, decimal_places=2)
    stock_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Purchase records are immutable. Bank ledger policy.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise ValueError("Purchase records cannot be deleted. Bank ledger policy.")

# For items 16-23 only (indirect costs)
class Item16CratesOutputs(models.Model):
    """Immutable consumption records for Crates"""
    output_number = models.CharField(max_length=50, unique=True)  # OUT-16-YYYYMMDD-XXX
    consumption_date = models.DateField()
    quantity_consumed = models.DecimalField(max_digits=10, decimal_places=2)
    reference_type = models.CharField(max_length=50)  # 'SalesDispatch', 'Manual', etc.
    reference_id = models.PositiveIntegerField(null=True)
    description = models.TextField(blank=True)
    
    consumed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    stock_before = models.DecimalField(max_digits=10, decimal_places=2)
    stock_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Same immutability as purchases
```

### StockAlert Model (Shared)
```python
class StockAlert(models.Model):
    """Stock level alerts (WARNING when low, CRITICAL when zero)"""
    class AlertLevel(models.TextChoices):
        WARNING = 'WARNING', 'Warning'
        CRITICAL = 'CRITICAL', 'Critical'
    
    inventory_item_id = models.PositiveIntegerField()
    alert_level = models.CharField(max_length=20, choices=AlertLevel.choices)
    current_stock = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2)
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    triggered_at = models.DateTimeField(auto_now_add=True)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    acknowledged_at = models.DateTimeField(null=True)
```

## 2.4 Production App Models

### ProductionBatch Model (Core)
**File:** `apps/production/models.py` (288 lines)

```python
class ProductionBatch(TimeStampedModel):
    """
    Immutable production batch record.
    Contains frozen snapshot of recipe at time of production.
    """
    batch_number = models.CharField(max_length=50, unique=True)  # PRD-YYYYMMDD-XXX
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    mix = models.ForeignKey(Mix, on_delete=models.PROTECT)
    
    # Frozen recipe snapshot (JSONField)
    mix_snapshot = models.JSONField(
        help_text="Complete recipe data frozen at batch creation time"
    )
    # Structure: {
    #   'mix_id': 1,
    #   'mix_name': 'Standard Bread Mix',
    #   'expected_yield': 100,
    #   'ingredients': [
    #     {'inventory_item_id': 1, 'item_name': 'Flour Type 1', 
    #      'quantity': '50.0000', 'unit': 'kg', 'unit_price': '85.00'},
    #     ...
    #   ],
    #   'total_ingredient_cost': '4250.00'
    # }
    
    # Production metrics
    quantity_produced = models.PositiveIntegerField()
    expected_yield = models.PositiveIntegerField()
    
    # Cost tracking (calculated from mix_snapshot)
    total_ingredient_cost = models.DecimalField(max_digits=12, decimal_places=2)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=4)
    
    # Timestamps
    production_date = models.DateField()
    production_time = models.TimeField(null=True, blank=True)
    produced_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    @property
    def yield_variance(self) -> int:
        """Difference between actual and expected yield"""
        return self.quantity_produced - self.expected_yield
    
    @property
    def yield_variance_percentage(self) -> Decimal:
        """Variance as percentage"""
        if self.expected_yield == 0:
            return Decimal('0')
        return (Decimal(self.quantity_produced) / Decimal(self.expected_yield) - 1) * 100
    
    @property
    def is_within_acceptable_variance(self) -> bool:
        """Check if yield is within mix's acceptable range"""
        pct = Decimal(self.quantity_produced) / Decimal(self.expected_yield)
        return self.mix.yield_variance_min <= pct <= self.mix.yield_variance_max
```

### BatchIngredientDeduction Model
```python
class BatchIngredientDeduction(TimeStampedModel):
    """
    Immutable audit trail of ingredient deductions for a batch.
    One record per ingredient used.
    """
    batch = models.ForeignKey(ProductionBatch, on_delete=models.PROTECT, 
                              related_name='ingredient_deductions')
    
    # Ingredient reference
    inventory_item_id = models.PositiveIntegerField()
    item_name = models.CharField(max_length=100)  # Snapshot at deduction time
    
    # Quantity and cost
    quantity_deducted = models.DecimalField(max_digits=10, decimal_places=4)
    unit = models.CharField(max_length=20)
    unit_price_at_deduction = models.DecimalField(max_digits=10, decimal_places=2)
    line_cost = models.DecimalField(max_digits=12, decimal_places=2)  # qty × price
    
    # Stock snapshot
    stock_before = models.DecimalField(max_digits=10, decimal_places=2)
    stock_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ['batch', 'inventory_item_id']
```

### ProductStock Model
```python
class ProductStock(models.Model):
    """
    Current finished goods stock level per product.
    Updated by Production (add) and Sales (deduct).
    """
    product = models.OneToOneField(Product, on_delete=models.PROTECT, 
                                   related_name='stock')
    current_stock = models.PositiveIntegerField(default=0)
    last_production_date = models.DateField(null=True)
    last_production_batch = models.ForeignKey(ProductionBatch, null=True, 
                                               on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)
```

### ProductStockMovement Model
```python
class ProductStockMovement(TimeStampedModel):
    """
    Immutable audit trail of all finished goods stock changes.
    """
    class MovementType(models.TextChoices):
        PRODUCTION = 'PRODUCTION', 'Production'      # Batch adds stock
        DISPATCH = 'DISPATCH', 'Dispatch'            # Sales dispatch deducts
        RETURN = 'RETURN', 'Return'                  # Sales return adds back
        ADJUSTMENT = 'ADJUSTMENT', 'Adjustment'      # Manual correction
    
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    
    # Quantity (positive = add, negative = deduct)
    quantity = models.IntegerField()  # Can be negative for dispatches
    
    # Stock snapshot
    stock_before = models.PositiveIntegerField()
    stock_after = models.PositiveIntegerField()
    
    # Reference to source record
    reference_type = models.CharField(max_length=50)  # 'ProductionBatch', 'SalesDispatch', etc.
    reference_id = models.PositiveIntegerField()
    
    moved_by = models.ForeignKey(User, on_delete=models.PROTECT)
```

## 2.5 Sales App Models

### SalesDispatch Model
**File:** `apps/sales/models.py` (408 lines)

```python
class SalesDispatch(TimeStampedModel):
    """
    Daily dispatch of products to a salesperson.
    Immutable except for return-related fields.
    """
    class Status(models.TextChoices):
        DISPATCHED = 'DISPATCHED', 'Dispatched'
        RETURNED = 'RETURNED', 'Returned'
    
    dispatch_number = models.CharField(max_length=50, unique=True)  # DSP-YYYYMMDD-XXX
    salesperson = models.ForeignKey(User, on_delete=models.PROTECT,
                                    limit_choices_to={'role': 'SALESMAN'})
    dispatch_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, 
                              default=Status.DISPATCHED)
    
    # Crate tracking
    crates_dispatched = models.PositiveIntegerField(default=0)
    
    # Return status (only mutable fields)
    is_returned = models.BooleanField(default=False)
    returned_at = models.DateTimeField(null=True, blank=True)
    
    # Audit
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['salesperson', 'dispatch_date'],
                name='unique_dispatch_per_salesperson_per_day'
            )
        ]
    
    @property
    def total_units(self) -> int:
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_items(self) -> int:
        return self.items.count()
    
    @property
    def expected_revenue(self) -> Decimal:
        return sum(item.line_total for item in self.items.all())
```

### SalesDispatchItem Model
```python
class SalesDispatchItem(models.Model):
    """Line items for a dispatch. Immutable."""
    dispatch = models.ForeignKey(SalesDispatch, on_delete=models.PROTECT, 
                                 related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Snapshot
    
    class Meta:
        unique_together = ['dispatch', 'product']
    
    @property
    def line_total(self) -> Decimal:
        return Decimal(self.quantity) * self.unit_price
```

### SalesReturn Model
```python
class SalesReturn(TimeStampedModel):
    """
    End-of-day settlement for a dispatch.
    Immutable except for crate resolution booleans.
    """
    dispatch = models.OneToOneField(SalesDispatch, on_delete=models.PROTECT,
                                    related_name='sales_return')
    return_date = models.DateField()
    
    # Calculated totals
    total_units_sold = models.PositiveIntegerField()
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Crate accountability (MUST equal crates_dispatched)
    crates_returned = models.PositiveIntegerField(default=0)
    crates_lost = models.PositiveIntegerField(default=0)
    crates_damaged = models.PositiveIntegerField(default=0)
    
    # Crate resolution status (only mutable fields)
    crates_marked_lost = models.BooleanField(default=False)
    crates_marked_damaged = models.BooleanField(default=False)
    
    # Commission (manually entered by Accountant)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, 
                                            null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    notes = models.TextField(blank=True)
    
    @property
    def crate_deficit(self) -> int:
        """Crates not returned in good condition"""
        return self.crates_lost + self.crates_damaged
    
    @property
    def crates_reconciled(self) -> bool:
        """All crate issues resolved"""
        lost_ok = self.crates_lost == 0 or self.crates_marked_lost
        damaged_ok = self.crates_damaged == 0 or self.crates_marked_damaged
        return lost_ok and damaged_ok
```

### SalesReturnItem Model
```python
class SalesReturnItem(models.Model):
    """Per-product breakdown of a return. Immutable."""
    sales_return = models.ForeignKey(SalesReturn, on_delete=models.PROTECT,
                                     related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    # Quantities (MUST: qty_sold + qty_returned == qty_dispatched)
    qty_dispatched = models.PositiveIntegerField()  # Snapshot from dispatch
    qty_sold = models.PositiveIntegerField()
    qty_returned = models.PositiveIntegerField()
    
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    revenue = models.DecimalField(max_digits=12, decimal_places=2)  # qty_sold × price
    
    class Meta:
        unique_together = ['sales_return', 'product']
    
    def clean(self):
        """Validate accountability"""
        if self.qty_sold + self.qty_returned != self.qty_dispatched:
            raise ValidationError(
                f"qty_sold ({self.qty_sold}) + qty_returned ({self.qty_returned}) "
                f"must equal qty_dispatched ({self.qty_dispatched})"
            )
```

## 2.6 Inventory Utility Functions

**Note:** A new `MiscExpenseCategory` and `MiscExpenseRecord` model will be added to `apps/payroll/models.py` to track expenses not in Inventory (Phase 0 of implementation). See `REPORTS_ANALYTICS_PLANNING.md` for model definition.

**File:** `apps/inventory/utils.py` (614 lines)

These ACID-compliant utilities are the ONLY way to modify inventory:

```python
@transaction.atomic
def create_purchase_atomic(
    item_id: int,
    quantity: Decimal,
    unit_price: Decimal,
    supplier_name: str,
    purchase_date: date,
    user: User,
    notes: str = ""
) -> dict:
    """
    Record a purchase. Updates stock, creates purchase record.
    Returns: {'success': bool, 'purchase': record, 'alert': StockAlert or None}
    """

@transaction.atomic
def create_output_atomic(
    item_id: int,  # Must be 16-23
    quantity: Decimal,
    consumption_date: date,
    reference_type: str,
    reference_id: int,
    user: User,
    description: str = ""
) -> dict:
    """
    Record consumption for indirect costs (items 16-23 only).
    Items 1-15 use deduct_ingredients_atomic instead.
    Returns: {'success': bool, 'output': record, 'alert': StockAlert or None}
    """

@transaction.atomic
def deduct_ingredients_atomic(
    batch: ProductionBatch,
    user: User
) -> dict:
    """
    Bulk deduction for production. Called when creating a batch.
    Deducts all ingredients from mix_snapshot.
    Creates BatchIngredientDeduction records.
    Returns: {'success': bool, 'deductions': [records], 'alerts': [StockAlerts]}
    """

@transaction.atomic
def deduct_crates_atomic(
    quantity: int,
    dispatch: SalesDispatch,
    user: User
) -> dict:
    """
    Deduct crates for a sales dispatch.
    Creates Item16CratesOutputs record for traceability.
    Returns: {'success': bool, 'output': record, 'alert': StockAlert or None}
    """

@transaction.atomic  
def return_crates_atomic(
    quantity: int,
    sales_return: SalesReturn,
    user: User
) -> dict:
    """
    Return crates from a sales return.
    Creates Item16CratesPurchases record (treated as stock addition).
    Returns: {'success': bool, 'purchase': record}
    """

def get_all_stock_levels() -> list[dict]:
    """
    Read-only utility. Returns current stock for all 23 items.
    Returns: [{'item_id': 1, 'name': 'Flour Type 1', 'current_stock': 500, 
               'unit': 'kg', 'minimum': 100, 'is_low': False}, ...]
    """
```

---

# 3. CROSS-APP DATA RELATIONSHIPS

## 3.1 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CHESANTO DATA FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   INVENTORY                     PRODUCTION                   SALES          │
│   ┌──────────┐                 ┌──────────────┐            ┌──────────┐    │
│   │ Purchase │ ─────────────→  │ Batch        │ ─────────→ │ Dispatch │    │
│   │ (add)    │  ingredients    │ (deduct inv) │  products  │ (deduct) │    │
│   └──────────┘                 │ (add stock)  │            └────┬─────┘    │
│        ↓                       └──────────────┘                 │          │
│   ┌──────────┐                       ↓                         ↓          │
│   │ Details  │                 ┌──────────────┐            ┌──────────┐    │
│   │ (state)  │ ←───────────── │ ProductStock │ ←───────── │ Return   │    │
│   └──────────┘  crate returns  │ (current)    │  unsold    │ (add)    │    │
│        ↓                       └──────────────┘            └──────────┘    │
│   ┌──────────┐                                                  ↓          │
│   │ Output   │ ←── crate dispatch ──────────────────────────────┘          │
│   │ (deduct) │                                                             │
│   └──────────┘                                                             │
│                                                                             │
│   ─────────────────────────────────────────────────────────────────────    │
│                                                                             │
│   REPORTS & ANALYTICS (READ-ONLY ACCESS TO ALL)                            │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │  Aggregates, calculations, visualizations                       │      │
│   │  • Daily/Weekly/Monthly summaries                               │      │
│   │  • Cross-app metrics (COGS, margins, efficiency)                │      │
│   │  • Historical trends and forecasting                            │      │
│   └─────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Key Relationships for Analytics

### Revenue Tracking
```python
# From SalesReturn (actual revenue)
total_revenue = SalesReturn.objects.filter(
    return_date__range=(start_date, end_date)
).aggregate(Sum('total_revenue'))['total_revenue__sum']

# From SalesReturnItem (per-product revenue)
product_revenue = SalesReturnItem.objects.filter(
    sales_return__return_date__range=(start_date, end_date)
).values('product__name').annotate(
    revenue=Sum('revenue'),
    units_sold=Sum('qty_sold')
)
```

### Cost of Goods Sold (COGS)
```python
# From ProductionBatch (ingredient cost)
production_cost = ProductionBatch.objects.filter(
    production_date__range=(start_date, end_date)
).aggregate(Sum('total_ingredient_cost'))['total_ingredient_cost__sum']

# From BatchIngredientDeduction (per-ingredient)
ingredient_usage = BatchIngredientDeduction.objects.filter(
    batch__production_date__range=(start_date, end_date)
).values('item_name').annotate(
    total_qty=Sum('quantity_deducted'),
    total_cost=Sum('line_cost')
)
```

### Salesperson Performance
```python
# Revenue and commission by salesperson
salesperson_stats = SalesReturn.objects.filter(
    return_date__range=(start_date, end_date)
).values(
    'dispatch__salesperson__id',
    'dispatch__salesperson__first_name',
    'dispatch__salesperson__last_name'
).annotate(
    total_revenue=Sum('total_revenue'),
    total_commission=Sum('commission_amount'),
    return_count=Count('id'),
    crates_lost=Sum('crates_lost'),
    crates_damaged=Sum('crates_damaged')
)
```

### Production Efficiency
```python
# Yield variance analysis
batches = ProductionBatch.objects.filter(
    production_date__range=(start_date, end_date)
).annotate(
    variance=F('quantity_produced') - F('expected_yield'),
    variance_pct=Cast(F('quantity_produced'), FloatField()) / 
                 Cast(F('expected_yield'), FloatField()) * 100 - 100
)
```

### Inventory Trends
```python
# Purchase history for an item (using routing)
from apps.inventory.routing import get_purchases_model

FlourPurchases = get_purchases_model(1)
flour_history = FlourPurchases.objects.filter(
    purchase_date__range=(start_date, end_date)
).values('purchase_date').annotate(
    total_qty=Sum('quantity_purchased'),
    avg_price=Avg('unit_price'),
    total_cost=Sum('total_cost')
).order_by('purchase_date')
```

---

# 4. REPORTS APP SPECIFICATION

## 4.0 Report Frequency Matrix (FINALIZED)

| Report Type | Daily | Weekly | Monthly | Annual | Notes |
|-------------|:-----:|:------:|:-------:|:------:|-------|
| **Sales Summary** | ✅ | ✅ | ✅ | ✅ | Revenue, products, salesperson |
| **Production Summary** | ✅ | ✅ | ✅ | ✅ | Batches, yields, ingredients |
| **Inventory Summary** | ✅ | ✅ | ✅ | ✅ | Stock, purchases, usage |
| **Profit & Loss** | ✅ | ✅ | ✅ | ✅ | Full P&L statement |
| **Payroll Summary** | ❌ | ❌ | ✅ | ✅ | Monthly/Annual only |
| **Low Stock Alerts** | ✅ | ❌ | ❌ | ❌ | Daily only |
| **Salesperson Performance** | ❌ | ✅ | ✅ | ❌ | Weekly/Monthly |

## 4.1 Current State
**File:** `apps/reports/models.py` - Contains legacy models that need refactoring.
**File:** `apps/reports/views.py` - Empty (just `# Create your views here.`)

### Existing Models (To Be Evaluated)
The Reports app has pre-defined report models:
- `DailyReport` - Hardcoded fields for bread/kdf/scones
- `WeeklyReport` - 7-day aggregations
- `MonthlyReport` - 30-day aggregations

**Issues with Current Design:**
1. Hardcoded product names (bread, kdf, scones) - not flexible
2. Uses old Sales model structure (before rebuild)
3. No actual views or generation logic

## 4.2 Recommended Reports App Architecture

### Design Decision: Real-time vs Pre-computed

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Real-time queries** | Always accurate, no sync issues | Slower for complex queries | Use for dashboards |
| **Pre-computed aggregates** | Fast, good for historical | Needs scheduled jobs, can be stale | Use for reports |
| **Hybrid** | Best of both | More complex | ✅ Recommended |

### Proposed Model Structure

```python
# apps/reports/models.py

class ReportPeriod(models.Model):
    """
    Container for report periods (daily, weekly, monthly).
    Generated automatically via management command or cron job.
    """
    class PeriodType(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'
    
    period_type = models.CharField(max_length=10, choices=PeriodType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Summary metrics (aggregated at generation time)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_production_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_units_produced = models.PositiveIntegerField(default=0)
    total_units_sold = models.PositiveIntegerField(default=0)
    total_commissions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Crate tracking
    total_crates_dispatched = models.PositiveIntegerField(default=0)
    total_crates_lost = models.PositiveIntegerField(default=0)
    total_crates_damaged = models.PositiveIntegerField(default=0)
    
    # Generation metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_locked = models.BooleanField(default=False)  # Lock after review
    
    class Meta:
        unique_together = ['period_type', 'start_date', 'end_date']
        ordering = ['-start_date', 'period_type']


class ReportProductSummary(models.Model):
    """
    Per-product breakdown for a report period.
    Flexible - works with any products in the system.
    """
    report_period = models.ForeignKey(ReportPeriod, on_delete=models.CASCADE,
                                      related_name='product_summaries')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    # Production metrics
    units_produced = models.PositiveIntegerField(default=0)
    production_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    batches_count = models.PositiveIntegerField(default=0)
    
    # Sales metrics
    units_dispatched = models.PositiveIntegerField(default=0)
    units_sold = models.PositiveIntegerField(default=0)
    units_returned = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Calculated
    @property
    def average_selling_price(self) -> Decimal:
        if self.units_sold == 0:
            return Decimal('0')
        return self.revenue / self.units_sold
    
    @property
    def return_rate(self) -> Decimal:
        if self.units_dispatched == 0:
            return Decimal('0')
        return Decimal(self.units_returned) / Decimal(self.units_dispatched) * 100


class ReportSalespersonSummary(models.Model):
    """
    Per-salesperson breakdown for a report period.
    """
    report_period = models.ForeignKey(ReportPeriod, on_delete=models.CASCADE,
                                      related_name='salesperson_summaries')
    salesperson = models.ForeignKey(User, on_delete=models.PROTECT)
    
    # Sales metrics
    dispatch_count = models.PositiveIntegerField(default=0)
    total_units_dispatched = models.PositiveIntegerField(default=0)
    total_units_sold = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Crate accountability
    crates_dispatched = models.PositiveIntegerField(default=0)
    crates_lost = models.PositiveIntegerField(default=0)
    crates_damaged = models.PositiveIntegerField(default=0)
    
    @property
    def crate_loss_rate(self) -> Decimal:
        if self.crates_dispatched == 0:
            return Decimal('0')
        return Decimal(self.crates_lost) / Decimal(self.crates_dispatched) * 100


class ReportInventorySummary(models.Model):
    """
    Per-inventory-item breakdown for a report period.
    """
    report_period = models.ForeignKey(ReportPeriod, on_delete=models.CASCADE,
                                      related_name='inventory_summaries')
    inventory_item_id = models.PositiveIntegerField()
    item_name = models.CharField(max_length=100)
    
    # Opening/closing balances
    opening_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    closing_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Movements
    total_purchased = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_consumed = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Price tracking
    avg_purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    @property
    def stock_movement(self) -> Decimal:
        return self.closing_stock - self.opening_stock
```

## 4.3 Reports App Views

### Access Control

**All report routes require ACCOUNTANT role or higher.**

```python
# apps/reports/decorators.py
REPORT_ACCESS_ROLES = ['SUPERADMIN', 'ADMIN', 'ACCOUNTANT']

def report_access_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.role not in REPORT_ACCESS_ROLES:
            messages.error(request, "Reports require Accountant access or higher.")
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
```

### URL Structure (35 Routes)

```python
# Proposed URL structure
urlpatterns = [
    # ═══════════════════════════════════════════════════════════════
    # DASHBOARD (Entry Point) - ACCOUNTANT+
    # ═══════════════════════════════════════════════════════════════
    path('', views.dashboard, name='dashboard'),
    
    # ═══════════════════════════════════════════════════════════════
    # SALES REPORTS (Daily / Weekly / Monthly / Annual) - ACCOUNTANT+
    # ═══════════════════════════════════════════════════════════════
    path('sales/', views.sales_index, name='sales_index'),
    path('sales/daily/', views.sales_daily, name='sales_daily'),
    path('sales/weekly/', views.sales_weekly, name='sales_weekly'),
    path('sales/monthly/', views.sales_monthly, name='sales_monthly'),
    path('sales/annual/', views.sales_annual, name='sales_annual'),
    path('sales/salesperson/', views.salesperson_performance, name='salesperson_performance'),
    path('sales/commissions/', views.commission_report, name='commission_report'),
    
    # ═══════════════════════════════════════════════════════════════
    # INVENTORY REPORTS (Daily / Weekly / Monthly / Annual) - ACCOUNTANT+
    # ═══════════════════════════════════════════════════════════════
    path('inventory/', views.inventory_index, name='inventory_index'),
    path('inventory/daily/', views.inventory_daily, name='inventory_daily'),
    path('inventory/weekly/', views.inventory_weekly, name='inventory_weekly'),
    path('inventory/monthly/', views.inventory_monthly, name='inventory_monthly'),
    path('inventory/annual/', views.inventory_annual, name='inventory_annual'),
    path('inventory/valuation/', views.inventory_valuation, name='inventory_valuation'),
    path('inventory/purchases/', views.purchase_history, name='purchase_history'),
    
    # ═══════════════════════════════════════════════════════════════
    # PRODUCTION REPORTS (Daily / Weekly / Monthly / Annual) - ACCOUNTANT+
    # ═══════════════════════════════════════════════════════════════
    path('production/', views.production_index, name='production_index'),
    path('production/daily/', views.production_daily, name='production_daily'),
    path('production/weekly/', views.production_weekly, name='production_weekly'),
    path('production/monthly/', views.production_monthly, name='production_monthly'),
    path('production/annual/', views.production_annual, name='production_annual'),
    path('production/efficiency/', views.production_efficiency, name='production_efficiency'),
    path('production/stock-movement/', views.stock_movement, name='stock_movement'),
    
    # ═══════════════════════════════════════════════════════════════
    # PAYROLL REPORTS (Monthly / Annual only) - ACCOUNTANT+
    # ═══════════════════════════════════════════════════════════════
    path('payroll/', views.payroll_index, name='payroll_index'),
    path('payroll/monthly/', views.payroll_monthly, name='payroll_monthly'),
    path('payroll/annual/', views.payroll_annual, name='payroll_annual'),
    path('payroll/casual-labor/', views.casual_labor_report, name='casual_labor_report'),
    path('payroll/misc-expenses/', views.misc_expense_report, name='misc_expense_report'),
    
    # ═══════════════════════════════════════════════════════════════
    # PROFIT & LOSS REPORTS (Daily / Weekly / Monthly / Annual) - ACCOUNTANT+
    # ═══════════════════════════════════════════════════════════════
    path('financial/', views.financial_index, name='financial_index'),
    path('financial/pnl/daily/', views.profit_loss_daily, name='profit_loss_daily'),
    path('financial/pnl/weekly/', views.profit_loss_weekly, name='profit_loss_weekly'),
    path('financial/pnl/monthly/', views.profit_loss_monthly, name='profit_loss_monthly'),
    path('financial/pnl/annual/', views.profit_loss_annual, name='profit_loss_annual'),
    path('financial/product-performance/', views.product_performance, name='product_performance'),
    path('financial/expense-summary/', views.expense_summary, name='expense_summary'),
    
    # ═══════════════════════════════════════════════════════════════
    # EXPORT/EMAIL ENDPOINTS (AJAX) - ACCOUNTANT+
    # ═══════════════════════════════════════════════════════════════
    path('export/csv/', views.export_csv, name='export_csv'),
    path('email/send/', views.email_report, name='email_report'),
]
```

## 4.4 Report Generation Service

### Email from Frontend: Universal Feature ✅

Every report view will have an "Email Report" button that:
1. Pre-fills current user's email
2. Allows adding additional recipients
3. Sends HTML report body + CSV attachment
4. Logs action to audit trail

```
┌─────────────────────────────────────────────────────────────┐
│  ANY REPORT VIEW                                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  [Export CSV]  [Print]  [📧 Email Report]              ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Report Data (table)                                   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Complete URL Reference

| URL | View Name | Purpose | Access | Email |
|-----|-----------|---------|--------|-------|
| `/reports/` | `dashboard` | Reports hub with KPIs | ACCOUNTANT+ | - |
| **SALES** |||||
| `/reports/sales/` | `sales_index` | Sales reports list | ACCOUNTANT+ | - |
| `/reports/sales/daily/` | `sales_daily` | Daily sales summary | ACCOUNTANT+ | ✅ |
| `/reports/sales/weekly/` | `sales_weekly` | Weekly sales summary | ACCOUNTANT+ | ✅ |
| `/reports/sales/monthly/` | `sales_monthly` | Monthly sales summary | ACCOUNTANT+ | ✅ |
| `/reports/sales/annual/` | `sales_annual` | Annual sales summary | ACCOUNTANT+ | ✅ |
| `/reports/sales/salesperson/` | `salesperson_performance` | Per-salesperson metrics | ACCOUNTANT+ | ✅ |
| `/reports/sales/commissions/` | `commission_report` | Commission breakdown | ACCOUNTANT+ | ✅ |
| **INVENTORY** |||||
| `/reports/inventory/` | `inventory_index` | Inventory reports list | ACCOUNTANT+ | - |
| `/reports/inventory/daily/` | `inventory_daily` | Daily inventory summary | ACCOUNTANT+ | ✅ |
| `/reports/inventory/weekly/` | `inventory_weekly` | Weekly inventory summary | ACCOUNTANT+ | ✅ |
| `/reports/inventory/monthly/` | `inventory_monthly` | Monthly inventory summary | ACCOUNTANT+ | ✅ |
| `/reports/inventory/annual/` | `inventory_annual` | Annual inventory summary | ACCOUNTANT+ | ✅ |
| `/reports/inventory/valuation/` | `inventory_valuation` | Stock values | ACCOUNTANT+ | ✅ |
| `/reports/inventory/purchases/` | `purchase_history` | Purchase log | ACCOUNTANT+ | ✅ |
| **PRODUCTION** |||||
| `/reports/production/` | `production_index` | Production reports list | ACCOUNTANT+ | - |
| `/reports/production/daily/` | `production_daily` | Daily production summary | ACCOUNTANT+ | ✅ |
| `/reports/production/weekly/` | `production_weekly` | Weekly production summary | ACCOUNTANT+ | ✅ |
| `/reports/production/monthly/` | `production_monthly` | Monthly production summary | ACCOUNTANT+ | ✅ |
| `/reports/production/annual/` | `production_annual` | Annual production summary | ACCOUNTANT+ | ✅ |
| `/reports/production/efficiency/` | `production_efficiency` | Yield analysis | ACCOUNTANT+ | ✅ |
| `/reports/production/stock-movement/` | `stock_movement` | Product stock flow | ACCOUNTANT+ | ✅ |
| **PAYROLL** (Monthly & Annual only) |||||
| `/reports/payroll/` | `payroll_index` | Payroll reports list | ACCOUNTANT+ | - |
| `/reports/payroll/monthly/` | `payroll_monthly` | Monthly payroll summary | ACCOUNTANT+ | ✅ |
| `/reports/payroll/annual/` | `payroll_annual` | Annual payroll + YTD | ACCOUNTANT+ | ✅ |
| `/reports/payroll/casual-labor/` | `casual_labor_report` | Casual payments | ACCOUNTANT+ | ✅ |
| `/reports/payroll/misc-expenses/` | `misc_expense_report` | Miscellaneous expenses | ACCOUNTANT+ | ✅ |
| **FINANCIAL / P&L** |||||
| `/reports/financial/` | `financial_index` | Financial reports list | ACCOUNTANT+ | - |
| `/reports/financial/pnl/daily/` | `profit_loss_daily` | Daily P&L | ACCOUNTANT+ | ✅ |
| `/reports/financial/pnl/weekly/` | `profit_loss_weekly` | Weekly P&L | ACCOUNTANT+ | ✅ |
| `/reports/financial/pnl/monthly/` | `profit_loss_monthly` | Monthly P&L | ACCOUNTANT+ | ✅ |
| `/reports/financial/pnl/annual/` | `profit_loss_annual` | Annual P&L | ACCOUNTANT+ | ✅ |
| `/reports/financial/product-performance/` | `product_performance` | Product profitability | ACCOUNTANT+ | ✅ |
| `/reports/financial/expense-summary/` | `expense_summary` | All expenses | ACCOUNTANT+ | ✅ |
| **ACTIONS** |||||
| `/reports/export/csv/` | `export_csv` | CSV download (POST) | ACCOUNTANT+ | - |
| `/reports/email/send/` | `email_report` | Send any report (POST) | ACCOUNTANT+ | - |

**Total Routes: 35** | **Email-capable: 28**

## 4.5 Report Generation Service

```python
# apps/reports/services.py

class ReportGenerationService:
    """
    Service for generating report periods from live data.
    Can be called via management command or cron job.
    """
    
    @staticmethod
    @transaction.atomic
    def generate_daily_report(date: date, user: User) -> ReportPeriod:
        """Generate daily report for a specific date."""
        
        # Create or get report period
        report, created = ReportPeriod.objects.get_or_create(
            period_type=ReportPeriod.PeriodType.DAILY,
            start_date=date,
            end_date=date,
            defaults={'generated_by': user}
        )
        
        if not created and report.is_locked:
            raise ValueError("Report is locked and cannot be regenerated")
        
        # Aggregate sales data
        sales_data = SalesReturn.objects.filter(
            return_date=date
        ).aggregate(
            total_revenue=Sum('total_revenue'),
            total_units_sold=Sum('total_units_sold'),
            total_commission=Sum('commission_amount'),
            crates_dispatched=Sum('dispatch__crates_dispatched'),
            crates_lost=Sum('crates_lost'),
            crates_damaged=Sum('crates_damaged')
        )
        
        # Aggregate production data
        production_data = ProductionBatch.objects.filter(
            production_date=date
        ).aggregate(
            total_units=Sum('quantity_produced'),
            total_cost=Sum('total_ingredient_cost')
        )
        
        # Update report period
        report.total_revenue = sales_data['total_revenue'] or 0
        report.total_units_sold = sales_data['total_units_sold'] or 0
        report.total_commissions = sales_data['total_commission'] or 0
        report.total_crates_dispatched = sales_data['crates_dispatched'] or 0
        report.total_crates_lost = sales_data['crates_lost'] or 0
        report.total_crates_damaged = sales_data['crates_damaged'] or 0
        report.total_units_produced = production_data['total_units'] or 0
        report.total_production_cost = production_data['total_cost'] or 0
        report.save()
        
        # Generate product summaries
        ReportGenerationService._generate_product_summaries(report, date, date)
        
        # Generate salesperson summaries
        ReportGenerationService._generate_salesperson_summaries(report, date, date)
        
        return report
    
    @staticmethod
    def _generate_product_summaries(report: ReportPeriod, start: date, end: date):
        """Generate per-product breakdowns."""
        # Clear existing
        report.product_summaries.all().delete()
        
        # Production by product
        production_qs = ProductionBatch.objects.filter(
            production_date__range=(start, end)
        ).values('product').annotate(
            units=Sum('quantity_produced'),
            cost=Sum('total_ingredient_cost'),
            batches=Count('id')
        )
        
        # Sales by product
        sales_qs = SalesReturnItem.objects.filter(
            sales_return__return_date__range=(start, end)
        ).values('product').annotate(
            dispatched=Sum('qty_dispatched'),
            sold=Sum('qty_sold'),
            returned=Sum('qty_returned'),
            revenue=Sum('revenue')
        )
        
        # Merge and create summaries...
```

---

# 5. ANALYTICS APP SPECIFICATION

## 5.1 Current State
**File:** `apps/analytics/views.py` - Contains disabled views with placeholder messages.
**File:** `apps/analytics/urls.py` - Has route definitions.

The Analytics app was disabled during the Sales app rebuild. It needs to be restored using the new model structure.

## 5.2 Analytics vs Reports: Key Distinction

| Aspect | Reports App | Analytics App |
|--------|-------------|---------------|
| **Purpose** | Historical records | Real-time insights |
| **Data** | Pre-computed aggregates | Live queries |
| **Models** | Has own models (ReportPeriod) | NO models (reads others) |
| **Speed** | Fast (pre-computed) | May be slower (live) |
| **Use Case** | "Show me September's sales" | "How are we doing today?" |
| **Export** | CSV, PDF | Interactive charts |

## 5.3 Recommended Analytics Dashboards

### Dashboard 1: Executive Overview
**URL:** `/analytics/`
**Purpose:** High-level KPIs for management

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTIVE DASHBOARD                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TODAY'S SNAPSHOT                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Revenue  │ │ Units    │ │ Batches  │ │ Alerts   │           │
│  │ KES 45K  │ │ Sold 850 │ │ 12 Done  │ │ 3 Low    │           │
│  │ ↑ 12%    │ │ ↑ 8%     │ │ ↓ 2      │ │ Stock    │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │            REVENUE TREND (Last 7 Days)                  │   │
│  │    📈 Line chart showing daily revenue                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────┐ ┌────────────────────────────┐     │
│  │   TOP PRODUCTS TODAY   │ │   TOP SALESPEOPLE TODAY    │     │
│  │   🥧 Pie chart          │ │   📊 Horizontal bar chart  │     │
│  └────────────────────────┘ └────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Dashboard 2: Sales Analytics
**URL:** `/analytics/sales/`
**Purpose:** Detailed sales performance

**Charts:**
1. **Revenue by Day** (Line chart, 30 days)
2. **Sales by Product** (Donut chart)
3. **Salesperson Leaderboard** (Horizontal bar)
4. **Return Rate Trend** (Line chart)
5. **Crate Accountability** (Stacked bar - returned/lost/damaged)

### Dashboard 3: Production Analytics
**URL:** `/analytics/production/`
**Purpose:** Production efficiency metrics

**Charts:**
1. **Daily Output** (Bar chart, 14 days)
2. **Yield Variance** (Line chart with target bands)
3. **Product Mix** (Pie chart)
4. **Batch Completion Time** (if tracking)
5. **Production vs Sales** (Dual-axis line chart)

### Dashboard 4: Inventory Analytics
**URL:** `/analytics/inventory/`
**Purpose:** Stock management insights

**Charts:**
1. **Current Stock Levels** (Horizontal bar with min lines)
2. **Stock Alerts Timeline** (Scatter/timeline)
3. **Purchase Price Trends** (Multi-line for key items)
4. **Consumption Patterns** (Stacked area chart)

### Dashboard 5: Profitability Analytics
**URL:** `/analytics/profitability/`
**Purpose:** Financial performance

**Charts:**
1. **Revenue vs COGS** (Stacked bar)
2. **Gross Margin Trend** (Line chart)
3. **Product Profitability** (Bubble chart: revenue × margin × volume)
4. **Commission Impact** (Bar showing revenue, cost, commission, net)

## 5.4 Analytics Views Structure

```python
# apps/analytics/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, F, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.sales.models import SalesDispatch, SalesReturn, SalesReturnItem
from apps.production.models import ProductionBatch, ProductStock
from apps.products.models import Product
from apps.inventory.routing import INVENTORY_ITEMS, get_details_model
from apps.inventory.models import StockAlert


@login_required
def executive_dashboard(request):
    """Main analytics dashboard with KPIs and charts."""
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)
    thirty_days_ago = today - timedelta(days=30)
    
    # Today's KPIs
    today_revenue = SalesReturn.objects.filter(
        return_date=today
    ).aggregate(total=Sum('total_revenue'))['total'] or Decimal('0')
    
    today_units_sold = SalesReturn.objects.filter(
        return_date=today
    ).aggregate(total=Sum('total_units_sold'))['total'] or 0
    
    today_batches = ProductionBatch.objects.filter(
        production_date=today
    ).count()
    
    active_alerts = StockAlert.objects.filter(
        is_acknowledged=False
    ).count()
    
    # 7-day revenue trend
    revenue_trend = []
    for i in range(7):
        day = today - timedelta(days=6-i)
        day_revenue = SalesReturn.objects.filter(
            return_date=day
        ).aggregate(total=Sum('total_revenue'))['total'] or 0
        revenue_trend.append({
            'date': day.strftime('%a'),
            'revenue': float(day_revenue)
        })
    
    # Today's product breakdown
    product_sales = SalesReturnItem.objects.filter(
        sales_return__return_date=today
    ).values('product__name').annotate(
        revenue=Sum('revenue')
    ).order_by('-revenue')[:5]
    
    # Today's salesperson leaderboard
    salesperson_stats = SalesReturn.objects.filter(
        return_date=today
    ).values(
        'dispatch__salesperson__first_name',
        'dispatch__salesperson__last_name'
    ).annotate(
        revenue=Sum('total_revenue')
    ).order_by('-revenue')[:5]
    
    context = {
        'today': today,
        # KPIs
        'today_revenue': today_revenue,
        'today_units_sold': today_units_sold,
        'today_batches': today_batches,
        'active_alerts': active_alerts,
        # Chart data (JSON for Chart.js)
        'revenue_trend_json': json.dumps(revenue_trend),
        'product_sales_json': json.dumps(list(product_sales)),
        'salesperson_stats_json': json.dumps(list(salesperson_stats)),
    }
    
    return render(request, 'analytics/executive_dashboard.html', context)
```

---

# 6. UI/STYLING PATTERNS

## 6.1 Established Design System

All templates follow consistent patterns established in Sales app rebuild.

### Color Palette

```css
/* Primary Blues (main brand) */
--blue-900: #1e3a8a;
--blue-800: #1e40af;
--blue-700: #1d4ed8;
--blue-600: #2563eb;
--blue-500: #3b82f6;
--blue-400: #60a5fa;

/* Accent Colors */
--green-600: #059669;    /* Success, positive values */
--amber-500: #f59e0b;    /* Warning, pending */
--red-600: #dc2626;      /* Error, negative values */

/* Neutrals */
--gray-900: #111827;     /* Headings */
--gray-700: #374151;     /* Body text */
--gray-500: #6b7280;     /* Secondary text */
--gray-200: #e5e7eb;     /* Borders */
--gray-100: #f3f4f6;     /* Backgrounds */
```

### Gradient Headers

```css
/* Section headers use blue gradient */
.section-header {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
    color: white;
    padding: 1.25rem 1.5rem;
    border-radius: 0.75rem 0.75rem 0 0;
}

/* Crate sections use amber gradient */
.crates-section__header {
    background: linear-gradient(135deg, #92400e 0%, #d97706 100%);
}

/* Success/summary sections use green */
.summary-section {
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
}
```

### Stats Bar Pattern

```html
<!-- Used in dispatch_form, dashboard, etc. -->
<div class="stats-bar">
    <div class="stats-bar__item">
        <span class="stats-bar__label">Total Revenue</span>
        <span class="stats-bar__value">KES 45,000</span>
    </div>
    <div class="stats-bar__item stats-bar__item--success">
        <span class="stats-bar__label">Units Sold</span>
        <span class="stats-bar__value">850</span>
    </div>
    <div class="stats-bar__item stats-bar__item--warning">
        <span class="stats-bar__label">Returns</span>
        <span class="stats-bar__value">45</span>
    </div>
</div>
```

```css
.stats-bar {
    display: flex;
    gap: 1.5rem;
    padding: 0.75rem 1.5rem;
    background: #f8fafc;
    border-bottom: 1px solid #e5e7eb;
}

.stats-bar__item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.stats-bar__label {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280;
}

.stats-bar__value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #111827;
}

.stats-bar__item--success .stats-bar__value { color: #059669; }
.stats-bar__item--warning .stats-bar__value { color: #d97706; }
.stats-bar__item--danger .stats-bar__value { color: #dc2626; }
```

### Card Pattern

```html
<div class="card">
    <div class="card__header">
        <h2 class="card__title">
            <svg>...</svg>
            Section Title
        </h2>
    </div>
    <div class="card__content">
        <!-- Content here -->
    </div>
</div>
```

### Table Pattern

```css
.data-table {
    width: 100%;
    border-collapse: collapse;
}

.data-table__th {
    padding: 0.875rem 1rem;
    text-align: left;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #6b7280;
    background: #f9fafb;
    border-bottom: 1px solid #e5e7eb;
}

.data-table__td {
    padding: 1rem;
    border-bottom: 1px solid #f3f4f6;
    vertical-align: middle;
}

.data-table__row:hover {
    background: #f8fafc;
}
```

### Button Styles

```css
.btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 1.25rem;
    border-radius: 0.5rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
}

.btn--primary {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
    color: white;
    border: none;
}

.btn--primary:hover {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
}

.btn--secondary {
    background: white;
    color: #374151;
    border: 1px solid #d1d5db;
}

.btn--secondary:hover {
    background: #f9fafb;
}
```

## 6.2 Date/Time Formatting Standard

| Field Type | Django Filter | Example Output |
|------------|---------------|----------------|
| DateField | `\|date:"M d, Y"` | Dec 04, 2025 |
| DateTimeField | `\|date:"M d, Y, g:i A"` | Dec 04, 2025, 3:22 PM |
| TimeField | `\|time:"g:i A"` | 3:22 PM |

## 6.3 Number Formatting

```python
# In views, format for display
revenue_display = f"KES {revenue:,.2f}"  # KES 45,000.00
percentage = f"{rate:.1f}%"               # 7.5%
units = f"{count:,}"                      # 1,234

# In templates
{{ value|floatformat:2 }}                 # 45000.00
{{ value|intcomma }}                      # 45,000 (requires humanize)
```

---

# 7. CHART.JS INTEGRATION

## 7.1 Why Chart.js

| Criteria | Chart.js | Verdict |
|----------|----------|---------|
| **Size** | ~60KB gzipped | ✅ Lightweight |
| **Django Integration** | JSON via template | ✅ Easy |
| **Chart Types** | Line, Bar, Pie, Doughnut, etc. | ✅ Sufficient |
| **Responsiveness** | Built-in | ✅ Mobile-friendly |
| **Documentation** | Excellent | ✅ Easy to learn |
| **Customization** | Good enough | ✅ Meets needs |

## 7.2 Setup

### Include Chart.js (via CDN)
```html
<!-- base.html or analytics/base_analytics.html -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
```

### Base Template Structure
```html
{% extends "base.html" %}

{% block extra_head %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
{% endblock %}

{% block content %}
<div class="dashboard">
    <div class="chart-container">
        <canvas id="revenueChart"></canvas>
    </div>
</div>

<script>
// Chart data passed from Django view
const chartData = {{ chart_data_json|safe }};
</script>
{% endblock %}
```

## 7.3 Common Chart Patterns

### Line Chart (Revenue Trend)
```javascript
// Revenue over time
const revenueCtx = document.getElementById('revenueChart').getContext('2d');
new Chart(revenueCtx, {
    type: 'line',
    data: {
        labels: chartData.dates,  // ['Mon', 'Tue', 'Wed', ...]
        datasets: [{
            label: 'Revenue (KES)',
            data: chartData.values,  // [45000, 52000, 48000, ...]
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4,  // Smooth curves
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: (ctx) => `KES ${ctx.parsed.y.toLocaleString()}`
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    callback: (value) => `KES ${(value/1000).toFixed(0)}K`
                }
            }
        }
    }
});
```

### Doughnut Chart (Product Breakdown)
```javascript
// Sales by product
const productCtx = document.getElementById('productChart').getContext('2d');
new Chart(productCtx, {
    type: 'doughnut',
    data: {
        labels: chartData.products,  // ['Bread', 'KDF', 'Scones']
        datasets: [{
            data: chartData.values,  // [25000, 15000, 8000]
            backgroundColor: [
                '#3b82f6',  // Blue
                '#10b981',  // Green
                '#f59e0b',  // Amber
                '#ef4444',  // Red
                '#8b5cf6',  // Purple
            ],
            borderWidth: 0,
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',  // Doughnut hole size
        plugins: {
            legend: {
                position: 'bottom',
                labels: { padding: 20 }
            }
        }
    }
});
```

### Horizontal Bar Chart (Leaderboard)
```javascript
// Salesperson leaderboard
const leaderboardCtx = document.getElementById('leaderboardChart').getContext('2d');
new Chart(leaderboardCtx, {
    type: 'bar',
    data: {
        labels: chartData.names,  // ['John', 'Mary', 'Peter']
        datasets: [{
            label: 'Revenue',
            data: chartData.values,  // [25000, 22000, 18000]
            backgroundColor: '#3b82f6',
            borderRadius: 4,
        }]
    },
    options: {
        indexAxis: 'y',  // Horizontal
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false }
        },
        scales: {
            x: {
                beginAtZero: true,
                ticks: {
                    callback: (value) => `KES ${(value/1000).toFixed(0)}K`
                }
            }
        }
    }
});
```

### Stacked Bar Chart (Crate Accountability)
```javascript
// Crate tracking
const crateCtx = document.getElementById('crateChart').getContext('2d');
new Chart(crateCtx, {
    type: 'bar',
    data: {
        labels: chartData.dates,
        datasets: [
            {
                label: 'Returned',
                data: chartData.returned,
                backgroundColor: '#10b981',
            },
            {
                label: 'Lost',
                data: chartData.lost,
                backgroundColor: '#ef4444',
            },
            {
                label: 'Damaged',
                data: chartData.damaged,
                backgroundColor: '#f59e0b',
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { stacked: true },
            y: { stacked: true }
        }
    }
});
```

## 7.4 Django View Pattern for Charts

```python
# views.py
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    """Handle Decimal serialization for Chart.js"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

@login_required
def dashboard(request):
    # ... aggregate data ...
    
    revenue_chart_data = {
        'dates': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'values': [45000, 52000, 48000, 55000, 61000, 45000, 38000]
    }
    
    context = {
        'revenue_chart_json': json.dumps(revenue_chart_data, cls=DecimalEncoder),
        # ... other context ...
    }
    return render(request, 'analytics/dashboard.html', context)
```

---

# 8. IMPLEMENTATION WORKFLOWS

## 8.1 Workflow-First Approach

Following the pattern established with foundation apps:

1. **Define Workflows** - What operations, who does them, what data
2. **Design Models** - Based on workflow needs
3. **Create Utilities** - Reusable service functions
4. **Build Views** - One workflow at a time
5. **Create Templates** - Consistent styling
6. **Test & Iterate** - Dry test each feature

## 8.2 Reports App Implementation Order

### Phase 0: New Model (MiscExpense in Payroll) - Day 0
1. Add `MiscExpenseCategory` and `MiscExpenseRecord` to `apps/payroll/models.py`
2. Create migration
3. Add admin registration
4. Create views for CRUD (similar to CasualLabor)
5. Seed default categories

### Phase 1: Foundation (Day 1)
1. Install Django-Q2, configure settings
2. Create `apps/reports/` structure with services/utils
3. Implement utility functions (export, email, audit)
4. Create base_report.html (print-friendly)
5. Create `report_access_required` decorator (ACCOUNTANT+)

### Phase 2: Manual Reports (Day 2-3)
1. Build Reports Dashboard (`/reports/`)
2. Sales Daily/Weekly/Monthly/Annual views
3. Production Daily/Weekly/Monthly/Annual views  
4. Inventory Daily/Weekly/Monthly/Annual views
5. P&L Daily/Weekly/Monthly/Annual views
6. Payroll Monthly/Annual views
7. Add Export CSV and Email buttons to all

### Phase 3: Scheduled Reports (Day 4)
1. Configure Django-Q2 schedules via Admin
2. Daily reports tasks (6 AM EAT)
3. Weekly reports tasks (Monday 7 AM EAT)
4. Monthly reports tasks (1st, 8 AM EAT)
5. Annual reports tasks (Jan 2nd, 9 AM EAT)
6. Event-triggered tasks (Payroll FINALIZED, etc.)

### Phase 4: Cross-App Analytics (Day 5)
1. COGS calculations
2. Margin analysis
3. Product Performance report
4. Dashboard with KPIs

## 8.3 Analytics App Implementation Order

### Phase 1: Executive Dashboard (Day 5)
1. Fix/restore `apps/analytics/views.py`
2. Create executive dashboard view
3. Build KPI calculation utilities
4. Create dashboard template with Chart.js

### Phase 2: Sales Analytics (Day 6)
5. Sales analytics view
6. Revenue trend chart
7. Product breakdown chart
8. Salesperson leaderboard

### Phase 3: Production Analytics (Day 7)
9. Production analytics view
10. Output charts
11. Yield variance visualization

### Phase 4: Inventory Analytics (Day 8)
12. Inventory analytics view
13. Stock level visualization
14. Price trend charts

### Phase 5: Profitability (Day 9)
15. Profitability dashboard
16. COGS calculations
17. Margin analysis

## 8.4 Testing Strategy

```bash
# After each phase, run:
python manage.py runserver

# Manual testing checklist:
# 1. Navigate to each new page
# 2. Verify data displays correctly
# 3. Check charts render
# 4. Test filters and date ranges
# 5. Verify calculations match manual verification
# 6. Test on mobile viewport
```

---

# 9. QUERY PATTERNS & EXAMPLES

## 9.1 Common Aggregations

### Daily Revenue
```python
from django.db.models import Sum
from apps.sales.models import SalesReturn

def get_daily_revenue(date):
    return SalesReturn.objects.filter(
        return_date=date
    ).aggregate(
        total=Sum('total_revenue')
    )['total'] or Decimal('0')
```

### Revenue by Date Range
```python
def get_revenue_by_day(start_date, end_date):
    """Returns list of {date, revenue} dicts"""
    from django.db.models.functions import TruncDate
    
    return SalesReturn.objects.filter(
        return_date__range=(start_date, end_date)
    ).annotate(
        day=TruncDate('return_date')
    ).values('day').annotate(
        revenue=Sum('total_revenue')
    ).order_by('day')
```

### Salesperson Ranking
```python
def get_salesperson_ranking(start_date, end_date, limit=10):
    return SalesReturn.objects.filter(
        return_date__range=(start_date, end_date)
    ).values(
        'dispatch__salesperson__id',
        'dispatch__salesperson__first_name',
        'dispatch__salesperson__last_name'
    ).annotate(
        total_revenue=Sum('total_revenue'),
        total_units=Sum('total_units_sold'),
        dispatch_count=Count('dispatch', distinct=True),
        commission=Sum('commission_amount')
    ).order_by('-total_revenue')[:limit]
```

### Product Performance
```python
def get_product_performance(start_date, end_date):
    return SalesReturnItem.objects.filter(
        sales_return__return_date__range=(start_date, end_date)
    ).values(
        'product__id',
        'product__name'
    ).annotate(
        units_dispatched=Sum('qty_dispatched'),
        units_sold=Sum('qty_sold'),
        units_returned=Sum('qty_returned'),
        revenue=Sum('revenue')
    ).order_by('-revenue')
```

### Production Output
```python
def get_production_by_day(start_date, end_date):
    return ProductionBatch.objects.filter(
        production_date__range=(start_date, end_date)
    ).values('production_date').annotate(
        total_units=Sum('quantity_produced'),
        total_cost=Sum('total_ingredient_cost'),
        batch_count=Count('id')
    ).order_by('production_date')
```

### Inventory Stock Levels
```python
def get_all_stock_status():
    """Get current stock for all 23 items"""
    from apps.inventory.routing import INVENTORY_ITEMS, get_details_model
    
    result = []
    for item_id, item_info in INVENTORY_ITEMS.items():
        DetailsModel = get_details_model(item_id)
        try:
            details = DetailsModel.objects.first()
            result.append({
                'item_id': item_id,
                'name': item_info['name'],
                'unit': item_info['unit'],
                'current_stock': details.current_stock if details else 0,
                'minimum': details.minimum_stock_level if details else 0,
                'is_low': details.is_low_stock if details else False,
                'last_price': details.last_purchase_unit_price if details else 0,
            })
        except Exception:
            result.append({
                'item_id': item_id,
                'name': item_info['name'],
                'error': 'No data'
            })
    return result
```

### Crate Accountability
```python
def get_crate_summary(start_date, end_date):
    return SalesReturn.objects.filter(
        return_date__range=(start_date, end_date)
    ).aggregate(
        total_dispatched=Sum('dispatch__crates_dispatched'),
        total_returned=Sum('crates_returned'),
        total_lost=Sum('crates_lost'),
        total_damaged=Sum('crates_damaged')
    )
```

---

# 10. TASK FUNCTIONS REFERENCE

## 10.1 Overview

Task Functions are **backend scheduled jobs** defined in `apps/reports/tasks.py`. They:
- Run automatically on a schedule (configured by SUPERADMIN via Django Admin)
- Use the same service logic as frontend views
- Auto-email reports to configured recipients
- Are NOT directly viewable on frontend UI

**Management Philosophy:**
| Responsibility | Owner |
|----------------|-------|
| Define functions | Developer (in code) |
| Schedule timing | SUPERADMIN (via Django Admin) |
| Pause/Resume | SUPERADMIN (via Django Admin) |
| View history/failures | SUPERADMIN (via Django Admin) |

## 10.2 Task Function Definitions

### Daily Tasks (6 functions) - Run 6:00 AM EAT

| Function Name | Purpose | Default Recipients |
|---------------|---------|-------------------|
| `daily_sales_summary` | Yesterday's sales totals, by product, by salesperson | SUPERADMIN |
| `daily_production_summary` | Batches produced, ingredients used | SUPERADMIN |
| `daily_inventory_summary` | Stock levels, purchases, usage | SUPERADMIN |
| `daily_profit_loss` | Daily P&L statement | SUPERADMIN |
| `daily_low_stock_alerts` | Items below reorder level | SUPERADMIN |
| `daily_dispatch_summary` | Dispatches sent, crates out | SUPERADMIN |

### Weekly Tasks (5 functions) - Run Monday 7:00 AM EAT

| Function Name | Purpose | Default Recipients |
|---------------|---------|-------------------|
| `weekly_sales_summary` | This week's sales + comparison to last week | SUPERADMIN |
| `weekly_production_summary` | Batches, yields, efficiency | SUPERADMIN |
| `weekly_inventory_summary` | Purchases, usage, current levels | SUPERADMIN |
| `weekly_profit_loss` | Weekly P&L statement | SUPERADMIN |
| `weekly_salesperson_performance` | Revenue, commission, crate accountability | SUPERADMIN |

### Monthly Tasks (7 functions) - Run 1st of month 8:00 AM EAT

| Function Name | Purpose | Default Recipients |
|---------------|---------|-------------------|
| `monthly_sales_summary` | Full month sales breakdown | SUPERADMIN |
| `monthly_production_summary` | Production metrics for the month | SUPERADMIN |
| `monthly_inventory_summary` | Stock value, movement, valuation | SUPERADMIN |
| `monthly_profit_loss` | Monthly P&L statement | SUPERADMIN |
| `monthly_payroll_summary` | Total payroll, statutory deductions | SUPERADMIN |
| `monthly_casual_labor_summary` | Casual payments for the month | SUPERADMIN |
| `monthly_expense_summary` | Indirect costs + miscellaneous | SUPERADMIN |

### Annual Tasks (5 functions) - Run January 2nd 9:00 AM EAT

| Function Name | Purpose | Default Recipients |
|---------------|---------|-------------------|
| `annual_sales_summary` | Full year sales breakdown | SUPERADMIN |
| `annual_production_summary` | Yearly production metrics | SUPERADMIN |
| `annual_inventory_summary` | Yearly stock movement + valuation | SUPERADMIN |
| `annual_profit_loss` | Annual P&L statement | SUPERADMIN |
| `annual_payroll_summary` | Yearly payroll + YTD per employee | SUPERADMIN |

### On-Demand Tasks (3 functions)

| Function Name | Purpose | Triggered By |
|---------------|---------|--------------|
| `send_report_email` | Generic: send any report to recipients | Manual from frontend |
| `send_payroll_report` | Email specific payroll period | Payroll FINALIZED event |
| `archive_report` | Send report to archive email | Any report generation |

**Total: 26 task functions**

## 10.3 Scheduled Reports (Default Cron)

### Daily (6:00 AM EAT)
| Task | Cron | Active |
|------|------|--------|
| `daily_sales_summary` | `0 6 * * *` | ✅ |
| `daily_production_summary` | `0 6 * * *` | ✅ |
| `daily_inventory_summary` | `0 6 * * *` | ✅ |
| `daily_profit_loss` | `0 6 * * *` | ✅ |
| `daily_low_stock_alerts` | `0 6 * * *` | ✅ |

### Weekly (Monday 7:00 AM EAT)
| Task | Cron | Active |
|------|------|--------|
| `weekly_sales_summary` | `0 7 * * 1` | ✅ |
| `weekly_production_summary` | `0 7 * * 1` | ✅ |
| `weekly_inventory_summary` | `0 7 * * 1` | ✅ |
| `weekly_profit_loss` | `0 7 * * 1` | ✅ |
| `weekly_salesperson_performance` | `0 7 * * 1` | ✅ |

### Monthly (1st of month, 8:00 AM EAT)
| Task | Cron | Active |
|------|------|--------|
| `monthly_sales_summary` | `0 8 1 * *` | ✅ |
| `monthly_production_summary` | `0 8 1 * *` | ✅ |
| `monthly_inventory_summary` | `0 8 1 * *` | ✅ |
| `monthly_profit_loss` | `0 8 1 * *` | ✅ |
| `monthly_payroll_summary` | `0 8 1 * *` | ✅ |

### Annual (January 2nd, 9:00 AM EAT)
| Task | Cron | Active |
|------|------|--------|
| `annual_sales_summary` | `0 9 2 1 *` | ✅ |
| `annual_production_summary` | `0 9 2 1 *` | ✅ |
| `annual_inventory_summary` | `0 9 2 1 *` | ✅ |
| `annual_profit_loss` | `0 9 2 1 *` | ✅ |
| `annual_payroll_summary` | `0 9 2 1 *` | ✅ |

## 10.4 Django-Q2 Configuration

```python
# settings.py
Q_CLUSTER = {
    'name': 'chesanto',
    'orm': 'default',      # Uses PostgreSQL
    'timeout': 300,        # 5 min max per task
    'retry': 600,          # Retry after 10 min
    'save_limit': 500,     # Keep last 500 task results
    'ack_failures': True,  # Log failed tasks
}
```

```
# Procfile (Railway)
web: gunicorn config.wsgi
worker: python manage.py qcluster
```

---

# 11. STARTING PROMPT FOR NEW CHAT

## 11.1 Recommended Starting Prompt

Copy and paste this prompt to start the new chat session:

```
I'm continuing work on the Chesanto Bakery Management System - a Django 5.2.7 multi-app monolith for a Kenyan bakery.

## CONTEXT
The foundation apps (Accounts, Inventory, Production, Sales) are COMPLETE and TESTED. All follow the "Bank Ledger" model - immutable records, ACID transactions, positive values only.

Now I need to implement the Reports & Analytics apps.

## KEY DECISIONS (FINALIZED)
1. **Access Control:** All report routes require ACCOUNTANT role or higher
2. **Report Frequency:** Sales, Production, Inventory, P&L → Daily/Weekly/Monthly/Annual
3. **Payroll Reports:** Monthly and Annual only
4. **Email Capability:** ALL reports and analytics views can be emailed from frontend
5. **Task Functions:** Backend scheduled jobs (26 total), NOT viewable on frontend
6. **Scheduling:** Django-Q2 with PostgreSQL as broker

## COMPREHENSIVE DOCUMENTS
Please read these planning documents:
- **Docs/REPORTS_ANALYTICS_WORKFLOWS.MD** - Tech spec (2200+ lines)
- **Docs/REPORTS_ANALYTICS_PLANNING.md** - Planning decisions

## APPROACH
Use the same workflow-first refactoring method as the foundation apps:
1. Define workflows first
2. Design/refactor models based on workflows
3. Create reusable service functions
4. Build views incrementally
5. Test each feature before moving to next

## FIRST TASK
Start with Phase 0: Add MiscExpenseCategory and MiscExpenseRecord models to apps/payroll/models.py
```

## 11.2 Key Context Points for New Chat

### Access Control
- **All report routes require ACCOUNTANT role or higher**
- Roles with access: SUPERADMIN, ADMIN, ACCOUNTANT
- All others redirected to main dashboard

### Technical Reminders
- **Timezone:** `Africa/Nairobi`, `USE_TZ = True`
- **Currency:** KES (Kenyan Shillings), format as `KES X,XXX.XX`
- **Immutability:** All Purchase, Output, Batch, Dispatch, Return records are CREATE-ONLY
- **Inventory:** 23 items with per-item tables, access via `get_details_model(item_id)`
- **User Roles:** SUPERADMIN, ADMIN, ACCOUNTANT, SALESMAN, PRODUCTION_MANAGER

### Report Frequencies (FINALIZED)
| Report | Daily | Weekly | Monthly | Annual |
|--------|:-----:|:------:|:-------:|:------:|
| Sales | ✅ | ✅ | ✅ | ✅ |
| Production | ✅ | ✅ | ✅ | ✅ |
| Inventory | ✅ | ✅ | ✅ | ✅ |
| P&L | ✅ | ✅ | ✅ | ✅ |
| Payroll | ❌ | ❌ | ✅ | ✅ |

### Email from Frontend
- ALL reports can be emailed via frontend button
- Pre-fills current user's email
- Allows adding additional recipients
- Sends HTML + CSV attachment
- Logs to audit trail

### Model Key Points
- `SalesReturn.total_revenue` = actual revenue from sold items
- `SalesReturn.commission_amount` = manually entered by Accountant
- `ProductionBatch.mix_snapshot` = JSONField with frozen recipe
- `ProductionBatch.total_ingredient_cost` = calculated at batch time
- `ProductStock.current_stock` = finished goods, updated by Production/Sales

### Styling Key Points
- Blue gradient headers: `linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)`
- Stats bars with colored values (success=green, warning=amber, danger=red)
- Tables with hover states and uppercase headers
- Buttons with gradient backgrounds

### Chart.js Key Points
- Use CDN: `https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js`
- Pass data as JSON via `{{ data_json|safe }}`
- Use `DecimalEncoder` for Decimal → float conversion

## 11.3 Files Already Created/Modified

| File | Status | Lines |
|------|--------|-------|
| `apps/accounts/models.py` | ✅ Complete | 455 |
| `apps/products/models.py` | ✅ Complete | 271 |
| `apps/inventory/routing.py` | ✅ Complete | 250 |
| `apps/inventory/utils.py` | ✅ Complete | 614 |
| `apps/production/models.py` | ✅ Complete | 288 |
| `apps/sales/models.py` | ✅ Complete | 408 |
| `apps/sales/views.py` | ✅ Complete | 600+ |
| `apps/reports/models.py` | ⚠️ Needs refactor | 250 |
| `apps/reports/views.py` | ❌ Empty | - |
| `apps/analytics/views.py` | ⚠️ Disabled | 200 |
| `Docs/SALES_APP_WORKFLOWS.md` | ✅ Complete | 2172 |
| `Docs/REPORTS_ANALYTICS_PLANNING.md` | ✅ This doc | 2000+ |

## 11.4 Success Criteria for Reports & Analytics

### Reports App Done When:
- [ ] Daily, Weekly, Monthly reports generate correctly
- [ ] Reports show product, salesperson, inventory breakdowns
- [ ] Reports can be exported to CSV
- [ ] Report list with filtering works
- [ ] Custom date range reports work

### Analytics App Done When:
- [ ] Executive dashboard with live KPIs works
- [ ] Sales analytics with charts works
- [ ] Production analytics works
- [ ] Inventory analytics works
- [ ] All charts render correctly on mobile
- [ ] Data matches manual calculations

---

# APPENDIX: SUMMARY TABLES

## A.1 Data Sources Quick Reference

### Analytics App Routes (`/analytics/`) - Existing

| URL | View Name | Purpose | Access | Email |
|-----|-----------|---------|--------|-------|
| `/analytics/dashboard/` | `dashboard_view` | Real-time KPIs (8 charts) | ACCOUNTANT+ | ✅ |
| `/analytics/products/` | `product_performance_view` | Live product metrics | ACCOUNTANT+ | ✅ |
| `/analytics/inventory/` | `inventory_status_view` | Current stock levels | ACCOUNTANT+ | ✅ |
| `/analytics/sales/` | `sales_trends_view` | Sales trends | ACCOUNTANT+ | ✅ |
| `/analytics/deficits/` | `deficit_analysis_view` | Deficit patterns | ACCOUNTANT+ | ✅ |

**Total Analytics Routes: 5** | **Email-capable: 5**

| Data Point | Source Model | Key Fields |
|------------|--------------|------------|
| Daily Revenue | `SalesReturn` | `return_date`, `total_revenue` |
| Units Sold | `SalesReturnItem` | `qty_sold` |
| Salesperson | `SalesReturn.dispatch.salesperson` | User FK |
| Commission | `SalesReturn` | `commission_amount` |
| Production Output | `ProductionBatch` | `production_date`, `quantity_produced` |
| Production Cost | `ProductionBatch` | `total_ingredient_cost` |
| Stock Levels | `ItemXXDetails` | `current_stock`, `minimum_stock_level` |
| Purchases | `ItemXXPurchases` | `purchase_date`, `quantity_purchased`, `unit_price` |
| Crates Out | `SalesDispatch` | `crates_dispatched` |
| Crates Lost | `SalesReturn` | `crates_lost`, `crates_damaged` |

## A.2 Analytics Categories

| Category | Priority | Charts |
|----------|----------|--------|
| Revenue Tracking | P0 | Line (trend), Bar (by product) |
| Salesperson Performance | P0 | Horizontal Bar (leaderboard) |
| Product Mix | P1 | Doughnut/Pie |
| Production Output | P1 | Bar (daily output) |
| Crate Accountability | P1 | Stacked Bar |
| Stock Levels | P2 | Horizontal Bar with min lines |
| Price Trends | P2 | Multi-line |
| Profitability | P2 | Dual-axis (revenue vs cost) |

## A.3 Report Types

| Report | Period | Key Metrics |
|--------|--------|-------------|
| Daily | 1 day | Revenue, units, batches, alerts |
| Weekly | 7 days | Totals, averages, trends |
| Monthly | ~30 days | Full P&L, salesperson rankings |
| Custom | Any range | User-defined analysis |

---

**Document Complete**



Weekly, Monthly, and Annual Schedules 
Schedules Created
Schedule	Time	Cron	Reports
Morning	6:00 AM daily	0 6 * * *	13 reports (daily ops + conditional weekly/monthly/annual)
Weekly	7:00 AM Monday	0 7 * * 1	4 reports
Monthly	7:00 AM 1st	0 7 1 * *	6 reports
Annual	8:00 AM Jan 1	0 8 1 1 *	2 reports
Evening	10:00 PM daily	0 22 * * *	8 reports
Reports by Schedule
Weekly Report (Mondays):

Weekly P&L Summary
Weekly Sales Summary
Weekly Production
Stock Movement (7 days)
Monthly Report (1st of month):

Monthly P&L Summary
Monthly Sales Summary
Monthly Production
Commission Report
Monthly Payroll
Inventory Valuation
Annual Report (January 1st):

Annual P&L Summary
Annual Payroll
Files Modified
models.py - Extended ReportSchedule with day_of_week, day_of_month, month fields and cron_expression property
tasks.py - Added send_weekly_report(), send_monthly_report(), send_annual_report() functions
setup_report_schedules.py - Updated to register all 5 schedules with Django-Q
To Start the Scheduler
