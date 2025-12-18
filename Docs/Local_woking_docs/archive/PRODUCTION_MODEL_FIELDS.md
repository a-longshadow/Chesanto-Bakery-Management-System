# PRODUCTION APP - MODEL FIELD REFERENCE
**Created:** October 29, 2025 9:35 AM  
**Purpose:** Comprehensive field reference for Production frontend development  
**Strategy:** Prevent field name errors (apply lessons from Products/Inventory debugging)

---

## 🎯 CRITICAL RULES FOR FRONTEND DEVELOPMENT

1. **Use EXACT field names** from this document in views and templates
2. **Auto-calculated fields (🤖)** - Display only, do NOT include in forms
3. **Manual fields (✏️)** - Include in forms with proper validation
4. **Read-only after 9PM** - Check `is_closed` flag before allowing edits
5. **Time-aware permissions** - Admin/CEO can edit closed books, Accountant cannot

---

## MODEL 1: DailyProduction

### Field Categories

#### **Book Closing Fields**
| Field Name | Type | Symbol | Notes |
|------------|------|--------|-------|
| `date` | DateField | ✏️ | Unique, production date |
| `is_closed` | BooleanField | 🤖 | Set to True at 9PM by cron |
| `closed_at` | DateTimeField | 🤖 | Timestamp when books closed |

#### **Opening Product Stock (Auto from previous day)**
| Field Name | Type | Symbol | Notes |
|------------|------|--------|-------|
| `opening_bread_stock` | IntegerField | 🤖 | From previous day's closing |
| `opening_kdf_stock` | IntegerField | 🤖 | From previous day's closing |
| `opening_scones_stock` | IntegerField | 🤖 | From previous day's closing |

#### **Production Totals (Auto from batches)**
| Field Name | Type | Symbol | Notes |
|------------|------|--------|-------|
| `bread_produced` | IntegerField | 🤖 | Sum of all Bread batches |
| `kdf_produced` | IntegerField | 🤖 | Sum of all KDF batches |
| `scones_produced` | IntegerField | 🤖 | Sum of all Scones batches |

#### **Dispatch/Returns (From Sales app)**
| Field Name | Type | Symbol | Notes |
|------------|------|--------|-------|
| `bread_dispatched` | IntegerField | ✏️ | From Sales Dispatch records |
| `kdf_dispatched` | IntegerField | ✏️ | From Sales Dispatch records |
| `scones_dispatched` | IntegerField | ✏️ | From Sales Dispatch records |
| `bread_returned` | IntegerField | ✏️ | From Sales Return records |
| `kdf_returned` | IntegerField | ✏️ | From Sales Return records |
| `scones_returned` | IntegerField | ✏️ | From Sales Return records |

#### **Closing Product Stock (Auto-calculated)**
| Field Name | Type | Symbol | Formula |
|------------|------|--------|---------|
| `closing_bread_stock` | IntegerField | 🤖 | opening + produced - dispatched + returned |
| `closing_kdf_stock` | IntegerField | 🤖 | opening + produced - dispatched + returned |
| `closing_scones_stock` | IntegerField | 🤖 | opening + produced - dispatched + returned |

#### **Indirect Costs (Manual entry)**
| Field Name | Type | Symbol | Description |
|------------|------|--------|-------------|
| `diesel_cost` | DecimalField(10,2) | ✏️ | Daily diesel consumption (KES) |
| `firewood_cost` | DecimalField(10,2) | ✏️ | Daily firewood cost (KES) |
| `electricity_cost` | DecimalField(10,2) | ✏️ | Daily electricity (estimated, KES) |
| `fuel_distribution_cost` | DecimalField(10,2) | ✏️ | Fuel for trucks/Bolero (KES) |
| `other_indirect_costs` | DecimalField(10,2) | ✏️ | Miscellaneous costs (KES) |
| `total_indirect_costs` | DecimalField(10,2) | 🤖 | Sum of all indirect costs |

#### **Reconciliation Fields**
| Field Name | Type | Symbol | Notes |
|------------|------|--------|-------|
| `reconciliation_notes` | TextField | ✏️ | Notes on variances, issues |
| `has_variance` | BooleanField | 🤖 | True if variance > 5% |
| `variance_percentage` | DecimalField(5,2) | 🤖 | Variance % if detected |

