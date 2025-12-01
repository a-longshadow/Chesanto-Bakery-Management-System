# Milestone 2: Core Business Operations
**Project:** Chesanto Bakery Management System  
**Status:** 📋 MVP Implementation  
**Date:** October 24, 2025

---

## 🎯 Navigation Bar Apps (8 Total)

1. **Products** - Catalog, mixes, recipes
2. **Inventory** - Ingredients, stock, restocking
3. **Production** - Daily batches, costs, P&L per mix
4. **Sales** - Dispatch, returns, deficits
5. **Accounting** - Invoices, financials
6. **Reports** - Daily/Weekly/Monthly (DB-stored)
7. **Analytics** - Graphical dashboard
8. **Payroll** - Salaries, deductions

---

## 🏗️ Data Flow

```
INVENTORY → PRODUCTS (mixes) → PRODUCTION → SALES → ACCOUNTING → REPORTS/ANALYTICS
                                                         ↓
                                                     PAYROLL
```

---

## 📦 1. Products App

### Terminology
- **KDF**: Pieces (12 = 1 packet), Variable output 98-107, Hand-cut
- **Bread**: Loaves (1 = 1 packet), Fixed output, Machine-weighed
  - **Bread Rejects**: Sub-product, variable pricing (default KES 50/loaf)
- **Scones**: Pieces (12 = 1 packet), Fixed output, Machine-weighed

**Note:** Product pricing, variance ranges, and titles are Super Admin configurable (not hardcoded)

### Data Flow
```
INVENTORY (Ingredients) → MIX (Recipe) → PRODUCT (Bread/KDF/Scones)
```
**Key Concept**: Mixes consume ingredients from Inventory to produce Products.

### Models
```python
Product: 
    name (✏️ Super Admin editable), 
    alias (✏️ Super Admin editable), 
    units_per_packet, 
    price_per_packet (KES - ✏️ Super Admin editable), 
    has_variable_output (bool),
    min_expected_output (✏️ Super Admin editable - e.g., 98 for KDF),
    max_expected_output (✏️ Super Admin editable - e.g., 107 for KDF),
    has_sub_product (bool - e.g., True for Bread with Rejects),
    sub_product_name (e.g., "Bread Rejects"),
    sub_product_price (KES - ✏️ Super Admin editable, default 50),
    is_active (bool), 
    created_by, created_at, updated_by, updated_at

Ingredient: 
    name, default_unit, inventory_item (FK to InventoryItem),
    is_active (bool), created_by, created_at, updated_by, updated_at

Mix: 
    product (FK), name, version, expected_packets, is_active (bool),
    total_cost (🤖 calculated - sum of all MixIngredients), 
    cost_per_packet (🤖 calculated - total_cost / expected_packets),
    created_by, created_at, updated_by, updated_at

MixIngredient: 
    mix (FK), ingredient (FK), 
    quantity (✏️ manual - e.g., 36, 4.5, 2.8), 
    unit (✏️ manual - kg, g, L),
    ingredient_cost (🤖 auto from Inventory - quantity × cost_per_unit),
    created_by, created_at, updated_by, updated_at
```

### Dynamic Features (✏️ Accountant+ Adjustable)

**1. Add/Remove Products:**
- ✅ **Create NEW Products**: Super Admin can add entirely new products (e.g., "Donuts", "Cookies", "Cakes")
- ✅ **Edit Product Details**: Names, prices, variance ranges, sub-product pricing
- ✅ **Add Custom Fields**: Via Django Admin (e.g., shelf_life, dietary_info, certifications)
- ✅ **Deactivate Products**: Soft delete (set `is_active=False`) - keeps historical data
- **Interface**: Django Admin + Custom forms (Phase 1)

**2. Add/Remove Ingredients:**
- ✅ **Add NEW Ingredients**: Link to InventoryItem (e.g., "Honey", "Sesame Seeds")
- ✅ **Edit Ingredient Details**: Name, default unit, linked inventory item
- ✅ **Remove Ingredients**: Soft delete (set `is_active=False`)
- **Interface**: Django Admin + inline forms

**3. Add/Remove Mixes:**
- Create new mix (e.g., "Mix 2" for Bread with different ratios)
- Clone existing mix and modify
- Deactivate old mix versions (keep for historical records)

**4. Adjust Mix Components:**
- ✏️ **Manual Entry**: Select ingredient, enter quantity & unit
- 🤖 **Auto-load**: When mix selected → all MixIngredients load with current costs
- 🤖 **Auto-calculate**: Change quantity → ingredient_cost recalculates from Inventory
- 🤖 **Auto-total**: Any change → total_cost & cost_per_packet update

**4. Cost Auto-fill Behavior:**
```
User selects "Bread Mix 1"
↓
System loads 7 MixIngredients:
  - Flour: 36 kg × KES 73/kg (from Inventory) = KES 2,628
  - Sugar: 4.5 kg × KES 144/kg (from Inventory) = KES 648
  - [... etc for all ingredients]
↓
Total Mix Cost: KES 4,224.38 (auto-calculated)
Cost per Loaf: KES 32.00 (auto-calculated)
```

**5. When to Recalculate:**
- Ingredient quantity changed → recalculate ingredient_cost
- Ingredient added/removed → recalculate total_cost
- Inventory price updated → recalculate all mixes using that ingredient
- Expected packets changed → recalculate cost_per_packet

### Admin Configuration Interface

**Django Admin + Custom Forms (Phase 1):**
- Super Admin dashboard for product/ingredient management
- Inline forms for mix ingredients (add/edit/remove on same page)
- Bulk actions (activate/deactivate multiple items)
- Change history tracking (who changed what when)
- Permission-based access (only Super Admin can add/delete)

### Example Mixes

#### Bread Mix 1
**Product**: Bread (132 loaves expected)  
**Selling Price**: KES 60/loaf (✏️ Super Admin editable)

**Sub-Product: Bread Rejects**  
- Loaves that don't meet quality standards (size, shape, color)
- Sold separately at reduced price
- Default Price: KES 50/loaf (✏️ Super Admin editable)
- Tracked separately in production and sales

**Ingredients (from Inventory):**
- Flour: 36 kg @ KES 73/kg = KES 2,628
- Sugar: 4.5 kg @ KES 144/kg = KES 648
- Bread improver: 60 g @ KES 0.6/g = KES 36
- Salt: 280 g @ KES 0.0/g = KES 9.9
- Calcium: 70 g @ KES 0.34/g = KES 23.8
- Yeast: 200 g @ KES 0.6/g = KES 111.1
- Cooking Fat: 2.8 kg @ KES 274/kg = KES 768

**Total Mix Cost**: KES 4,224.38  
**Expected Output**: 132 loaves  
**Cost per Loaf**: KES 32.00  
**Selling Price per Loaf**: KES 60  
**Profit per Loaf**: KES 28.00  
**Profit per Mix**: KES 3,696.00

**Note:** Rejects count toward production but sold at different price

---

#### KDF Mix 1
**Product**: KDF (107 packets expected, 12 pieces/packet)  
**Selling Price**: KES 100/packet (✏️ Super Admin editable)

**Ingredients (from Inventory):**
- Flour: 50 kg @ KES 73/kg = KES 3,650
- Sugar: 2.5 kg @ KES 144/kg = KES 360
- Yeast: 160 g @ KES 0.9/g = KES 142
- Salt: 300 g @ KES 0.04/g = KES 10.65
- Calcium: 60 g @ KES 0.34/g = KES 20.4
- Cooking fat: 1.5 kg @ KES 274/kg = KES 411
- Cooking oil: 7.5 L @ KES 237/L = KES 1,774

**Total Mix Cost**: KES 6,368  
**Expected Output**: 107 packets  
**Cost per Packet**: KES 59.52  
**Selling Price per Packet**: KES 100  
**Profit per Packet**: KES 40.48  
**Profit per Mix**: KES 4,331.36

---

#### Scones Mix 1
**Product**: Scones (102 packets expected, 12 pieces/packet)  
**Selling Price**: KES 50/packet (✏️ Super Admin editable)

**Ingredients (from Inventory):**
- Flour: 26 kg @ KES 72/kg = KES 1,872
- Sugar: 3.8 kg @ KES 144/kg = KES 547
- Yeast: 190 g @ KES 0.6/g = KES 108
- Salt: 280 g @ KES 0.04/g = KES 9.94
- Calcium: 50 g @ KES 0.34/g = KES 17
- Cooking fat: 2.3 kg @ KES 260/kg = KES 598
- Bread improver: 50 g @ KES 0.3/g = KES 14

**Total Mix Cost**: KES 3,166  
**Expected Output**: 102 packets  
**Cost per Packet**: KES 31.04  
**Selling Price per Packet**: KES 50  
**Profit per Packet**: KES 18.96  
**Profit per Mix**: KES 1,933.92

### Inputs/Outputs
- ✏️ **Manual**: Product details, pricing, mix recipes (ingredients + quantities)
- 🤖 **Auto**: Ingredient costs (pulled from Inventory), total mix cost, cost per packet
- **Output**: Product catalog, mix recipes, cost per packet calculations

---

## 📦 2. Inventory App

### Dynamic Inventory Management

**Admin Can (✏️ Configurable):**
- ✅ **Add NEW Inventory Items**: Create new items (e.g., "Honey", "Sesame Seeds", "Vanilla Extract")
- ✅ **Edit Item Properties**: Name, category, unit, cost_per_unit, reorder_level, alert_threshold_days
- ✅ **Adjust Categories**: Add new expense categories or modify existing
- ✅ **Deactivate Items**: Soft delete (set `is_active=False`) - preserves historical purchases
- ✅ **Bulk Import**: CSV upload for multiple items (Phase 2 enhancement)
- **Interface**: Django Admin + Custom forms

### Categories & Items (All Adjustable - Add/Remove)

**Direct Expenses (Ingredients):**
- Flour
- Cooking fat
- Cooking oil
- Sugar
- Yeast
- Food colour
- Bread improver
- Calcium
- **Packaging materials (bags @ KES 3.3/unit)**
- Stock transportation
- Salt

**Packaging Rules:**
- **Bread**: 1 bag per loaf (132 loaves = 132 bags)
- **KDF**: 1 bag per packet of 12 pieces (107 packets = 107 bags)
- **Scones**: 1 bag per packet of 12 pieces (102 packets = 102 bags)
- **Standard Cost**: KES 3.3 per bag (adjustable in Inventory)

**Indirect Costs:**
- Diesel (production - 20L jerycans/liters)
- Firewood (production)
- Fuel for old truck (distribution)
- Fuel for new truck (distribution)
- Fuel Bolero (production)
- Electricity

**Fuel Tracking:**
- **Diesel**: Production use (jerrycans @ filling station)
- **Vehicle Fuel**: Old Truck, New Truck, Bolero (petrol/diesel), any addition
- **Reconciliation**: Ikapolok Filling Station statements, any other filling station
- **Vehicle-wise consumption** tracking for cost analysis

**Direct Salaries:**
- Salaries for production staff
- Salaries for sales staff
- Casuals

**Commissions:**
- Bread commission
- KDF commission
- Scones commission

**Administration Expenses:**
- Salaries for admin staff
- Staff loans
- Bank charges
- Stationery
- Vehicle repairs/insurance
- Machine repairs
- Packaging papers purchases
- Depot rent
- Bolero purchase
- Business permit
- Sundry expenses
- Expired & missing stock
- Deficits (bad debts)
- Education policy (reserves)

### Inventory Stock (Raw Materials) Tracking

**Opening/Closing Inventory Stock Items:**
- Flour (bags) - *1 bag = 12 packets × 2kg = 24kg*
- Sugar (kg)
- Cooking Oil (20L jerycans)
- Cooking Fat (17kg buckets)
- Yeast (450g packets)
- Yeast (2-in-1)
- Bread Improver (1kg packets)
- Calcium (kg)
- Salt (1kg packets)
- Food Colour (units)
- Diesel (L)
- Packaging paper (units)

### Unit Conversions
```python
# System tracks both purchase units and recipe units
Flour: 
  - Purchase unit: bags (1 bag = 24kg)
  - Recipe unit: kg
  - Conversion: 1 bag = 24kg

Cooking Fat:
  - Purchase unit: 17kg buckets
  - Recipe unit: kg
  - Conversion: 1 bucket = 17kg

Cooking Oil:
  - Purchase unit: 20L jerycans
  - Recipe unit: L
  - Conversion: 1 jerycan = 20L

Yeast:
  - Purchase unit: 450g packets
  - Recipe unit: g
  - Conversion: 1 packet = 450g

Bread Improver:
  - Purchase unit: 1kg packets
  - Recipe unit: g
  - Conversion: 1 packet = 1000g

Salt:
  - Purchase unit: 1kg packets
  - Recipe unit: g
  - Conversion: 1 packet = 1000g
```

### Features
- **Adjustable lists** (add/remove items from any category)
- **Opening/Closing Inventory Stock** (raw materials)
- **Purchase/Expenditure tracking** (raw materials, operational supplies)
- Restocking (manual add with purchase details)
- Reorder levels (default + custom)
- **Smart Alerts** (admin-configurable thresholds)
- Auto-deduct on production
- **Unit conversion** (purchase units ↔ recipe units)
- Crate tracking

