# Manual Testing Checklist: Data Management Feature

**Created:** January 2026  
**Feature:** Dependency-aware record deletion + Full System Reset  
**Automated Tests:** 13 tests in `apps/core/tests/test_data_management.py`

---

## Pre-requisites

1. Start the development server:
   ```bash
   python manage.py runserver
   ```

2. Have users with these roles available:
   - **Primary SUPERADMIN** (`is_primary_superadmin=True`)
   - **Regular SUPERADMIN** (`is_primary_superadmin=False`)
   - **ADMIN** role
   - **SALESMAN** role

---

## 1. Delete Button Visibility Tests

### 1.1 Purchase Delete Button (SUPERADMIN only)

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **SALESMAN** | | |
| 2 | Go to Inventory > any item > Purchase History | | |
| 3 | Look for "Delete" button | ❌ No delete button visible | ☐ |
| 4 | Log out | | |
| 5 | Log in as **SUPERADMIN** | | |
| 6 | Go to Inventory > any item > Purchase History | | |
| 7 | Look for "Delete" button | ✅ Delete button visible for deletable purchases | ☐ |

### 1.2 Batch Delete Button (SUPERADMIN only)

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **ADMIN** | | |
| 2 | Go to Production > Batches > any batch detail | | |
| 3 | Look for "Delete Batch" button | ❌ No delete button visible | ☐ |
| 4 | Log out | | |
| 5 | Log in as **SUPERADMIN** | | |
| 6 | Go to Production > Batches > any batch detail | | |
| 7 | Look for "Delete Batch" button | ✅ Delete button visible | ☐ |

### 1.3 Dispatch Delete Button (SUPERADMIN only)

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **SALESMAN** | | |
| 2 | Go to Sales > Dispatches > any dispatch detail | | |
| 3 | Look for "Delete" button | ❌ No delete button visible | ☐ |
| 4 | Log out | | |
| 5 | Log in as **SUPERADMIN** | | |
| 6 | Go to Sales > Dispatches > any dispatch detail | | |
| 7 | Look for "Delete" button | ✅ Delete button visible for deletable dispatches | ☐ |

---

## 2. Dependency Blocking Tests

### 2.1 Purchase with Batch Dependency

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **SUPERADMIN** | | |
| 2 | Create a purchase for an ingredient | | |
| 3 | Create a batch that uses that ingredient | | |
| 4 | Go to the purchase history for that ingredient | | |
| 5 | Look at the purchase's delete button | ❌ Button disabled/grayed with tooltip "Used in X batch(es)" | ☐ |
| 6 | Delete the batch | | |
| 7 | Refresh the purchase history page | | |
| 8 | Look at the purchase's delete button | ✅ Button now active/clickable | ☐ |

### 2.2 Batch with Dispatch Dependency

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **SUPERADMIN** | | |
| 2 | Create a batch | | |
| 3 | Create a dispatch that includes products from that batch | | |
| 4 | Go to the batch detail page | | |
| 5 | Look at the "Delete Batch" button | ❌ Button disabled with message about dispatch dependency | ☐ |
| 6 | Delete the dispatch | | |
| 7 | Refresh the batch detail page | | |
| 8 | Look at the "Delete Batch" button | ✅ Button now active/clickable | ☐ |

### 2.3 Dispatch with SalesReturn Dependency

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **SUPERADMIN** | | |
| 2 | Create a dispatch to a customer | | |
| 3 | Process a return for that dispatch | | |
| 4 | Go to the dispatch detail page | | |
| 5 | Look at the "Delete" button | ❌ Button disabled with message about return processed | ☐ |
| 6 | Note: Returns CANNOT be deleted | Dispatch is permanently locked | ☐ |

---

## 3. Delete Confirmation Flow Tests

### 3.1 Purchase Delete Flow

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **SUPERADMIN** | | |
| 2 | Go to a deletable purchase | | |
| 3 | Click "Delete" button | Confirmation page appears with purchase details | ☐ |
| 4 | Check warning message | Shows what will be reversed (stock, costs) | ☐ |
| 5 | Click "Cancel" | Returns to previous page, no changes | ☐ |
| 6 | Click "Delete" again | Confirmation page appears | ☐ |
| 7 | Click "Confirm Delete" | Purchase deleted, success message shown | ☐ |
| 8 | Check stock levels | Stock reduced by deleted purchase quantity | ☐ |

