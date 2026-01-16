"""
Tests for Data Management Feature

Tests the dependency checkers, delete services, and access control.
Does NOT test visual/template rendering - those require manual verification.

Run with:
    python manage.py test apps.core.tests.test_data_management

Author: Chesanto Bakery Management System
Created: January 2026
"""

from decimal import Decimal
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.core.services import (
    can_delete_batch,
    can_delete_dispatch,
    DataManagementError,
)

User = get_user_model()


def create_test_user(username, email, role='SUPERADMIN', is_primary_superadmin=False, **kwargs):
    """Helper to create a fully-formed test user with all required fields."""
    defaults = {
        'username': username,
        'email': email,
        'password': 'testpass123',
        'role': role,
        'first_name': 'Test',
        'last_name': 'User',
        'mobile_primary': '+254700000000',
        'is_active': True,
        'is_approved': True,
        'is_staff': True,  # Required for admin URL access
        'is_primary_superadmin': is_primary_superadmin,
    }
    defaults.update(kwargs)
    password = defaults.pop('password')
    user = User(**defaults)
    user.set_password(password)
    user.save()
    return user


# =============================================================================
# DEPENDENCY CHECKER TESTS
# =============================================================================

class CanDeleteDispatchTests(TestCase):
    """Tests for can_delete_dispatch() function."""
    
    def setUp(self):
        """Create test fixtures."""
        from apps.sales.models import SalesDispatch, SalesReturn
        
        self.SalesReturn = SalesReturn
        
        # Create users
        self.superadmin = create_test_user(
            'superadmin_disp',
            'admin_disp@example.com',
            role='SUPERADMIN',
        )
        self.salesperson = create_test_user(
            'salesman_disp',
            'salesman_disp@example.com',
            role='SALESMAN',
        )
        
        # Create a dispatch
        self.dispatch = SalesDispatch.objects.create(
            dispatch_number='TEST-DISP-002',
            salesperson=self.salesperson,
            dispatch_date=timezone.now().date(),
            crates_dispatched=5,
            created_by=self.superadmin,
        )
    
    def test_can_delete_when_no_return_exists(self):
        """Dispatch can be deleted when no return exists for it."""
        can_delete, reason = can_delete_dispatch(self.dispatch)
        
        self.assertTrue(can_delete)
        self.assertEqual(reason, "")
    
    def test_cannot_delete_when_return_exists(self):
        """Dispatch cannot be deleted when a return was processed for it."""
        # Create a return for this dispatch
        sales_return = self.SalesReturn.objects.create(
            dispatch=self.dispatch,
            return_date=timezone.now().date(),
            crates_returned=5,
            created_by=self.superadmin,
        )
        
        can_delete, reason = can_delete_dispatch(self.dispatch)
        
        self.assertFalse(can_delete)
        self.assertIn("Cannot delete", reason)
        self.assertIn("return", reason.lower())
        
        # Cleanup - use QuerySet.delete() to bypass model guard
        self.SalesReturn.objects.filter(pk=sales_return.pk).delete()


# =============================================================================
# RETURN IMMUTABILITY TESTS
# =============================================================================

