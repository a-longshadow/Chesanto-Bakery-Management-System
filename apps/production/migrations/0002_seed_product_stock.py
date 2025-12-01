"""
Seed ProductStock records for all active products.
Creates one ProductStock record per product with initial quantity of 0.
"""
from django.db import migrations


def seed_product_stock(apps, schema_editor):
    """Create ProductStock records for each active product."""
    Product = apps.get_model('products', 'Product')
    ProductStock = apps.get_model('production', 'ProductStock')
    
    created_count = 0
    for product in Product.objects.filter(is_active=True):
        stock, created = ProductStock.objects.get_or_create(
            product=product,
            defaults={
                'current_stock': 0,  # Match migration field name
            }
        )
        if created:
            created_count += 1
            print(f"  ✅ Created stock record for: {product.name}")
    
    print(f"\n📦 Created {created_count} ProductStock records")


def reverse_seed(apps, schema_editor):
    """Remove seeded ProductStock records."""
    ProductStock = apps.get_model('production', 'ProductStock')
    # Only delete records with 0 quantity (untouched seed data)
    deleted = ProductStock.objects.filter(current_stock=0).delete()
    print(f"🗑️ Removed {deleted[0]} ProductStock records")


class Migration(migrations.Migration):
    """Seed migration for ProductStock records."""
    
    dependencies = [
        ('production', '0001_initial'),
        ('products', '0002_seed_products_and_mixes'),
    ]
    
    operations = [
        migrations.RunPython(seed_product_stock, reverse_seed),
    ]
