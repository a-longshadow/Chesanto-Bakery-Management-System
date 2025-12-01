"""
Inventory App - Forms
Forms for purchase recording and output creation.
"""
from datetime import date, timedelta
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .routing import (
    INVENTORY_ITEMS,
    get_items_for_dropdown,
    is_indirect_cost,
)


class PurchaseForm(forms.Form):
    """Form for recording a new purchase"""
    
    inventory_item_id = forms.ChoiceField(
        label='Inventory Item',
        help_text='Select the item being purchased'
    )
    supplier_name = forms.CharField(
        label='Supplier Name',
        max_length=200,
        required=False,
        help_text='Optional: Name of the vendor/supplier'
    )
    quantity_purchased = forms.DecimalField(
        label='Quantity',
        max_digits=10,
        decimal_places=4,
        min_value=Decimal('0.0001'),
        help_text='Amount purchased in standard units'
    )
    unit_price = forms.DecimalField(
        label='Unit Price (KES)',
        max_digits=10,
        decimal_places=4,
        min_value=Decimal('0.0001'),
        help_text='Price per unit'
    )
    purchase_date = forms.DateField(
        label='Purchase Date',
        initial=date.today,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Cannot be future or more than 30 days old'
    )
    notes = forms.CharField(
        label='Notes',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Optional purchase notes'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate item choices
        self.fields['inventory_item_id'].choices = [
            ('', '-- Select Item --')
        ] + get_items_for_dropdown()
    
    def clean_purchase_date(self):
        purchase_date = self.cleaned_data['purchase_date']
        today = date.today()
        
        if purchase_date > today:
            raise ValidationError("Purchase date cannot be in the future")
        
        min_date = today - timedelta(days=30)
        if purchase_date < min_date:
            raise ValidationError("Purchase date cannot be more than 30 days old")
        
        return purchase_date


class OutputForm(forms.Form):
    """Form for recording consumption output (indirect costs only)"""
    
    inventory_item_id = forms.ChoiceField(
        label='Indirect Cost Item',
        help_text='Select the item being consumed'
    )
    quantity_consumed = forms.DecimalField(
        label='Quantity Consumed',
        max_digits=10,
        decimal_places=4,
        min_value=Decimal('0.0001'),
        help_text='Amount consumed (must not exceed current stock)'
    )
    consumption_date = forms.DateField(
        label='Consumption Date',
        initial=date.today,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Cannot be future or more than 30 days old'
    )
    date_range_start = forms.DateField(
        label='Period Start (Optional)',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='Start date of consumption period for reporting'
    )
    date_range_end = forms.DateField(
        label='Period End (Optional)',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='End date of consumption period for reporting'
    )
    description = forms.CharField(
        label='Description',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Optional: What was this consumption for?'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show indirect cost items
        self.fields['inventory_item_id'].choices = [
            ('', '-- Select Item --')
        ] + get_items_for_dropdown(include_ingredients=False, include_indirect_costs=True)
    
    def clean_consumption_date(self):
        consumption_date = self.cleaned_data['consumption_date']
        today = date.today()
        
        if consumption_date > today:
            raise ValidationError("Consumption date cannot be in the future")
        
        min_date = today - timedelta(days=30)
        if consumption_date < min_date:
            raise ValidationError("Consumption date cannot be more than 30 days old")
        
        return consumption_date
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate date range if provided
        date_range_start = cleaned_data.get('date_range_start')
        date_range_end = cleaned_data.get('date_range_end')
        
        if date_range_start and date_range_end:
            if date_range_start > date_range_end:
                raise ValidationError({
                    'date_range_end': "End date must be after start date"
                })
        
        return cleaned_data


class ItemSettingsForm(forms.Form):
    """Form for updating item settings (admin only)"""
    
    name = forms.CharField(
        label='Display Name',
        max_length=200,
        help_text='Name shown in dropdowns and reports'
    )
    minimum_stock_level = forms.DecimalField(
        label='Minimum Stock Level',
        max_digits=10,
        decimal_places=4,
        min_value=Decimal('0'),
        help_text='Threshold for low stock alerts'
    )
