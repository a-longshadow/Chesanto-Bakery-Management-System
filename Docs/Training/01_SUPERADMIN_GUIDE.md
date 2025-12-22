# 👑 Superadmin Guide

> **Role:** CEO / Developer | **Access Level:** Full System Access

As a Superadmin, you have complete access to all system features. This guide covers the administrative functions unique to your role.

---

## 🎯 Your Responsibilities

- User management (create, approve, deactivate accounts)
- Payroll management
- Full access to all reports and analytics
- System configuration
- All features available to other roles

---

## 👥 User Management

### Viewing All Users

1. Go to **Admin Panel** (or Users section)
2. You'll see a list of all user accounts
3. Use filters to find specific users:
   - By role (Superadmin, Admin, Salesman, etc.)
   - By status (Active, Inactive, Pending Approval)
   - By name or email

### Creating a New User

1. Go to **Users** → **Add New User**
2. Fill in the required information:
   - **Email** (must be unique)
   - **First Name**
   - **Last Name**
   - **Role** (select from dropdown)
   - **Phone Number**
3. For employees (Salesman, Dispatch, etc.):
   - **Employee ID** (e.g., CHE001)
   - **Department**
   - **Position**
4. Click **"Create User"**
5. The user will receive an email with login instructions

### Approving New Users

If users can self-register:

1. Go to **Users** → **Pending Approval**
2. Review the user's information
3. Assign the appropriate **Role**
4. Click **"Approve"** or **"Reject"**

### Deactivating a User

To disable a user's access without deleting their account:

1. Find the user in the user list
2. Click on their profile
3. Click **"Deactivate"**
4. Confirm the action

**Note:** Deactivated users cannot log in but their historical data is preserved.

### Resetting a User's Password

If a user is locked out:

1. Find the user in the user list
2. Click **"Reset Password"**
3. A new temporary password will be generated
4. Communicate this password to the user securely

---

## 💰 Payroll Module

**Location:** Main Menu → **Payroll**

### Viewing Payroll Dashboard

The payroll dashboard shows:
- Total payroll for current period
- Employee count by department
- Pending salary payments

### Managing Employee Salaries

1. Go to **Payroll** → **Employee Salaries**
2. View or edit employee salary information:
   - Basic Salary
   - Pay per Day (for daily workers)
   - Commission Rate (for salesmen)
   - Sales Target

### Processing Payroll

1. Go to **Payroll** → **Process Payroll**
2. Select the pay period (dates)
3. Review calculated salaries
4. Include/exclude specific employees if needed
5. Click **"Generate Payroll"**
6. Review the summary
7. Click **"Confirm & Process"**

---

## 📊 Reports & Analytics

You have access to ALL reports. See the [Admin Guide](./02_ADMIN_GUIDE.md) for detailed report instructions.

### Key Reports

| Report | Location | Frequency |
|--------|----------|-----------|
| Daily P&L | Reports → Daily | Daily |
| Weekly Summary | Reports → Weekly | Weekly |
| Monthly P&L | Reports → Monthly | Monthly |
| Annual Report | Reports → Annual | Yearly |
| Commission Report | Sales → Commission Report | As needed |

### Scheduled Reports

Reports are automatically generated and emailed:
- **Morning Report:** Sent at 7:00 AM (previous day summary)
- **Weekly Report:** Sent Monday mornings
- **Monthly Report:** Sent 1st of each month

---

## ⚙️ System Configuration

### Expense Categories

1. Go to **Settings** → **Expense Categories**
2. Add, edit, or deactivate categories used in reporting

### Report Recipients

To manage who receives scheduled reports:

1. Go to **Settings** → **Report Schedules**
2. View/edit recipients for each report type
3. Add email addresses for automatic report delivery

---

## 🔒 Security Notes

As a Superadmin:

1. **You cannot edit other Superadmins' profiles** (mutual protection)
2. **All your actions are logged** for audit purposes
3. **Use a strong, unique password**
4. **Log out when not using the system**
5. **Be careful when deactivating users** - it affects their access immediately

---

## 📋 Quick Reference

| Task | Navigation |
|------|------------|
| Create User | Users → Add New User |
| Approve User | Users → Pending Approval |
| Deactivate User | Users → Find User → Deactivate |
| Reset Password | Users → Find User → Reset Password |
| View Payroll | Payroll → Dashboard |
| Process Payroll | Payroll → Process Payroll |
| View Reports | Reports → Select Report Type |
| Manage Settings | Settings → (various options) |

---

## 🔗 Related Guides

Since you have full access, you may also want to review:

- [Admin Guide](./02_ADMIN_GUIDE.md) - Financial operations
- [Production Manager Guide](./03_PRODUCTION_MANAGER_GUIDE.md) - Production workflows
- [Dispatch Guide](./04_DISPATCH_GUIDE.md) - Sales dispatch operations

---

**← Back to [Table of Contents](./README.md)**
