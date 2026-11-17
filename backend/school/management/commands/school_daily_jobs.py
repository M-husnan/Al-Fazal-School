from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone
class Command(BaseCommand):
    help='Run idempotent daily school jobs; schedule once daily with a Render Cron Job/system cron.'
    def handle(self,*args,**options):
        today=timezone.localdate()
        call_command('generate_monthly_fees')
        call_command('generate_monthly_quiz_reports')
        if today.day>=5: call_command('generate_fee_pending_reports')
        self.stdout.write(self.style.SUCCESS(f'Daily school jobs checked for {today}.'))
