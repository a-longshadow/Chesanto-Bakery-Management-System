"""
Management command to recalculate all Mix costs from Inventory
Run this after linking ingredients to inventory items or when inventory prices change
"""
from django.core.management.base import BaseCommand
from apps.products.models import Mix, MixIngredient


class Command(BaseCommand):
    help = 'Recalculate all Mix costs from linked InventoryItems'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🧮 RECALCULATING MIX COSTS FROM INVENTORY'))
        self.stdout.write('='*60 + '\n')

        # Get all MixIngredients
        mix_ingredients = MixIngredient.objects.select_related(
            'ingredient__inventory_item',
            'mix__product'
        ).all()

        total_ingredients = mix_ingredients.count()
        updated_count = 0

        self.stdout.write(f'📊 Found {total_ingredients} mix ingredients to recalculate\n')

        # Track costs by mix
        mix_costs = {}

        for mix_ingredient in mix_ingredients:
            old_cost = mix_ingredient.ingredient_cost
            
            # Recalculate cost
            mix_ingredient.calculate_cost()
            mix_ingredient.save(update_fields=['ingredient_cost'])
            
            new_cost = mix_ingredient.ingredient_cost
            
            # Track for mix totals
            mix_id = mix_ingredient.mix.id
            if mix_id not in mix_costs:
                mix_costs[mix_id] = {
                    'mix': mix_ingredient.mix,
                    'ingredients': []
                }
            
            mix_costs[mix_id]['ingredients'].append({
                'name': mix_ingredient.ingredient.name,
                'quantity': mix_ingredient.quantity,
                'unit': mix_ingredient.unit,
                'old_cost': old_cost,
                'new_cost': new_cost,
                'linked': mix_ingredient.ingredient.inventory_item is not None
            })
            
            if old_cost != new_cost:
                updated_count += 1

        # Display results by mix
        for mix_id, data in mix_costs.items():
            mix = data['mix']
            self.stdout.write('\n' + '-'*60)
            self.stdout.write(self.style.SUCCESS(
                f"📋 {mix.product.name} - {mix.name} (v{mix.version})"
            ))
            self.stdout.write('-'*60)
            
            for ing_data in data['ingredients']:
                status = '✓' if ing_data['linked'] else '⚠'
                color = self.style.SUCCESS if ing_data['linked'] else self.style.WARNING
                
                self.stdout.write(color(
                    f"{status} {ing_data['name']}: "
                    f"{ing_data['quantity']} {ing_data['unit']} "
                    f"= KES {ing_data['new_cost']:.2f}"
                ))
                
                if not ing_data['linked']:
                    self.stdout.write(self.style.WARNING(
                        f"    → No inventory link (cost = KES 0.00)"
                    ))
            
            # Recalculate mix totals
            old_total = mix.total_cost
            old_per_packet = mix.cost_per_packet
            
            mix.calculate_costs()
            
            self.stdout.write('\n' + self.style.SUCCESS(
                f"  TOTAL COST: KES {mix.total_cost:.2f} "
                f"(was KES {old_total:.2f})"
            ))
            self.stdout.write(self.style.SUCCESS(
                f"  COST/PACKET: KES {mix.cost_per_packet:.2f} "
                f"(was KES {old_per_packet:.2f})"
            ))
            self.stdout.write(self.style.SUCCESS(
                f"  EXPECTED OUTPUT: {mix.expected_packets} {mix.product.packet_label}s"
            ))

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ COST RECALCULATION COMPLETE!'))
        self.stdout.write('='*60)
        self.stdout.write(f'  Total Ingredients: {total_ingredients}')
        self.stdout.write(f'  Updated: {updated_count}')
        self.stdout.write(f'  Unchanged: {total_ingredients - updated_count}')
        self.stdout.write(f'  Mixes Recalculated: {len(mix_costs)}')
        self.stdout.write('\n' + self.style.SUCCESS('🎉 All mix costs updated from inventory!'))
        self.stdout.write('')
