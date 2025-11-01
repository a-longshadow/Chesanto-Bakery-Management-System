# Milestone 2: Core Business Operations
**Project:** Chesanto Bakery Management System  
**Status:** 📋 Planning Phase  
**Date:** October 19, 2025

---

## Overview

Replicate Excel-based operations with automation, background processes, and alerts to minimize overhead and maximize accuracy. All features accessible via navigation bar (no hidden menus).

**Accountant = Single Source of Truth** (data entry, dispatch issuance, manual operations)  
**CEO + Developer = Supervisors** (oversight, monitoring)  
**Product Managers = Product-Specific Data Entry** (optional, can be done by accountant)

---

## App Structure

### Primary Apps (Navigation Bar)
1. **Products** - Product catalog (KDF, Bread, Scones + extensible)
2. **Inventory** - Raw materials tracking (direct + indirect)
3. **Sales** - Dispatch, returns, actual vs expected sales
4. **Reports** - Daily, Weekly, Monthly summaries
5. **Payroll** - Employee compensation (from Milestone 1)
6. **Analytics** - Graphical insights (minimal text)

---

## 1. Products App

### Product Types (Current)
- **KDF** (Kenya Dairy Food)
- **Bread**
- **Scones**
- *(Extensible for future products)*

### Product Lifecycle
```
Raw Ingredients → Mix (measured in metrics: g, kg) → Baking/Processing → Packaging → Dispatch
```

### Key Features
- **Mix Recipes**: Define ingredient quantities per product
- **Output Variability**:
  - **KDF**: Variable output (98-105 units from baseline 100) - hand-cut
  - **Bread**: Fixed output per mix - machine weighed
  - **Scones**: Fixed output per mix - machine weighed
- **Packaging Rules**:
  - **Bread**: 1 unit per packet
  - **Scones**: 12 units per packet (1 dozen)
  - **KDF**: 12 units per packet (1 dozen)

### Data Models

```python
# products/models.py

class Product(models.Model):
    """Main product catalog"""
    name = models.CharField(max_length=100)  # KDF, Bread, Scones
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Output characteristics
    has_variable_output = models.BooleanField(default=False)
    baseline_output = models.IntegerField(help_text="Expected units per mix")
    min_output = models.IntegerField(null=True, blank=True)  # For KDF: 98
    max_output = models.IntegerField(null=True, blank=True)  # For KDF: 105
    
    # Packaging
    units_per_packet = models.IntegerField(default=1)  # Bread=1, KDF=12, Scones=12
    
    # Pricing
    price_per_packet = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)


class Mix(models.Model):
    """Recipe for each product - what ingredients + quantities needed"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='mixes')
    name = models.CharField(max_length=200)  # "Standard Bread Mix"
    is_active = models.BooleanField(default=True)
    
    # Expected yield
    expected_packets = models.IntegerField(help_text="How many packets this mix produces")
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MixIngredient(models.Model):
    """Individual ingredients in a mix"""
    mix = models.ForeignKey(Mix, on_delete=models.CASCADE, related_name='ingredients')
    inventory_item = models.ForeignKey('inventory.InventoryItem', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)  # Support grams
    unit = models.CharField(max_length=20, choices=[
        ('g', 'Grams'),
        ('kg', 'Kilograms'),
        ('ml', 'Milliliters'),
        ('l', 'Liters'),
    ])
```

---

## 2. Inventory App

### Categories
1. **Direct Costs** (Ingredients): Flour, cooking fat, calcium, yeast, sugar, etc.
2. **Indirect Costs**: Fuel, packaging materials, transport, utilities, crates

