# Django Project Structure - Chesanto Bakery Management System

**Date:** October 16, 2025  
**Status:** ✅ APPROVED STRUCTURE  
**Philosophy:** Modular, scalable, easy to add/remove features

---

# Project Organization

```
chesanto-bakery/
├── manage.py
├── README.md
├── LICENSE
├── .env.example
├── .gitignore
├── Procfile                    # Railway deployment
├── railway.json               # Railway configuration
├── db.sqlite3                 # Development database
│
├── requirements/              # Dependency management
│   ├── base.txt              # Core dependencies (shared)
│   ├── local.txt             # Development tools
│   ├── production.txt        # Production requirements
│   └── test.txt              # Testing dependencies
│
├── config/                    # Django project configuration
│   ├── __init__.py
│   ├── urls.py               # Root URL configuration
│   ├── wsgi.py               # WSGI entry point
│   ├── asgi.py               # ASGI entry point (future WebSockets)
│   └── settings/
│       ├── __init__.py
│       ├── base.py           # Base settings (shared)
│       ├── local.py          # Development settings
│       ├── test.py           # Test settings
│       └── prod.py           # Production settings
│
├── apps/                      # All business modules
│   │
│   ├── core/                 # ✅ CORE - Shared utilities
│   │   ├── __init__.py
│   │   ├── models.py         # Base models (TimestampedModel, etc)
│   │   ├── mixins.py         # Reusable model mixins
│   │   ├── managers.py       # Custom model managers
│   │   ├── validators.py     # Custom validators
│   │   ├── utils.py          # Helper functions
│   │   ├── middleware.py     # Custom middleware
│   │   ├── decorators.py     # Custom decorators
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       └── test_utils.py
│   │
│   ├── accounts/             # ✅ PRIORITY 1 - Authentication & Users
│   │   ├── __init__.py
│   │   ├── models.py         # User (enhanced with payroll fields), UserInvitation, EmailOTP
│   │   │                     # UserProfileChange (audit trail), EmailVerificationToken
│   │   ├── views.py          # Login, Register, Invite, OTP, Profile Edit
│   │   ├── forms.py          # Auth forms, ProfilePhotoForm, UserProfileForm
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── middleware.py     # Activity tracking, session management, request context
│   │   ├── decorators.py     # @role_required, @auth_required
│   │   ├── utils.py          # OTP generation, password utils, email verification
│   │   ├── signals.py        # User creation signals, profile change tracking
│   │   ├── managers.py       # Custom user manager
│   │   ├── templates/
│   │   │   └── accounts/
│   │   │       ├── login.html
│   │   │       ├── register.html
│   │   │       ├── invite.html
│   │   │       ├── otp_verify.html
│   │   │       ├── password_change.html
│   │   │       ├── password_reset_request.html
│   │   │       ├── password_reset_verify.html
│   │   │       ├── profile_view.html          # NEW: View user profile
│   │   │       ├── profile_edit.html          # NEW: Edit profile
│   │   │       ├── profile_photo_upload.html  # NEW: Photo upload with drag-to-center
│   │   │       └── profile_changes_log.html   # NEW: Audit trail of changes
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       ├── test_views.py
│   │       ├── test_auth.py
│   │       ├── test_profile_changes.py  # NEW: Test profile change tracking
│   │       └── factories.py
│   │
│   ├── communications/       # ✅ PRIORITY 1 - Email/SMS System
│   │   ├── __init__.py
│   │   ├── models.py         # EmailLog, SMSLog, MessageTemplate
│   │   │                     # ChatMessage, ChatConversation (future)
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── urls.py           # Future: Webhook endpoints, chat routes
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # BaseMessageService
│   │   │   ├── email.py      # EmailService (Gmail SMTP)
│   │   │   ├── sms.py        # SMSService (future)
│   │   │   └── chat.py       # ChatService (future - Phase 3)
│   │   ├── consumers.py      # Future: WebSocket consumers for chat
│   │   ├── routing.py        # Future: WebSocket routing
│   │   ├── templates/
│   │   │   ├── emails/
│   │   │   │   ├── base.html
│   │   │   │   ├── components/
│   │   │   │   │   ├── header.html
│   │   │   │   │   ├── footer.html
│   │   │   │   │   └── button.html
│   │   │   │   ├── auth/     # Authentication emails
│   │   │   │   │   ├── invitation.html
│   │   │   │   │   ├── otp.html
│   │   │   │   │   ├── password_reset.html
│   │   │   │   │   ├── password_changed.html
│   │   │   │   │   ├── account_approved.html
│   │   │   │   │   └── daily_reminder.html
│   │   │   │   ├── sales/    # Sales emails (future)
│   │   │   │   ├── production/  # Production emails (future)
│   │   │   │   ├── inventory/   # Inventory emails (future)
│   │   │   │   └── reports/     # Report emails (future)
│   │   │   └── chat/         # Future: Chat UI templates
│   │   │       ├── inbox.html
│   │   │       └── conversation.html
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_email_service.py
│   │       ├── test_models.py
│   │       └── test_chat.py  # Future: Chat tests
│   │
│   ├── audit/                # ✅ PRIORITY 1 - Audit Trail
│   │   ├── __init__.py
│   │   ├── models.py         # AuditLog, AuditLogArchive
│   │   ├── views.py          # Audit log viewer
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── middleware.py     # Navigation tracking
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── logger.py     # Audit logging service
│   │   │   └── archiver.py   # Log archival service
│   │   ├── templates/
│   │   │   └── audit/
│   │   │       ├── log_list.html
│   │   │       └── log_detail.html
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_logging.py
│   │
│   ├── products/             # 🔴 TIER 1 - Product Catalog & Recipes
│   │   ├── __init__.py
│   │   ├── models.py         # Product, Recipe, RecipeIngredient, PackagingSpec
│   │   │                     # SharedInventoryItem (crates, diesel, etc.)
│   │   ├── views.py          # Product list, detail, recipe editor
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py          # ProductForm, RecipeForm
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── recipe.py     # Recipe calculator (ingredients → yield)
│   │   │   └── costing.py    # Product cost calculator
│   │   ├── templates/
│   │   │   └── products/
│   │   │       ├── product_list.html
│   │   │       ├── product_detail.html
│   │   │       ├── recipe_editor.html
│   │   │       └── cost_breakdown.html
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_models.py
│   │       ├── test_recipes.py
│   │       └── test_costing.py
│   │
│   ├── production/           # � TIER 1 - Production Management
│   │   ├── __init__.py
│   │   ├── models.py         # ProductionBatch, DailyProduction, MaterialConsumption
│   │   │                     # ProductionVariance, StaffPerformance
│   │   ├── views.py          # Daily entry, variance alerts, performance tracking
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py          # DailyProductionForm (per product)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── variance.py   # Variance detection (99-105 KDF, fixed scones/bread)
│   │   │   └── material.py   # Material consumption calculator
│   │   ├── templates/
│   │   │   └── production/
│   │   │       ├── daily_entry.html
│   │   │       ├── batch_detail.html
│   │   │       ├── variance_alerts.html
│   │   │       └── staff_performance.html
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_production.py
│   │       └── test_variance.py
│   │
│   ├── sales/                # � TIER 1 - Sales & Orders
│   │   ├── __init__.py
│   │   ├── models.py         # Sale, SaleItem, Customer, Payment, Commission
│   │   │                     # Return, SalesTarget, ZeroSaleEntry
│   │   ├── views.py          # Daily sales entry, commission tracking, zero entries
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py          # DailySalesForm, PaymentForm, ZeroEntryForm
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── commission.py  # Commission calculation (5 KES/bread discount)
│   │   │   └── reconciliation.py  # Sales/returns/deposits reconciliation
│   │   ├── templates/
│   │   │   └── sales/
│   │   │       ├── daily_entry.html
│   │   │       ├── commission_report.html
│   │   │       ├── customer_list.html
│   │   │       └── reconciliation.html
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_sales.py
│   │       └── test_commission.py
│   │
│   ├── inventory/            # � TIER 1 - Inventory & Assets
│   │   ├── __init__.py
│   │   ├── models.py         # Crate, CrateMovement, RawMaterial, Stock
│   │   │                     # StockMovement, Reorder, FinishedGoods, Packaging
│   │   ├── views.py          # Crate tracking, stock levels, reorder alerts
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py          # CrateDispatchForm, StockReceiptForm, ReorderForm
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── crates.py      # Crate management (300 units, track missing)
│   │   │   ├── reorder.py     # Auto-reorder alerts for raw materials
│   │   │   └── stock.py       # Stock level tracking
│   │   ├── templates/
│   │   │   └── inventory/
│   │   │       ├── crate_tracker.html
│   │   │       ├── crate_alerts.html  # Missing crates alert
│   │   │       ├── stock_levels.html
│   │   │       ├── raw_materials.html
│   │   │       └── reorder_list.html
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_crates.py
│   │       └── test_stock.py
│   │
│   ├── finance/              # � TIER 1 - Financial Management
│   │   ├── __init__.py
│   │   ├── models.py         # PettyCash, Expense, ProductCost, ProfitMargin
│   │   │                     # PriceUpdate, Transaction, BankDeposit, MobileMoneyPayment
│   │   ├── views.py          # Petty cash entry, profit reports, cost tracking
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py          # PettyCashForm, ExpenseForm, PriceUpdateForm
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── petty_cash.py  # Weekly 5,000 KES tracking
│   │   │   ├── costing.py     # Production cost calculator
│   │   │   └── profit.py      # Daily/weekly profit margin calculator
│   │   ├── templates/
│   │   │   └── finance/
│   │   │       ├── petty_cash.html
│   │   │       ├── expense_entry.html
│   │   │       ├── profit_report.html
│   │   │       ├── cost_breakdown.html
│   │   │       └── price_updates.html
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_petty_cash.py
│   │       └── test_profit.py
│   │
│   ├── dispatch/             # � TIER 2 - Dispatch & Delivery
│   │   ├── __init__.py
│   │   ├── models.py         # Delivery, Vehicle, Route, DispatchLog
│   │   │                     # CrateDispatch (links to inventory.Crate)
│   │   ├── views.py          # Dispatch entry, delivery tracking, route management
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py          # DispatchForm, DeliveryForm
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── accountability.py  # Link dispatch to specific personnel
│   │   ├── templates/
│   │   │   └── dispatch/
│   │   │       ├── dispatch_entry.html
│   │   │       ├── delivery_tracker.html
│   │   │       └── route_management.html
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_dispatch.py
│   │
│   ├── reports/              # � TIER 2 - Reporting System
│   │   ├── __init__.py
│   │   ├── models.py         # ReportSchedule, ReportExport, ReportTemplate
│   │   │                     # DailyReport, WeeklyReport, MonthlyReport
│   │   ├── views.py          # Report viewer, generator, scheduler
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── generators/
│   │   │   │   ├── pdf.py
│   │   │   │   ├── excel.py
│   │   │   │   ├── daily.py      # Daily profit margin per product
│   │   │   │   ├── weekly.py     # Weekly summaries
│   │   │   │   └── monthly.py    # Monthly financial reports
│   │   │   └── schedulers/
│   │   │       └── auto_report.py  # Automatic report generation
│   │   ├── templates/
│   │   │   └── reports/
│   │   │       ├── report_viewer.html
│   │   │       ├── daily_profit.html
│   │   │       ├── weekly_summary.html
│   │   │       └── monthly_financial.html
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_generators.py
│   │
│   └── api/                  # 📋 FUTURE - REST API
│       ├── __init__.py
│       ├── urls.py
│       ├── v1/
│       │   ├── __init__.py
│       │   ├── serializers.py
│       │   ├── views.py
│       │   └── urls.py
│       └── tests/
│           └── __init__.py
│
├── templates/                # Global templates
│   ├── base.html            # Base template (all pages extend this)
│   ├── layouts/
│   │   ├── dashboard.html   # Dashboard layout
│   │   └── public.html      # Public pages layout
│   ├── components/          # Reusable UI components
│   │   ├── navbar.html
│   │   ├── sidebar.html
│   │   ├── breadcrumbs.html
│   │   ├── pagination.html
│   │   ├── table.html
│   │   ├── form_field.html
│   │   └── alerts.html
│   ├── errors/              # Error pages
│   │   ├── 400.html
│   │   ├── 403.html
│   │   ├── 404.html
│   │   └── 500.html
│   └── pages/               # Static pages
│       ├── home.html
│       ├── about.html
│       └── contact.html
│
├── static/                   # Static files
│   ├── css/
│   │   ├── base.css         # Base styles
│   │   ├── components.css   # Component styles
│   │   ├── main.css         # Main application styles
│   │   └── vendor/          # Third-party CSS
│   ├── js/
│   │   ├── base.js          # Base JavaScript
│   │   ├── main.js          # Main application JS
│   │   └── vendor/          # Third-party JS
│   ├── images/
│   │   ├── logo.svg
│   │   ├── favicon.ico
│   │   └── branding/
│   └── fonts/
│
├── media/                    # User-uploaded files (production)
│   ├── uploads/
│   ├── exports/
│   └── temp/
│
├── tests/                    # Integration & E2E tests
│   ├── __init__.py
│   ├── conftest.py          # pytest configuration
│   ├── factories.py         # Test data factories
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_auth_flow.py
│   │   └── test_user_management.py
│   └── e2e/                 # End-to-end tests (future)
│       └── __init__.py
│
├── scripts/                  # Utility scripts
│   ├── backup_database.py
│   ├── restore_database.py
│   ├── seed_data.py         # Seed development data
│   ├── cleanup_logs.py
│   └── setup_env.py
│
├── docs/                     # Project documentation
│   ├── README.md
│   ├── AUTHENTICATION_SYSTEM.md
│   ├── COMMUNICATION.md
│   ├── USER_PROFILES_AND_CHAT.md  # NEW: User profiles + payroll + chat
│   ├── DEPLOYMENT.md
│   ├── LOCAL_SETUP.md
│   ├── api/                 # API documentation (future)
│   │   └── openapi.yaml
│   └── guides/              # User guides
│       └── admin_guide.md
│
└── logs/                     # Application logs (gitignored)
    ├── django.log
    ├── error.log
    └── access.log
```