### 3.2 Batch Delete Flow

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **SUPERADMIN** | | |
| 2 | Go to a deletable batch | | |
| 3 | Click "Delete Batch" button | Confirmation page appears with batch details | ☐ |
| 4 | Check warning message | Shows what will be reversed | ☐ |
| 5 | Click "Cancel" | Returns to batch detail, no changes | ☐ |
| 6 | Click "Delete Batch" again | Confirmation page appears | ☐ |
| 7 | Click "Confirm Delete" | Batch deleted, success message shown | ☐ |
| 8 | Check ingredient stock | Ingredients restored | ☐ |
| 9 | Check product stock | Product stock reduced | ☐ |

### 3.3 Dispatch Delete Flow

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **SUPERADMIN** | | |
| 2 | Go to a deletable dispatch | | |
| 3 | Click "Delete" button | Confirmation page appears with dispatch details | ☐ |
| 4 | Check warning message | Shows what will be reversed | ☐ |
| 5 | Click "Cancel" | Returns to dispatch detail, no changes | ☐ |
| 6 | Click "Delete" again | Confirmation page appears | ☐ |
| 7 | Click "Confirm Delete" | Dispatch deleted, success message shown | ☐ |
| 8 | Check product stock | Stock restored to warehouse | ☐ |
| 9 | Check crates out | Crates returned to inventory | ☐ |

---

## 4. Full System Reset Tests

### 4.1 Access Control

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **ADMIN** | | |
| 2 | Navigate to `/admin/data-management/full-reset/` | ❌ Redirected/Access Denied | ☐ |
| 3 | Log out | | |
| 4 | Log in as **Regular SUPERADMIN** | | |
| 5 | Navigate to `/admin/data-management/full-reset/` | ❌ Redirected/Access Denied | ☐ |
| 6 | Log out | | |
| 7 | Log in as **Primary SUPERADMIN** | | |
| 8 | Navigate to `/admin/data-management/full-reset/` | ✅ Page loads with reset form | ☐ |

### 4.2 Reset Confirmation

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **Primary SUPERADMIN** | | |
| 2 | Go to Full System Reset page | | |
| 3 | Check type confirmation phrase required | Must type exact phrase | ☐ |
| 4 | Type wrong phrase, click Reset | ❌ Error message shown | ☐ |
| 5 | Type correct phrase, click Reset | ⚠️ Second confirmation required | ☐ |
| 6 | Confirm reset | Reset executes | ☐ |
| 7 | Check all data tables | All transactional data cleared | ☐ |
| 8 | Check user accounts | Users preserved | ☐ |
| 9 | Check products/recipes | Master data preserved | ☐ |

---

## 5. SalesReturn Immutability Tests

### 5.1 No Delete Option

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Log in as **Primary SUPERADMIN** | | |
| 2 | Go to Sales > Returns | | |
| 3 | Click on any return to view details | | |
| 4 | Look for any "Delete" button | ❌ No delete button anywhere | ☐ |

### 5.2 Limited Edit Options

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Go to a SalesReturn detail page | | |
| 2 | Look for editable fields | Only crates_marked_lost, crates_marked_damaged editable | ☐ |
| 3 | Try to access edit URL manually | ❌ Not available or only crate fields editable | ☐ |

---

## 6. Audit Log Verification

| Step | Action | Expected Result | Pass? |
|------|--------|-----------------|-------|
| 1 | Perform a purchase delete as SUPERADMIN | | |
| 2 | Check audit log | Delete action recorded with user, timestamp, details | ☐ |
| 3 | Perform a batch delete as SUPERADMIN | | |
| 4 | Check audit log | Delete action recorded | ☐ |
| 5 | Perform a dispatch delete as SUPERADMIN | | |
| 6 | Check audit log | Delete action recorded | ☐ |
| 7 | Perform full system reset | | |
| 8 | Check audit log | Reset action recorded (audit log itself preserved) | ☐ |

---

## Summary

| Test Category | Total Tests | Passed | Failed |
|---------------|-------------|--------|--------|
| Delete Button Visibility | 6 | | |
| Dependency Blocking | 6 | | |
| Delete Confirmation Flow | 11 | | |
| Full System Reset | 11 | | |
| SalesReturn Immutability | 3 | | |
| Audit Log Verification | 8 | | |
| **TOTAL** | **45** | | |

---

## Notes

- **Automated tests cover**: Access control, dependency logic, SalesReturn immutability
- **Manual tests required for**: Visual rendering, button styling, confirmation UX, stock verification, audit logs
- **Critical**: Never test Full System Reset on production without a backup!

---

Tested by: _____________________  
Date: _____________________  
Environment: ☐ Local ☐ Staging ☐ Production
