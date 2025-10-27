# Milestone 2: Core Business Operations (Iteration 2)
**Project:** Chesanto Bakery Management System  
**Status:** 📋 Planning Phase - Revised  
**Date:** October 24, 2025

---

## Overview

Replicate Excel-based operations with automation, background processes, and alerts to minimize overhead and maximize accuracy. **All features accessible via navigation bar (no hidden menus).**

**Key Principles:**
- ✅ **Single Source of Truth**: Accountant/Operations Manager (data entry only)
- ✅ **Zero Manual Error Checking**: System automates deficits, overstocks, unsubmitted work
- ✅ **Immediate Critical Alerts**: Email/SMS notifications for urgent issues
- ✅ **Store Reports in Database**: Generate once, view many times (performance + accountability)
- ✅ **Automated Decline/Notifications**: No manual combing for errors

**User Roles:**
- **Accountant/Operations Manager** = Data entry (mixes, cash at hand, invoices)
- **Product Managers** = Optional product-specific entry
- **CEO + Developer** = Supervisors (full access to all reports, can override closed books)

---

## App Structure

### Primary Apps (Navigation Bar)
1. **Products** - Product catalog, mixes, aliases
2. **Inventory** - Ingredients, restocking, direct/indirect costs
3. **Production** - Daily batches, opening/closing stock
4. **Sales** - Dispatch, returns, deficit tracking
5. **Accounting** - Invoices, P&L per mix, financials
6. **Reports** - Daily/Weekly/Monthly (stored in DB)
7. **Analytics** - Graphical dashboard (minimal text)
8. **Payroll** - Connected to Accounting + Accounts

---

## Terminology & Aliases

### Product Naming
- **KDF**: 
  - Base unit: **Pieces/Units** (hand-cut, variable output)
  - Packaging: **12 pieces = 1 packet (dozen)**
  - Baseline: 100 units → Range: 98-105 units
- **Bread**: 
  - Base unit: **Loaves** (machine-weighed, fixed output)
  - Packaging: **1 loaf = 1 packet**
- **Scones**: 
  - Base unit: **Pieces** (machine-weighed, fixed output)
  - Packaging: **12 pieces = 1 packet (dozen)**

### Currency
- **Default**: Kenyan Shillings (KES) for all financial fields

---

## Data Flow & Dependencies

### App Relationships
```
┌─────────────────────────────────────────────────────────────┐
│                      INVENTORY (Foundation)                  │
│                    Ingredients + Stock Levels                │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  ├──→ PRODUCTS (Depends on Inventory)
                  │    Mixes → Ingredients → Inventory
                  │
                  └──→ PRODUCTION (Depends on Inventory)
                       Uses ingredients, tracks output
                       │
                       ├──→ SALES (Depends on Production)
                       │    Expected Sales = Production × Price
                       │    Actual Sales = Dispatch - Returns
                       │
                       └──→ ACCOUNTING (Depends on Production + Sales)
                            P&L per mix, Invoices, Financials
                            │
                            ├──→ REPORTS (Pulls from ALL apps)
                            │    Daily/Weekly/Monthly summaries
                            │
                            ├──→ ANALYTICS (Pulls from ALL apps)
                            │    Graphical insights
                            │
                            └──→ PAYROLL (Connected to Accounting + Accounts)
                                 Employee compensation
```

---

## 1. Products App

### Purpose
Product catalog with aliases, mixes, and ingredient recipes

### Key Features
- Product aliases (KDF pieces, Bread loaves, Scone pieces)
- Mix recipes (adjustable - add/remove ingredients)
- Expected packet yields per mix
- Variable vs fixed output tracking

### Data Models

