from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re


# Phone number validator for Kenyan numbers
phone_validator = RegexValidator(
    regex=r'^\+?254\d{9}$|^0\d{9}$',
    message="Phone number must be in format: '+254712345678' or '0712345678'"
)


def validate_kenyan_national_id(value):
    """Validate Kenyan National ID (7-8 digits)"""
    if not re.match(r'^\d{7,8}$', str(value)):
        raise ValidationError(
            'National ID must be 7 or 8 digits',
            params={'value': value},
        )


def validate_file_size(file, max_size_mb=5):
    """Validate uploaded file size"""
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f'File size cannot exceed {max_size_mb}MB')
