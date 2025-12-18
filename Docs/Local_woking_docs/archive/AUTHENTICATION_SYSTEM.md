# Authentication System - Complete Specification
**Project:** Chesanto Bakery Management System  
**Date:** October 15, 2025  
**Status:** ✅ APPROVED BY CEO  
**Priority:** URGENT - Week of Oct 12-18, 2025

---

# PART 1: HIGH-LEVEL OVERVIEW (FOR HUMANS)

## Executive Summary

Secure authentication system that prevents unauthorized access and tracks all user activity. Priority driven by **90,000 KES loss** from inability to track who did what.

## Why We Need This

**Real Business Problem:**
- 90,000 KES goods disappeared - no tracking
- 20,000 KES deficit undetected for a month
- No accountability for data changes 

**Solution:**
- All users must login with email verification
- All actions logged (who, what, when, from where)
- Admin sees everything

## How It Works

### For New Staff

**Option A: Admin Invite (Existing Staff)**
1. Admin fills form: Email +  Name (first, last or both) + Role
2. System creates account with **random** temp password (e.g., `Kx9mP2vL`)
3. Email sent with:
   - Login URL: `https://yourserver.com/login`
   - Email: `staff@company.com`
   - Password: `Kx9mP2vL` (unique random 8-character password)
   - "Change password after first login"
4. Staff login → Forced to change password → Start working

**Option B: Self-Registration (New Hires)**
1. Fill complete registration form (email, password, name, phone, role)
2. Account created but INACTIVE
3. See message: "Registration complete. Awaiting admin approval."
4. Admin approves → Account ACTIVATED
5. Redirected to home page → Start working
6. Confirmation email sent

**Special: Superadmin Emails (Auto-Approved) - list can be modified**
- `madame@chesanto.com` (CEO)
- `joe@coophive.network` (Developer)
- Skip approval → Instant ACTIVE **superadmin** access
- Role: SUPERADMIN (not Admin)
- **Set in .env file:** `SUPERADMIN_EMAILS="madame@chesanto.com,joe@coophive.network"`
- **Setup Confirmation:** System reads from .env on registration to auto-approve superadmins

### Daily Login

1. Enter email + password
2. **IF** < 24hrs since last login → In!
3. **IF** ≥ 24hrs → Check email for 6-digit code (valid 10 min)
4. Enter code → In!

**Why 24hr re-auth?** Security. Prevents stolen passwords from working forever.

### Forgot Password

1. Click "Forgot Password"
2. Enter email
3. Get 6-digit code (valid 15 min)
4. Enter code
5. Set new password
6. Done (confirmation email sent)

### Session Rules

- **1hr inactivity** → Auto logout (ONLY if no unsaved data or active operations)
- **24hrs since password** → Prompt for re-auth (does NOT force logout during active work)
- **No "trust device"** → Security first
- **All pages require auth** → No unauthorized access
- **Smart Logout:** System detects unsaved data/active forms and delays logout until safe

## User Roles (Chesanto Hierarchy)

| Technical Role | Chesanto Title | Access Level | Permissions | Can Be Modified By |
|----------------|----------------|--------------|-------------|-------------------|
| **SUPERADMIN** | CEO / Developer | 100% | Everything - Create/edit/delete users, modify permissions, see all logs, override all actions, system config | N/A (Hardcoded) |
| **ADMIN** | Accountant | 90% | Financial data entry, petty cash, all reports, approve transactions, user management (except superadmin) | Superadmin |
| **PRODUCT_MANAGER** | Production Manager | 70% | Production data, recipes, inventory, production reports, staff schedules | Superadmin |
| **DEPT_HEAD** | Department Head | 60% | Team data, department reports, staff attendance, limited approvals | Superadmin |
| **DISPATCH** | Dispatch Officer | 40% | Crate tracking, deliveries, vehicle logs, dispatch reports | Superadmin, Admin |
| **SALESMAN** | Sales Representative | 30% | Sales entry (mandatory daily), customer data, own sales reports, commission tracking (see Sales Module) | Superadmin, Admin |
| **SECURITY** | Gate Man / Security | 20% | Entry/exit logs, visitor records, vehicle gate pass, incident reports | Superadmin, Admin |

**Permission Inheritance:**
- Superadmin → Can modify ALL role permissions
- Each role has predefined permissions (see Technical Specs)
- Permissions are additive, not restrictive
- Superadmin approval required for permission changes

**User Management:**
- **Superadmin & Admin** can add/delete/modify all user accounts (except Superadmin accounts)
- **Dispatch Personnel Management**: Admin can create individual dispatch accounts, each with unique login credentials for accountability
- **Salesman Management**: Admin manages salesman accounts and assigns territories/clients
- All user actions logged with individual user ID to prevent "missing goods" scenarios

## Audit Logging

**What's Tracked:**
- **Authentication**: Login/logout (timestamp, IP, device)
- **Navigation**: Every page view (URL, timestamp, duration)
- **Data Changes**: Before/after values (field-level tracking)
- **Report Generation**: Which reports, parameters, export format
- **Password Changes**: Old/new hash comparison
- **Failed Attempts**: Login failures, invalid OTP, unauthorized access
- **Permissions**: Role changes, permission modifications
- **Suspicious Activity**: Multiple failed logins, unusual hours, IP changes

**Who Sees Logs:**
- **Superadmin**: Everyone's logs (full access)
- **Admin (Accountant)**: All logs except superadmin actions
- **Other Users**: Only their own logs

**Retention & Archival:**
- **Active Logs**: 1 year in primary database
- **Archive**: After 1 year → Move to archive table/file storage
- **Archive Access**: Superadmin only, read-only
- **Archive Format**: full detail JSON/CSV exports
- **Archive Retention**: Indefinite 

**Daily Data Entry Policy:**
- **Salesmen**: MUST log daily sales entries (even if zero sales occurred)
- **Dispatch**: MUST log daily dispatch activities (even if no dispatches)
- **Purpose**: Prevents "silent days" where tracking gaps enable losses
- **Enforcement**: System sends reminder notifications for missing entries
- **Non-compliance**: Flagged to Admin/Superadmin with alerts
- **Sunday Exception**: Company does not operate on Sundays
  - System auto-skips Sunday entries (no reminder sent)
  - Sunday marked as "Non-Operating Day" in reports
  - Weekly reports automatically exclude Sundays from compliance checks

## Security Features

✅ Email OTP (6-digit, no apps, manual entry only - no autofill)  
✅ Password rules (8+ chars minimum - simple but effective)  
✅ 24hr re-auth (prompts only, never force-logout during work)  
✅ 1hr timeout (smart: detects unsaved data before logout)  - will trigger an autosave from another app and after OK, log-out.
✅ No saved devices  
✅ Rate limiting  
✅ Email notifications  
✅ Complete audit trail  
✅ All routes protected by auth + role  
✅ Force password change on first login with random temp password  
✅ Sunday auto-skip for data entry (company closed)

## Communication System

**Emails Sent:**
- Invitations (with temp password + login URL)
- OTP codes
- Password resets
- Password change alerts
- Approval notifications
- Security alerts
- Daily entry reminders (for salesmen/dispatch)

**Implementation:**
- **Separate app**: `apps.communications`
- **Used by**: Auth, Production, Sales, Inventory, Reports
- **Service**: Gmail SMTP
- **Future**: SMS via Twilio/Africa's Talking
- **Benefit**: One place for all email logic, reusable templates

## Module Cross-References

**User Profiles & Payroll Integration:**
- Detailed user profiles with payroll fields (employee_id, basic_salary, commission_rate, etc.)
- Up to 3 mobile numbers per user for emergency contact
- Profile photo upload (max 5MB) with drag-to-center positioning
- Full audit trail of all profile changes (who changed what, when)
- See **USER_PROFILES_AND_CHAT.md** for complete specifications

**Commission Tracking (Sales Module):**
- Salesman role has "commission tracking" permission in auth system
- Actual commission calculations, discounts (e.g., 5 KES per bread), and payment tracking handled in **Sales Module**
- Auth system provides role-based access control for commission features
- See Sales Module documentation for detailed commission logic

**Crate Management (Assets/Inventory Module):**
- Dispatch role has "crate tracking" permission in auth system
- Crate check-in/check-out, missing crate alerts, and crate inventory managed in **Assets/Inventory Module** (subsystem)
- Auth system logs all crate-related actions with user ID for accountability
- Prevents "missing 8 crates from 300" scenarios through individual user tracking
- See Assets/Inventory Module documentation for crate management workflow

**In-App Chat System (Future):**
- Real-time messaging integrated with Communications app
- Reduces SMS costs, maintains audit trail
- WebSocket-based with Django Channels + Redis
- See **USER_PROFILES_AND_CHAT.md** for architecture and roadmap

---

# USER FLOWS & FORM SPECIFICATIONS

## User Flow Diagrams

### Flow 1: Admin Invites New User

```
┌─────────────────────────────────────────────────────────────────┐
│ ADMIN DASHBOARD                                                  │
│ ┌─────────────────┐                                             │
│ │ Click "Invite   │                                             │
│ │ New User"       │                                             │
│ └────────┬────────┘                                             │
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ INVITE USER FORM                                            ││
│ │ ┌─────────────────────────────────────────────────────────┐││
│ │ │ Email:           [________________]                     │││
│ │ │ Full Name:       [________________]                     │││
│ │ │ Phone (opt):     [________________]                     │││
│ │ │ Role:            [▼ Select Role   ]                     │││
│ │ │                                                          │││
│ │ │            [ Cancel ]  [ Send Invitation ]              │││
│ │ └─────────────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ SYSTEM ACTIONS                                              ││
│ │ • Generate temp password (e.g., "Zx8n4Kp2!")              ││
│ │ • Create user account (INACTIVE, must_change_password)    ││
│ │ • Save to user_invitations table                          ││
│ │ • Send email via Communications app                       ││
│ │ • Log action in audit_logs                                ││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ SUCCESS MESSAGE                                             ││
│ │ ✓ Invitation sent to staff@example.com                     ││
│ │   User will receive login credentials via email.           ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

                              │
                              ▼
                    
┌─────────────────────────────────────────────────────────────────┐
│ NEW USER EMAIL INBOX                                             │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ From: Chesanto Bakery <noreply@chesanto.com>               ││
│ │ Subject: Welcome to Chesanto Bakery                        ││
│ │                                                             ││
│ │ Hi [Name],                                                  ││
│ │                                                             ││
│ │ You've been invited to join Chesanto Bakery System.       ││
│ │                                                             ││
│ │ Login URL: https://chesanto.railway.app/login              ││
│ │ Email: staff@example.com                                   ││
│ │ Temporary Password: Zx8n4Kp2!                              ││
│ │                                                             ││
│ │ ⚠️  You'll be required to change this password on first    ││
│ │    login for security.                                      ││
│ │                                                             ││
│ │            [ Login Now ]                                    ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

                              │
                              ▼
                              
┌─────────────────────────────────────────────────────────────────┐
│ LOGIN PAGE (First Time)                                          │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Email:           [staff@example.com]                        ││
│ │ Password:        [Kx9mP2vL       ]                          ││
│ │                         [ Login ]                           ││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ FORCE PASSWORD CHANGE                                       ││
│ │ ⚠️  For security, please change your password               ││
│ │                                                             ││
│ │ New Password:         [________________]                    ││
│ │ Confirm Password:     [________________]                    ││
│ │                                                             ││
│ │ Requirements: Minimum 8 characters                         ││
│ │                       [ Change Password ]                   ││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ✓ Password changed successfully!                            ││
│ │   Redirecting to dashboard...                               ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Flow 2: Self-Registration (New Hire)

```
┌─────────────────────────────────────────────────────────────────┐
│ PUBLIC WEBSITE / LOGIN PAGE                                      │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Don't have an account?  [ Register ]                        ││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ REGISTRATION FORM                                           ││
│ │ ┌─────────────────────────────────────────────────────────┐││
│ │ │ Email:           [________________] *                   │││
│ │ │ Full Name:       [________________] *                   │││
│ │ │ Phone Number:    [________________] *                   │││
│ │ │ Password:        [________________] *                   │││
│ │ │ Confirm Password:[________________] *                   │││
│ │ │ Desired Role:    [▼ Select Role   ] *                   │││
│ │ │                                                          │││
│ │ │ Password Requirements:                                  │││
│ │ │ ☐ Minimum 8 characters                                  │││
│ │ │ (Strength meter will show above)                        │││
│ │ │                                                          │││
│ │ │          [ Cancel ]  [ Create Account ]                 │││
│ │ └─────────────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ SYSTEM CHECKS                                               ││
│ │ • Check if email in SUPERADMIN_EMAILS → Auto-approve       ││
│ │ • If not superadmin → Create INACTIVE account              ││
│ │ • is_active = FALSE, is_approved = FALSE                   ││
│ │ • Log action in audit_logs                                 ││
│ │ • Notify admin via email                                   ││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ PENDING APPROVAL MESSAGE                                    ││
│ │                                                             ││
│ │ ✓ Registration complete!                                    ││
│ │                                                             ││
│ │ Your account is awaiting admin approval.                   ││
│ │ You'll receive an email when approved.                     ││
│ │                                                             ││
│ │            [ Back to Login ]                                ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

                              │
                              ▼
                              