```python
# products/models.py

class Product(models.Model):
    """Main product catalog with aliases"""
    name = models.CharField(max_length=100)  # KDF, Bread, Scones
    alias = models.CharField(max_length=100, blank=True)  # "Pieces", "Loaves", "Pieces"
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Output characteristics
    has_variable_output = models.BooleanField(default=False)  # KDF=True, others=False
    baseline_output = models.IntegerField(help_text="Expected units per mix")
    min_output = models.IntegerField(null=True, blank=True)  # KDF: 98
    max_output = models.IntegerField(null=True, blank=True)  # KDF: 105
    
    # Packaging
    units_per_packet = models.IntegerField(default=1)  # Bread=1, KDF=12, Scones=12
    packet_label = models.CharField(max_length=50, default="packet")  # "dozen", "loaf", "packet"
    
    # Pricing (KES)
    price_per_packet = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='products_created')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='products_updated')


class Ingredient(models.Model):
    """Master ingredients table - used in mixes"""
    name = models.CharField(max_length=200)  # Wheat Flour, Yeast, Sugar, etc.
    description = models.TextField(blank=True)
    default_unit = models.CharField(max_length=20, choices=[
        ('g', 'Grams'),
        ('kg', 'Kilograms'),
        ('ml', 'Milliliters'),
        ('l', 'Liters'),
        ('pcs', 'Pieces'),
    ])
    
    # Link to inventory
    inventory_item = models.ForeignKey('inventory.InventoryItem', on_delete=models.PROTECT)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ingredients_created')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ingredients_updated')


class Mix(models.Model):
    """Recipe for each product - adjustable ingredient list"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='mixes')
    name = models.CharField(max_length=200)  # "Standard Bread Mix"
    version = models.IntegerField(default=1)  # Track recipe changes
    is_active = models.BooleanField(default=True)
    
    # Expected yield
    expected_packets = models.IntegerField(help_text="How many packets this mix produces")
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='mixes_created')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='mixes_updated')


class MixIngredient(models.Model):
    """Individual ingredients in a mix - ADD/REMOVE capability"""
    mix = models.ForeignKey(Mix, on_delete=models.CASCADE, related_name='ingredients')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)  # Support grams
    unit = models.CharField(max_length=20, choices=[
        ('g', 'Grams'),
        ('kg', 'Kilograms'),
        ('ml', 'Milliliters'),
        ('l', 'Liters'),
        ('pcs', 'Pieces'),
    ])
    
    # Metadata
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

### Inputs/Outputs

**INPUTS:**
- ✏️ **Manual**: Product name, alias, pricing, mix recipes, ingredient quantities
- 🤖 **Automated**: Ingredient costs (from Inventory), expected yields (from mix)

**PROCESSING:**
- Calculate cost per packet based on ingredient costs
- Validate ingredient availability before allowing production

**OUTPUTS:**
- Product catalog with aliases
- Mix recipes for production
- Expected packet yields
- Cost per packet (for Accounting)

---

## 2. Inventory App

### Purpose
Track all raw materials (ingredients), restocking, and direct/indirect costs

### Key Features
- **Full ingredients list** (comprehensive master data)
- **Restocking option** (add stock levels manually)
- **Reorder level triggers** (default + custom adjustable)
- **Automatic deduction** when production happens
- **Audit trail** for all stock movements

### Data Models

```python
# inventory/models.py

class InventoryCategory(models.Model):
    """Direct vs Indirect costs"""
    DIRECT = 'DIRECT'
    INDIRECT = 'INDIRECT'
    
    CATEGORY_CHOICES = [
        (DIRECT, 'Direct Cost (Ingredients)'),
        (INDIRECT, 'Indirect Cost (Fuel, Packaging, etc.)'),
    ]
    
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)


class InventoryItem(models.Model):
    """Raw materials and supplies - FULL INGREDIENTS LIST"""
    name = models.CharField(max_length=200)  # "Wheat Flour", "Diesel", "Bread Bags"
    category = models.ForeignKey(InventoryCategory, on_delete=models.PROTECT)
    
    # Stock tracking
    current_stock = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Reorder levels - DEFAULT + CUSTOM
    default_reorder_level = models.DecimalField(max_digits=10, decimal_places=3, default=10)
    custom_reorder_level = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    
    @property
    def reorder_level(self):
        """Use custom if set, otherwise default"""
        return self.custom_reorder_level if self.custom_reorder_level else self.default_reorder_level
    
    unit = models.CharField(max_length=20)  # kg, liters, pieces, etc.
    
    # Pricing (KES)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Alerts
    alert_enabled = models.BooleanField(default=True)
    alert_recipients = models.ManyToManyField(User, related_name='inventory_alerts')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_items_created')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_items_updated')