### Key Features
- Track stock levels (opening, usage, closing)
- Auto-deduct from inventory when mixes are produced
- Alert when stock reaches reorder level
- Support metric measurements (g, kg, ml, l)
- Track crates (dispatched vs returned)

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
    """Raw materials and supplies"""
    name = models.CharField(max_length=200)  # "Wheat Flour", "Diesel", "Bread Bags"
    category = models.ForeignKey(InventoryCategory, on_delete=models.PROTECT)
    
    # Stock tracking
    current_stock = models.DecimalField(max_digits=10, decimal_places=3)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=3)
    unit = models.CharField(max_length=20)  # kg, liters, pieces, etc.
    
    # Pricing
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Alerts
    alert_enabled = models.BooleanField(default=True)
    alert_recipients = models.ManyToManyField(User, related_name='inventory_alerts')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class StockMovement(models.Model):
    """Track all inventory changes - audit trail"""
    PURCHASE = 'PURCHASE'
    PRODUCTION_USE = 'PRODUCTION_USE'
    ADJUSTMENT = 'ADJUSTMENT'
    DAMAGE = 'DAMAGE'
    
    MOVEMENT_TYPES = [
        (PURCHASE, 'Purchase/Restock'),
        (PRODUCTION_USE, 'Used in Production'),
        (ADJUSTMENT, 'Manual Adjustment'),
        (DAMAGE, 'Damaged/Spoiled'),
    ]
    
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Before/After for audit
    stock_before = models.DecimalField(max_digits=10, decimal_places=3)
    stock_after = models.DecimalField(max_digits=10, decimal_places=3)
    
    # Cost tracking
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

---

## 3. Production App (NEW - Supporting Module)

### Purpose
Bridge between Inventory and Sales - track daily production batches

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
    packets_produced = models.IntegerField(help_text="Actual packets produced")
    expected_packets = models.IntegerField(help_text="Expected based on mix recipe")
    
    # Variance (for KDF)
    variance = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Costs (auto-calculated)
    direct_cost = models.DecimalField(max_digits=12, decimal_places=2)  # Ingredients
    indirect_cost = models.DecimalField(max_digits=12, decimal_places=2)  # Fuel, packaging, etc.
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    cost_per_packet = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Who recorded this
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
    
    is_closed = models.BooleanField(default=False)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## 4. Sales App

### Workflow
```
Production → Dispatch (Salesmen take crates + products) → Sales → Returns (unsold products + crates) → Closing
```

### Key Features
- Track dispatch to salesmen and schools
- Record returns (products + crates)
- Calculate **Expected Sales** (production × price)
- Calculate **Actual Sales** (money returned - commission)
- Identify deficits (sales that didn't add up, missing crates)

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


class Dispatch(models.Model):
    """Daily dispatch to salesmen/schools"""
    date = models.DateField(default=timezone.now)
    salesperson = models.ForeignKey(Salesperson, on_delete=models.PROTECT)
    
    # What went out
    crates_dispatched = models.IntegerField()
    
    # Status
    is_returned = models.BooleanField(default=False)
    
    dispatched_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='dispatches_made')
    dispatched_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']


class DispatchItem(models.Model):
    """Products in each dispatch"""
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    packets_dispatched = models.IntegerField()
    expected_revenue = models.DecimalField(max_digits=12, decimal_places=2)  # packets × price


class SalesReturn(models.Model):
    """What came back from dispatch"""
    dispatch = models.OneToOneField(Dispatch, on_delete=models.CASCADE, related_name='returns')
    
    # Returns
    crates_returned = models.IntegerField()
    crates_deficit = models.IntegerField(default=0)  # dispatched - returned
    
    # Money
    cash_returned = models.DecimalField(max_digits=12, decimal_places=2)
    commission_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_revenue = models.DecimalField(max_digits=12, decimal_places=2)  # cash - commission
    
    # Discrepancies
    revenue_deficit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)


