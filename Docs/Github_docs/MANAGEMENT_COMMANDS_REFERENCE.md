# Management Commands Reference - Phase 1

Quick reference for all custom management commands in Chesanto Bakery Management System.

---

## 🌱 Seeding Commands

### `seed_all` - Master Seeding Command
**Purpose:** Seed all apps with initial data in correct dependency order

**Usage:**
```bash
# Seed all apps (idempotent - safe to run multiple times)
python manage.py seed_all

# Skip if data exists (production safety)
python manage.py seed_all --skip-existing

# Seed specific apps only
python manage.py seed_all --apps inventory products
```

**What it does:**
1. Seeds Inventory app (categories, conversions, items)
2. Seeds Products app (products, ingredients, mixes)
3. Recalculates all mix costs from inventory

**Output:** Success/failure count, next steps

---

### `seed_inventory` - Inventory Data Seeding
**Purpose:** Seed all inventory data from MILESTONE_2.md specifications

**Usage:**
```bash
python manage.py seed_inventory
```

**What it seeds:**
- 5 expense categories (RAW_MATERIALS, PACKAGING, FUEL_ENERGY, CONSUMABLES, OTHER)
- 6 unit conversions (bag→kg: 50, jerycan→L: 20, kg→g: 1000, l→ml: 1000, packet→g: 450, dozen→pcs: 12)
- 20 inventory items with realistic costs and stock levels

**Features:**
- Idempotent (uses `get_or_create`)
- Creates admin user if not exists
- Color-coded output

---

### `seed_products` - Products Data Seeding
**Purpose:** Seed products, ingredients, and mixes with inventory linking

**Usage:**
```bash
python manage.py seed_products
```

**What it seeds:**
- 3 products (Bread, KDF, Scones) with pricing and specifications
- 10 ingredients linked to inventory items
- 3 mixes (recipes) with 21 total mix ingredients

**Features:**
- Links ingredients to inventory for auto-costing
- Updates existing ingredients with inventory links
- Creates realistic mix recipes from MILESTONE_2.md

---

## 💰 Cost Management Commands

### `recalculate_costs` - Recalculate Mix Costs
**Purpose:** Recalculate all mix costs from linked inventory items

**Usage:**
```bash
python manage.py recalculate_costs
```

**When to run:**
- After inventory price changes
- After linking ingredients to inventory
- After adding new mixes or ingredients
- During production deployment
- When costs look incorrect

**Output:**
- Cost breakdown for each mix
- Ingredient costs with quantities
- Before/after comparison
- Updated/unchanged counts
- Validation of inventory links

**Example Output:**
```
📋 Bread - Mix 1 (v1)
✓ Wheat Flour: 36.000 kg = KES 2,628.00
✓ Sugar: 4.500 kg = KES 648.00
...
TOTAL COST: KES 4,234.20 (was KES 4,234.20)
COST/PACKET: KES 32.08
```

---

### `show_costs` - Display Cost Analysis
**Purpose:** Display comprehensive cost and profitability analysis

**Usage:**
```bash
python manage.py show_costs
```

**What it shows:**
- **Production Details:** Expected output, variability, units per packet
- **Cost Breakdown:** Total mix cost, cost per packet
- **Pricing:** Selling price per unit
- **Profitability:** Profit per packet, profit margin (%), total profit
- **Ingredients:** Complete list with quantities and costs
- **Sub-Products:** If applicable (e.g., Bread Rejects)
- **Overall Summary:** Daily production potential, total revenue/costs/profit

**Use Cases:**
- Business decision-making
- Pricing strategy
- Cost verification
- Profitability analysis
- Investor reporting

**Example Output:**
```
🍞 Bread - Mix 1 (v1)

📊 PRODUCTION DETAILS:
  Expected Output: 132 loafs
  
💵 COST BREAKDOWN:
  Total Mix Cost: KES 4,234.20
  Cost per Packet: KES 32.08
  
💰 PRICING:
  Selling Price: KES 60.00 per loaf
  
📈 PROFITABILITY:
  Profit per Packet: KES 27.92
  Profit Margin: 46.5%
  Total Profit (if all sold): KES 3,685.80
```

---

## 🔄 Common Workflows

### Initial Setup (Development)
```bash
# 1. Run migrations
python manage.py migrate

# 2. Seed all data
python manage.py seed_all

# 3. View costs
python manage.py show_costs

# 4. Access admin
python manage.py runserver
# Visit http://127.0.0.1:8000/admin/
```

### Production Deployment (Railway)
```bash
# Use the deployment script
./scripts/deploy_seed.sh

# Or manually:
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_all --skip-existing
python manage.py createsuperuser  # if needed
```

### After Inventory Price Changes
```bash
# 1. Update inventory prices in Django Admin

# 2. Recalculate mix costs
python manage.py recalculate_costs

# 3. Verify new profitability
python manage.py show_costs
```

### Adding New Products
```bash
# 1. Add product in Django Admin
# 2. Add ingredients (link to inventory)
# 3. Add mix with ingredients

# 4. Recalculate costs
python manage.py recalculate_costs

# 5. Verify
python manage.py show_costs
```

---

## 🧪 Testing Commands

### Verify Complete Integration
```bash
# Test complete seeding workflow
python manage.py seed_all

# Expected output:
# ✅ Inventory seeded successfully
# ✅ Products seeded successfully
# ✅ Mix Costs seeded successfully
# Success: 3 | Failed: 0
```

### Verify Cost Calculations
```bash
# Recalculate and verify
python manage.py recalculate_costs

# Expected: All ingredients show ✓ (linked to inventory)
# No ⚠ warnings
```

### Verify Profitability
```bash
# Show complete analysis
python manage.py show_costs

# Expected: 
# - All costs > 0
# - All margins > 0
# - Overall margin ~41.6%
```

---

## 📊 Output Color Coding

- ✅ **Green (SUCCESS):** Successful operations
- ⚠️  **Yellow (WARNING):** Warnings (e.g., no inventory link)
- ❌ **Red (ERROR):** Errors (e.g., failed seeding)
- ✓ **Checkmark:** Completed/Validated items
- → **Arrow:** Already exists (idempotent skip)

---

## 🔗 Related Documentation

- [SEEDING_GUIDE.md](SEEDING_GUIDE.md) - Complete seeding patterns and architecture
- [DAY_5_INTEGRATION_COMPLETE.md](DAY_5_INTEGRATION_COMPLETE.md) - Integration details
- [PHASE_1_IMPLEMENTATION_LOG.md](PHASE_1_IMPLEMENTATION_LOG.md) - Phase 1 progress
- [MILESTONE_2.md](MILESTONE_2.md) - Full specifications and data sources

---

## 🚀 Quick Reference Card

```bash
# Seed all apps
python manage.py seed_all

# Seed specific app
python manage.py seed_inventory
python manage.py seed_products

# Recalculate costs (after price changes)
python manage.py recalculate_costs

# View profitability
python manage.py show_costs

# Production deployment
./scripts/deploy_seed.sh
```

---

**Last Updated:** October 27, 2025 (Day 5 - Integration Complete)  
**Phase:** Phase 1 Complete (Products & Inventory)  
**Next Phase:** Week 2 Frontend UI or Phase 2 Production App
