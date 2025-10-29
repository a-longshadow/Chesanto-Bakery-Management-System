# Inventory App - Model Field Reference
**Created:** October 29, 2025  
**Purpose:** Field name checklist for frontend development

---

## InventoryItem Model (Primary)

### Basic Information
- `name` (CharField, unique) - Item name
- `category` (FK to ExpenseCategory) - Expense category
- `description` (TextField, blank)

### Units & Purchasing
- `purchase_unit` (CharField, choices) - Unit for purchasing (e.g., 'bag')
- `recipe_unit` (CharField, choices) - Unit for recipes (e.g., 'kg')
- `conversion_factor` (DecimalField) - Convert purchase_unit to recipe_unit

**UNIT_CHOICES:**
- 'kg', 'g', 'l', 'ml', 'pcs', 'bag', 'jerycan', 'packet'

### Stock Tracking
- `current_stock` (DecimalField) - Current stock in recipe_unit
- `reorder_level` (DecimalField) - Alert threshold (7 days supply)

### Costing
- `cost_per_purchase_unit` (DecimalField) - Cost per purchase_unit (KES)
- `cost_per_recipe_unit` (DecimalField) - 🤖 AUTO-CALCULATED

### Alerts
- `low_stock_alert` (BooleanField) - 🤖 AUTO: True if current_stock < reorder_level
- `days_remaining` (IntegerField) - 🤖 AUTO: Calculated from usage rate

### Status
- `is_active` (BooleanField) - Soft delete

### Metadata
- `created_at` (DateTimeField, auto_now_add)
- `created_by` (FK to User)
- `updated_at` (DateTimeField, auto_now)
- `updated_by` (FK to User)

---

## Purchase Model

### Purchase Information
- `purchase_number` (CharField, unique) - Auto-generated: PUR-YYYYMMDD-XXX
- `supplier` (FK to Supplier)
- `purchase_date` (DateField)
- `expected_delivery_date` (DateField, nullable)
- `actual_delivery_date` (DateField, nullable)

### Status
- `status` (CharField, choices) - DRAFT, ORDERED, RECEIVED, CANCELLED
- `total_amount` (DecimalField) - 🤖 AUTO: Sum of all purchase items

### Notes
- `notes` (TextField, blank)

### Metadata
- `created_at` (DateTimeField)
- `created_by` (FK to User)
- `updated_at` (DateTimeField)
- `updated_by` (FK to User)

---

## PurchaseItem Model

- `purchase` (FK to Purchase, CASCADE)
- `item` (FK to InventoryItem, PROTECT)
- `quantity` (DecimalField) - Quantity in purchase_unit
- `unit_cost` (DecimalField) - Cost per purchase_unit (KES)
- `total_cost` (DecimalField) - 🤖 AUTO: quantity × unit_cost
- `added_at` (DateTimeField)

**Related Name:** `purchase.purchaseitem_set`

---

## WastageRecord Model

### Damage Details
- `item` (FK to InventoryItem)
- `damage_type` (CharField, choices) - SPILL, EXPIRED, DAMAGED, CONTAMINATED, OTHER
- `quantity` (DecimalField) - Quantity damaged (in recipe_unit)
- `cost` (DecimalField) - 🤖 AUTO: quantity × cost_per_recipe_unit
- `damage_date` (DateField)
- `description` (TextField)

### Approval (for > KES 500)
- `requires_approval` (BooleanField) - 🤖 AUTO: True if cost > KES 500
- `approval_status` (CharField, choices) - PENDING, APPROVED, REJECTED
- `approved_by` (FK to User, nullable) - CEO approval
- `approved_at` (DateTimeField, nullable)
- `approval_notes` (TextField, blank)

### Metadata
- `created_at` (DateTimeField)
- `created_by` (FK to User)

---

## Supplier Model

- `name` (CharField, unique)
- `contact_person` (CharField, blank)
- `phone` (CharField, blank)
- `email` (EmailField, blank)
- `address` (TextField, blank)
- `payment_terms` (CharField, blank)
- `is_active` (BooleanField)
- `created_at` (DateTimeField)
- `created_by` (FK to User)

---

## StockMovement Model (Audit Trail)

- `item` (FK to InventoryItem)
- `movement_type` (CharField, choices) - PURCHASE, PRODUCTION, DAMAGE, ADJUSTMENT, RETURN
- `quantity` (DecimalField) - Positive for additions, negative for deductions
- `unit` (CharField)
- `reference_type` (CharField, blank) - e.g., 'Purchase', 'ProductionBatch'
- `reference_id` (IntegerField, nullable)
- `notes` (TextField, blank)
- `stock_before` (DecimalField)
- `stock_after` (DecimalField)
- `created_at` (DateTimeField)
- `created_by` (FK to User)

---

## RestockAlert Model

- `item` (FK to InventoryItem)
- `alert_level` (CharField, choices) - LOW, CRITICAL, OUT
- `days_remaining` (IntegerField)
- `message` (TextField)
- `is_acknowledged` (BooleanField)
- `acknowledged_by` (FK to User, nullable)
- `acknowledged_at` (DateTimeField, nullable)
- `created_at` (DateTimeField)

---

## Key Patterns Identified

### Auto-Calculated Fields (Never show in forms):
- `cost_per_recipe_unit` - Calculated on save
- `total_cost` (Purchase/PurchaseItem) - Calculated on save
- `low_stock_alert` - Calculated on save
- `requires_approval` - Calculated on save
- `cost` (WastageRecord) - Calculated on save

### ForeignKey Relationships:
- InventoryItem → ExpenseCategory (category)
- InventoryItem → User (created_by, updated_by)
- Purchase → Supplier
- Purchase → User (created_by, updated_by)
- PurchaseItem → Purchase, InventoryItem
- WastageRecord → InventoryItem, User

### Status Fields with Choices:
- Purchase.status: DRAFT, ORDERED, RECEIVED, CANCELLED
- WastageRecord.damage_type: SPILL, EXPIRED, DAMAGED, CONTAMINATED, OTHER
- WastageRecord.approval_status: PENDING, APPROVED, REJECTED

### Date Fields:
- purchase_date (DateField)
- expected_delivery_date (DateField, nullable)
- actual_delivery_date (DateField, nullable)
- damage_date (DateField)

---

## Frontend Development Checklist

✅ Read all model files FIRST  
✅ Document field names and types  
✅ Identify auto-calculated fields (exclude from forms)  
✅ Verify ForeignKey relationships  
✅ Check choice fields for dropdowns  
✅ Note nullable/blank fields  
⏳ Create views with correct field names  
⏳ Create templates matching model structure  
⏳ Test immediately after each view
