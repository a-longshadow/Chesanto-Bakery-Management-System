# Enhancement Summary - User Profiles & In-App Chat
**Date:** October 16, 2025  
**Status:** ✅ SPECIFICATIONS COMPLETE  
**Implementation:** Phase 1 (with Authentication System)

---

## Summary of Changes

### 1. ✅ Enhanced User Profiles with Payroll Integration

**Name Fields:**
- `first_name` (required) - Max 100 chars
- `middle_names` (optional) - Max 200 chars, space-separated for multiple
- `last_name` (required) - Max 100 chars

**Contact Information:**
- `mobile_primary` (required) - Primary contact
- `mobile_secondary` (optional) - Secondary contact
- `mobile_tertiary` (optional) - Tertiary contact
- Method: `get_all_mobile_numbers()` returns list of all numbers

**Email Verification:**
- `email_verified` (boolean)
- `email_verified_at` (timestamp)
- New model: `EmailVerificationToken` with token expiry

**Profile Photo:**
- Max size: 5MB
- Formats: JPG, PNG only
- Storage: `profiles/%Y/%m/` organized by year/month
- Display: Circular with drag-to-center positioning
- Fields:
  - `profile_photo` (ImageField)
  - `photo_uploaded_at` (timestamp)
  - `photo_uploaded_by` (ForeignKey to User)
  - `photo_center_x` (Decimal 0-100%)
  - `photo_center_y` (Decimal 0-100%)
- Default avatar: `/static/images/default-avatar.png`

**Employee/Payroll Fields:**
- `employee_id` (unique) - e.g., CHE001, CHE028
- `national_id` (unique) - For official records
- `position` - Job title
- `department` - Production, Sales, Dispatch, etc.
- `basic_salary` - Monthly basic salary (KES) - **TRACKED, not paid from app**
- `pay_per_day` - Auto-calculated: basic_salary / 30 - **for expense tracking**
- `overtime_rate` - Per mix for production staff - **for cost tracking**
- `commission_rate` - Default 7% above target - **for commission tracking**
- `sales_target` - Default 35,000 KES/month
- `date_hired` - Employment start date
- `date_terminated` - Employment end date (if applicable)
- `employment_status` - ACTIVE, INACTIVE, TERMINATED
- `current_loan_balance` - **Tracked like petty cash expenses** (links to Finance Module)
- `current_advance_balance` - **Tracked like petty cash expenses** (links to Finance Module)

**Important Clarification:**
- **We track payroll numbers, NOT process payroll payments**
- Just like daily petty cash expenses tracked by accountant
- Payroll data used for monthly income calculations → affects profit/loss statements
- Actual payment processing happens outside the app
- These fields exist for **expense tracking and financial reporting**, not payment execution

**Audit Fields:**
- `created_by` - User who created account
- `updated_by` - User who last updated profile
- `updated_at` - Last update timestamp

---

### 2. ✅ Profile Change Tracking

**New Model: `UserProfileChange`**
- Tracks ALL changes to user profiles
- Fields monitored:
  - Name fields (first, middle, last)
  - Contact info (email, mobiles)
  - Employee info (ID, position, department)
  - Payroll data (salary, rates, targets)
  - Employment status
  - Role changes
  - Loan/advance balances

**Tracking Details:**
- `user` - Profile being changed
- `changed_by` - User making the change
- `field_name` - Which field changed
- `old_value` - Previous value
- `new_value` - New value
- `change_reason` - Optional explanation
- `changed_at` - Timestamp
- `ip_address` - IP of change request

**Implementation:**
- Django signals (`pre_save`) automatically track changes
- Middleware stores current request in thread-local for context
- Admin/users can provide reason for changes (logged separately)

---

### 3. ✅ Forms Enhancements

**New Forms:**

1. **ProfilePhotoForm**
   - File upload with validation (5MB max, JPG/PNG only)
   - Hidden fields for center positioning (X, Y)
   - JavaScript-powered drag-to-center interface

2. **UserProfileForm**
   - All profile fields editable
   - Optional `change_reason` textarea (logged in audit)
   - Permission-based field restrictions:
     - Regular users: Can edit name, contact info
     - Admin/Superadmin: Can edit payroll fields
   - Auto-calculates `pay_per_day` on save
   - Sets `updated_by` automatically

---

### 4. ✅ User Model Methods

**New Methods:**
```python
get_full_name()           # First + Middle + Last
get_display_name()        # First + Last only
get_all_mobile_numbers()  # List of all mobile numbers
calculate_pay_per_day()   # Auto-calc from basic_salary
get_profile_photo_url()   # Photo URL or default avatar
clean()                   # Validation before save
```

---

### 5. ✅ In-App Chat Planning (SIMPLIFIED - Django Only)

- **Complete architecture** documented in USER_PROFILES_AND_CHAT.md
- **Technology**: Django ORM + AJAX polling (NO Redis, NO WebSockets)
- **Integration**: Part of Communications app
- **Simplified Features**:
  - Direct user-to-user text messaging only
  - Message history (view past conversations)
  - Reply to specific messages (threading)
  - Simple read receipts (read_at timestamp)
  - AJAX polling for updates (every 3-5 seconds)
- **NOT Included** (keeping it simple):
  - ❌ Group chats (not needed initially)
  - ❌ File attachments (not needed initially)
  - ❌ WebSockets/Redis (too complex)
  - ❌ Voice/video calls (not needed)
  - ❌ Typing indicators (not needed)
- **Database models** simplified: ChatConversation (user-to-user), ChatMessage (text + reply)
- **Cost savings**: Reduces SMS costs for internal communication
- **Audit trail**: All conversations logged for accountability

---

## Files Modified

