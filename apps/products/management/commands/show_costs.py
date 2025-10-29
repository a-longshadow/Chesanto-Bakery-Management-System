"""
Management command to display Mix costs and profitability
"""
from django.core.management.base import BaseCommand
from apps.products.models import Mix, Product


class Command(BaseCommand):
    help = 'Display Mix costs and profitability analysis'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('💰 CHESANTO BAKERY - PRODUCT COST ANALYSIS'))
        self.stdout.write('='*70 + '\n')

        mixes = Mix.objects.filter(is_active=True).select_related('product').order_by('product__name')

        for mix in mixes:
            product = mix.product
            
            self.stdout.write('\n' + '-'*70)
            self.stdout.write(self.style.SUCCESS(
                f"🍞 {product.name} - {mix.name} (v{mix.version})"
            ))
            self.stdout.write('-'*70)
            
            # Production Details
            self.stdout.write(self.style.SUCCESS('\n📊 PRODUCTION DETAILS:'))
            self.stdout.write(f"  Expected Output: {mix.expected_packets} {product.packet_label}s")
            if product.has_variable_output:
                self.stdout.write(f"  Output Range: {product.min_expected_output}-{product.max_expected_output} {product.packet_label}s")
            self.stdout.write(f"  Units per Packet: {product.units_per_packet}")
            
            # Cost Breakdown
            self.stdout.write(self.style.SUCCESS('\n💵 COST BREAKDOWN:'))
            self.stdout.write(f"  Total Mix Cost: KES {mix.total_cost:,.2f}")
            self.stdout.write(f"  Cost per Packet: KES {mix.cost_per_packet:.2f}")
            
            # Pricing
            self.stdout.write(self.style.SUCCESS('\n💰 PRICING:'))
            self.stdout.write(f"  Selling Price: KES {product.price_per_packet:.2f} per {product.packet_label}")
            
            # Profitability
            profit_per_packet = product.price_per_packet - mix.cost_per_packet
            total_revenue = product.price_per_packet * mix.expected_packets
            total_profit = total_revenue - mix.total_cost
            
            if product.price_per_packet > 0:
                profit_margin = (profit_per_packet / product.price_per_packet) * 100
            else:
                profit_margin = 0
            
            self.stdout.write(self.style.SUCCESS('\n📈 PROFITABILITY:'))
            self.stdout.write(f"  Profit per Packet: KES {profit_per_packet:.2f}")
            
            if profit_per_packet >= 0:
                self.stdout.write(self.style.SUCCESS(
                    f"  Profit Margin: {profit_margin:.1f}%"
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    f"  ⚠️  LOSS MARGIN: {profit_margin:.1f}% (SELLING BELOW COST!)"
                ))
            
            self.stdout.write(f"  Total Revenue (if all sold): KES {total_revenue:,.2f}")
            self.stdout.write(f"  Total Profit (if all sold): KES {total_profit:,.2f}")
            
            # Sub-products
            if product.has_sub_product:
                self.stdout.write(self.style.SUCCESS('\n🥖 SUB-PRODUCT:'))
                self.stdout.write(f"  {product.sub_product_name}: KES {product.sub_product_price:.2f} per {product.packet_label}")
            
            # Ingredients Summary
            self.stdout.write(self.style.SUCCESS('\n📋 INGREDIENTS:'))
            for mix_ingredient in mix.mixingredient_set.all().select_related('ingredient', 'ingredient__inventory_item'):
                linked = '✓' if mix_ingredient.ingredient.inventory_item else '⚠'
                self.stdout.write(
                    f"  {linked} {mix_ingredient.ingredient.name}: "
                    f"{mix_ingredient.quantity} {mix_ingredient.unit} = "
                    f"KES {mix_ingredient.ingredient_cost:.2f}"
                )

        # Overall Summary
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS('📊 OVERALL SUMMARY'))
        self.stdout.write('='*70)
        
        total_mixes = mixes.count()
        total_products = Product.objects.filter(is_active=True).count()
        
        self.stdout.write(f"  Active Products: {total_products}")
        self.stdout.write(f"  Active Mixes: {total_mixes}")
        
        # Calculate total daily potential
        total_daily_revenue = sum(
            mix.product.price_per_packet * mix.expected_packets 
            for mix in mixes
        )
        total_daily_cost = sum(mix.total_cost for mix in mixes)
        total_daily_profit = total_daily_revenue - total_daily_cost
        
        self.stdout.write(f"\n  Daily Production Potential:")
        self.stdout.write(f"    Total Revenue: KES {total_daily_revenue:,.2f}")
        self.stdout.write(f"    Total Costs: KES {total_daily_cost:,.2f}")
        self.stdout.write(self.style.SUCCESS(
            f"    Total Profit: KES {total_daily_profit:,.2f}"
        ))
        
        if total_daily_revenue > 0:
            overall_margin = (total_daily_profit / total_daily_revenue) * 100
            self.stdout.write(self.style.SUCCESS(
                f"    Overall Margin: {overall_margin:.1f}%"
            ))
        
        self.stdout.write('\n' + self.style.SUCCESS('✅ Analysis complete!'))
        self.stdout.write('')
