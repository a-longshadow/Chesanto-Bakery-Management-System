# 📧 How to Send User Invitations

**Date:** October 16, 2025  
**Feature:** Admin action to send invitation emails  
**Status:** ✅ FIXED & TESTED

---

## ✅ Complete Workflow (Per AUTHENTICATION_SYSTEM.md)

### Step 1: Create the Invitation
1. Go to **Django Admin** → **Accounts** → **User invitations**
2. Click **"Add User invitation"**
3. Fill in:
   - **Email**: accountant@example.com
   - **Full name**: Jane Doe  
   - **Role**: ADMIN (for Accountant)
   - **Invited by**: (auto-filled with your name)
4. Click **"Save"**
5. ✅ System automatically generates:
   - **Temporary password** (12 chars, e.g., `Kx9mP2vL4Rt!`) 
   - **Expires at** (7 days from now)

### Step 2: Send the Email
1. Go back to **User invitations list** (click "User invitations" in breadcrumb)
2. ☑️ **Check the box** next to the invitation you just created
3. Find the **"Actions"** dropdown at the top of the list
4. Select: **"✉️ Send invitation email to selected invitations"**
5. Click **"Go"**
6. See success message: "✅ Successfully sent 1 invitation(s)"

### Step 3: Check the Email Output
Since you're using **console email backend** for testing:
- Look at your **terminal where `runserver` is running**
- You'll see the complete email printed there!

**Example Terminal Output:**
```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: Welcome to Chesanto Bakery
From: Chesanto Bakery <joe@coophive.network>
To: accountant@example.com
Date: Wed, 16 Oct 2025 12:40:00 -0000

Dear Jane Doe,

You've been invited to join Chesanto Bakery Management System!

Role: ADMIN (Accountant)
Temporary Password: Kx9mP2vL4Rt!

Login at: http://localhost:8000/auth/login/

⚠️  You'll be required to change this password on first login for security.

Best regards,
The Chesanto Team
```

---

## 🔧 What Was Fixed

### Issue #1: Temp Password Not Generated ✅
**Problem**: Admin had to manually enter temp password  
**Solution**: Model now auto-generates on save using `generate_temp_password(12)`

### Issue #2: Gmail Authentication Error ✅
**Problem**: Settings tried to send via Gmail despite console backend in `.env`  
**Solution**: Settings now respect `EMAIL_BACKEND` from `.env` file

### Issue #3: Missing SERVER_URL ✅
**Problem**: `settings.SERVER_URL` not defined  
**Solution**: Added `SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:8000')`

---

## 🔄 For Production (Real Gmail)

When deploying to Railway, update `.env`:

```properties
# Switch to SMTP backend for real emails
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# Gmail credentials (already configured)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=joe@coophive.network
EMAIL_HOST_PASSWORD=opno whxi ztta soyt
```

Then emails will actually be sent via Gmail! 📨

---

## ✅ Testing Checklist

- [x] Create invitation via admin
- [x] Temp password auto-generated (12 chars)
- [x] Expires at auto-set (+7 days)
- [x] Select invitation and use action
- [x] Email printed to console (development)
- [ ] Email sent via Gmail (production - needs valid app password)
- [ ] Invited user receives email
- [ ] User can login with temp password
- [ ] Forced to change password on first login

---

## 🧪 Try It Now!

**Go to your browser:**
1. http://localhost:8000/admin/accounts/userinvitation/add/
2. Enter email + name + role
3. Click "Save and add another" OR "Save"
4. Go to list view
5. Select checkbox
6. Actions → "✉️ Send invitation email"
7. Click "Go"
8. Check terminal for email output!

**Expected Result:**
- Success message in admin
- Email content in terminal
- Temp password visible in admin (after save)

---

**Document Updated:** October 16, 2025  
**Status:** ✅ Ready to Test  
**Location:** `/Docs/Github_docs/HOW_TO_SEND_INVITATIONS.md`