### Documentation Created/Updated:
1. ✅ **USER_PROFILES_AND_CHAT.md** (NEW)
   - Complete specifications for user profiles
   - Payroll integration details
   - In-app chat architecture and roadmap

2. ✅ **AUTHENTICATION_SYSTEM.md** (UPDATED)
   - Added cross-reference to user profiles
   - Updated module dependencies

3. ✅ **COMMUNICATION.md** (UPDATED)
   - Added in-app chat to message types
   - Cross-reference to USER_PROFILES_AND_CHAT.md

4. ✅ **project_structure.md** (UPDATED)
   - Updated accounts app structure (new templates, tests)
   - Updated communications app (chat services, consumers)
   - Added USER_PROFILES_AND_CHAT.md to docs folder

---

## Implementation Checklist

### Phase 1: User Profiles (Oct 15-18, 2025)
- [ ] Update User model with all new fields
- [ ] Create UserProfileChange model
- [ ] Create EmailVerificationToken model
- [ ] Implement profile change tracking signals
- [ ] Create ProfilePhotoForm
- [ ] Create UserProfileForm
- [ ] Create profile view templates:
  - [ ] profile_view.html
  - [ ] profile_edit.html
  - [ ] profile_photo_upload.html
  - [ ] profile_changes_log.html
- [ ] Add profile photo upload JavaScript (drag-to-center)
- [ ] Create profile management views
- [ ] Add profile routes to accounts/urls.py
- [ ] Create migration for new fields
- [ ] Update admin interface for new fields
- [ ] Write unit tests for profile changes
- [ ] Test photo upload with size validation
- [ ] Test multi-mobile number functionality

### Phase 2: Email Verification (Oct 19-Nov 1, 2025)
- [ ] Create email verification token generation
- [ ] Send verification email on registration
- [ ] Create email verification view
- [ ] Update login to check email_verified
- [ ] Add re-send verification email option

### Phase 3: In-App Chat (Post-Reports Module)
- [ ] Install Django packages (no Redis needed)
- [ ] Create ChatConversation, ChatMessage models
- [ ] Implement ChatService (simple CRUD operations)
- [ ] Create chat inbox view
- [ ] Create conversation view
- [ ] Add AJAX polling for new messages (3-5 second intervals)
- [ ] Implement reply-to-message feature
- [ ] Add simple read receipts
- [ ] Create chat UI templates
- [ ] Add chat routes
- [ ] Create chat tests

---

## Dependencies

### Python Packages (Add to requirements/base.txt):
```
Pillow>=10.0.0              # Image processing for profile photos
# NO Redis/Channels needed - using Django ORM polling for chat
```

### New Environment Variables:
```bash
# Profile Photo Settings
MAX_PROFILE_PHOTO_SIZE=5242880  # 5MB in bytes
ALLOWED_PHOTO_FORMATS=jpg,jpeg,png

# Email Verification
EMAIL_VERIFICATION_EXPIRY=86400  # 24 hours in seconds

# Chat Settings (Simple Django Polling)
CHAT_POLL_INTERVAL=3  # Seconds between AJAX polls for new messages
CHAT_MESSAGE_HISTORY_LIMIT=50  # Number of messages to show per page
```

### Database Migrations:
```bash
python manage.py makemigrations accounts
python manage.py migrate accounts
```

---

## Testing Strategy

### Unit Tests:
1. **Profile Changes**
   - Test signal triggers on field changes
   - Verify change history logged correctly
   - Test permission-based field restrictions

2. **Photo Upload**
   - Test 5MB size limit
   - Test file format validation
   - Test drag-to-center positioning

3. **Name Fields**
   - Test get_full_name() with/without middle names
   - Test get_display_name()

4. **Payroll Calculations**
   - Test calculate_pay_per_day()
   - Verify auto-calculation on save

5. **Mobile Numbers**
   - Test get_all_mobile_numbers()
   - Test up to 3 numbers

### Integration Tests:
1. Profile edit flow (user vs admin permissions)
2. Photo upload and display
3. Email verification flow
4. Change history viewing

---

## Security Considerations

1. **Profile Photo Upload**
   - Validate file type (magic bytes, not just extension)
   - Scan for malware (future integration)
   - Store in separate media directory
   - Serve via CDN in production (future)

2. **Profile Changes**
   - Require authentication for all changes
   - Log IP address of change requests
   - Rate limit profile updates (prevent spam)
   - Admin approval for sensitive field changes (optional)

3. **Email Verification**
   - Secure token generation (secrets module)
   - Token expiry (24 hours)
   - One-time use tokens
   - Rate limit verification requests

4. **In-App Chat (Future)**
   - Message encryption at rest (future)
   - WebSocket authentication
   - Rate limiting for messages
   - Content moderation (profanity filter)

---

## Monitoring & Maintenance

### Profile Photo Storage:
```bash
# Monthly cleanup of orphaned photos
python manage.py cleanup_orphaned_photos

# Monitor storage usage
du -sh media/profiles/
```

### Profile Change Audits:
```sql
-- Most frequently changed fields
SELECT field_name, COUNT(*) as change_count
FROM accounts_user_profile_change
WHERE changed_at >= NOW() - INTERVAL '30 days'
GROUP BY field_name
ORDER BY change_count DESC;

-- Users with most profile changes
SELECT u.first_name, u.last_name, COUNT(*) as change_count
FROM accounts_user_profile_change pc
JOIN accounts_user u ON pc.user_id = u.id
WHERE pc.changed_at >= NOW() - INTERVAL '30 days'
GROUP BY u.id, u.first_name, u.last_name
ORDER BY change_count DESC;
```

---

**Document Version:** 1.0  
**Last Updated:** October 16, 2025  
**Next Review:** When implementing user profiles (Phase 1)