┌─────────────────────────────────────────────────────────────────┐
│ ADMIN DASHBOARD - PENDING APPROVALS                              │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 🔔 1 New Registration Pending                               ││
│ │                                                             ││
│ │ ┌─────────────────────────────────────────────────────────┐││
│ │ │ Name: John Doe                                          │││
│ │ │ Email: john@example.com                                 │││
│ │ │ Phone: +254712345678                                    │││
│ │ │ Requested Role: Salesman                                │││
│ │ │ Registered: Oct 15, 2025 10:30 AM                       │││
│ │ │                                                          │││
│ │ │        [ Reject ]           [ Approve ]                 │││
│ │ └─────────────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────────────┘│
│          │ (Admin clicks Approve)                               │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ SYSTEM ACTIONS                                              ││
│ │ • Set is_active = TRUE                                      ││
│ │ • Set is_approved = TRUE                                    ││
│ │ • Send approval email to user                              ││
│ │ • Log action in audit_logs                                 ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘

                              │
                              ▼
                              
┌─────────────────────────────────────────────────────────────────┐
│ USER EMAIL INBOX                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ From: Chesanto Bakery                                       ││
│ │ Subject: Account Approved - Welcome!                       ││
│ │                                                             ││
│ │ Hi John,                                                    ││
│ │                                                             ││
│ │ Good news! Your account has been approved.                 ││
│ │                                                             ││
│ │ You can now login at:                                       ││
│ │ https://chesanto.railway.app/login                         ││
│ │                                                             ││
│ │            [ Login Now ]                                    ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Flow 3: Daily Login (With 24hr Re-auth)

```
┌─────────────────────────────────────────────────────────────────┐
│ LOGIN PAGE                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Email:           [user@chesanto.com]                        ││
│ │ Password:        [••••••••••••••••]                         ││
│ │                                                             ││
│ │ ☐ Remember me    [ Forgot Password? ]                       ││
│ │                         [ Login ]                           ││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ SYSTEM CHECKS                                               ││
│ │ • Validate email + password                                 ││
│ │ • Check last_password_login timestamp                       ││
│ │ • IF < 24 hours → Direct login                             ││
│ │ • IF ≥ 24 hours → Require OTP                              ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
          │                                    │
          │ (< 24hrs)                          │ (≥ 24hrs)
          ▼                                    ▼
┌───────────────────────┐      ┌─────────────────────────────────┐
│ ✓ Login Successful    │      │ OTP VERIFICATION REQUIRED        │
│ Redirecting...        │      │ ┌─────────────────────────────┐ │
└───────────────────────┘      │ │ 📧 We've sent a 6-digit     │ │
                               │ │    code to your email       │ │
                               │ │                             │ │
                               │ │ Enter Code: [_ _ _ _ _ _]  │ │
                               │ │                             │ │
                               │ │ Code expires in 10 minutes │ │
                               │ │                             │ │
                               │ │ Didn't receive? [Resend]   │ │
                               │ │         [ Verify ]          │ │
                               │ └─────────────────────────────┘ │
                               └─────────────────────────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────────┐
                               │ SYSTEM VALIDATES OTP            │
                               │ • Check code_hash match         │
                               │ • Check expiry (10 min)         │
                               │ • Check attempts (max 3)        │
                               │ • Update last_password_login    │
                               └─────────────────────────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────────┐
                               │ ✓ Verification Successful       │
                               │   Redirecting to dashboard...   │
                               └─────────────────────────────────┘
```

### Flow 4: Forgot Password

```
┌─────────────────────────────────────────────────────────────────┐
│ LOGIN PAGE                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ [ Forgot Password? ]  ← Click                               ││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ PASSWORD RESET REQUEST                                      ││
│ │ ┌─────────────────────────────────────────────────────────┐││
│ │ │ Enter your email address to receive                     │││
│ │ │ a password reset code.                                  │││
│ │ │                                                          │││
│ │ │ Email: [___________________________]                    │││
│ │ │                                                          │││
│ │ │        [ Cancel ]  [ Send Reset Code ]                  │││
│ │ └─────────────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ SYSTEM ACTIONS                                              ││
│ │ • Generate 6-digit OTP                                      ││
│ │ • Hash and store in email_otp table                        ││
│ │ • Set 15-minute expiry                                      ││
│ │ • Send email with code                                     ││
│ │ • Rate limit: Max 3 requests/hour                          ││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ VERIFY RESET CODE                                           ││
│ │ ┌─────────────────────────────────────────────────────────┐││
│ │ │ 📧 A 6-digit code has been sent to                      │││
│ │ │    u***@chesanto.com                                    │││
│ │ │                                                          │││
│ │ │ Enter Code: [_ _ _ _ _ _]                               │││
│ │ │                                                          │││
│ │ │ Code expires in 15 minutes                              │││
│ │ │                                                          │││
│ │ │ Didn't receive? [Resend Code]                           │││
│ │ │         [ Verify Code ]                                 │││
│ │ └─────────────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ SET NEW PASSWORD                                            ││
│ │ ┌─────────────────────────────────────────────────────────┐││
│ │ │ New Password:         [________________]                │││
│ │ │ Confirm Password:     [________________]                │││
│ │ │                                                          │││
│ │ │ Requirements:                                           │││
│ │ │ ☐ Minimum 8 characters                                  │││
│ │ │                                                          │││
│ │ │         [ Reset Password ]                              │││
│ │ └─────────────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────────────┘│
│          │                                                       │
│          ▼                                                       │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ ✓ Password reset successful!                                ││
│ │   Confirmation email sent.                                  ││
│ │   Redirecting to login...                                   ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Form Specifications

### Form 1: User Invitation Form (Admin Only)

**Route:** `/admin/users/invite`  
**Method:** POST (AJAX)  
**Access:** SUPERADMIN, ADMIN  
**Reload:** NO - Form submits via AJAX, page stays active

#### Field Specifications

| Field | Type | Required | Placeholder | Helper Text | Icon |
|-------|------|----------|-------------|-------------|------|
| `email` | Email | Yes | `staff@chesanto.com` | "Work email address" | 📧 |
| `full_name` | Text | Yes | `John Doe` | "Full name as it appears on ID" | 👤 |
| `phone_number` | Tel | No | `+254712345678` | "Format: +254XXXXXXXXX (optional)" | 📱 |
| `role` | Select | Yes | `-- Select Role --` | "User's job position" | 🔐 |

#### Real-Time Validation
```javascript
// Email field
- On blur: Check if email exists (AJAX)
- Show ✓ green checkmark if available
- Show ❌ red X if taken
- Debounce: 500ms after typing stops

// Phone field
- Auto-format as user types: +254 712 345 678
- Show format hint below field
- Optional: Gray out if empty

// Full name
- Auto-capitalize first letter of each word
- Strip extra spaces on blur
```

#### Validation Rules
```python
def validate_invite_form(data):
    errors = {}
    
    # Email validation
    if not data.get('email'):
        errors['email'] = "Email is required"
    elif not is_valid_email(data['email']):
        errors['email'] = "Invalid email format. Example: staff@chesanto.com"
    elif User.objects.filter(email__iexact=data['email']).exists():
        errors['email'] = "This email is already registered"
    elif is_blacklisted_domain(data['email']):
        errors['email'] = "Temporary email addresses are not allowed"
    
    # Full name validation
    if not data.get('full_name'):
        errors['full_name'] = "Full name is required"
    elif len(data['full_name'].strip()) < 2:
        errors['full_name'] = "Name must be at least 2 characters"
    elif len(data['full_name']) > 100:
        errors['full_name'] = "Name is too long (max 100 characters)"
    elif not re.match(r"^[a-zA-Z\s\-']+$", data['full_name']):
        errors['full_name'] = "Name can only contain letters, spaces, hyphens and apostrophes"
    
    # Phone validation (optional)
    if data.get('phone_number'):
        if not re.match(r'^\+254[71]\d{8}$', data['phone_number']):
            errors['phone_number'] = "Invalid phone format. Use +254712345678"
    
    # Role validation
    if not data.get('role'):
        errors['role'] = "Role selection is required"
    elif data['role'] not in [r[0] for r in User.Role.choices if r[0] != 'SUPERADMIN']:
        errors['role'] = "Invalid role selected"
    
    return errors
```

#### Success Response (AJAX)
```json
{
    "success": true,
    "message": "✓ Invitation sent successfully!",
    "details": {
        "recipient": "john@example.com",
        "role": "Salesman",
        "invitation_id": 123
    },
    "toast": {
        "type": "success",
        "title": "Invitation Sent",
        "message": "john@example.com will receive login credentials via email",
        "duration": 5000
    }
}
```

#### Error Responses (AJAX)
```json
// Field validation errors
{
    "success": false,
    "errors": {
        "email": "This email is already registered",
        "phone_number": "Invalid phone format. Use +254712345678"
    },
    "toast": {
        "type": "error",
        "title": "Validation Failed",
        "message": "Please fix the errors and try again",
        "duration": 5000
    }
}

