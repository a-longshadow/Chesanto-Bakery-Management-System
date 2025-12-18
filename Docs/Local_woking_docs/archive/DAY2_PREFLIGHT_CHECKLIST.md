# 🎨 Day 2 Frontend - Pre-Flight Checklist

**Date:** October 16, 2025  
**Phase:** Pre-Development Review  
**Status:** Validating Requirements Before Starting

---

## ✅ DESIGN SYSTEM VALIDATION

### Color Palette ✅ CONFIRMED
**Primary Colors (Blue, White, Black - NO PURPLE):**
- ✅ Blue: `#2563eb` (Primary actions, links, focus states)
- ✅ White: `#ffffff` (Backgrounds, cards)
- ✅ Black: `#000000` (Headers, strong emphasis)
- ✅ Grays: 50-900 scale for neutral UI elements

**Status Colors:**
- ✅ Success: `#059669` (Green - approvals, success messages)
- ✅ Warning: `#d97706` (Amber - warnings, pending states)
- ✅ Error: `#dc2626` (Red - errors, validation failures)
- ✅ Info: `#0891b2` (Cyan - informational messages)

**❌ EXPLICITLY FORBIDDEN:**
- ❌ NO Purple (#7c3aed, #8b5cf6, etc.)
- ❌ NO Purple gradients
- ❌ NO Flashy/neon colors

**Design Philosophy:**
- ✅ Apple-inspired aesthetic
- ✅ Professional & minimal
- ✅ Clean lines and whitespace
- ✅ Sophisticated gray palette

---

## 📋 FRONTEND REQUIREMENTS CHECKLIST

### 1. Authentication Views (8 Required) ⏳

**Flow Reference:** AUTHENTICATION_SYSTEM.md

| # | View | Purpose | Required Fields | Status |
|---|------|---------|----------------|--------|
| 1 | **LoginView** | Email + password login, 24hr re-auth check | email, password | ⏳ Todo |
| 2 | **RegisterView** | Self-registration with approval | email, password, first_name, last_name, mobile_primary, role | ⏳ Todo |
| 3 | **InviteUserView** | Admin sends invitation | email, full_name, role | ⏳ Todo |
| 4 | **OTPVerifyView** | 6-digit code validation (max 3 attempts) | code (6 digits) | ⏳ Todo |
| 5 | **PasswordChangeView** | Force change on first login | old_password, new_password, confirm_password | ⏳ Todo |
| 6 | **PasswordResetRequestView** | Request reset code | email | ⏳ Todo |
| 7 | **PasswordResetVerifyView** | Enter code + new password | code, new_password, confirm_password | ⏳ Todo |
| 8 | **ProfileEditView** | Edit user profile | See UserProfileForm | ⏳ Todo |

---

### 2. Authentication Forms (7 Required) ⏳

**Validation Requirements:**
- ✅ Email format validation
- ✅ Password strength (min 8 chars)
- ✅ Phone format (+254XXXXXXXXX or 07XXXXXXXX)
- ✅ OTP exactly 6 digits
- ✅ Password confirmation matching

| # | Form | Fields | Validation Rules | Status |
|---|------|--------|-----------------|--------|
| 1 | **LoginForm** | email, password | Email format, not empty | ⏳ Todo |
| 2 | **RegisterForm** | email, password, confirm_password, first_name, last_name, mobile_primary, role | Email unique, password min 8 chars, phone format, role in choices | ⏳ Todo |
| 3 | **InviteForm** | email, full_name, role | Email format, role in choices | ⏳ Todo |
| 4 | **OTPForm** | code | Exactly 6 digits, numeric only | ⏳ Todo |
| 5 | **PasswordChangeForm** | old_password, new_password, confirm_password | Old password correct, new min 8 chars, passwords match | ⏳ Todo |
| 6 | **PasswordResetRequestForm** | email | Email exists in system | ⏳ Todo |
| 7 | **PasswordResetVerifyForm** | code, new_password, confirm_password | Code valid, password min 8 chars, passwords match | ⏳ Todo |

---

### 3. HTML Templates (11 Required) ⏳

**Design Requirements:**
- ✅ Based on `template_schema.md`
- ✅ Apple-inspired minimal design
- ✅ Blue/White/Black color scheme (NO PURPLE)
- ✅ Inter font (Google Fonts)
- ✅ Responsive (mobile-first)
- ✅ Accessibility (WCAG 2.1 AA)

| # | Template | Purpose | Design Notes | Status |
|---|----------|---------|--------------|--------|
| 1 | **base.html** | Master layout | Navigation, footer, blocks for content | ⏳ Todo |
| 2 | **login.html** | Login form | Centered card, minimal, "Forgot password?" link | ⏳ Todo |
| 3 | **register.html** | Registration form | Multi-step or single form, show approval message | ⏳ Todo |
| 4 | **invite_user.html** | Admin invite form | Admin-only, show temp password after save | ⏳ Todo |
| 5 | **otp_verify.html** | OTP input | 6 boxes for digits, countdown timer (10 min), resend button | ⏳ Todo |
| 6 | **password_change.html** | Change password | Show password strength indicator, requirements checklist | ⏳ Todo |
| 7 | **password_reset_request.html** | Request reset | Simple email input, show "Check your email" message | ⏳ Todo |
| 8 | **password_reset_verify.html** | Enter code + new password | Code input + password fields | ⏳ Todo |
| 9 | **profile.html** | View profile | Display all user info, "Edit" button, profile photo | ⏳ Todo |
| 10 | **profile_edit.html** | Edit profile | Form with editable fields, save button | ⏳ Todo |
| 11 | **profile_changes.html** | Change history | Table of changes with old/new values | ⏳ Todo |

---

### 4. URL Routing (11 Routes) ⏳

**Convention:** `/auth/` prefix for authentication, `/profile/` for profiles

| # | URL Pattern | View | Name | Status |
|---|-------------|------|------|--------|
| 1 | `/auth/login/` | LoginView | `login` | ⏳ Todo |
| 2 | `/auth/logout/` | LogoutView | `logout` | ⏳ Todo |
| 3 | `/auth/register/` | RegisterView | `register` | ⏳ Todo |
| 4 | `/auth/invite/` | InviteUserView | `invite_user` | ⏳ Todo |
| 5 | `/auth/otp-verify/` | OTPVerifyView | `otp_verify` | ⏳ Todo |
| 6 | `/auth/password/change/` | PasswordChangeView | `password_change` | ⏳ Todo |
| 7 | `/auth/password/reset/` | PasswordResetRequestView | `password_reset_request` | ⏳ Todo |
| 8 | `/auth/password/reset/verify/` | PasswordResetVerifyView | `password_reset_verify` | ⏳ Todo |
| 9 | `/profile/` | ProfileView | `profile` | ⏳ Todo |
| 10 | `/profile/edit/` | ProfileEditView | `profile_edit` | ⏳ Todo |
| 11 | `/profile/history/` | ProfileChangesView | `profile_changes` | ⏳ Todo |

---

### 5. Middleware Activation (3 Classes) ⏳

**Currently Disabled - Enable After Views Created:**

| Middleware | Purpose | Enable After | Status |
|------------|---------|--------------|--------|
| `RouteProtectionMiddleware` | Redirect unauthenticated users to login | 'login' URL exists | ⏳ Todo |
| `SessionSecurityMiddleware` | 1-hour timeout, smart logout | All views created | ⏳ Todo |
| `ReAuthenticationMiddleware` | 24-hour re-auth prompt | Re-auth flow implemented | ⏳ Todo |

---

## 🎨 DESIGN SYSTEM REFERENCE

### Typography Stack
```css
/* Primary Font */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;

/* Sizes (Mobile-first) */
--text-xs: 0.75rem;    /* 12px - labels */
--text-sm: 0.875rem;   /* 14px - body, buttons */
--text-base: 1rem;     /* 16px - default */
--text-lg: 1.125rem;   /* 18px - emphasis */
--text-xl: 1.25rem;    /* 20px - small headings */
--text-2xl: 1.5rem;    /* 24px - section headings */
--text-3xl: 1.875rem;  /* 30px - page headings */
```

### Spacing Scale
```css
--space-1: 0.25rem;   /* 4px  - tight */
--space-2: 0.5rem;    /* 8px  - small */
--space-3: 0.75rem;   /* 12px - default */
--space-4: 1rem;      /* 16px - standard */
--space-6: 1.5rem;    /* 24px - sections */
--space-8: 2rem;      /* 32px - large */
--space-12: 3rem;     /* 48px - breaks */
```

### Component Classes
```css
.btn                 /* Base button */
.btn--primary       /* Blue button (#2563eb) */
.btn--secondary     /* Gray button */
.btn--ghost         /* Minimal button */

.card               /* Container with shadow */
.card__header       /* Header section */
.card__content      /* Main content */
.card__footer       /* Footer section */

.form-group         /* Field wrapper */
.form-label         /* Field label */
.form-control       /* Input field */
.form-error         /* Error message (red) */
.form-help          /* Help text (gray) */

.alert              /* Notification box */
.alert--success     /* Green alert */
.alert--error       /* Red alert */
.alert--warning     /* Amber alert */
.alert--info        /* Cyan alert */
```

### Color Classes
```css
/* Text Colors */
.text-primary       /* Blue #2563eb */
.text-success       /* Green #059669 */
.text-warning       /* Amber #d97706 */
.text-error         /* Red #dc2626 */
.text-muted         /* Gray #6b7280 */

/* Background Colors */
.bg-primary         /* Blue background */
.bg-gray-50         /* Very light gray */
.bg-white           /* White */
```

---

## 📚 REFERENCE DOCUMENTS

### Must Read Before Coding
1. ✅ **AUTHENTICATION_SYSTEM.md** - Complete auth flows
2. ✅ **USER_PROFILES_AND_CHAT.md** - Profile specs
3. ✅ **template_schema.md** - Design system
4. ✅ **COMMUNICATION.md** - Email integration

### Key Points from Specs

**From AUTHENTICATION_SYSTEM.md:**
- ✅ Force password change on first login (temp password)
- ✅ 24-hour re-auth prompt (NOT force logout)
- ✅ 1-hour session timeout with smart detection (no logout during active work)
- ✅ OTP: 6 digits, max 3 attempts, 10 min expiry
- ✅ Password reset: 6 digits, 15 min expiry
- ✅ SUPERADMIN_EMAILS auto-approved (skip approval)
- ✅ Sunday exception: No data entry reminders (company closed)

**From USER_PROFILES_AND_CHAT.md:**
- ✅ Up to 3 mobile numbers (primary required, secondary/tertiary optional)
- ✅ Profile photo max 5MB (JPG, PNG)
- ✅ Drag-to-center photo positioning (photo_center_x, photo_center_y)
- ✅ Profile change tracking (26 fields monitored)
- ✅ Payroll fields OPTIONAL for superadmins (important correction)

**From template_schema.md:**
- ✅ Apple-inspired minimal design
- ✅ NO PURPLE - Blue/White/Black only
- ✅ Inter font from Google Fonts
- ✅ Mobile-first responsive
- ✅ WCAG 2.1 AA accessibility

---

## 🔍 VALIDATION QUESTIONS

### Before Starting Development

**1. Design Confirmation ✅**
- [x] Color scheme confirmed: Blue (#2563eb), White (#ffffff), Black (#000000)
- [x] No purple anywhere in design
- [x] Apple-inspired minimal aesthetic
- [x] Inter font loaded from Google Fonts

**2. Form Requirements ✅**
- [x] All 7 forms identified with field lists
- [x] Validation rules documented for each form
- [x] Error message patterns defined
- [x] Success message patterns defined

**3. View Requirements ✅**
- [x] All 8 views mapped to user flows
- [x] Authentication logic understood
- [x] OTP flow clear (3 attempts max)
- [x] Re-auth flow clear (24hr check)

**4. Template Requirements ✅**
- [x] All 11 templates listed
- [x] Base template structure understood
- [x] Component reusability planned
- [x] Responsive breakpoints defined

**5. Integration Points ✅**
- [x] EmailService methods known (send_otp, send_invitation, etc.)
- [x] AuditLogger integration points identified
- [x] Middleware integration understood
- [x] Session management clear

---

## 📊 ESTIMATED TIME BREAKDOWN

### Day 2 Schedule (10 hours total)

**Morning Session (4 hours):**
- Views: 8 views × 20 min = 2.5 hours
- Forms: 7 forms × 15 min = 1.5 hours
- **Break:** 15 min

**Afternoon Session (4 hours):**
- Base template: 30 min
- Auth templates: 8 templates × 20 min = 2.5 hours
- Profile templates: 3 templates × 15 min = 45 min
- **Break:** 15 min

**Evening Session (2 hours):**
- URL routing: 30 min
- Enable middleware: 15 min
- Testing: 45 min
- Bug fixes: 30 min

---

## ✅ PRE-FLIGHT CHECKLIST

**Design System:**
- [x] Color palette validated (Blue/White/Black, NO PURPLE)
- [x] Typography system reviewed
- [x] Spacing scale understood
- [x] Component classes documented

**Requirements:**
- [x] 8 views identified and documented
- [x] 7 forms identified and documented
- [x] 11 templates identified and documented
- [x] 11 URL routes mapped
- [x] 3 middleware classes ready to enable

**Reference Docs:**
- [x] AUTHENTICATION_SYSTEM.md reviewed
- [x] USER_PROFILES_AND_CHAT.md reviewed
- [x] template_schema.md reviewed
- [x] COMMUNICATION.md reviewed

**Backend Ready:**
- [x] All models in database
- [x] EmailService working (tested)
- [x] AuditLogger active
- [x] Middleware configured
- [x] Admin interface operational

---

## 🚀 READY TO START?

**Status:** ✅ ALL CHECKS PASSED

**Confirmed:**
- ✅ Design system (Blue/White/Black - NO PURPLE)
- ✅ Forms requirements clear
- ✅ View requirements documented
- ✅ Templates planned
- ✅ Backend operational

**Next Command:**
```bash
# Create views.py
touch apps/accounts/views.py
```

**First File to Create:**
`apps/accounts/views.py` with 8 authentication views

---

**Document Created:** October 16, 2025 - 1:00 PM  
**Purpose:** Pre-flight validation before Day 2 frontend development  
**Status:** ✅ Ready to proceed with frontend implementation  
**Location:** `/Docs/Github_docs/DAY2_PREFLIGHT_CHECKLIST.md`
