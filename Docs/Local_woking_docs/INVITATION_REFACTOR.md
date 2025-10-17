# User Invitation System Refactor

## Date: October 17, 2025

## Problem
- Duplicate logic between frontend view (`/auth/invite/`) and Django admin
- Inconsistent behavior depending on where invitation was created
- Field name errors (`is_accepted` vs `used_at`, `is_used` vs `used_at`)
- More code = more bugs

## Solution: Admin-Only Pattern

### What Changed
1. **Removed** `/auth/invite/` view completely
2. **Removed** `invite_user_view()` function from views.py
3. **Removed** URL route from urls.py
4. **Updated** navbar to show only "Admin" link (removed "Invite User")
5. **Kept** Django admin as single source of truth

### How It Works Now

#### Creating Invitations (via Django Admin)
1. Admin goes to `/admin/accounts/userinvitation/add/`
2. Fills in: email, full_name, role
3. Saves the invitation

#### Automatic Process (via Signal)
When invitation is saved, `create_user_from_invitation` signal:
1. ✅ Auto-generates temporary password (12 characters)
2. ✅ Creates User account with:
   - `is_active=True`
   - `is_approved=True`
   - `must_change_password=True`
3. ✅ Sends invitation email with temp password
4. ✅ All in one atomic operation

#### User Experience
1. User receives email with temp password
2. User logs in immediately (no waiting for approval)
3. System forces password change on first login
4. After password change, invitation marked as `used_at=<timestamp>`

### Benefits
✅ **Single source of truth** - Admin interface only  
✅ **No duplicate logic** - Signal handles everything  
✅ **Consistent behavior** - Works same way every time  
✅ **Less code** - Removed ~80 lines  
✅ **Better maintainability** - Fix once, works everywhere  
✅ **Professional** - Uses Django admin properly  

### Files Modified
- `apps/accounts/views.py` - Removed `invite_user_view()`
- `apps/accounts/urls.py` - Removed `/auth/invite/` route
- `apps/accounts/templates/accounts/base.html` - Updated navbar
- `apps/accounts/signals.py` - Enhanced signal to auto-create users + send emails

### Files Obsolete (can be deleted later)
- `apps/accounts/templates/accounts/invite_user.html` - No longer used

### Admin Workflow
```
/admin/ → User invitations → Add user invitation
↓
Fill form: email, full name, role
↓
Save
↓
Signal fires automatically:
  - Creates user account
  - Sends email
  - Shows admin confirmation
```

### Code Architecture
```
Django Admin (User Input)
    ↓
UserInvitation.save()
    ↓
post_save signal fires
    ↓
create_user_from_invitation()
    ├── Create User account
    └── Send invitation email
```

## Design Principle Applied
**"Admin as source of truth"** - Frontend should extend admin functionality, not duplicate it. For staff-only operations, use Django admin directly rather than creating custom views.