### Models
```python
ExpenseCategory: name, category_type (DIRECT_EXPENSE/INDIRECT_COST/DIRECT_SALARY/COMMISSION/ADMIN_EXPENSE)

InventoryItem: 
    name, category (FK), 
    
    # Stock Levels
    current_stock, 
    default_reorder_level, 
    custom_reorder_level,
    
    # Smart Alert Configuration (✏️ Admin adjustable)
    alert_threshold_days (default: 7 - weeks worth of production),
    weekly_usage_average (🤖 Auto-calculated from past 4 weeks),
    calculated_alert_level (🤖 Auto = weekly_usage_average × alert_threshold_days),
    
    # Unit Management
    purchase_unit (e.g., "bags", "17kg buckets", "20L jerycans"),
    recipe_unit (e.g., "kg", "L", "g"),
    conversion_factor (e.g., 24 for flour: 1 bag = 24kg),
    
    # Costing
    cost_per_purchase_unit (KES),
    cost_per_recipe_unit (KES - calculated),
    
    # Flags
    is_active, is_custom (user-added),
    
    created_by, created_at, updated_by, updated_at

DailyInventoryStock:
    date,
    
    # Per Inventory Item (JSON or separate model)
    opening_stock (in purchase units),
    additional_stock (purchases/restocking),
    daily_usage (from production - in recipe units, displayed in purchase units),
    closing_stock (🤖 Auto = opening + additional - usage),
    
    # Overall
    total_opening_value (KES),
    total_purchases_value (KES),
    total_usage_value (KES),
    total_closing_value (KES),
    
    is_closed (bool),
    closed_by (FK to User),
    closed_at (timestamp),
    created_by, created_at, updated_by, updated_at

Purchase:
    # Transaction Details
    purchase_date,
    purchase_number (unique - e.g., PUR-2025-001),
    supplier_name,
    
    # Items & Costs
    total_quantity (units),
    total_amount (KES),
    
    # Payment
    payment_status (PENDING/PARTIAL/PAID),
    amount_paid (KES),
    payment_method (CASH/BANK_TRANSFER/MPESA/CREDIT),
    payment_reference,
    
    # Approval (✏️ Accountant+)
    is_approved (bool),
    approved_by (FK to User),
    approved_at,
    
    # Notes
    notes,
    
    created_by, created_at, updated_by, updated_at

PurchaseItem:
    purchase (FK),
    inventory_item (FK),
    
    # Details
    description,
    quantity,
    unit (purchase_unit),
    unit_cost (KES),
    total_cost (🤖 quantity × unit_cost),
    
    created_at

StockMovement: 
    item (FK), movement_type (PURCHASE/PRODUCTION_USE/ADJUSTMENT/RETURN), 
    quantity, 
    unit (purchase_unit or recipe_unit),
    stock_before, stock_after (in purchase units), 
    
    # Reference to source transaction
    reference_type (Purchase/ProductionBatch/SalesReturn/Manual), 
    reference_id,
    
    notes, created_by, created_at

Crate: 
    total_crates, available_crates, dispatched_crates, damaged_crates,
    updated_by, updated_at

Vehicle:
    # Vehicle Details
    name (e.g., "Old Truck", "New Truck", "Bolero"),
    registration_number,
    vehicle_type (TRUCK/VAN/MOTORBIKE),
    fuel_type (PETROL/DIESEL),
    
    # Status
    is_active (bool),
    
    created_by, created_at, updated_by, updated_at

FuelTransaction:
    # Transaction Details
    transaction_date,
    transaction_number,
    filling_station (e.g., "Ikapolok Filling Station"),
    
    # Fuel Details
    fuel_type (DIESEL/PETROL),
    purpose (PRODUCTION/DISTRIBUTION),
    vehicle (FK - nullable for production diesel),
    
    # Quantity & Cost
    quantity (liters or jerycans),
    unit (L/JERYCAN),
    amount (KES),
    cost_per_unit (🤖 Auto = amount / quantity),
    
    # Reconciliation
    running_balance (KES - at filling station),
    payment_method (CASH/CREDIT/MPESA),
    is_reconciled (bool),
    
    # Reference
    receipt_number,
    notes,
    
    created_by, created_at, updated_by, updated_at

FuelReconciliation:
    # Period
    month, year,
    filling_station,
    
    # Balances
    opening_balance (KES),
    total_fuel_purchases (KES),
    total_diesel_purchases (KES),
    total_payments_made (KES),
    closing_balance (KES),
    
    # Reconciliation Status
    is_reconciled (bool),
    reconciled_by (FK to User),
    reconciled_at,
    variance (KES),
    variance_notes,
    
    created_by, created_at, updated_by, updated_at
```

### Purchase/Expenditure Tracking

**Example from Sheet 10 Analysis:**
```
Total Expenditure: KES 18,078,039 (113 transactions)
Average Transaction: KES 168,954
Categories: Raw Materials (Flour, Cooking Fat, Oil), Operational Costs (Fuel, Maintenance)

Sample Transaction:
─────────────────────────────────────
Date: 15/09/2025
Supplier: Unga Suppliers Ltd
Purchase #: PUR-2025-045

Items:
  - Flour: 50 bags @ KES 1,825/bag = KES 91,250
  - Cooking Oil: 10 jerycans @ KES 4,500/jerycan = KES 45,000
  - Sugar: 100 kg @ KES 180/kg = KES 18,000

Total: KES 154,250
Payment: Bank Transfer (Reference: TXN123456)
Status: PAID
Approved by: Accountant (Eddah Silungi)
─────────────────────────────────────
Result: Stock movements created for all 3 items
        Opening Inventory Stock updated
        Expenditure recorded in Accounting
```

### Purchase Workflow

**Step 1: Create Purchase Order** (✏️ Accountant)
```
New Purchase → Enter supplier, date
Add items (Flour, Oil, Sugar, etc.)
Quantities & unit costs
System calculates totals
```

**Step 2: Approval** (✏️ Accountant/Admin)
```
Review purchase details
Approve → is_approved = True
```

**Step 3: Record Payment** (✏️ Accountant)
```
Payment method: Cash/Bank/M-Pesa
Amount paid (full or partial)
Payment reference
Mark status: PAID
```

**Step 4: Auto-update Stock** (🤖 System)
```
For each PurchaseItem:
  - Create StockMovement (type: PURCHASE)
  - Update InventoryItem.current_stock
  - Update DailyInventoryStock.additional_stock
  - Link to Purchase via reference_type/reference_id
```

**Step 5: Accounting Integration** (🤖 System)
```
Purchase finalized → Creates expense in Accounting
Category: Direct Expenses (Flour, Sugar, etc.) or Indirect Costs (Fuel, etc.)
Amount: Purchase.total_amount
Linked to Purchase record
```

### Inventory Stock Flow Example
```
FLOUR (1 bag = 24kg)
───────────────────────────────────────
Opening Inventory Stock:    50 bags (1,200 kg)
Additional Stock:           +10 bags (240 kg) purchased
Daily Usage:                -45.5 kg (1.9 bags) from 8 bread mixes
Closing Inventory Stock:    58.1 bags (1,394.5 kg)

COOKING OIL (1 jerycan = 20L)
───────────────────────────────────────
Opening Inventory Stock:    5 jerycans (100 L)
Additional Stock:           +0 jerycans
Daily Usage:                -7.5 L (0.375 jerycans) from KDF mixes
Closing Inventory Stock:    4.625 jerycans (92.5 L)
```

### Fuel Tracking & Reconciliation

**Fuel Transaction Recording:**
```
Date: 15/09/2025
Filling Station: Ikapolok Filling Station
Receipt #: IKP-2025-0915

Transaction 1:
  Type: Diesel (Production)
  Quantity: 5 jerycans (100 L)
  Amount: KES 15,500
  Cost/L: KES 155
  Purpose: Production (bakery ovens)
  Balance: KES 45,000 (credit)

Transaction 2:
  Type: Petrol (Distribution)
  Vehicle: Old Truck
  Quantity: 40 L
  Amount: KES 7,200
  Cost/L: KES 180
  Purpose: Distribution
  Balance: KES 52,200 (credit)

Transaction 3:
  Type: Diesel (Distribution)
  Vehicle: Bolero
  Quantity: 30 L
  Amount: KES 4,800
  Cost/L: KES 160
  Purpose: Distribution
  Balance: KES 57,000 (credit)
```

**Monthly Reconciliation (September 2025):**
```
Ikapolok Filling Station Statement
───────────────────────────────────────
Opening Balance:        KES 25,000 (credit)
Fuel Purchases:        +KES 85,000
Diesel Purchases:      +KES 120,000
Total Credit:           KES 230,000

Payments Made:         -KES 180,000
───────────────────────────────────────
Closing Balance:        KES 50,000 (credit)
Status: Reconciled ✓
Variance: KES 0
```

**Vehicle Consumption Analysis:**
```
September 2025 Summary
───────────────────────────────────────
Old Truck:
  - 12 transactions
  - 480 L fuel
  - KES 86,400 total
  - Avg: KES 180/L

New Truck:
  - 8 transactions
  - 320 L fuel
  - KES 57,600 total
  - Avg: KES 180/L

Bolero:
  - 15 transactions
  - 450 L diesel
  - KES 72,000 total
  - Avg: KES 160/L

Production Diesel:
  - 20 jerycans (400 L)
  - KES 62,000 total
  - Avg: KES 155/L
───────────────────────────────────────
Total Fuel Cost: KES 278,000
```

### Packaging Material Tracking
```python
# Automatic calculation when ProductionBatch is saved:
ProductionBatch.packaging_cost = packets_produced × packaging_bag_cost (KES 3.3)

# Example from screenshots:
Bread (8 mixes): 1,056 loaves × KES 3.3 = KES 3,484.80
KDF: 832 packets × KES 3.3 = KES 2,745.60
Scones: 612 packets × KES 3.3 = KES 2,019.60
─────────────────────────────────────────────────
Total Daily Packaging: 2,500 bags × KES 3.3 = KES 8,250
```

### Inputs/Outputs
- ✏️ **Manual (Accountant+)**: 
  - **Purchase orders**: Supplier, items, quantities, costs
  - **Payment recording**: Method, reference, amount
  - **Purchase approval**: Review and authorize
  - **Fuel transactions**: Date, vehicle, quantity, amount, receipt #
  - **Fuel reconciliation**: Match filling station statements, resolve variances
  - **Alert thresholds**: Admin can adjust (e.g., "Alert when < 7 days production supply")
  - Initial stock, restocking (additional stock), custom reorder levels
  - Unit conversions (e.g., 1 bag flour = 24kg)
  - Costs per purchase unit
  - Add/remove items, vehicles
  - Packaging bag cost (default KES 3.3)
- 🤖 **Auto**: 
  - **Stock movements from purchases** (PURCHASE type)
  - **Inventory stock updates** (current_stock, additional_stock)
  - **Accounting expense entries** (Direct Expenses, Indirect Costs, Fuel costs)
  - **Fuel cost allocation**: Production vs Distribution
  - **Vehicle consumption tracking**: Cost per vehicle, per liter averages
  - **Fuel reconciliation balances**: Running totals, variance detection
  - **Smart alerts**: When current_stock < calculated_alert_level (7 days production)
  - **Weekly usage calculation**: Auto-calculated from past 4 weeks
  - Daily usage deductions (from production - ingredients + packaging bags)
  - Closing inventory stock (opening + additional - usage)
  - Cost per recipe unit calculations
  - Unit conversions for reports
  - Low stock alerts
  - Packaging cost calculations
  - Purchase totals
- **Output**: 
  - **Purchase orders with approval status**
  - **Expenditure reports** (by category, supplier, date range)
  - **Budget vs Actual spending**
  - **Fuel reconciliation reports** (monthly, by filling station)
  - **Vehicle consumption analysis** (cost per vehicle, trends)
  - **Fuel cost breakdown**: Production diesel vs Distribution fuel
  - **Smart inventory alerts** (email + dashboard notification)
  - Opening/Closing Inventory Stock reports (raw materials)
  - Stock levels in both purchase and recipe units
  - Alerts for reorder levels
  - Inventory valuation
  - Audit trail with conversions
  - Packaging usage reports
  - **Purchase history & trends**

---

## 🏭 3. Production App

### Features
- Daily batch tracking
- **Opening/closing PRODUCT stock tracking (finished goods: Bread, KDF, Scones)**
- **P&L per mix** (CEO requirement)
- Auto-deduct inventory (raw materials)
- Cost calculations
- **Permission Level**: Accountant or higher can adjust production records

### Product Stock Flow Logic
```
OPENING PRODUCT STOCK (per product) = Previous day's closing product stock
  ↓
+ PRODUCTION (from mixes today)
  ↓
- DISPATCH (sent to salesmen/schools/depots)
  ↓
+ RETURNS (from salesmen/schools/depots)
  ↓
= CLOSING PRODUCT STOCK (per product)
```