---

# Module Status & Priority

## ✅ PRIORITY 1 - Immediate Implementation (Oct 15-18, 2025)
**Focus:** Security & Foundation  
**Deadline:** Oct 18, 2025 (2 days remaining)

1. **accounts** - Authentication, users, roles, permissions, payroll tracking
2. **communications** - Email/SMS for all modules, in-app chat (simplified)
3. **audit** - Audit trail, navigation tracking, archival

## � TIER 1 - URGENT (Oct 19 - Nov 15, 2025)
**Focus:** Core Business Operations (Prevents 110K KES losses)  
**CEO MVP Definition:** "Digitize current Excel processes with core daily production, sales, and inventory tracking"

4. **products** 🔴 CRITICAL - **NEW!**
   - **Pain Point**: No centralized product definitions causing inconsistency
   - **Business Need**: 
     - 3 main products: KDF (variable yield 97-115 packets), Scones (fixed), Bread (fixed)
     - Each has specific ingredient recipes (26 kg flour, 3.8 kg sugar per scone mix)
     - Shared inventory (crates, diesel, packaging)
     - Support for future products
   - **Models**: Product, Recipe, RecipeIngredient, PackagingSpec
   - **Business Impact**: Standardized production, accurate costing, recipe management
   - **Dependencies**: None (foundation for production app)
   - **Timeline**: Week 2 (Oct 19-25)

