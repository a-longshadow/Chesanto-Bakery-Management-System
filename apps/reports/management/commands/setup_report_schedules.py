"""
Setup Report Schedules Management Command
==========================================
Creates default report schedules, report types, and registers Django-Q schedules.

Usage:
    python manage.py setup_report_schedules

This will:
1. Create DAILY, WEEKLY, MONTHLY, ANNUAL ReportSchedule records
2. Create all ReportType records mapping to PDF views
3. Create default ScheduleReport assignments
4. Register schedules with Django-Q
5. Optionally add default recipients

Schedule Design:
- DAILY: 9 PM every day - sends today's complete data
- WEEKLY: 9 PM Sunday - sends Mon-Sun complete week
- MONTHLY: 9 PM last day of month - sends complete month
- ANNUAL: 9 PM Dec 31 - sends complete year
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import schedule as schedule_task

from apps.reports.models import (
    ReportSchedule,
    ReportType,
    ScheduleReport,
    ReportRecipient,
)


class Command(BaseCommand):
    help = 'Set up report schedules, report types, and Django-Q schedules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing schedules and recreate',
        )
        parser.add_argument(
            '--add-recipient',
            type=str,
            help='Add a recipient email (format: "Name <email>")',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING('Resetting all schedules...'))
            ReportSchedule.objects.all().delete()
            ReportType.objects.all().delete()
            Schedule.objects.filter(name__startswith='report_').delete()
        
        self.stdout.write('Setting up report schedules...\n')
        
        # Step 1: Create Report Schedules
        self.create_schedules()
        
        # Step 2: Create Report Types
        self.create_report_types()
        
        # Step 3: Create Schedule-Report Assignments
        self.create_schedule_assignments()
        
        # Step 4: Register Django-Q Schedules
        self.register_django_q_schedules()
        
        # Step 5: Add recipient if specified
        if options['add_recipient']:
            self.add_recipient(options['add_recipient'])
        
        self.stdout.write(self.style.SUCCESS('\n✅ Report schedules setup complete!'))
        self.stdout.write('\nNext steps:')
        self.stdout.write('  1. Add recipients: python manage.py setup_report_schedules --add-recipient "Name <email>"')
        self.stdout.write('  2. Or add via Django Admin: /admin/reports/reportrecipient/')
        self.stdout.write('  3. Start Django-Q cluster: python manage.py qcluster')

    def create_schedules(self):
        """Create all report schedules (DAILY, WEEKLY, MONTHLY, ANNUAL)."""
        schedules = [
            {
                'name': 'Daily Report',
                'schedule_type': 'DAILY',
                'hour': 21,  # 9 PM
                'minute': 0,
                'subject_template': 'Chesanto Bakery - Daily Report - {date}',
            },
            {
                'name': 'Weekly Report',
                'schedule_type': 'WEEKLY',
                'hour': 21,  # 9 PM
                'minute': 0,
                'day_of_week': 'SUN',  # Sunday
                'subject_template': 'Chesanto Bakery - Weekly Report - {date}',
            },
            {
                'name': 'Monthly Report',
                'schedule_type': 'MONTHLY',
                'hour': 21,  # 9 PM
                'minute': 0,
                'day_of_month': None,  # Runs on last day via cron 28-31 + check
                'subject_template': 'Chesanto Bakery - Monthly Report - {date}',
            },
            {
                'name': 'Annual Report',
                'schedule_type': 'ANNUAL',
                'hour': 21,  # 9 PM
                'minute': 0,
                'month': 12,
                'day_of_month': 31,
                'subject_template': 'Chesanto Bakery - Annual Report - {date}',
            },
        ]
        
        for sched_data in schedules:
            schedule, created = ReportSchedule.objects.update_or_create(
                schedule_type=sched_data['schedule_type'],
                defaults=sched_data
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status}: {schedule.name} ({schedule.time_display})')

    def create_report_types(self):
        """Create all available report types."""
        report_types = [
            # Financial Reports
            {
                'code': 'pnl_daily',
                'name': "Daily P&L Summary",
                'category': 'FINANCIAL',
                'period_type': 'DAILY',
                'pdf_view_name': 'reports:pnl_daily_pdf',
                'description': 'Profit & Loss for today',
                'sort_order': 1,
            },
            {
                'code': 'pnl_weekly',
                'name': 'Weekly P&L Summary',
                'category': 'FINANCIAL',
                'period_type': 'WEEKLY',
                'pdf_view_name': 'reports:pnl_weekly_pdf',
                'description': 'Profit & Loss for the week',
                'sort_order': 2,
            },
            {
                'code': 'pnl_monthly',
                'name': 'Monthly P&L Summary',
                'category': 'FINANCIAL',
                'period_type': 'MONTHLY',
                'pdf_view_name': 'reports:pnl_monthly_pdf',
                'description': 'Profit & Loss for the month',
                'sort_order': 3,
            },
            {
                'code': 'pnl_annual',
                'name': 'Annual P&L Summary',
                'category': 'FINANCIAL',
                'period_type': 'ANNUAL',
                'pdf_view_name': 'reports:pnl_annual_pdf',
                'description': 'Profit & Loss for the year',
                'sort_order': 4,
            },
            
            # Sales Reports
            {
                'code': 'sales_daily',
                'name': "Daily Sales Summary",
                'category': 'SALES',
                'period_type': 'DAILY',
                'pdf_view_name': 'reports:sales_daily_pdf',
                'description': 'Sales summary for today',
                'sort_order': 10,
            },
            {
                'code': 'sales_weekly',
                'name': 'Weekly Sales Summary',
                'category': 'SALES',
                'period_type': 'WEEKLY',
                'pdf_view_name': 'reports:sales_weekly_pdf',
                'description': 'Sales summary for the week',
                'sort_order': 11,
            },
            {
                'code': 'sales_monthly',
                'name': 'Monthly Sales Summary',
                'category': 'SALES',
                'period_type': 'MONTHLY',
                'pdf_view_name': 'reports:sales_monthly_pdf',
                'description': 'Sales summary for the month',
                'sort_order': 12,
            },
            {
                'code': 'salesperson_performance',
                'name': 'Salesperson Performance',
                'category': 'SALES',
                'period_type': 'DAILY',  # Included daily but shows month-to-date
                'pdf_view_name': 'reports:salesperson_performance_pdf',
                'description': 'Performance metrics for each salesperson',
                'sort_order': 15,
            },
            {
                'code': 'commission_report',
                'name': 'Commission Report',
                'category': 'SALES',
                'period_type': 'MONTHLY',
                'pdf_view_name': 'reports:commission_report_pdf',
                'description': 'Commission earned by salespeople',
                'sort_order': 16,
            },
            
            # Inventory Reports
            {
                'code': 'stock_levels',
                'name': 'Current Stock Levels',
                'category': 'INVENTORY',
                'period_type': 'SNAPSHOT',
                'pdf_view_name': 'reports:inventory_daily_pdf',
                'description': 'Current inventory quantities',
                'sort_order': 20,
            },
            {
                'code': 'low_stock_alerts',
                'name': 'Low Stock Alerts',
                'category': 'INVENTORY',
                'period_type': 'SNAPSHOT',
                'pdf_view_name': 'reports:low_stock_pdf',
                'description': 'Items below reorder level',
                'sort_order': 21,
            },
            {
                'code': 'stock_movement',
                'name': 'Stock Movement (7 days)',
                'category': 'INVENTORY',
                'period_type': 'SNAPSHOT',
                'pdf_view_name': 'reports:stock_movement_pdf',
                'description': 'Stock in/out over last 7 days',
                'sort_order': 22,
            },
            {
                'code': 'inventory_valuation',
                'name': 'Inventory Valuation',
                'category': 'INVENTORY',
                'period_type': 'SNAPSHOT',
                'pdf_view_name': 'reports:inventory_valuation_pdf',
                'description': 'Total value of current inventory',
                'sort_order': 23,
            },
            {
                'code': 'crate_accountability',
                'name': 'Crate Accountability',
                'category': 'INVENTORY',
                'period_type': 'SNAPSHOT',
                'pdf_view_name': 'reports:crate_accountability_pdf',
                'description': 'Outstanding crates by salesperson',
                'sort_order': 24,
            },
            
            # Production Reports
            {
                'code': 'production_daily',
                'name': "Yesterday's Production",
                'category': 'PRODUCTION',
                'period_type': 'DAILY',
                'pdf_view_name': 'reports:production_daily_pdf',
                'description': 'Production batches from previous day',
                'sort_order': 30,
            },
            {
                'code': 'production_weekly',
                'name': 'Weekly Production',
                'category': 'PRODUCTION',
                'period_type': 'WEEKLY',
                'pdf_view_name': 'reports:production_weekly_pdf',
                'description': 'Production summary for previous week',
                'sort_order': 31,
            },
            {
                'code': 'production_monthly',
                'name': 'Monthly Production',
                'category': 'PRODUCTION',
                'period_type': 'MONTHLY',
                'pdf_view_name': 'reports:production_monthly_pdf',
                'description': 'Production summary for previous month',
                'sort_order': 32,
            },
            {
                'code': 'efficiency_report',
                'name': 'Production Efficiency',
                'category': 'PRODUCTION',
                'period_type': 'SNAPSHOT',
                'pdf_view_name': 'reports:efficiency_pdf',
                'description': 'Waste, yield, and efficiency metrics',
                'sort_order': 35,
            },
            
            # Payroll Reports
            {
                'code': 'payroll_monthly',
                'name': 'Monthly Payroll',
                'category': 'PAYROLL',
                'period_type': 'MONTHLY',
                'pdf_view_name': 'reports:payroll_monthly_pdf',
                'description': 'Payroll summary for the month',
                'sort_order': 40,
            },
            {
                'code': 'payroll_annual',
                'name': 'Annual Payroll',
                'category': 'PAYROLL',
                'period_type': 'ANNUAL',
                'pdf_view_name': 'reports:payroll_annual_pdf',
                'description': 'Payroll summary for the year',
                'sort_order': 41,
            },
        ]
        
        self.stdout.write('\nCreating report types:')
        for rt_data in report_types:
            rt, created = ReportType.objects.update_or_create(
                code=rt_data['code'],
                defaults=rt_data
            )
            status = '✓' if created else '↻'
            self.stdout.write(f'  {status} {rt.name}')

    def create_schedule_assignments(self):
        """Assign reports to schedules."""
        try:
            daily = ReportSchedule.objects.get(schedule_type='DAILY')
        except ReportSchedule.DoesNotExist:
            daily = None
            
        try:
            weekly = ReportSchedule.objects.get(schedule_type='WEEKLY')
        except ReportSchedule.DoesNotExist:
            weekly = None
            
        try:
            monthly = ReportSchedule.objects.get(schedule_type='MONTHLY')
        except ReportSchedule.DoesNotExist:
            monthly = None
            
        try:
            annual = ReportSchedule.objects.get(schedule_type='ANNUAL')
        except ReportSchedule.DoesNotExist:
            annual = None
        
        # DAILY schedule (9 PM every day): Today's data + snapshots
        daily_reports = [
            'pnl_daily',           # Today's P&L
            'sales_daily',         # Today's sales
            'production_daily',    # Today's production
            'stock_levels',        # Current inventory
            'low_stock_alerts',    # Low stock items
        ]
        
        # WEEKLY schedule (9 PM Sunday): Complete week data
        weekly_reports = [
            'pnl_weekly',              # Mon-Sun P&L
            'sales_weekly',            # Mon-Sun sales
            'production_weekly',       # Mon-Sun production
            'efficiency_report',       # Week efficiency
            'stock_movement',          # Week stock flow
            'salesperson_performance', # Week performance
            'crate_accountability',    # Crate status
        ]
        
        # MONTHLY schedule (9 PM last day): Complete month data
        monthly_reports = [
            'pnl_monthly',           # Month P&L
            'sales_monthly',         # Month sales
            'production_monthly',    # Month production
            'commission_report',     # Month commissions
            'payroll_monthly',       # Month payroll
            'inventory_valuation',   # Month-end valuation
        ]
        
        # ANNUAL schedule (9 PM Dec 31): Complete year data
        annual_reports = [
            'pnl_annual',          # Year P&L
            'payroll_annual',      # Year payroll
        ]
        
        self.stdout.write('\nAssigning reports to schedules:')
        
        # Daily assignments
        if daily:
            self.stdout.write(f'\n  {daily.name}:')
            for order, code in enumerate(daily_reports, 1):
                try:
                    rt = ReportType.objects.get(code=code)
                    sr, created = ScheduleReport.objects.update_or_create(
                        schedule=daily,
                        report_type=rt,
                        defaults={'sort_order': order, 'is_active': True}
                    )
                    self.stdout.write(f'    {order}. {rt.name}')
                except ReportType.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'    ⚠ Report type not found: {code}'))
        
        # Weekly assignments
        if weekly:
            self.stdout.write(f'\n  {weekly.name}:')
            for order, code in enumerate(weekly_reports, 1):
                try:
                    rt = ReportType.objects.get(code=code)
                    sr, created = ScheduleReport.objects.update_or_create(
                        schedule=weekly,
                        report_type=rt,
                        defaults={'sort_order': order, 'is_active': True}
                    )
                    self.stdout.write(f'    {order}. {rt.name}')
                except ReportType.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'    ⚠ Report type not found: {code}'))
        
        # Monthly assignments
        if monthly:
            self.stdout.write(f'\n  {monthly.name}:')
            for order, code in enumerate(monthly_reports, 1):
                try:
                    rt = ReportType.objects.get(code=code)
                    sr, created = ScheduleReport.objects.update_or_create(
                        schedule=monthly,
                        report_type=rt,
                        defaults={'sort_order': order, 'is_active': True}
                    )
                    self.stdout.write(f'    {order}. {rt.name}')
                except ReportType.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'    ⚠ Report type not found: {code}'))
        
        # Annual assignments
        if annual:
            self.stdout.write(f'\n  {annual.name}:')
            for order, code in enumerate(annual_reports, 1):
                try:
                    rt = ReportType.objects.get(code=code)
                    sr, created = ScheduleReport.objects.update_or_create(
                        schedule=annual,
                        report_type=rt,
                        defaults={'sort_order': order, 'is_active': True}
                    )
                    self.stdout.write(f'    {order}. {rt.name}')
                except ReportType.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f'    ⚠ Report type not found: {code}'))

    def register_django_q_schedules(self):
        """Register all schedules with Django-Q."""
        self.stdout.write('\nRegistering Django-Q schedules:')
        
        # Delete existing schedules
        Schedule.objects.filter(name__startswith='report_').delete()
        
        # Schedule configuration mapping: schedule_type -> (task_func, description)
        # Note: Eligibility checks (is_sunday, is_last_day_of_month, is_dec_31) 
        # are done in the task itself, so cron just needs to trigger at the right times
        schedule_configs = {
            'DAILY': ('apps.reports.tasks.send_daily_report', 'every day at {time}'),
            'WEEKLY': ('apps.reports.tasks.send_weekly_report', 'every Sunday at {time}'),
            'MONTHLY': ('apps.reports.tasks.send_monthly_report', 'days 28-31 at {time} (last day check in task)'),
            'ANNUAL': ('apps.reports.tasks.send_annual_report', 'December 31 at {time}'),
        }
        
        for schedule_type, (func, desc_format) in schedule_configs.items():
            try:
                report_schedule = ReportSchedule.objects.get(schedule_type=schedule_type)
                if not report_schedule.is_active:
                    self.stdout.write(f'  ⊘ {schedule_type} report: INACTIVE (skipped)')
                    continue
                
                # Use the cron_expression property from the model
                Schedule.objects.create(
                    name=f'report_{schedule_type.lower()}',
                    func=func,
                    schedule_type=Schedule.CRON,
                    cron=report_schedule.cron_expression,
                    repeats=-1,  # Repeat forever
                )
                time_str = f'{report_schedule.hour:02d}:{report_schedule.minute:02d}'
                description = desc_format.format(time=time_str)
                self.stdout.write(f'  ✓ {schedule_type} report: {description}')
                self.stdout.write(f'      Cron: {report_schedule.cron_expression}')
                
            except ReportSchedule.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  ⚠ {schedule_type} schedule not found (skipped)'))

    def add_recipient(self, recipient_str: str):
        """Add a recipient email."""
        import re
        
        # Parse "Name <email>" format
        match = re.match(r'^(.+?)\s*<(.+?)>$', recipient_str.strip())
        if match:
            name = match.group(1).strip()
            email = match.group(2).strip()
        else:
            # Just email
            email = recipient_str.strip()
            name = email.split('@')[0].title()
        
        recipient, created = ReportRecipient.objects.get_or_create(
            email=email,
            defaults={'name': name, 'is_active': True}
        )
        
        # Add to both schedules
        for schedule in ReportSchedule.objects.filter(is_active=True):
            recipient.schedules.add(schedule)
        
        status = 'Added' if created else 'Updated'
        self.stdout.write(f'\n{status} recipient: {recipient}')
        self.stdout.write(f'  Assigned to: {", ".join(s.name for s in recipient.schedules.all())}')
