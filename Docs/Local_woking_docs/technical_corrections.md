# Technical Corrections to System Design

## 1. Product Packaging Corrections
```python
# Product Constants - CORRECTED
PRODUCTS = {
    'BREAD': {
        'base_price': 60,  # KSH
        'commission': 5,
        'packaging_type': 'individual_packet',
        'mix_types': ['Mix 1', 'Mix 2', 'Mix 3']
    },
    'KDF': {
        'base_price': 100,  # KSH
        'commission': 10,
        'packaging_type': '12_piece_pack',  # CORRECTED
        'mix_types': ['Mix 1', 'Mix 2']
    },
    'SCONES': {
        'base_price': 50,  # KSH
        'commission': 5,
        'packaging_type': '12_piece_pack',  # CORRECTED
        'mix_types': ['Mix 1', 'Mix 2']
    }
}
```

## 2. East African Context Updates
```python
# System Settings - UPDATED
SETTINGS = {
    'timezone': 'Africa/Nairobi',
    'currency': 'KES',  # Kenyan Shilling
    'working_hours': {
        'weekday': {
            'start': '06:00',
            'end': '18:00'
        },
        'saturday': {
            'start': '06:00',
            'end': '14:00'
        }
    },
    'banking_hours': {
        'weekday': {
            'start': '08:00',
            'end': '17:00'
        },
        'saturday': {
            'start': '09:00',
            'end': '12:00'
        }
    },
    'banking_deadline': '16:00',  # Weekday deadline for deposits
    'saturday_banking_deadline': '11:30',
    'stock_threshold_percentage': 20,
    'commission_calculation_frequency': 'daily',
    'report_generation_time': '17:00'
}
```

These corrections ensure:
1. Proper packaging units for KDF and Scones (12-piece packs)
2. East African timezone context
3. Kenyan currency
4. Accurate banking hours for Kenya
5. Proper working hours context

Please update the system design specification with these corrections.