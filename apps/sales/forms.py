"""
Sales Forms for Chesanto Bakery Management System
Handles dispatch creation, sales returns, and related forms
"""
from django import forms
from django.forms import inlineformset_factory
from .models import Dispatch, DispatchItem, SalesReturn, SalesReturnItem
from apps.products.models import Product
from apps.accounts.models import User


class DispatchForm(forms.ModelForm):
    """
    Form for creating/editing dispatches
    """
    class Meta:
        model = Dispatch
        fields = ['salesperson', 'date', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'salesperson': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter salespersons only
        self.fields['salesperson'].queryset = User.objects.filter(
            role='SALESPERSON',
            is_active=True
        )


class DispatchItemForm(forms.ModelForm):
    """
    Form for adding products to a dispatch
    """
    class Meta:
        model = DispatchItem
        fields = ['product', 'quantity', 'expected_revenue']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1'
            }),
            'expected_revenue': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Auto-calculated'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only active products
        self.fields['product'].queryset = Product.objects.filter(is_active=True)


# Formset for multiple dispatch items
DispatchItemFormSet = inlineformset_factory(
    Dispatch,
    DispatchItem,
    form=DispatchItemForm,
    extra=3,  # Show 3 empty forms by default
    can_delete=True,
    min_num=1,  # Require at least one item
    validate_min=True
)


class SalesReturnForm(forms.ModelForm):
    """
    Form for recording sales returns
    """
    class Meta:
        model = SalesReturn
        fields = [
            'actual_revenue',
            'revenue_deficit',
            'crates_returned',
            'crate_deficit',
            'commission_per_unit',
            'commission_bonus',
            'notes'
        ]
        widgets = {
            'actual_revenue': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Total revenue collected'
            }),
            'revenue_deficit': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-calculated'
            }),
            'crates_returned': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
            'crate_deficit': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-calculated'
            }),
            'commission_per_unit': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-calculated'
            }),
            'commission_bonus': forms.NumberInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': 'Auto-calculated'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notes about returns, damages, etc.'
            }),
        }


class SalesReturnItemForm(forms.ModelForm):
    """
    Form for recording individual product returns
    """
    class Meta:
        model = SalesReturnItem
        fields = ['product', 'quantity_sold', 'quantity_returned', 'quantity_damaged']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity_sold': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1'
            }),
            'quantity_returned': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': 'Unsold items'
            }),
            'quantity_damaged': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': 'Damaged items'
            }),
        }


# Formset for sales return items
SalesReturnItemFormSet = inlineformset_factory(
    SalesReturn,
    SalesReturnItem,
    form=SalesReturnItemForm,
    extra=0,  # Will be pre-populated from dispatch items
    can_delete=False,
    min_num=1,
    validate_min=True
)
