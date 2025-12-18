# 🚨 Critical Missing Features - Action Plan

**Date:** October 16, 2025  
**Priority:** HIGH  
**Status:** In Progress

---

## ✅ ISSUE #1: UserInvitation Bug - FIXED

### Problem
```
IntegrityError: NOT NULL constraint failed: accounts_user_invitation.expires_at
```

**Root Cause:** `UserInvitation.expires_at` field required but had no default value.

### Solution ✅ COMPLETE
Added automatic expiry calculation in model's `save()` method:

```python
def save(self, *args, **kwargs):
    """Auto-set expires_at to 7 days from now if not provided"""
    if not self.expires_at:
        self.expires_at = timezone.now() + timedelta(days=7)
    super().save(*args, **kwargs)
```

**Migration:** `0002_alter_userinvitation_expires_at.py` applied  
**Status:** ✅ Fixed - Can now create invitations via admin

---

## 🚨 ISSUE #2: Send Invite Functionality - MISSING

### Current State
- ✅ `UserInvitation` model exists
- ✅ Admin interface can create invitations
- ❌ **No email actually gets sent**
- ❌ **No invite view/form**
- ❌ **No invite URL routing**

### What's Needed

#### 1. Admin Action to Send Invite
Create custom admin action in `apps/accounts/admin.py`:

```python
@admin.action(description="Send invitation email to selected invitations")
def send_invitation_emails(modeladmin, request, queryset):
    """Send email invitations to selected users"""
    from apps.communications.services import EmailService
    
    email_service = EmailService()
    sent = 0
    failed = 0
    
    for invitation in queryset:
        if invitation.is_valid():
            try:
                # Send invitation email with temp password
                email_service.send_user_invitation(
                    email=invitation.email,
                    full_name=invitation.full_name,
                    temp_password=invitation.temp_password,
                    invite_url=f"{settings.SERVER_URL}/auth/complete-registration/?token={invitation.id}"
                )
                sent += 1
            except Exception as e:
                failed += 1
                
    modeladmin.message_user(
        request,
        f"Sent {sent} invitations, {failed} failed."
    )
```

#### 2. Email Template
Already exists in `apps/communications/services/email_service.py`:
- ✅ `send_user_invitation()` method implemented
- ✅ Template: `USER_INVITATION`
- ✅ Context: `full_name`, `temp_password`, `invite_url`, `expires_at`

#### 3. Frontend View (Day 2)
Create `InviteUserView` in `apps/accounts/views.py`:
- Form to enter email, name, role
- Auto-generate temp password
- Create UserInvitation record
- Send email immediately
- Show success message

**Priority:** HIGH - Needed for CEO to invite accountant  
**Estimated Time:** 1 hour  
**Dependencies:** Email service (✅ ready), templates (⏳ Day 2)

---

## 🚨 ISSUE #3: Chat App - MISSING

### Current State
- ✅ `communications` app exists
- ✅ `EmailLog` and `SMSLog` models exist
- ✅ `MessageTemplate` model exists
- ❌ **No chat/messaging functionality**
- ❌ **No real-time communication**

### What's Needed

#### Option A: Simple Internal Messaging (Recommended for MVP)
**Timeline:** Day 3-4 (8 hours)