// Server error
{
    "success": false,
    "error": "Failed to send invitation email",
    "details": "SMTP connection timeout",
    "toast": {
        "type": "error",
        "title": "Email Delivery Failed",
        "message": "Could not send invitation. Please try again or contact support.",
        "duration": 7000
    }
}

// Rate limit exceeded
{
    "success": false,
    "error": "Too many invitations sent",
    "retry_after": 3600,
    "toast": {
        "type": "warning",
        "title": "Rate Limit Exceeded",
        "message": "Maximum 10 invitations per hour. Try again in 60 minutes.",
        "duration": 7000
    }
}

// Network error (client-side)
{
    "success": false,
    "error": "Network connection failed",
    "toast": {
        "type": "error",
        "title": "Connection Error",
        "message": "Check your internet connection and try again",
        "duration": 5000
    }
}
```

#### UX Enhancements
- **Loading State**: Button shows spinner + "Sending..." during submit
- **Success Feedback**: Green toast notification + form clears automatically
- **Error Feedback**: Red inline errors below each field + error toast
- **Auto-Focus**: Focus returns to email field after successful submission
- **Keyboard Shortcuts**: Enter key submits, Escape clears form

---

### Form 2: Self-Registration Form (Public)

**Route:** `/register`  
**Method:** POST (AJAX)  
**Access:** Public (unauthenticated)  
**Reload:** NO - AJAX submission with real-time validation

#### Field Specifications with Icons

| Field | Type | Required | Placeholder | Helper Text | Icon | Toggle |
|-------|------|----------|-------------|-------------|------|--------|
| `email` | Email | Yes | `you@example.com` | "Use work or personal email" | 📧 | - |
| `full_name` | Text | Yes | `John Maina Doe` | "Full name as per ID" | 👤 | - |
| `phone_number` | Tel | Yes | `+254712345678` | "Kenyan mobile number" | 📱 | - |
| `password` | Password | Yes | `••••••••••` | "Min 8 chars with uppercase, lowercase & number" | 🔒 | 👁️ Show/Hide |
| `password_confirm` | Password | Yes | `••••••••••` | "Re-enter password to confirm" | 🔒 | 👁️ Show/Hide |
| `role` | Select | Yes | `-- What's your role? --` | "Select your job position" | 💼 | - |

#### Password Visibility Toggle
```javascript
// Eye icon to show/hide password
<div class="password-field-wrapper">
    <input type="password" id="password" class="form-input" />
    <button type="button" class="toggle-password" aria-label="Toggle password visibility">
        <span class="icon-eye-closed">👁️‍🗨️</span>  <!-- Hidden state -->
        <span class="icon-eye-open hidden">👁️</span>  <!-- Visible state -->
    </button>
</div>

// Toggle logic
document.querySelector('.toggle-password').addEventListener('click', function() {
    const input = document.getElementById('password');
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    this.querySelector('.icon-eye-closed').classList.toggle('hidden');
    this.querySelector('.icon-eye-open').classList.toggle('hidden');
});
```

#### Real-Time Password Strength Meter
```html
<div class="password-strength-meter">
    <div class="strength-bar" data-strength="0"></div>
    <span class="strength-text">Password strength: <strong>Weak</strong></span>
</div>

<!-- Visual indicator -->
Weak:      ████░░░░░░░░░░░░ 🔴 (< 8 chars)
Fair:      ████████░░░░░░░░ 🟠 (8+ chars)
Good:      ████████████░░░░ 🟡 (8+ chars + mixed case)
Strong:    ████████████████ 🟢 (8+ chars + mixed + numbers + special)
```

#### Validation Rules with Comprehensive Error Messages
```python
def validate_registration_form(data):
    errors = {}
    
    # Email validation
    if not data.get('email'):
        errors['email'] = "Email address is required"
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', data['email']):
        errors['email'] = "Invalid email format. Example: you@example.com"
    elif User.objects.filter(email__iexact=data['email']).exists():
        errors['email'] = "This email is already registered. Try logging in instead."
    elif is_disposable_email(data['email']):
        errors['email'] = "Temporary/disposable emails are not allowed"
    
    # Full name validation
    if not data.get('full_name'):
        errors['full_name'] = "Full name is required"
    elif len(data['full_name'].strip()) < 2:
        errors['full_name'] = "Name must be at least 2 characters"
    elif len(data['full_name']) > 100:
        errors['full_name'] = "Name is too long (maximum 100 characters)"
    elif not re.match(r"^[a-zA-Z\s\-']+$", data['full_name']):
        errors['full_name'] = "Name can only contain letters, spaces, hyphens (-) and apostrophes (')"
    
    # Phone validation
    if not data.get('phone_number'):
        errors['phone_number'] = "Phone number is required"
    elif not re.match(r'^\+254[71]\d{8}$', data['phone_number']):
        errors['phone_number'] = "Invalid Kenyan phone. Format: +254712345678 or +254722345678"
    elif User.objects.filter(phone_number=data['phone_number']).exists():
        errors['phone_number'] = "This phone number is already registered"
    
    # Password validation
    if not data.get('password'):
        errors['password'] = "Password is required"
    elif len(data['password']) < 8:
        errors['password'] = "Password must be at least 8 characters long"
    elif data['password'] in COMMON_PASSWORDS:
        errors['password'] = "This password is too common. Please choose a stronger password"
    
    # Password confirmation
    if not data.get('password_confirm'):
        errors['password_confirm'] = "Please confirm your password"
    elif data.get('password') != data.get('password_confirm'):
        errors['password_confirm'] = "Passwords do not match. Please re-enter."
    
    # Role validation
    if not data.get('role'):
        errors['role'] = "Please select your role/position"
    elif data['role'] not in [r[0] for r in User.Role.choices]:
        errors['role'] = "Invalid role selected"
    
    return errors
```

#### Success Responses (AJAX)
```json
// Regular user (requires approval)
{
    "success": true,
    "message": "Registration successful!",
    "user_id": 456,
    "is_superadmin": false,
    "requires_approval": true,
    "next_step": "awaiting_approval",
    "toast": {
        "type": "success",
        "title": "✓ Registration Complete",
        "message": "Your account is awaiting admin approval. You'll receive an email when approved.",
        "duration": 7000
    },
    "redirect": null,
    "modal": {
        "show": true,
        "title": "Thank You for Registering!",
        "body": "Your account has been created and is awaiting approval from the administrator. You'll receive an email at <strong>john@example.com</strong> once your account is activated.",
        "icon": "⏳",
        "buttons": [
            {"text": "Back to Login", "url": "/login", "class": "primary"}
        ]
    }
}

// Superadmin email (auto-approved)
{
    "success": true,
    "message": "Welcome aboard!",
    "user_id": 1,
    "is_superadmin": true,
    "requires_approval": false,
    "next_step": "redirect_dashboard",
    "toast": {
        "type": "success",
        "title": "✓ Account Created",
        "message": "Welcome! Redirecting to dashboard...",
        "duration": 3000
    },
    "redirect": "/dashboard",
    "redirect_delay": 2000
}
```

#### Error Responses (AJAX)
```json
// Field validation errors
{
    "success": false,
    "errors": {
        "email": "This email is already registered. Try logging in instead.",
        "password": "Password must contain at least one uppercase letter (A-Z)",
        "password_confirm": "Passwords do not match. Please re-enter."
    },
    "toast": {
        "type": "error",
        "title": "Validation Failed",
        "message": "Please correct the errors below",
        "duration": 5000
    }
}

// Server error
{
    "success": false,
    "error": "Registration failed due to server error",
    "error_code": "REG_500",
    "toast": {
        "type": "error",
        "title": "Registration Failed",
        "message": "Something went wrong. Please try again or contact support.",
        "duration": 7000
    }
}

// Database error
{
    "success": false,
    "error": "Could not create account",
    "details": "Database connection timeout",
    "toast": {
        "type": "error",
        "title": "System Error",
        "message": "Unable to create account. Please try again in a few minutes.",
        "duration": 7000
    }
}
```

#### UX Enhancements
- **Real-Time Checks**: Email availability checked on blur (AJAX, no reload)
- **Password Strength**: Live indicator updates as user types
- **Auto-Format Phone**: Adds +254 prefix automatically if user enters 07/01
- **Confirm Match Indicator**: ✓ or ❌ shows instantly on password_confirm field
- **Loading Button**: "Creating Account..." with spinner during submission
- **Success Modal**: Shows pending approval message (no reload)
- **Form Persistence**: Form data saved to localStorage if network fails

---

### Form 3: Login Form

**Route:** `/login`  
**Method:** POST (AJAX)  
**Access:** Public  
**Purpose:** Authenticate existing users and redirect to OTP verification.

#### Field Specifications

| Field | Type | Icon | Toggle | Required | Max Length | Validation |
|-------|------|------|--------|----------|------------|------------|
| Email | text | 📧 | - | ✓ | 255 | Email format, lowercase |
| Password | password | 🔒 | 👁️ | ✓ | - | Min 8 chars (no complexity requirements) |
| Remember Me | checkbox | 💾 | - | - | - | Boolean |

#### UX Enhancements
**Password Visibility Toggle:**
```javascript
const togglePassword = document.querySelector('#toggle-password');
const passwordInput = document.querySelector('#password');

togglePassword.addEventListener('click', function() {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);
    this.textContent = type === 'password' ? '👁️' : '👁️‍🗨️';
});
```

**Remember Me Functionality:**
- If checked: Extend session to 30 days (but still enforce 24hr password re-auth)
- If unchecked: Session expires on browser close
- Tooltip: "Stay logged in for 30 days (you'll still need to re-authenticate for security)"

**Other Features:**
- Loading states: Disable submit button and show spinner during validation
- Auto-focus: Focus on email field on page load
- Enter key: Submit form on Enter keypress
- Forgot password link below password field

#### Form Helpers
```html
<label for="email">Email Address 📧</label>
<input 
    type="email" 
    id="email" 
    name="email" 
    placeholder="you@chesanto.com" 
    required 
    autofocus
    autocomplete="email"
/>

<label for="password">Password 🔒 <a href="/reset-request/" class="forgot-link">Forgot?</a></label>
<div class="password-field-wrapper">
    <input 
        type="password" 
        id="password" 
        name="password" 
        placeholder="Enter your password" 
        required 
        minlength="8"
        autocomplete="current-password"
    />
    <button type="button" id="toggle-password" class="toggle-btn" aria-label="Toggle password visibility">👁️</button>
</div>

<label class="checkbox-label">
    <input type="checkbox" id="remember_me" name="remember_me" />
    <span>Remember me for 30 days 💾</span>
</label>
```