class StockMovement(models.Model):
    """Track all inventory changes - AUDIT TRAIL"""
    PURCHASE = 'PURCHASE'
    RESTOCK = 'RESTOCK'  # Manual addition
    PRODUCTION_USE = 'PRODUCTION_USE'  # Auto-deducted
    ADJUSTMENT = 'ADJUSTMENT'
    DAMAGE = 'DAMAGE'
    
    MOVEMENT_TYPES = [
        (PURCHASE, 'Purchase/Supplier Delivery'),
        (RESTOCK, 'Manual Restocking'),
        (PRODUCTION_USE, 'Used in Production'),
        (ADJUSTMENT, 'Manual Adjustment'),
        (DAMAGE, 'Damaged/Spoiled'),
    ]
    
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Before/After for audit
    stock_before = models.DecimalField(max_digits=10, decimal_places=3)
    stock_after = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Cost tracking (KES)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Link to production if applicable
    production_batch = models.ForeignKey('production.ProductionBatch', null=True, blank=True, on_delete=models.SET_NULL)


class Crate(models.Model):
    """Track crates used for dispatch"""
    total_crates = models.IntegerField(default=0)
    available_crates = models.IntegerField(default=0)
    dispatched_crates = models.IntegerField(default=0)
    damaged_crates = models.IntegerField(default=0)
    
    last_updated = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

### Inputs/Outputs

**INPUTS:**
- ✏️ **Manual**: Initial stock levels, restocking (adding inventory), custom reorder levels, cost per unit
- 🤖 **Automated**: Stock deductions (when production uses ingredients), low stock alerts

**PROCESSING:**
- Calculate total inventory value (stock × cost per unit)
- Monitor reorder levels (default or custom)
- Auto-trigger alerts when stock < reorder level
- Create audit trail for all movements

**OUTPUTS:**
- Current stock levels
- Low stock alerts (to Accountant, Inventory Manager)
- Inventory valuation
- Stock movement history (audit trail)

---

## 3. Production App

### Purpose
Track daily production batches, opening/closing stock, and cost per mix

### Data Models

```python
# production/models.py

class ProductionBatch(models.Model):
    """Daily production run for a product"""
    date = models.DateField(default=timezone.now)
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    mix = models.ForeignKey('products.Mix', on_delete=models.PROTECT)
    
    # Quantities
    mixes_produced = models.IntegerField(help_text="Number of mix batches made")
    units_produced = models.IntegerField(help_text="Actual units produced (KDF pieces, Bread loaves)")
    packets_produced = models.IntegerField(help_text="Actual packets produced")
    expected_packets = models.IntegerField(help_text="Expected based on mix recipe")
    
    # Variance (for KDF)
    variance = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Costs (auto-calculated in KES)
    direct_cost = models.DecimalField(max_digits=12, decimal_places=2)  # Ingredients
    indirect_cost = models.DecimalField(max_digits=12, decimal_places=2)  # Fuel, packaging
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    cost_per_packet = models.DecimalField(max_digits=10, decimal_places=2)
    
    # P&L per mix (for CEO)
    revenue_if_sold = models.DecimalField(max_digits=12, decimal_places=2)  # packets × price
    profit_per_mix = models.DecimalField(max_digits=12, decimal_places=2)  # revenue - total_cost
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2)  # percentage
    
    # Metadata
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='batches_recorded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='batches_updated')
    
    # Status
    is_finalized = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date', 'product']),
        ]


class DailyProduction(models.Model):
    """Summary of all production for a day"""
    date = models.DateField(unique=True)
    
    # Opening stock (from previous day's closing)
    opening_stock = models.JSONField(default=dict)  # {product_id: packets}
    
    # Production totals
    total_packets_produced = models.IntegerField(default=0)
    total_direct_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_indirect_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_production_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Closing stock
    closing_stock = models.JSONField(default=dict)  # {product_id: packets}
    
    # Book closing
    is_closed = models.BooleanField(default=False)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='production_closed')
    closed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='production_updated')
```

