from datetime import date
from django.core.management.base import BaseCommand
from django.utils import timezone
from school.models import FeeRecord, Student
class Command(BaseCommand):
    help='Create this month’s fee entry for each active student (safe to rerun).'
    def add_arguments(self,parser): parser.add_argument('--month',help='YYYY-MM, defaults to current month')
    def handle(self,*args,**options):
        today=timezone.localdate()
        if options['month']:
            try: year,month=map(int,options['month'].split('-')); first=date(year,month,1)
            except Exception: self.stderr.write('Use --month YYYY-MM');return
        else: first=today.replace(day=1)
        due=date(first.year,first.month,min(5,28))
        created=0
        for student in Student.objects.filter(is_active=True).select_related('classroom').iterator():
            _,was_created=FeeRecord.objects.get_or_create(student=student,month=first,defaults={'amount':student.classroom.monthly_fee,'due_date':due})
            created+=int(was_created)
        self.stdout.write(self.style.SUCCESS(f'Fee month {first:%B %Y}: created {created} new records; existing records unchanged.'))
