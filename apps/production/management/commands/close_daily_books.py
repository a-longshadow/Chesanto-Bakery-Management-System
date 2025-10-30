"""
Management command to close daily production books at 9PM
Run via Railway Cron: 0 21 * * * (9PM daily)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from apps.production.models import DailyProduction
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Close daily production books and finalize all batches'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to close (YYYY-MM-DD). Defaults to today.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force close even if already closed',
        )
    
    def handle(self, *args, **options):
        # Get date to close
        if options['date']:
            try:
                from datetime import datetime
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR('Invalid date format. Use YYYY-MM-DD'))
                return
        else:
            target_date = date.today()
        
        # Get or create daily production
        try:
            daily_production = DailyProduction.objects.get(date=target_date)
        except DailyProduction.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'No production record for {target_date}'))
            # Create empty record
            system_user = User.objects.filter(is_superuser=True).first()
            daily_production = DailyProduction.objects.create(
                date=target_date,
                created_by=system_user
            )
            self.stdout.write(self.style.SUCCESS(f'Created empty production record for {target_date}'))
        
        # Check if already closed
        if daily_production.is_closed and not options['force']:
            self.stdout.write(self.style.WARNING(f'Books for {target_date} already closed'))
            return
        
        # Close books
        try:
            system_user = User.objects.filter(is_superuser=True).first()
            daily_production.close_books(system_user)
            
            self.stdout.write(self.style.SUCCESS(f'✅ Books closed successfully for {target_date}'))
            self.stdout.write(f'  - Bread: {daily_production.bread_produced} loaves produced')
            self.stdout.write(f'  - KDF: {daily_production.kdf_produced} packets produced')
            self.stdout.write(f'  - Scones: {daily_production.scones_produced} packets produced')
            self.stdout.write(f'  - Total Batches: {daily_production.batches.count()}')
            self.stdout.write(f'  - Indirect Costs: KES {daily_production.total_indirect_costs:,.2f}')
            
            # Check variance
            if daily_production.has_variance:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Variance detected: {daily_production.variance_percentage}%'))
            else:
                self.stdout.write(self.style.SUCCESS(f'  ✓ No variance'))
            
            # TODO: Send email report (Phase 3)
            # send_daily_report_email(daily_production)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error closing books: {str(e)}'))
            raise