class SalesReturnImmutabilityTests(TestCase):
    """
    Tests that SalesReturn is truly immutable.
    
    From spec: Returns (SalesReturn) are NEVER deletable.
    """
    
    def setUp(self):
        """Create test fixtures."""
        from apps.sales.models import SalesDispatch, SalesReturn
        
        self.SalesReturn = SalesReturn
        
        # Create users
        self.superadmin = create_test_user(
            'superadmin_imm',
            'admin_imm@example.com',
            role='SUPERADMIN',
            is_primary_superadmin=True,
        )
        self.salesperson = create_test_user(
            'salesman_imm',
            'salesman_imm@example.com',
            role='SALESMAN',
        )
        
        # Create a dispatch
        self.dispatch = SalesDispatch.objects.create(
            dispatch_number='TEST-DISP-IMM-003',
            salesperson=self.salesperson,
            dispatch_date=timezone.now().date(),
            crates_dispatched=5,
            created_by=self.superadmin,
        )
        
        # Create a return
        self.sales_return = self.SalesReturn.objects.create(
            dispatch=self.dispatch,
            return_date=timezone.now().date(),
            crates_returned=5,
            created_by=self.superadmin,
        )
    
    def test_model_delete_raises_error(self):
        """SalesReturn.delete() raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            self.sales_return.delete()
        
        self.assertIn("cannot be deleted", str(ctx.exception).lower())
    
    def test_save_immutable_field_raises_error(self):
        """Modifying immutable fields raises ValueError on save."""
        self.sales_return.total_revenue = Decimal('99999.00')
        
        with self.assertRaises(ValueError) as ctx:
            self.sales_return.save()
        
        self.assertIn("immutable", str(ctx.exception).lower())
    
    def test_crate_status_fields_are_mutable(self):
        """Only crates_marked_lost and crates_marked_damaged can be changed."""
        # These should NOT raise errors
        self.sales_return.crates_marked_lost = True
        self.sales_return.crates_marked_damaged = True
        self.sales_return.save()  # Should succeed
        
        # Reload and verify
        self.sales_return.refresh_from_db()
        self.assertTrue(self.sales_return.crates_marked_lost)
        self.assertTrue(self.sales_return.crates_marked_damaged)
    
    def tearDown(self):
        """Clean up - use QuerySet.delete() to bypass model guard."""
        self.SalesReturn.objects.filter(pk=self.sales_return.pk).delete()


# =============================================================================
# ACCESS CONTROL TESTS
# =============================================================================

class DeleteViewAccessControlTests(TestCase):
    """Tests that delete views enforce SUPERADMIN-only access."""
    
    def setUp(self):
        """Create users with different roles."""
        self.client = Client()
        
        # Create SUPERADMIN user
        self.superadmin = create_test_user(
            'superadmin_access',
            'superadmin_access@example.com',
            role='SUPERADMIN',
        )
        
        # Create non-SUPERADMIN users
        self.admin = create_test_user(
            'admin_access',
            'admin_access@example.com',
            role='ADMIN',
        )
        self.salesman = create_test_user(
            'salesman_access',
            'salesman_access@example.com',
            role='SALESMAN',
        )
    
    def test_admin_cannot_access_batch_delete(self):
        """ADMIN role cannot access batch delete view."""
        self.client.login(email='admin_access@example.com', password='testpass123')
        
        # Try to access batch delete (batch ID doesn't need to exist - access check comes first)
        response = self.client.get('/production/batch/999/delete/')
        
        # Should redirect (302) - access denied
        self.assertEqual(response.status_code, 302)
    
    def test_salesman_cannot_access_dispatch_delete(self):
        """SALESMAN role cannot access dispatch delete view."""
        self.client.login(email='salesman_access@example.com', password='testpass123')
        
        response = self.client.get('/sales/dispatch/999/delete/')
        
        # Should redirect (302) - access denied
        self.assertEqual(response.status_code, 302)
    
    def test_admin_cannot_access_purchase_delete(self):
        """ADMIN role cannot access purchase delete view."""
        self.client.login(email='admin_access@example.com', password='testpass123')
        
        response = self.client.get('/inventory/item/1/purchase/999/delete/')
        
        # Should redirect (302) - access denied
        self.assertEqual(response.status_code, 302)


class FullResetAccessControlTests(TestCase):
    """Tests that full reset is PRIMARY SUPERADMIN only."""
    
    def setUp(self):
        """Create users with different superadmin levels."""
        self.client = Client()
        
        # Primary Superadmin - with all required fields
        self.primary_superadmin = create_test_user(
            'primary_sa',
            'primary@example.com',
            role='SUPERADMIN',
            is_primary_superadmin=True,
        )
        
        # Regular Superadmin (not primary)
        self.regular_superadmin = create_test_user(
            'regular_sa',
            'regular@example.com',
            role='SUPERADMIN',
            is_primary_superadmin=False,
        )
        
        # Admin
        self.admin = create_test_user(
            'admin_reset',
            'admin_reset@example.com',
            role='ADMIN',
        )
    
    def test_primary_superadmin_can_access_reset(self):
        """Primary SUPERADMIN can access full reset page."""
        # Use email for login since USERNAME_FIELD = 'email'
        logged_in = self.client.login(email='primary@example.com', password='testpass123')
        self.assertTrue(logged_in, "Login should succeed for primary superadmin")
        
        response = self.client.get('/admin/data-management/full-reset/')
        
        # Should return 200 OK
        self.assertEqual(response.status_code, 200)
    
    def test_regular_superadmin_cannot_access_reset(self):
        """Regular SUPERADMIN (not primary) cannot access reset."""
        self.client.login(email='regular@example.com', password='testpass123')
        
        response = self.client.get('/admin/data-management/full-reset/')
        
        # Should redirect (302) - access denied
        self.assertEqual(response.status_code, 302)
    
    def test_admin_cannot_access_reset(self):
        """ADMIN role cannot access full reset."""
        self.client.login(email='admin_reset@example.com', password='testpass123')
        
        response = self.client.get('/admin/data-management/full-reset/')
        
        # Should redirect (302) - access denied
        self.assertEqual(response.status_code, 302)


# =============================================================================
# NO DELETE_RETURN FUNCTION EXISTS
# =============================================================================

class NoDeleteReturnTests(TestCase):
    """
    Tests that no mechanism exists to delete returns.
    
    From spec: No delete_return() or delete_return_atomic() function exists.
    """
    
    def test_no_delete_return_in_services(self):
        """No delete_return function exists in core.services."""
        from apps.core import services
        
        self.assertFalse(hasattr(services, 'delete_return'))
        self.assertFalse(hasattr(services, 'delete_return_atomic'))
    
    def test_no_return_delete_url(self):
        """No /sales/return/<id>/delete/ URL route exists."""
        from django.urls import resolve, Resolver404
        
        with self.assertRaises(Resolver404):
            resolve('/sales/return/1/delete/')
