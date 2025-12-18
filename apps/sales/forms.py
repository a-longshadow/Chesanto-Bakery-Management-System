"""
Sales App - Forms

Forms for dispatch creation and return processing.
"""

from decimal import Decimal
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.products.models import Product
from .services import COMMISSION_MAX_PERCENTAGE

User = get_user_model()


class DispatchForm(forms.Form):
    """
    Form for creating a dispatch.
    
    Products are added dynamically via __init__.
    """
    
    salesperson = forms.ModelChoiceField(
        queryset=User.objects.filter(role='SALESMAN', is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Select salesperson (User with role=SALESMAN)",
        empty_label="-- Select Salesperson --"
    )
    
    dispatch_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'readonly': 'readonly'  # Prevent manual date entry - must be today
        }),
        help_text="Dispatches can only be created for today's date."
    )
    
    crates = forms.IntegerField(
        min_value=0,
        initial=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0'
        })
    )
    
    def __init__(self, *args, products=None, **kwargs):
        """
        Initialize form with dynamic product quantity fields.
        
        Args:
            products: List of dicts with product info and stock levels
        """
        super().__init__(*args, **kwargs)
        
        # Store products for validation
        self.products = products or []
        
        # Dynamically add product quantity fields
        for product in self.products:
            field_name = f"qty_{product['id']}"
            self.fields[field_name] = forms.IntegerField(
                min_value=0,
                initial=0,
                required=False,
                label=product['name'],
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'min': '0',
                    'max': str(product['current_stock']),
                    'data-stock': str(product['current_stock']),
                    'data-price': str(product['selling_price']),
                    'data-product-id': str(product['id'])
                })
            )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Ensure at least one product has quantity
        has_products = False
        for key, value in cleaned_data.items():
            if key.startswith('qty_') and value and value > 0:
                has_products = True
                break
        
        if not has_products:
            raise ValidationError("At least one product must be dispatched.")
        
        return cleaned_data
    
    def get_items(self):
        """
        Extract product items from cleaned data.
        
        Returns:
            List of {'product_id': int, 'quantity': int}
        """
        items = []
        for product in self.products:
            field_name = f"qty_{product['id']}"
            quantity = self.cleaned_data.get(field_name, 0) or 0
            if quantity > 0:
                items.append({
                    'product_id': product['id'],
                    'quantity': quantity
                })
        return items


class ReturnForm(forms.Form):
    """
    Form for processing returns.
    
    Accountant enters sold/returned quantities per product.
    Enforces: sold + returned == dispatched
    """
    
    crates_returned = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0'
        })
    )
    
    crates_lost = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0'
        })
    )
    
    crates_damaged = forms.IntegerField(
        min_value=0,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0'
        })
    )
    
    commission_amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
        initial=Decimal('0'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '0.01',
            'placeholder': 'Enter commission amount'
        }),
        help_text="Manual entry. Max allowed = 20% of total revenue."
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': '2',
            'placeholder': 'Additional notes (optional)'
        })
    )
    
    def __init__(self, *args, dispatch=None, **kwargs):
        """
        Initialize form with dispatch context.
        
        Args:
            dispatch: SalesDispatch object with items
        """
        super().__init__(*args, **kwargs)
        self.dispatch = dispatch
        
        if not dispatch:
            return
        
        # TODO: Check if salesperson has commission enabled
        # For now, keep the field visible for all
        
        # Dynamically add sold/returned fields for each product
        for item in dispatch.items.all():
            # Sold field
            self.fields[f"sold_{item.product_id}"] = forms.IntegerField(
                min_value=0,
                initial=0,
                label=f"{item.product.name} Sold",
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'min': '0',
                    'max': str(item.quantity),
                    'data-dispatched': str(item.quantity),
                    'data-price': str(item.unit_price),
                    'data-product-id': str(item.product_id)
                })
            )
            
            # Returned field
            self.fields[f"returned_{item.product_id}"] = forms.IntegerField(
                min_value=0,
                initial=0,
                label=f"{item.product.name} Returned",
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'min': '0',
                    'max': str(item.quantity),
                    'data-dispatched': str(item.quantity),
                    'data-product-id': str(item.product_id)
                })
            )
    
    def clean(self):
        cleaned_data = super().clean()
        
        if not self.dispatch:
            raise ValidationError("No dispatch context provided.")
        
        errors = []
        total_revenue = Decimal('0.00')
        
        # Validate accountability for each product
        for item in self.dispatch.items.all():
            sold = cleaned_data.get(f"sold_{item.product_id}", 0) or 0
            returned = cleaned_data.get(f"returned_{item.product_id}", 0) or 0
            
            total = sold + returned
            if total != item.quantity:
                errors.append(
                    f"{item.product.name}: sold ({sold}) + returned ({returned}) = {total} "
                    f"≠ dispatched ({item.quantity})"
                )
            
            # Calculate revenue for commission validation
            total_revenue += Decimal(str(sold)) * item.unit_price
        
        if errors:
            raise ValidationError(errors)
        
        # Store total_revenue for commission validation
        cleaned_data['_total_revenue'] = total_revenue
        
        # Validate crates
        crates_returned = cleaned_data.get('crates_returned', 0) or 0
        crates_lost = cleaned_data.get('crates_lost', 0) or 0
        crates_damaged = cleaned_data.get('crates_damaged', 0) or 0
        crates_total = crates_returned + crates_lost + crates_damaged
        
        if crates_total != self.dispatch.crates_dispatched:
            raise ValidationError(
                f"Crates: returned ({crates_returned}) + lost ({crates_lost}) + "
                f"damaged ({crates_damaged}) = {crates_total} "
                f"≠ dispatched ({self.dispatch.crates_dispatched})"
            )
        
        # Validate commission
        commission_amount = cleaned_data.get('commission_amount') or Decimal('0')
        max_commission = total_revenue * COMMISSION_MAX_PERCENTAGE
        
        if commission_amount > max_commission:
            raise ValidationError(
                f"Commission ({commission_amount}) exceeds maximum allowed "
                f"(20% of revenue = {max_commission})"
            )
        
        return cleaned_data
    
    def get_items(self):
        """
        Extract return items from cleaned data.
        
        Returns:
            List of {'product_id': int, 'qty_sold': int, 'qty_returned': int}
        """
        items = []
        for item in self.dispatch.items.all():
            items.append({
                'product_id': item.product_id,
                'qty_sold': self.cleaned_data.get(f"sold_{item.product_id}", 0) or 0,
                'qty_returned': self.cleaned_data.get(f"returned_{item.product_id}", 0) or 0
            })
        return items


class CrateStatusForm(forms.Form):
    """
    Form for updating crate resolution status.
    This is the ONLY mutable action on a SalesReturn.
    """
    
    crates_marked_lost = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check when lost crates issue is resolved"
    )
    
    crates_marked_damaged = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check when damaged crates issue is resolved"
    )