5. **production** 🔴 CRITICAL
   - **Pain Point**: "20k deficit in Lorina's stock undetected for a month"
   - **Business Need**:
     - Daily mixes tracking (opening stock, production, returns, closing stock)
     - Real-time variance detection (e.g., KDF: 97-115 packets acceptable)
     - Raw material consumption per mix
     - Production staff performance tracking
   - **Models**: ProductionBatch, DailyProduction, MaterialConsumption, ProductionVariance
   - **Business Impact**: Loss prevention, cost control, waste reduction
   - **Dependencies**: Requires accounts + **products** (recipe data)
   - **Timeline**: Week 2-3 (Oct 19 - Nov 1)

6. **inventory** 🔴 CRITICAL
   - **Pain Point**: "Missing 8 crates from initial 300 - significant cost impact"
   - **Business Need**:
     - Crate tracking (dispatch, returns, missing units)
     - Raw materials (flour, sugar, yeast, etc.)
     - Packaging materials (packets for 4 or 12 units)
     - Shared items (diesel fuel)
     - Finished goods (KDF, Scones, Bread)
   - **Sub-modules**: Crates (URGENT), RawMaterials, FinishedGoods, Packaging
   - **Models**: Crate, CrateMovement, RawMaterial, Stock, StockMovement, Reorder
   - **Business Impact**: Asset protection, theft prevention, stock visibility
   - **Dependencies**: Requires accounts + **products** + production
   - **Timeline**: Week 4 (Nov 2-8)

