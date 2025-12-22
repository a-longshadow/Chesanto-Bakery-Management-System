# 🚚 Dispatch Guide

> **Role:** Dispatch Officer | **Access Level:** Sales Dispatches + Stock View

As a Dispatch Officer, you manage the flow of products from the bakery to salespeople: creating dispatches, tracking crates, and processing returns.

---

## 🎯 Your Responsibilities

- Create dispatches for salespeople
- Assign products and crates to dispatches
- Process returns when salespeople come back
- Track crate status (out/returned)
- View available stock before dispatching

---

## 🏠 Sales Dashboard

**Location:** Main Menu → **Sales**

The dashboard shows:
- Today's dispatches (pending and completed)
- Total products dispatched today
- Total returns processed
- Crates out vs returned

---

## 📤 Creating a New Dispatch

When a salesperson is ready to go out:

### Step 1: Access Dispatch Creation

1. Go to **Sales** → **New Dispatch**

### Step 2: Select Salesperson

2. Select the **Salesperson** from the dropdown
   - Only active salespeople are shown
   - If someone is missing, contact Admin

### Step 3: Check Available Stock

3. The system shows **available stock** for each product:
   - Bread: X units available
   - Scones: X units available
   - KDF: X units available
   - Family Bread 800g: X units available

**Important:** You cannot dispatch more than available stock.

### Step 4: Enter Quantities

4. Enter the quantity for each product to dispatch:
   - Only enter products the salesperson is taking
   - Leave others at 0

### Step 5: Crates

5. Enter the number of **crates** being taken:
   - Crates are tracked for return
   - Count physical crates given

### Step 6: Review and Create

6. Review the dispatch summary:
   - Salesperson name
   - Products and quantities
   - Number of crates
7. Click **"Create Dispatch"**

### What Happens

- Dispatch is created with status "Dispatched"
- Stock is deducted from available inventory
- Dispatch number is generated (e.g., DSP-20251222-001)
- Dispatch appears in the list

### Printing (Optional)

If you need a printed dispatch slip:
1. View the dispatch details
2. Click **"Print"**

---

## 📋 Viewing Dispatches

**Location:** Sales → **All Dispatches**

### Dispatch List

Shows all dispatches with:

| Column | Meaning |
|--------|---------|
| Dispatch # | Unique identifier (click to view details) |
| Salesperson | Who took the products |
| Date | When dispatched |
| Products | What was dispatched |
| Crates | Number of crates out |
| Status | Dispatched / Returned |
| Revenue | (shows after return processed) |

### Filtering Dispatches

Use filters to find specific dispatches:
- **Date range:** Today, yesterday, last 7 days, custom
- **Salesperson:** Filter by specific person
- **Status:** Dispatched only, Returned only, All

### Dispatch Details

Click on a dispatch number to see:
- Full product breakdown
- Salesperson information
- Dispatch time
- Return information (if processed)

---

## 📥 Processing Returns

When a salesperson returns from selling:

### Step 1: Find the Dispatch

1. Go to **Sales** → **All Dispatches**
2. Find the dispatch (filter by salesperson or today's date)
3. Click **"Process Return"** on the dispatch

### Step 2: Enter Returns

4. For each product, enter what the salesperson returned:

| Product | Dispatched | Returned | Sold |
|---------|------------|----------|------|
| Bread | 50 | 5 | 45 (auto-calculated) |
| Scones | 30 | 2 | 28 (auto-calculated) |

- **Returned:** How many unsold products came back
- **Sold:** Automatically calculated (Dispatched - Returned)

### Step 3: Select Return Quality

5. For each returned product, select **quality**:
   - **Good:** Goes to Leftovers stock (can be sold tomorrow)
   - **Reject:** Will be disposed as waste

### Step 4: Crates Returned

6. Enter number of **crates returned**
   - Should match what was dispatched
   - Note any missing crates

### Step 5: Review and Submit

7. Review the return summary:
   - Products sold (revenue calculated)
   - Products returned (going to leftovers or waste)
   - Commission calculated (based on sales)
   - Crate status
8. Click **"Process Return"**

### What Happens

- Dispatch status changes to "Returned"
- Revenue is calculated and recorded
- Commission is calculated for the salesperson
- Good returns are added to Leftovers stock
- Rejected returns are recorded as waste
- Crate status is updated

---

## 📦 Viewing Stock

**Location:** Production → **Stock Dashboard**

Before creating dispatches, check available stock:

1. Go to **Production** → **Stock Dashboard**
2. View current stock for each product
3. Only dispatch what's available

**Note:** Stock updates in real-time as:
- Production adds stock (batches)
- Dispatches remove stock
- Returns add back to Leftovers stock

---

## 📊 Crate Tracking

### Crates Out

When you create a dispatch, enter crates given to salesperson.

### Crates Returned

When processing returns, enter crates brought back.

### Missing Crates

If crates are missing:
- Note in the return process
- Report to supervisor
- Crate discrepancies are tracked

---

## 📋 Daily Checklist

| Time | Task |
|------|------|
| Morning | Check stock levels |
| Morning | Create dispatches for departing salespeople |
| Throughout Day | Process returns as salespeople come back |
| End of Day | Verify all dispatches have returns processed |
| End of Day | Check crate counts |

---

## ⚠️ Important Rules

1. **Never dispatch more than available stock**
2. **Process returns the same day** - don't let them accumulate
3. **Be accurate with returned quantities** - affects sales calculations
4. **Track all crates** - they're company assets
5. **Good vs Reject matters** - affects stock and waste reporting

---

## 📋 Quick Reference

| Task | Navigation |
|------|------------|
| Create Dispatch | Sales → New Dispatch |
| View All Dispatches | Sales → All Dispatches |
| Process Return | Sales → All Dispatches → Process Return |
| Check Stock | Production → Stock Dashboard |
| View Dispatch Details | Sales → All Dispatches → Click dispatch # |

---

## ❓ Common Questions

### Q: What if a salesperson loses products?
Enter 0 returned. The "sold" amount will include the loss. Note it for management.

### Q: What if returns are partially good, partially bad?
Process them separately if possible, or note in comments. The system allows quality selection per product.

### Q: What if stock shows available but products aren't physically there?
Report the discrepancy to Production Manager. There may be a recording error.

### Q: What if I create a dispatch by mistake?
Contact Admin to void/cancel the dispatch before it's processed.

### Q: Can a salesperson have multiple dispatches in one day?
Yes, but usually it's one dispatch per trip. Each dispatch is tracked separately.

---

**← Back to [Table of Contents](./README.md)**
