# 🏭 Production Manager Guide

> **Role:** Production Manager / Department Head | **Access Level:** Production + View Sales/Inventory

As a Production Manager, you oversee production operations: recording batches, managing stock, handling waste, and monitoring production efficiency.

---

## 🎯 Your Responsibilities

- Record daily production batches
- Monitor product stock levels
- Manage waste and rejects
- View production analytics
- View inventory levels (read-only)
- View products and recipes (read-only)

---

## 🏠 Production Dashboard

**Location:** Main Menu → **Production**

The dashboard shows:
- Today's production summary
- Current stock levels by product
- Recent batches
- Waste/spoilage summary

---

## 📝 Recording a Production Batch

When production completes a batch:

### Step 1: Access Batch Creation

1. Go to **Production** → **Create Batch**

### Step 2: Select Product and Mix

2. Select the **Product** (e.g., Bread, Scones, KDF, Family Bread 800g)
3. Select the **Mix/Recipe** to use (usually "Standard Mix")
4. The system shows:
   - Expected yield (units)
   - Required ingredients

### Step 3: Enter Actual Production

5. Enter the **Actual Yield** (units produced)
   - For fixed yield products (Bread, Scones): should match expected
   - For variable yield products (KDF): enter actual count

### Step 4: Review Ingredient Deduction

6. Review the ingredients that will be deducted:
   - Flour: X kg
   - Sugar: X kg
   - Yeast: X kg
   - etc.
7. If any ingredient adjustments are needed, note them

### Step 5: Save the Batch

8. Click **"Record Batch"**
9. The system will:
   - Create the production batch record
   - Deduct ingredients from inventory
   - Add produced units to product stock

### Batch Information Saved

| Field | Description |
|-------|-------------|
| Batch Number | Auto-generated (e.g., PRD-20251222-001) |
| Product | What was produced |
| Mix Used | Recipe used |
| Expected Yield | Standard output |
| Actual Yield | What was actually produced |
| Variance | Difference (if any) |
| Date/Time | When recorded |
| Recorded By | Your name |

---

## 📦 Viewing Stock Levels

**Location:** Production → **Stock Dashboard**

### Stock Dashboard

Shows current stock for all products:

| Column | Meaning |
|--------|---------|
| Product | Product name |
| Current Stock | Units available for dispatch |
| Last Updated | When stock was last changed |

### Stock Details

Click on a product to see:
- Stock history (movements in/out)
- Production batches that added stock
- Dispatches that removed stock
- Returns that added stock back

---

## 🗑️ Waste Management

**Location:** Production → **Waste Log**

### Recording Waste/Spoilage

When products must be disposed of (expired, damaged, spoiled):

1. Go to **Production** → **Waste Log**
2. Click **"Record Waste"**
3. Enter:
   - **Product** (select from dropdown)
   - **Quantity** (units being disposed)
   - **Reason** (Expired, Damaged, Spoiled, Quality Issue, Other)
   - **Notes** (optional details)
4. Click **"Record Waste"**

The system will:
- Deduct from product stock
- Log the waste for P&L reporting (as loss)
- Record who disposed and when

### Viewing Waste History

1. Go to **Production** → **Waste Log**
2. View all waste records with:
   - Date
   - Product
   - Quantity
   - Reason
   - Recorded by

---

## 📊 Production Analytics

**Location:** Analytics → **Production**

View production performance:

- Batches per day/week/month
- Yield variance (expected vs actual)
- Production by product
- Efficiency trends

---

## 📦 Viewing Inventory (Read-Only)

**Location:** Main Menu → **Inventory**

You can view but not edit inventory:

### Inventory Dashboard

- Current stock levels for all ingredients
- Low stock alerts
- Recent purchases (view only)

### Checking Ingredient Availability

Before production, check if ingredients are available:

1. Go to **Inventory** → **Dashboard**
2. View stock levels for:
   - Flour Type 1
   - Sugar
   - Yeast
   - Salt
   - Calcium
   - Cooking Fat
   - Cooking Oil (for KDF)
   - Bread Improver

**Note:** If ingredients are low, inform the Admin/Accountant to record a purchase.

---

## 🏷️ Viewing Products (Read-Only)

**Location:** Main Menu → **Products**

You can view products and their recipes:

### Product List

- All products with prices
- Parent/sub-product relationships
- Active/inactive status

### Viewing Recipes (Mixes)

1. Select a product
2. View its mixes
3. See ingredient requirements per batch

**Note:** To edit products or recipes, contact an Admin.

---

## 📋 Daily Checklist

| Time | Task |
|------|------|
| Start of Shift | Check ingredient stock levels |
| After each batch | Record the production batch |
| End of Day | Record any waste/spoilage |
| End of Day | Verify stock levels match physical count |

---

## ⚠️ Important Notes

1. **Record batches immediately** after production completes
2. **Accurate yields matter** - they affect stock and reports
3. **Report low ingredients** to Admin before you run out
4. **Record all waste** - even small amounts, for accurate P&L
5. **Variance tracking** - consistent variances may indicate recipe issues

---

## 📋 Quick Reference

| Task | Navigation |
|------|------------|
| Record Batch | Production → Create Batch |
| View Stock | Production → Stock Dashboard |
| Record Waste | Production → Waste Log → Record Waste |
| View Waste History | Production → Waste Log |
| Check Ingredients | Inventory → Dashboard |
| View Products | Products → Dashboard |
| View Recipe | Products → Select Product → Mixes |

---

## ❓ Common Questions

### Q: What if I record wrong yield?
Contact an Admin to correct the batch record.

### Q: What if ingredients are low?
Notify the Admin/Accountant to record a purchase. Do not produce if ingredients are insufficient.

### Q: What's the difference between fixed and variable yield?
- **Fixed yield:** Machine-portioned (Bread: 132, Scones: 102). Should match every time.
- **Variable yield:** Hand-cut (KDF: 97-107). Enter actual count.

### Q: Where do returned products go?
Returns are processed by Dispatch. Good returns go to "Leftovers" products, rejected returns become waste.

---

**← Back to [Table of Contents](./README.md)**