7. **sales** 🔴 CRITICAL
   - **Pain Point**: "90,000 KES worth of goods disappeared due to poor dispatch tracking"
   - **Business Need**:
     - Daily sales entry (cash and credit arrangements with schools)
     - Zero-entry tracking (if no sales occurred)
     - Commission calculations (5 shillings per bread discount)
     - Payment tracking (bank deposits, mobile money + transaction codes)
     - Link sales/returns/deposits to specific salesmen
   - **Models**: Sale, SaleItem, Customer, Payment, Commission, Return
   - **Business Impact**: Revenue tracking, loss prevention, accountability
   - **Dependencies**: Requires accounts + **products** + inventory
   - **Timeline**: Week 4-5 (Nov 2-15)

8. **finance** 🔴 CRITICAL
   - **Pain Point**: "Petty cash operations - 5,000 KES weekly needs tracking"
   - **Business Need**:
     - Petty cash tracking (5,000 KES weekly)
     - Daily/weekly profit margin calculations
     - Production cost tracking per product
     - Ingredient costs (weekly price updates)
     - Link to payroll tracking (from accounts app)
   - **Models**: PettyCash, Expense, ProductCost, ProfitMargin, PriceUpdate
   - **Business Impact**: Financial visibility, cash flow control, profitability
   - **Dependencies**: Requires accounts + **products** + production + inventory + sales
   - **Timeline**: Week 6-7 (Nov 16-29)

