# 4. TEMPLATES & DESIGN SYSTEM

**Document Status**: Complete  
**Last Updated**: October 16, 2025  
**Token Budget**: ~6,000 tokens (4 pages)

---

## PART 1: DESIGN PHILOSOPHY

### Overview
Apple-inspired design system emphasizing **clarity, simplicity, and consistency**. Blue/white/black color scheme (no purple). Mobile-first responsive approach.

### Design Principles
1. **Content First** - Remove visual clutter, let content breathe
2. **Hierarchy** - Clear typographic scale (12px → 36px)
3. **Consistency** - Reusable components, predictable patterns
4. **Accessibility** - WCAG 2.1 AA compliant (contrast ratios, keyboard nav)
5. **Performance** - Inline critical CSS, defer non-critical assets

### Color System
```css
Primary: #2563eb (Blue) - CTAs, links, focus states
Success: #059669 (Green) - Confirmations, success messages
Warning: #d97706 (Orange) - Warnings, pending states
Error: #dc2626 (Red) - Errors, destructive actions
Grays: #f9fafb → #111827 (9 shades) - Text, backgrounds, borders
```

### Typography
- **Font**: Inter (Google Fonts) - Modern, highly legible
- **Weights**: 300 (light), 400 (regular), 500 (medium), 600 (semibold), 700 (bold)
- **Scale**: 0.75rem, 0.875rem, 1rem, 1.125rem, 1.25rem, 1.5rem, 1.875rem, 2.25rem
- **Line Height**: 1.5 (body), 1.25 (headings)

### Spacing System
```css
--spacing-1: 0.25rem (4px)   → Tight spacing (icon gaps)
--spacing-2: 0.5rem (8px)    → Small spacing (form labels)
--spacing-3: 0.75rem (12px)  → Input padding
--spacing-4: 1rem (16px)     → Default spacing
--spacing-6: 1.5rem (24px)   → Section spacing
--spacing-8: 2rem (32px)     → Large spacing
--spacing-12: 3rem (48px)    → Page sections
```

---

## PART 2: TEMPLATE HIERARCHY

### Base Template Structure
**File**: `apps/accounts/templates/accounts/base.html` (366 lines)

```
<!DOCTYPE html>
├── <head>
│   ├── Meta tags (charset, viewport, X-UA-Compatible)
│   ├── Google Fonts (Inter)
│   ├── Inline CSS (design tokens + components)
│   └── {% block extra_css %}
├── <body>
│   ├── Navigation Bar (.nav)
│   ├── Main Content (.container)
│   │   ├── Messages (Django messages framework)
│   │   └── {% block content %}
│   ├── Footer (.footer)
│   └── {% block extra_js %}
```

### Template Inheritance Pattern
All page templates extend `base.html`:
```django
{% extends "accounts/base.html" %}
{% block title %}Page Title{% endblock %}
{% block container_class %}container--narrow{% endblock %}  {# Optional #}
{% block content %}
  <!-- Page-specific content -->
{% endblock %}
```

### Existing Page Templates (11 templates)
1. **login.html** - Email/password form, forgot password link
2. **register.html** - Full registration form (name, email, mobile, password)
3. **otp_verify.html** - 6-digit OTP input
4. **password_reset_request.html** - Email input for reset
5. **password_reset_verify.html** - OTP + new password form
6. **password_change.html** - Current + new password form
7. **profile.html** - User info display with edit button
8. **profile_edit.html** - Editable profile form
9. **profile_changes.html** - Profile change history table
10. **invite_user.html** - Staff-only invitation form
11. **base.html** - Master template (nav, footer, messages)

---

## PART 3: COMPONENT LIBRARY

### Navigation Bar
**Location**: `base.html` lines 320-343  
**Behavior**: Context-aware (authenticated vs guest)

```html
<nav class="nav">
  <div class="nav__container">
    <a href="/" class="nav__brand">Chesanto Bakery</a>
    <ul class="nav__menu">
      <!-- Authenticated: Profile, Invite (staff), Admin (staff), Logout -->
      <!-- Guest: Login, Register -->
    </ul>
  </div>
</nav>
```

**Styles**:
- White background, 1px gray border-bottom
- Brand: 1.25rem, semibold (600)
- Links: 0.875rem, gray-600, hover to primary blue
- Flexbox layout, responsive (max-width 1200px)

### Cards
**Usage**: All form pages use card components  
**Structure**: `.card` > `.card__header` + `.card__content` + `.card__footer`

