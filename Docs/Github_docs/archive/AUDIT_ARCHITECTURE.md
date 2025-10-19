# Audit System Architecture
**Project:** Chesanto Bakery Management System  
**Date:** October 16, 2025  
**Status:** ✅ ARCHITECTURAL DECISION  
**Priority:** CRITICAL - Foundation for accountability

---

## Problem Statement

Initial implementation conflated two distinct concerns:
1. **Activity Logging** - Recording user actions for analytics/debugging
2. **Audit Trail** - Legal/financial accountability for data changes

**Critical Issue:** Authentication was blocked by audit logging failures. Password resets failed because `AuditLogger.log_security_event()` threw errors, preventing users from accessing the system.

**Root Cause:** Wrong dependency direction - Authentication depended on Audit, when it should be the opposite.

---

## Architectural Decision

Split the audit app into two independent subsystems:

### 1. Activity Logger (Non-Critical)
**Purpose:** Track user behavior for analytics, debugging, and security monitoring

**Characteristics:**
- ✅ **Non-blocking** - Failures never prevent user actions
- ✅ **Fire-and-forget** - Async/background processing
- ✅ **Eventually consistent** - OK if logs arrive out of order
- ✅ **Graceful degradation** - System works fine without it

**Use Cases:**
- Login/logout timestamps
- Page views and navigation
- Button clicks and form submissions
- Failed login attempts
- OTP code generations
- Password reset requests
- Session timeouts
- Search queries
- Export/download actions

**Storage:**
- Fast writes (async queues)
- Can use separate database/service
- Can be archived/deleted without regulatory concerns
- Indexed for queries: `user_id`, `timestamp`, `action_type`

**Error Handling:**
```python
try:
    ActivityLogger.log_login(user, request)
except Exception as e:
    logger.warning(f"Activity logging failed: {e}")
    # Continue - user is already logged in
```

---

### 2. Audit Trail (Critical)
**Purpose:** Legally defensible record of who changed what data and when

**Characteristics:**
- ✅ **Transactional** - Part of database transaction (ACID compliance)
- ✅ **Blocking** - If audit fails, data change ROLLS BACK
- ✅ **Immutable** - Records can never be edited/deleted
- ✅ **Cryptographically signed** - Tamper detection (future enhancement)

**Use Cases:**
- Inventory quantity changes (prevent "90,000 KES missing goods")
- Financial transactions (petty cash, sales, expenses)
- Price modifications
- User role/permission changes
- Product recipe changes
- Salary/commission adjustments
- Deletion of records
- Bulk imports/exports

**Storage:**
- Same database transaction as business data
- Never deleted (regulatory retention: 7+ years)
- Includes: `user_id`, `timestamp`, `model`, `object_id`, `field`, `old_value`, `new_value`, `reason`, `ip_address`

**Error Handling:**
```python
with transaction.atomic():
    old_quantity = item.quantity
    item.quantity = new_quantity
    item.save()
    
    # If this fails, item.save() is rolled back
    AuditTrail.record_change(
        user=request.user,
        model='Inventory',
        object_id=item.id,
        field='quantity',
        old_value=old_quantity,
        new_value=new_quantity
    )
```

---

## Directory Structure

```
apps/audit/
├── __init__.py
├── admin.py
├── apps.py
├── models.py              # Both ActivityLog and AuditTrail models
├── middleware.py          # Auto-capture page views (activity only)
├── migrations/
│   └── ...
├── services/
│   ├── __init__.py
│   ├── activity_logger.py  # Non-blocking activity logging
│   ├── audit_trail.py      # Transactional audit records
│   └── archiver.py         # Archive old activity logs (audit trail never archived)
└── __pycache__/
```

---

## Models

### ActivityLog (Non-Critical)
```python
class ActivityLog(models.Model):
    """Non-blocking activity logging for analytics and debugging"""
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=100, db_index=True)  # 'login', 'page_view', 'logout'
    url = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    details = models.JSONField(default=dict, blank=True)  # Flexible extra data
    
    class Meta:
        db_table = 'activity_logs'
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"
```