## � TIER 2 - IMPORTANT (Nov 16 - Dec 15, 2025)
**Focus:** Financial Control & Visibility

9. **reports** 🟡 HIGH PRIORITY
   - **Pain Point**: "Monthly-only tracking obscures short-term issues"
   - **Business Need**:
     - Daily profit margin reports per product
     - Weekly summaries (production, sales, inventory)
     - Monthly financial reports
     - Automatic report generation
   - **Models**: ReportSchedule, ReportExport, ReportTemplate
   - **Business Impact**: Decision-making, visibility, operational control
   - **Dependencies**: Requires ALL data-generating apps
   - **Timeline**: Week 8-9 (Nov 30 - Dec 13)

10. **dispatch** 🟡 MEDIUM PRIORITY
    - **Pain Point**: "90,000 KES goods disappeared due to poor dispatch tracking"
    - **Business Need**:
      - Link transactions to specific dispatch personnel
      - Vehicle tracking
      - Route management
      - Crate tracking during deliveries
    - **Models**: Delivery, Vehicle, Route, DispatchLog
    - **Business Impact**: Delivery tracking, driver accountability
    - **Dependencies**: Requires inventory + sales
    - **Timeline**: Week 10 (Dec 14-20)

## 🔮 TIER 3 - FUTURE (Jan 2026+)
**Focus:** Optimization & Scalability

11. **api** 🟢 LOW PRIORITY
    - **Use Case**: Mobile access, third-party integrations
    - **Business Impact**: Remote monitoring, mobile data entry
    - **Dependencies**: Requires stable core apps first
    - **Timeline**: Q1 2026

---

# Design Principles

## 1. Modular Architecture
- **Each app is independent** - Can be added/removed without breaking others
- **Clear boundaries** - Each app has its own models, views, templates
- **Loose coupling** - Apps communicate through signals and services

## 2. Shared Infrastructure
- **Core app** - Shared utilities, base models, validators
- **Communications app** - Centralized messaging for all modules
- **Audit app** - Centralized logging for all modules

## 3. Scalability
- **Easy to add new modules** - Follow same structure pattern
- **Easy to remove modules** - No hard dependencies
- **Future-proof** - Room for mobile API, webhooks, integrations

## 4. Django Best Practices
- **Settings split** - base/local/test/prod for different environments
- **Requirements split** - base/local/test/prod for dependencies
- **Template inheritance** - base.html → layouts → pages
- **Static files** - Organized by type (css/js/images)
- **Testing** - Unit tests in each app, integration tests in root

---

# Key Configuration Files