#### Validation Function
```python
def validate_login_form(email, password, ip_address):
    errors = {}
    
    # Email validation
    if not email:
        errors['email'] = "Email is required"
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors['email'] = "Please enter a valid email address"
    
    # Password validation
    if not password:
        errors['password'] = "Password is required"
    elif len(password) < 8:
        errors['password'] = "Password must be at least 8 characters"
    
    # Rate limiting check
    if check_rate_limit_exceeded(ip_address, 'login'):
        errors['_form'] = "Too many login attempts. Please try again in 10 minutes."
        return errors
    
    # Credential validation (if basic checks pass)
    if not errors:
        try:
            user = User.objects.get(email__iexact=email.lower())
            
            # Check password
            if not user.check_password(password):
                log_failed_login(email, ip_address)
                errors['_form'] = "Invalid email or password"  # Generic for security
            
            # Check account approval status
            elif not user.is_approved:
                errors['_form'] = "Your account is pending approval. Please contact the administrator."
            
            # Check account active status
            elif not user.is_active:
                errors['_form'] = "Your account has been deactivated. Please contact the administrator."
            
        except User.DoesNotExist:
            log_failed_login(email, ip_address)
            errors['_form'] = "Invalid email or password"  # Generic for security
    
    return errors
```

#### Success Responses

**1. Direct Login (< 24hrs since last password login):**
```json
{
    "success": true,
    "requires_otp": false,
    "redirect": "/dashboard",
    "message": "Login successful! Redirecting..."
}
```

**2. OTP Required (≥ 24hrs since last password login):**
```json
{
    "success": true,
    "requires_otp": true,
    "redirect": "/login/verify-otp",
    "message": "Please check your email for the verification code",
    "email_sent": true
}
```
- Generate 6-digit OTP code (10-minute validity)
- Send OTP email to user
- Store session flag: `request.session['pending_otp_user_id'] = user.id`

**3. Must Change Password (Invited user first login):**
```json
{
    "success": true,
    "requires_password_change": true,
    "redirect": "/change-password",
    "message": "Please change your temporary password to continue"
}
```

#### Error Responses

**1. Field Validation Errors:**
```json
{
    "success": false,
    "errors": {
        "email": "Please enter a valid email address",
        "password": "Password is required"
    }
}
```

**2. Invalid Credentials:**
```json
{
    "success": false,
    "message": "Invalid email or password. Please try again.",
    "attempts_remaining": 8
}
```
- **Security Note:** Use generic message—don't reveal if email exists or password is wrong

**3. Account Pending Approval:**
```json
{
    "success": false,
    "message": "Your account is pending approval. You'll receive an email once approved.",
    "status": "pending",
    "contact_admin": true
}
```

**4. Account Deactivated:**
```json
{
    "success": false,
    "message": "Your account has been deactivated. Please contact the administrator for assistance.",
    "status": "inactive",
    "contact_admin": true
}
```

**5. Rate Limit Exceeded:**
```json
{
    "success": false,
    "message": "Too many login attempts from this IP address. Please try again in 10 minutes.",
    "retry_after": 600,
    "countdown": "9 minutes 23 seconds remaining"
}
```

**6. Email Delivery Failed (OTP):**
```json
{
    "success": false,
    "message": "Failed to send verification code. Please try again or contact the administrator.",
    "error_type": "email_delivery"
}
```

**7. Server Error:**
```json
{
    "success": false,
    "message": "An unexpected error occurred. Please try again or contact support.",
    "error_type": "server_error"
}
```

#### Rate Limiting
- Max 10 login attempts per 10 minutes per IP address
- Failed attempts are logged to audit trail
- Display countdown timer: "Too many attempts. Try again in 8 minutes 32 seconds."
- Lockout duration: 10 minutes

