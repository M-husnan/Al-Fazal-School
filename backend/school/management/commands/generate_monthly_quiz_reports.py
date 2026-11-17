from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, F, FloatField, ExpressionWrapper
from django.utils import timezone
from school.models import ClassRoom, Quiz, QuizResult, CampusPost, UserNotification
class Command(BaseCommand):
    help='Create idempotent monthly class quiz summary posts.'
    def add_arguments(self,parser): parser.add_argument('--month',help='YYYY-MM, defaults to previous month')
    def handle(self,*args,**options):
        today=timezone.localdate()
        if options['month']:
            try: year,month=map(int,options['month'].split('-')); first=date(year,month,1)
            except Exception: self.stderr.write('Use --month YYYY-MM');return
        else:
            first=(today.replace(day=1)-timedelta(days=1)).replace(day=1)
        last=date(first.year,first.month,__import__('calendar').monthrange(first.year,first.month)[1]);created=0
        for classroom in ClassRoom.objects.filter(is_active=True):
            results=QuizResult.objects.filter(quiz__classroom=classroom,quiz__quiz_date__range=(first,last)).select_related('quiz','student')
            if not results.exists(): continue
            student_scores=list(results.values('student_id','student__full_name').annotate(
                average=Avg(ExpressionWrapper(F('marks')*100.0/F('quiz__max_marks'),output_field=FloatField())),
                quiz_count=Count('id'),
            ).order_by('-average','student__full_name'))
            average=sum(float(row['average']) for row in student_scores)/len(student_scores)
            best=student_scores[0]; worst=student_scores[-1]
            title=f'{classroom.name} quiz report — {first:%B %Y}'
            body=(f'{classroom.name} monthly quiz performance for {first:%B %Y}.\n'
                  f'Class average: {average:.1f}% across {len(student_scores)} students.\n'
                  f'Topper: {best["student__full_name"]} ({best["average"]:.1f}%).\n'
                  f'Lowest: {worst["student__full_name"]} ({worst["average"]:.1f}%).\n\n'
                  'Student monthly averages:\n'+'\n'.join(f'{row["student__full_name"]}: {row["average"]:.1f}% ({row["quiz_count"]} quizzes)' for row in student_scores))
            post,was_created=CampusPost.objects.get_or_create(title=title,post_type=CampusPost.Type.QUIZ,classroom=classroom,is_automatic=True,defaults={'body':body})
            created+=int(was_created)
            if was_created and classroom.incharge: UserNotification.objects.create(user=classroom.incharge,title='Monthly quiz report published',body=title,link='/quizzes')
        self.stdout.write(self.style.SUCCESS(f'Created {created} quiz report posts for {first:%B %Y}.'))