## config/settings/base.py
```python
"""
Base settings shared across all environments.
"""
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key')

# Application definition
INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'django_ratelimit',
    
    # Local apps (PRIORITY 1)
    'apps.core',
    'apps.accounts',
    'apps.communications',
    'apps.audit',
    
    # Local apps (TIER 1 - URGENT - uncomment when building)
    # 'apps.products',      # Week 2 (Oct 19-25) - Foundation for production
    # 'apps.production',    # Week 2-3 (Oct 19 - Nov 1)
    # 'apps.inventory',     # Week 4 (Nov 2-8)
    # 'apps.sales',         # Week 4-5 (Nov 2-15)
    # 'apps.finance',       # Week 6-7 (Nov 16-29)
    
    # Local apps (TIER 2 - IMPORTANT - build after core MVP)
    # 'apps.reports',       # Week 8-9 (Nov 30 - Dec 13)
    # 'apps.dispatch',      # Week 10 (Dec 14-20)
    
    # Local apps (TIER 3 - FUTURE - build when scaling)
    # 'apps.api',           # Q1 2026
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Custom middleware
    'apps.accounts.middleware.ActivityTrackingMiddleware',
    'apps.audit.middleware.NavigationTrackingMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (User uploads)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 465))
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Chesanto Bakery <noreply@chesanto.com>')

# Session Configuration
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', 3600))  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
RE_AUTH_INTERVAL = int(os.getenv('RE_AUTH_INTERVAL', 86400))  # 24 hours

# OTP Configuration
OTP_CODE_LENGTH = int(os.getenv('OTP_CODE_LENGTH', 6))
OTP_CODE_VALIDITY = int(os.getenv('OTP_CODE_VALIDITY', 600))  # 10 min
PASSWORD_RESET_CODE_VALIDITY = int(os.getenv('PASSWORD_RESET_CODE_VALIDITY', 900))  # 15 min

# Superadmin Configuration
SUPERADMIN_EMAILS = os.getenv('SUPERADMIN_EMAILS', '').split(',')

# Server URL
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:8000')

# Business Configuration
SUNDAY_AUTO_SKIP = os.getenv('SUNDAY_AUTO_SKIP', 'True') == 'True'
OPERATING_DAYS = [int(d) for d in os.getenv('OPERATING_DAYS', '1,2,3,4,5,6').split(',')]
```

## config/settings/local.py
```python
"""Development settings"""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Database - SQLite for development
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email backend - Console for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Security - Relaxed for development
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Debug toolbar (if installed)
if 'debug_toolbar' in INSTALLED_APPS:
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
```

## config/settings/prod.py
```python
"""Production settings for Railway.app"""
from .base import *
import dj_database_url

DEBUG = False

# Railway.app detection
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None

ALLOWED_HOSTS = [
    'chesanto.railway.app',
    os.getenv('RAILWAY_PUBLIC_DOMAIN', ''),
]

# Database - PostgreSQL on Railway
if IS_RAILWAY:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('PGDATABASE'),
            'USER': os.getenv('PGUSER'),
            'PASSWORD': os.getenv('PGPASSWORD'),
            'HOST': os.getenv('PGHOST'),
            'PORT': os.getenv('PGPORT', 5432),
        }
    }

# Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Static files (WhiteNoise)
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

---

# Adding a New Module

## Step-by-Step Guide

### 1. Create App Structure
```bash
python manage.py startapp <app_name> apps/<app_name>
```

### 2. Add to INSTALLED_APPS
```python
# config/settings/base.py
INSTALLED_APPS = [
    # ...
    'apps.<app_name>',
]
```

### 3. Create Models
```python
# apps/<app_name>/models.py
from django.db import models
from apps.core.models import TimestampedModel

class YourModel(TimestampedModel):
    # Your fields here
    pass
```

### 4. Create URL Configuration
```python
# apps/<app_name>/urls.py
from django.urls import path
from . import views

app_name = '<app_name>'

urlpatterns = [
    path('', views.index, name='index'),
]
```

### 5. Register in Root URLs
```python
# config/urls.py
urlpatterns = [
    # ...
    path('<app-url>/', include('apps.<app_name>.urls')),
]
```

### 6. Run Migrations
```bash
python manage.py makemigrations <app_name>
python manage.py migrate
```

---

# Removing a Module

## Step-by-Step Guide

### 1. Remove from INSTALLED_APPS
```python
# config/settings/base.py
# Comment out or remove:
# 'apps.<app_name>',
```

### 2. Remove URL Includes
```python
# config/urls.py
# Comment out or remove:
# path('<app-url>/', include('apps.<app_name>.urls')),
```

### 3. Run Migrations (if needed)
```bash
# If you want to remove database tables:
python manage.py migrate <app_name> zero
```

### 4. Delete App Directory (optional)
```bash
rm -rf apps/<app_name>
```

---

**Document Version:** 2.0  
**Last Updated:** October 16, 2025  
**Next Review:** When adding first Priority 2 module

## Domain-Specific Components

### 1. Core App Structure
```python
# core/models/base.py
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

