# 2FA Authentication Implementation Plan
**Priority: URGENT - Week of Oct 15-22, 2025**  
**Status: Planning Phase**

## Executive Summary
Based on CEO meeting (Oct 12, 2025), 2FA authentication is the **top priority this week** to secure the system before any financial data is entered. This plan outlines the complete implementation strategy.

---

## Business Requirements (from CEO Meeting)

### Critical Security Needs
1. **Two-Factor Authentication (2FA)** - Mandatory for all users
2. **Role-Based Access Control (RBAC)** - Different permissions per role
3. **User Activity Logging** - Complete audit trail of all actions
4. **User Accountability** - Link all transactions to specific users (especially dispatch personnel)

### User Roles Identified
| Role | Users | Primary Responsibilities | Access Level |
|------|-------|-------------------------|--------------|
| **Administrator (main: Joe, CEO & Madame)** | Multiple | Full system access, user management, final approvals | FULL |
| **Accountant** | 1 person | Daily data entry, petty cash, alpha testing | HIGH |
| **Product Manager** | Multiple | Production data input, recipe tracking | MEDIUM |
| **Department Head** | Multiple | Data verification, reports viewing | MEDIUM |
| **Dispatch Personnel** | Multiple | Crate tracking, delivery confirmation | LIMITED |
| **Salesman** | Multiple | Daily sales entry, zero-entry reports | LIMITED |

---

## Technical Requirements

### 1. Authentication Methods to Support
**✅ APPROVED: Email-based OTP ONLY**
- [x] **Email-based OTP** (One-Time Password via Gmail SMTP)
  - 6-digit code
  - Valid for 10 minutes
  - Required for every login (no exceptions)
- [ ] ~~SMS-based OTP~~ (Not needed - email sufficient)
- [ ] ~~TOTP App~~ (Not needed - simplicity over complexity)

### 2. Security Features Required
- [x] Password complexity requirements (min 8 chars, mixed case, numbers)
- [x] Account lockout after 5 failed log-in attempts + **→ Re-authentication every 24 hours**
- [x] Session timeout after **1 hour** inactivity (APPROVED)
- [x] Force logout all devices option (for Admin)
- [x] Password reset with email verification (6-digit code)
- [x] IP address logging for suspicious activity detection
- [x] Email notification for ALL password changes
- [x] ~~Trusted device option~~ **→ REJECTED - No trusted devices**