**Alternative calculation:**
```
CLOSING PRODUCT STOCK = (Opening + Production) - Dispatched + Returns
                      = Not Dispatched + Returns
```

### Models
```python
ProductionBatch: 
    # Identification
    date, product (FK), mix (FK), batch_number,
    
    # Production Output (✏️ Accountant+)
    units_produced, packets_produced, variance (from expected),
    
    # Cost Breakdown (🤖 Auto-calculated from Inventory)
    direct_cost (ingredients), 
    indirect_cost (diesel, firewood, electricity - allocated daily),
    packaging_cost,
    total_cost,
    cost_per_packet,
    
    # Revenue & Profitability (🤖 Auto-calculated)
    revenue_if_sold (packets × selling_price),
    profit_per_mix (revenue - total_cost),
    profit_margin (%), 
    
    # Audit trail
    created_by (FK), created_at, updated_by (FK), updated_at,
    is_finalized (bool - locked after book closing)
                 
DailyProduction: 
    date,
    
    # Opening Product Stock (🤖 Auto = Previous day's closing product stock)
    opening_product_stock_bread (loaves),
    opening_product_stock_kdf (packets),
    opening_product_stock_scones (packets),
    opening_product_stock_total_value (KES - at cost),
    
    # Production Summary
    total_batches, 
    bread_produced (loaves),
    kdf_produced (packets),
    scones_produced (packets),
    total_packets_produced,
    total_production_cost (sum of all batches),
    
    # Dispatch Summary (from Sales App)
    bread_dispatched (loaves),
    kdf_dispatched (packets),
    scones_dispatched (packets),
    total_dispatched,
    
    # Returns Summary (from Sales App)
    bread_returned (loaves),
    kdf_returned (packets),
    scones_returned (packets),
    total_returned,
    
    # Closing Product Stock (🤖 Auto = Opening + Production - Dispatched + Returns)
    closing_product_stock_bread (loaves),
    closing_product_stock_kdf (packets), 
    closing_product_stock_scones (packets),
    closing_product_stock_total_value (KES - at cost),
    
    # Indirect Costs (✏️ Accountant+ adjustable)
    diesel_cost, firewood_cost, electricity_cost,
    fuel_old_truck, fuel_new_truck, fuel_bolero,
    total_indirect_costs,
    
    # Book Closing
    is_closed (bool), 
    closed_by (FK to User), 
    closed_at (timestamp),
    
    # Audit trail
    created_by (FK), created_at, updated_by (FK), updated_at
```

### Permission Matrix
| Action | Production Staff | Accountant | Admin/CEO |
|--------|-----------------|------------|-----------|
| View batches | ✅ | ✅ | ✅ |
| Add batch | ✅ | ✅ | ✅ |
| Edit batch (before closing) | ❌ | ✅ | ✅ |
| Edit batch (after closing) | ❌ | ❌ | ✅ |
| Adjust indirect costs | ❌ | ✅ | ✅ |
| Close daily production | ❌ | ✅ | ✅ |
| Reopen closed day | ❌ | ❌ | ✅ |

### Inputs/Outputs
- ✏️ **Manual (Accountant+)**: Mixes produced, actual units/packets, indirect costs (diesel, firewood, electricity, fuel)
- 🤖 **Auto**: Opening stock (from previous closing), ingredient costs (from Inventory), expected yields, variance calculations, P&L calculations, cost allocations
- **Output**: Production batches, P&L per mix, opening/closing stock, daily production summary

### Business Rules
1. **Product Configuration (✏️ Super Admin Editable)**:
   - Product names, aliases, titles
   - Selling prices (Bread: KES 60, KDF: KES 100, Scones: KES 50, Bread Rejects: KES 50)
   - Variance ranges (KDF: 98-107, Bread/Scones: fixed output)
   - Sub-product pricing (Bread Rejects: variable, default KES 50)
2. **Variance Tracking**: 
   - KDF: Variable output 98-107 packets (✏️ range adjustable by Super Admin)
   - Bread: Fixed output + Rejects sub-product
   - Scones: Fixed output
3. **Bread Rejects Handling**:
   - Count toward total production
   - Sold at reduced price (default KES 50, ✏️ Super Admin editable)
   - Tracked separately in dispatch and sales
   - Same packaging cost (KES 3.3/bag)
4. **Indirect Cost Allocation**: Daily indirect costs divided across all batches proportionally by total_cost
5. **Packaging Auto-deduction**: 
   - Bread: 1 bag per loaf (132 loaves = 132 bags @ KES 3.3 = KES 435.60)
   - Bread Rejects: 1 bag per loaf @ KES 3.3
   - KDF: 1 bag per packet (107 packets = 107 bags @ KES 3.3 = KES 353.10)
   - Scones: 1 bag per packet (102 packets = 102 bags @ KES 3.3 = KES 336.60)
   - Django signal deducts bags from Inventory when ProductionBatch saved
6. **Opening Product Stock**: 🤖 Auto-calculated from previous day's closing product stock
7. **Closing Product Stock**: 🤖 Auto-calculated = Opening + Production - Dispatched + Returns
8. **Stock Reconciliation Rule (What Comes In Must Go Out - Enhanced)**:
   ```
   INVENTORY (Raw Materials):
   Opening Stock + Purchases = Usage in Production + Damage/Wastage + Closing Stock
   
   PRODUCTS (Finished Goods):
   Opening Stock + Production = Dispatched - Returns + Damage/Expired + Closing Stock
   
   DISPATCH/SALES:
   What Goes Out (Dispatch) = Sales + Returns
   ```
   
   **Damage/Wastage Tracking:**
   - **New Model: StockDamage** (tracks all losses separately)
     ```python
     StockDamage:
         item (FK - InventoryItem or Product),
         item_type (INVENTORY/PRODUCT),
         quantity,
         damage_reason (SPOILAGE/SPILL/EXPIRED/CONTAMINATION/PEST/THEFT/BREAKAGE/OTHER),
         damage_date,
         value_lost (KES - calculated),
         recorded_by,
         approved_by (FK - User, null=True),
         approval_required (bool - True if > KES 500),
         is_approved (bool),
         notes,
         created_at
     ```
   - **Approval Workflow**:
     - Accountant+ can record damage
     - CEO must approve if value > KES 500
     - Unapproved damages flagged in reconciliation report
   - **Damage Reasons**:
     - SPOILAGE: Food gone bad, mold
     - SPILL: Liquid ingredients spilled during handling
     - EXPIRED: Past best-before date
     - CONTAMINATION: Cross-contamination, foreign objects
     - PEST: Rodent/insect damage
     - THEFT: Missing stock (suspected theft)
     - BREAKAGE: Dropped, crushed products
     - OTHER: Specify in notes
   - **Variance Alert**: If variance > 5% after accounting for damages → Investigation
   - **Monthly Report**: Total damages by category, trends, prevention recommendations
9. **Book Closing**: At 9PM daily, `is_closed=True`, Accountant locked out (only CEO/Admin can edit)
10. **Time-Aware Permissions** (Defense-in-Depth):
    ```python
    def can_edit_production(user, production_date):
        if production_date < timezone.now().date():
            # Past date
            if user.role in ['CEO', 'ADMIN']:
                return True  # CEO/Admin can always edit
            elif user.role == 'ACCOUNTANT' and timezone.now().hour < 21:
                return True  # Accountant can edit before 9PM
            else:
                return False  # Locked after 9PM for Accountant
        return True  # Today's production - anyone authorized can edit
    ```
    - **Hybrid Approach**: Cron closes books at 9PM + Permission layer prevents late edits
    - **Why Both?**: Cron ensures reports go out, permissions prevent accidental edits if cron fails
11. **Next Day Opening**: When new DailyProduction created → opening_product_stock auto-loads from previous closing_product_stock
12. **Auto-deduction**: When ProductionBatch saved → Django signal deducts ingredients + packaging bags from Inventory (raw materials)

---

## 💰 4. Sales App

### Features
- **Strong FK**: Dispatch → Returns (1-to-1)
- **Permission Level**: Accountant dispatches, Salesmen view their own, Admin views all
- **Mixed Product Dispatch**: Most dispatches contain 2-3 products (Bread + KDF + Scones)
- **Multiple Recipient Types**: Salesmen, Schools (students), Depots, Others (adjustable)
- Expected vs Actual sales tracking per product
- **Immediate deficit alerts**

### Models
```python
Salesperson: 
    user (FK - optional, some may not have login), 
    name, 
    salesperson_type (SALESMAN/SCHOOL/DEPOT/DISTRIBUTOR/OTHER),
    
    # Commission Structure (KES per unit)
    commission_rate_bread (KES per unit), 
    commission_rate_kdf (KES per unit),
    commission_rate_scones (KES per unit),
    
    # Performance Targets
    sales_target (KES - e.g., 35,000),
    target_commission_rate (% - e.g., 7% above target),
    
    # Banking Details
    bank_name,
    account_number,
    mpesa_number,
    
    is_active (bool),
    created_by, created_at, updated_by, updated_at

Dispatch: 
    date, 
    salesperson (FK), 
    dispatch_number (unique),
    crates_dispatched (total),
    is_returned (bool),
    dispatched_by (FK to User - Accountant),
    created_at

DispatchItem: 
    dispatch (FK), 
    product (FK), 
    
    # Dispatch Details
    units_dispatched (loaves for Bread, packets for KDF/Scones),
    cost_per_unit (KES - from Production),
    total_expected_revenue (units × selling_price),
    
    created_at

SalesReturn: 
    dispatch (OneToOne), 
    return_date,
    crates_returned,
    crates_deficit,
    
    # Banking & Reconciliation
    expected_banking (KES - total expected from dispatch),
    actual_banking (KES - cash/transfer received),
    banking_method (CASH/BANK_TRANSFER/MPESA),
    banking_reference,
    
    # Deficit Tracking (Sheet 12)
    revenue_deficit (KES - expected - actual),
    deficit_reason (SHORTAGE/DAMAGE/THEFT/EXPIRED/OTHER),
    deficit_notes,
    deficit_alert_sent (bool),
    
    # Commission Calculation (Sheet 13)
    total_sales_value (KES),
    sales_target (KES - from Salesperson),
    sales_above_target (🤖 Auto = total_sales_value - sales_target if positive, else 0),
    target_commission_rate (% - from Salesperson),
    commission_on_target (🤖 Auto = sales_above_target × target_commission_rate),
    commission_per_unit_bread (KES),
    commission_per_unit_kdf (KES),
    commission_per_unit_scones (KES),
    total_commission_earned (🤖 Auto = sum of all commissions),
    commission_paid (KES),
    commission_payment_status (PENDING/PAID/PARTIAL),
    
    is_finalized (bool),
    returned_by (FK to User),
    created_at, updated_at

SalesReturnItem: 
    sales_return (FK), 
    product (FK),
    
    # Returns
    units_returned,
    cost_per_unit (KES),
    total_returns_value (units_returned × cost_per_unit),
    
    # Sales
    units_sold (dispatched - returned),
    selling_price_per_unit (KES),
    gross_sales (units_sold × selling_price_per_unit),
    
    # Commission
    commission_per_unit (KES),
    total_commission (units_sold × commission_per_unit),
    
    # Net
    net_sales_after_commission (gross_sales - total_commission),
    
    created_at

DailySales: 
    date, 
    
    # Dispatch Summary
    total_dispatches,
    total_dispatched_value (KES),
    
    # Returns Summary
    total_actual_revenue (KES),
    revenue_deficit (KES),
    crate_deficit,
    
    # Product Breakdown
    bread_dispatched, bread_sold, bread_returned,
    kdf_dispatched, kdf_sold, kdf_returned,
    scones_dispatched, scones_sold, scones_returned,
    
    is_closed (bool), 
    closed_by (FK to User), 
    closed_at,
    created_by, created_at, updated_by, updated_at
```

### Dispatch Workflow

**Step 1: Accountant Creates Dispatch** (✏️ Manual)
```
Salesperson: John Doe (SALESMAN)
Products dispatched:
  - Bread: 50 loaves @ KES 32 cost = KES 1,600 expected @ KES 60 selling = KES 3,000
  - KDF: 30 packets @ KES 59.52 cost = KES 1,785.60 expected @ KES 60 selling = KES 1,800
  - Scones: 20 packets @ KES 31.04 cost = KES 620.80 expected @ KES 60 selling = KES 1,200
Crates: 5 crates dispatched
Total Expected Revenue: KES 6,000
```

**Step 2: Salesman Returns** (✏️ Manual entry by Accountant)
```
Returns:
  - Bread: 5 loaves returned, 45 sold
  - KDF: 3 packets returned, 27 sold
  - Scones: 2 packets returned, 18 sold
Crates: 5 returned, 0 deficit
Cash: KES 5,400 returned
```