#### Security Features
- Generic error messages (don't reveal if email exists)
- Log all failed attempts with IP, timestamp, and user agent
- Brute-force protection via rate limiting
- Session-based OTP flow (not URL-based)
- Password not stored in session

---

### Form 4: OTP Verification Form

**Route:** `/login/verify-otp`  
**Method:** POST (AJAX)  
**Access:** Authenticated (session-based, pending OTP)  
**Purpose:** Verify the 6-digit OTP code sent to user's email.

#### Field Specifications

| Field | Type | Icon | Required | Max Length | Validation |
|-------|------|------|----------|------------|------------|
| OTP Code | text | 🔢 | ✓ | 6 | Numeric only, exactly 6 digits |

#### UX Enhancements
**Auto-Focus & Format:**
```javascript
// Auto-focus on input when page loads
document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('#otp_code').focus();
});

// Only allow numeric input
const otpInput = document.querySelector('#otp_code');
otpInput.addEventListener('input', function(e) {
    this.value = this.value.replace(/[^0-9]/g, '').slice(0, 6);
    
    // Auto-submit when 6 digits entered
    if (this.value.length === 6) {
        document.querySelector('#otp-form').requestSubmit();
    }
});

// Visual digit boxes (6 separate boxes)
// Each box contains one digit for better UX
```

**Resend Code Functionality:**
```javascript
let resendTimeout = 60;  // 60 seconds cooldown

function enableResendButton() {
    const resendBtn = document.querySelector('#resend-otp');
    resendBtn.disabled = false;
    resendBtn.textContent = 'Resend Code';
}

function startResendCooldown() {
    const resendBtn = document.querySelector('#resend-otp');
    resendBtn.disabled = true;
    
    const interval = setInterval(() => {
        resendTimeout--;
        resendBtn.textContent = `Resend in ${resendTimeout}s`;
        
        if (resendTimeout === 0) {
            clearInterval(interval);
            enableResendButton();
            resendTimeout = 60;
        }
    }, 1000);
}
```

**Attempts Counter:**
- Display: "2 attempts remaining" below input
- Update dynamically after each failed attempt
- Disable form after 3 failed attempts

#### Form Helpers
```html
<label for="otp_code">Enter Verification Code 🔢</label>
<p class="helper-text">Check your email ({{ email }}) for a 6-digit code</p>

<div class="otp-input-container">
    <input 
        type="text" 
        id="otp_code" 
        name="otp_code" 
        placeholder="000000" 
        required 
        maxlength="6"
        pattern="[0-9]{6}"
        inputmode="numeric"
        autocomplete="off"
        data-lpignore="true"
    />
</div>

<!-- Security: Disable autofill/paste for OTP -->
<script>
document.getElementById('otp_code').addEventListener('paste', function(e) {
    // Allow paste but clear any non-numeric characters
    setTimeout(() => {
        this.value = this.value.replace(/[^0-9]/g, '').slice(0, 6);
    }, 0);
});
</script>

<p class="expiry-notice">⏰ Code expires in <span id="countdown">10:00</span></p>

<p class="attempts-remaining" id="attempts">3 attempts remaining</p>

<button type="button" id="resend-otp" disabled>Resend in 60s</button>
```

#### Validation Function
```python
def validate_otp_code(user_id, otp_code, session_id):
    errors = {}
    
    # Check code format
    if not otp_code:
        errors['otp_code'] = "Verification code is required"
    elif not re.match(r'^\d{6}$', otp_code):
        errors['otp_code'] = "Code must be exactly 6 digits"
    
    if not errors:
        try:
            otp_record = EmailOTP.objects.get(
                user_id=user_id,
                purpose='LOGIN',
                used_at__isnull=True
            )
            
            # Check expiry (10 minutes)
            if timezone.now() > otp_record.expires_at:
                errors['_form'] = "Verification code has expired. Please request a new one."
            
            # Check attempts (max 3)
            elif otp_record.attempts >= 3:
                errors['_form'] = "Too many failed attempts. Please request a new code."
            
            # Verify code hash
            elif not check_password(otp_code, otp_record.code_hash):
                otp_record.attempts += 1
                otp_record.save()
                attempts_left = 3 - otp_record.attempts
                errors['_form'] = f"Invalid code. {attempts_left} {'attempts' if attempts_left != 1 else 'attempt'} remaining."
            
        except EmailOTP.DoesNotExist:
            errors['_form'] = "No pending verification code found. Please log in again."
    
    return errors
```

#### Success Response
```json
{
    "success": true,
    "message": "Verification successful! Redirecting to dashboard...",
    "redirect": "/dashboard"
}
```
- Mark OTP as used: `otp_record.used_at = timezone.now()`
- Update user: `user.last_password_login = timezone.now()`
- Log successful login to audit trail
- Redirect to dashboard

#### Error Responses

**1. Field Validation Error:**
```json
{
    "success": false,
    "errors": {
        "otp_code": "Code must be exactly 6 digits"
    }
}
```

**2. Invalid Code:**
```json
{
    "success": false,
    "message": "Invalid code. 2 attempts remaining.",
    "attempts_remaining": 2,
    "can_resend": true
}
```

**3. Code Expired:**
```json
{
    "success": false,
    "message": "Verification code has expired. Please request a new one.",
    "expired": true,
    "can_resend": true
}
```

**4. Too Many Attempts:**
```json
{
    "success": false,
    "message": "Too many failed attempts. Please request a new code.",
    "locked": true,
    "can_resend": true
}
```

**5. No Pending Code:**
```json
{
    "success": false,
    "message": "No pending verification code found. Please log in again.",
    "redirect": "/login"
}
```

**6. Server Error:**
```json
{
    "success": false,
    "message": "An unexpected error occurred. Please try again.",
    "error_type": "server_error"
}
```

#### Rate Limiting
- Resend OTP: 60-second cooldown between requests
- Max 3 OTP resends per 10 minutes per user
- Automatic cooldown timer displayed to user

#### Security Features
- OTP codes are hashed before storage (never store plain text)
- 10-minute expiry from generation time
- Max 3 verification attempts per code
- Session-based validation (user_id from session)
- Countdown timer shows remaining validity

---

### Form 5: Password Change Form (Forced)
- Rate limit: 10 requests per 10 minutes
```

**Success Response:**
```json
{
    "success": true,
    "message": "Verification successful",
    "redirect": "/dashboard"
}
```

**Error Responses:**
```json
// Invalid code
{
    "success": false,
    "error": "Invalid verification code",
    "attempts_remaining": 2
}

// Expired code
{
    "success": false,
    "error": "Code expired. Request a new one.",
    "can_resend": true
}

// Too many attempts
{
    "success": false,
    "error": "Too many failed attempts. Request a new code.",
    "can_resend": true
}
```

---

### Form 5: Password Change Form (Forced)

**Route:** `/change-password`  
**Method:** POST (AJAX)  
**Access:** Authenticated (must_change_password = True)  
**Purpose:** Force invited users to change temporary password on first login.

#### Field Specifications

| Field | Type | Icon | Toggle | Required | Max Length | Validation |
|-------|------|------|--------|----------|------------|------------|
| New Password | password | 🔒 | 👁️ | ✓ | - | Min 8 chars |
| Confirm Password | password | 🔒 | 👁️ | ✓ | - | Must match new password |

#### UX Enhancements
**Password Visibility Toggle (Both Fields):**
```javascript
document.querySelectorAll('.toggle-password').forEach(button => {
    button.addEventListener('click', function() {
        const input = this.previousElementSibling;
        const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
        input.setAttribute('type', type);
        this.textContent = type === 'password' ? '👁️' : '👁️‍🗨️';
    });
});
```

**Real-Time Password Strength Meter:**
```javascript
const newPasswordInput = document.querySelector('#new_password');
const strengthBar = document.querySelector('#strength-bar');
const strengthText = document.querySelector('#strength-text');

newPasswordInput.addEventListener('input', function() {
    const password = this.value;
    let strength = 0;
    let text = 'Weak';
    let color = '#ef4444';  // Red
    
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    
    if (strength === 1) {
        text = 'Weak 🔴';
        color = '#ef4444';
    } else if (strength === 2) {
        text = 'Fair 🟠';
        color = '#f59e0b';
    } else if (strength === 3) {
        text = 'Good 🟡';
        color = '#eab308';
    } else if (strength === 4) {
        text = 'Strong 🟢';
        color = '#10b981';
    }
    
    strengthBar.style.width = (strength * 25) + '%';
    strengthBar.style.backgroundColor = color;
    strengthText.textContent = text;
});
```

**Confirm Password Match Indicator:**
```javascript
const confirmInput = document.querySelector('#confirm_password');
const matchIndicator = document.querySelector('#match-indicator');

confirmInput.addEventListener('input', function() {
    const newPassword = document.querySelector('#new_password').value;
    const confirmPassword = this.value;
    
    if (confirmPassword === '') {
        matchIndicator.textContent = '';
    } else if (newPassword === confirmPassword) {
        matchIndicator.textContent = '✓ Passwords match';
        matchIndicator.style.color = '#10b981';
    } else {
        matchIndicator.textContent = '✗ Passwords do not match';
        matchIndicator.style.color = '#ef4444';
    }
});
```

#### Form Helpers
```html
<div class="alert alert-warning">
    <strong>⚠️ Password Change Required</strong>
    <p>For security reasons, you must change your temporary password before accessing the system.</p>
</div>

<label for="new_password">New Password 🔒</label>
<div class="password-field-wrapper">
    <input 
        type="password" 
        id="new_password" 
        name="new_password" 
        placeholder="Create a strong password" 
        required 
        minlength="8"
        autocomplete="new-password"
    />
    <button type="button" class="toggle-password" aria-label="Toggle password visibility">👁️</button>
</div>

<div class="password-strength">
    <div class="strength-bar-container">
        <div id="strength-bar" class="strength-bar"></div>
    </div>
    <span id="strength-text">Weak</span>
</div>

<div class="password-requirements">
    <p><strong>Requirements:</strong></p>
    <ul>
        <li id="req-length">☐ At least 8 characters</li>
        <li id="req-upper">☐ Uppercase letter (A-Z)</li>
        <li id="req-lower">☐ Lowercase letter (a-z)</li>
        <li id="req-number">☐ Number (0-9)</li>
    </ul>
</div>

<label for="confirm_password">Confirm New Password 🔒</label>
<div class="password-field-wrapper">
    <input 
        type="password" 
        id="confirm_password" 
        name="confirm_password" 
        placeholder="Re-enter your new password" 
        required 
        minlength="8"
        autocomplete="new-password"
    />
    <button type="button" class="toggle-password" aria-label="Toggle password visibility">👁️</button>
</div>
<span id="match-indicator"></span>
```

#### Validation Function
```python
def validate_password_change(user, new_password, confirm_password, temp_password_hash):
    errors = {}
    
    # New password validation
    if not new_password:
        errors['new_password'] = "New password is required"
    elif len(new_password) < 8:
        errors['new_password'] = "Password must be at least 8 characters long"
    elif check_password(new_password, temp_password_hash):
        errors['new_password'] = "New password cannot be the same as your temporary password"
    
    # Confirm password validation
    if not confirm_password:
        errors['confirm_password'] = "Please confirm your new password"
    elif new_password != confirm_password:
        errors['confirm_password'] = "Passwords do not match"
    
    # Check against common passwords
    if not errors and new_password.lower() in COMMON_PASSWORDS:
        errors['new_password'] = "This password is too common. Please choose a more unique password."
    
    return errors
```

#### Success Response
```json
{
    "success": true,
    "message": "Password changed successfully! Redirecting to dashboard...",
    "redirect": "/dashboard"
}
```
- Update user password: `user.set_password(new_password)`
- Set `must_change_password = False`
- Set `last_password_login = timezone.now()`
- Log password change to audit trail
- Send confirmation email to user

#### Error Responses

**1. Field Validation Errors:**
```json
{
    "success": false,
    "errors": {
        "new_password": "Password must contain at least one uppercase letter",
        "confirm_password": "Passwords do not match"
    }
}
```

**2. Same as Temporary Password:**
```json
{
    "success": false,
    "errors": {
        "new_password": "New password cannot be the same as your temporary password"
    }
}
```

**3. Common Password:**
```json
{
    "success": false,
    "errors": {
        "new_password": "This password is too common. Please choose a more unique password."
    }
}
```

**4. Server Error:**
```json
{
    "success": false,
    "message": "Failed to update password. Please try again or contact support.",
    "error_type": "server_error"
}
```

**5. Email Send Failed:**
```json
{
    "success": true,
    "message": "Password changed successfully, but failed to send confirmation email.",
    "redirect": "/dashboard",
    "warning": "email_not_sent"
}
```

#### Security Features
- Cannot reuse temporary password
- Common password blacklist check
- Password strength enforcement
- Confirmation email sent on successful change
- Audit log entry created
- Session updated with new authentication timestamp

---

### Form 6: Password Reset Request Form

**Route:** `/forgot-password`  
**Method:** POST (AJAX)  
**Access:** Public  
**Purpose:** Request a password reset code via email.

#### Field Specifications

| Field | Type | Icon | Required | Max Length | Validation |
|-------|------|------|----------|------------|------------|
| Email | text | 📧 | ✓ | 255 | Email format |

#### UX Enhancements
**Security Message:**
- Display: "For security, we won't reveal if this email exists in our system"
- Always return success message (even if email doesn't exist)
- This prevents account enumeration attacks

**Auto-focus:**
- Focus on email field on page load

**Loading State:**
- Disable submit button and show spinner during request
- Display: "Sending reset code..."

#### Form Helpers
```html
<label for="email">Email Address 📧</label>
<input 
    type="email" 
    id="email" 
    name="email" 
    placeholder="you@chesanto.com" 
    required 
    autofocus
    autocomplete="email"
/>
<p class="helper-text">Enter the email address associated with your account</p>

<div class="security-notice">
    <p><strong>🔒 Security Note:</strong> If an account exists with this email, you'll receive a reset code within a few minutes.</p>
</div>
```

#### Validation Function
```python
def validate_reset_request(email, ip_address):
    """
    Security Best Practices:
    - Always return generic success message (prevents account enumeration)
    - Only send email if: account exists, is active, AND is approved
    - Log all attempts (successful and failed) for security monitoring
    - Rate limit per IP and per email
    """
    errors = {}
    
    # Email format validation
    if not email:
        errors['email'] = "Email is required"
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors['email'] = "Please enter a valid email address"
    
    # Rate limiting check (per IP)
    if check_rate_limit_exceeded(ip_address, 'password_reset'):
        errors['_form'] = "Too many reset requests. Please try again in 1 hour."
        return errors
    
    # Rate limiting check (per email) - prevents targeted attacks
    if check_rate_limit_exceeded(email, 'password_reset_email'):
        # Still don't reveal if email exists
        errors['_form'] = "Too many reset requests. Please try again in 1 hour."
        return errors
    
    # Process request (even if email doesn't exist - security)
    if not errors:
        email_sent = False
        try:
            user = User.objects.get(email__iexact=email.lower())
            
            # Security checks (ONLY send email if ALL conditions met)
            if user.is_active and user.is_approved:
                # Generate OTP code (15 min expiry)
                otp_code = generate_otp(user, purpose='PASSWORD_RESET', expiry_minutes=15)
                
                # Send reset email via Communications app
                from apps.communications.services.email import EmailService
                email_sent = EmailService.send_password_reset(
                    email=user.email,
                    name=user.get_full_name(),
                    code=otp_code
                )
                
                # Log successful request
                log_audit(
                    user=user,
                    action='PASSWORD_RESET_REQUEST',
                    ip_address=ip_address,
                    success=True,
                    details={'email_sent': email_sent}
                )
            else:
                # Account exists but inactive/unapproved - log but don't send
                log_audit(
                    user=user,
                    action='PASSWORD_RESET_REQUEST_BLOCKED',
                    ip_address=ip_address,
                    success=False,
                    details={
                        'reason': 'inactive' if not user.is_active else 'unapproved',
                        'is_active': user.is_active,
                        'is_approved': user.is_approved
                    }
                )
        
        except User.DoesNotExist:
            # Email doesn't exist - log attempt but don't reveal
            log_audit(
                user=None,
                action='PASSWORD_RESET_REQUEST_FAILED',
                ip_address=ip_address,
                success=False,
                details={'email': email, 'reason': 'user_not_found'}
            )
        
        # IMPORTANT: Always increment rate limit counter (even for non-existent emails)
        increment_rate_limit(ip_address, 'password_reset')
        increment_rate_limit(email, 'password_reset_email')
    
    return errors
```

#### Success Response
```json
{
    "success": true,
    "message": "If an account exists with this email, you'll receive a reset code shortly. Please check your inbox and spam folder.",
    "redirect": "/reset-password"
}
```
- **Security:** Always return success, even if email doesn't exist
- Generate 6-digit OTP with 15-minute expiry
- Send reset email with code
- Redirect to password reset verification form

#### Error Responses

**1. Field Validation Error:**
```json
{
    "success": false,
    "errors": {
        "email": "Please enter a valid email address"
    }
}
```

**2. Rate Limit Exceeded:**
```json
{
    "success": false,
    "message": "Too many reset requests from this IP address. Please try again in 1 hour.",
    "retry_after": 3600
}
```

**3. Email Delivery Failed:**
```json
{
    "success": true,
    "message": "Request received. If an account exists, you'll receive a reset code shortly.",
    "warning": "email_delivery_issue"
}
```
- **Note:** Still return success to user, but log error internally

**4. Server Error:**
```json
{
    "success": false,
    "message": "An unexpected error occurred. Please try again or contact support.",
    "error_type": "server_error"
}
```

#### Rate Limiting
- Max 3 reset requests per hour per IP address
- Max 3 reset requests per hour per email (even if email doesn't exist)
- Display countdown: "Too many requests. Try again in 42 minutes."

#### Security Features
- **Account Enumeration Protection:** Always return generic success message (even for non-existent emails)
- **Only send reset email if:** Account exists AND is active AND is approved
- **Inactive/Unapproved accounts:** Silently reject (no email sent, no error shown to user)
- **Rate Limiting:** Both per-IP and per-email to prevent targeted attacks
- **Comprehensive Logging:** All attempts logged (success, blocked, failed) with reason codes
- **15-minute OTP expiry:** Longer than login OTP due to potential email delivery delays
- **No information disclosure:** Generic message prevents revealing account status

**Security Rationale:**
1. **Generic Success Message:** Prevents attackers from discovering valid email addresses
2. **Silent Rejection for Inactive/Unapproved:** Prevents account status enumeration
3. **Dual Rate Limiting:** Prevents both spray attacks (many emails) and targeted attacks (one email)
4. **Detailed Logging:** Enables security team to detect attack patterns
5. **No Auto-Activation:** Forgot password cannot be used to activate inactive accounts

---

### Form 7: Password Reset Verification Form

**Route:** `/reset-password`  
**Method:** POST (AJAX)  
**Access:** Public  
**Purpose:** Verify reset code and set new password.

#### Field Specifications

| Field | Type | Icon | Toggle | Required | Max Length | Validation |
|-------|------|------|--------|----------|------------|------------|
| Email | text | 📧 | - | ✓ | 255 | Email format |
| Reset Code | text | 🔢 | - | ✓ | 6 | Numeric only, 6 digits, manual entry |
| New Password | password | 🔒 | 👁️ | ✓ | - | Min 8 chars |
| Confirm Password | password | 🔒 | 👁️ | ✓ | - | Must match new password |

#### UX Enhancements
**Password Visibility Toggle:**
```javascript
document.querySelectorAll('.toggle-password').forEach(button => {
    button.addEventListener('click', function() {
        const input = this.previousElementSibling;
        const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
        input.setAttribute('type', type);
        this.textContent = type === 'password' ? '👁️' : '👁️‍🗨️';
    });
});
```

**Real-Time Password Strength Meter:**
- Same implementation as Form 5 (Password Change)
- Show strength bar: Weak 🔴 / Fair 🟠 / Good 🟡 / Strong 🟢
- Display requirements checklist

**Reset Code Auto-Format:**
```javascript
const codeInput = document.querySelector('#reset_code');
codeInput.addEventListener('input', function(e) {
    this.value = this.value.replace(/[^0-9]/g, '').slice(0, 6);
});
```

**Attempts Counter:**
- Display: "2 attempts remaining" below reset code input
- Update after each failed attempt
- Lock form after 3 failed attempts

#### Form Helpers
```html
<label for="email">Email Address 📧</label>
<input 
    type="email" 
    id="email" 
    name="email" 
    placeholder="you@chesanto.com" 
    required 
    autofocus
    autocomplete="email"
/>
<p class="helper-text">Enter the email you used to request the reset</p>

<label for="reset_code">Reset Code 🔢</label>
<input 
    type="text" 
    id="reset_code" 
    name="reset_code" 
    placeholder="000000" 
    required 
    maxlength="6"
    pattern="[0-9]{6}"
    inputmode="numeric"
    autocomplete="off"
    data-lpignore="true"
/>
<p class="helper-text">Check your email for a 6-digit reset code (manual entry only)</p>
<p class="expiry-notice">⏰ Code expires in 15 minutes</p>
<p class="attempts-remaining" id="attempts">3 attempts remaining</p>

<label for="new_password">New Password 🔒</label>
<div class="password-field-wrapper">
    <input 
        type="password" 
        id="new_password" 
        name="new_password" 
        placeholder="Create a strong password" 
        required 
        minlength="8"
        autocomplete="new-password"
    />
    <button type="button" class="toggle-password" aria-label="Toggle password visibility">👁️</button>
</div>

<div class="password-strength">
    <div class="strength-bar-container">
        <div id="strength-bar" class="strength-bar"></div>
    </div>
    <span id="strength-text">Weak</span>
</div>

<div class="password-requirements">
    <p><strong>Requirements:</strong></p>
    <ul>
        <li id="req-length">☐ At least 8 characters</li>
        <li id="req-upper">☐ Uppercase letter (A-Z)</li>
        <li id="req-lower">☐ Lowercase letter (a-z)</li>
        <li id="req-number">☐ Number (0-9)</li>
    </ul>
</div>

<label for="confirm_password">Confirm New Password 🔒</label>
<div class="password-field-wrapper">
    <input 
        type="password" 
        id="confirm_password" 
        name="confirm_password" 
        placeholder="Re-enter your new password" 
        required 
        minlength="8"
        autocomplete="new-password"
    />
    <button type="button" class="toggle-password" aria-label="Toggle password visibility">👁️</button>
</div>
<span id="match-indicator"></span>
```

#### Validation Function
```python
def validate_password_reset(email, reset_code, new_password, confirm_password):
    errors = {}
    
    # Email validation
    if not email:
        errors['email'] = "Email is required"
    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors['email'] = "Please enter a valid email address"
    
    # Reset code validation
    if not reset_code:
        errors['reset_code'] = "Reset code is required"
    elif not re.match(r'^\d{6}$', reset_code):
        errors['reset_code'] = "Reset code must be exactly 6 digits"
    
    # New password validation
    if not new_password:
        errors['new_password'] = "New password is required"
    elif len(new_password) < 8:
        errors['new_password'] = "Password must be at least 8 characters long"
    
    # Confirm password validation
    if not confirm_password:
        errors['confirm_password'] = "Please confirm your new password"
    elif new_password != confirm_password:
        errors['confirm_password'] = "Passwords do not match"
    
    # Verify reset code
    if not errors:
        try:
            user = User.objects.get(email__iexact=email.lower())
            otp_record = EmailOTP.objects.get(
                user=user,
                purpose='PASSWORD_RESET',
                used_at__isnull=True
            )
            
            # Check expiry (15 minutes)
            if timezone.now() > otp_record.expires_at:
                errors['reset_code'] = "Reset code has expired. Please request a new one."
            
            # Check attempts (max 3)
            elif otp_record.attempts >= 3:
                errors['reset_code'] = "Too many failed attempts. Please request a new code."
            
            # Verify code hash
            elif not check_password(reset_code, otp_record.code_hash):
                otp_record.attempts += 1
                otp_record.save()
                attempts_left = 3 - otp_record.attempts
                errors['reset_code'] = f"Invalid code. {attempts_left} {'attempts' if attempts_left != 1 else 'attempt'} remaining."
        
        except (User.DoesNotExist, EmailOTP.DoesNotExist):
            errors['_form'] = "Invalid email or reset code."
    
    # Check against common passwords
    if not errors and new_password.lower() in COMMON_PASSWORDS:
        errors['new_password'] = "This password is too common. Please choose a more unique password."
    
    return errors
```

#### Success Response
```json
{
    "success": true,
    "message": "Password reset successful! You can now log in with your new password. Redirecting...",
    "redirect": "/login"
}
```
- Update user password: `user.set_password(new_password)`
- Mark OTP as used: `otp_record.used_at = timezone.now()`
- Log password reset to audit trail
- Send confirmation email to user
- Invalidate all active sessions (force re-login)
- Redirect to login page

#### Error Responses

**1. Field Validation Errors:**
```json
{
    "success": false,
    "errors": {
        "email": "Please enter a valid email address",
        "reset_code": "Reset code must be exactly 6 digits",
        "new_password": "Password must contain at least one uppercase letter",
        "confirm_password": "Passwords do not match"
    }
}
```

**2. Invalid Reset Code:**
```json
{
    "success": false,
    "errors": {
        "reset_code": "Invalid code. 2 attempts remaining."
    },
    "attempts_remaining": 2
}
```

**3. Code Expired:**
```json
{
    "success": false,
    "errors": {
        "reset_code": "Reset code has expired. Please request a new one."
    },
    "expired": true,
    "redirect_to_request": true
}
```

**4. Too Many Attempts:**
```json
{
    "success": false,
    "errors": {
        "reset_code": "Too many failed attempts. Please request a new code."
    },
    "locked": true,
    "redirect_to_request": true
}
```

**5. Invalid Email/Code Combination:**
```json
{
    "success": false,
    "message": "Invalid email or reset code. Please check your information and try again.",
    "error_type": "invalid_credentials"
}
```

**6. Common Password:**
```json
{
    "success": false,
    "errors": {
        "new_password": "This password is too common. Please choose a more unique password."
    }
}
```

**7. Server Error:**
```json
{
    "success": false,
    "message": "Failed to reset password. Please try again or contact support.",
    "error_type": "server_error"
}
```

#### Rate Limiting
- Max 3 verification attempts per reset code
- Max 10 reset attempts per hour per IP address
- Display countdown after rate limit hit

#### Security Features
- Email + code combination required (prevents code guessing)
- 15-minute OTP expiry
- Max 3 attempts per code
- All active sessions invalidated after password reset
- Confirmation email sent to user
- Audit log entry created
- Password strength enforcement
- Common password blacklist

---

## Design Guidelines

### UI/UX Principles
- **Apple-Inspired Design**: Clean, minimal, spacious
- **Mobile-First**: Responsive forms, touch-friendly
- **Accessibility**: WCAG 2.1 AA compliance, keyboard navigation
- **Real-Time Validation**: Instant feedback, clear error messages
- **Progress Indicators**: Show steps for multi-step flows
- **Security Visibility**: Password strength meter, session timeout warnings
- **Smart Session Management**: Never logout during active work or with unsaved data

### Color Scheme (Contextual, No Purple)
- **Success**: Green (#10b981) - Approvals, successful actions
- **Error**: Red (#ef4444) - Validation errors, failed actions
- **Warning/Alert**: Amber (#f59e0b) - Pending items, cautions
- **Info**: Blue (#3b82f6) - General information, links
- **Neutral**: Gray (#6b7280) - Secondary text, borders

### Form Styling Standards
```css
/* Input Fields */
- Height: 44px (mobile touch-friendly)
- Border: 1px solid #d1d5db
- Border-radius: 8px
- Focus: 2px solid #3b82f6 (blue)
- Error: 2px solid #ef4444 (red)
- Success: 2px solid #10b981 (green)
- Font: 16px (prevents mobile zoom)

/* Buttons */
- Primary: bg-blue-600, hover:bg-blue-700 (blue)
- Success: bg-green-600, hover:bg-green-700 (green)
- Danger: bg-red-600, hover:bg-red-700 (red)
- Warning: bg-amber-600, hover:bg-amber-700 (amber)
- Secondary: bg-gray-200, hover:bg-gray-300
- Height: 44px, rounded-lg

/* Error Messages */
- Color: #dc2626
- Icon: ⚠️ or ❌
- Position: Below field

/* Success Messages */
- Color: #16a34a
- Icon: ✓
- Position: Top of form or inline
```

### Password Strength Indicator
```
Weak:      ████░░░░░░░░░░░░ 🔴 (< 8 chars)
Fair:      ████████░░░░░░░░ 🟠 (8+ chars)
Good:      ████████████░░░░ 🟡 (8+ chars + mixed case)
Strong:    ████████████████ 🟢 (8+ chars + mixed + numbers)
```

---

# EMAIL TEMPLATES & SAMPLES

## Email 1: User Invitation Email

**Template File:** `communications/emails/invitation.html`  
**Subject:** `Welcome to Chesanto Bakery Management System`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #ffffff; padding: 40px 30px; border: 1px solid #e5e7eb; }
        .credentials-box { background: #f3f4f6; border-left: 4px solid #3b82f6; padding: 20px; margin: 20px 0; border-radius: 5px; }
        .credential-item { margin: 10px 0; font-size: 14px; }
        .credential-label { font-weight: bold; color: #6b7280; }
        .credential-value { color: #111827; font-family: 'Courier New', monospace; background: #fff; padding: 5px 10px; border-radius: 3px; display: inline-block; }
        .button { display: inline-block; background: #3b82f6; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600; }
        .button:hover { background: #2563eb; }
        .warning { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 5px; }
        .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🥖 Chesanto Bakery</h1>
            <p>Welcome to the Team!</p>
        </div>
        <div class="content">
            <p>Hi <strong>{{ name }}</strong>,</p>
            
            <p>You've been invited to join the Chesanto Bakery Management System as a <strong>{{ role }}</strong>.</p>
            
            <p>Use the credentials below to access your account:</p>
            
            <div class="credentials-box">
                <div class="credential-item">
                    <span class="credential-label">Login URL:</span><br>
                    <span class="credential-value">{{ login_url }}</span>
                </div>
                <div class="credential-item">
                    <span class="credential-label">Email:</span><br>
                    <span class="credential-value">{{ email }}</span>
                </div>
                <div class="credential-item">
                    <span class="credential-label">Temporary Password:</span><br>
                    <span class="credential-value">{{ password }}</span>
                </div>
            </div>
            
            <div class="warning">
                <strong>⚠️ Important:</strong> You'll be required to change this password on your first login for security reasons.
            </div>
            
            <center>
                <a href="{{ login_url }}" class="button">Login to Your Account</a>
            </center>
            
            <p><strong>What happens next?</strong></p>
            <ol>
                <li>Click the button above or visit {{ login_url }}</li>
                <li>Enter your email and temporary password</li>
                <li>Create a new secure password</li>
                <li>Start using the system!</li>
            </ol>
            
            <p>If you have any questions, contact the administrator or reply to this email.</p>
            
            <p>Best regards,<br>
            <strong>Chesanto Bakery Team</strong></p>
        </div>
        <div class="footer">
            <p>This email was sent to {{ email }} | <a href="{{ login_url }}">Login</a></p>
            <p>&copy; 2025 Chesanto Bakery. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
```

**Plain Text Version:**
```
Chesanto Bakery - Welcome to the Team!

Hi {{ name }},

You've been invited to join the Chesanto Bakery Management System as a {{ role }}.

Login Details:
--------------
Login URL: {{ login_url }}
Email: {{ email }}
Temporary Password: {{ password }}

⚠️ IMPORTANT: You'll be required to change this password on your first login for security reasons.

What happens next?
1. Visit {{ login_url }}
2. Enter your email and temporary password
3. Create a new secure password
4. Start using the system!

If you have any questions, contact the administrator.

Best regards,
Chesanto Bakery Team

---
© 2025 Chesanto Bakery. All rights reserved.
```

---

## Email 2: OTP Code (Login/Password Reset)

**Template File:** `communications/emails/otp.html`  
**Subject:** `Your Verification Code - Chesanto Bakery`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; padding: 30px 20px; }
        .otp-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center; padding: 40px; margin: 30px 0; border-radius: 10px; }
        .otp-code { font-size: 48px; font-weight: bold; letter-spacing: 10px; font-family: 'Courier New', monospace; margin: 20px 0; }
        .expiry { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 5px; color: #92400e; }
        .security-tip { background: #f3f4f6; padding: 20px; border-radius: 8px; margin-top: 20px; }
        .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Verification Code</h1>
        </div>
        <div class="content">
            <p>Hi <strong>{{ name }}</strong>,</p>
            
            <p>You requested a verification code for <strong>{{ purpose }}</strong>.</p>
            
            <div class="otp-box">
                <p style="margin: 0; font-size: 16px;">Your verification code is:</p>
                <div class="otp-code">{{ otp_code }}</div>
                <p style="margin: 0; font-size: 14px;">Enter this code to continue</p>
            </div>
            
            <div class="expiry">
                <strong>⏰ This code expires in {{ expiry_minutes }} minutes</strong><br>
                <small>After that, you'll need to request a new code.</small>
            </div>
            
            <div class="security-tip">
                <p><strong>🔒 Security Tips:</strong></p>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>Never share this code with anyone</li>
                    <li>Chesanto staff will never ask for your code</li>
                    <li>If you didn't request this code, ignore this email and contact admin</li>
                </ul>
            </div>
            
            <p>If you're having trouble, contact the administrator or reply to this email.</p>
            
            <p>Best regards,<br>
            <strong>Chesanto Bakery Team</strong></p>
        </div>
        <div class="footer">
            <p>This email was sent to {{ email }}</p>
            <p>&copy; 2025 Chesanto Bakery. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
```

**Plain Text Version:**
```
Chesanto Bakery - Verification Code

Hi {{ name }},

You requested a verification code for {{ purpose }}.

YOUR VERIFICATION CODE:
========================
{{ otp_code }}
========================

⏰ This code expires in {{ expiry_minutes }} minutes.

🔒 Security Tips:
- Never share this code with anyone
- Chesanto staff will never ask for your code
- If you didn't request this code, ignore this email

Best regards,
Chesanto Bakery Team

---
© 2025 Chesanto Bakery. All rights reserved.
```

---

## Email 3: Account Approved

**Template File:** `communications/emails/approval.html`  
**Subject:** `🎉 Your Chesanto Account Has Been Approved`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 40px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #ffffff; padding: 40px 30px; border: 1px solid #e5e7eb; }
        .success-badge { font-size: 64px; margin-bottom: 10px; }
        .button { display: inline-block; background: #10b981; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600; }
        .info-box { background: #eff6ff; border-left: 4px solid #3b82f6; padding: 20px; margin: 20px 0; border-radius: 5px; }
        .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
            <div class="success-badge">✅</div>
            <h1>Account Approved!</h1>
            <p>You can now access the system</p>
        </div>
        <div class="content">
            <p>Hi <strong>{{ name }}</strong>,</p>
            
            <p>Great news! Your Chesanto Bakery account has been approved by <strong>{{ approved_by }}</strong>.</p>
            
            <div class="info-box">
                <p><strong>Your Account Details:</strong></p>
                <ul style="margin: 10px 0;">
                    <li><strong>Role:</strong> {{ role }}</li>
                    <li><strong>Email:</strong> {{ email }}</li>
                    <li><strong>Status:</strong> ✓ Active</li>
                </ul>
            </div>
            
            <p>You can now login and start using the system.</p>
            
            <center>
                <a href="{{ login_url }}" class="button">Login to Your Account</a>
            </center>
            
            <p><strong>Getting Started:</strong></p>
            <ol>
                <li>Click the button above to visit the login page</li>
                <li>Enter your email and password</li>
                <li>Explore your dashboard and features</li>
                <li>Contact admin if you need training or support</li>
            </ol>
            
            <p>Welcome to the team! If you have any questions, don't hesitate to reach out.</p>
            
            <p>Best regards,<br>
            <strong>Chesanto Bakery Team</strong></p>
        </div>
        <div class="footer">
            <p>This email was sent to {{ email }} | <a href="{{ login_url }}">Login</a></p>
            <p>&copy; 2025 Chesanto Bakery. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
```

---

## Email 4: Password Changed Confirmation

**Template File:** `communications/emails/password_changed.html`  
**Subject:** `Password Changed - Chesanto Bakery`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #3b82f6; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #ffffff; padding: 40px 30px; border: 1px solid #e5e7eb; }
        .alert-box { background: #fef2f2; border-left: 4px solid #ef4444; padding: 20px; margin: 20px 0; border-radius: 5px; }
        .details-box { background: #f9fafb; padding: 15px; border-radius: 5px; margin: 15px 0; font-size: 14px; }
        .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔒 Password Changed</h1>
        </div>
        <div class="content">
            <p>Hi <strong>{{ name }}</strong>,</p>
            
            <p>Your password for Chesanto Bakery Management System was successfully changed.</p>
            
            <div class="details-box">
                <p><strong>Change Details:</strong></p>
                <ul style="margin: 10px 0;">
                    <li><strong>Date & Time:</strong> {{ timestamp }}</li>
                    <li><strong>IP Address:</strong> {{ ip_address }}</li>
                    <li><strong>Device:</strong> {{ user_agent }}</li>
                </ul>
            </div>
            
            <div class="alert-box">
                <p><strong>⚠️ Didn't make this change?</strong></p>
                <p>If you didn't change your password, your account may be compromised. Contact the administrator immediately:</p>
                <ul style="margin: 10px 0;">
                    <li>Email: admin@chesanto.com</li>
                    <li>Phone: +254 XXX XXX XXX</li>
                </ul>
            </div>
            
            <p>Your account security is important to us. Remember to:</p>
            <ul>
                <li>Use a strong, unique password</li>
                <li>Never share your password with anyone</li>
                <li>Log out when using shared computers</li>
            </ul>
            
            <p>Best regards,<br>
            <strong>Chesanto Bakery Team</strong></p>
        </div>
        <div class="footer">
            <p>This email was sent to {{ email }}</p>
            <p>&copy; 2025 Chesanto Bakery. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
```

---

## Email 5: Daily Entry Reminder (Salesmen/Dispatch)

**Template File:** `communications/emails/daily_reminder.html`  
**Subject:** `⏰ Daily Entry Reminder - {{ date }}`

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f59e0b; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #ffffff; padding: 40px 30px; border: 1px solid #e5e7eb; }
        .reminder-box { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 20px; margin: 20px 0; border-radius: 5px; }
        .button { display: inline-block; background: #f59e0b; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; margin: 20px 0; font-weight: 600; }
        .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⏰ Daily Entry Reminder</h1>
            <p>{{ date }}</p>
        </div>
        <div class="content">
            <p>Hi <strong>{{ name }}</strong>,</p>
            
            <p>This is a friendly reminder to submit your daily entry for <strong>{{ date }}</strong>.</p>
            
            <div class="reminder-box">
                <p><strong>📝 What to do:</strong></p>
                <ul style="margin: 10px 0;">
                    <li>Log into the system</li>
                    <li>Submit your daily {{ entry_type }} report</li>
                    <li>Even if there were no {{ entry_type }} today, enter zero</li>
                </ul>
            </div>
            
            <p><strong>Why is this important?</strong><br>
            Daily entries help prevent tracking gaps and ensure accurate records. Even zero entries are valuable!</p>
            
            <center>
                <a href="{{ dashboard_url }}" class="button">Submit Entry Now</a>
            </center>
            
            <p><small>Missing entries are flagged to the administrator. Thank you for your cooperation!</small></p>
            
            <p>Best regards,<br>
            <strong>Chesanto Bakery Team</strong></p>
        </div>
        <div class="footer">
            <p>This email was sent to {{ email }}</p>
            <p>&copy; 2025 Chesanto Bakery. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
```

---

# PART 2: TECHNICAL SPECIFICATIONS (FOR DEVELOPERS)

## App Architecture

```
apps/
├── accounts/              # Authentication & users
│   ├── models.py         # User, EmailOTP, UserInvitation, AuditLog
│   ├── views.py          # Login, Register, Invite, OTP
│   ├── forms.py          # Auth forms (match design language)
│   ├── middleware.py     # Activity tracking, route protection
│   ├── decorators.py     # @role_required, @auth_required
│   └── utils.py          # OTP, password, superadmin checks
│
├── communications/        # Email & SMS (SEPARATE)
│   ├── services/
│   │   ├── email.py      # Gmail SMTP
│   │   └── sms.py        # Future SMS
│   ├── templates/emails/
│   │   ├── invitation.html
│   │   ├── otp.html
│   │   ├── password_reset.html
│   │   └── approval.html
│   └── models.py         # EmailLog, SMSLog
│
└── [production, sales, inventory, etc.]
    └── # Import from communications for emails
```

**Why Separate Communications?**
- **Reusable**: All apps send emails
- **Maintainable**: Update templates once
- **Testable**: Mock easily
- **Scalable**: Add SMS/push later

## Environment Variables

```bash
# Auto-Superadmin (Read from .env on startup)
SUPERADMIN_EMAILS="madame@chesanto.com,joe@coophive.network"

# Server URL (for email links)
SERVER_URL="https://chesanto.railway.app"

# OTP (Manual entry only - no autofill)
OTP_CODE_LENGTH=6
OTP_CODE_VALIDITY=600        # 10 min
PASSWORD_RESET_CODE_VALIDITY=900  # 15 min
OTP_AUTOCOMPLETE=False       # Disable browser autofill

# Session (Smart logout - detects unsaved data)
SESSION_COOKIE_AGE=3600      # 1 hour inactivity
SESSION_SAVE_EVERY_REQUEST=True
SESSION_COOKIE_SECURE=True   # Prod only
RE_AUTH_INTERVAL=86400       # 24 hours (prompts only, no force logout)
SMART_LOGOUT_ENABLED=True    # Detects unsaved data before logout

# Rate Limits
LOGIN_RATE_LIMIT="10/m"
PASSWORD_RESET_RATE_LIMIT="3/h"

# Audit
AUDIT_LOG_RETENTION_DAYS=365

# Business Operations
SUNDAY_AUTO_SKIP=True        # Company closed on Sundays
OPERATING_DAYS="1,2,3,4,5,6" # Monday-Saturday (0=Sunday)
AUDIT_LOG_ARCHIVE_ENABLED=True
AUDIT_TRACK_NAVIGATION=True

# Email (Gmail SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL="Chesanto Bakery <your@gmail.com>"
```

## Database Schema

### Users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE,
    email VARCHAR(254) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    role VARCHAR(20) NOT NULL,
    phone_number VARCHAR(15),
    is_active BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT FALSE,
    must_change_password BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    last_password_login TIMESTAMP,
    last_activity TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),
    custom_permissions JSONB DEFAULT '{}'
);
```

### User Invitations
```sql
CREATE TABLE user_invitations (
    id SERIAL PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    temp_password VARCHAR(128) NOT NULL,
    invited_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    used_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

### Email OTP
```sql
CREATE TABLE email_otp (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    code_hash VARCHAR(255) NOT NULL,
    purpose VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    attempts INTEGER DEFAULT 0,
    ip_address VARCHAR(45)
);
```

### Audit Logs
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    session_id VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    url_path VARCHAR(500),
    model_name VARCHAR(100),
    object_id INTEGER,
    changes JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    success BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);

CREATE TABLE audit_log_archives (
    id SERIAL PRIMARY KEY,
    archived_at TIMESTAMP DEFAULT NOW(),
    log_data JSONB NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    record_count INTEGER NOT NULL
);
```

### Email Logs
```sql
CREATE TABLE email_logs (
    id SERIAL PRIMARY KEY,
    recipient VARCHAR(254) NOT NULL,
    subject VARCHAR(255),
    template VARCHAR(100),
    sent_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20),
    error_message TEXT
);
```

## Django Models

```python
# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = 'SUPERADMIN', 'CEO / Developer'
        ADMIN = 'ADMIN', 'Accountant'
        PRODUCT_MANAGER = 'PRODUCT_MANAGER', 'Production Manager'
        DEPT_HEAD = 'DEPT_HEAD', 'Department Head'
        DISPATCH = 'DISPATCH', 'Dispatch Officer'
        SALESMAN = 'SALESMAN', 'Sales Representative'
        SECURITY = 'SECURITY', 'Gate Man / Security'
    
    role = models.CharField(max_length=20, choices=Role.choices)
    phone_number = models.CharField(max_length=15, blank=True)
    is_approved = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False)
    last_password_login = models.DateTimeField(null=True)
    last_activity = models.DateTimeField(null=True)
    created_by = models.ForeignKey('self', null=True, on_delete=models.SET_NULL)
    custom_permissions = models.JSONField(default=dict, blank=True)  # For superadmin modifications