#### **Metadata Fields**
| Field Name | Type | Notes |
|------------|------|-------|
| `created_at` | DateTimeField | Auto-populated |
| `created_by` | ForeignKey(User) | User who created |
| `updated_at` | DateTimeField | Auto-updated |
| `updated_by` | ForeignKey(User) | Last editor |

### Key Methods
- `calculate_closing_stock()` - Calculate closing stock for all products
- `calculate_total_indirect_costs()` - Sum all indirect costs
- `check_reconciliation_variance()` - Check for > 5% variance
- `close_books(user)` - Close books at 9PM (locks edits)
- `save()` - Auto-calculates all values

### Related Models
- **ProductionBatch** (reverse relation: `batches`)
- **IndirectCost** (reverse relation: `indirect_cost_details`)

---

## MODEL 2: ProductionBatch

### Field Categories

#### **Batch Identification**
| Field Name | Type | Symbol | Notes |
|------------|------|--------|-------|
| `daily_production` | ForeignKey(DailyProduction) | ✏️ | Parent daily production |
| `mix` | ForeignKey(Mix) | ✏️ | Mix selection (Bread Mix 1, etc.) |
| `batch_number` | IntegerField | ✏️ | Batch number for the day (1, 2, 3...) |
| `start_time` | TimeField | ✏️ | When production started |
| `end_time` | TimeField | ✏️ | When production finished |

#### **Output Fields**
| Field Name | Type | Symbol | Notes |
|------------|------|--------|-------|
| `actual_packets` | IntegerField | ✏️ | **USER INPUT** - Actual units produced |
| `expected_packets` | IntegerField | 🤖 | From Mix.expected_packets |
| `variance_packets` | IntegerField | 🤖 | actual - expected |
| `variance_percentage` | DecimalField(5,2) | 🤖 | (variance / expected) × 100 |
| `rejects_produced` | IntegerField | ✏️ | Bread rejects (if applicable) |

#### **Cost Fields (All Auto-calculated)**
| Field Name | Type | Symbol | Formula |
|------------|------|--------|---------|
| `ingredient_cost` | DecimalField(12,2) | 🤖 | From Mix.total_cost |
| `packaging_cost` | DecimalField(10,2) | 🤖 | (actual_packets + rejects) × KES 3.3 |
| `allocated_indirect_cost` | DecimalField(10,2) | 🤖 | Proportional share of daily indirect |
| `total_cost` | DecimalField(12,2) | 🤖 | ingredient + packaging + indirect |
| `cost_per_packet` | DecimalField(10,2) | 🤖 | total_cost / actual_packets |

#### **P&L Fields (CEO Requirement)**
| Field Name | Type | Symbol | Formula |
|------------|------|--------|---------|
| `selling_price_per_packet` | DecimalField(10,2) | 🤖 | From Product.price_per_packet |
| `expected_revenue` | DecimalField(12,2) | 🤖 | actual_packets × selling_price |
| `gross_profit` | DecimalField(12,2) | 🤖 | expected_revenue - total_cost |
| `gross_margin_percentage` | DecimalField(5,2) | 🤖 | (gross_profit / expected_revenue) × 100 |

#### **Quality Control**
| Field Name | Type | Symbol | Notes |
|------------|------|--------|-------|
| `quality_notes` | TextField | ✏️ | Quality observations, issues |
| `is_finalized` | BooleanField | 🤖 | Locked after book closing (9PM) |

#### **Metadata Fields**
| Field Name | Type | Notes |
|------------|------|-------|
| `created_at` | DateTimeField | Auto-populated |
| `created_by` | ForeignKey(User) | User who created |
| `updated_at` | DateTimeField | Auto-updated |
| `updated_by` | ForeignKey(User) | Last editor |