**Step 3: System Calculates** (🤖 Auto)
```
BREAD:
  - Sold: 45 loaves × KES 60 = KES 2,700
  - Commission: 45 × KES 5 = KES 225
  - Net Sales: KES 2,700 - KES 225 = KES 2,475

KDF:
  - Sold: 27 packets × KES 60 = KES 1,620
  - Commission: 27 × KES 5 = KES 135
  - Net Sales: KES 1,620 - KES 135 = KES 1,485

SCONES:
  - Sold: 18 packets × KES 60 = KES 1,080
  - Commission: 18 × KES 5 = KES 90
  - Net Sales: KES 1,080 - KES 90 = KES 990

TOTALS:
  - Gross Sales: KES 5,400
  - Per-unit Commission: KES 450
  - Net Sales: KES 4,950

DEFICIT TRACKING (Sheet 12):
  - Expected Banking: KES 6,000
  - Actual Banking: KES 5,400
  - Revenue Deficit: KES 600
  - Alert: ⚠️ Immediate notification sent

COMMISSION CALCULATION (Sheet 13):
  - Total Sales: KES 5,400
  - Sales Target: KES 35,000
  - Below Target: No additional commission
  - Per-unit Commission: KES 450 (earned)
  - Commission Status: PENDING payment
```

### Permission Matrix
| Action | Salesman | Accountant | Admin/CEO |
|--------|----------|------------|-----------|
| View own dispatches | ✅ | ✅ | ✅ |
| View all dispatches | ❌ | ✅ | ✅ |
| Create dispatch | ❌ | ✅ | ✅ |
| Edit dispatch (before return) | ❌ | ✅ | ✅ |
| Record return | ❌ | ✅ | ✅ |
| Edit return (after finalized) | ❌ | ❌ | ✅ |

### Deficit & Commission Examples (From Sheets 12 & 13)

**Example 1: Deficit Case (Sheet 12)**
```
Salesperson: Okiya (Depot)
Date: 15/09/2025

Expected Banking:       KES 45,000
Actual Banking:         KES 42,500 (M-Pesa)
Deficit:                KES 2,500

Reason: Expired Stock (10 loaves Bread)
Notes: "Some loaves expired during transport to depot"
Alert Sent: ✓ Yes (to CEO + Accountant)
Status: Under Investigation
```

**Example 2: High Performer with Bonus Commission (Sheet 13)**
```
Salesperson: John Doe (Salesman)
Date: 20/09/2025

Sales Performance:
  - Total Sales: KES 48,000
  - Sales Target: KES 35,000
  - Above Target: KES 13,000 ✓

Commission Calculation:
  1. Per-unit Commission:
     - Bread: 50 loaves × KES 5 = KES 250
     - KDF: 40 packets × KES 5 = KES 200
     - Scones: 30 packets × KES 5 = KES 150
     - Subtotal: KES 600

  2. Bonus Commission (7% above target):
     - Sales above target: KES 13,000
     - Bonus rate: 7%
     - Bonus earned: KES 13,000 × 7% = KES 910

  3. Total Commission:
     - Per-unit: KES 600
     - Bonus: KES 910
     - TOTAL: KES 1,510

Banking Details:
  - Expected: KES 48,000
  - Actual: KES 48,000 (Bank Transfer)
  - Deficit: KES 0 ✓

Payment Status:
  - Commission Earned: KES 1,510
  - Commission Paid: KES 1,510 (via M-Pesa)
  - Payment Date: 30/09/2025
  - Status: PAID ✓
```

**Example 3: Multiple Issues (Combined Sheets 12 & 13)**
```
Salesperson: Edwardo (Distributor)
Date: 25/09/2025

Dispatch:
  - Bread: 80 loaves × KES 60 = KES 4,800
  - KDF: 60 packets × KES 60 = KES 3,600
  - Expected Total: KES 8,400

Returns:
  - Bread returned: 5 loaves
  - KDF returned: 3 packets
  - Damaged: 2 loaves (not sellable)

Sales:
  - Bread sold: 73 loaves (80 - 5 - 2 damaged)
  - KDF sold: 57 packets
  - Actual Sales: KES 7,800

Deficit Analysis:
  - Expected Banking: KES 8,400
  - Actual Banking: KES 7,200
  - Revenue Deficit: KES 600
  - Breakdown:
    • Damaged stock: KES 120 (2 loaves)
    • Shortage: KES 480 (unexplained)
  - Alert: ⚠️ IMMEDIATE (shortage > KES 300)

Commission Calculation:
  - Sales Total: KES 7,800
  - Target: KES 35,000
  - Status: Below target (no bonus)
  - Per-unit Commission:
    • Bread: 73 × KES 5 = KES 365
    • KDF: 57 × KES 5 = KES 285
    • Total: KES 650
  - Commission Status: PENDING (awaiting deficit resolution)
```

### Deficit Alert System (Sheet 12 Integration)

**Automatic Alerts Triggered When:**
1. Revenue deficit > KES 0 → Email to Accountant
2. Revenue deficit > KES 500 → Email to Accountant + CEO
3. Crate deficit > 0 → Immediate alert (SMS + Email)
4. Pattern detection: Same salesperson 3+ deficits in month → Flag for review

**Deficit Report:**
```
Monthly Deficit Summary (September 2025)
─────────────────────────────────────
Total Deficits: KES 15,200
Number of Incidents: 8
Affected Salespeople: 5

Top Deficits:
1. Okiya Depot: KES 2,500 (Expired stock)
2. Edwardo: KES 600 (Shortage + Damage)
3. Mary: KES 450 (Banking error - resolved)

Action Required: Investigation on Okiya depot storage
```

### Commission Report (Sheet 13 Integration)

**Monthly Commission Summary (September 2025):**
```
Total Sales Staff: 12
Total Sales: KES 540,000
Average Sales/Person: KES 45,000

Commission Breakdown:
─────────────────────────────────────
Per-unit Commission:     KES 8,200
Bonus Commission (7%):   KES 3,150
TOTAL EARNED:            KES 11,350

Payment Status:
  - Paid: KES 9,800 (10 staff)
  - Pending: KES 1,550 (2 staff - deficits under review)

Top Performers:
1. John Doe: KES 1,510 (Sales: KES 48,000)
2. Jane Smith: KES 1,420 (Sales: KES 46,500)
3. Peter Omondi: KES 1,100 (Sales: KES 42,000)
```

### Inputs/Outputs
- ✏️ **Manual (Accountant)**: 
  - Dispatch: Select salesperson/school/depot, add products (Bread/KDF/Scones), quantities, crates
  - Return: Units returned per product, crates returned, cash amount, crates deficit
- 🤖 **Auto**: 
  - Expected revenue calculations
  - Units sold (dispatched - returned)
  - Gross sales per product
  - Commission calculations per product
  - Net sales after commission
  - Revenue deficit alerts (immediate)
  - Crate deficit alerts
- **Output**: 
  - Dispatch records with mixed products
  - Detailed sales performance per product
  - **Deficit alerts** (revenue + crates)
  - Commission reports per salesperson
  - Product-level sales analysis

---

## 📊 5. Accounting App

### Features
- Invoice generation
- **P&L per mix** (daily auto-gen)
- Profit margins & percentages
- Connected to Payroll

### Models
```python
Invoice: invoice_number, date, customer_name, dispatch (FK), subtotal, tax, total (KES), paid
InvoiceItem: invoice (FK), product (FK), quantity, unit_price, total
MixProfitLoss: date, mix (FK), batches_produced, packets_produced, total_cost,
               expected_revenue, actual_revenue, gross_profit, gross_margin (%)
```

### Inputs/Outputs
- ✏️ **Manual**: Invoice details
- 🤖 **Auto**: P&L per mix, revenue/cost data
- **Output**: Invoices, P&L reports, financial summaries

---

## 📄 6. Reports App

### Report Storage Strategy

**Key Concept:** Books are closed daily → Data is permanent → Store once, view many times

