"""
RBAC Decorator Tests
Tests role-based access control for all decorators.
"""
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User


class RBACDecoratorTests(TestCase):
    """Test role-based access control decorators."""
    
    @classmethod
    def setUpTestData(cls):
        """Create test users for each role."""
        cls.superadmin = User.objects.create_user(
            username='test_superadmin',
            email='superadmin@test.com',
            password='testpass123',
            role='SUPERADMIN'
        )
        cls.admin = User.objects.create_user(
            username='test_admin',
            email='admin@test.com',
            password='testpass123',
            role='ADMIN'
        )
        cls.product_manager = User.objects.create_user(
            username='test_pm',
            email='pm@test.com',
            password='testpass123',
            role='PRODUCT_MANAGER'
        )
        cls.dept_head = User.objects.create_user(
            username='test_dh',
            email='dh@test.com',
            password='testpass123',
            role='DEPT_HEAD'
        )
        cls.dispatch = User.objects.create_user(
            username='test_dispatch',
            email='dispatch@test.com',
            password='testpass123',
            role='DISPATCH'
        )
        cls.salesman = User.objects.create_user(
            username='test_salesman',
            email='salesman@test.com',
            password='testpass123',
            role='SALESMAN'
        )
        cls.security = User.objects.create_user(
            username='test_security',
            email='security@test.com',
            password='testpass123',
            role='SECURITY'
        )
    
    def setUp(self):
        self.client = Client()
    
    # =========================================================================
    # PRODUCTION APP TESTS (@management_required)
    # =========================================================================
    
    def test_production_dashboard_superadmin_allowed(self):
        """SUPERADMIN can access production dashboard."""
        self.client.force_login(self.superadmin)
        response = self.client.get('/production/')
        self.assertEqual(response.status_code, 200)
    
    def test_production_dashboard_admin_allowed(self):
        """ADMIN can access production dashboard."""
        self.client.force_login(self.admin)
        response = self.client.get('/production/')
        self.assertEqual(response.status_code, 200)
    
    def test_production_dashboard_product_manager_allowed(self):
        """PRODUCT_MANAGER can access production dashboard."""
        self.client.force_login(self.product_manager)
        response = self.client.get('/production/')
        self.assertEqual(response.status_code, 200)
    
    def test_production_dashboard_salesman_blocked(self):
        """SALESMAN cannot access production dashboard."""
        self.client.force_login(self.salesman)
        response = self.client.get('/production/')
        # Should redirect to home (302) not 200
        self.assertNotEqual(response.status_code, 200)
    
    def test_production_dashboard_security_blocked(self):
        """SECURITY cannot access production dashboard."""
        self.client.force_login(self.security)
        response = self.client.get('/production/')
        self.assertNotEqual(response.status_code, 200)
    
    # =========================================================================
    # SALES APP TESTS
    # =========================================================================
    
    def test_sales_dashboard_dispatch_allowed(self):
        """DISPATCH can access sales dashboard."""
        self.client.force_login(self.dispatch)
        response = self.client.get('/sales/')
        self.assertEqual(response.status_code, 200)
    
    def test_sales_dashboard_salesman_blocked(self):
        """SALESMAN cannot access main sales dashboard."""
        self.client.force_login(self.salesman)
        response = self.client.get('/sales/')
        self.assertNotEqual(response.status_code, 200)
    
    def test_dispatch_create_dispatch_allowed(self):
        """DISPATCH can access dispatch create."""
        self.client.force_login(self.dispatch)
        response = self.client.get('/sales/dispatch/create/')
        self.assertEqual(response.status_code, 200)
    
    def test_dispatch_create_salesman_blocked(self):
        """SALESMAN cannot create dispatch."""
        self.client.force_login(self.salesman)
        response = self.client.get('/sales/dispatch/create/')
        self.assertNotEqual(response.status_code, 200)
    
    def test_sales_report_admin_allowed(self):
        """ADMIN can access sales report."""
        self.client.force_login(self.admin)
        response = self.client.get('/sales/reports/')
        self.assertEqual(response.status_code, 200)
    
    def test_sales_report_dispatch_blocked(self):
        """DISPATCH cannot access sales report (financial data)."""
        self.client.force_login(self.dispatch)
        response = self.client.get('/sales/reports/')
        self.assertNotEqual(response.status_code, 200)
    
    # =========================================================================
    # SALESMAN-SPECIFIC VIEWS
    # =========================================================================
    
    def test_my_dispatches_salesman_allowed(self):
        """SALESMAN can access their own dispatches."""
        self.client.force_login(self.salesman)
        response = self.client.get('/sales/my-dispatches/')
        self.assertEqual(response.status_code, 200)
    
    def test_my_dispatches_admin_allowed(self):
        """ADMIN can access my-dispatches with supervisory access."""
        self.client.force_login(self.admin)
        response = self.client.get('/sales/my-dispatches/')
        self.assertEqual(response.status_code, 200)
    
    def test_my_commissions_salesman_allowed(self):
        """SALESMAN can access their own commissions."""
        self.client.force_login(self.salesman)
        response = self.client.get('/sales/my-commissions/')
        self.assertEqual(response.status_code, 200)
    
    # =========================================================================
    # SECURITY-SPECIFIC VIEWS
    # =========================================================================
    
    def test_gate_log_security_allowed(self):
        """SECURITY can access gate log."""
        self.client.force_login(self.security)
        response = self.client.get('/sales/gate-log/')
        self.assertEqual(response.status_code, 200)
    
    def test_gate_log_salesman_blocked(self):
        """SALESMAN cannot access gate log."""
        self.client.force_login(self.salesman)
        response = self.client.get('/sales/gate-log/')
        self.assertNotEqual(response.status_code, 200)
    
    # =========================================================================
    # INVENTORY APP TESTS (@management_required, @admin_required for create)
    # =========================================================================
    
    def test_inventory_dashboard_admin_allowed(self):
        """ADMIN can access inventory dashboard."""
        self.client.force_login(self.admin)
        response = self.client.get('/inventory/')
        self.assertEqual(response.status_code, 200)
    
    def test_inventory_dashboard_salesman_blocked(self):
        """SALESMAN cannot access inventory dashboard."""
        self.client.force_login(self.salesman)
        response = self.client.get('/inventory/')
        self.assertNotEqual(response.status_code, 200)
    
    def test_create_purchase_admin_allowed(self):
        """ADMIN can create purchases."""
        self.client.force_login(self.admin)
        response = self.client.get('/inventory/purchase/create/')
        self.assertEqual(response.status_code, 200)
    
    def test_create_purchase_product_manager_blocked(self):
        """PRODUCT_MANAGER cannot create purchases (admin only)."""
        self.client.force_login(self.product_manager)
        response = self.client.get('/inventory/purchase/create/')
        self.assertNotEqual(response.status_code, 200)
    
    # =========================================================================
    # PRODUCTS APP TESTS
    # =========================================================================
    
    def test_products_dashboard_management_allowed(self):
        """DEPT_HEAD can access products dashboard."""
        self.client.force_login(self.dept_head)
        response = self.client.get('/products/')
        self.assertEqual(response.status_code, 200)
    
    def test_products_dashboard_dispatch_blocked(self):
        """DISPATCH cannot access products dashboard."""
        self.client.force_login(self.dispatch)
        response = self.client.get('/products/')
        self.assertNotEqual(response.status_code, 200)
    
    def test_product_create_admin_allowed(self):
        """ADMIN can create products."""
        self.client.force_login(self.admin)
        response = self.client.get('/products/create/')
        self.assertEqual(response.status_code, 200)
    
    def test_product_create_product_manager_blocked(self):
        """PRODUCT_MANAGER cannot create products (admin only)."""
        self.client.force_login(self.product_manager)
        response = self.client.get('/products/create/')
        self.assertNotEqual(response.status_code, 200)
    
    # =========================================================================
    # ANALYTICS APP TESTS (@admin_required)
    # =========================================================================
    
    def test_analytics_dashboard_admin_allowed(self):
        """ADMIN can access analytics dashboard."""
        self.client.force_login(self.admin)
        response = self.client.get('/analytics/dashboard/')
        self.assertEqual(response.status_code, 200)
    
    def test_analytics_dashboard_product_manager_blocked(self):
        """PRODUCT_MANAGER cannot access analytics (admin only)."""
        self.client.force_login(self.product_manager)
        response = self.client.get('/analytics/dashboard/')
        self.assertNotEqual(response.status_code, 200)
    
    def test_analytics_dashboard_salesman_blocked(self):
        """SALESMAN cannot access analytics."""
        self.client.force_login(self.salesman)
        response = self.client.get('/analytics/dashboard/')
        self.assertNotEqual(response.status_code, 200)