# core/models/user.py
class User(AbstractUser, TimestampedModel):
    employee_id = models.CharField(unique=True)
    role = models.CharField(choices=ROLE_CHOICES)
```

### 2. Testing Structure
```python
# tests/conftest.py
@pytest.fixture
def test_user():
    return UserFactory()

@pytest.fixture
def test_product():
    return ProductFactory()

# apps/sales/tests/test_orders.py
class TestOrderCreation:
    def test_order_process(self, test_user, test_product):
        order = create_order(test_user, test_product)
        assert order.status == 'created'
```

### 3. Template Hierarchy
```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    {% include 'components/meta.html' %}
    {% include 'components/styles.html' %}
</head>
<body>
    {% include 'nav.html' %}
    {% block content %}{% endblock %}
    {% include 'components/scripts.html' %}
</body>
</html>
```

### 4. Backup System Integration
```python
# scripts/backup.py
class ProjectBackup:
    def __init__(self):
        self.source = settings.BASE_DIR
        self.backup_dir = settings.BACKUP_DIR
        
    def create_backup(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.backup_dir}/backup_{timestamp}"
        
        # Copy files
        shutil.copytree(self.source, backup_path)
        
        # Export database
        self.export_database(backup_path)
        
        # Verify backup
        self.verify_backup(backup_path)
        
        # Cleanup old backups
        self.cleanup_old_backups()
```

## Railway.app Integration

### 1. Database Configuration
```python
# config/settings/base.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    } if not os.getenv('RAILWAY_ENVIRONMENT') else {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('PGDATABASE'),
        'USER': os.getenv('PGUSER'),
        'PASSWORD': os.getenv('PGPASSWORD'),
        'HOST': os.getenv('PGHOST'),
        'PORT': os.getenv('PGPORT'),
    }
}
```

### 2. Deployment Configuration
```python
# railway.toml
[build]
builder = "nixpacks"
buildCommand = "python manage.py collectstatic --noinput"

[deploy]
startCommand = "gunicorn config.wsgi:application"
healthcheckPath = "/health/"
restartPolicyType = "on_failure"
```o Project Structure

## Project Organization
```
chesanto/
├── apps/                      # Domain-specific applications
│   ├── core/                 # Core functionality
│   │   ├── models/
│   │   │   ├── user.py      # Custom user model
│   │   │   └── common.py    # Base models
│   │   ├── tests/
│   │   │   ├── factories.py # Test data factories
│   │   │   ├── test_models.py
│   │   │   └── test_views.py
│   │   └── utils/           # Shared utilities
│   │
│   ├── audit/              # Audit and logging
│   │   ├── models/
│   │   │   ├── audit_log.py    # Audit trail model
│   │   │   ├── system_log.py   # System events
│   │   │   └── user_action.py  # User actions
│   │   ├── services/
│   │   │   ├── audit_service.py  # Audit logging
│   │   │   └── report_service.py # Audit reporting
│   │   └── views/
│   │       └── audit_views.py    # Audit trail views
│   │
│   ├── reports/            # Reporting system
│   │   ├── templates/
│   │   │   ├── pdf/       # PDF report templates
│   │   │   └── excel/     # Excel report templates
│   │   ├── services/
│   │   │   ├── generators/  # Report generators
│   │   │   └── schedulers/  # Report scheduling
│   │   └── views/
│   │       └── report_views.py
│   │
│   ├── notifications/     # Notification system
│   │   ├── templates/
│   │   │   ├── email/    # Email templates
│   │   │   └── sms/      # SMS templates
│   │   ├── services/
│   │   │   ├── email_service.py
│   │   │   └── sms_service.py
│   │   └── views/
│   │
│   ├── production/          # Production management
│   │   ├── models/
│   │   ├── tests/
│   │   ├── services/       # Business logic
│   │   └── views/
│   │
│   ├── sales/             # Sales operations
│   │   ├── models/
│   │   ├── tests/
│   │   ├── services/
│   │   └── views/
│   │
│   ├── inventory/        # Inventory management
│   │   ├── models/
│   │   ├── tests/
│   │   ├── services/
│   │   └── views/
│   │
│   ├── finance/         # Financial operations
│   │   ├── models/
│   │   ├── tests/
│   │   ├── services/
│   │   └── views/
│   │
│   └── api/            # API endpoints
│       ├── v1/
│       ├── tests/
│       └── docs/       # API documentation
│
├── config/            # Project configuration
│   ├── settings/
│   │   ├── base.py     # Base settings
│   │   ├── local.py    # Development settings
│   │   ├── test.py     # Test settings
│   │   └── prod.py     # Production settings
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── templates/         # HTML templates
│   ├── base/
│   │   ├── base.html          # Main template
│   │   ├── nav.html           # Navigation
│   │   └── footer.html        # Footer
│   ├── components/            # Reusable components
│   │   ├── forms/
│   │   └── widgets/
│   └── pages/                 # Page templates
│
├── static/           # Static files
│   ├── css/
│   │   ├── base.css    # Base styles
│   │   └── theme.css   # Theme variables
│   ├── js/
│   └── images/
│
├── tests/            # Integration tests
│   ├── conftest.py   # Test configuration
│   ├── factories.py  # Test data factories
│   └── integration/  # Integration test suites
│
├── scripts/          # Utility scripts
│   ├── setup_dev.sh  # Dev environment setup
│   └── setup_test.sh # Test environment setup
│
└── requirements/     # Dependencies
    ├── base.txt     # Shared requirements
    ├── local.txt    # Development
    ├── test.txt     # Testing
    └── prod.txt     # Production
