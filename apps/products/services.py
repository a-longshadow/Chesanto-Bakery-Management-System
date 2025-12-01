"""
Products App - Service Layer
Business logic for Product and Mix operations with ACID compliance.

All service methods use:
- @transaction.atomic for atomicity
- select_for_update() for row-level locking where needed
- Comprehensive validation before database operations
"""
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Product, Mix, MixIngredient


class ProductService:
    """Business logic for Product operations"""
    
    @staticmethod
    @transaction.atomic
    def create_product(
        name: str,
        selling_price: Decimal,
        created_by,
        parent_product_id: int = None,
        description: str = ""
    ) -> Product:
        """
        Create a new product with validation.
        
        Args:
            name: Product name (must be unique)
            selling_price: Price per unit in KES
            created_by: User creating the product
            parent_product_id: Optional parent for sub-products
            description: Optional description
        
        Returns:
            Created Product instance
        
        Raises:
            ValidationError: If name already exists or parent invalid
        """
        # Validate unique name
        if Product.objects.filter(name__iexact=name).exists():
            raise ValidationError(f"Product '{name}' already exists.")
        
        # Validate price
        if selling_price <= 0:
            raise ValidationError("Selling price must be positive.")
        
        # Validate parent if provided
        parent = None
        if parent_product_id:
            try:
                parent = Product.objects.get(id=parent_product_id, is_active=True)
            except Product.DoesNotExist:
                raise ValidationError(f"Parent product {parent_product_id} not found or inactive.")
        
        product = Product.objects.create(
            name=name,
            selling_price=selling_price,
            parent_product=parent,
            description=description,
            created_by=created_by
        )
        
        return product
    
    @staticmethod
    @transaction.atomic
    def update_product(
        product_id: int,
        updated_by,
        name: str = None,
        selling_price: Decimal = None,
        description: str = None,
        parent_product_id: int = None
    ) -> Product:
        """
        Update product details.
        
        Args:
            product_id: ID of product to update
            updated_by: User making the update
            name: New name (optional)
            selling_price: New price (optional)
            description: New description (optional)
            parent_product_id: New parent ID (optional, use -1 to remove parent)
        
        Returns:
            Updated Product instance
        """
        product = Product.objects.select_for_update().get(id=product_id)
        
        if name is not None and name != product.name:
            if Product.objects.filter(name__iexact=name).exclude(id=product_id).exists():
                raise ValidationError(f"Product '{name}' already exists.")
            product.name = name
        
        if selling_price is not None:
            if selling_price <= 0:
                raise ValidationError("Selling price must be positive.")
            product.selling_price = selling_price
        
        if description is not None:
            product.description = description
        
        if parent_product_id is not None:
            if parent_product_id == -1:
                product.parent_product = None
            else:
                try:
                    parent = Product.objects.get(id=parent_product_id, is_active=True)
                    if parent.id == product.id:
                        raise ValidationError("Product cannot be its own parent.")
                    product.parent_product = parent
                except Product.DoesNotExist:
                    raise ValidationError(f"Parent product {parent_product_id} not found or inactive.")
        
        product.updated_by = updated_by
        product.save()
        
        return product
    
    @staticmethod
    @transaction.atomic
    def update_price(product_id: int, new_price: Decimal, updated_by) -> Product:
        """
        Update product selling price with audit trail.
        
        Args:
            product_id: ID of product to update
            new_price: New selling price in KES
            updated_by: User making the update
        
        Returns:
            Updated Product instance
        """
        product = Product.objects.select_for_update().get(id=product_id)
        
        if new_price <= 0:
            raise ValidationError("Price must be positive.")
        
        old_price = product.selling_price
        product.selling_price = new_price
        product.updated_by = updated_by
        product.save()
        
        # TODO: Add audit log when audit app is ready
        # AuditLog.log_price_change(product, old_price, new_price, updated_by)
        
        return product
    
    @staticmethod
    @transaction.atomic
    def archive_product(product_id: int, archived_by) -> Product:
        """
        Soft delete a product (and its active mixes).
        
        Args:
            product_id: ID of product to archive
            archived_by: User archiving the product
        
        Returns:
            Archived Product instance
        
        Note: Does NOT affect historical production/sales records.
        """
        product = Product.objects.select_for_update().get(id=product_id)
        
        # Archive all active mixes for this product
        active_mixes = product.mixes.filter(is_active=True)
        for mix in active_mixes:
            mix.archive(archived_by)
        
        product.archive(archived_by)
        return product
    
    @staticmethod
    @transaction.atomic
    def restore_product(product_id: int, restored_by) -> Product:
        """
        Restore an archived product.
        
        Args:
            product_id: ID of product to restore
            restored_by: User restoring the product
        
        Returns:
            Restored Product instance
        
        Note: Does NOT automatically restore mixes - they must be restored separately.
        """
        product = Product.objects.select_for_update().get(id=product_id)
        product.restore(restored_by)
        return product
    
    @staticmethod
    def get_active_products():
        """Get all active products with related data"""
        return Product.objects.filter(
            is_active=True
        ).select_related(
            'parent_product'
        ).prefetch_related(
            'mixes'
        ).order_by('name')
    
    @staticmethod
    def get_main_products():
        """Get only main products (no sub-products)"""
        return Product.objects.filter(
            is_active=True,
            parent_product__isnull=True
        ).prefetch_related('mixes').order_by('name')
    
    @staticmethod
    def get_product_for_production(product_id: int) -> dict:
        """
        Get product data formatted for Production app.
        Returns dict (not model instance) for loose coupling.
        
        Returns:
            {
                'success': True/False,
                'data': {...} or 'error': '...'
            }
        """
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            mix = product.mixes.filter(is_active=True).prefetch_related('ingredients').first()
            
            if not mix:
                return {'success': False, 'error': f'No active mix for product {product.name}'}
            
            return {
                'success': True,
                'data': {
                    'product_id': product.id,
                    'product_name': product.name,
                    'selling_price': str(product.selling_price),
                    **mix.get_snapshot_data()
                }
            }
        except Product.DoesNotExist:
            return {'success': False, 'error': f'Product {product_id} not found or inactive'}


