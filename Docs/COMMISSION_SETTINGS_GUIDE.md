# 💰 Commission Settings - Quick Reference Guide

**For:** Superadmin users  
**Purpose:** Configure and manage commission rates  
**Access:** Django Admin Panel

---

## 🎯 Overview

The Commission Settings system allows superadmins to configure commission rates without modifying code. All sales returns will automatically use the active commission settings.

### Commission Structure:
1. **Per-Unit Commission:** Fixed amount paid per unit sold (e.g., KES 5 per unit)
2. **Bonus Commission:** Percentage of revenue above a threshold (e.g., 7% above KES 35,000)

---

## 📖 How to Access

1. Log in to Django Admin: `http://yourdomain.com/admin/`
2. Navigate to **SALES** section
3. Click **Commission Settings**

---

## ➕ Creating New Commission Settings

### Step 1: Add New Settings
1. Click **"ADD COMMISSION SETTINGS"** button (top right)
2. Fill in the form:

   ```
   Per unit commission: 5.00
   Bonus threshold: 35000.00
   Bonus percentage: 7.00
   Effective from: 2025-11-04  (when these rates become active)
   Is active: ✅ (check this box)
   Notes: (optional explanation, e.g., "Increased per-unit rate due to inflation")
   ```

3. Click **"SAVE"**

### Step 2: Automatic Deactivation
- When you check "Is active" on a new setting, all previous settings are automatically deactivated
- Only ONE setting can be active at any time
- This ensures consistent rates across all new returns

---

## 🔄 Changing Commission Rates

### Scenario 1: Rate Increase
**Example:** Increase per-unit commission from KES 5 to KES 6

1. Create new CommissionSettings:
   - Per unit commission: **6.00** (increased)
   - Bonus threshold: 35000.00 (unchanged)
   - Bonus percentage: 7.00 (unchanged)
   - Effective from: **2025-12-01** (future date)
   - Is active: ✅

2. **Result:**
   - Returns created before 2025-12-01 use old rates (KES 5)
   - Returns created after 2025-12-01 use new rates (KES 6)

### Scenario 2: Adjust Bonus Structure
**Example:** Increase bonus to 10% above KES 40,000

1. Create new CommissionSettings:
   - Per unit commission: 5.00 (unchanged)
   - Bonus threshold: **40000.00** (increased)
   - Bonus percentage: **10.00** (increased)
   - Effective from: 2025-12-01
   - Is active: ✅

2. **Result:**
   - Salespeople now need KES 40,000 in sales to trigger bonus
   - But earn 10% instead of 7% on the excess

### Scenario 3: Remove Bonus Temporarily
**Example:** Pause bonus during slow season

1. Create new CommissionSettings:
   - Per unit commission: 5.00 (unchanged)
   - Bonus threshold: **999999.00** (unreachably high)
   - Bonus percentage: 0.00 (disabled)
   - Effective from: 2025-06-01 (start of slow season)
   - Is active: ✅

2. Create another to re-enable later:
   - (Set for 2025-09-01 with original bonus structure)

---

## 📊 Viewing Current Settings

### Admin List View Shows:
- **Effective From:** When these rates became/become active
- **Per Unit:** Current per-unit commission (green highlight)
- **Bonus Structure:** "X% above KES Y"
- **Is Active:** ✅ (only one should be checked)
- **Updated At:** Last modification date
- **Updated By:** Who made the change

### Sorting & Filtering:
- **Filter by:** Is Active, Effective From
- **Search by:** Notes field
- **Order by:** Effective From (newest first by default)

---

## 🛡️ Important Rules

### 1. Only One Active Setting
- System enforces singleton pattern
- Creating a new active setting deactivates all others
- Cannot have overlapping active periods

### 2. Cannot Delete Active Settings
- Active settings are protected from deletion
- Must deactivate first, then delete

### 3. Historical Data Preserved
- Old returns keep their original commission amounts
- Changing settings does NOT recalculate past commissions
- Audit trail maintained indefinitely

### 4. Per-Salesperson Overrides (Advanced)
The system checks rates in this order:
1. Salesperson-specific rates (Bread/KDF/Scones fields)
2. CommissionSettings (system-wide default)
3. Hardcoded fallback (KES 5.00)