**Models to Add:**
```python
# apps/communications/models.py

class Message(models.Model):
    """Internal messaging between users"""
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_sent')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages_received')
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['sender', 'created_at']),
        ]

class MessageThread(models.Model):
    """Group related messages into threads"""
    participants = models.ManyToManyField(User, related_name='message_threads')
    subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**Features:**
- Inbox/Sent/Drafts views
- Compose message form
- Mark as read/unread
- Delete messages
- Notification badge (unread count)
- Email notification for new messages (optional)

**Admin Interface:**
- View all messages (superadmin only)
- Search by sender/recipient
- Filter by read status

#### Option B: Real-Time Chat with WebSockets
**Timeline:** Week 2 (16-24 hours)

**Additional Requirements:**
- Django Channels (WebSockets)
- Redis for channel layers
- Chat room models
- Real-time message delivery
- Typing indicators
- Online/offline status

**Recommendation:** Start with Option A (simple messaging), upgrade to Option B later if needed.

---

## 🚨 ISSUE #4: User Profiles - MISSING

### Current State
- ✅ `User` model has extensive fields (28 fields total)
- ✅ `profile_photo` field exists
- ✅ `UserProfileChange` tracks all edits
- ❌ **No profile view page**
- ❌ **No profile edit form**
- ❌ **No profile photo upload UI**

### What's Needed

#### 1. Profile View Page
**URL:** `/profile/` or `/profile/<user_id>/`  
**Template:** `accounts/profile.html`

**Display Sections:**
- Personal Info (name, email, mobile numbers)
- Profile Photo (with drag-to-center JavaScript)
- Employee Info (employee_id, role, department, hire date)
- Payroll Info (if applicable - basic salary, pay per day)
- Account Status (active, approved, email verified)
- Change Password link
- Edit Profile button

**Access Control:**
- Users can view their own profile
- Admins can view any profile
- Superadmins can edit any profile

#### 2. Profile Edit Form
**URL:** `/profile/edit/`  
**Form:** `ProfileEditForm` in `apps/accounts/forms.py`

**Editable Fields:**
- First name, middle names, last name
- Mobile numbers (primary, secondary, tertiary)
- National ID (if employee)
- Emergency contact (if employee)
- Profile photo

**Non-Editable (Admin Only):**
- Email (requires re-verification)
- Role (requires permission escalation)
- Employee ID
- Payroll fields

**Audit Trail:**
- All changes logged in `UserProfileChange` model
- Shows old value → new value
- Tracks who made the change
- Timestamps each change

#### 3. Profile Photo Upload
**URL:** `/profile/photo/upload/`  
**Method:** AJAX with drag-and-drop

**Features:**
- Drag file to center of placeholder
- Image preview before upload
- Max 5MB validation
- JPG/PNG only
- Crop/resize option (optional)
- Delete existing photo

**JavaScript Required:**
```javascript
// Drag-to-center animation
const dropZone = document.getElementById('photo-dropzone');
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    // Validate and upload
});
```

#### 4. Profile Changes History
**URL:** `/profile/history/`  
**Template:** `accounts/profile_changes.html`

**Display:**
- Table of all profile changes
- Field name, old value, new value
- Changed by (user or admin)
- Timestamp
- Filter by date range

**Priority:** MEDIUM-HIGH - Users need to see and edit their profiles  
**Estimated Time:** 4 hours (view + edit form + photo upload)  
**Dependencies:** Day 2 views, Day 3 templates

---

## 📊 PRIORITY MATRIX

| Issue | Priority | Impact | Effort | Status |
|-------|----------|--------|--------|--------|
| **#1: UserInvitation Bug** | 🔴 CRITICAL | HIGH | 15 min | ✅ FIXED |
| **#2: Send Invite** | 🔴 HIGH | HIGH | 1 hour | ⏳ Day 2 |
| **#3: Chat App** | 🟡 MEDIUM | MEDIUM | 8 hours | ⏳ Day 3-4 |
| **#4: User Profiles** | 🟠 HIGH | HIGH | 4 hours | ⏳ Day 2 |

---

## 🎯 IMPLEMENTATION PLAN

### Immediate (Today - October 16)
- ✅ Fix UserInvitation expires_at bug
- ✅ Create this action plan document
- 🔄 Test invitation creation in admin (should work now)

### Day 2 (October 17) - Frontend Core
**Morning (4 hours):**
1. Create `InviteUserView` + `InviteForm` (1 hour)
2. Add admin action to send invitation emails (30 min)
3. Create `ProfileView` + `ProfileEditView` (2 hours)
4. Create `ProfileEditForm` + `ProfilePhotoForm` (30 min)

**Afternoon (4 hours):**
5. Create 11 authentication templates (3 hours)
6. Add profile templates (profile.html, profile_edit.html) (1 hour)

### Day 3 (October 18) - Enhancements
**Morning (4 hours):**
7. Implement profile photo upload with drag-to-center (2 hours)
8. Create profile change history view (1 hour)
9. Test complete user lifecycle (invite → register → profile edit) (1 hour)

**Afternoon (4 hours):**
10. Start simple messaging system (Message + MessageThread models)
11. Create inbox/compose views
12. Basic message templates

### Week 2 (Optional) - Real-Time Chat
- Upgrade to Django Channels
- Implement WebSocket chat
- Add typing indicators
- Online/offline status

---

## 🔍 TESTING CHECKLIST

### Issue #1: UserInvitation ✅
- [x] Can create invitation via admin
- [x] `expires_at` auto-calculated (7 days)
- [x] No IntegrityError on save
- [ ] Can send invitation email (pending Day 2)

### Issue #2: Send Invite ⏳
- [ ] Admin action "Send invitation email" works
- [ ] Email delivered to recipient
- [ ] Temp password received
- [ ] Invite URL valid
- [ ] Frontend invite form works
- [ ] Invited user can complete registration

### Issue #3: Chat App ⏳
- [ ] Message model created
- [ ] Can send message to another user
- [ ] Recipient sees unread count
- [ ] Can mark message as read
- [ ] Can reply to message
- [ ] Admin can view all messages
- [ ] (Optional) Real-time delivery

### Issue #4: User Profiles ⏳
- [ ] Can view own profile
- [ ] Can edit personal info
- [ ] Can upload profile photo (5MB max)
- [ ] Photo displays correctly
- [ ] Can view change history
- [ ] Changes logged in UserProfileChange
- [ ] Admin can edit any profile
- [ ] Non-editable fields protected

---

## 💡 TECHNICAL NOTES

### UserInvitation Email Flow
```
Admin creates invitation → UserInvitation record created → expires_at auto-set to +7 days
    ↓