class UserInvitation(models.Model):
    email = models.EmailField()
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=User.Role.choices)
    temp_password = models.CharField(max_length=128)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField()


class EmailOTP(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = 'LOGIN'
        PASSWORD_RESET = 'PASSWORD_RESET'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=255)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True)
    attempts = models.IntegerField(default=0)


class AuditLog(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=100, null=True)
    action = models.CharField(max_length=50)  # LOGIN, LOGOUT, VIEW, CREATE, UPDATE, DELETE, NAVIGATE
    url_path = models.CharField(max_length=500, null=True)  # For navigation tracking
    model_name = models.CharField(max_length=100, null=True)
    object_id = models.IntegerField(null=True)
    changes = models.JSONField(null=True)  # Before/after values
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)


class AuditLogArchive(models.Model):
    """Archived logs older than 1 year"""
    archived_at = models.DateTimeField(auto_now_add=True)
    log_data = models.JSONField()  # Compressed audit log data
    start_date = models.DateField()
    end_date = models.DateField()
    record_count = models.IntegerField()


# apps/communications/models.py
class EmailLog(models.Model):
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    template = models.CharField(max_length=100)
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20)
    error_message = models.TextField(blank=True)
```

## Core Functions

```python
# apps/accounts/utils.py
import os
import random
import string
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta

