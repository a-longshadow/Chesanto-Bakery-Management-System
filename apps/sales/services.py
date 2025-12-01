"""
Sales App - Service Layer

All sales business logic with ACID compliance.
Each method follows:
- @transaction.atomic for database integrity
- select_for_update() for row locking where needed
- Comprehensive validation before any writes
- Structured return dicts for consistent API
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from datetime import date

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.products.models import Product
from apps.production.models import ProductStock, ProductStockMovement
from apps.production.services import ProductionService

from .models import (
    SalesDispatch,
    SalesDispatchItem,
    SalesReturn,
    SalesReturnItem
)

User = get_user_model()


# ============================================================================
# CONSTANTS
# ============================================================================

COMMISSION_MAX_PERCENTAGE = Decimal('0.20')  # 20% of revenue


# ============================================================================
# DISPATCH SERVICE
# ============================================================================

class DispatchService:
    """
    Service for dispatch creation and validation.
    
    All methods follow ACID principles:
    - Atomic transactions
    - Consistent state
    - Isolated operations
    - Durable records
    """
    
    @staticmethod
    def get_available_products() -> List[Dict]:
        """
        Get list of active products with current stock levels.
        
        Returns:
            List of dicts with product info and stock levels
        """
        products = Product.objects.filter(is_active=True).order_by('name')
        result = []
        
        for product in products:
            try:
                stock = ProductStock.objects.get(product=product)
                current_stock = stock.current_stock
            except ProductStock.DoesNotExist:
                current_stock = 0
            
            result.append({
                'id': product.id,
                'name': product.name,
                'selling_price': product.selling_price,
                'current_stock': current_stock
            })
        
        return result
    
    @staticmethod
    def get_salespeople() -> List[Dict]:
        """
        Get list of active salespeople (Users with role=SALESMAN).
        
        Returns:
            List of dicts with salesperson info
        """
        salespeople = User.objects.filter(
            role='SALESMAN',
            is_active=True
        ).order_by('first_name', 'last_name')
        
        return [
            {
                'id': sp.id,
                'name': sp.get_display_name(),
                'full_name': sp.get_full_name()
            }
            for sp in salespeople
        ]
    
    @staticmethod
    def validate_dispatch_request(
        salesperson_id: int,
        dispatch_date: date,
        items: List[Dict],
        crates: int = 0
    ) -> Dict[str, Any]:
        """
        Pre-transaction validation for dispatch creation.
        
        Args:
            salesperson_id: ID of User with role=SALESMAN
            dispatch_date: Date of dispatch
            items: List of {'product_id': int, 'quantity': int}
            crates: Number of crates to dispatch
        
        Returns:
            dict with 'valid', 'errors', 'warnings' keys
        """
        errors = []
        warnings = []
        
        # Validate salesperson
        try:
            salesperson = User.objects.get(
                id=salesperson_id,
                role='SALESMAN',
                is_active=True
            )
        except User.DoesNotExist:
            errors.append("Invalid or inactive salesperson selected.")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        # Check for existing dispatch
        if SalesDispatch.objects.filter(
            salesperson_id=salesperson_id,
            dispatch_date=dispatch_date
        ).exists():
            errors.append(
                f"A dispatch already exists for {salesperson.get_display_name()} "
                f"on {dispatch_date}. Only one dispatch per salesperson per day is allowed."
            )
        
        # Validate items
        if not items:
            errors.append("At least one product must be dispatched.")
        else:
            for item in items:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 0)
                
                if quantity <= 0:
                    continue  # Skip zero quantities
                
                # Check product exists
                try:
                    product = Product.objects.get(id=product_id, is_active=True)
                except Product.DoesNotExist:
                    errors.append(f"Product ID {product_id} not found or inactive.")
                    continue
                
                # Check stock availability
                try:
                    stock = ProductStock.objects.get(product_id=product_id)
                    if stock.current_stock < quantity:
                        errors.append(
                            f"Insufficient stock for {product.name}: "
                            f"requested {quantity}, available {stock.current_stock}"
                        )
                    elif stock.current_stock - quantity <= 10:
                        warnings.append(
                            f"Low stock warning: {product.name} will have only "
                            f"{stock.current_stock - quantity} units after dispatch"
                        )
                except ProductStock.DoesNotExist:
                    errors.append(f"No stock record found for {product.name}")
        
        # Validate crates (if needed in future with Inventory integration)
        if crates < 0:
            errors.append("Crates cannot be negative.")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @classmethod
    @transaction.atomic
    def create_dispatch(
        cls,
        salesperson_id: int,
        dispatch_date: date,
        items: List[Dict],
        crates: int,
        user
    ) -> Tuple[Optional[SalesDispatch], Dict[str, Any]]:
        """
        Create a dispatch with full ACID compliance.
        
        Args:
            salesperson_id: ID of User with role=SALESMAN
            dispatch_date: Date of dispatch
            items: List of {'product_id': int, 'quantity': int}
            crates: Number of crates to dispatch
            user: User creating the dispatch
        
        Returns:
            Tuple of (SalesDispatch or None, result dict)
        """
        result = {'success': False, 'errors': [], 'warnings': []}
        
        try:
            # Step 1: Validate request
            validation = cls.validate_dispatch_request(
                salesperson_id, dispatch_date, items, crates
            )
            
            if not validation['valid']:
                result['errors'] = validation['errors']
                result['warnings'] = validation['warnings']
                return None, result
            
            result['warnings'] = validation['warnings']
            
            # Step 2: Get salesperson (lock row)
            salesperson = User.objects.select_for_update().get(
                id=salesperson_id,
                role='SALESMAN',
                is_active=True
            )
            
            # Step 3: Re-check no existing dispatch (inside transaction)
            if SalesDispatch.objects.filter(
                salesperson_id=salesperson_id,
                dispatch_date=dispatch_date
            ).exists():
                result['errors'].append("Dispatch already exists for this date.")
                return None, result
            
            # Step 4: Create dispatch record
            dispatch = SalesDispatch(
                salesperson=salesperson,
                dispatch_date=dispatch_date,
                crates_dispatched=crates,
                created_by=user
            )
            dispatch.save()
            
            # Step 5: Create items and deduct stock
            total_units = 0
            expected_revenue = Decimal('0.00')
            
            for item in items:
                quantity = item.get('quantity', 0)
                if quantity <= 0:
                    continue
                
                product_id = item['product_id']
                product = Product.objects.get(id=product_id)
                
                # Create dispatch item
                dispatch_item = SalesDispatchItem(
                    dispatch=dispatch,
                    product=product,
                    quantity=quantity,
                    unit_price=product.selling_price
                )
                dispatch_item.save()
                
                total_units += quantity
                expected_revenue += dispatch_item.line_total
                
                # Deduct from stock via Production service
                stock_result = ProductionService.deduct_dispatch_from_stock(
                    product_id=product_id,
                    quantity=quantity,
                    dispatch_id=dispatch.id,
                    user=user
                )
                
                if not stock_result.get('success'):
                    raise ValueError(
                        f"Stock deduction failed for {product.name}: "
                        f"{stock_result.get('error', 'Unknown error')}"
                    )
            
            # Step 6: Deduct crates if any (future: integrate with Inventory)
            # For now, just track the number on the dispatch
            
            result['success'] = True
            result['data'] = {
                'dispatch': dispatch,
                'dispatch_number': dispatch.dispatch_number,
                'salesperson_name': salesperson.get_display_name(),
                'total_units': total_units,
                'expected_revenue': expected_revenue,
                'crates_dispatched': crates
            }
            
            return dispatch, result
            
        except ValueError as e:
            result['errors'].append(str(e))
            return None, result
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error creating dispatch: {e}")
            result['errors'].append(f"An unexpected error occurred: {str(e)}")
            return None, result


# ============================================================================
# RETURN SERVICE
# ============================================================================

class ReturnService:
    """
    Service for processing returns with full accountability.
    
    Enforces:
    - qty_sold + qty_returned == qty_dispatched (per product)
    - crates_returned + crates_lost + crates_damaged == crates_dispatched
    """
    
    @staticmethod
    def validate_return_request(
        dispatch_id: int,
        items: List[Dict],
        crates_returned: int,
        crates_lost: int,
        crates_damaged: int,
        commission_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Pre-transaction validation for return processing.
        
        Args:
            dispatch_id: ID of the SalesDispatch
            items: List of {'product_id': int, 'qty_sold': int, 'qty_returned': int}
            crates_returned: Crates returned in good condition
            crates_lost: Crates lost
            crates_damaged: Crates returned damaged
            commission_amount: Optional commission amount
        
        Returns:
            dict with 'valid', 'errors' keys
        """
        errors = []
        
        # Get dispatch
        try:
            dispatch = SalesDispatch.objects.prefetch_related('items').get(id=dispatch_id)
        except SalesDispatch.DoesNotExist:
            errors.append("Dispatch not found.")
            return {'valid': False, 'errors': errors}
        
        # Check not already returned
        if dispatch.is_returned:
            errors.append("This dispatch has already been returned.")
            return {'valid': False, 'errors': errors}
        
        # Validate product accountability
        dispatch_items_map = {di.product_id: di for di in dispatch.items.all()}
        total_revenue = Decimal('0.00')
        
        for item in items:
            product_id = item['product_id']
            qty_sold = item.get('qty_sold', 0)
            qty_returned = item.get('qty_returned', 0)
            
            dispatch_item = dispatch_items_map.get(product_id)
            if not dispatch_item:
                errors.append(f"Product ID {product_id} not found in dispatch.")
                continue
            
            total = qty_sold + qty_returned
            if total != dispatch_item.quantity:
                errors.append(
                    f"{dispatch_item.product.name}: "
                    f"sold ({qty_sold}) + returned ({qty_returned}) = {total} "
                    f"≠ dispatched ({dispatch_item.quantity})"
                )
            
            # Calculate revenue for commission validation
            total_revenue += Decimal(str(qty_sold)) * dispatch_item.unit_price
        
        # Validate crate accountability
        crates_total = crates_returned + crates_lost + crates_damaged
        if crates_total != dispatch.crates_dispatched:
            errors.append(
                f"Crate accountability error: "
                f"returned ({crates_returned}) + lost ({crates_lost}) + "
                f"damaged ({crates_damaged}) = {crates_total} "
                f"≠ dispatched ({dispatch.crates_dispatched})"
            )
        
        # Validate commission if provided
        if commission_amount is not None and commission_amount > 0:
            max_commission = total_revenue * COMMISSION_MAX_PERCENTAGE
            if commission_amount > max_commission:
                errors.append(
                    f"Commission ({commission_amount}) exceeds maximum allowed "
                    f"(20% of revenue = {max_commission})"
                )
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'total_revenue': total_revenue
        }
    
    @classmethod
    @transaction.atomic
    def process_return(
        cls,
        dispatch_id: int,
        items: List[Dict],
        crates_returned: int,
        crates_lost: int,
        crates_damaged: int,
        notes: str,
        commission_amount: Optional[Decimal],
        user
    ) -> Tuple[Optional[SalesReturn], Dict[str, Any]]:
        """
        Process a return with full ACID compliance.
        
        Args:
            dispatch_id: ID of the SalesDispatch
            items: List of {'product_id': int, 'qty_sold': int, 'qty_returned': int}
            crates_returned: Crates returned in good condition
            crates_lost: Crates lost
            crates_damaged: Crates returned damaged
            notes: Optional notes
            commission_amount: Optional commission amount (NULL if disabled)
            user: User processing the return
        
        Returns:
            Tuple of (SalesReturn or None, result dict)
        """
        result = {'success': False, 'errors': []}
        
        try:
            # Step 1: Validate request
            validation = cls.validate_return_request(
                dispatch_id, items, crates_returned, crates_lost,
                crates_damaged, commission_amount
            )
            
            if not validation['valid']:
                result['errors'] = validation['errors']
                return None, result
            
            # Step 2: Lock dispatch
            dispatch = SalesDispatch.objects.select_for_update().get(id=dispatch_id)
            
            # Re-verify not already returned
            if dispatch.is_returned:
                result['errors'].append("Dispatch already returned.")
                return None, result
            
            # Step 3: Calculate totals
            total_units_sold = 0
            total_revenue = Decimal('0.00')
            
            dispatch_items_map = {di.product_id: di for di in dispatch.items.all()}
            
            for item in items:
                qty_sold = item.get('qty_sold', 0)
                total_units_sold += qty_sold
                dispatch_item = dispatch_items_map[item['product_id']]
                total_revenue += Decimal(str(qty_sold)) * dispatch_item.unit_price
            
            # Step 4: Create SalesReturn
            sales_return = SalesReturn(
                dispatch=dispatch,
                return_date=timezone.now().date(),
                total_units_sold=total_units_sold,
                total_revenue=total_revenue,
                crates_returned=crates_returned,
                crates_lost=crates_lost,
                crates_damaged=crates_damaged,
                commission_amount=commission_amount,
                notes=notes,
                created_by=user
            )
            sales_return.save()
            
            # Step 5: Create return items and restore stock for returned products
            for item in items:
                product_id = item['product_id']
                qty_sold = item.get('qty_sold', 0)
                qty_returned = item.get('qty_returned', 0)
                
                dispatch_item = dispatch_items_map[product_id]
                
                # Create return item
                return_item = SalesReturnItem(
                    sales_return=sales_return,
                    product_id=product_id,
                    qty_dispatched=dispatch_item.quantity,
                    qty_sold=qty_sold,
                    qty_returned=qty_returned,
                    unit_price=dispatch_item.unit_price
                )
                return_item.save()
                
                # Restore stock for returned units
                if qty_returned > 0:
                    stock_result = ProductionService.add_return_to_stock(
                        product_id=product_id,
                        quantity=qty_returned,
                        return_id=sales_return.id,
                        user=user
                    )
                    
                    if not stock_result.get('success'):
                        raise ValueError(
                            f"Stock restoration failed for {dispatch_item.product.name}: "
                            f"{stock_result.get('error', 'Unknown error')}"
                        )
            
            # Step 6: Return only good crates to inventory (future)
            # For now, just recorded on the return record
            
            # Step 7: Mark dispatch as returned
            dispatch.is_returned = True
            dispatch.returned_at = timezone.now()
            dispatch.status = SalesDispatch.Status.RETURNED
            dispatch.save()
            
            result['success'] = True
            result['data'] = {
                'sales_return': sales_return,
                'dispatch_number': dispatch.dispatch_number,
                'salesperson_name': dispatch.salesperson.get_display_name(),
                'total_units_sold': total_units_sold,
                'total_revenue': total_revenue,
                'commission_amount': commission_amount
            }
            
            return sales_return, result
            
        except ValueError as e:
            result['errors'].append(str(e))
            return None, result
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error processing return: {e}")
            result['errors'].append(f"An unexpected error occurred: {str(e)}")
            return None, result