class MixService:
    """Business logic for Mix/Recipe operations"""
    
    @staticmethod
    @transaction.atomic
    def create_mix_with_ingredients(
        product_id: int,
        name: str,
        expected_yield: Decimal,
        is_fixed_yield: bool,
        ingredients: list,
        created_by,
        yield_variance_min: Decimal = None,
        yield_variance_max: Decimal = None,
        notes: str = ""
    ) -> Mix:
        """
        Create a mix with its ingredients atomically.
        
        Args:
            product_id: ID of product this mix is for
            name: Mix/recipe name
            expected_yield: Expected units produced per mix
            is_fixed_yield: True for machine-weighed, False for variable
            ingredients: List of dicts with keys:
                - inventory_item_id (int 1-23)
                - quantity_required (Decimal)
                - unit_of_measure (str)
                - notes (str, optional)
            created_by: User creating the mix
            yield_variance_min: Min yield for variable products
            yield_variance_max: Max yield for variable products
            notes: Optional recipe notes
        
        Returns:
            Created Mix instance
        
        Raises:
            ValidationError: If product already has active mix or invalid ingredients
        """
        # Get and validate product
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise ValidationError(f"Product {product_id} not found or inactive.")
        
        # Check for existing active mix
        if product.mixes.filter(is_active=True).exists():
            raise ValidationError(
                f"Product '{product.name}' already has an active mix. "
                "Archive it first before creating a new one."
            )
        
        # Validate variable yield settings
        if not is_fixed_yield:
            if not yield_variance_min or not yield_variance_max:
                raise ValidationError(
                    "Variable yield products must have min and max variance values."
                )
            if yield_variance_min >= yield_variance_max:
                raise ValidationError(
                    "Minimum variance must be less than maximum variance."
                )
        
        # Validate all ingredients
        if not ingredients:
            raise ValidationError("A mix must have at least one ingredient.")
        
        for ing in ingredients:
            item_id = ing.get('inventory_item_id')
            if not isinstance(item_id, int) or not 1 <= item_id <= 23:
                raise ValidationError(
                    f"Invalid inventory_item_id: {item_id}. Must be integer 1-23."
                )
            
            qty = ing.get('quantity_required')
            if qty is None or Decimal(str(qty)) <= 0:
                raise ValidationError(
                    f"Invalid quantity for item {item_id}. Must be positive."
                )
        
        # Create mix
        mix = Mix.objects.create(
            product=product,
            name=name,
            expected_yield=expected_yield,
            is_fixed_yield=is_fixed_yield,
            yield_variance_min=yield_variance_min if not is_fixed_yield else None,
            yield_variance_max=yield_variance_max if not is_fixed_yield else None,
            notes=notes,
            created_by=created_by
        )
        
        # Create ingredients
        mix_ingredients = [
            MixIngredient(
                mix=mix,
                inventory_item_id=ing['inventory_item_id'],
                quantity_required=Decimal(str(ing['quantity_required'])),
                unit_of_measure=ing['unit_of_measure'],
                notes=ing.get('notes', '')
            )
            for ing in ingredients
        ]
        MixIngredient.objects.bulk_create(mix_ingredients)
        
        return mix
    
    @staticmethod
    @transaction.atomic
    def update_mix(
        mix_id: int,
        updated_by,
        name: str = None,
        expected_yield: Decimal = None,
        is_fixed_yield: bool = None,
        yield_variance_min: Decimal = None,
        yield_variance_max: Decimal = None,
        notes: str = None
    ) -> Mix:
        """
        Update mix settings (not ingredients).
        
        Use update_mix_ingredients() to change ingredients.
        """
        mix = Mix.objects.select_for_update().get(id=mix_id)
        
        if name is not None:
            mix.name = name
        
        if expected_yield is not None:
            if expected_yield <= 0:
                raise ValidationError("Expected yield must be positive.")
            mix.expected_yield = expected_yield
        
        if is_fixed_yield is not None:
            mix.is_fixed_yield = is_fixed_yield
            if is_fixed_yield:
                mix.yield_variance_min = None
                mix.yield_variance_max = None
        
        if yield_variance_min is not None:
            mix.yield_variance_min = yield_variance_min
        
        if yield_variance_max is not None:
            mix.yield_variance_max = yield_variance_max
        
        if notes is not None:
            mix.notes = notes
        
        # Validate variable yield settings
        if not mix.is_fixed_yield:
            if not mix.yield_variance_min or not mix.yield_variance_max:
                raise ValidationError(
                    "Variable yield products must have min and max variance values."
                )
            if mix.yield_variance_min >= mix.yield_variance_max:
                raise ValidationError(
                    "Minimum variance must be less than maximum variance."
                )
        
        mix.updated_by = updated_by
        mix.save()
        
        return mix
    
    @staticmethod
    @transaction.atomic
    def update_mix_ingredients(mix_id: int, ingredients: list, updated_by) -> Mix:
        """
        Update mix ingredients (replace all).
        
        Args:
            mix_id: ID of mix to update
            ingredients: List of dicts with keys:
                - inventory_item_id (int 1-23)
                - quantity_required (Decimal)
                - unit_of_measure (str)
                - notes (str, optional)
            updated_by: User making the update
        
        Returns:
            Updated Mix instance
        
        Note: Production snapshots mix data at batch creation time,
        so editing mixes is always safe - no blocking needed.
        """
        mix = Mix.objects.select_for_update().get(id=mix_id)
        
        # Validate all ingredients
        if not ingredients:
            raise ValidationError("A mix must have at least one ingredient.")
        
        for ing in ingredients:
            item_id = ing.get('inventory_item_id')
            if not isinstance(item_id, int) or not 1 <= item_id <= 23:
                raise ValidationError(
                    f"Invalid inventory_item_id: {item_id}. Must be integer 1-23."
                )
            
            qty = ing.get('quantity_required')
            if qty is None or Decimal(str(qty)) <= 0:
                raise ValidationError(
                    f"Invalid quantity for item {item_id}. Must be positive."
                )
        
        # Delete existing and create new (replace strategy)
        mix.ingredients.all().delete()
        
        mix_ingredients = [
            MixIngredient(
                mix=mix,
                inventory_item_id=ing['inventory_item_id'],
                quantity_required=Decimal(str(ing['quantity_required'])),
                unit_of_measure=ing['unit_of_measure'],
                notes=ing.get('notes', '')
            )
            for ing in ingredients
        ]
        MixIngredient.objects.bulk_create(mix_ingredients)
        
        mix.updated_by = updated_by
        mix.save()
        
        return mix
    
    @staticmethod
    @transaction.atomic
    def add_ingredient(mix_id: int, ingredient: dict, updated_by) -> MixIngredient:
        """
        Add a single ingredient to a mix.
        
        Args:
            mix_id: ID of mix
            ingredient: Dict with inventory_item_id, quantity_required, unit_of_measure, notes
            updated_by: User making the update
        
        Returns:
            Created MixIngredient instance
        """
        mix = Mix.objects.select_for_update().get(id=mix_id)
        
        item_id = ingredient.get('inventory_item_id')
        if not isinstance(item_id, int) or not 1 <= item_id <= 23:
            raise ValidationError(f"Invalid inventory_item_id: {item_id}. Must be 1-23.")
        
        # Check if ingredient already exists
        if mix.ingredients.filter(inventory_item_id=item_id).exists():
            raise ValidationError(f"Item {item_id} already in this mix.")
        
        mix_ingredient = MixIngredient.objects.create(
            mix=mix,
            inventory_item_id=item_id,
            quantity_required=Decimal(str(ingredient['quantity_required'])),
            unit_of_measure=ingredient['unit_of_measure'],
            notes=ingredient.get('notes', '')
        )
        
        mix.updated_by = updated_by
        mix.save(update_fields=['updated_by', 'updated_at'])
        
        return mix_ingredient
    
    @staticmethod
    @transaction.atomic
    def remove_ingredient(mix_id: int, inventory_item_id: int, updated_by) -> bool:
        """
        Remove an ingredient from a mix.
        
        Returns:
            True if removed, False if not found
        """
        mix = Mix.objects.select_for_update().get(id=mix_id)
        
        # Ensure at least one ingredient remains
        if mix.ingredients.count() <= 1:
            raise ValidationError("Cannot remove the last ingredient. A mix must have at least one.")
        
        deleted, _ = mix.ingredients.filter(inventory_item_id=inventory_item_id).delete()
        
        if deleted:
            mix.updated_by = updated_by
            mix.save(update_fields=['updated_by', 'updated_at'])
        
        return deleted > 0
    
    @staticmethod
    @transaction.atomic
    def archive_mix(mix_id: int, archived_by) -> Mix:
        """Soft delete a mix."""
        mix = Mix.objects.select_for_update().get(id=mix_id)
        mix.archive(archived_by)
        return mix
    
    @staticmethod
    @transaction.atomic
    def restore_mix(mix_id: int, restored_by) -> Mix:
        """
        Restore an archived mix.
        Will fail if product already has another active mix.
        """
        mix = Mix.objects.select_for_update().get(id=mix_id)
        
        if mix.product.mixes.filter(is_active=True).exists():
            raise ValidationError(
                f"Cannot restore: {mix.product.name} already has an active mix."
            )
        
        mix.restore(restored_by)
        return mix
    
    @staticmethod
    def get_active_mix_for_product(product_id: int) -> dict:
        """
        Get active mix data for Production app.
        Returns dict (not model instance) for loose coupling.
        """
        try:
            product = Product.objects.get(id=product_id, is_active=True)
            mix = product.mixes.prefetch_related('ingredients').get(is_active=True)
            
            return {
                'success': True,
                'data': {
                    'product_id': product.id,
                    'product_name': product.name,
                    'selling_price': str(product.selling_price),
                    **mix.get_snapshot_data()
                }
            }
        except Product.DoesNotExist:
            return {'success': False, 'error': f'Product {product_id} not found or inactive'}
        except Mix.DoesNotExist:
            return {'success': False, 'error': f'No active mix for product {product_id}'}
