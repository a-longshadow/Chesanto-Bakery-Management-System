"""
Send Scheduled Report Management Command
=========================================
Triggers a specific scheduled report. Designed for Railway Cron jobs.

Usage:
    python manage.py send_scheduled_report MORNING
    python manage.py send_scheduled_report EVENING
    python manage.py send_scheduled_report WEEKLY
    python manage.py send_scheduled_report MONTHLY
    python manage.py send_scheduled_report ANNUAL

Railway Cron Configuration:
    Add these as separate cron jobs in Railway:
    - Morning:  0 6 * * *   python manage.py send_scheduled_report MORNING
    - Evening:  0 22 * * *  python manage.py send_scheduled_report EVENING
    - Weekly:   0 7 * * 1   python manage.py send_scheduled_report WEEKLY
    - Monthly:  0 7 1 * *   python manage.py send_scheduled_report MONTHLY
    - Annual:   0 8 1 1 *   python manage.py send_scheduled_report ANNUAL
"""

from django.core.management.base import BaseCommand, CommandError

from apps.reports.tasks import send_scheduled_reports


class Command(BaseCommand):
    help = 'Send a scheduled report by type (MORNING, EVENING, WEEKLY, MONTHLY, ANNUAL)'

    def add_arguments(self, parser):
        parser.add_argument(
            'schedule_type',
            type=str,
            choices=['MORNING', 'EVENING', 'WEEKLY', 'MONTHLY', 'ANNUAL'],
            help='The schedule type to send',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )

    def handle(self, *args, **options):
        schedule_type = options['schedule_type'].upper()
        dry_run = options['dry_run']
        
        self.stdout.write(f'Sending {schedule_type} report...')
        
        if dry_run:
            from apps.reports.models import ReportSchedule, ScheduleReport, ReportRecipient
            
            try:
                schedule = ReportSchedule.objects.get(schedule_type=schedule_type)
            except ReportSchedule.DoesNotExist:
                raise CommandError(f'Schedule {schedule_type} not found')
            
            reports = ScheduleReport.objects.filter(
                schedule=schedule, is_active=True
            ).select_related('report_type')
            
            recipients = ReportRecipient.objects.filter(
                schedules=schedule, is_active=True
            )
            
            self.stdout.write(f'\n[DRY RUN] Would send {schedule.name}:')
            self.stdout.write(f'  Reports ({reports.count()}):')
            for sr in reports:
                self.stdout.write(f'    - {sr.report_type.name}')
            self.stdout.write(f'  Recipients ({recipients.count()}):')
            for r in recipients:
                self.stdout.write(f'    - {r.name} <{r.email}>')
            return
        
        # Actually send the report
        result = send_scheduled_reports(schedule_type)
        
        if result.get('status') == 'success':
            self.stdout.write(self.style.SUCCESS(
                f"✅ {schedule_type} report sent successfully!\n"
                f"   Recipients: {result.get('recipients_count', 0)}\n"
                f"   Reports: {', '.join(result.get('reports_generated', []))}"
            ))
        elif result.get('status') == 'skipped':
            self.stdout.write(self.style.WARNING(
                f"⊘ {schedule_type} report skipped: {result.get('errors', ['Unknown'])}"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"❌ {schedule_type} report failed: {result.get('errors', ['Unknown'])}"
            ))
            raise CommandError(f"Report sending failed: {result.get('errors')}")