# ============================================================================
# COMMISSION SERVICE
# ============================================================================

class CommissionService:
    """
    Read-only service for commission reporting.
    Commission amounts are manually entered by Accountant during return processing.
    """
    
    @staticmethod
    def get_max_commission(total_revenue: Decimal) -> Decimal:
        """
        Calculate maximum allowed commission (20% of revenue).
        
        Args:
            total_revenue: Total sales revenue
        
        Returns:
            Maximum commission amount
        """
        return total_revenue * COMMISSION_MAX_PERCENTAGE
    
    @staticmethod
    def get_monthly_report(year: int, month: int) -> Dict[str, Any]:
        """
        Get monthly commission report by salesperson.
        
        Args:
            year: Year
            month: Month (1-12)
        
        Returns:
            dict with commission data by salesperson
        """
        from django.db.models import Sum, Count
        from datetime import date
        
        # Get all returns for the month
        returns = SalesReturn.objects.filter(
            return_date__year=year,
            return_date__month=month
        ).select_related('dispatch__salesperson')
        
        # Aggregate by salesperson
        summary = returns.values(
            'dispatch__salesperson__id',
            'dispatch__salesperson__first_name',
            'dispatch__salesperson__last_name'
        ).annotate(
            total_returns=Count('id'),
            total_revenue=Sum('total_revenue'),
            total_commission=Sum('commission_amount')
        ).order_by('dispatch__salesperson__first_name')
        
        # Calculate totals
        grand_total_revenue = Decimal('0.00')
        grand_total_commission = Decimal('0.00')
        
        salespeople = []
        for row in summary:
            revenue = row['total_revenue'] or Decimal('0.00')
            commission = row['total_commission'] or Decimal('0.00')
            
            grand_total_revenue += revenue
            grand_total_commission += commission
            
            salespeople.append({
                'id': row['dispatch__salesperson__id'],
                'name': f"{row['dispatch__salesperson__first_name']} {row['dispatch__salesperson__last_name']}",
                'total_returns': row['total_returns'],
                'total_revenue': revenue,
                'total_commission': commission
            })
        
        return {
            'year': year,
            'month': month,
            'salespeople': salespeople,
            'grand_total_revenue': grand_total_revenue,
            'grand_total_commission': grand_total_commission
        }