def is_superadmin_email(email):
    """Check if email in SUPERADMIN_EMAILS env"""
    emails = os.getenv('SUPERADMIN_EMAILS', '').split(',')
    return email.strip().lower() in [e.strip().lower() for e in emails]


def generate_temp_password():
    """Generate random temp password (8 characters: letters + digits)"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=8))


def generate_otp(user, purpose='LOGIN'):
    """Generate 6-digit OTP"""
    from .models import EmailOTP
    
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    validity = settings.OTP_CODE_VALIDITY if purpose == 'LOGIN' else settings.PASSWORD_RESET_CODE_VALIDITY
    
    EmailOTP.objects.create(
        user=user,
        code_hash=make_password(code),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(seconds=validity)
    )
    return code


def validate_otp(user, code, purpose='LOGIN'):
    """Validate OTP (max 3 attempts)"""
    from .models import EmailOTP
    
    otp = EmailOTP.objects.filter(
        user=user,
        purpose=purpose,
        used_at__isnull=True,
        expires_at__gt=timezone.now()
    ).order_by('-created_at').first()
    
    if not otp or otp.attempts >= 3:
        return False
    
    otp.attempts += 1
    otp.save()
    
    if check_password(code, otp.code_hash):
        otp.used_at = timezone.now()
        otp.save()
        return True
    return False


def requires_reauth(user):
    """Check if 24 hours passed"""
    if not user.last_password_login:
        return True
    elapsed = timezone.now() - user.last_password_login
    return elapsed.total_seconds() >= settings.RE_AUTH_INTERVAL


# apps/communications/services/email.py
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from ..models import EmailLog

class EmailService:
    @staticmethod
    def send_invitation(email, name, role, temp_password, login_url):
        """Send invitation with temp password"""
        context = {
            'name': name,
            'email': email,
            'password': temp_password,
            'login_url': login_url
        }
        
        html = render_to_string('communications/emails/invitation.html', context)
        
        try:
            send_mail(
                subject='Welcome to Chesanto Bakery',
                message=f'Login: {login_url}\nEmail: {email}\nPassword: {temp_password}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html
            )
            EmailLog.objects.create(recipient=email, template='invitation', status='SENT')
            return True
        except Exception as e:
            EmailLog.objects.create(recipient=email, template='invitation', status='FAILED', error_message=str(e))
            return False
    
    @staticmethod
    def send_otp(email, code):
        """Send OTP code"""
        try:
            send_mail(
                subject='Your Login Code',
                message=f'Your code: {code}\nExpires in 10 minutes.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email]
            )
            EmailLog.objects.create(recipient=email, template='otp', status='SENT')
            return True
        except:
            return False
```

## Installation

```bash
# 1. Install
pip install django-auditlog django-ratelimit

# 2. Settings
INSTALLED_APPS = [
    'apps.accounts',
    'apps.communications',
    'auditlog',
    'django_ratelimit',
]

AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'apps.accounts.middleware.AuthProtectionMiddleware',
]

# 3. Migrate
python manage.py makemigrations accounts communications
python manage.py migrate

# 4. Set env vars
SUPERADMIN_EMAILS=madame@chesanto.com,joe@coophive.network
SERVER_URL=https://chesanto.railway.app
```

## Implementation & Deployment Plan

### Phase 1: Development (Oct 15-18, 2025)
- [ ] Create `apps.accounts` Django app
- [ ] Create `apps.communications` Django app
- [ ] Implement models (User, EmailOTP, UserInvitation, AuditLog, AuditLogArchive, EmailLog)
- [ ] Implement core functions (utils.py)
- [ ] Implement views (login, register, invite, OTP verification)
- [ ] Implement middleware (activity tracking, route protection)
- [ ] Create forms (match Apple-inspired design language)
- [ ] Create email templates (invitation, OTP, password reset, approval)
- [ ] Run migrations
- [ ] Set up environment variables

### Phase 2: Testing (Post-Development)
**Alpha Testing (Week of Oct 19-25):**
- [ ] Madame (Accountant) tests user invite flow
- [ ] Madame tests user approval/rejection
- [ ] Product manager tests role-based access
- [ ] Developer tests all security features (OTP, 24hr re-auth, rate limiting)
- [ ] Test dispatch user management
- [ ] Test salesman daily entry enforcement

**Beta Testing (Week of Oct 26-Nov 1):**
- [ ] Dispatch personnel test login and permissions
- [ ] Salesmen test daily sales entry workflow
- [ ] Security guard tests gate logs entry
- [ ] Full audit log review by Superadmin
- [ ] Test mandatory daily entry reminders
- [ ] Test commission tracking permissions (link to Sales Module)
- [ ] Test crate tracking permissions (link to Assets/Inventory)

### Phase 3: Production Deployment
- [ ] Deploy to Railway.com
- [ ] Set environment variables in Railway dashboard
- [ ] Configure Gmail SMTP with production credentials
- [ ] Test email delivery in production
- [ ] Create initial Superadmin accounts (madame@chesanto.com, joe@coophive.network)
- [ ] Verify 2FA working in production
- [ ] Verify all routes protected
- [ ] Monitor first-week performance and logs

### Phase 4: Documentation & Training (Post-Deployment)
- [ ] Write user documentation for each role
- [ ] Create video tutorials for common tasks
- [ ] Document troubleshooting guides
- [ ] Admin training for Madame (user management, logs review)
- [ ] Department head & product manager training
- [ ] Dispatch, salesman, and security guard training
- [ ] Create quick reference cards
- [ ] Setup help desk/support channel

---

**Document Version:** 2.0  
**Last Updated:** October 15, 2025
