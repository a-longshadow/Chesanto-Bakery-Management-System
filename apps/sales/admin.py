from django.contrib import admin
from .models import Salesperson, Dispatch


@admin.register(Salesperson)
class SalespersonAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'salesperson_type', 'phone', 'is_active', 'created_at']
    list_filter = ['salesperson_type', 'is_active', 'created_at']
    search_fields = ['name', 'phone']
    readonly_fields = ['created_at', 'created_by', 'updated_by']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new
            obj.created_by = request.user
        else:  # Updating
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Dispatch)
class DispatchAdmin(admin.ModelAdmin):
    list_display = [
        'dispatch_number', 'salesperson', 'dispatch_date',
        'bread_qty', 'kdf_qty', 'scones_qty',
        'is_returned', 'total_revenue', 'created_at'
    ]
    list_filter = ['is_returned', 'dispatch_date', 'created_at']
    search_fields = ['dispatch_number', 'salesperson__name']
    readonly_fields = [
        'dispatch_number', 'created_at', 'created_by',
        'updated_at', 'updated_by', 'returned_at',
        'deleted_at', 'deleted_by'
    ]
    
    fieldsets = (
        ('Dispatch Information', {
            'fields': ('dispatch_number', 'salesperson', 'dispatch_date')
        }),
        ('Products Dispatched', {
            'fields': ('bread_qty', 'kdf_qty', 'scones_qty')
        }),
        ('Crates', {
            'fields': ('crates_dispatched',)
        }),
        ('Return Information', {
            'fields': (
                'bread_sold', 'bread_returned',
                'kdf_sold', 'kdf_returned',
                'scones_sold', 'scones_returned',
                'bread_revenue', 'kdf_revenue', 'scones_revenue', 'total_revenue',
                'crates_returned', 'crate_deficit',
                'is_returned', 'returned_at'
            )
        }),
        ('Audit Trail', {
            'fields': (
                'created_at', 'created_by',
                'updated_at', 'updated_by',
                'deleted_at', 'deleted_by'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new
            obj.created_by = request.user
        else:  # Updating
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