# ============================================================================
# SALES REPORT SERVICE
# ============================================================================

class SalesReportService:
    """
    Service for sales reporting and analytics.
    """
    
    @staticmethod
    def get_sales_report(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        salesperson_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get sales report for date range.
        
        Args:
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)
            salesperson_id: Filter by salesperson (optional)
        
        Returns:
            dict with sales data and summary
        """
        from django.db.models import Sum, Count
        from datetime import timedelta
        
        if end_date is None:
            end_date = timezone.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        # Base queryset
        queryset = SalesReturn.objects.filter(
            return_date__gte=start_date,
            return_date__lte=end_date
        ).select_related('dispatch__salesperson')
        
        if salesperson_id:
            queryset = queryset.filter(dispatch__salesperson_id=salesperson_id)
        
        # Get summary
        summary = queryset.aggregate(
            total_returns=Count('id'),
            total_units=Sum('total_units_sold'),
            total_revenue=Sum('total_revenue')
        )
        
        # Get sales list
        sales = queryset.order_by('-return_date').values(
            'id',
            'return_date',
            'dispatch__dispatch_number',
            'dispatch__salesperson__first_name',
            'dispatch__salesperson__last_name',
            'total_units_sold',
            'total_revenue'
        )
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'sales': list(sales),
            'summary': {
                'total_returns': summary['total_returns'] or 0,
                'total_units': summary['total_units'] or 0,
                'total_revenue': summary['total_revenue'] or Decimal('0.00')
            }
        }
    
    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """
        Get stats for sales dashboard.
        
        Returns:
            dict with today's stats and pending dispatches
        """
        from django.db.models import Sum, Count
        
        today = timezone.now().date()
        
        # Today's dispatches
        today_dispatches = SalesDispatch.objects.filter(
            dispatch_date=today
        ).count()
        
        # Pending returns (dispatched but not returned)
        pending_returns = SalesDispatch.objects.filter(
            is_returned=False
        ).count()
        
        # Today's returns
        today_returns = SalesReturn.objects.filter(
            return_date=today
        ).aggregate(
            count=Count('id'),
            revenue=Sum('total_revenue')
        )
        
        return {
            'today_dispatches': today_dispatches,
            'pending_returns': pending_returns,
            'today_returns_count': today_returns['count'] or 0,
            'today_revenue': today_returns['revenue'] or Decimal('0.00')
        }