### 3. User Management Features
- [x] User creation by SuperAdmin (sends invite)
- [x] Self-registration with SuperAdmin approval workflow
- [x] User deactivation (SuperAdmin only)
- [x] Role assignment and modification (SuperAdmin only)
- [x] User activity dashboard (who's logged in, last activity)
- [x] Pending registrations review page (Admin)

### 4. Audit Logging Requirements
**✅ APPROVED: TRACK EVERYTHING**

Track the following for **EVERY user action** (no exceptions):
- User ID and name
- Timestamp (Africa/Nairobi timezone)
- Action performed (login, data entry, edit, delete, view, export, report)
- IP address
- Device/browser info (User-Agent)
- Before/after values (for data changes)
- Success/failure status
- Session ID (for tracing related actions)

**Access Control:**
- Admin: Can view ALL logs (everyone's activity)
- Regular Users: Can view ONLY their own activity logs
- Retention: Minimum 1 year (financial/legal compliance)

---

## Implementation Approach

### Phase 1: Core Authentication (Days 1-2)
**Goal:** Basic login with strong passwords

**Tasks:**
1. Create custom User model with role field
2. Extend Django's built-in authentication
3. Create login/logout views and templates
4. Implement password complexity validation
5. Add session management
6. Basic unit tests

**Deliverables:**
- Users can login with username/email + password
- Sessions expire after inactivity
- Failed login attempts are tracked

### Phase 2: 2FA Implementation (Days 3-4)
**Goal:** Add second authentication factor

**Tasks:**
1. Install 2FA library (`django-otp` or `pyotp`)
2. Generate QR codes for TOTP setup
3. Create OTP verification flow
4. Implement email OTP as alternative
5. Add "Trust this device" option (7 days)
6. Create 2FA setup wizard for first-time users
7. Test 2FA flows

**Deliverables:**
- Users must verify 2FA code after password
- Email backup codes available
- Smooth onboarding experience

### Phase 3: Role-Based Access Control (Days 5-6)
**Goal:** Restrict features by role

**Tasks:**
1. Define permission groups per role
2. Create permission decorators for views
3. Implement template-level permission checks
4. Add role-based menu/navigation
5. Create permission denied pages
6. Test all role combinations

**Deliverables:**
- Each role sees only their allowed features
- Graceful handling of unauthorized access
- Clear permission boundaries

### Phase 4: Audit Logging (Day 7)
**Goal:** Track all user activity

**Tasks:**
1. Install audit library (`django-auditlog` or custom)
2. Configure models to track
3. Create activity log viewer (Admin only)
4. Add login/logout logging
5. Implement log retention policy (1 year)
6. Export logs to CSV/PDF

**Deliverables:**
- Complete audit trail of all actions
- Searchable activity logs
- Compliance-ready reporting

---

## Technology Stack Decision

### Option A: Django Built-in + Extensions (RECOMMENDED)
**Pros:**
- Leverages Django's mature auth system
- Well-documented and tested
- Easy to maintain
- Free and open-source

**Stack:**
```
django.contrib.auth (base authentication)
+ django-otp (2FA via TOTP)
+ pyotp (OTP generation)
+ qrcode (QR code generation)
+ django-auditlog (activity tracking)
```

**Cons:**
- Requires combining multiple packages
- Need to customize for email OTP

### Option B: All-in-One (django-allauth)
**Pros:**
- Social auth support (future: Google login)
- Email verification built-in
- 2FA extensions available

**Cons:**
- Heavier package
- More complexity than needed now
- Overkill for current requirements

**DECISION:** Go with **Option A** - simpler, more control, fits current needs

---

## User Experience Flow

### ✅ First-Time User Setup (Admin Invite - Preferred)
```
1. Admin creates account in system
2. System generates unique invitation link (valid 48 hours)
3. System sends email: "Welcome to Chesanto Bakery System - Set Your Password"
4. User clicks link → Redirected to password setup page
5. User enters new password (with strength indicator)
6. User confirms password
7. Password saved → Auto-login (skip OTP for first setup)
8. User sees welcome dashboard with role-appropriate features
```

### ✅ First-Time User Setup (Self-Registration - New Hires)
```
1. User visits public registration page
2. User fills form: Name, Email, Phone, Desired Role, Reason
3. User submits form
4. System sends email: "Registration Received - Pending Approval"
5. System notifies Admin: "New User Registration Awaiting Approval"
6. Admin reviews request in approval dashboard
7a. If APPROVED:
    - System sends email: "Account Approved - Set Your Password"
    - User clicks link → Sets password → Logs in
7b. If REJECTED:
    - System sends email: "Registration Denied" with reason (optional)
```

### ✅ Daily Login Flow (UPDATED - 24hr re-auth)
```
1. User enters username + password
2. System validates credentials
3. System checks last login time:
   - If < 24 hours ago AND session active → Login successful (skip OTP)
   - If ≥ 24 hours ago OR new session → Proceed to step 4
4. System generates 6-digit OTP code
5. System sends email: "Your Login Code: 123456 (valid 10 minutes)"
6. User enters OTP on verification page
7. System validates OTP (expires after 10 minutes)
8. Login successful → User sees role-appropriate dashboard
9. Activity timer starts (1 hour inactivity = auto-logout)
```

### ✅ Password Reset Flow (APPROVED)
```
1. User clicks "Forgot Password" on login page
2. User enters registered email address
3. System verifies account exists
4. System generates 6-digit reset code
5. System sends email: "Password Reset Code: 123456 (valid 15 minutes)"
6. User redirected to "Enter Reset Code" page
7. User enters 6-digit code
8. System validates code (max 3 attempts, expires in 15 minutes)
9. User redirected to "Set New Password" page
10. User enters new password (twice for confirmation)
11. System validates password strength
12. System saves new password (hashed)
13. System sends email: "Your password was changed on Oct 15, 2025 at 2:30 PM"
14. User redirected to login page
15. User logs in with new password + email OTP
16. END
```

### ~~Account Lockout Flow~~ (NOT USED - 24hr re-auth instead)
```
Removed - No account lockout policy.
Instead: Users must re-authenticate every 24 hours with password + OTP.
```

---

## Testing Strategy

### Unit Tests
- [ ] User model creation with all roles
- [ ] Password validation rules
- [ ] OTP generation and verification
- [ ] Session timeout logic
- [ ] Permission checks for each role

### Integration Tests
- [ ] Complete login flow (password + 2FA)
- [ ] Password reset flow
- [ ] Account lockout and unlock
- [ ] Role-based access restrictions
- [ ] Audit log creation

### User Acceptance Testing (UAT)
**Participants:**
- Madame (Admin role)
- Accountant (alpha tester)
- One representative from each role

**Test Scenarios:**
1. First-time setup experience
2. Daily login (with and without trusted device)
3. Forgotten password recovery
4. 2FA device lost (backup codes)
5. Try accessing unauthorized features
6. Review activity logs

---

## Security Considerations

### Data Protection
- Passwords hashed with bcrypt (Django default)
- 2FA secrets encrypted at rest
- Session tokens rotated on privilege elevation
- HTTPS enforced in production (Railway handles this)

### Attack Prevention
- Rate limiting on login attempts (django-ratelimit)
- CSRF protection (Django default)
- SQL injection protection (Django ORM)
- XSS protection (Django templates auto-escape)

### Compliance
- GDPR considerations (data access, deletion)
- Kenyan Data Protection Act compliance
- Audit logs for financial regulations

---

## Database Schema (Planned)

### Users Table
```sql
- id (primary key)
- username (unique)
- email (unique)
- password_hash
- role (enum: ADMIN, ACCOUNTANT, PRODUCT_MANAGER, etc.)
- phone_number
- is_active (boolean)
- is_approved (boolean, for self-registration)
- last_login (timestamp)
- last_password_login (timestamp) -- track 24hr re-auth
- last_activity (timestamp) -- track 1hr inactivity
- created_at, updated_at
- created_by (foreign key to admin user, nullable)
```

### Email OTP Codes Table (NEW)
```sql
- id (primary key)
- user_id (foreign key)
- code (6-digit string, hashed)
- purpose (enum: LOGIN, PASSWORD_RESET)
- created_at (timestamp)
- expires_at (timestamp)
- used_at (timestamp, nullable)
- attempts (integer, default: 0)
- ip_address (varchar)
```

### User Invitations Table (NEW)
```sql
- id (primary key)
- email (unique for pending invites)
- token (unique, for invitation link)
- role (enum: assigned by admin)
- invited_by (foreign key to admin user)
- created_at (timestamp)
- expires_at (timestamp)
- accepted_at (timestamp, nullable)
```

### User Registration Requests Table (NEW)
```sql
- id (primary key)
- email (varchar)
- full_name (varchar)
- phone_number (varchar)
- desired_role (varchar)
- reason (text)
- status (enum: PENDING, APPROVED, REJECTED)
- reviewed_by (foreign key to admin, nullable)
- reviewed_at (timestamp, nullable)
- rejection_reason (text, nullable)
- created_at (timestamp)
```

### Audit Logs Table
```sql
- id (primary key)
- user_id (foreign key)
- session_id (varchar)
- action (varchar: LOGIN, LOGOUT, CREATE, UPDATE, DELETE, VIEW, EXPORT, REPORT)
- model_name (varchar: nullable)
- object_id (integer: nullable)
- changes (JSON: before/after values)
- ip_address (varchar)
- user_agent (text)
- timestamp (timestamp)
- success (boolean)
```

### ~~Trusted Devices Table~~ (REMOVED - Not needed)
```sql
REMOVED: No trusted device functionality per CEO decision
```

---

## Dependencies to Install

```txt
# Authentication & 2FA
django-otp>=1.2.0           # TOTP 2FA (will use email method instead)
pyotp>=2.9.0                # OTP generation (6-digit codes)
# NO qrcode - not using authenticator apps
# NO pillow - not generating QR codes

# Email OTP (PRIMARY METHOD)
# Already configured: Django SMTP via Gmail

# Audit Logging
django-auditlog>=2.3.0      # Activity tracking

# Security Enhancements
django-ratelimit>=4.1.0     # Rate limiting (password resets, login attempts)
django-axes>=6.1.0          # Failed login tracking (for logging, not lockout)

# User Registration/Approval Workflow
django-registration>=3.3    # Self-registration with approval

# Testing
factory-boy>=3.3.0          # Test data generation
faker>=19.0.0               # Fake data for tests
```

---

## Configuration Requirements

### Environment Variables Needed
```bash
# 2FA Settings (Email OTP)
OTP_EMAIL_SENDER="noreply@chesantobakery.com"
OTP_CODE_LENGTH=6
OTP_CODE_VALIDITY=600  # 10 minutes in seconds
PASSWORD_RESET_CODE_VALIDITY=900  # 15 minutes in seconds
PASSWORD_RESET_MAX_ATTEMPTS=3

# Session Security (UPDATED per CEO requirements)
SESSION_COOKIE_AGE=3600  # 1 hour (3600 seconds)
SESSION_SAVE_EVERY_REQUEST=True
SESSION_COOKIE_SECURE=True  # HTTPS only in production
SESSION_COOKIE_HTTPONLY=True
SESSION_EXPIRE_AT_BROWSER_CLOSE=False
RE_AUTH_INTERVAL=86400  # 24 hours (force re-auth)

# Rate Limiting (Password Reset Protection)
PASSWORD_RESET_RATE_LIMIT="3/h"  # 3 requests per hour per email
LOGIN_RATE_LIMIT="10/m"  # 10 login attempts per minute per IP

# User Registration
REGISTRATION_OPEN=True  # Allow self-registration
REGISTRATION_AUTO_LOGIN=False  # Require admin approval
INVITATION_EXPIRY=48  # hours

# Auto-Superadmin (CRITICAL - CEO REQUIREMENT)
SUPERADMIN_EMAILS="madame@chesanto.com,joe@coophive.network"  # Comma-separated list

# Audit Logging
AUDIT_LOG_RETENTION_DAYS=365  # 1 year minimum
```

---

## Rollout Plan

### Week 1 (Oct 15-22, 2025) - CURRENT WEEK
- **Mon-Tue:** Complete this planning document, get CEO approval
- **Wed-Thu:** Implement Phases 1-2 (core auth + 2FA)
- **Fri:** Implement Phase 3 (RBAC)
- **Sat:** Implement Phase 4 (audit logging)
- **Sun:** Testing and documentation

### Week 2 (Oct 23-29, 2025)
- **Mon-Tue:** UAT with Accountant (alpha tester)
- **Wed:** Bug fixes from alpha testing
- **Thu:** UAT with Madame (Admin testing)
- **Fri:** Deploy to production (Railway)
- **Sat:** Create user accounts for all staff
- **Sun:** Monitor for issues

### Week 3 (Oct 30+, 2025)
- **Mon:** Staff training sessions (role by role)
- **Tue-Wed:** Supervised first logins for all users
- **Thu-Fri:** Support and troubleshooting
- **Ongoing:** Monitor audit logs, collect feedback

---

## Success Metrics

### Technical Metrics
- [ ] 100% of users can login with 2FA
- [ ] Zero unauthorized access incidents
- [ ] All user actions logged (100% coverage)
- [ ] Session timeout working correctly
- [ ] Account lockout prevents brute force attacks

### Business Metrics
- [ ] Madame (Admin) can create/manage all user accounts
- [ ] Each role can access only their features
- [ ] Accountant successfully completes alpha testing
- [ ] All staff trained and able to login independently
- [ ] No security incidents in first month

### User Experience Metrics
- [ ] Login time < 30 seconds (including 2FA)
- [ ] First-time setup time < 5 minutes
- [ ] Zero user lockouts due to confusion (vs. security)
- [ ] Positive feedback from UAT participants

---

## Risk Management

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| ~~Users lose 2FA device~~ | ~~HIGH~~ | ~~MEDIUM~~ | ✅ Not applicable - using email OTP only |
| Users lose email access | HIGH | LOW | Admin can update email address after identity verification |
| Forgotten passwords | MEDIUM | HIGH | Self-service password reset with 6-digit email code |
| Email delivery delays | MEDIUM | MEDIUM | Use reliable Gmail SMTP; OTP valid for 10 minutes |
| Staff resist email 2FA | LOW | LOW | Simpler than app-based; clear training on security benefits |
| Bugs in production | HIGH | MEDIUM | Thorough testing + staged rollout (accountant first) |
| Registration spam/abuse | MEDIUM | LOW | Admin approval required; email verification; rate limiting |
| 24hr re-auth frustration | MEDIUM | MEDIUM | Clear messaging; emphasize security (90K KES loss prevention) |
| Session timeouts during work | MEDIUM | HIGH | 1-hour timeout with activity tracking; 5-min warning |

---

## ✅ CEO Approved Requirements (Oct 15, 2025)

### 1. **2FA Method: EMAIL ONLY**
- **Decision:** Email-based OTP codes
- **Rationale:** Simpler for non-technical users, no app download required, free
- **Implementation:** 6-digit code sent via Gmail SMTP
- **Code Validity:** 10 minutes

### 2. **Re-authentication Policy: EVERY 24 HOURS**
- **Decision:** Users must re-enter password every 24 hours
- **Implementation:** After 24 hours, user must login again with password + email OTP
- **No "Remember Me" option** - Security priority

### 3. **Session Timeout: 1 HOUR INACTIVITY**
- **Decision:** Auto-logout after 1 hour of inactivity
- **Implementation:** Activity tracking on every request
- **Warning:** 5-minute warning before logout (optional UX enhancement)

### 4. **Trusted Devices: NONE**
- **Decision:** NO trusted device functionality
- **Rationale:** Maximum security - always require full authentication
- **Impact:** Every login requires password + email OTP (no exceptions)

### 5. **User Onboarding: DUAL APPROACH + AUTO-SUPERADMIN**

**Auto-Superadmin Setup:**
- Environment variable: `SUPERADMIN_EMAILS="madame@chesanto.com,joe@coophive.network"`
- When user registers/is invited with email in this list → Auto-approved as ADMIN role
- No manual approval needed for superadmins
- Works with both flows below

**Option A - Admin Invite (Preferred for existing staff):**
1. Admin creates account → System sends invite → User sets password → Login

**Option B - Self-Registration with Approval (For new hires):**
1. User registers → If email in SUPERADMIN_EMAILS → Auto-approve as ADMIN
2. Otherwise → Admin reviews → Approve/Reject → User notified → Sets password

### 6. **Password Reset Flow: SECURE 6-DIGIT CODE**
**Approved Flow:**
```
1. User clicks "Forgot Password"
2. User enters email address
3. System verifies account exists
4. System generates 6-digit reset code
5. System sends code via email (valid 15 minutes)
6. User enters code on verification page
7. System validates code
8. User enters new password (twice for confirmation)
9. System saves new password
10. System redirects to login page
11. User logs in with new password + email OTP
12. System sends email notification of password change
13. END
```

**Security Features:**
- Code expires after 15 minutes
- Maximum 3 attempts per code
- Rate limiting: 3 reset requests per hour per email
- Email notification of ALL password changes (alerts user of unauthorized resets)

### 7. **Audit Logging: COMPREHENSIVE - ALL USERS**
- **Decision:** Track EVERYTHING for EVERY user
- **Access:** Admin can view all logs; Users can view their own activity
- **Priority:** Security and accuracy first
- **Retention:** Minimum 1 year (financial compliance)

**Logged Actions:**
- Login attempts (success/failure)
- Logout events
- Password changes
- All data entry (create/update/delete)
- Report generation
- Data exports
- Permission changes
- Account modifications
- Failed authorization attempts

---

## Next Steps

### Immediate Actions (Today - Oct 15)
1. **REVIEW this plan** with CEO (Madame)
2. **GET ANSWERS** to open questions above
3. **APPROVE** technology choices and timeline
4. **CONFIRM** user roles and permissions matrix

### After Approval
5. Create detailed technical specification document
6. Set up development branch for authentication feature
7. Begin Phase 1 implementation
8. Daily progress updates to CEO

---

## Documentation Deliverables

Once implementation begins, create:
- [ ] API documentation (authentication endpoints)
- [ ] User manual (how to login, setup 2FA, reset password)
- [ ] Admin guide (user management, audit logs)
- [ ] Training slides for each role
- [ ] Troubleshooting guide (common issues)

---

## Notes from CEO Meeting (Oct 12, 2025)

> "Authentication is priority number one this week. We need to know who's doing what in the system. The 90,000 KES loss happened because we couldn't track who dispatched what. That stops now."

**Key Takeaways:**
- Security is driven by real financial losses
- User accountability is critical (especially dispatch)
- Timeline is urgent but quality can't be compromised
- CEO (Madame) wants to test everything before staff access
- Accountant will be alpha tester (trustworthy, tech-capable)

---

**Document Status:** ✅ APPROVED BY CEO - Ready for Implementation  
**Created:** October 15, 2025  
**Approved:** October 15, 2025  
**Author:** Development Team  
**Next Review:** After Phase 1 completion
