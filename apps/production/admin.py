"""
Production App Admin Configuration
Django Admin interfaces for DailyProduction, ProductionBatch, and IndirectCost
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import DailyProduction, ProductionBatch, IndirectCost


class ProductionBatchInline(admin.TabularInline):
    """Inline for ProductionBatch in DailyProduction admin"""
    model = ProductionBatch
    extra = 0
    fields = [
        'batch_number', 'mix', 'actual_packets', 'rejects_produced',
        'variance_display', 'total_cost', 'gross_profit', 'quality_notes'
    ]
    readonly_fields = ['variance_display', 'total_cost', 'gross_profit']
    
    def variance_display(self, obj):
        """Display variance with color coding"""
        if not obj.id:
            return '-'
        
        variance = obj.variance_packets
        percentage = obj.variance_percentage
        
        if variance > 0:
            color = '#059669'  # Green for over-production
            symbol = '+'
        elif variance < 0:
            color = '#dc2626'  # Red for under-production
            symbol = ''
        else:
            color = '#6b7280'  # Gray for exact
            symbol = ''
        
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}{} ({}%)</span>',
            color, symbol, variance, percentage
        )
    variance_display.short_description = 'Variance'


class IndirectCostInline(admin.TabularInline):
    """Inline for IndirectCost details in DailyProduction admin"""
    model = IndirectCost
    extra = 1
    fields = ['cost_type', 'description', 'amount', 'receipt_number', 'vendor']


@admin.register(DailyProduction)
class DailyProductionAdmin(admin.ModelAdmin):
    """
    Admin interface for DailyProduction
    Shows daily production summary, opening/closing stock, indirect costs
    """
    list_display = [
        'date',
        'status_badge',
        'bread_total_display',
        'kdf_total_display',
        'scones_total_display',
        'total_indirect_costs',
        'variance_indicator',
        'closed_at'
    ]
    list_filter = ['is_closed', 'has_variance', 'date']
    search_fields = ['date', 'reconciliation_notes']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Date & Status', {
            'fields': ('date', 'is_closed', 'closed_at', 'has_variance', 'variance_percentage')
        }),
        ('Opening Product Stock (Finished Goods)', {
            'fields': ('opening_bread_stock', 'opening_kdf_stock', 'opening_scones_stock'),
            'description': '🤖 AUTO: From previous day\'s closing stock'
        }),
        ('Production (From Batches)', {
            'fields': ('bread_produced', 'kdf_produced', 'scones_produced'),
            'description': '🤖 AUTO: Calculated from production batches below'
        }),
        ('Dispatch (From Sales App)', {
            'fields': ('bread_dispatched', 'kdf_dispatched', 'scones_dispatched'),
            'description': '✏️ MANUAL: Enter dispatch quantities from sales records'
        }),
        ('Returns (From Sales App)', {
            'fields': ('bread_returned', 'kdf_returned', 'scones_returned'),
            'description': '✏️ MANUAL: Enter return quantities from sales records'
        }),
        ('Closing Product Stock (Calculated)', {
            'fields': ('closing_bread_stock', 'closing_kdf_stock', 'closing_scones_stock'),
            'description': '🤖 AUTO: Opening + Produced - Dispatched + Returned'
        }),
        ('Indirect Costs (Daily Operational Costs)', {
            'fields': (
                'diesel_cost', 'firewood_cost', 'electricity_cost',
                'fuel_distribution_cost', 'other_indirect_costs', 'total_indirect_costs'
            ),
            'description': '✏️ MANUAL: Enter daily operational costs (auto-allocated to batches)'
        }),
        ('Reconciliation', {
            'fields': ('reconciliation_notes',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'opening_bread_stock', 'opening_kdf_stock', 'opening_scones_stock',
        'bread_produced', 'kdf_produced', 'scones_produced',
        'closing_bread_stock', 'closing_kdf_stock', 'closing_scones_stock',
        'total_indirect_costs', 'closed_at', 'has_variance', 'variance_percentage'
    ]
    
    inlines = [ProductionBatchInline, IndirectCostInline]
    
    actions = ['close_books_action']
    
    def status_badge(self, obj):
        """Display status badge (OPEN/CLOSED)"""
        if obj.is_closed:
            return format_html(
                '<span style="background: #dc2626; color: white; padding: 4px 8px; '
                'border-radius: 4px; font-weight: 600; font-size: 0.75rem;">CLOSED</span>'
            )
        else:
            return format_html(
                '<span style="background: #059669; color: white; padding: 4px 8px; '
                'border-radius: 4px; font-weight: 600; font-size: 0.75rem;">OPEN</span>'
            )
    status_badge.short_description = 'Status'
    
    def bread_total_display(self, obj):
        """Display Bread production with stock flow"""
        return format_html(
            '<div style="font-size: 0.875rem;">'
            '<div style="font-weight: 600; color: #1f2937;">{} loaves</div>'
            '<div style="color: #6b7280; font-size: 0.75rem;">Opening: {} | Closing: {}</div>'
            '</div>',
            obj.bread_produced, obj.opening_bread_stock, obj.closing_bread_stock
        )
    bread_total_display.short_description = 'Bread'
    
    def kdf_total_display(self, obj):
        """Display KDF production with stock flow"""
        return format_html(
            '<div style="font-size: 0.875rem;">'
            '<div style="font-weight: 600; color: #1f2937;">{} packets</div>'
            '<div style="color: #6b7280; font-size: 0.75rem;">Opening: {} | Closing: {}</div>'
            '</div>',
            obj.kdf_produced, obj.opening_kdf_stock, obj.closing_kdf_stock
        )
    kdf_total_display.short_description = 'KDF'
    
    def scones_total_display(self, obj):
        """Display Scones production with stock flow"""
        return format_html(
            '<div style="font-size: 0.875rem;">'
            '<div style="font-weight: 600; color: #1f2937;">{} packets</div>'
            '<div style="color: #6b7280; font-size: 0.75rem;">Opening: {} | Closing: {}</div>'
            '</div>',
            obj.scones_produced, obj.opening_scones_stock, obj.closing_scones_stock
        )
    scones_total_display.short_description = 'Scones'
    
    def variance_indicator(self, obj):
        """Show variance indicator if detected"""
        if obj.has_variance:
            return format_html(
                '<span style="color: #dc2626; font-weight: 600;">⚠️ {}%</span>',
                obj.variance_percentage
            )
        return format_html('<span style="color: #059669;">✓</span>')
    variance_indicator.short_description = 'Variance'
    
    def close_books_action(self, request, queryset):
        """Admin action to close books for selected days"""
        for daily_prod in queryset:
            if not daily_prod.is_closed:
                daily_prod.close_books(request.user)
        self.message_user(request, f"{queryset.count()} day(s) closed successfully.")
    close_books_action.short_description = "Close books for selected days"
    
    def save_model(self, request, obj, form, change):
        """Track user on save"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    """
    Admin interface for ProductionBatch
    Detailed view of individual batches with P&L
    """
    list_display = [
        'batch_display',
        'mix',
        'actual_output',
        'variance_display',
        'cost_display',
        'revenue_display',
        'profit_display',
        'finalized_badge'
    ]
    list_filter = [
        'daily_production__date',
        'mix__product__name',
        'is_finalized',
        'daily_production__is_closed'
    ]
    search_fields = ['mix__product__name', 'quality_notes', 'batch_number']
    date_hierarchy = 'daily_production__date'
    
    fieldsets = (
        ('Batch Information', {
            'fields': ('daily_production', 'mix', 'batch_number', 'start_time', 'end_time')
        }),
        ('Output', {
            'fields': (
                'actual_packets', 'expected_packets', 'variance_packets', 
                'variance_percentage', 'rejects_produced'
            ),
            'description': '✏️ MANUAL: Enter actual output | 🤖 AUTO: Variance calculated'
        }),
        ('Costs', {
            'fields': (
                'ingredient_cost', 'packaging_cost', 'allocated_indirect_cost',
                'total_cost', 'cost_per_packet'
            ),
            'description': '🤖 AUTO: All costs calculated automatically'
        }),
        ('P&L (Profit & Loss)', {
            'fields': (
                'selling_price_per_packet', 'expected_revenue',
                'gross_profit', 'gross_margin_percentage'
            ),
            'description': '🤖 AUTO: P&L calculated from selling price and costs'
        }),
        ('Quality Control', {
            'fields': ('quality_notes', 'is_finalized'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'expected_packets', 'variance_packets', 'variance_percentage',
        'ingredient_cost', 'packaging_cost', 'allocated_indirect_cost',
        'total_cost', 'cost_per_packet', 'selling_price_per_packet',
        'expected_revenue', 'gross_profit', 'gross_margin_percentage'
    ]
    
    def batch_display(self, obj):
        """Display batch with date and number"""
        return format_html(
            '<div style="font-weight: 600;">{}</div>'
            '<div style="color: #6b7280; font-size: 0.75rem;">Batch #{}</div>',
            obj.daily_production.date, obj.batch_number
        )
    batch_display.short_description = 'Date & Batch'
    
    def actual_output(self, obj):
        """Display actual output with rejects"""
        if obj.rejects_produced > 0:
            return format_html(
                '{} units<br><span style="color: #dc2626; font-size: 0.75rem;">'
                '+ {} rejects</span>',
                obj.actual_packets, obj.rejects_produced
            )
        return f"{obj.actual_packets} units"
    actual_output.short_description = 'Actual Output'
    
    def variance_display(self, obj):
        """Display variance with color"""
        variance = obj.variance_packets
        percentage = obj.variance_percentage
        
        if variance > 0:
            color = '#059669'
            symbol = '+'
        elif variance < 0:
            color = '#dc2626'
            symbol = ''
        else:
            color = '#6b7280'
            symbol = ''
        
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}{}</span><br>'
            '<span style="color: #6b7280; font-size: 0.75rem;">({}%)</span>',
            color, symbol, variance, percentage
        )
    variance_display.short_description = 'Variance'
    
    def cost_display(self, obj):
        """Display total cost breakdown"""
        return format_html(
            '<div style="font-weight: 600;">KES {:,.2f}</div>'
            '<div style="color: #6b7280; font-size: 0.75rem;">'
            'KES {:.2f}/unit</div>',
            obj.total_cost, obj.cost_per_packet
        )
    cost_display.short_description = 'Total Cost'
    
    def revenue_display(self, obj):
        """Display expected revenue"""
        return format_html(
            '<div style="font-weight: 600;">KES {:,.2f}</div>'
            '<div style="color: #6b7280; font-size: 0.75rem;">'
            '@KES {:.2f}/unit</div>',
            obj.expected_revenue, obj.selling_price_per_packet
        )
    revenue_display.short_description = 'Expected Revenue'
    
    def profit_display(self, obj):
        """Display profit with margin"""
        profit = obj.gross_profit
        margin = obj.gross_margin_percentage
        
        if profit >= 0:
            color = '#059669'
            symbol = '+'
        else:
            color = '#dc2626'
            symbol = ''
        
        return format_html(
            '<div style="color: {}; font-weight: 600;">{} KES {:,.2f}</div>'
            '<div style="color: #6b7280; font-size: 0.75rem;">{}% margin</div>',
            color, symbol, profit, margin
        )
    profit_display.short_description = 'Gross Profit'
    
    def finalized_badge(self, obj):
        """Show finalized status"""
        if obj.is_finalized:
            return format_html(
                '<span style="background: #6b7280; color: white; padding: 2px 6px; '
                'border-radius: 3px; font-size: 0.75rem;">🔒 LOCKED</span>'
            )
        return format_html(
            '<span style="color: #059669; font-size: 0.75rem;">✏️ Editable</span>'
        )
    finalized_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        """Track user on save"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(IndirectCost)
class IndirectCostAdmin(admin.ModelAdmin):
    """
    Admin interface for IndirectCost details
    Track individual indirect cost transactions
    """
    list_display = [
        'daily_production',
        'cost_type',
        'description',
        'amount_display',
        'vendor',
        'receipt_number'
    ]
    list_filter = ['cost_type', 'daily_production__date']
    search_fields = ['description', 'vendor', 'receipt_number']
    date_hierarchy = 'daily_production__date'
    
    fields = [
        'daily_production', 'cost_type', 'description', 'amount',
        'receipt_number', 'vendor'
    ]
    
    def amount_display(self, obj):
        """Display amount with KES formatting"""
        return format_html(
            '<span style="font-weight: 600;">KES {:,.2f}</span>',
            obj.amount
        )
    amount_display.short_description = 'Amount'
    
    def save_model(self, request, obj, form, change):
        """Track user on save"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
