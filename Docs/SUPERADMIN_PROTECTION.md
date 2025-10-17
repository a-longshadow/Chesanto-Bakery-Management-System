# SUPERADMIN Protection Safeguards

## Overview
This document describes the security safeguards implemented to protect SUPERADMIN accounts from unauthorized modifications.

## Protection Rules

### 1. Primary SUPERADMIN Protection
The first/primary SUPERADMIN (typically the CEO or System Owner) has special protections:

- **Cannot be edited by anyone except themselves**
- **Cannot be deleted by anyone**
- **Cannot have their role changed**
- **Is designated using the management command**

#### How to Designate Primary SUPERADMIN
```bash
python manage.py set_primary_superadmin user@example.com
```

This command:
- Sets the `is_primary_superadmin` flag to `True`
- Ensures only one Primary SUPERADMIN exists at a time
- Prompts for confirmation if replacing an existing Primary SUPERADMIN

### 2. Mutual SUPERADMIN Protection
SUPERADMINs cannot modify other SUPERADMIN accounts:

- **SUPERADMIN A cannot edit SUPERADMIN B's profile**
- **SUPERADMIN A cannot delete SUPERADMIN B**
- **SUPERADMINs can only edit their own profiles**

This prevents:
- Privilege escalation attacks
- Unauthorized role changes
- Account hijacking between administrators

### 3. Self-Edit Only for SUPERADMINs
Each SUPERADMIN has full control over their own account:

- ✅ Can edit their own profile (all fields)
- ✅ Can upload/change their own profile photo
- ✅ Can update their own contact information
- ❌ Cannot edit other SUPERADMIN accounts
- ❌ Cannot delete other SUPERADMIN accounts

## Implementation Details

### Model Changes (`apps/accounts/models.py`)

#### New Field
```python
is_primary_superadmin = models.BooleanField(
    default=False,
    help_text="Reserved for the first/primary SUPERADMIN (CEO/System Owner)"
)
```

#### New Methods
```python
def can_edit_user(self, target_user):
    """Check if this user can edit the target user's profile"""
    # Returns True/False based on protection rules

def can_delete_user(self, target_user):
    """Check if this user can delete the target user"""
    # Returns True/False based on protection rules
```

### View Changes (`apps/accounts/views.py`)

#### Updated `profile_edit_view`
- Now accepts optional `user_id` parameter for editing other users
- Enforces protection rules using `can_edit_user()` method
- Limits field editing based on user role and permissions
- Tracks changes via `UserProfileChange` model

**Field Access Rules:**
- **SUPERADMIN editing self:** All fields editable
- **SUPERADMIN editing non-SUPERADMIN:** All fields editable
- **Regular user editing self:** Only `mobile_secondary`, `mobile_tertiary`, and photo editable
- **SUPERADMIN editing another SUPERADMIN:** ❌ Blocked

### Admin Changes (`apps/accounts/admin.py`)

#### Enhanced Security
```python
def get_readonly_fields(self, request, obj=None):
    # Makes critical fields read-only for protected accounts

def has_delete_permission(self, request, obj=None):
    # Uses can_delete_user() to enforce deletion rules
```

**Django Admin Protections:**
- Primary SUPERADMIN fields are read-only to other admins
- SUPERADMIN role/permissions cannot be changed by other SUPERADMINs
- Delete button is hidden for protected accounts

### URL Changes (`apps/accounts/urls.py`)

New URL pattern for admin editing other users:
```python
path('profile/edit/<int:user_id>/', views.profile_edit_view, name='profile_edit_other')
```

### Template Changes (`profile_edit.html`)

Added visual warnings:
- **Primary SUPERADMIN warning:** Shows when attempting to edit Primary SUPERADMIN
- **SUPERADMIN protection info:** Explains why SUPERADMINs cannot edit each other

## Migration

Migration file: `apps/accounts/migrations/0005_user_is_primary_superadmin.py`

To apply:
```bash
python manage.py migrate accounts
```

## Usage Examples

### Example 1: Designate Primary SUPERADMIN
```bash
# Set the CEO as Primary SUPERADMIN
python manage.py set_primary_superadmin ceo@chesanto.com

# Output:
# ✓ Successfully designated ceo@chesanto.com as Primary SUPERADMIN
#   Name: John Doe
#   Role: CEO / Developer
# 
# Protections Applied:
#   • Cannot be edited by other SUPERADMINs
#   • Cannot be deleted by anyone
#   • Can only be modified by themselves
```

### Example 2: SUPERADMIN Editing Their Own Profile
```python
# SUPERADMIN logs in and navigates to /profile/edit/
# They can edit ALL fields:
# - Basic info (name, mobile)
# - Employee info (ID, national ID, position)
# - Profile photo
```

### Example 3: SUPERADMIN Attempting to Edit Another SUPERADMIN
```python
# SUPERADMIN A tries to access /profile/edit/123/
# where user 123 is SUPERADMIN B
# 
# Result: ❌ Error message
# "You do not have permission to edit this user."
# Redirect to their own profile
```

### Example 4: Regular User Editing Their Profile
```python
# Regular user logs in and navigates to /profile/edit/
# They can ONLY edit:
# - mobile_secondary
# - mobile_tertiary
# - profile_photo
# 
# All other fields are read-only (gray background)
```

## Security Benefits

1. **Prevents Privilege Escalation:** No SUPERADMIN can promote themselves by demoting others
2. **Protects System Owner:** Primary SUPERADMIN account cannot be compromised by other admins
3. **Audit Trail Integrity:** Changes are tracked with `UserProfileChange` model
4. **Role Isolation:** Clear separation between self-editing and admin functions
5. **Fail-Safe Design:** Multiple layers of protection (model, view, admin, template)

## Testing Checklist

- [ ] Create a SUPERADMIN account
- [ ] Designate as Primary SUPERADMIN using management command
- [ ] Try to edit Primary SUPERADMIN from another SUPERADMIN account (should fail)
- [ ] Try to delete Primary SUPERADMIN from Django admin (should be blocked)
- [ ] Create a second SUPERADMIN account
- [ ] Try to edit second SUPERADMIN from first SUPERADMIN (should fail)
- [ ] Edit own SUPERADMIN profile (should succeed with all fields)
- [ ] Login as regular user and try to edit profile (should only allow mobile fields + photo)
- [ ] Check that `is_primary_superadmin` field is read-only in admin for non-primary admins

## Related Files

- `apps/accounts/models.py` - User model with protection logic
- `apps/accounts/views.py` - Profile editing views with safeguards
- `apps/accounts/admin.py` - Django admin with protection enforcement
- `apps/accounts/urls.py` - URL routing for profile editing
- `apps/accounts/templates/accounts/profile_edit.html` - Template with warnings
- `apps/accounts/management/commands/set_primary_superadmin.py` - Management command

## Notes

- Only ONE Primary SUPERADMIN can exist at a time
- The Primary SUPERADMIN designation can be transferred using the management command
- These protections are enforced at multiple layers (model, view, admin, database)
- All profile changes are logged in the `UserProfileChange` model for audit purposes