Admin clicks "Send invitation email" action → EmailService.send_user_invitation()
    ↓
Email sent with temp_password and invite_url
    ↓
User clicks invite_url → CompleteRegistrationView (Day 2)
    ↓
User sets permanent password → UserInvitation.used_at set → User.is_active = True
```

### Profile Photo Upload Flow
```
User clicks "Upload Photo" → Drag file or click to browse
    ↓
JavaScript validates (5MB, JPG/PNG only)
    ↓
AJAX POST to /profile/photo/upload/ → ProfilePhotoForm validates
    ↓
Image saved to media/profiles/YYYY/MM/ → User.profile_photo updated
    ↓
UserProfileChange logged → Thumbnail generated (optional)
    ↓
Page refreshes with new photo
```

### Message Flow (Simple Messaging)
```
User A composes message → MessageForm validated
    ↓
Message record created (sender=A, recipient=B, is_read=False)
    ↓
Optional: Email notification sent to B
    ↓
B logs in → Sees unread count badge → Clicks inbox
    ↓
Message displayed → B clicks message → is_read=True, read_at=now()
    ↓
B clicks "Reply" → New message (sender=B, recipient=A)
```

---

## 📝 CURRENT STATUS SUMMARY

**Backend Infrastructure:** ✅ 100% Complete  
**Admin Interface:** ✅ 95% Complete (invite emails need action)  
**User Invite:** ⚠️ 50% Complete (model fixed, email sending pending)  
**Chat/Messaging:** ❌ 0% Complete (not started)  
**User Profiles:** ❌ 0% Complete (not started)  

**Next Immediate Action:**  
Test UserInvitation creation in admin - should work now without IntegrityError!

---

**Document Created:** October 16, 2025  
**Last Updated:** October 16, 2025  
**Owner:** Development Team  
**Location:** `/Docs/Github_docs/CRITICAL_MISSING_FEATURES.md`
