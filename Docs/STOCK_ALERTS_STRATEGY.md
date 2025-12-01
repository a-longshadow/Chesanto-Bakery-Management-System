# 🚨 STOCK ALERTS IMPLEMENTATION STRATEGY

**Date:** November 28, 2025  
**Last Updated:** November 29, 2025  
**Status:** ✅ Merged into `INVENTORY_APP_WORKFLOWS.md`

---

## 📚 **THIS DOCUMENT HAS BEEN SUPERSEDED**

The stock alerts strategy is now fully documented in the comprehensive Inventory App specification.

**See:** `INVENTORY_APP_WORKFLOWS.md` → Section: **External Workflow 4: Stock Alerts**

---

## 📋 **QUICK SUMMARY**

### **Decision: Real-Time Alerts (No Cron Jobs)**
- ✅ Alerts created when stock changes (via deduction utilities)
- ✅ Uses existing `communications.EmailService` (DRY)
- ✅ Dashboard widget for manual review
- ✅ Email notifications on production/output creation

### **Key Components:**
| Component | Description |
|-----------|-------------|
| **StockAlert Model** | Shared table for all 23 items (event log) |
| **Dashboard Widget** | Color-coded alerts (critical/warning/ok) |
| **Email Notifications** | Via `EmailService.send_stock_alert()` |
| **Trigger Points** | `deduct_ingredients_atomic()`, `create_output_atomic()` |

### **Alert Levels:**
- 🚨 **CRITICAL** - Stock ≤ 0 (out of stock)
- ⚠️ **WARNING** - Stock < minimum_stock_level (low stock)

---

## � **RELATED DOCUMENTATION**

| Document | Section |
|----------|---------|
| `INVENTORY_APP_WORKFLOWS.md` | StockAlert model definition |
| `INVENTORY_APP_WORKFLOWS.md` | External Workflow 4: Stock Alerts |
| `INVENTORY_APP_WORKFLOWS.md` | User Flow 7: Stock Alert Flow (Mermaid) |
| `FOUNDATION_REFACTORING_PLAN.md` | Inventory App Summary |

---

**Note:** This file is kept for historical reference. All implementation details are in `INVENTORY_APP_WORKFLOWS.md`.