```

## Key Design Decisions

### 1. Environment Configuration
```python
# config/settings/base.py
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment detection
ENVIRONMENT = os.getenv('DJANGO_ENV', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_TESTING = 'test' in sys.argv

# Railway.app specific
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None
DATABASE_URL = os.getenv('DATABASE_URL')
```

### 2. Database Configuration
```python
# config/settings/base.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    } if not IS_RAILWAY else {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('PGDATABASE'),
        'USER': os.getenv('PGUSER'),
        'PASSWORD': os.getenv('PGPASSWORD'),
        'HOST': os.getenv('PGHOST'),
        'PORT': os.getenv('PGPORT'),
    }
}
```

### 3. Railway Deployment Setup
```yaml
# railway.toml
[build]
builder = "nixpacks"
buildCommand = "python manage.py collectstatic --noinput"

[deploy]
startCommand = "gunicorn config.wsgi:application"
healthcheckPath = "/health/"
restartPolicyType = "on_failure"

[env]
DJANGO_ENV = "production"
PYTHON_VERSION = "3.11"
```

### 4. Testing Strategy

1. **Unit Tests**
   - One test file per module
   - pytest as test runner
   - Factory Boy for test data
   - Mock external services

2. **Integration Tests**
   - End-to-end workflows
   - API endpoint testing
   - Database interactions
   - External service integration

3. **Test Configuration**
   ```python
   # config/settings/test.py
   from .base import *

   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.sqlite3',
           'NAME': ':memory:'
       }
   }
   ```

### 5. Template Structure

1. **Base Templates**
   ```html
   <!-- templates/base/base.html -->
   <!DOCTYPE html>
   <html lang="en">
   <head>
       {% include 'base/meta.html' %}
       {% include 'base/styles.html' %}
   </head>
   <body>
       {% include 'base/nav.html' %}
       {% block content %}{% endblock %}
       {% include 'base/footer.html' %}
       {% include 'base/scripts.html' %}
   </body>
   </html>
   ```

2. **Theme Configuration**
   ```css
   /* static/css/theme.css */
   :root {
       --primary-color: #007bff;
       --secondary-color: #6c757d;
       --font-family: 'Roboto', sans-serif;
       --spacing-unit: 1rem;
   }
   ```

### 6. Development Workflow

1. **Local Development**
   ```bash
   python manage.py runserver --settings=config.settings.local
   ```

2. **Testing**
   ```bash
   pytest --ds=config.settings.test
   ```

3. **Railway Deployment**
   - GitHub Actions for CI/CD
   - Automatic deployments on main branch
   - Environment variable management
   - Database migrations