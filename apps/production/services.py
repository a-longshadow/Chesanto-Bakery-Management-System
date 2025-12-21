"""
Production App - Service Layer

All production business logic with ACID compliance.
Each method follows:
- @transaction.atomic for database integrity
- select_for_update() for row locking where needed
- Comprehensive validation before any writes
- Structured return dicts for consistent API
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any
from datetime import date

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.products.models import Mix, MixIngredient
from apps.inventory.routing import get_details_model
from apps.inventory.utils import deduct_ingredients_atomic
from .models import (
    ProductionBatch,
    BatchIngredientDeduction,
    ProductStock,
    ProductStockMovement
)


# ============================================================================
# CONSTANTS
# ============================================================================

QUANTITY_PRECISION = Decimal('0.001')
PRICE_PRECISION = Decimal('0.01')
COST_PER_UNIT_PRECISION = Decimal('0.0001')


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def round_quantity(value) -> Decimal:
    """Round quantity to 3 decimal places."""
    return Decimal(str(value)).quantize(QUANTITY_PRECISION, rounding=ROUND_HALF_UP)


def round_price(value) -> Decimal:
    """Round price/cost to 2 decimal places."""
    return Decimal(str(value)).quantize(PRICE_PRECISION, rounding=ROUND_HALF_UP)


def round_cost_per_unit(value) -> Decimal:
    """Round cost per unit to 4 decimal places."""
    return Decimal(str(value)).quantize(COST_PER_UNIT_PRECISION, rounding=ROUND_HALF_UP)


# ============================================================================
# PRODUCTION SERVICE
# ============================================================================

class ProductionService:
    """
    Core service for production batch operations.
    
    All methods follow ACID principles:
    - Atomic transactions
    - Consistent state
    - Isolated operations
    - Durable records
    """
    
    @staticmethod
    def generate_batch_number(production_date: date) -> str:
        """
        Generate unique batch number for the given date.
        
        Format: PRD-YYYYMMDD-XXX
        Where XXX is sequential for the day (001, 002, etc.)
        
        Args:
            production_date: Date of production
        
        Returns:
            Unique batch number string
        """
        date_str = production_date.strftime('%Y%m%d')
        prefix = f"PRD-{date_str}-"
        
        # Find highest existing batch number for this date
        last_batch = ProductionBatch.objects.filter(
            batch_number__startswith=prefix
        ).order_by('-batch_number').first()
        
        if last_batch:
            # Extract sequence number and increment
            last_seq = int(last_batch.batch_number.split('-')[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        
        return f"{prefix}{next_seq:03d}"
    
    @staticmethod
    def validate_mix_availability(mix_id: int) -> Dict[str, Any]:
        """
        Validate that a mix exists and is active.
        
        Args:
            mix_id: ID of the mix to validate
        
        Returns:
            dict with validation result and mix data
        
        Raises:
            ValueError: If mix not found or inactive
        """
        try:
            mix = Mix.objects.select_related('product').prefetch_related(
                'ingredients'
            ).get(id=mix_id, is_active=True, product__is_active=True)
        except Mix.DoesNotExist:
            raise ValueError(f"Mix {mix_id} not found or is inactive")
        
        return {
            'mix': mix,
            'product': mix.product,
            'expected_yield': mix.expected_yield,
            'ingredient_count': mix.ingredients.count()
        }
    
    @staticmethod
    def check_ingredient_availability(mix: Mix) -> Dict[str, Any]:
        """
        Check if all ingredients are available in sufficient quantity.
        
        Args:
            mix: Mix object with prefetched ingredients
        
        Returns:
            dict with:
            - available: bool
            - ingredients: list with availability details
            - shortages: list of ingredients with insufficient stock
        """
        ingredients_status = []
        shortages = []
        
        for mi in mix.ingredients.all():
            try:
                DetailsModel = get_details_model(mi.inventory_item_id)
                details = DetailsModel.objects.get(pk=1)
                
                available = details.current_stock >= mi.quantity_required
                
                status = {
                    'inventory_item_id': mi.inventory_item_id,
                    'item_name': details.name,
                    'required': mi.quantity_required,
                    'available': details.current_stock,
                    'unit': mi.unit_of_measure or details.unit,
                    'sufficient': available,
                    'unit_price': details.last_purchase_unit_price
                }
                ingredients_status.append(status)
                
                if not available:
                    shortages.append({
                        'item_name': details.name,
                        'required': mi.quantity_required,
                        'available': details.current_stock,
                        'shortage': mi.quantity_required - details.current_stock,
                        'unit': mi.unit_of_measure or details.unit
                    })
            except Exception as e:
                shortages.append({
                    'item_name': f"Item {mi.inventory_item_id}",
                    'error': str(e)
                })
        
        return {
            'available': len(shortages) == 0,
            'ingredients': ingredients_status,
            'shortages': shortages
        }
    
    @staticmethod
    def build_mix_snapshot(mix: Mix, ingredients_status: List[Dict]) -> Dict[str, Any]:
        """
        Build complete mix snapshot with current prices.
        
        Args:
            mix: Mix object
            ingredients_status: Output from check_ingredient_availability
        
        Returns:
            Complete snapshot dict for ProductionBatch.mix_snapshot
        """
        ingredients_snapshot = []
        total_cost = Decimal('0.00')
        
        for ing in ingredients_status:
            qty = Decimal(str(ing['required']))
            price = Decimal(str(ing['unit_price']))
            line_cost = round_price(qty * price)
            total_cost += line_cost
            
            ingredients_snapshot.append({
                'inventory_item_id': ing['inventory_item_id'],
                'item_name': ing['item_name'],
                'quantity_required': str(round_quantity(qty)),
                'unit': ing['unit'],
                'unit_price_at_batch': str(round_price(price)),
                'line_cost': str(line_cost)
            })
        
        return {
            'mix_id': mix.id,
            'mix_name': mix.name,
            'expected_yield': int(mix.expected_yield),
            'ingredients': ingredients_snapshot,
            'total_mix_cost': str(round_price(total_cost)),
            'snapshot_timestamp': timezone.now().isoformat()
        }
    
    @classmethod
    @transaction.atomic
    def create_production_batch(
        cls,
        mix_id: int,
        quantity_produced: int,
        production_date: date,
        user,
        production_time=None,
        notes: str = ''
    ) -> Dict[str, Any]:
        """
        Create a production batch with full ACID compliance.
        
        This is the primary entry point for recording production.
        
        Args:
            mix_id: ID of the mix being produced
            quantity_produced: Actual units produced
            production_date: Date of production
            user: User recording the batch
            production_time: Optional time of production
            notes: Optional production notes
        
        Returns:
            dict with:
            - success: bool
            - data: batch details, alerts, stock info
            - error: error message (if failed)
        """
        try:
            # STEP 1: Validate mix
            mix_validation = cls.validate_mix_availability(mix_id)
            mix = mix_validation['mix']
            product = mix_validation['product']
            
            # STEP 2: Check ingredient availability
            availability = cls.check_ingredient_availability(mix)
            
            if not availability['available']:
                return {
                    'success': False,
                    'error': 'Insufficient ingredients',
                    'shortages': availability['shortages']
                }
            
            # STEP 3: Build mix snapshot with prices
            mix_snapshot = cls.build_mix_snapshot(mix, availability['ingredients'])
            total_cost = Decimal(mix_snapshot['total_mix_cost'])
            
            # STEP 4: Generate batch number
            batch_number = cls.generate_batch_number(production_date)
            
            # STEP 5: Calculate cost per unit
            cost_per_unit = round_cost_per_unit(total_cost / Decimal(quantity_produced))
            
            # STEP 6: Create ProductionBatch
            batch = ProductionBatch(
                batch_number=batch_number,
                product=product,
                mix=mix,
                mix_snapshot=mix_snapshot,
                quantity_produced=quantity_produced,
                expected_yield=int(mix.expected_yield),
                total_ingredient_cost=total_cost,
                cost_per_unit=cost_per_unit,
                production_date=production_date,
                production_time=production_time,
                produced_by=user,
                notes=notes
            )
            batch.save(force_insert=True)
            
            # STEP 7: Deduct ingredients from Inventory
            deductions = []
            for ing in mix_snapshot['ingredients']:
                deductions.append({
                    'inventory_item_id': ing['inventory_item_id'],
                    'quantity': Decimal(ing['quantity_required'])
                })
            
            deduction_result = deduct_ingredients_atomic(
                ingredients_list=deductions,
                requested_by_app='production',
                requested_by_user=user
            )
            
            if not deduction_result['success']:
                raise ValidationError(deduction_result.get('error', 'Failed to deduct ingredients'))
            
            # STEP 8: Create BatchIngredientDeduction records
            for ing in mix_snapshot['ingredients']:
                # Get before/after from deduction result
                item_deduction = next(
                    (d for d in deduction_result['data']['items']
                     if d['inventory_item_id'] == ing['inventory_item_id']),
                    None
                )
                
                # Calculate stock_before from new_stock + quantity_deducted
                qty_deducted = Decimal(ing['quantity_required'])
                new_stock = Decimal(item_deduction['new_stock']) if item_deduction else Decimal('0')
                stock_before = new_stock + qty_deducted
                
                BatchIngredientDeduction.objects.create(
                    batch=batch,
                    inventory_item_id=ing['inventory_item_id'],
                    item_name=ing['item_name'],
                    quantity_deducted=qty_deducted,
                    unit=ing['unit'],
                    unit_price_at_deduction=Decimal(ing['unit_price_at_batch']),
                    line_cost=Decimal(ing['line_cost']),
                    stock_before=stock_before,
                    stock_after=new_stock
                )
            
            # STEP 9: Update ProductStock
            stock, created = ProductStock.objects.select_for_update().get_or_create(
                product=product,
                defaults={'current_stock': 0}
            )
            
            stock_before = stock.current_stock
            stock.current_stock += quantity_produced
            stock.last_production_date = production_date
            stock.last_production_batch = batch
            stock.save()
            
            # STEP 10: Create ProductStockMovement
            ProductStockMovement.objects.create(
                product=product,
                movement_type=ProductStockMovement.MovementType.PRODUCTION,
                quantity=quantity_produced,
                stock_before=stock_before,
                stock_after=stock.current_stock,
                reference_type='ProductionBatch',
                reference_id=batch.id,
                recorded_by=user
            )
            
            # STEP 11: Return success with all details
            return {
                'success': True,
                'data': {
                    'batch': batch,
                    'batch_number': batch_number,
                    'product_name': product.name,
                    'quantity_produced': quantity_produced,
                    'expected_yield': int(mix.expected_yield),
                    'yield_variance': quantity_produced - int(mix.expected_yield),
                    'total_cost': total_cost,
                    'cost_per_unit': cost_per_unit,
                    'stock_before': stock_before,
                    'stock_after': stock.current_stock,
                    'stock_alerts': deduction_result.get('alerts', [])
                }
            }
            
        except ValueError as e:
            return {
                'success': False,
                'error': str(e)
            }
        except ValidationError as e:
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f"Error creating production batch: {e}")
            
            return {
                'success': False,
                'error': f'An unexpected error occurred: {str(e)}'
            }
    
    @staticmethod
    def get_production_summary(date_filter: date = None, product_id: int = None) -> Dict[str, Any]:
        """
        Get production summary for dashboard display.
        
        Args:
            date_filter: Filter by date (default: today)
            product_id: Filter by product (optional)
        
        Returns:
            dict with production statistics
        """
        from django.db.models import Sum, Count, Avg
        
        if date_filter is None:
            date_filter = timezone.now().date()
        
        queryset = ProductionBatch.objects.filter(production_date=date_filter)
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        
        stats = queryset.aggregate(
            total_batches=Count('id'),
            total_units=Sum('quantity_produced'),
            total_cost=Sum('total_ingredient_cost'),
            avg_cost_per_unit=Avg('cost_per_unit')
        )
        
        # Get per-product breakdown
        by_product = queryset.values('product__name').annotate(
            batches=Count('id'),
            units=Sum('quantity_produced'),
            cost=Sum('total_ingredient_cost')
        ).order_by('product__name')
        
        return {
            'date': date_filter,
            'totals': stats,
            'by_product': list(by_product)
        }
    
    @staticmethod
    def get_batch_details(batch_id: int) -> Dict[str, Any]:
        """
        Get complete details for a production batch.
        
        Args:
            batch_id: ID of the batch
        
        Returns:
            dict with batch details, deductions, and computed values
        
        Raises:
            ValueError: If batch not found
        """
        try:
            batch = ProductionBatch.objects.select_related(
                'product', 'mix', 'produced_by'
            ).get(id=batch_id)
        except ProductionBatch.DoesNotExist:
            raise ValueError(f"Batch {batch_id} not found")
        
        deductions = BatchIngredientDeduction.objects.filter(
            batch=batch
        ).order_by('inventory_item_id')
        
        return {
            'batch': batch,
            'deductions': list(deductions),
            'yield_variance': batch.yield_variance,
            'yield_variance_percentage': batch.yield_variance_percentage,
            'is_within_acceptable_variance': batch.is_within_acceptable_variance
        }
    
    @staticmethod
    @transaction.atomic
    def deduct_dispatch_from_stock(
        product_id: int,
        quantity: int,
        dispatch_id: int,
        user
    ) -> Dict[str, Any]:
        """
        Deduct dispatched quantity from product stock.
        Called by Sales App when creating a dispatch.
        
        Args:
            product_id: Product being dispatched
            quantity: Units to dispatch
            dispatch_id: ID of the SalesDispatch record
            user: User performing the action
        
        Returns:
            dict with success status and new stock level
        
        Raises:
            ValueError: If insufficient stock
        """
        stock = ProductStock.objects.select_for_update().get(product_id=product_id)
        
        if stock.current_stock < quantity:
            raise ValueError(
                f"Insufficient stock. Available: {stock.current_stock}, "
                f"Requested: {quantity}"
            )
        
        stock_before = stock.current_stock
        stock.current_stock -= quantity
        stock.save()
        
        # Create movement record
        ProductStockMovement.objects.create(
            product_id=product_id,
            movement_type=ProductStockMovement.MovementType.DISPATCH,
            quantity=-quantity,  # Negative for deduction
            stock_before=stock_before,
            stock_after=stock.current_stock,
            reference_type='SalesDispatch',
            reference_id=dispatch_id,
            recorded_by=user
        )
        
        return {
            'success': True,
            'stock_before': stock_before,
            'stock_after': stock.current_stock
        }
    
    @staticmethod
    @transaction.atomic
    def add_return_to_stock(
        product_id: int,
        quantity: int,
        return_id: int,
        user
    ) -> Dict[str, Any]:
        """
        Add returned units back to product stock.
        Called by Sales App when processing returns.
        
        Args:
            product_id: Product being returned
            quantity: Units returned
            return_id: ID of the SalesReturn record
            user: User performing the action
        
        Returns:
            dict with success status and new stock level
        """
        # Use get_or_create to handle Leftovers products that may not have stock records yet
        stock, created = ProductStock.objects.select_for_update().get_or_create(
            product_id=product_id,
            defaults={'current_stock': 0}
        )
        
        stock_before = stock.current_stock
        stock.current_stock += quantity
        stock.save()
        
        ProductStockMovement.objects.create(
            product_id=product_id,
            movement_type=ProductStockMovement.MovementType.RETURN,
            quantity=quantity,  # Positive for addition
            stock_before=stock_before,
            stock_after=stock.current_stock,
            reference_type='SalesReturn',
            reference_id=return_id,
            recorded_by=user
        )
        
        return {
            'success': True,
            'stock_before': stock_before,
            'stock_after': stock.current_stock
        }

    # ========================================================================
    # WASTE DISPOSAL OPERATIONS
    # ========================================================================

    @staticmethod
    def generate_waste_number(disposal_date: date) -> str:
        """
        Generate unique waste number for the given date.
        
        Format: WST-YYYYMMDD-XXX
        Where XXX is sequential for the day (001, 002, etc.)
        
        Args:
            disposal_date: Date of waste disposal
        
        Returns:
            Unique waste number string
        """
        from .models import WasteLog
        
        date_str = disposal_date.strftime('%Y%m%d')
        prefix = f"WST-{date_str}-"
        
        # Find highest existing waste number for this date
        last_waste = WasteLog.objects.filter(
            waste_number__startswith=prefix
        ).order_by('-waste_number').first()
        
        if last_waste:
            # Extract sequence number and increment
            last_seq = int(last_waste.waste_number.split('-')[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        
        return f"{prefix}{next_seq:03d}"

    @staticmethod
    @transaction.atomic
    def dispose_waste(
        product_id: int,
        quantity: int,
        source: str,
        reason: str,
        disposal_date: date,
        user,
        notes: str = ''
    ) -> Dict[str, Any]:
        """
        Dispose of waste from ProductStock with full audit trail.
        
        Creates immutable WasteLog record for P&L tracking and
        deducts from ProductStock with WASTE movement type.
        
        Args:
            product_id: ID of the product being disposed
            quantity: Units to dispose (positive integer)
            source: WasteLog.Source choice (SALES_RETURN or BAKERY_STOCK)
            reason: Brief reason for disposal
            disposal_date: Date of disposal
            user: User performing the disposal
            notes: Optional additional notes
        
        Returns:
            dict with success status and waste record details
        
        Raises:
            ValueError: If validation fails
        """
        from .models import WasteLog
        from apps.products.models import Product
        
        # Validate quantity
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Validate source
        valid_sources = [choice[0] for choice in WasteLog.Source.choices]
        if source not in valid_sources:
            raise ValueError(f"Invalid source. Must be one of: {valid_sources}")
        
        # Get product with lock
        try:
            product = Product.objects.select_for_update().get(id=product_id)
        except Product.DoesNotExist:
            raise ValueError(f"Product with ID {product_id} not found")
        
        # Get stock with lock
        stock, _ = ProductStock.objects.select_for_update().get_or_create(
            product=product,
            defaults={'current_stock': 0}
        )
        
        # Validate sufficient stock
        if stock.current_stock < quantity:
            raise ValueError(
                f"Insufficient stock. Available: {stock.current_stock}, "
                f"Requested: {quantity}"
            )
        
        # Determine unit value (use product's selling price)
        unit_value = round_price(product.selling_price) if product.selling_price else Decimal('0.00')
        total_value = round_price(unit_value * quantity)
        
        # Generate waste number
        waste_number = ProductionService.generate_waste_number(disposal_date)
        
        # Deduct from stock
        stock_before = stock.current_stock
        stock.current_stock -= quantity
        stock.save()
        
        # Create immutable WasteLog record
        waste_log = WasteLog.objects.create(
            waste_number=waste_number,
            product=product,
            quantity=quantity,
            unit_value=unit_value,
            total_value=total_value,
            source=source,
            reason=reason,
            notes=notes,
            disposal_date=disposal_date,
            disposed_by=user
        )
        
        # Create stock movement record
        ProductStockMovement.objects.create(
            product=product,
            movement_type=ProductStockMovement.MovementType.WASTE,
            quantity=-quantity,  # Negative for deduction
            stock_before=stock_before,
            stock_after=stock.current_stock,
            reference_type='WasteLog',
            reference_id=waste_log.id,
            recorded_by=user
        )
        
        return {
            'success': True,
            'waste_number': waste_number,
            'product_name': product.name,
            'quantity': quantity,
            'unit_value': str(unit_value),
            'total_value': str(total_value),
            'stock_before': stock_before,
            'stock_after': stock.current_stock
        }