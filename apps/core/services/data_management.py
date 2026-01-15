"""
Data Management Service - Core Infrastructure

This module provides controlled deletion of immutable records with full audit trail.
All deletion operations bypass model-level immutability guards using QuerySet.delete().

INTERNAL USE ONLY - These functions should only be called from:
- apps/inventory/services/delete.py
- apps/production/services/delete.py  
- apps/sales/services/delete.py
- apps/core/services/system_reset.py

Author: Chesanto Bakery Management System
Created: January 2026
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)


class DataManagementError(Exception):
    """
    Raised when a delete operation cannot proceed safely.
    
    This exception indicates either:
    - Dependencies exist (downstream records would be orphaned)
    - Permission denied (user is not SUPERADMIN)
    - Data integrity issue (would cause negative stock, etc.)
    
    Usage:
        from apps.core.services import DataManagementError
        
        try:
            delete_purchase_atomic(purchase, user, reason)
        except DataManagementError as e:
            messages.error(request, str(e))
            return redirect(...)
    """
    pass


def _serialize_instance(instance) -> dict:
    """
    Serialize a model instance to a JSON-safe dictionary for audit logging.
    
    Handles:
    - Decimal → str
    - date/datetime → ISO format string
    - ForeignKey → pk value
    - ManyToMany → list of pks (if loaded)
    
    Args:
        instance: Django model instance
    
    Returns:
        dict: JSON-serializable representation of the instance
    
    Example output:
        {
            "id": 47,
            "purchase_number": "PUR-FLOUR_TYPE1-2026-01-10-001",
            "quantity_purchased": "100.0000",
            "unit_price": "85.0000",
            "purchase_date": "2026-01-10",
            "purchased_by": 3,
            ...
        }
    """
    from django.forms.models import model_to_dict
    
    try:
        # Get all field values including non-editable fields
        data = {}
        for field in instance._meta.get_fields():
            # Skip reverse relations and many-to-many (unless we need them)
            if field.one_to_many or field.many_to_many:
                continue
            
            try:
                field_name = field.name
                value = getattr(instance, field_name, None)
                
                # Handle different types
                if value is None:
                    data[field_name] = None
                elif isinstance(value, Decimal):
                    data[field_name] = str(value)
                elif isinstance(value, datetime):
                    data[field_name] = value.isoformat()
                elif isinstance(value, date):
                    data[field_name] = value.isoformat()
                elif hasattr(value, 'pk'):  # ForeignKey - store the pk
                    data[field_name] = value.pk
                else:
                    # Try to use the value directly (for str, int, bool, etc.)
                    data[field_name] = value
            except Exception:
                # Skip fields that can't be serialized
                continue
        
        return data
        
    except Exception as e:
        logger.warning(f"Error serializing {instance.__class__.__name__}: {e}")
        # Fallback to basic model_to_dict
        try:
            return model_to_dict(instance)
        except Exception:
            return {"error": f"Could not serialize {instance.__class__.__name__}", "pk": str(instance.pk)}


def _force_delete(instance, user, action_type: str, reason: str = ''):
    """
    Safely delete an immutable record with full audit trail.
    
    This function bypasses model-level delete() guards by using QuerySet.delete().
    It should ONLY be called after dependency validation has passed.
    
    INTERNAL USE ONLY - not exposed to views directly.
    Called only from delete service functions after validation passes.
    
    Args:
        instance: Model instance to delete (must have a pk)
        user: User performing the deletion (must have role='SUPERADMIN')
        action_type: String like 'DELETE_PURCHASE', 'DELETE_BATCH', 'DELETE_DISPATCH'
        reason: Optional human-readable reason for deletion
    
    Returns:
        AuditLog: The created audit log entry
    
    Raises:
        DataManagementError: If user is not SUPERADMIN or deletion fails
    
    Example:
        from apps.core.services import _force_delete, DataManagementError
        
        # After all validations pass:
        audit_entry = _force_delete(purchase, user, 'DELETE_PURCHASE', 'Wrong quantity')
    """
    from apps.audit.models import AuditLog
    
    # Verify user has permission
    if not hasattr(user, 'role') or user.role != 'SUPERADMIN':
        raise DataManagementError(
            f"Permission denied: Only SUPERADMIN can delete records. "
            f"Your role: {getattr(user, 'role', 'unknown')}"
        )
    
    if not instance.pk:
        raise DataManagementError("Cannot delete an unsaved instance (no pk)")
    
    # Capture metadata before deletion
    model_class = instance.__class__
    app_label = instance._meta.app_label
    model_name = model_class.__name__
    object_pk = str(instance.pk)
    
    # Serialize record BEFORE deletion
    record_snapshot = _serialize_instance(instance)
    
    # Build audit message
    audit_message = f"{action_type}"
    if reason:
        audit_message = f"{action_type}: {reason}"
    
    # Create audit log entry BEFORE deletion
    # This ensures we have a record even if something goes wrong
    audit_entry = AuditLog.objects.create(
        action='DELETE',
        user=user,
        app_label=app_label,
        model_name=model_name,
        object_pk=object_pk,
        changes=record_snapshot,
        message=audit_message
    )
    
    logger.info(
        f"[DATA_MANAGEMENT] {user.email} deleting {app_label}.{model_name} pk={object_pk} "
        f"reason='{reason}' audit_id={audit_entry.pk}"
    )
    
    # Use QuerySet.delete() to bypass model's delete() method
    # This is the ONLY place in the codebase where this bypass is allowed
    deleted_count, _ = model_class.objects.filter(pk=instance.pk).delete()
    
    if deleted_count != 1:
        # This shouldn't happen, but log it if it does
        logger.error(
            f"[DATA_MANAGEMENT] Unexpected delete count: {deleted_count} for "
            f"{app_label}.{model_name} pk={object_pk}"
        )
    
    return audit_entry