```html
<div class="card">
  <div class="card__header">
    <h1 class="card__title">Title</h1>
  </div>
  <div class="card__content">
    <!-- Form or content -->
  </div>
  <div class="card__footer">
    <!-- Secondary actions/links -->
  </div>
</div>
```

**Styles**:
- White background, 0.5rem border-radius
- Box shadow: `0 1px 3px rgba(0,0,0,0.1)`
- Header/footer: Gray-50 background, 1px border

### Buttons
**Classes**: `.btn` + modifier (`.btn--primary`, `.btn--secondary`, `.btn--ghost`, `.btn--block`)

```html
<button class="btn btn--primary">Primary Action</button>
<button class="btn btn--secondary">Secondary</button>
<a href="#" class="btn btn--ghost">Ghost Link</a>
<button class="btn btn--primary btn--block">Full Width</button>
```

**Styles**:
- Primary: Blue background, white text, hover darkens
- Secondary: Gray-200 background, dark text
- Ghost: Transparent, blue text, hover light blue background
- Block: `width: 100%`
- Padding: 0.75rem × 1.5rem, 0.375rem border-radius

### Form Controls
**Structure**: `.form-group` > `.form-label` + `.form-control` + `.form-help`/`.form-error`

```html
<div class="form-group">
  <label for="email" class="form-label">Email Address</label>
  <input type="email" id="email" class="form-control" required>
  <span class="form-help">We'll never share your email</span>
  <span class="form-error">{{ error_message }}</span>
</div>
```

**Styles**:
- Label: 0.875rem, medium (500), gray-700
- Input: 1rem padding, 1px gray-300 border, 0.375rem radius
- Focus: Blue border, 3px light blue shadow (`box-shadow: 0 0 0 3px #dbeafe`)
- Help: 0.875rem, gray-500
- Error: 0.875rem, red

### Alerts/Messages
**Django Integration**: Automatically styled via messages framework  
**Classes**: `.alert` + `.alert--success`/`.alert--error`/`.alert--warning`/`.alert--info`

```django
{% if messages %}
  {% for message in messages %}
    <div class="alert alert--{{ message.tags }}">
      {{ message }}
    </div>
  {% endfor %}
{% endif %}
```

