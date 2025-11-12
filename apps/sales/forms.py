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
        fields = ['salesperson', 'date']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'salesperson': forms.Select(attrs={'class': 'form-control'}),
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


class SalesReconciliationForm(forms.ModelForm):
    """
    Form for sales reconciliation phase
    Records cash collected and product-level sales breakdown
    """
    class Meta:
        model = SalesReturn
        fields = ['return_date', 'return_time', 'cash_returned']
        widgets = {
            'return_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'return_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),
            'cash_returned': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Total cash collected from customers'
            }),
        }


class SalesReturnItemForm(forms.ModelForm):
    """
    Form for recording individual product returns in sales reconciliation
    """
    class Meta:
        model = SalesReturnItem
        fields = ['units_returned', 'units_damaged']
        widgets = {
            'units_returned': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': 'Unsold items'
            }),
            'units_damaged': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': 'Damaged items'
            }),
        }


class CrateReturnForm(forms.ModelForm):
    """
    Form for crate return phase
    Records crate returns and conditions
    """
    class Meta:
        model = SalesReturn
        fields = []  # No direct fields, handled through items
        
    # We'll add dynamic fields for each product in the view


class CrateReturnItemForm(forms.ModelForm):
    """
    Form for recording crate returns for each product
    """
    class Meta:
        model = SalesReturnItem
        fields = ['crates_returned', 'crate_condition']
        widgets = {
            'crates_returned': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': 'Number of crates'
            }),
            'crate_condition': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