### Inputs/Outputs

**INPUTS:**
- ✏️ **Manual**: Mixes produced, actual units/packets produced (hand-count for KDF)
- 🤖 **Automated**: Opening stock (from previous day's closing), ingredient costs (from Inventory), expected yields (from Mix)

**PROCESSING:**
- Auto-deduct ingredients from inventory when batch created
- Calculate direct costs (ingredient usage × cost per unit)
- Calculate indirect costs (fuel, packaging allocation)
- Calculate cost per packet
- Calculate P&L per mix (revenue_if_sold - total_cost)
- Track variance for KDF (actual vs expected)
- Update opening/closing stock

**OUTPUTS:**
- Production batches with costs
- P&L per mix (for CEO)
- Opening/closing stock daily
- Ingredient usage report
- Available packets for dispatch

---

## 4. Sales App

### Purpose
Track dispatch, returns, deficits, and actual vs expected sales

### Key Features
- **Strong foreign keys**: Dispatch → Returns (one-to-one relationship)
- **Permission inheritance**: Salesmen can file returns, Accountant can override
- **Expected sales** = Production × Price (automated)
- **Actual sales** = Dispatch - Returns (manual entry)
- **Deficit tracking** = Expected - Actual (automated alert)

### Data Models

```python
# sales/models.py

class Salesperson(models.Model):
    """Salesmen and school accounts"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=200)
    
    SALESMAN = 'SALESMAN'
    SCHOOL = 'SCHOOL'
    
    TYPE_CHOICES = [
        (SALESMAN, 'Salesman'),
        (SCHOOL, 'School Account'),
    ]
    
    salesperson_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Percentage
    
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='salespeople_created')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='salespeople_updated')


class Dispatch(models.Model):
    """Daily dispatch to salesmen/schools - STRONG FK"""
    date = models.DateField(default=timezone.now)
    salesperson = models.ForeignKey(Salesperson, on_delete=models.PROTECT)
    
    # What went out
    crates_dispatched = models.IntegerField()
    
    # Status
    is_returned = models.BooleanField(default=False)
    
    # Metadata
    dispatched_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='dispatches_made')
    dispatched_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='dispatches_updated')
    
    class Meta:
        ordering = ['-date']


class DispatchItem(models.Model):
    """Products in each dispatch"""
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    packets_dispatched = models.IntegerField()
    expected_revenue = models.DecimalField(max_digits=12, decimal_places=2)  # packets × price (KES)


class SalesReturn(models.Model):
    """What came back from dispatch - STRONG FK to Dispatch"""
    dispatch = models.OneToOneField(Dispatch, on_delete=models.CASCADE, related_name='returns')
    
    # Returns
    crates_returned = models.IntegerField()
    crates_deficit = models.IntegerField(default=0)  # dispatched - returned (AUTO-CALCULATED)
    
    # Money (KES)
    cash_returned = models.DecimalField(max_digits=12, decimal_places=2)
    commission_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_revenue = models.DecimalField(max_digits=12, decimal_places=2)  # cash - commission (AUTO-CALCULATED)
    
    # Discrepancies (AUTO-CALCULATED)
    revenue_deficit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    
    # Metadata - Salesmen can file, Accountant can override
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='returns_recorded')
    recorded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='returns_updated')


class SalesReturnItem(models.Model):
    """Unsold products returned"""
    sales_return = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    packets_returned = models.IntegerField()
    packets_sold = models.IntegerField()  # dispatched - returned (AUTO-CALCULATED)


class DailySales(models.Model):
    """Summary of all sales for a day"""
    date = models.DateField(unique=True)
    
    # Dispatch totals (KES)
    total_dispatched_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_crates_dispatched = models.IntegerField(default=0)
    
    # Returns totals (KES)
    total_actual_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_crates_returned = models.IntegerField(default=0)
    
    # Deficits (AUTO-CALCULATED, IMMEDIATE ALERT)
    revenue_deficit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    crate_deficit = models.IntegerField(default=0)
    
    # Book closing
    is_closed = models.BooleanField(default=False)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_closed')
    closed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales_updated')
```

### Inputs/Outputs

**INPUTS:**
- ✏️ **Manual**: Dispatch records (salesperson, crates, products), Return data (crates returned, cash returned)
- 🤖 **Automated**: Expected revenue (packets × price), Deficits (dispatched - returned), Commission calculations

**PROCESSING:**
- Calculate expected revenue per dispatch
- Calculate actual revenue (cash - commission)
- Calculate deficits (crates, revenue)
- **IMMEDIATE ALERT** if deficit detected
- Update available stock (add returns back)
- Track salesperson performance

**OUTPUTS:**
- Dispatch records
- Sales returns
- **Deficit alerts** (to Accountant, CEO)
- Actual vs Expected sales comparison
- Salesperson performance data

---

## 5. Accounting App (NEW)

### Purpose
Invoices, P&L per mix, financial summaries, connected to Payroll

### Key Features
- **Invoice generation** (manual entry by Accountant)
- **P&L per mix** (auto-calculated from Production)
- **P&L percentages and margins** (for Analytics)
- **Connected to Payroll** (expense tracking)

### Data Models

```python
# accounting/models.py

class Invoice(models.Model):
    """Customer invoices - manual entry"""
    invoice_number = models.CharField(max_length=50, unique=True)
    date = models.DateField(default=timezone.now)
    customer_name = models.CharField(max_length=200)
    
    # Link to dispatch or manual entry
    dispatch = models.ForeignKey('sales.Dispatch', null=True, blank=True, on_delete=models.SET_NULL)
    
    # Amounts (KES)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payment
    paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='invoices_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='invoices_updated')


class InvoiceItem(models.Model):
    """Line items in invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)


class MixProfitLoss(models.Model):
    """P&L analysis per mix - auto-generated daily"""
    date = models.DateField()
    mix = models.ForeignKey('products.Mix', on_delete=models.CASCADE)
    
    # Production
    batches_produced = models.IntegerField()
    packets_produced = models.IntegerField()
    
    # Costs (KES)
    total_direct_cost = models.DecimalField(max_digits=12, decimal_places=2)
    total_indirect_cost = models.DecimalField(max_digits=12, decimal_places=2)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Revenue (KES)
    expected_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    actual_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Profit (KES)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2)  # revenue - total_cost
    gross_margin = models.DecimalField(max_digits=5, decimal_places=2)  # percentage
    
    generated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['date', 'mix']
```

### Inputs/Outputs

**INPUTS:**
- ✏️ **Manual**: Invoice details (customer, items, amounts)
- 🤖 **Automated**: P&L per mix (from Production batches), Revenue data (from Sales), Cost data (from Production)

**PROCESSING:**
- Generate invoices with unique numbers
- Calculate P&L per mix daily
- Calculate profit margins and percentages
- Track payment status

**OUTPUTS:**
- Invoices (PDF/HTML export)
- P&L per mix report (for CEO)
- Financial summaries
- Data for Payroll integration

---

## 6. Reports App

### Purpose
Daily, Weekly, Monthly reports - **stored in database**, same template structure

### Key Features
- **3 time periods**: Daily, Weekly, Monthly
- **Same template structure** (only period changes)
- **Stored in database** (generate once, view many times)
- **Backed up and tracked** (audit trail)
- **HTML export** (not PDF - easier for email/display)

### Report Schedule
- **Daily**: Auto-generate at **9:00 PM** (3-hour grace period after 6 PM close)
  - Books closed at 9 PM → Accountant cannot edit after
  - Only CEO, Developer, Superadmins can adjust
- **Weekly**: Auto-generate **Sunday 8:00 AM**
- **Monthly**: Auto-generate **1st of every month at 12:00 AM**

### Data Models

```python
# reports/models.py

class DailyReport(models.Model):
    """Comprehensive daily summary - STORED IN DATABASE"""
    date = models.DateField(unique=True)
    
    # Production summary
    production_summary = models.JSONField(default=dict)
    # {product_id: {batches, packets, direct_cost, indirect_cost, total_cost}}
    
    # Sales summary
    sales_summary = models.JSONField(default=dict)
    # {salesperson_id: {dispatched, returned, revenue, commission, deficit}}
    
    # Stock summary
    opening_stock = models.JSONField(default=dict)  # {product_id: packets}
    closing_stock = models.JSONField(default=dict)  # {product_id: packets}
    
    # Financials (KES)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    total_costs = models.DecimalField(max_digits=12, decimal_places=2)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2)  # percentage
    
    # Deficits
    revenue_deficit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    crate_deficit = models.IntegerField(default=0)
    
    # Report metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    is_finalized = models.BooleanField(default=False)
    html_content = models.TextField(blank=True)  # Store rendered HTML
    
    class Meta:
        ordering = ['-date']


class WeeklyReport(models.Model):
    """Aggregate of 6 daily reports (Mon-Sat) - STORED IN DATABASE"""
    week_start = models.DateField()
    week_end = models.DateField()
    
    # Aggregated data
    total_production = models.JSONField(default=dict)
    total_sales = models.JSONField(default=dict)
    
    # Financials (KES)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    total_costs = models.DecimalField(max_digits=12, decimal_places=2)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Deficits
    total_revenue_deficit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_crate_deficit = models.IntegerField(default=0)
    
    # Report metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    html_content = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['week_start', 'week_end']
        ordering = ['-week_start']


class MonthlyReport(models.Model):
    """Aggregate of all weeks in a month - STORED IN DATABASE"""
    month = models.DateField()  # First day of month
    
    # Aggregated data
    total_production = models.JSONField(default=dict)
    total_sales = models.JSONField(default=dict)
    
    # Financials (KES)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    total_costs = models.DecimalField(max_digits=12, decimal_places=2)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Trends
    best_selling_product = models.CharField(max_length=100)
    worst_performing_day = models.DateField()
    best_salesperson = models.CharField(max_length=200)
    
    # Deficits
    total_revenue_deficit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_crate_deficit = models.IntegerField(default=0)
    
    # Report metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    html_content = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-month']


class ReportRecipient(models.Model):
    """Who receives which reports"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Report types
    receives_daily = models.BooleanField(default=False)
    receives_weekly = models.BooleanField(default=False)
    receives_monthly = models.BooleanField(default=False)
    
    # CEO and Developer get ALL reports by default
```

### Report Template Structure

All reports share the same HTML structure:

```html
<!DOCTYPE html>
<html>
<head>
    <title>{{ report_type }} Report - {{ period }}</title>
    <style>/* Same styling for all reports */</style>
</head>
<body>
    <h1>{{ report_type }} Report</h1>
    <p>Period: {{ period }}</p>
    
    <!-- A. Production Section -->
    <section>
        <h2>Production</h2>
        <!-- Direct costs, indirect costs, packets produced -->
    </section>
    
    <!-- B. Dispatch Section -->
    <section>
        <h2>Dispatch & Returns</h2>
        <!-- Products/crates dispatched and returned -->
    </section>
    
    <!-- C. Sales Section -->
    <section>
        <h2>Sales</h2>
        <!-- Expected vs Actual, variance, commission -->
    </section>
    
    <!-- D. Closing Stock -->
    <section>
        <h2>Stock Movement</h2>
        <!-- Opening, production, sales, returns, closing -->
    </section>
    
    <!-- E. Profit & Loss -->
    <section>
        <h2>Profit & Loss</h2>
        <!-- Revenue, costs, gross/net profit, margins -->
    </section>
    
    <!-- F. Deficits (if any) -->
    <section class="alert">
        <h2>Deficits</h2>
        <!-- Revenue/crate deficits with alerts -->
    </section>
</body>
</html>
```

### Inputs/Outputs

**INPUTS:**
- 🤖 **Automated**: All data from Production, Sales, Accounting apps

**PROCESSING:**
- Auto-generate reports at scheduled times
- Store HTML content in database
- Calculate aggregates for weekly/monthly
- Identify trends and anomalies

**OUTPUTS:**
- Daily reports (stored, viewable, emailable)
- Weekly reports (stored, viewable, emailable)
- Monthly reports (stored, viewable, emailable)
- **CEO + Developer get ALL reports**

---

## 7. Analytics App

### Purpose
Graphical dashboard with minimal text - CEO insights

### Key Features
- **Real-time dashboard**
- **Actual profit/loss** with percentages
- **Profit margins** visualized
- **Contextual colors**: Red (loss/deficit), Green (profit/success), Blue (neutral)
- **Animations** for visual appeal

### Charts & Metrics

1. **Inventory Levels** (Bar chart)
   - Current stock vs reorder level
   - Color: Red (below reorder), Green (above)

2. **Production Trends** (Line graph)
   - Daily packets produced over time
   - Overlay expected vs actual

3. **Expected vs Actual Sales** (Comparison chart)
   - Side-by-side bars
   - Show variance percentage

4. **Profit Margins** (Pie chart)
   - Revenue breakdown by product
   - Show profit margin per product

5. **Deficits Tracking** (Trend line)
   - Revenue deficits over time
   - Crate deficits over time

6. **Best/Worst Performers**
   - Products (by profit)
   - Salespeople (by revenue)

### Charting Library
**Recommendation**: **Chart.js** (free, Python/Django compatible)
- ✅ Free and open-source
- ✅ Visually appealing with animations
- ✅ Contextual colors supported
- ✅ Responsive and interactive
- ✅ Easy Django integration via `django-chartjs`

**Alternative**: **Plotly** (more advanced, also free)

### Inputs/Outputs

**INPUTS:**
- 🤖 **Automated**: All data from Reports, Production, Sales, Inventory

**PROCESSING:**
- Generate charts from stored reports
- Calculate KPIs (profit margins, trends)
- Identify anomalies

**OUTPUTS:**
- Interactive dashboard
- Graphical insights (minimal text)
- Export charts as images

---

## 8. Payroll App

### Purpose
Employee compensation connected to Accounting and Accounts

### Key Features
- **Connected to Accounting** (expense tracking)
- **Connected to Accounts** (user/employee data)
- Salary calculations
- Deductions (loans, advances, taxes)
- Payslip generation

*(Details to be expanded in separate iteration)*

---

## Automation & Scheduling

### Timer-Based Automation (No Celery!)

**Why avoid Celery?**
- Added complexity (Redis broker, worker processes)
- Session timeout already works with timers (1-hour cookie)
- Can use Django signals + scheduled management commands

**Alternative Approach:**

1. **Django Management Commands** (run via cron or Railway scheduled tasks)
   ```python
   # management/commands/close_daily_books.py
   python manage.py close_daily_books  # Runs at 9:00 PM
   python manage.py generate_weekly_report  # Runs Sunday 8:00 AM
   python manage.py generate_monthly_report  # Runs 1st of month
   ```

2. **Railway Cron Jobs** (built-in, no Celery needed)
   ```toml
   # railway.toml
   [cron.close_books]
   schedule = "0 21 * * *"  # 9:00 PM daily
   command = "python manage.py close_daily_books"
   
   [cron.weekly_report]
   schedule = "0 8 * * 0"  # 8:00 AM Sunday
   command = "python manage.py generate_weekly_report"
   
   [cron.monthly_report]
   schedule = "0 0 1 * *"  # 12:00 AM 1st of month
   command = "python manage.py generate_monthly_report"
   ```

3. **Django Signals** (immediate alerts)
   ```python
   # When SalesReturn is saved, check for deficits
   @receiver(post_save, sender=SalesReturn)
   def check_deficit(sender, instance, **kwargs):
       if instance.revenue_deficit > 0 or instance.crates_deficit > 0:
           send_immediate_alert(instance)  # Email/SMS to CEO, Accountant
   ```

### Automated Tasks

1. ✅ **Close Daily Books**: 9:00 PM (lock edits, generate report)
2. ✅ **Generate Weekly Report**: Sunday 8:00 AM
3. ✅ **Generate Monthly Report**: 1st of month 12:00 AM
4. ✅ **Low Stock Alerts**: Check on every stock movement (signal)
5. ✅ **Deficit Alerts**: Immediate (signal on SalesReturn save)
6. ✅ **Inventory Deduction**: Immediate (signal on ProductionBatch save)

---

## Answers to Clarification Questions

### 1. Indirect Costs Allocation
**Decision**: **Per day** (not per batch)
- Fuel, packaging, transport are daily overheads
- Allocate proportionally across all batches produced that day

### 2. Commission
**Decision**: **Variable per salesman**
- Each salesperson has a `commission_rate` field (percentage)
- Can be 0% for schools, 5-10% for salesmen

### 3. Deficits Handling
**Decision**: **Flag + Immediate Alert**
- System calculates deficit automatically
- **Immediate email/SMS alert** to Accountant and CEO
- Logged in daily report
- No automatic deductions (requires manual investigation)

### 4. Schools vs Salesmen
**Decision**: **Same workflow, different commission**
- Schools: commission_rate = 0%, possible credit terms
- Salesmen: commission_rate > 0%, daily cash payment
- Both use same Dispatch/Return models

### 5. Pricing Changes
**Decision**: **Locked at day start**
- Product prices set at midnight (or before first dispatch)
- Cannot change mid-day to avoid discrepancies
- Price changes take effect next day

### 6. Returns Handling
**Decision**: **Add back to stock**
- Returned packets added to closing stock
- Available for next day's opening stock
- Track if returned items are damaged (separate field)

### 7. Crate Damage
**Decision**: **Separate damage tracking**
- `Crate` model has `damaged_crates` field
- If crate not returned and not in deficit, mark as damaged
- Accountant can manually adjust crate count

---

## Implementation Summary

### Phase 1: Foundation (Week 1-2)
- ✅ Products app (aliases, ingredients, mixes)
- ✅ Inventory app (full ingredients list, restocking)
- ✅ Basic forms with manual/auto input labels

### Phase 2: Core Operations (Week 3-4)
- ✅ Production app (batches, P&L per mix)
- ✅ Sales app (dispatch, returns, deficits)
- ✅ Accounting app (invoices, financials)

### Phase 3: Reports & Analytics (Week 5-6)
- ✅ Reports app (daily/weekly/monthly, stored in DB)
- ✅ Analytics app (Chart.js dashboard)
- ✅ Scheduled tasks (Railway cron)

### Phase 4: Integration & Polish (Week 7)
- ✅ Payroll integration
- ✅ Alert system (signals)
- ✅ HTML report templates
- ✅ Testing and deployment

---

## Technical Stack Updates

### New Dependencies
- ✅ **Chart.js** (via `django-chartjs==2.3.0`): Graphical analytics
- ✅ **No Celery/Redis**: Use Django management commands + Railway cron
- ✅ **Django Signals**: Immediate alerts and auto-calculations

### Removed
- ❌ **Celery**: Too complex, use cron instead
- ❌ **Redis**: Not needed without Celery
- ❌ **WeasyPrint**: Using HTML instead of PDF

---

## Next Steps

1. ✅ **Review & Approve** this iteration
2. ✅ **Start Phase 1**: Build Products + Inventory apps
3. ✅ **Test daily**: Ensure manual/auto inputs work correctly
4. ✅ **Iterate**: Build incrementally, get feedback

**Priority**: CEO needs to see P&L per mix + deficit alerts working first! 🚀
