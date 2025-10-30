"""
Production Forms for Chesanto Bakery Management System
Django forms for production batch and indirect costs entry
"""
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import ProductionBatch, DailyProduction, IndirectCost
from apps.products.models import Mix


class ProductionBatchForm(forms.ModelForm):
    """
    Form for creating/editing production batches
    Validates:
    - Rejects only for Bread
    - Positive quantities
    - Unique batch numbers per day
    """
    
    class Meta:
        model = ProductionBatch
        fields = [
            'mix',
            'batch_number',
            'actual_packets',
            'rejects_produced',
            'start_time',
            'end_time',
            'quality_notes',
        ]
        widgets = {
            'mix': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'batch_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'required': True,
            }),
            'actual_packets': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'required': True,
                'placeholder': 'Enter actual packets produced',
            }),
            'rejects_produced': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0,
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time',
            }),
            'quality_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any quality observations or issues...',
            }),
        }
        labels = {
            'mix': '✏️ Select Mix',
            'batch_number': '✏️ Batch Number',
            'actual_packets': '✏️ Actual Packets Produced',
            'rejects_produced': '✏️ Rejects (Bread only)',
            'start_time': '✏️ Start Time',
            'end_time': '✏️ End Time',
            'quality_notes': '✏️ Quality Notes',
        }
        help_texts = {
            'mix': 'Select the mix used for this batch',
            'batch_number': 'Batch number for the day (1, 2, 3...)',
            'actual_packets': 'Main input - actual units/packets produced',
            'rejects_produced': 'Only for Bread - number of reject loaves',
            'quality_notes': 'Optional notes on quality, observations, or issues',
        }
    
    def __init__(self, *args, **kwargs):
        self.daily_production = kwargs.pop('daily_production', None)
        super().__init__(*args, **kwargs)
        
        # Filter active mixes only
        self.fields['mix'].queryset = Mix.objects.filter(
            is_active=True
        ).select_related('product')
    
    def clean_actual_packets(self):
        """Validate actual packets is positive"""
        actual_packets = self.cleaned_data.get('actual_packets')
        if actual_packets is not None and actual_packets < 1:
            raise ValidationError('Actual packets must be at least 1.')
        return actual_packets
    
    def clean_rejects_produced(self):
        """Validate rejects only for Bread"""
        rejects = self.cleaned_data.get('rejects_produced', 0)
        mix = self.cleaned_data.get('mix')
        
        if rejects > 0 and mix and mix.product.name != 'Bread':
            raise ValidationError('Only Bread can have rejects.')
        
        return rejects
    
    def clean_batch_number(self):
        """Validate unique batch number for this day"""
        batch_number = self.cleaned_data.get('batch_number')
        
        if self.daily_production:
            # Check if batch number already exists (excluding current instance if editing)
            existing = ProductionBatch.objects.filter(
                daily_production=self.daily_production,
                batch_number=batch_number
            )
            
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(
                    f'Batch number {batch_number} already exists for this date.'
                )
        
        return batch_number
    
    def clean(self):
        """Additional validation"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Validate end time is after start time
        if start_time and end_time and end_time <= start_time:
            raise ValidationError('End time must be after start time.')
        
        return cleaned_data


class IndirectCostForm(forms.ModelForm):
    """
    Form for entering daily indirect costs
    All costs in KES (Kenyan Shillings)
    """
    
    class Meta:
        model = DailyProduction
        fields = [
            'diesel_cost',
            'firewood_cost',
            'electricity_cost',
            'fuel_distribution_cost',
            'other_indirect_costs',
            'reconciliation_notes',
        ]
        widgets = {
            'diesel_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'firewood_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'electricity_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'fuel_distribution_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'other_indirect_costs': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': '0.00',
            }),
            'reconciliation_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Notes on variances, issues, or reconciliation details...',
            }),
        }
        labels = {
            'diesel_cost': '✏️ Diesel Cost (KES)',
            'firewood_cost': '✏️ Firewood Cost (KES)',
            'electricity_cost': '✏️ Electricity Cost (KES)',
            'fuel_distribution_cost': '✏️ Fuel Distribution Cost (KES)',
            'other_indirect_costs': '✏️ Other Costs (KES)',
            'reconciliation_notes': '✏️ Reconciliation Notes',
        }
        help_texts = {
            'diesel_cost': 'Daily diesel consumption for production',
            'firewood_cost': 'Daily firewood cost',
            'electricity_cost': 'Estimated daily electricity cost',
            'fuel_distribution_cost': 'Fuel for trucks/Bolero distribution',
            'other_indirect_costs': 'Miscellaneous indirect costs',
            'reconciliation_notes': 'Optional notes on stock variances or issues',
        }
    
    def clean(self):
        """Validate all costs are non-negative"""
        cleaned_data = super().clean()
        
        cost_fields = [
            'diesel_cost',
            'firewood_cost',
            'electricity_cost',
            'fuel_distribution_cost',
            'other_indirect_costs',
        ]
        
        for field in cost_fields:
            value = cleaned_data.get(field, Decimal('0'))
            if value < 0:
                self.add_error(field, 'Cost cannot be negative.')
        
        return cleaned_data


class BookClosingConfirmForm(forms.Form):
    """
    Simple confirmation form for book closing
    Requires explicit user confirmation
    """
    confirm = forms.BooleanField(
        required=True,
        label='I confirm that I want to close the books for this date',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        error_messages={
            'required': 'You must confirm before closing books.',
        }
    )
    
    notes = forms.CharField(
        required=False,
        label='Closing Notes (Optional)',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Any final notes or observations for this day...',
        }),
    )


class IndirectCostDetailForm(forms.ModelForm):
    """
    Optional detailed form for individual indirect cost transactions
    Used for audit trail and receipt tracking
    """
    
    class Meta:
        model = IndirectCost
        fields = [
            'cost_type',
            'description',
            'amount',
            'receipt_number',
            'vendor',
        ]
        widgets = {
            'cost_type': forms.Select(attrs={
                'class': 'form-control',
                'required': True,
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'placeholder': 'e.g., 20L diesel from Ikapolok',
                'maxlength': 200,
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'required': True,
                'placeholder': '0.00',
            }),
            'receipt_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Receipt/invoice number',
                'maxlength': 100,
            }),
            'vendor': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Vendor/supplier name',
                'maxlength': 200,
            }),
        }
        labels = {
            'cost_type': '✏️ Cost Type',
            'description': '✏️ Description',
            'amount': '✏️ Amount (KES)',
            'receipt_number': '✏️ Receipt Number',
            'vendor': '✏️ Vendor',
        }
    
    def clean_amount(self):
        """Validate amount is positive"""
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError('Amount must be greater than zero.')
        return amount