**Styles**:
- Success: Green background (#d1fae5), dark green text, green border
- Error: Red background (#fee2e2), dark red text, red border
- Warning: Orange background (#fed7aa), dark orange text
- Info: Cyan background (#cffafe), dark cyan text
- Padding: 1rem, 0.375rem radius, margin-bottom: 1.5rem

### Footer
**Location**: `base.html` lines 364-369  
**Content**: Copyright notice, centered

```html
<footer class="footer">
  <div class="footer__container">
    <p>&copy; 2025 Chesanto Bakery Management System. All rights reserved.</p>
  </div>
</footer>
```

**Styles**:
- White background, 1px gray border-top
- Padding: 2rem vertical
- Margin-top: 3rem (pushes to bottom)
- Centered text, 0.875rem, gray-500

---

## PART 4: PATTERNS & BEST PRACTICES

### Form Validation Patterns
**Client-Side**: HTML5 attributes (`required`, `type="email"`, `minlength`, `pattern`)  
**Server-Side**: Django forms with `clean_*()` methods  
**Display**: Errors shown via `.form-error` spans or alert messages

**Example** (login.html):
```html
<input type="email" name="email" required autofocus
       placeholder="your.email@example.com">
<!-- Required attribute prevents submission if empty -->
<!-- type="email" validates email format -->
<!-- autofocus puts cursor in field on page load -->
```

### Responsive Design
**Approach**: Mobile-first, single-column by default  
**Breakpoints**: None defined (future: 640px, 768px, 1024px)  
**Current State**: Desktop-optimized (max-width 1200px containers)

**Profile Grid Example**:
```html
<div style="display: grid; grid-template-columns: 1fr 2fr; gap: 2rem;">
  <!-- Left: Profile photo (1 column) -->
  <!-- Right: User details (2 columns) -->
</div>
```

### Accessibility Features
1. **Semantic HTML**: `<nav>`, `<main>`, `<footer>`, `<form>`
2. **Labels**: All inputs have associated `<label for="id">`
3. **Focus States**: Blue outline + shadow on interactive elements
4. **Color Contrast**: WCAG AA compliant (4.5:1 minimum)
5. **Keyboard Navigation**: Tab through forms, Enter to submit

**Missing** (Future Work):
- ARIA labels for screen readers
- Skip-to-content link
- Focus trap for modals
- Reduced motion support (`prefers-reduced-motion`)

### File Organization
```
apps/accounts/templates/accounts/
├── base.html               # Master template (nav, footer, design system)
├── login.html              # Authentication pages
├── register.html
├── otp_verify.html
├── password_reset_*.html   # Password flows (3 templates)
├── password_change.html
├── profile*.html           # Profile pages (3 templates)
└── invite_user.html        # Admin invitation

static/css/
├── base.css                # Design tokens, global styles (447 lines)
├── components.css          # Reusable UI components
└── main.css                # Page-specific overrides

apps/communications/templates/
└── emails/
    ├── base.html           # Email master template
    ├── auth/*.html         # 5 transactional emails
    └── components/*.html   # Header, footer partials
```

### Email Templates
**Base**: `communications/emails/base.html` - Inline styles for email clients  
**Auth Emails**: OTP, password reset, invitation, password changed, account approved  
**Pattern**: Consistent branding, single CTA per email, plain-text fallback

### Known Issues & Future Work

**CRITICAL** (Documented, Not Fixed per User Directive):
1. **Password Reset Broken**: Line 512 `NameError: ActivityLogger not defined` (bytecode caching issue)
2. **Invite Feature Broken**: Line 263 uses `is_accepted=False` but model has `used_at` field
3. **Browser Caching**: Users may see old forms (need hard refresh: Cmd+Shift+R)

**Design Improvements Needed**:
1. **Responsive Breakpoints**: Add mobile/tablet styles (currently desktop-only)
2. **Dark Mode**: Implement `prefers-color-scheme: dark` support
3. **Loading States**: Spinner/skeleton screens for async actions
4. **Modals/Dialogs**: Confirmation dialogs for destructive actions
5. **Toast Notifications**: Non-intrusive success/error messages (replace alerts)
6. **Empty States**: Illustrations for "no data" scenarios
7. **Pagination**: Component for long lists/tables
8. **Breadcrumbs**: Navigation trail for deep pages
9. **Tabs**: Component for multi-section pages
10. **Dropdowns**: Custom select styling, menus

**External CSS Files** (`static/css/`):
- Currently exist but NOT linked in base.html
- All styles inline in `<style>` tag for performance
- Future: Extract to external files for caching, add `{% load static %}`

### Design System Extensions
**Static Assets** (`static/`):
```
static/
├── css/
│   ├── base.css          # Design tokens (447 lines) - NOT LINKED
│   ├── components.css    # UI components - NOT LINKED
│   └── main.css          # Overrides - NOT LINKED
├── js/
│   ├── base.js           # Global JavaScript
│   └── main.js           # Page-specific JS
└── images/
    └── favicon.svg       # Site icon
```

**Current**: All CSS inline in base.html `<style>` tag (lines 16-313)  
**Reason**: Performance (eliminate render-blocking requests), simplicity  
**Trade-off**: No browser caching, larger HTML files

### Browser Compatibility
**Tested**: Chrome, Safari, Firefox (latest versions)  
**CSS Features**: Flexbox, Grid, Custom Properties (CSS Variables)  
**Fallbacks**: None (assumes modern browsers, 2020+)  
**IE11**: Not supported (uses `:focus`, `rem` units, custom properties)

---

## SUMMARY

**Total Documentation**: 4 master docs, ~46,500 tokens (4.6% of 1M budget)

1. **1_ACCOUNTS_APP.md** (~12,000 tokens) - Complete accounts app with failures documented
2. **2_IMPLEMENTATION_STATUS.md** (~9,000 tokens) - Project progress, blockers, timeline
3. **3_PROJECT_STRUCTURE.md** (~10,500 tokens) - Directory tree, data flows, ERD
4. **4_TEMPLATES_DESIGN.md** (~6,000 tokens) - Design system, components, patterns

**Design System Maturity**: 70% complete
- ✅ Color system, typography, spacing tokens defined
- ✅ Navigation, cards, forms, buttons, alerts implemented
- ✅ 11 page templates, consistent patterns
- ❌ No responsive breakpoints, dark mode, advanced components
- 🔴 Critical: Password reset broken, invite broken (see 1_ACCOUNTS_APP.md)

**Next Steps**:
1. Fix password reset bytecode caching mystery
2. Fix invite view field error (`is_accepted` → `used_at`)
3. Add responsive breakpoints for mobile/tablet
4. Extract inline CSS to external files (static/css/)
5. Implement missing components (modals, toasts, pagination)

---

**END OF DOCUMENTATION CONSOLIDATION**  
All failures registered. No corrections applied per user directive.
