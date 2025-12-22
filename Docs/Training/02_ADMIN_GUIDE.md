# 📊 Admin Guide (Accountant)

> **Role:** Accountant | **Access Level:** Financial & Administrative

As an Admin (Accountant), you manage the financial aspects of the bakery: tracking costs, generating reports, and ensuring accurate record-keeping.

---

## 🎯 Your Responsibilities

- Generate and review financial reports (P&L)
- Record inventory purchases and costs
- Manage product prices
- Track sales commissions
- Monitor analytics
- Manage expense categories

---

## 📈 Reports Module

**Location:** Main Menu → **Reports**

### Daily Report

Shows the previous day's performance:

1. Go to **Reports** → **Daily Report**
2. Select the date (defaults to yesterday)
3. View:
   - Total Sales Revenue
   - Total Production Cost
   - Product-by-product breakdown
   - Commission expenses
   - Net profit/loss
4. Click **"Download PDF"** to save or print

### Weekly Report

1. Go to **Reports** → **Weekly Report**
2. Select the week (Mon-Sun)
3. View aggregated data for the week
4. Compare to previous weeks

### Monthly Report

1. Go to **Reports** → **Monthly Report**
2. Select the month and year
3. Comprehensive monthly P&L including:
   - Total Revenue
   - Cost of Goods Sold (COGS)
   - Gross Profit
   - Operating Expenses
   - Product Waste/Spoilage
   - Net Profit

### Annual Report

1. Go to **Reports** → **Annual Report**
2. Select the year
3. Full year financial summary

### Downloading Reports

All reports can be downloaded as PDF:
1. View the report
2. Click **"Download PDF"** or **"Export"**
3. Save to your computer

---

## 📦 Inventory - Recording Purchases

**Location:** Main Menu → **Inventory**

### Recording a New Purchase

When raw materials are purchased:

1. Go to **Inventory** → **Create Purchase**
2. Select the **Item** (e.g., Flour Type 1, Sugar, Yeast)
3. Enter purchase details:
   - **Quantity** (in the item's unit - kg, L, units)
   - **Total Cost** (KES)
   - **Supplier** (optional)
   - **Invoice/Receipt Number** (optional)
   - **Purchase Date**
4. Click **"Save Purchase"**

The system automatically:
- Updates the item's stock level
- Records the cost for P&L calculations
- Updates the average unit cost

### Viewing Purchase History

1. Go to **Inventory** → **Purchase History**
2. Filter by:
   - Date range
   - Item type
   - Supplier
3. View all recorded purchases

---

## 📦 Inventory - Recording Outputs (Indirect Costs)

For items like diesel, electricity, packaging:

1. Go to **Inventory** → **Create Output**
2. Select the **Item** (e.g., Diesel, Electricity)
3. Enter:
   - **Quantity Used**
   - **Purpose/Notes** (optional)
   - **Date**
4. Click **"Save Output"**

This records the consumption as an indirect cost in the P&L.

---

## 🏷️ Products - Price Management

**Location:** Main Menu → **Products**

### Viewing Products

1. Go to **Products** → **Dashboard**
2. View all products with current prices
3. See parent products and their sub-products (e.g., Bread → Bread Leftovers)

### Updating a Product Price

1. Go to **Products** → Select a product
2. Click **"Edit"**
3. Update the **Selling Price**
4. Click **"Save"**

**Note:** Price changes apply to new dispatches only. Existing dispatches keep their original prices.

### Creating a New Product

1. Go to **Products** → **Create Product**
2. Enter:
   - **Name**
   - **Selling Price**
   - **Description** (optional)
   - **Parent Product** (if this is a sub-product like "Leftovers")
3. Click **"Create"**

### Managing Recipes (Mixes)

Recipes define what ingredients are used per production batch:

1. Go to **Products** → Select a product → **Mixes**
2. View or edit the mix:
   - Expected yield (units per batch)
   - Fixed or variable yield
   - Ingredient quantities
3. To edit, click **"Edit Mix"**
4. Update ingredient quantities as needed
5. Click **"Save"**

---

## 💰 Commission Report

**Location:** Sales → **Commission Report**

### Viewing Commission Report

1. Go to **Sales** → **Commission Report**
2. Select date range
3. View:
   - Commission by salesperson
   - Total commission expense
   - Commission rates
   - Sales targets vs actual

### Understanding Commissions

- **Commission Rate:** Percentage of revenue (e.g., 7%)
- **Sales Target:** Monthly target amount
- Commission is calculated on returned dispatches (actual sales)

---

## 📉 Analytics Dashboard

**Location:** Main Menu → **Analytics**

### Available Analytics

| View | What It Shows |
|------|---------------|
| Overview | Key metrics, trends, summaries |
| Product Performance | Best/worst selling products |
| Inventory Status | Stock levels, alerts |
| Sales Trends | Sales over time, patterns |
| Production Analytics | Production efficiency |
| Deficit Analysis | Shortages, variances |

### Using Filters

Most analytics views support:
- Date range selection
- Product filtering
- Comparison periods

---

## 📂 Expense Categories

Used to categorize expenses in reports:

1. Go to **Settings** → **Expense Categories**
2. View existing categories:
   - Salaries
   - Commissions
   - Transport
   - Utilities
   - Maintenance
   - etc.
3. Add new categories as needed

---

## 📋 Daily Checklist

| Time | Task |
|------|------|
| Morning | Review previous day's report |
| As needed | Record inventory purchases |
| As needed | Record indirect cost outputs |
| Weekly | Review weekly report |
| Monthly | Generate monthly P&L, review commissions |

---

## ⚠️ Important Notes

1. **Always record purchases promptly** - delays affect stock accuracy
2. **Verify costs before saving** - corrections are difficult
3. **Price changes are immediate** - but only affect new dispatches
4. **Reports are generated automatically** - but you can regenerate manually

---

## 📋 Quick Reference

| Task | Navigation |
|------|------------|
| View Daily Report | Reports → Daily Report |
| Record Purchase | Inventory → Create Purchase |
| Record Output | Inventory → Create Output |
| Update Price | Products → Select → Edit |
| View Commissions | Sales → Commission Report |
| View Analytics | Analytics → Select View |

---

**← Back to [Table of Contents](./README.md)**