### AuditTrail (Critical)
```python
class AuditTrail(models.Model):
    """Immutable, transactional audit trail for data accountability"""
    
    user = models.ForeignKey(User, on_delete=models.PROTECT)  # Never cascade delete
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)  # 'Inventory', 'Sale'
    object_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=20, choices=[
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
    ])
    field_name = models.CharField(max_length=100, blank=True)  # For UPDATE
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    reason = models.TextField(blank=True)  # Admin must provide reason for changes
    ip_address = models.GenericIPAddressField()
    
    # Future: Cryptographic signature for tamper detection
    # signature = models.CharField(max_length=128, blank=True)
    
    class Meta:
        db_table = 'audit_trail'
        indexes = [
            models.Index(fields=['model_name', 'object_id', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
        ordering = ['-timestamp']
        permissions = [
            ('view_all_audit', 'Can view all audit records'),
            ('view_own_audit', 'Can view own audit records'),
        ]
    
    def __str__(self):
        return f"{self.user} {self.action} {self.model_name}#{self.object_id} at {self.timestamp}"
```

---

## Service Layer

### ActivityLogger API

```python
from apps.audit.services.activity_logger import ActivityLogger

# All methods are fire-and-forget (never raise exceptions to caller)

ActivityLogger.log_login(user, request)
ActivityLogger.log_logout(user, request)
ActivityLogger.log_login_failed(email, request, reason='Invalid password')
ActivityLogger.log_page_view(user, request, url, duration_ms=None)
ActivityLogger.log_otp_sent(user, request, purpose='login')
ActivityLogger.log_otp_verified(user, request, purpose='login')
ActivityLogger.log_password_reset_requested(email, request)
ActivityLogger.log_export(user, request, export_type='CSV', model='Sales')
ActivityLogger.log_search(user, request, query, results_count)
```

### AuditTrail API

```python
from apps.audit.services.audit_trail import AuditTrail

# All methods are transactional (raise exceptions if they fail)

# Record a creation
AuditTrail.record_create(
    user=request.user,
    model_name='Sale',
    object_id=sale.id,
    ip_address=get_client_ip(request),
    reason='Daily sales entry'
)

# Record an update (field-level)
AuditTrail.record_update(
    user=request.user,
    model_name='Inventory',
    object_id=item.id,
    field_name='quantity',
    old_value='100',
    new_value='85',
    ip_address=get_client_ip(request),
    reason='Sold 15 units to Customer XYZ'
)

# Record a deletion
AuditTrail.record_delete(
    user=request.user,
    model_name='Product',
    object_id=product.id,
    old_value=model_to_dict(product),  # Store full snapshot
    ip_address=get_client_ip(request),
    reason='Product discontinued'
)

# Get audit history for an object
history = AuditTrail.get_history(model_name='Inventory', object_id=42)

# Get user's audit records (for accountability report)
user_actions = AuditTrail.get_user_actions(user=some_user, start_date=..., end_date=...)
```

---

## Usage in Views

### Example 1: Login (Activity Only)
```python
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(email=email, password=password)
        
        if user:
            login(request, user)
            
            # Activity logging - non-blocking
            ActivityLogger.log_login(user, request)
            
            return redirect('dashboard')
        else:
            # Activity logging - non-blocking
            ActivityLogger.log_login_failed(email, request, reason='Invalid credentials')
            
            messages.error(request, 'Invalid credentials')
            return render(request, 'accounts/login.html')
    
    return render(request, 'accounts/login.html')
```

### Example 2: Inventory Update (Audit Trail)
```python
@transaction.atomic
def update_inventory_view(request, item_id):
    item = get_object_or_404(Inventory, id=item_id)
    
    if request.method == 'POST':
        old_quantity = item.quantity
        new_quantity = int(request.POST.get('quantity'))
        reason = request.POST.get('reason', '')
        
        # Update business data
        item.quantity = new_quantity
        item.save()
        
        # Audit trail - MUST succeed or transaction rolls back
        AuditTrail.record_update(
            user=request.user,
            model_name='Inventory',
            object_id=item.id,
            field_name='quantity',
            old_value=str(old_quantity),
            new_value=str(new_quantity),
            ip_address=get_client_ip(request),
            reason=reason or 'Manual adjustment'
        )
        
        # Activity logging - fire-and-forget
        ActivityLogger.log_page_view(request.user, request, request.path)
        
        messages.success(request, f'Inventory updated: {old_quantity} → {new_quantity}')
        return redirect('inventory_list')
    
    return render(request, 'inventory/edit.html', {'item': item})
```

