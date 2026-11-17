from datetime import date
from django.core.management.base import BaseCommand
from django.utils import timezone
from school.models import ClassRoom, FeeRecord, CampusPost, UserNotification
class Command(BaseCommand):
    help='Create idempotent class-wise pending-fee posts and teacher notifications.'
    def add_arguments(self,parser): parser.add_argument('--month',help='YYYY-MM, defaults to current month')
    def handle(self,*args,**options):
        today=timezone.localdate()
        if options['month']:
            try: year,month=map(int,options['month'].split('-')); first=date(year,month,1)
            except Exception: self.stderr.write('Use --month YYYY-MM');return
        else: first=today.replace(day=1)
        created=0
        for classroom in ClassRoom.objects.filter(is_active=True).select_related('incharge'):
            fees=FeeRecord.objects.filter(student__classroom=classroom,student__is_active=True,month=first).exclude(status='paid').select_related('student')
            names=[f'{f.student.roll_no} {f.student.full_name}' for f in fees]
            if not names: continue
            title=f'{classroom.name} fee pending — {first:%B %Y}'
            post,was_created=CampusPost.objects.get_or_create(title=title,post_type=CampusPost.Type.FEE,classroom=classroom,is_automatic=True,defaults={'body':f'{classroom.name}: {len(names)} students fee pending.\n'+'\n'.join(names),'author':None})
            created+=int(was_created)
            if was_created and classroom.incharge:
                UserNotification.objects.create(user=classroom.incharge,title='Pending fee report',body=f'In your class {classroom.name}, {len(names)} students fee is pending: '+', '.join(names),link='/fees')
        self.stdout.write(self.style.SUCCESS(f'Created {created} new pending fee posts for {first:%B %Y}.'))
