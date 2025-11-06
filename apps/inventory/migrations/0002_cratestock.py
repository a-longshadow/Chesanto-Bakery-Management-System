# Generated migration for Crate Stock Management

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CrateStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_crates', models.IntegerField(default=0, help_text='Total crates owned by bakery')),
                ('available_crates', models.IntegerField(default=0, help_text='Crates available at bakery (not dispatched)')),
                ('dispatched_crates', models.IntegerField(default=0, help_text='Crates currently with salespeople')),
                ('damaged_crates', models.IntegerField(default=0, help_text='Crates marked as damaged/unusable')),
                ('last_counted_at', models.DateTimeField(blank=True, help_text='Last physical count date', null=True)),
                ('last_counted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='crate_counts', to=settings.AUTH_USER_MODEL)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Crate Stock',
                'verbose_name_plural': 'Crate Stock',
            },
        ),
        migrations.CreateModel(
            name='CrateMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('movement_type', models.CharField(choices=[('DISPATCH', 'Dispatched to Salesperson'), ('RETURN', 'Returned from Salesperson'), ('PURCHASE', 'New Crates Purchased'), ('DAMAGE', 'Crates Damaged'), ('REPAIR', 'Crates Repaired'), ('COUNT', 'Physical Count Adjustment')], help_text='Type of crate movement', max_length=20)),
                ('quantity', models.IntegerField(help_text='Number of crates (positive or negative)')),
                ('salesperson_name', models.CharField(blank=True, help_text='Salesperson name if dispatch/return', max_length=200)),
                ('dispatch_id', models.IntegerField(blank=True, help_text='Related dispatch ID if applicable', null=True)),
                ('notes', models.TextField(blank=True, help_text='Additional notes or reason')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='crate_movements', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Crate Movement',
                'verbose_name_plural': 'Crate Movements',
                'ordering': ['-created_at'],
            },
        ),
    ]
