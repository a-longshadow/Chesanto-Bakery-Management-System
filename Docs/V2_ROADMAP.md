# V2 Roadmap - Future Improvements
**Project:** Chesanto Bakery Management System  
**Status:** 📋 Post-MVP Enhancements  
**Last Updated:** October 18, 2025

---

## V1 (MVP) - In Development

**Core Business Modules:**
- ✅ Accounts (authentication, user management) - **COMPLETE**
- 🚧 Products + Inventory - **NEXT** (Milestone 2)
- 🚧 Production + Sales - **PENDING** (Milestone 2)
- 🚧 Accounting + Reports - **PENDING** (Milestone 2)
- 🚧 Analytics + Payroll - **PENDING** (Milestone 2)

---

## V2 - Future Enhancements

### App: Accounts

#### Module: Media Storage
**Decision:** Cloudinary (FREE tier: 25GB storage/bandwidth)  
**Priority:** HIGH | **Time:** 15-20 mins

**Plan:**
- Install `django-cloudinary-storage==0.3.0` and `cloudinary==1.41.0`
- Add Cloudinary credentials to Railway environment variables
- Update `settings/prod.py` with `DEFAULT_FILE_STORAGE` configuration
- Test profile photo uploads persist after deployment

---

#### Module: Attendance Tracking
**Decision:** Clock-In/Clock-Out system  
**Priority:** MEDIUM | **Time:** 2-3 hours

**Plan:**
- Create `Attendance` model (clock_in/out times, hours_worked, date, is_late)
- Build clock-in/clock-out views with duplicate prevention
- Add employee dashboard showing today's status + recent history
- Calculate hours worked automatically on clock-out
- Track IP addresses for security
- Admin dashboard for viewing all employee attendance
- Generate weekly/monthly attendance reports
- Integrate with Payroll module for hours-based calculations

---

#### Module: SMS Notifications
**Decision:** Twilio (recommended) or Africa's Talking  
**Priority:** LOW | **Time:** 1-2 hours

**Plan:**
- Choose SMS provider (Twilio ~$0.0075/SMS, Africa's Talking ~$0.005/SMS)
- Create SMS service abstraction layer
- Add `SmsOTP` model for SMS-based authentication
- Implement phone number validation (Kenyan format)
- Add rate limiting to prevent SMS spam
- Set monthly budget limits and cost tracking
- Use SMS for: OTP backup, shift reminders, urgent alerts
- Fallback to email if SMS fails

---

## V3 - Advanced Features

**Proposals:**
- Mobile app (React Native / Flutter)
- Real-time notifications (WebSockets)
- ML-based sales predictions
- Multi-branch support
- Customer loyalty program
- Advanced analytics (predictive inventory, sales forecasting)

---

## Implementation Order

1. **V1 (MVP):** Accounts ✅ → Products/Inventory → Sales/Orders → Payroll → Reports
2. **V2 (Enhancements):** Cloudinary → Clock-In/Out → SMS
3. **V3 (Advanced):** Mobile app → Real-time features → ML analytics