### Example 3: Password Reset (Activity Only)
```python
def password_reset_request_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.success(request, 'If account exists, you will receive a code.')
            return render(request, 'accounts/password_reset_request.html')
        
        # Generate and send code
        code = generate_otp(user, purpose='PASSWORD_RESET')
        
        try:
            EmailService.send_password_reset(email, code, user)
        except Exception as e:
            messages.error(request, 'Failed to send code. Try again.')
            return render(request, 'accounts/password_reset_request.html')
        
        # Activity logging - fire-and-forget (never blocks password reset)
        ActivityLogger.log_password_reset_requested(email, request)
        
        messages.success(request, 'Code sent to your email.')
        return redirect('password_reset_verify')
    
    return render(request, 'accounts/password_reset_request.html')
```

---

## Permission Matrix

| Action | Activity Logger | Audit Trail |
|--------|-----------------|-------------|
| **View Own Logs** | All users | All users |
| **View Others' Activity** | Admin, Superadmin | Admin, Superadmin |
| **View Others' Audit** | Admin (except Superadmin actions), Superadmin (all) | Admin (except Superadmin actions), Superadmin (all) |
| **Delete Records** | Admin (archive after 1 year) | NEVER (immutable) |
| **Export** | Admin, Superadmin | Superadmin only |

---

## Migration Strategy

### Phase 1: Create New Services (Non-Breaking)
1. Create `services/activity_logger.py` with fire-and-forget methods
2. Create `services/audit_trail.py` with transactional methods
3. Keep old `services/logger.py` as deprecated wrapper

### Phase 2: Update Views (Gradual)
1. Authentication views → Use ActivityLogger (non-blocking)
2. Financial/Inventory views → Use AuditTrail (transactional)
3. Other views → Use ActivityLogger for now

### Phase 3: Remove Old Code
1. Delete `services/logger.py`
2. Search codebase for `AuditLogger` → Replace with `ActivityLogger` or `AuditTrail`
3. Update all imports

---

## Testing Strategy

### Activity Logger Tests
```python
def test_activity_logger_never_blocks():
    """Activity logging failures should not raise exceptions"""
    with mock.patch('apps.audit.models.ActivityLog.objects.create', side_effect=Exception):
        # Should not raise
        ActivityLogger.log_login(user, request)

def test_activity_log_records_details():
    ActivityLogger.log_login(user, request)
    log = ActivityLog.objects.latest('timestamp')
    assert log.user == user
    assert log.action == 'login'
    assert log.ip_address == '127.0.0.1'
```

### Audit Trail Tests
```python
def test_audit_trail_blocks_on_failure():
    """Audit trail failures should prevent data changes"""
    with transaction.atomic():
        old_qty = item.quantity
        item.quantity = 50
        item.save()
        
        with mock.patch('apps.audit.models.AuditTrail.objects.create', side_effect=Exception):
            with pytest.raises(Exception):
                AuditTrail.record_update(...)
        
        item.refresh_from_db()
        assert item.quantity == old_qty  # Rolled back

def test_audit_trail_immutable():
    """Audit records cannot be modified"""
    audit = AuditTrail.objects.create(...)
    
    with pytest.raises(PermissionDenied):
        audit.old_value = 'hacked'
        audit.save()
```

---

## Future Enhancements

### 1. Cryptographic Signatures (Audit Trail)
- Hash each audit record with previous record's hash (blockchain-like)
- Detect tampering: If hash chain breaks, records were modified
- Implement: `AuditTrail.verify_integrity()` method

### 2. Async Activity Logging
- Use Celery/Redis queue for ActivityLogger
- Batch insert 100s of logs at once (performance)
- Graceful degradation if queue is down

### 3. Real-Time Monitoring Dashboard
- Show live activity feed for Superadmin
- Alert on suspicious patterns: Multiple failed logins, unusual hours, large data exports
- Integration with security monitoring tools

### 4. Machine Learning Anomaly Detection
- Learn normal user behavior patterns
- Flag anomalies: User A usually works 8am-5pm, suddenly active at 2am
- Prevent insider threats

---

## Key Principles

1. **Authentication NEVER depends on Audit**
2. **Activity logging is optional (analytics/debugging)**
3. **Audit trail is mandatory (legal/financial accountability)**
4. **Audit trail = Database transaction (ACID)**
5. **Activity logging = Fire-and-forget (eventual consistency)**
6. **Audit records are immutable (tamper-proof)**
7. **Activity logs can be archived/deleted**

---

## References

- **AUTHENTICATION_SYSTEM.md** - See "Audit Logging" section
- **project_structure.md** - See `apps/audit/` folder structure
- Django Transactions: https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- ACID Compliance: https://en.wikipedia.org/wiki/ACID