class SalesReturnItem(models.Model):
    """Unsold products returned"""
    sales_return = models.ForeignKey(SalesReturn, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    packets_returned = models.IntegerField()
    packets_sold = models.IntegerField()  # dispatched - returned


class DailySales(models.Model):
    """Summary of all sales for a day"""
    date = models.DateField(unique=True)
    
    # Dispatch totals
    total_dispatched_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_crates_dispatched = models.IntegerField(default=0)
    
    # Returns totals
    total_actual_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_crates_returned = models.IntegerField(default=0)
    
    # Deficits
    revenue_deficit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    crate_deficit = models.IntegerField(default=0)
    
    is_closed = models.BooleanField(default=False)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
```

---

## 5. Reports App

### Report Types
1. **Daily Report** (Monday-Saturday)
2. **Weekly Report** (Aggregates 6 days)
3. **Monthly Report** (Aggregates all weeks)

### Report Sections

#### A. Production Section
- Direct costs (ingredients by product)
- Indirect costs (fuel, packaging, transport)
- Packets produced vs expected
- Cost per packet by product

#### B. Dispatch Section
- Products dispatched (by salesman/school)
- Crates dispatched
- Products returned
- Crates returned
- Deficits (products, crates)

#### C. Sales Section
- **Expected Sales**: Production × Price per packet
- **Actual Sales**: Cash returned - Commission
- **Variance**: Expected - Actual
- Sales by salesman/school
- Commission paid

#### D. Closing Stock
- Opening stock (from previous day)
- Production added
- Sales deducted
- Returns added
- Closing stock (carried to next day)

#### E. Profit & Loss
- Total Revenue (actual sales)
- Total Production Cost
- Total Indirect Costs
- Gross Profit
- Net Profit (after commission)

### Data Models

```python
# reports/models.py

class DailyReport(models.Model):
    """Comprehensive daily summary"""
    date = models.DateField(unique=True)
    
    # Production
    production_summary = models.JSONField(default=dict)
    
    # Sales
    sales_summary = models.JSONField(default=dict)
    
    # Stock
    opening_stock = models.JSONField(default=dict)
    closing_stock = models.JSONField(default=dict)
    
    # Financials
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    total_costs = models.DecimalField(max_digits=12, decimal_places=2)
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = models.DecimalField(max_digits=5, decimal_places=2)  # Percentage
    
    generated_at = models.DateTimeField(auto_now_add=True)


class WeeklyReport(models.Model):
    """Aggregate of 6 daily reports (Mon-Sat)"""
    week_start = models.DateField()
    week_end = models.DateField()
    
    # Aggregated data
    total_production = models.JSONField(default=dict)
    total_sales = models.JSONField(default=dict)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    total_costs = models.DecimalField(max_digits=12, decimal_places=2)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2)
    
    generated_at = models.DateTimeField(auto_now_add=True)


class MonthlyReport(models.Model):
    """Aggregate of all weeks in a month"""
    month = models.DateField()  # First day of month
    
    # Aggregated data
    total_production = models.JSONField(default=dict)
    total_sales = models.JSONField(default=dict)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    total_costs = models.DecimalField(max_digits=12, decimal_places=2)
    net_profit = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Trends
    best_selling_product = models.CharField(max_length=100)
    worst_performing_day = models.DateField()
    
    generated_at = models.DateTimeField(auto_now_add=True)