### Key Methods
- `calculate_variance()` - Calculate actual vs expected variance
- `calculate_packaging_cost()` - KES 3.3 per unit (including rejects)
- `calculate_costs()` - Calculate all costs
- `calculate_pl()` - Calculate P&L metrics
- `allocate_indirect_costs()` - Proportional allocation from DailyProduction
- `update_daily_production_totals()` - Update parent totals
- `clean()` - Validation (can't edit finalized, rejects only for Bread)
- `save()` - Auto-calculates all values

### Unique Constraint
- `unique_together = ['daily_production', 'batch_number']`

### Related Models
- **DailyProduction** (parent)
- **Mix** (via `mix` FK) → Product, MixIngredients

---

## MODEL 3: IndirectCost

### Fields

| Field Name | Type | Symbol | Notes |
|------------|------|--------|-------|
| `daily_production` | ForeignKey(DailyProduction) | ✏️ | Parent record |
| `cost_type` | CharField(20) | ✏️ | **CHOICES:** DIESEL, FIREWOOD, ELECTRICITY, FUEL_DISTRIBUTION, OTHER |
| `description` | CharField(200) | ✏️ | Cost description (e.g., "20L diesel from Ikapolok") |
| `amount` | DecimalField(10,2) | ✏️ | Cost amount in KES |
| `receipt_number` | CharField(100) | ✏️ | Receipt/invoice number (optional) |
| `vendor` | CharField(200) | ✏️ | Vendor/supplier name (optional) |
| `created_at` | DateTimeField | - | Auto-populated |
| `created_by` | ForeignKey(User) | - | User who created |

### Choices for `cost_type`
```python
COST_TYPE_CHOICES = [
    ('DIESEL', 'Diesel (Production)'),
    ('FIREWOOD', 'Firewood'),
    ('ELECTRICITY', 'Electricity'),
    ('FUEL_DISTRIBUTION', 'Fuel (Distribution)'),
    ('OTHER', 'Other'),
]
```

---

## 🔐 PERMISSIONS & TIME-AWARE EDITING

### Book Closing Rules (9PM Daily)
1. **Before 9PM:**
   - All authorized users can edit today's production
   - Add batches, enter indirect costs, update stock
   
2. **After 9PM (Books Closed):**
   - `DailyProduction.is_closed = True`
   - `ProductionBatch.is_finalized = True`
   - **Accountant:** Cannot edit closed books
   - **Admin/CEO:** Can edit with audit trail
   - Display warning: "Books closed at [timestamp]"

### User Role Permissions
| Role | Can View | Can Create Batch | Can Edit After 9PM |
|------|----------|------------------|-------------------|
| SUPERADMIN | ✅ All | ✅ Yes | ✅ Yes |
| CEO | ✅ All | ✅ Yes | ✅ Yes (with notes) |
| MANAGER | ✅ All | ✅ Yes | ✅ Yes (with notes) |
| ACCOUNTANT | ✅ All | ✅ Yes | ❌ No (locked) |
| BASIC_USER | ✅ Current day only | ❌ No | ❌ No |

---

## 📊 FORM FIELD MAPPINGS

### DailyProduction Form (Indirect Costs Only)
**Manual Fields (User Input):**
- `diesel_cost` (DecimalField, KES)
- `firewood_cost` (DecimalField, KES)
- `electricity_cost` (DecimalField, KES)
- `fuel_distribution_cost` (DecimalField, KES)
- `other_indirect_costs` (DecimalField, KES)
- `reconciliation_notes` (Textarea, optional)

**Display Only:**
- `date` (today's date, read-only)
- `is_closed` (status indicator)
- All opening/closing stock (calculated)
- All production totals (from batches)

### ProductionBatch Form
**Manual Fields (User Input):**
- `mix` (Select dropdown from active mixes)
- `batch_number` (IntegerField, auto-increment suggestion)
- `start_time` (TimeField, optional)
- `end_time` (TimeField, optional)
- `actual_packets` ⭐ **CRITICAL** - Main user input
- `rejects_produced` (IntegerField, only for Bread)
- `quality_notes` (Textarea, optional)

**Display Only:**
- `expected_packets` (from selected mix)
- `variance_packets` (calculated)
- `variance_percentage` (calculated, color-coded)
- All cost fields (ingredient, packaging, indirect, total)
- All P&L fields (revenue, profit, margin)

### IndirectCost Detail Form (Optional)
**Manual Fields:**
- `cost_type` (Select from COST_TYPE_CHOICES)
- `description` (CharField, 200 max)
- `amount` (DecimalField, KES)
- `receipt_number` (CharField, optional)
- `vendor` (CharField, optional)

---

## 🎨 DISPLAY PATTERNS

### Status Indicators
```python
# Book Status
if daily_production.is_closed:
    badge_class = "badge--error"  # Red
    status_text = "CLOSED"
else:
    badge_class = "badge--success"  # Green
    status_text = "OPEN"
```

### Variance Color Coding
```python
# Production Variance
if batch.variance_percentage >= 5:
    color = "var(--color-success)"  # Green (overproduction)
elif batch.variance_percentage <= -5:
    color = "var(--color-error)"  # Red (underproduction)
else:
    color = "var(--color-gray-600)"  # Gray (acceptable)
```

### Margin Color Coding
```python
# Profit Margin
if batch.gross_margin_percentage >= 30:
    color = "var(--color-success)"  # Green (good)
elif batch.gross_margin_percentage >= 20:
    color = "var(--color-warning)"  # Orange (acceptable)
else:
    color = "var(--color-error)"  # Red (poor)
```

---

## 🚨 VALIDATION RULES

### ProductionBatch Validation
1. **Cannot edit finalized batches** - Check `is_finalized` flag
2. **Actual packets must be positive** - `actual_packets > 0`
3. **Rejects only for Bread** - `if rejects_produced > 0 and product != "Bread" → Error`
4. **Unique batch number per day** - Enforce `unique_together`

### DailyProduction Validation
1. **Only one record per date** - `date` field is unique
2. **Cannot close books twice** - Check `is_closed` before closing
3. **Variance threshold** - Alert if `variance_percentage > 5%`

---

## 📈 CALCULATED FIELDS FORMULAS

### Closing Stock
```python
closing_stock = opening_stock + produced - dispatched + returned
```

### Packaging Cost
```python
packaging_cost = (actual_packets + rejects_produced) × KES 3.30
```

### Total Cost
```python
total_cost = ingredient_cost + packaging_cost + allocated_indirect_cost
```

### Cost Per Packet
```python
cost_per_packet = total_cost / actual_packets
```

### Expected Revenue
```python
expected_revenue = actual_packets × selling_price_per_packet
```

### Gross Profit
```python
gross_profit = expected_revenue - total_cost
```

### Gross Margin %
```python
gross_margin_percentage = (gross_profit / expected_revenue) × 100
```

### Production Variance
```python
variance_packets = actual_packets - expected_packets
variance_percentage = (variance_packets / expected_packets) × 100
```

### Indirect Cost Allocation (Proportional)
```python
# For each batch:
total_ingredient_cost_all_batches = sum(batch.ingredient_cost for all batches)
proportion = batch.ingredient_cost / total_ingredient_cost_all_batches
allocated_indirect_cost = proportion × daily_production.total_indirect_costs
```

---

## ⚡ DJANGO SIGNALS (Backend Integration)

### On ProductionBatch Save
1. **Deduct ingredients from Inventory** (`post_save` signal)
2. **Deduct packaging from Inventory** (bags)
3. **Check low stock alerts** (< 7 days supply)
4. **Update DailyProduction totals** (bread_produced, kdf_produced, scones_produced)

### On DailyProduction Close (9PM)
1. **Lock all batches** (`is_finalized = True`)
2. **Calculate closing stock** for all products
3. **Check reconciliation variance** (> 5% alert)
4. **Generate DailyReport** (Reports app)
5. **Set opening stock for next day**

---

## 📝 FRONTEND TEMPLATE REQUIREMENTS

### 5 Templates Needed
1. **daily_production.html** - Dashboard for today's production
2. **production_batch_form.html** - Record batch with P&L display
3. **product_stock_summary.html** - Opening/closing stock table
4. **indirect_costs_form.html** - Enter daily indirect costs
5. **book_closing_view.html** - Finalize day with lock indicator

### Key Features to Implement
- ✅ Time-aware editing (9PM lock with countdown timer)
- ✅ Real-time P&L calculation (profit/margin display)
- ✅ Variance color coding (red/green/gray)
- ✅ Stock reconciliation warnings (> 5% variance)
- ✅ Permission-based UI (Admin/CEO can edit closed books)
- ✅ Auto-refresh opening stock from previous day
- ✅ Batch number auto-increment suggestion
- ✅ Mix selection with expected output display

---

**Last Updated:** October 29, 2025 9:35 AM  
**Status:** ✅ READY FOR FRONTEND DEVELOPMENT  
**Next Step:** Create production templates using these exact field names
