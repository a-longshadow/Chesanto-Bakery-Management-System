"""
Seed ProductStock record for Family Bread 800g.
Creates ProductStock record with initial quantity of 0.
"""
from django.db import migrations


def seed_family_bread_stock(apps, schema_editor):
    """Create ProductStock record for Family Bread 800g."""
    Product = apps.get_model('products', 'Product')
    ProductStock = apps.get_model('production', 'ProductStock')
    
    try:
        family_bread = Product.objects.get(name='Family Bread 800g', is_active=True)
        stock, created = ProductStock.objects.get_or_create(
            product=family_bread,
            defaults={
                'current_stock': 0,
            }
        )
        if created:
            print(f"  ✅ Created stock record for: Family Bread 800g")
        else:
            print(f"  ℹ️  Stock record already exists for: Family Bread 800g")
    except Product.DoesNotExist:
        print("  ⚠️  Family Bread 800g product not found. Skipping stock creation.")


def reverse_seed(apps, schema_editor):
    """Remove seeded ProductStock record for Family Bread 800g."""
    Product = apps.get_model('products', 'Product')
    ProductStock = apps.get_model('production', 'ProductStock')
    
    try:
        family_bread = Product.objects.get(name='Family Bread 800g')
        # Only delete if stock is 0 (untouched seed data)
        deleted = ProductStock.objects.filter(product=family_bread, current_stock=0).delete()
        print(f"🗑️ Removed {deleted[0]} ProductStock record for Family Bread 800g")
    except Product.DoesNotExist:
        pass


class Migration(migrations.Migration):
    """Seed migration for Family Bread 800g ProductStock record."""
    
    dependencies = [
        ('production', '0002_seed_product_stock'),
        ('products', '0003_seed_family_bread'),
    ]
    
    operations = [
        migrations.RunPython(seed_family_bread_stock, reverse_seed),
    ]