```

---

## 6. Analytics App

### Purpose
Graphical insights with minimal text - CEO dashboard

### Key Metrics
- Inventory levels (bar charts)
- Production trends (line graphs)
- Expected vs Actual sales (comparison charts)
- Profit margins (pie charts)
- Deficits tracking (trend lines)
- Best/worst performing products
- Best/worst performing salesmen

### Features
- Real-time dashboard
- Date range filters
- Export charts as images/PDF
- Alerts for anomalies

---

## Automation & Background Tasks

### Auto-Calculations (No Manual Input)
1. ✅ **Inventory Deduction**: Auto-deduct ingredients when production batch created
2. ✅ **Cost Calculation**: Auto-calculate direct/indirect costs per batch
3. ✅ **Expected Sales**: Auto-calculate (packets × price)
4. ✅ **Deficits**: Auto-calculate (dispatched - returned)
5. ✅ **Profit/Loss**: Auto-calculate from revenue and costs
6. ✅ **Stock Movements**: Auto-update opening/closing stock

### Background Processes (Celery Tasks)
1. 🔔 **Low Stock Alerts**: Check inventory levels every hour
2. 🔔 **Deficit Alerts**: Notify when crates/revenue don't match
3. 🔔 **Daily Report Generation**: Auto-generate at end of day (6 PM?)
4. 🔔 **Weekly Report Generation**: Auto-generate every Saturday night
5. 🔔 **Monthly Report Generation**: Auto-generate on last day of month

### Alert Recipients
- **Low Stock**: Accountant, Inventory Manager
- **Deficits**: Accountant, CEO
- **Production Issues**: Product Managers
- **Report Ready**: CEO, Accountant

---

## User Workflows

### Accountant (Primary Data Entry)
1. **Morning**: Enter opening stock (or auto-loaded from previous day)
2. **Production Time**: Enter mix data, actual output
3. **Dispatch Time**: Create dispatch records (salesman, products, crates)
4. **Evening**: Record returns (products, crates, cash)
5. **Close Day**: Review and finalize daily report

### Product Managers (Optional)
1. Enter production data for their specific product line
2. Update mix recipes if needed
3. View product-specific reports

### CEO (Supervisor)
1. View analytics dashboard
2. Review daily/weekly/monthly reports
3. Receive alerts for deficits/anomalies
4. Monitor overall operations

---

## Data Integrity Rules

### Avoid Duplication
- ✅ Mix recipes stored once, reused for production
- ✅ Product prices updated centrally
- ✅ Inventory items defined once
- ✅ Opening stock = Previous day's closing stock (auto-linked)

### Audit Trail (All Actions Logged)
- Who created production batch
- Who dispatched products
- Who recorded returns
- Who updated prices/recipes
- Timestamp for all actions

### Validation Rules
1. Cannot dispatch more than available stock
2. Cannot return more than dispatched
3. Closing stock must match: Opening + Production - Sales + Returns
4. Crates returned ≤ Crates dispatched

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Set up Products app (models, admin)
- Set up Inventory app (models, admin)
- Create basic forms for data entry

### Phase 2: Production (Week 2)
- Production batch tracking
- Mix usage and inventory deduction
- Opening/closing stock automation

### Phase 3: Sales (Week 3)
- Dispatch module
- Returns module
- Deficit tracking

### Phase 4: Reports (Week 4)
- Daily report generation
- Weekly/monthly aggregation
- Export functionality

### Phase 5: Analytics (Week 5)
- Dashboard with charts
- Real-time metrics
- Alerts and notifications

### Phase 6: Polish (Week 6)
- UI/UX improvements
- Background task setup (Celery)
- Testing and bug fixes

---

## Technical Stack Additions

### New Dependencies
- **Django Celery**: Background tasks (alerts, reports)
- **Redis**: Celery broker + caching
- **Chart.js / Plotly**: Graphical analytics
- **Pandas**: Data processing for reports
- **WeasyPrint**: PDF report generation

---

## Questions to Clarify

1. **Indirect Costs**: How do we allocate fuel/transport costs? Per batch? Per day?
2. **Commission**: Fixed rate per salesman or variable?
3. **Deficits**: What happens when cash doesn't match expected sales? Just flag it?
4. **Schools**: Do they operate differently from salesmen? Payment terms?
5. **Pricing**: Can prices change mid-day or only at day start?
6. **Returns**: Are returned products added back to stock or discarded?
7. **Crate Damage**: How to record damaged crates that can't be returned?

---

**Next Steps:**
1. Review and approve this plan
2. Answer clarification questions
3. Start with Phase 1 (Products + Inventory apps)
4. Build iteratively, test daily

**Priority:** Navigation bar placement - keep all 6 apps visible for user-friendliness