**Example:**
- CommissionSettings: KES 5 per unit
- Salesperson.commission_per_bread: KES 6
- Result: Bread sales earn KES 6, other products earn KES 5

---

## 🧮 Commission Calculation Examples

### Example 1: Standard Commission
**Settings:**
- Per unit: KES 5
- Bonus threshold: KES 35,000
- Bonus percentage: 7%

**Sales Return:**
- Units sold: 100
- Revenue: KES 30,000

**Calculation:**
- Per-unit: 100 × KES 5 = **KES 500**
- Bonus: KES 0 (below threshold)
- **Total: KES 500**

### Example 2: With Bonus
**Settings:**
- Per unit: KES 5
- Bonus threshold: KES 35,000
- Bonus percentage: 7%

**Sales Return:**
- Units sold: 150
- Revenue: KES 45,000

**Calculation:**
- Per-unit: 150 × KES 5 = **KES 750**
- Bonus: (45,000 - 35,000) × 7% = **KES 700**
- **Total: KES 1,450**

### Example 3: High Performer
**Settings:**
- Per unit: KES 6 (increased)
- Bonus threshold: KES 35,000
- Bonus percentage: 10% (increased)

**Sales Return:**
- Units sold: 200
- Revenue: KES 60,000

**Calculation:**
- Per-unit: 200 × KES 6 = **KES 1,200**
- Bonus: (60,000 - 35,000) × 10% = **KES 2,500**
- **Total: KES 3,700**

---

## 📱 Where Commission Rates Display

### 1. Sales Return Form
- Shows current rates in info box
- Example: "ℹ️ Current Rate: KES 5 per unit (7% bonus above KES 35,000)"

### 2. Sales Return Detail Page
- Commission breakdown card
- Shows per-unit and bonus amounts separately

### 3. Commission Report
- Info box at top: "📊 Commission Structure"
- Lists current rates for reference

### 4. Admin Panel
- Commission Settings list view
- Individual SalesReturn records

---

## ⚠️ Troubleshooting

### Issue: New rates not applying
**Check:**
1. Is new setting marked "Is active"? ✅
2. Is "Effective from" date in the past or today?
3. Clear browser cache and refresh page
4. Check if salesperson has override rates set

### Issue: Can't delete old settings
**Solution:**
- Active settings cannot be deleted (protection)
- Uncheck "Is active" first, then delete
- Or just leave inactive settings (acts as history)

### Issue: Bonus not calculating
**Check:**
1. Is revenue above bonus threshold?
2. Is bonus percentage > 0?
3. Check for revenue deficits (reduce total revenue)

### Issue: Different salespeople show different rates
**Explanation:**
- Per-salesperson overrides take precedence
- Check Salesperson model fields:
  - commission_per_bread
  - commission_per_kdf
  - commission_per_scones
- If set, these override CommissionSettings

---

## 📈 Best Practices

### 1. Plan Ahead
- Set "Effective from" dates in advance
- Create future settings before they're needed
- Review rates quarterly

### 2. Document Changes
- Always fill in "Notes" field
- Explain WHY rates changed
- Example: "Q4 bonus increase to drive sales"

### 3. Communicate Changes
- Notify salespeople before new rates take effect
- Post announcements in team meetings
- Send email reminders

### 4. Monitor Impact
- Check commission report after rate changes
- Compare average commission before/after
- Adjust if needed

### 5. Audit Regularly
- Review historical settings monthly
- Check for errors or inconsistencies
- Verify "Updated by" field shows correct user

---

## 🔐 Permissions

### Who Can Access:
- ✅ Superusers (full access)
- ❌ Regular staff (read-only if needed)
- ❌ Salespeople (hidden from them)

### Adding Permission:
If you want managers (not superusers) to edit settings:

1. Go to **Admin → Groups**
2. Create "Commission Managers" group
3. Add permission: `sales | commission settings | Can change commission settings`
4. Assign users to this group

---

## 📞 Support

**Questions?**
- Contact: System Administrator
- Email: admin@chesantobakery.com
- Documentation: `/docs/SALES_UI_IMPROVEMENTS_SUMMARY.md`

**Report Issues:**
- If commission calculations seem wrong
- If settings aren't saving
- If active settings conflict

---

**Last Updated:** November 4, 2025  
**Version:** 1.0