**Why Store Reports?**
- ✅ Books locked at 9PM (data won't change)
- ✅ Fast retrieval (no recalculation)
- ✅ Historical audit trail
- ✅ Can re-send emails anytime
- ✅ Secure access (requires login)

### Email Strategy: Link to Report (Not Full Content)

**Problem:** Sending full HTML tables in email is clunky, charts don't work

**Solution:** Email contains **summary + secure link** to view full report in app

**Email Example:**
```
Subject: Daily P&L Report - October 25, 2025

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 DAILY BOOKS CLOSED AT 9:00 PM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Quick Summary:
Total Sales:        KES 456,000
Production Cost:    KES 285,000
Net Profit:         KES 171,000
Profit Margin:      37.5%

Product Performance:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bread:    KES 85,000 profit
KDF:      KES 52,000 profit  
Scones:   KES 34,000 profit

📊 View Full Report (Tables + Interactive Charts):
https://chesanto.railway.app/reports/daily/2025-10-25/

🔒 Report is LOCKED. Only Admin can edit.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Chesanto Bakery Management System
```

**Benefits:**
- ✅ Lightweight email (no heavy HTML tables)
- ✅ Charts work (rendered in browser when clicked)
- ✅ Secure (requires login to view)
- ✅ Mobile-friendly (user can zoom/interact)
- ✅ Can forward link to authorized users

### Schedule
- **Daily**: 9:00 PM (books close, report generated, email sent)
- **Weekly**: Sunday 8:00 AM
- **Monthly**: 1st of month 12:00 AM

### Features
- **Stored in DB** (generate once, view many times)
- **Email contains:** Summary + link (not full content)
- **Report page:** Tables (pre-calculated) + Charts (Chart.js renders on-demand)
- CEO + Developer get ALL reports

### Models
```python
DailyReport: 
    date, 
    report_url (e.g., '/reports/daily/2025-10-25/'),
    
    # Overall P&L (STORED - calculated when books close)
    sales_bread, sales_kdf, sales_scones, total_sales (KES),
    production_cost_bread, production_cost_kdf, production_cost_scones, total_production_costs (KES),
    gross_profit (KES),
    packaging_material_cost (KES), commission_total (KES),
    net_profit (KES), profit_margin (%),
    
    # Product-specific P&L (STORED)
    bread_net_sales, bread_production_cost, bread_gross_profit, bread_packaging, bread_commission, bread_net_profit (KES),
    kdf_net_sales, kdf_production_cost, kdf_gross_profit, kdf_packaging, kdf_commission, kdf_net_profit (KES),
    scones_net_sales, scones_production_cost, scones_gross_profit, scones_packaging, scones_commission, scones_net_profit (KES),
    
    # Detailed breakdown (JSON - STORED)
    production_summary (JSON),  # All batches with costs
    sales_summary (JSON),       # All dispatches/returns
    opening_stock (JSON),       # Stock levels at start
    closing_stock (JSON),       # Stock levels at end
    
    # Metadata
    revenue_deficit (KES), crate_deficit,
    is_finalized (bool - always True for daily reports),
    generated_at (timestamp),
    emailed_to (JSON - list of recipients),
    
    created_by, created_at, updated_by, updated_at
             
WeeklyReport: 
    week_start_date, week_end_date,
    report_url (e.g., '/reports/weekly/2025-10-20/2025-10-26/'),
    
    # Same structure as DailyReport (aggregated over 7 days)
    # ... all fields from DailyReport ...
    
    # Additional weekly metrics
    best_day (date), worst_day (date),
    avg_daily_sales (KES), avg_daily_profit (KES),
    
    is_finalized, generated_at, emailed_to

MonthlyReport: 
    month, year,
    report_url (e.g., '/reports/monthly/2025/10/'),
    
    # Same structure as DailyReport (aggregated over month)
    # ... all fields from DailyReport ...
    
    # Additional monthly metrics
    best_selling_product, 
    worst_performing_day, 
    best_salesperson,
    total_working_days,
    avg_daily_sales (KES),
    avg_daily_profit (KES),
    
    is_finalized, generated_at, emailed_to

ReportRecipient: 
    user (FK), 
    receives_daily (bool - default True), 
    receives_weekly (bool - default True), 
    receives_monthly (bool - default True)
```

### Report Viewing Flow

**Step 1: Report Generated** (9:00 PM)
```python
# management/commands/close_daily_books.py

# 1. Close books
DailyProduction.objects.filter(date=today).update(is_closed=True)
DailySales.objects.filter(date=today).update(is_closed=True)

# 2. Calculate and STORE all values
daily_report = DailyReport.objects.create(
    date=today,
    report_url=f'/reports/daily/{today}/',
    total_sales=calculate_total_sales(today),
    net_profit=calculate_net_profit(today),
    # ... store ALL calculated values ...
    production_summary=get_production_summary_json(today),
    sales_summary=get_sales_summary_json(today),
    is_finalized=True,
    generated_at=timezone.now()
)

# 3. Send email with link (not full content)
send_mail(
    subject=f'Daily P&L Report - {today}',
    message=generate_email_summary(daily_report),  # Summary + link
    recipient_list=get_report_recipients('daily')
)
```

**Step 2: User Clicks Link**
```
URL: https://chesanto.railway.app/reports/daily/2025-10-25/

Page displays:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DAILY P&L REPORT - October 25, 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Overall P&L Table - from stored data]
[Product-Specific Tables - from stored data]
[Interactive Charts - Chart.js renders from stored data]

[Export to CSV] [Print] [Email to Others]
```

**Step 3: Charts Render** (Real-time from stored data)
```javascript
// Report page loads stored data via API
fetch('/api/reports/daily/2025-10-25/')
  .then(response => response.json())
  .then(data => {
    // Chart.js renders interactive charts from stored data
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Bread', 'KDF', 'Scones'],
        datasets: [{
          label: 'Net Profit (KES)',
          data: [data.bread_net_profit, data.kdf_net_profit, data.scones_net_profit]
        }]
      }
    });
  });
```

### Report Sections (In Web View)

#### 1. Overall Performance (P&L Statement)
**Data:** Pre-calculated, stored in DailyReport model  
**Display:** HTML table (fast rendering)

```
Sales Bread                     KES XXX
Sales KDF                       KES XXX
Sales Scones                    KES XXX
─────────────────────────────────────
TOTAL SALES                     KES XXX

Production Cost Bread           KES XXX
Production Cost KDF             KES XXX
Production Cost Scones          KES XXX
─────────────────────────────────────
TOTAL PRODUCTION COSTS          KES XXX

GROSS PROFIT                    KES XXX
Less: Packaging Material        KES XXX
Less: Commission                KES XXX
─────────────────────────────────────
NET PROFIT                      KES XXX
```

#### 2. Product-Specific Performance (Bread/KDF/Scones)
**Data:** Pre-calculated, stored in DailyReport model  
**Display:** HTML tables + Bar charts (Chart.js)

```
BREAD PERFORMANCE
─────────────────────────────────────
Total Net Sales                 KES XXX
Total Production Cost           KES XXX
Gross Profit/Loss               KES XXX
Less: Packaging Material        KES XXX
Less: Commission                KES XXX
─────────────────────────────────────
NET PROFIT (Bread)              KES XXX

[Interactive Bar Chart - Bread Profit Breakdown]
```

#### 3. Production Summary
**Data:** Stored in `production_summary` JSON field  
**Display:** Detailed table + Line chart (trend)

- Direct/indirect costs per batch
- Packets produced per mix
- Cost per packet analysis

#### 4. Dispatch Summary
**Data:** Stored in `sales_summary` JSON field  
**Display:** Table + Pie chart (distribution)

- Products/crates dispatched
- Returns and deficits
- Salesperson performance

#### 5. Sales Summary
**Data:** Stored in `sales_summary` JSON field  
**Display:** Table + Comparison chart

- Expected vs Actual revenue
- Variance analysis
- Commission breakdown

#### 6. Stock Movement
**Data:** Stored in `opening_stock` and `closing_stock` JSON fields  
**Display:** Table with reconciliation check

- Opening → Production → Sales → Returns → Closing
- Variance alerts highlighted

### Inputs/Outputs
- 🤖 **Auto**: All data from Production, Sales, Accounting (calculated at 9PM)
- **Output**: 
  - Stored report (database)
  - Email with summary + link
  - Web page with tables + interactive charts
  - CSV export option
  - Print-friendly view

---

## 📈 7. Analytics App

### Purpose
**Real-time dashboard** for live data analysis (not locked like Reports)

**Difference from Reports:**
| Feature | Reports App | Analytics App |
|---------|-------------|---------------|
| **Data** | Stored (locked books) | Real-time queries |
| **URL** | `/reports/daily/2025-10-25/` | `/analytics/dashboard/` |
| **Editable** | ❌ Locked | Shows current state |
| **Email Link** | ✅ Yes | ❌ No |
| **Use Case** | Historical analysis | Live monitoring |

### Charts (Chart.js - FREE & Open Source)

**Why Chart.js?**
- ✅ Completely FREE (MIT License)
- ✅ Lightweight (11kb gzipped - auto-compressed when downloading from CDN)
- ✅ Beautiful animations
- ✅ Responsive by default
- ✅ 8 chart types built-in
- ✅ No dependencies
- ✅ Extensive documentation
- ✅ Works in browser (not in email - emails get links to web view)

**Package:** `django-chartjs==2.3.0` (Django wrapper)

**Alternative (If Needed):** Plotly (also FREE, more interactive features)

### Chart Interactivity (Chart.js Default Features)

**1. Hover Tooltips**
- Show exact values on hover
- Example: Hover on bar → "Bread: KES 45,000 (38% of total profit)"
- Multi-line tooltips for grouped charts
- Custom formatting: Currency (KES), percentages, units

**2. Click Actions**
- Click product bar → Drill down to daily breakdown
- Click deficit point → Show deficit details (salesperson, reason, date)
- Click inventory bar (red) → Show reorder recommendation
- Double-click chart → Full-screen view (Phase 2)

**3. Legend Toggle**
- Click legend item → Hide/show data series
- Example: Click "Bread" in legend → Hide Bread data, recalculate scale
- Useful for comparing specific products

**4. Zoom/Pan (Mobile)**
- Pinch to zoom on touch devices
- Two-finger pan to navigate zoomed chart
- Reset zoom button

**5. Export Options**
- Download as PNG (right-click → Save Image)
- Copy to clipboard (for reports/presentations)
- Print-optimized view

### Animations (Chart.js Default)

**1. Initial Load Animations**
- **Bar Charts**: Grow from bottom to top (800ms, easeOutQuart)
- **Line Charts**: Draw from left to right (1000ms, easeInOutQuad)
- **Pie/Doughnut Charts**: Rotate in clockwise (800ms, easeOutBounce)
- **Staggered**: Bars animate sequentially (not all at once)

**2. Data Update Animations**
- Smooth transitions when filters change (400ms)
- Example: Change date range → bars smoothly adjust heights
- Color transitions for threshold changes (red ↔ green)

**3. Hover Effects**
- Scale animation on hover (200ms, grow 5%)
- Subtle shadow on focused element
- Tooltip fade-in (150ms)

**4. Performance Optimization**
- Animations disabled if > 1000 data points (prevents lag)
- Reduced motion for accessibility (respects OS settings)
- Hardware acceleration (CSS transforms)

**5. Animation Configuration**
```javascript
options: {
  animation: {
    duration: 800,        // 0.8 seconds
    easing: 'easeOutQuart',  // Smooth deceleration
    delay: function(context) {
      // Stagger bars: first bar 0ms, second bar 50ms, etc.
      return context.dataIndex * 50;
    },
    onComplete: function() {
      // Animation finished - enable full interactions
      console.log('Chart ready');
    }
  },
  hover: {
    animationDuration: 200  // Quick response
  },
  responsiveAnimationDuration: 0  // No animation on resize
}
```

#### Financial Charts
1. **Overall P&L** (Waterfall Chart)
   - Total Sales → Production Costs → Gross Profit → Packaging → Commission → Net Profit
   
2. **Product Performance Comparison** (Grouped Bar Chart)
   - Side-by-side comparison: Bread vs KDF vs Scones
   - Metrics: Sales, Production Cost, Gross Profit, Net Profit
   
3. **Profit Margins by Product** (Pie Chart)
   - Bread contribution to total profit
   - KDF contribution to total profit
   - Scones contribution to total profit

#### Operational Charts
4. **Inventory Levels** (Bar Chart)
   - Current stock vs reorder level
   - Color: Red (below reorder), Green (above)

5. **Production Trends** (Line Graph)
   - Daily packets produced over time (by product)
   - Overlay expected vs actual

6. **Expected vs Actual Sales** (Comparison Chart)
   - Side-by-side bars per product
   - Show variance percentage

7. **Deficits Tracking** (Trend Line)
   - Revenue deficits over time
   - Crate deficits over time

8. **Best/Worst Performers**
   - Products (by net profit)
   - Salespeople (by revenue)

### Dashboard Sections

**Section 1: Financial Overview**
- Overall P&L summary card
- Net profit trend (last 7 days)
- Product profit breakdown

**Section 2: Product Performance**
- Bread performance card (sales, costs, profit)
- KDF performance card
- Scones performance card

**Section 3: Operations**
- Inventory alerts
- Production efficiency
- Sales performance
- Deficit warnings

### Features
- Contextual colors (Red/Green/Blue)
- Animations
- Real-time data
- Date range filters
- Export charts (PNG/CSV)
- **Desktop-optimized** (complex data/graphs priority)
- **Mobile-friendly basics** (Bootstrap responsive where feasible)

### Inputs/Outputs
- 🤖 **Auto**: Data from Reports, Production, Sales, Inventory
- **Output**: Interactive dashboard, graphical insights, P&L visualizations, CSV exports

---

## 💼 8. Payroll App

### Dynamic Employee Management

**Super Admin Can (✏️ Fully Configurable):**
- ✅ **Add NEW Employees**: Unlimited capacity (currently 20+, can grow)
- ✅ **Add Custom Fields**: Via Django Admin (e.g., NHIF, NSSF, housing_allowance, transport_allowance)
- ✅ **Adjust Deduction Types**: Add statutory deductions (PAYE, NHIF, NSSF, pension)
- ✅ **Define Departments**: Group employees by department/role
- ✅ **Configure Payment Methods**: Add new payment channels (bank accounts, mobile money)
- ✅ **Deactivate Employees**: Soft delete (preserves payroll history)
- **Interface**: Django Admin + Custom forms

**Note:** Accountant is also an employee (CHE028 - Eddah Silungi, KES 38,000/month)

### Features
- Unlimited employee capacity (20+ currently, scalable)
- Multiple employee types (permanent staff, casual laborers, contractors)
- Flexible salary structures (monthly/daily/weekly/hourly)
- Custom deduction fields (statutory + company-specific)
- Automatic payroll calculations based on days/hours worked
- Casual laborer daily/weekly payment tracking
- Integration with Accounting (Direct Salaries expense category)
- Integration with Accounts app (User/Employee linkage for system access)
- **Permission Level**: Super Admin manages structure, Accountant processes payroll

### Models
```python
Employee:
    # Identification
    staff_number (e.g., CHE028, CHE001, ... CHE020+),
    user (FK - optional, not all employees need system login),
    full_name,
    id_number (National ID/Passport),
    mobile_number,
    email (optional),
    
    # Employment
    position (✏️ Super Admin editable - e.g., "Bakery Accountant/Supervisor", "Bread Production Supervisor"),
    department (✏️ Super Admin configurable - PRODUCTION/SALES/ADMIN/FINANCE/DISTRIBUTION),
    employee_type (PERMANENT_STAFF/CASUAL_LABORER/CONTRACT/INTERN),
    date_started,
    date_ended (nullable - for terminated employees),
    is_active (bool),
    
    # Compensation
    salary_type (MONTHLY/DAILY/WEEKLY/HOURLY),
    base_salary (KES - monthly or daily/hourly rate),
    
    # Statutory Deductions (✏️ Super Admin can add more fields)
    paye_applicable (bool),
    nhif_applicable (bool),
    nssf_applicable (bool),
    pension_applicable (bool),
    
    # Custom Fields (✏️ Super Admin editable via Django Admin)
    housing_allowance (KES, nullable),
    transport_allowance (KES, nullable),
    custom_field_1 (JSONField - for future flexibility),
    
    # Banking
    bank_name,
    account_number,
    mpesa_number,
    
    created_by, created_at, updated_by, updated_at

MonthlyPayroll:
    # Period
    month, year,
    payment_date,
    
    # Processing
    is_finalized (bool),
    finalized_by (FK to User),
    finalized_at,
    
    created_by, created_at, updated_by, updated_at

PayrollItem:
    payroll (FK),
    employee (FK),
    
    # Calculation Base
    days_in_month (e.g., 30, 31),
    days_worked (✏️ Accountant adjustable - for absences),
    hours_worked (for hourly employees),
    base_salary (KES - from Employee record),
    
    # Earnings (✏️ Accountant adjustable)
    housing_allowance (KES),
    transport_allowance (KES),
    overtime_pay (KES),
    bonus (KES),
    bonus_notes,
    
    # Statutory Deductions (🤖 Auto-calculated or ✏️ Manual)
    paye (KES - Pay As You Earn tax),
    nhif (KES - National Hospital Insurance Fund),
    nssf (KES - National Social Security Fund),
    pension (KES),
    
    # Other Deductions (✏️ Accountant adjustable)
    staff_loan_deduction (KES),
    advance_deduction (KES),
    other_deductions (KES),
    deduction_notes,
    
    # Totals (🤖 Auto-calculated)
    gross_salary (base × days_worked / days_in_month for monthly; hours × rate for hourly),
    total_allowances,
    total_statutory_deductions,
    total_other_deductions,
    net_salary (gross + allowances - all deductions + bonus),
    
    # Payment
    payment_status (PENDING/PAID/PARTIAL),
    amount_paid (KES),
    payment_method (CASH/BANK_TRANSFER/MPESA/CHEQUE),
    payment_reference,
    paid_at,
    
    created_by, created_at, updated_by, updated_at

CasualLabor:
    # Daily/Weekly tracking for casual laborers
    date,
    employee (FK - Employee with employee_type=CASUAL_LABORER),
    
    # Work Details
    hours_worked (default: 8 for full day),
    task_description (e.g., "Packaging", "Cleaning", "Loading"),
    location (e.g., "Factory", "Depot"),
    daily_rate (KES - from Employee record or custom for task),
    hourly_rate (KES - if paid by hour),
    
    # Payment (🤖 Auto or ✏️ Manual)
    amount_due (hours × hourly_rate OR daily_rate),
    is_paid (bool),
    payment_method (CASH/MPESA),
    paid_at,
    paid_by (FK to User),
    
    # Weekly Aggregation (for reporting)
    week_ending (calculated from date),
    
    notes,
    created_by, created_at, updated_by, updated_at
```

### Example Data (From Screenshots - Sample of 20+ Employees)

**Permanent Staff (Sample - 4 shown, 20+ total):**
```
CHE028 - Eddah Silungi
Position: Bakery Accountant/Supervisor
Salary: KES 38,000/month
Started: 01/09/2025
September 2025: 30 days → Net Salary: KES 38,000
Note: Also system Accountant user

CHE001 - Elizabeth Ichelai (ID: 32543030)
Position: Bakery Accountant
Salary: KES 13,000/month
Started: 08/09/2024
September 2025: 30 days → Net Salary: KES 13,000

CHE002 - Martin Ikapel (ID: 9955897)
Position: Bread Production Supervisor
Salary: KES 12,000/month
Started: 08/10/2024
September 2025: 30 days → Net Salary: KES 6,000 (partial month or deductions)

CHE003 - Gabriel Imoo (ID: 7421512)
Position: KDF Production Supervisor
Salary: KES 15,000/month
Started: 08/10/2024
September 2025: 30 days → Net Salary: KES 15,000

... [16+ more permanent staff]
Total Permanent Staff: 20+ (expandable, no limit)
```

**Casual Laborers (September 2025 - Sample):**
```
Martina Achogo (ID: 13170785)
Task: Packaging/General Labor
Payment Dates:
  - 06/09: KES 1,200 (full day)
  - 13/09: KES 1,200 (full day)
  - 20/09: KES 1,200 (full day)
  - 27/09: KES 1,200 (full day)
  - 30/09: KES 400 (partial day or different task)
Total September: KES 5,200
Payment Method: Cash

Irine Nyanweso
Task: Packaging/General Labor
Payment Dates:
  - 06/09: KES 1,200 (full day)
  - 13/09: KES 1,200 (full day)
  - 20/09: KES 1,200 (full day)
  - 27/09: KES 1,200 (full day)
  - 30/09: KES 400 (partial day)
Total September: KES 5,200
Payment Method: Cash

... [Multiple other casual laborers]

Casual Labor Pattern:
  - Typical Rate: KES 1,200/day (8 hours)
  - Partial Day: KES 400-600 (varies by hours)
  - Payment: Weekly or bi-weekly (cash/M-Pesa)
  - Tasks: Packaging, cleaning, loading, general labor
```

### Payroll Workflow (Permanent Staff)

**Step 1: Monthly Payroll Creation** (✏️ Accountant)
```
Create payroll for September 2025
Payment Date: 30/09/2025
Days in month: 30
```

**Step 2: Add/Review Employees** (🤖 Auto-populated from active permanent staff)
```
Load all 20+ active permanent staff
For each employee:
  - Base salary from Employee record
  - Days worked: default = days in month (adjustable for absences)
  - Allowances: housing, transport (from Employee record)
  - Statutory deductions: PAYE, NHIF, NSSF (auto-calculated or manual)
  - Other deductions: loans, advances (default = 0, adjustable)
  - Bonus: default = 0 (adjustable)
```

**Step 3: Adjustments** (✏️ Accountant)
```
Example: Martin Ikapel (CHE002)
  - Base: KES 12,000
  - Days worked: 15/30 (started mid-month or 15 days absent)
  - Gross: KES 6,000 (12,000 × 15/30)
  - Deductions: KES 0
  - Net: KES 6,000

Example with Statutory Deductions: Employee earning KES 50,000
  - Gross: KES 50,000
  - PAYE: KES 6,500 (auto-calculated based on tax brackets)
  - NHIF: KES 1,700
  - NSSF: KES 1,080
  - Staff Loan: KES 5,000
  - Net: KES 35,720
```

**Step 4: Finalize** (🤖 Auto-generates accounting entries)
```
Payroll finalized → Creates expense in Accounting (Direct Salaries category)
Total Payroll (20+ employees): KES [calculated sum]
Posted to Accounting as Direct Salary expense
Generate payslips (PDF) for each employee
```

### Casual Labor Workflow

**Step 1: Daily/Weekly Recording** (✏️ Accountant or Supervisor)
```
Date: 06/09/2025
Employee: Martina Achogo (Casual)
Task: Packaging
Hours: 8 hours (full day)
Rate: KES 1,200/day (or KES 150/hour)
Amount Due: KES 1,200
Payment Status: Pending
```

**Step 2: Weekly Payment** (✏️ Accountant)
```
Week Ending: 10/09/2025
Casual Laborers Summary:
  - Martina Achogo: 5 days × KES 1,200 = KES 6,000
  - Irine Nyanweso: 4 days × KES 1,200 = KES 4,800
  - [Others...]
Total: KES [sum]

Payment Method: Cash/M-Pesa
Mark all as Paid
```

**Step 3: Monthly Integration** (🤖 Auto)
```
Total Casual Labor (September): KES 45,000
Posted to Accounting as Direct Salaries expense (separate line item)
Appears in monthly reports
```

### Casual Labor Reporting

**Weekly Summary:**
```
Week Ending: 10/09/2025
─────────────────────────────────
Martina Achogo:    5 days  KES 6,000  ✓ Paid
Irine Nyanweso:    4 days  KES 4,800  ✓ Paid
[Other casuals...]
─────────────────────────────────
Total Labor Days:  35
Total Cost:        KES 42,000
Average/Day:       KES 1,200
```

**Monthly Summary:**
```
September 2025 Casual Labor
─────────────────────────────────
Total Laborers:    12 individuals
Total Days Worked: 156 days
Total Cost:        KES 187,200
Average/Person:    KES 15,600
Most Frequent:     Martina Achogo (22 days)
─────────────────────────────────
Tasks Breakdown:
  - Packaging:     120 days (77%)
  - Cleaning:      20 days (13%)
  - Loading:       16 days (10%)
```

**Step 5: Record Payments** (✏️ Accountant marks as paid)
```
Employee by employee (20+ employees):
  - Payment method: Bank Transfer / Cash / M-Pesa
  - Amount paid: KES XXX
  - Reference: Transaction ID / Receipt #
  - Mark as PAID
```

**Step 6: Generate Reports** (🤖 Auto)
```
- Individual payslips (PDF) for each employee
- Bank transfer file (CSV) for bulk payments
- M-Pesa payment list
- Monthly payroll summary
- Statutory deductions report (PAYE, NHIF, NSSF)
```

### Integration Points

**1. With Accounting App:**
- Finalized payroll → Creates Direct Salaries expense entry
- Permanent staff total: KES [sum of 20+ employees]
- Casual labor total: KES [sum of daily/weekly payments]
- Statutory deductions (PAYE, NHIF, NSSF) → Separate expense/liability entries
- Monthly total feeds into P&L reports

**2. With Accounts App:**
- Employee user accounts linked to Employee records (optional - not all 20+ employees need login)
- Accountant (CHE028 - Eddah) has both Employee record + User account
- Role-based permissions (Supervisor, Accountant, CEO, etc.)
- Contact information for payments (M-Pesa mobile numbers, bank accounts)

**3. With Reports App:**
- Payroll summary in monthly reports
- Staff cost analysis by department (Production vs Sales vs Admin vs Finance)
- Employee count trends (permanent vs casual)
- Casual labor cost trends over time
- Cost per employee analysis

### Permission Matrix
| Action | Production Staff | Accountant | Super Admin/CEO |
|--------|-----------------|------------|-----------------|
| View own payslip | ✅ | ✅ | ✅ |
| View all payroll | ❌ | ✅ | ✅ |
| Create payroll | ❌ | ✅ | ✅ |
| Adjust salaries | ❌ | ✅ | ✅ |
| Add deductions/bonus | ❌ | ✅ | ✅ |
| Finalize payroll | ❌ | ✅ | ✅ |
| Record payments | ❌ | ✅ | ✅ |
| **Add NEW employees** | ❌ | ❌ | ✅ |
| **Add custom fields (NHIF, etc.)** | ❌ | ❌ | ✅ |
| **Configure deduction types** | ❌ | ❌ | ✅ |

### Inputs/Outputs
- ✏️ **Manual (Super Admin)**: 
  - Add NEW employees (unlimited capacity, currently 20+)
  - Add custom fields (NHIF, NSSF, pension, allowances via Django Admin)
  - Configure deduction types and statutory requirements
  - Set salary structures and payment methods
- ✏️ **Manual (Accountant)**: 
  - Days/hours worked adjustments
  - Statutory deductions (PAYE, NHIF, NSSF - if not auto-calculated)
  - Other deductions (staff loans, advances)
  - Allowances (housing, transport - if not from Employee record)
  - Bonuses
  - Payment recording (method, reference)
  - Casual labor daily/weekly entries (task, hours, rate)
- 🤖 **Auto**: 
  - Gross salary calculations (pro-rata for partial months, hourly rates)
  - Statutory deductions (PAYE, NHIF, NSSF - based on brackets)
  - Net salary (gross + allowances - all deductions + bonus)
  - Accounting entries (Direct Salaries expense - separate for permanent/casual)
  - Payroll summaries (permanent + casual totals)
  - Weekly casual labor aggregation
- **Output**: 
  - Individual payslips (20+ permanent staff)
  - Bank transfer file (CSV for bulk payments)
  - M-Pesa payment list
  - Monthly payroll reports (permanent + casual breakdown)
  - Statutory deductions report (PAYE, NHIF, NSSF)
  - Casual labor weekly/monthly summaries
  - Department cost analysis
  - Casual labor summaries
  - Staff cost analysis
  - Payment schedules
  - Accounting integration (expense entries)

---

## ⚙️ Automation Strategy

### Railway Cron + Django Signals

**Why This Approach:**
- ⭐ **Zero additional packages** - Railway native feature + Django built-in
- ⭐ **Zero infrastructure** - No Redis, no message queues, no workers
- ⭐ **Zero additional cost** - Included in Railway
- ⭐ **Simple debugging** - Management commands run like any Django command
- ⭐ **Perfect for scheduled tasks** - Daily/weekly/monthly reports, book closing
- ⭐ **Perfect for immediate alerts** - Django signals fire instantly
- ⭐ **Easy maintenance** - Standard Django patterns

**What We're Using:**
1. **Railway Cron** → Scheduled tasks (reports, book closing, stock checks)
2. **Django Signals** → Immediate alerts (low stock, deficits, reconciliation)
3. **Django Email** → Built-in email sending (no external service)

---

### Railway Cron Configuration

**File:** `railway.json` (in project root)
```json
{
  "cron": [
    {
      "schedule": "0 20 * * *",
      "command": "python manage.py close_daily_books",
      "name": "Close Daily Books & Generate Report"
    },
    {
      "schedule": "0 8 * * 0",
      "command": "python manage.py generate_weekly_report",
      "name": "Weekly Report (Sunday 8AM)"
    },
    {
      "schedule": "0 0 1 * *",
      "command": "python manage.py generate_monthly_report",
      "name": "Monthly Report (1st 12AM)"
    },
    {
      "schedule": "0 8 * * *",
      "command": "python manage.py check_stock_levels",
      "name": "Daily Stock Level Check (8AM)"
    }
  ]
}
```

**Cron Schedule Format:** `minute hour day month day_of_week`
- `0 20 * * *` = Every day at 8:00 PM (20:00)
- `0 8 * * 0` = Every Sunday at 8:00 AM (0 = Sunday)
- `0 0 1 * *` = 1st of every month at midnight

---

### Django Management Commands

**1. Close Daily Books + Generate Report** (9:00 PM)
```bash
python manage.py close_daily_books
```
- Lock DailyProduction (is_closed=True)
- Lock DailySales (is_closed=True)
- Calculate all P&L metrics
- Store in DailyReport (database)
- Send email with link to report

**2. Weekly Report** (Sunday 8:00 AM)
```bash
python manage.py generate_weekly_report
```
- Aggregate last 7 days of DailyReports
- Store in WeeklyReport (database)
- Send email with link to report

**3. Monthly Report** (1st of month 12:00 AM)
```bash
python manage.py generate_monthly_report
```
- Aggregate last month's DailyReports
- Store in MonthlyReport (database)
- Include best/worst performers
- Send email with link to report

**4. Stock Level Check** (8:00 AM daily)
```bash
python manage.py check_stock_levels
```
- Check all inventory items
- Alert if stock < 7 days production
- Email summary to Accountant

---

### Django Signals (Immediate Alerts)

**Trigger:** Instant (when data changes)  
**No queue needed** - Runs synchronously in same request

```python
# Inventory Alert (Low Stock)
@receiver(post_save, sender=ProductionBatch)
def check_inventory_after_production(sender, instance, **kwargs):
    """Triggers immediately when batch saved"""
    for ingredient in instance.mix.ingredients:
        if ingredient.current_stock < ingredient.calculated_alert_level:
            send_mail(
                subject=f'⚠️ Low Stock: {ingredient.name}',
                message=f'Only {ingredient.current_stock} remaining',
                recipient_list=['accountant@chesanto.com']
            )

# Deficit Alert (High Revenue Loss)
@receiver(post_save, sender=SalesReturn)
def check_deficit_alert(sender, instance, **kwargs):
    """Triggers immediately when return saved"""
    if instance.revenue_deficit > 500:
        send_mail(
            subject=f'🚨 HIGH DEFICIT: {instance.salesperson.name}',
            message=f'Deficit: KES {instance.revenue_deficit}',
            recipient_list=['ceo@chesanto.com', 'accountant@chesanto.com']
        )

# Inventory Deduction (Auto-update Stock)
@receiver(post_save, sender=ProductionBatch)
def deduct_inventory(sender, instance, created, **kwargs):
    """Auto-deduct ingredients + packaging when batch created"""
    if created:
        for mix_ingredient in instance.mix.mixingredient_set.all():
            StockMovement.objects.create(
                item=mix_ingredient.ingredient.inventory_item,
                movement_type='PRODUCTION_USE',
                quantity=-mix_ingredient.quantity,
                reference_type='ProductionBatch',
                reference_id=instance.id
            )

# Stock Reconciliation (Daily Variance Check)
@receiver(post_save, sender=DailyProduction)
def check_stock_reconciliation(sender, instance, **kwargs):
    """Check if opening + production = dispatched + closing"""
    if instance.is_closed:
        expected_closing = (
            instance.opening_product_stock_bread + 
            instance.bread_produced - 
            instance.bread_dispatched + 
            instance.bread_returned
        )
        if expected_closing != instance.closing_product_stock_bread:
            variance = abs(expected_closing - instance.closing_product_stock_bread)
            if variance / expected_closing > 0.05:  # 5% threshold
                send_mail(
                    subject='⚠️ Stock Reconciliation Variance',
                    message=f'Bread variance: {variance} loaves (5%+)',
                    recipient_list=['accountant@chesanto.com']
                )
```

**Alert Types:**
- ✅ **Low stock** → Immediate (after production)
- ✅ **Deficit** → Immediate (after sales return)
- ✅ **Inventory deduction** → Immediate (after production)
- ✅ **Stock variance** → Immediate (at book closing)

---

## 🔐 System Configuration

### Alert Thresholds (Admin Configurable)

**Inventory Alerts:**
- **Default**: Alert when stock < 7 days of production
- **Calculation**: 
  ```python
  weekly_usage = sum(last_4_weeks_usage) / 4
  alert_threshold = weekly_usage × alert_threshold_days (default: 7)
  
  if current_stock < alert_threshold:
      send_alert()  # Email + Dashboard notification
  ```
- **Admin Override**: Super Admin can set custom threshold per item (e.g., Flour = 10 days, Salt = 14 days)

**Deficit Alerts:**
- Revenue deficit > KES 0 → Accountant
- Revenue deficit > KES 500 → Accountant + CEO
- Crate deficit > 0 → Immediate (SMS + Email)
- Pattern: Same salesperson 3+ deficits/month → Flag for review

**Stock Reconciliation Alerts:**
- Daily variance check at book closing (9PM)
- Inventory: Opening + Purchases ≠ Usage + Closing → Alert
- Products: Opening + Production ≠ Dispatched - Returns + Closing → Alert
- Variance > 5% → Immediate investigation required

---

## 💾 Backup & Recovery Strategy

### ⚠️ Railway File System Limitation
**Railway uses ephemeral/read-only file systems** - files saved locally are lost on restart/deploy.

**Solution:** Store backups in **DATABASE** (PostgreSQL has plenty of space) + **Email delivery**

### Database Backups (In-Database Storage)

**Model for Backup Storage:**
```python
DatabaseBackup:
    backup_date (date),
    backup_type (DAILY/MANUAL),
    
    # Compressed Data (stored as binary/text)
    backup_data (TextField - JSON compressed),
    backup_size (bytes),
    
    # Metadata
    tables_included (JSON - list of table names),
    record_counts (JSON - {"products": 15, "inventory": 42, ...}),
    
    # Email delivery
    emailed_to (email addresses - comma separated),
    email_sent_at (timestamp),
    
    created_by, created_at
```

**Backup Strategy:**
- **Retention**: Keep only **2 most recent daily backups** (avoid data overload)
- **Storage**: PostgreSQL database (as compressed JSON text)
- **Schedule**: Daily at 2:00 AM (Railway cron)
- **Auto-cleanup**: Delete oldest when creating 3rd backup

**Backup Workflow:**
```python
# Management command: python manage.py create_database_backup

1. Query all critical tables:
   - Products, Inventory, Production, Sales, Accounting, Payroll
   
2. Serialize to JSON and compress (gzip):
   backup_data = gzip.compress(json.dumps(all_data))
   
3. Store in DatabaseBackup model:
   - Keep only 2 most recent
   - Delete oldest: DatabaseBackup.objects.order_by('created_at')[2:].delete()
   
4. Email compressed backup to CEO + Developer:
   - Attachment: backup-2025-10-25.json.gz
   - Size: ~500KB compressed (even with months of data)
   
5. Also store in DB for web-based restore
```

**Restore Options:**

**Option 1: Web-Based Restore** (Recommended)
```
Admin Dashboard → System → Database Backups
- View list of 2 most recent backups
- Click "Restore from this backup"
- Confirm → System restores data
- Verify data integrity
```

**Option 2: Email-Based Restore**
```
1. CEO/Admin downloads backup-2025-10-25.json.gz from email
2. Upload via Admin Dashboard → Restore from File
3. System decompresses and imports
4. Verify data integrity
```

**Option 3: Management Command** (Direct PostgreSQL access)
```bash
# If you have Railway CLI access to production database
python manage.py restore_from_backup --backup-id=123
# OR
python manage.py restore_from_file --file=/path/to/backup.json.gz
```

### Data Exports (On-Demand)

**CSV Exports (Lighter Weight):**
- All reports exportable to CSV
- Admin can export specific data:
  - Current inventory stock
  - Monthly sales data
  - Payroll for specific month
  - Production batches
- Format: UTF-8, Excel-compatible
- Download immediately (no file storage needed)
- Optional: Email to recipient

**HTML Report Archives:**
- Daily/Weekly/Monthly reports already stored in database
- Can be re-sent via email anytime
- Searchable by date range
- Export: Generate ZIP in memory, download immediately (no file save)

**Manual Backup Workflow:**
```
Admin Dashboard → System Settings → Backup & Export
Options:
  1. Create Database Backup Now (immediate → email + DB storage)
  2. Export Current Data (CSV bundle → download)
  3. Export Reports (HTML bundle → download)
  4. Email Latest Backup
```

### Backup Storage Summary

**What's Stored WHERE:**
- ✅ **In PostgreSQL DB**: 
  - 2 most recent full backups (compressed JSON)
  - All daily/weekly/monthly reports (HTML)
  - All operational data
  
- ✅ **In Email Archives** (CEO + Developer):
  - Daily backup attachments (kept in email)
  - Weekly/Monthly reports (HTML)
  
- ❌ **NOT on Railway File System**: 
  - No local files (ephemeral - would be lost)
  
### Recovery Procedures

**Full System Restore (Disaster Recovery):**
```
1. Access Admin Dashboard (or Railway PostgreSQL console)
2. Go to System → Database Backups
3. Select most recent backup (or upload from email)
4. Click "Restore"
5. System confirms: "Restore will overwrite current data"
6. Proceed → Data restored
7. Run integrity checks:
   - python manage.py check_data_integrity
   - Verify stock reconciliation
   - Check last 3 days of reports
```

**Partial Restore (Specific Data):**
```
1. Download backup from email or database
2. Extract specific table data (e.g., inventory)
3. Admin Dashboard → Import → Select table
4. Upload CSV or JSON
5. System validates and imports
```

**Data Verification Post-Restore:**
- Auto-run reconciliation checks:
  - Inventory: Opening + Purchases = Usage + Closing
  - Products: Opening + Production = Dispatched - Returns + Closing
  - Sales: What went out = Sales + Returns
- Generate test daily report
- Compare totals with last known good state

---

## �📱 Responsive Design Strategy

### Desktop Priority (Complex Data/Graphs)

**Primary Focus:** Desktop/Laptop browsers (1024px+ width)
- Wide tables for production batches, sales returns, payroll
- Complex graphs with multiple data points
- Side-by-side comparisons
- Full-width dashboards

**Why Desktop First:**
- Finance/accounting work requires large screens
- Complex data entry (mixes, purchases, payroll)
- Multiple columns in reports (P&L statements)
- Graph readability (8 charts on Analytics dashboard)

### Mobile-Friendly Basics (Bootstrap Responsive)

**Where Mobile Works:**
- Login/logout
- View simple lists (products, salespeople, inventory items)
- Basic dashboards (summary cards)
- Alerts/notifications
- Single-product dispatch/return entry

**Mobile Limitations (Acceptable):**
- Complex tables may require horizontal scroll
- Graphs may stack vertically
- Multi-product dispatch entry easier on desktop
- Report viewing optimized for desktop

**Technical Approach:**
- Bootstrap 5 grid system (responsive by default)
- Media queries for key breakpoints (768px, 1024px)
- Mobile: Stack cards, simplified navigation
- Desktop: Full-width tables, side-by-side panels

---

## ✅ Business Rules (Answered)

1. **Indirect Costs**: Per day (allocated across all batches)
2. **Commission**: Variable per salesman (0% schools, 5-10% salesmen)
3. **Deficits**: Flag + immediate alert (no auto-deduction)
4. **Schools vs Salesmen**: Same workflow, different commission
5. **Pricing**: Locked at day start (changes next day)
6. **Returns**: Add back to stock (track damage separately)
7. **Crate Damage**: Separate field in Crate model
8. **Book Closing**: Daily 9 PM (Accountant locked, only CEO/Admin can edit)

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Products app (models, aliases, mixes)
- Inventory app (ingredients, restocking, smart alerts)
- Forms with ✏️Manual/🤖Auto labels
- Unit conversion system
- **Bootstrap 5 integration** (responsive base)

### Phase 2: Core Ops (Week 3-4)
- Production app (batches, P&L per mix, stock reconciliation)
- Sales app (dispatch, returns, deficits)
- Accounting app (invoices)
- **Stock reconciliation logic** (what comes in must go out)

### Phase 3: Reports & Analytics (Week 5-6)
- Reports app (daily/weekly/monthly, HTML)
- Analytics app (Chart.js dashboard, 8 charts)
- Scheduled tasks (Railway cron)
- **CSV export functionality**

### Phase 4: Integration & Launch (Week 7)
- Payroll integration
- Alert system (signals + smart thresholds)
- **Backup system** (in-database storage + email delivery, 2 backups max)
- **Admin configuration panel** (adjust thresholds)
- Testing & deployment
- **Data verification** (fresh start, manual backfill)
- User training documentation

---

## 🛠️ Tech Stack

### Core Dependencies
```python
# Django
Django==5.2.7

# Analytics & Visualization
django-chartjs==2.3.0       # Chart.js wrapper (FREE, MIT License) ✅ CONFIRMED

# Responsive Design
# Bootstrap 5 (via CDN - no package needed)
```

### Chart.js Features (FREE) ✅ SELECTED
- 8 chart types: Line, Bar, Pie, Doughnut, Radar, Polar, Bubble, Scatter
- Responsive & animated by default
- Tooltips & legends built-in
- No server-side dependencies
- MIT License (completely free)
- Size: 11kb gzipped (auto-compressed during CDN download)
- Renders in browser (not in email - users click link to view)
- Documentation: https://www.chartjs.org/

### Email System (Django Built-in)
```python
# settings/prod.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Or Railway SMTP
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD')
DEFAULT_FROM_EMAIL = 'Chesanto Bakery <alerts@chesanto.com>'
```

### Railway Configuration (Cron + Backups)
```json
// railway.json - Scheduled tasks
{
  "cron": [
    {
      "schedule": "0 20 * * *",
      "command": "python manage.py close_daily_books",
      "name": "Close Daily Books & Generate Report"
    },
    {
      "schedule": "0 8 * * 0",
      "command": "python manage.py generate_weekly_report",
      "name": "Weekly Report (Sunday 8AM)"
    },
    {
      "schedule": "0 0 1 * *",
      "command": "python manage.py generate_monthly_report",
      "name": "Monthly Report (1st 12AM)"
    },
    {
      "schedule": "0 8 * * *",
      "command": "python manage.py check_stock_levels",
      "name": "Daily Stock Level Check"
    }
  ]
}
```

**Railway PostgreSQL Backups (FREE):**
- Automatic daily backups (Railway native feature)
- Keep 2 latest backups
- Restore via Railway dashboard or CLI
- No additional packages needed

### Report Delivery Strategy
- **Email:** Summary + secure link to view full report
- **Report page:** Tables (stored data) + Charts (Chart.js renders on-demand)
- **Charts:** Only work in web browser (not in email)
- **Security:** Requires login to view reports

### NOT Using (Complexity Avoided) ❌
- ❌ **Background task queues** (Celery/Redis) → Using Railway cron + Django signals
- ❌ **django-dbbackup** → Using Railway PostgreSQL native backups
- ❌ **WeasyPrint** → Using HTML (not PDF)
- ❌ **Paid charting libraries** → Chart.js is free & powerful
- ❌ **AWS S3** → Railway PostgreSQL + email delivery sufficient
- ❌ **Plotly** → Chart.js sufficient (simpler)

---

## 📋 All Updated Fields

Every model that allows input/edit has:
- `created_by` (FK to User)
- `created_at` (timestamp)
- `updated_by` (FK to User)
- `updated_at` (timestamp)

---

## 📋 Implementation Checklist

### Phase 1: Foundation (Week 1-2)
- [ ] **Railway Setup**
  - [ ] Create `railway.json` in project root
  - [ ] Configure Railway environment variables
- [ ] **Email Configuration**
  - [ ] Set up Django email backend (settings/prod.py)
  - [ ] Test email sending in development
  - [ ] Verify SMTP credentials
- [ ] **Products App**
  - [ ] Models: Product, Ingredient, Mix, MixIngredient
  - [ ] Django Admin interface for product management
  - [ ] Create NEW products feature (not just edit existing)
  - [ ] Add custom fields to Product model via admin
  - [ ] Dynamic mix management (add/remove ingredients)
  - [ ] Auto-cost loading from Inventory
  - [ ] Soft delete (is_active flag)
- [ ] **Inventory App**
  - [ ] Models: ExpenseCategory, InventoryItem, DailyInventoryStock, StockDamage
  - [ ] Django Admin interface for inventory management
  - [ ] Add NEW inventory items feature
  - [ ] Edit item properties (unit, category, reorder level)
  - [ ] Unit conversion system
  - [ ] Smart alert configuration (7 days production)
  - [ ] Purchase workflow
  - [ ] Damage/wastage tracking with approval workflow
- [ ] **Bootstrap 5 Integration**
  - [ ] Base template with responsive grid
  - [ ] Forms with ✏️Manual/🤖Auto labels

### Phase 2: Core Operations (Week 3-4)
- [ ] **Production App**
  - [ ] ProductionBatch with cost breakdown
  - [ ] DailyProduction with Product Stock tracking
  - [ ] P&L per mix calculations
  - [ ] Stock reconciliation logic (with damage accounting)
  - [ ] Book closing at 9PM (Railway Cron)
  - [ ] Time-aware permissions (defense-in-depth)
  - [ ] Damage/wastage integration in reconciliation
- [ ] **Sales App**
  - [ ] Multi-product dispatch system
  - [ ] SalesReturn with deficit tracking
  - [ ] Dual commission calculation
  - [ ] Deficit alerts (Django signals)
- [ ] **Accounting App**
  - [ ] Invoice generation
  - [ ] MixProfitLoss tracking
  - [ ] Integration with Purchase, Payroll, Fuel
- [ ] **Django Signals**
  - [ ] Low stock alerts (immediate)
  - [ ] Deficit alerts (immediate)
  - [ ] Inventory auto-deduction (immediate)
  - [ ] Stock reconciliation variance (immediate)

### Phase 3: Reports & Analytics (Week 5-6)
- [ ] **Reports App**
  - [ ] DailyReport model (store calculated data)
  - [ ] WeeklyReport and MonthlyReport models
  - [ ] Report viewing page (tables + charts)
  - [ ] Email template (summary + link)
  - [ ] CSV export functionality
- [ ] **Management Commands**
  - [ ] `close_daily_books` (9:00 PM)
  - [ ] `generate_weekly_report` (Sunday 8:00 AM)
  - [ ] `generate_monthly_report` (1st 12:00 AM)
  - [ ] `check_stock_levels` (8:00 AM daily)
- [ ] **Railway Cron**
  - [ ] Configure cron jobs in railway.json
  - [ ] Test in staging environment
  - [ ] Verify cron execution logs
- [ ] **Analytics App**
  - [ ] Chart.js integration (django-chartjs)
  - [ ] 8 charts (Financial + Operational)
  - [ ] Chart interactivity (hover tooltips, click actions, legend toggle)
  - [ ] Animations configuration (initial load, data updates, hover effects)
  - [ ] Performance optimization (disable animations for large datasets)
  - [ ] 3 dashboard sections
  - [ ] Real-time data queries
  - [ ] Export options (PNG, CSV)

### Phase 4: Integration & Launch (Week 7)
- [ ] **Payroll App**
  - [ ] Employee model (20+ capacity, unlimited scalability)
  - [ ] Django Admin interface for employee management
  - [ ] Add custom fields capability (NHIF, NSSF, pension, allowances)
  - [ ] MonthlyPayroll model
  - [ ] PayrollItem model (with statutory deductions)
  - [ ] CasualLabor model (daily/weekly tracking)
  - [ ] Payroll workflow (5 steps - creation, population, adjustment, finalization, payment)
  - [ ] Casual labor workflow (daily entry, weekly payment, monthly integration)
  - [ ] Statutory deduction calculations (PAYE, NHIF, NSSF)
  - [ ] Bank transfer file generation (CSV)
  - [ ] M-Pesa payment list
  - [ ] Payslip generation (PDF for 20+ employees)
  - [ ] Integration with Accounting (permanent + casual totals)
- [ ] **Alert System**
  - [ ] Configure alert thresholds (admin panel)
  - [ ] Test all Django signals (low stock, deficit, deduction, variance)
  - [ ] Test all scheduled alerts (stock levels daily)
  - [ ] Test damage approval workflow (CEO approval for > KES 500)
  - [ ] Verify email delivery
  - [ ] Test escalation (Accountant → CEO)
- [ ] **Backup System**
  - [ ] DatabaseBackup model
  - [ ] Backup creation management command
  - [ ] Web-based restore functionality
  - [ ] Test backup/restore cycle
- [ ] **Security & Access Control**
  - [ ] Report access permissions
  - [ ] ReportView audit trail
  - [ ] Test role-based access
- [ ] **Data Verification**
  - [ ] Fresh database setup
  - [ ] Manual backfill of verified data
  - [ ] Test complete workflow (production → sales → reports)
- [ ] **Testing**
  - [ ] Unit tests for all models (including StockDamage, Employee, CasualLabor)
  - [ ] Integration tests for workflows (production → damage → reconciliation)
  - [ ] Test damage approval workflow
  - [ ] Test time-aware permissions (book closing)
  - [ ] Test product/inventory/employee creation via Django Admin
  - [ ] Test payroll calculations (statutory deductions, pro-rata)
  - [ ] Test casual labor weekly aggregation
  - [ ] End-to-end tests
  - [ ] Performance tests (chart animations with large datasets, 20+ employee payroll)
- [ ] **Deployment**
  - [ ] Deploy to Railway production
  - [ ] Verify Railway cron jobs running
  - [ ] Test automated report generation
  - [ ] User acceptance testing (test with 20+ employees)
- [ ] **Documentation**
  - [ ] User training materials
  - [ ] Admin guide (alert configuration, product/inventory/employee management)
  - [ ] Damage approval workflow documentation
  - [ ] Chart interactivity user guide
  - [ ] Payroll processing guide (permanent + casual)
  - [ ] Employee management guide (adding custom fields like NHIF, NSSF)
  - [ ] Troubleshooting guide

---

**Priority**: CEO needs **P&L per mix** + **deficit alerts** working ASAP! 🚀

---

## 📝 Enhancements Summary (October 27, 2025)

### 1. ✅ Product & Inventory Management
**Added:** Full CRUD capabilities via Django Admin
- Create NEW products (not just edit existing)
- Add NEW inventory items (e.g., "Honey", "Sesame Seeds")
- Add custom fields to models
- Soft delete (is_active flag) preserves historical data
- Bulk actions (activate/deactivate multiple items)
- Change history tracking

### 2. ✅ Stock Reconciliation Enhancement
**Added:** Damage/Wastage tracking in reconciliation formula
- New model: `StockDamage` (tracks all losses separately)
- Enhanced reconciliation: `Opening + Purchases = Usage + DAMAGE + Closing`
- Approval workflow (CEO approval for damages > KES 500)
- 8 damage reasons: SPOILAGE, SPILL, EXPIRED, CONTAMINATION, PEST, THEFT, BREAKAGE, OTHER
- Monthly damage reports with trends and prevention recommendations

### 3. ✅ Hybrid Book Closing
**Added:** Time-aware permissions + Railway Cron (defense-in-depth)
- Railway Cron closes books at 9PM (automatic, generates reports)
- Time-aware permissions prevent Accountant edits after 9PM (safety layer)
- CEO/Admin can always edit (emergency corrections)
- Why both? Cron ensures reports go out, permissions prevent accidents

### 4. ✅ Chart Interactivity Details
**Added:** Complete specification of Chart.js features
- **Hover Tooltips**: Show exact values (e.g., "Bread: KES 45,000 (38%)")
- **Click Actions**: Drill down to daily breakdown, show deficit details
- **Legend Toggle**: Hide/show data series
- **Zoom/Pan**: Touch device support
- **Export**: Download PNG, copy to clipboard

### 5. ✅ Animation Specifications
**Added:** Detailed animation configuration
- **Bar Charts**: Grow from bottom (800ms, easeOutQuart)
- **Line Charts**: Draw left to right (1000ms, easeInOutQuad)
- **Pie Charts**: Rotate in (800ms, easeOutBounce)
- **Staggered**: Sequential animation (50ms delay between bars)
- **Performance**: Auto-disable for > 1000 data points
- **Accessibility**: Respects OS reduced motion settings

### 6. ✅ Implementation Checklist Updates
**Added:** 15+ new tasks across all phases
- Django Admin setup for products/inventory
- StockDamage model implementation
- Time-aware permission layer
- Chart interactivity configuration
- Animation optimization
- Damage approval workflow testing
- Performance testing for large datasets

### 7. ✅ Payroll App Enhancement (October 27, 2025 - Latest)
**Added:** Scalable employee management and casual labor tracking
- **Unlimited Employee Capacity**: System supports 20+ employees currently, unlimited scalability
- **Accountant as Employee**: CHE028 - Eddah Silungi (KES 38,000/month) has both Employee record + User account
- **Custom Fields**: Super Admin can add NHIF, NSSF, pension, allowances via Django Admin
- **Statutory Deductions**: PAYE, NHIF, NSSF calculations and tracking
- **Enhanced Employee Model**: 
  - Department field (PRODUCTION/SALES/ADMIN/FINANCE/DISTRIBUTION)
  - Multiple employee types (PERMANENT/CASUAL/CONTRACT/INTERN)
  - Salary types (MONTHLY/DAILY/WEEKLY/HOURLY)
  - Banking details (bank + M-Pesa)
  - Flexible allowances (housing, transport, custom JSONField)
- **Casual Labor Detailed Tracking**:
  - Daily/weekly entry system
  - Task descriptions (Packaging, Cleaning, Loading)
  - Hourly/daily rates (typical KES 1,200/day, KES 150/hour)
  - Weekly payment batches
  - Monthly aggregation (e.g., September: 12 laborers, 156 days, KES 187,200)
  - Task breakdown reporting
- **Enhanced PayrollItem Model**:
  - Statutory deductions fields (PAYE, NHIF, NSSF, pension)
  - Multiple allowances (housing, transport, overtime)
  - Pro-rata calculations for partial months
  - Hourly calculations for hourly employees
- **Reports & Export**:
  - Individual payslips for 20+ employees
  - Bank transfer file (CSV for bulk payments)
  - M-Pesa payment lists
  - Statutory deductions report
  - Weekly/monthly casual labor summaries
  - Department cost analysis
- **Permission Matrix**: Super Admin manages structure, Accountant processes payroll

### Documentation Completeness
- ✅ All 8 apps justified (domain-driven design)
- ✅ Product/inventory configurability documented
- ✅ **Employee management scalability documented (20+ unlimited)**
- ✅ **Casual labor workflow fully specified**
- ✅ Damage tracking integrated in reconciliation
- ✅ Alerts well-documented (4 types, escalation, thresholds)
- ✅ Book closing hybrid approach explained
- ✅ 8 charts clearly defined (3 Financial + 5 Operational)
- ✅ Chart interactivity and animations fully specified
- ✅ Clear separation: Reports (stored) vs Analytics (live)
- ✅ **Payroll with statutory deductions (PAYE, NHIF, NSSF)**
- ✅ Implementation roadmap: 4 phases, 7 weeks, 85+ tasks

**Status:** MILESTONE_2.md is comprehensive and ready for Phase 1 implementation 🚀


