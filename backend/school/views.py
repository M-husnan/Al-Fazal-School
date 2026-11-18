import calendar
import uuid
from datetime import date
from decimal import Decimal
from io import BytesIO
from django.db.models import Count, Sum, Avg, Q, F, FloatField, ExpressionWrapper
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .models import User, ClassRoom, Student, FeeRecord, Quiz, QuizResult, Attendance, CampusPost, ChatRoom, Message, UserNotification
from .serializers import (UserSerializer, TeacherCreateSerializer, ClassRoomSerializer, StudentSerializer,
 FeeRecordSerializer, QuizSerializer, QuizResultSerializer, AttendanceSerializer, CampusPostSerializer,
 ChatRoomSerializer, MessageSerializer, UserNotificationSerializer)
from .permissions import SchoolObjectPermission

class ScopedViewSet(viewsets.ModelViewSet):
    permission_classes=[SchoolObjectPermission]
    def is_principal(self): return self.request.user.is_principal
    def own_classes(self): return ClassRoom.objects.filter(incharge=self.request.user)
    def restrict_classrooms(self, qs, field='classroom'):
        return qs if self.is_principal() else qs.filter(**{f'{field}__in':self.own_classes()})

class ClassRoomViewSet(ScopedViewSet):
    serializer_class=ClassRoomSerializer
    def get_queryset(self):
        qs=ClassRoom.objects.annotate(student_count=Count('students',filter=Q(students__is_active=True))).select_related('incharge')
        return qs if self.is_principal() else qs.filter(incharge=self.request.user)
    def create(self,request,*args,**kwargs):
        if not self.is_principal(): raise PermissionDenied()
        return super().create(request,*args,**kwargs)
    def update(self,request,*args,**kwargs):
        if not self.is_principal(): raise PermissionDenied()
        return super().update(request,*args,**kwargs)
    def destroy(self,request,*args,**kwargs):
        if not self.is_principal(): raise PermissionDenied()
        return super().destroy(request,*args,**kwargs)

class TeacherViewSet(viewsets.ModelViewSet):
    serializer_class=TeacherCreateSerializer
    permission_classes=[IsAuthenticated]
    def get_queryset(self):
        if not self.request.user.is_principal:
            return User.objects.filter(is_active=True).filter(Q(role=User.Role.TEACHER)|Q(role=User.Role.PRINCIPAL)|Q(is_superuser=True)).order_by('role','first_name','username')
        return User.objects.filter(role=User.Role.TEACHER).order_by('first_name','username')
    def get_permissions(self):
        if self.action in ('list','retrieve'):
            return [IsAuthenticated()]
        from .permissions import PrincipalOnly
        return [PrincipalOnly()]
    def get_serializer_class(self): return UserSerializer if self.action in ('list','retrieve') else TeacherCreateSerializer

class StudentViewSet(ScopedViewSet):
    serializer_class=StudentSerializer
    def get_queryset(self):
        include_inactive=self.request.query_params.get('include_inactive')=='true' and self.is_principal()
        qs=Student.objects.select_related('classroom')
        if not include_inactive: qs=qs.filter(is_active=True)
        qs=self.restrict_classrooms(qs)
        class_id=self.request.query_params.get('classroom')
        if class_id: qs=qs.filter(classroom_id=class_id)
        term=self.request.query_params.get('search','').strip()
        if term: qs=qs.filter(Q(full_name__icontains=term)|Q(father_name__icontains=term)|Q(admission_no__icontains=term)|Q(roll_no__icontains=term))
        return qs
    def perform_create(self,serializer):
        c=serializer.validated_data.get('classroom')
        if not self.is_principal() and c.incharge_id != self.request.user.id: raise PermissionDenied('You can only add students to your assigned class.')
        serializer.save()
    def perform_update(self,serializer):
        c=serializer.validated_data.get('classroom', serializer.instance.classroom)
        if not self.is_principal() and c.incharge_id != self.request.user.id: raise PermissionDenied()
        serializer.save()
    def destroy(self,request,*args,**kwargs):
        student=self.get_object()
        if not self.is_principal(): raise PermissionDenied('Only the principal can delete a student.')
        student.is_active=False; student.save(update_fields=['is_active']); return Response(status=status.HTTP_204_NO_CONTENT)
    @action(detail=True,methods=['post'])
    def mark_leaving(self,request,pk=None):
        if not self.is_principal(): raise PermissionDenied('Only the principal can record a student leaving.')
        student=self.get_object()
        leaving_status=request.data.get('enrollment_status','left')
        allowed={Student.EnrollmentStatus.LEFT,Student.EnrollmentStatus.TRANSFERRED,Student.EnrollmentStatus.GRADUATED}
        if leaving_status not in allowed: raise ValidationError({'enrollment_status':'Choose left, transferred, or graduated.'})
        leaving_date=request.data.get('leaving_date')
        if not leaving_date: raise ValidationError({'leaving_date':'A leaving date is required.'})
        from django.utils.dateparse import parse_date
        parsed_date=parse_date(str(leaving_date))
        if not parsed_date: raise ValidationError({'leaving_date':'Use YYYY-MM-DD.'})
        student.enrollment_status=leaving_status
        student.leaving_date=parsed_date
        student.leaving_reason=str(request.data.get('leaving_reason','')).strip()[:255]
        student.certificate_no=student.certificate_no or f'AF-{timezone.localdate():%Y}-SLC-{uuid.uuid4().hex[:8].upper()}'
        student.is_active=False
        student.save(update_fields=['enrollment_status','leaving_date','leaving_reason','certificate_no','is_active'])
        return Response(self.get_serializer(student).data)
    @action(detail=True,methods=['get'])
    def leaving_certificate(self,request,pk=None):
        if not self.is_principal(): raise PermissionDenied('Only the principal can issue a leaving certificate.')
        student=self.get_object()
        if student.enrollment_status==Student.EnrollmentStatus.ACTIVE or not student.certificate_no:
            return Response({'detail':'Record the student leaving before issuing a certificate.'},status=400)
        buf=BytesIO(); pdf=canvas.Canvas(buf,pagesize=A4); pdf.setTitle('School Leaving Certificate')
        pdf.setFont('Helvetica-Bold',18); pdf.drawCentredString(297,790,'Al-Fazal Higher Secondary School')
        pdf.setFont('Helvetica',10); pdf.drawCentredString(297,772,'G.M Abad, Faisalabad')
        pdf.line(55,754,540,754); pdf.setFont('Helvetica-Bold',16); pdf.drawCentredString(297,720,'SCHOOL LEAVING CERTIFICATE')
        pdf.setFont('Helvetica',10); pdf.drawRightString(535,690,f'Certificate No: {student.certificate_no}')
        lines=[('This is to certify that', ''),('Student name',student.full_name),('Father name',student.father_name),('Admission number',student.admission_no),('Class / roll number',f'{student.classroom.name} / {student.roll_no}'),('Date of admission',str(student.admission_date)),('Date of leaving',str(student.leaving_date)),('Status',student.get_enrollment_status_display()),('Reason',student.leaving_reason or 'Not specified')]
        y=650
        for label,value in lines:
            pdf.setFont('Helvetica-Bold' if value else 'Helvetica-Oblique',11)
            pdf.drawString(70,y,label if not value else f'{label}:')
            if value:
                pdf.setFont('Helvetica',11); pdf.drawString(220,y,str(value)[:55])
            y-=30
        pdf.setFont('Helvetica',10); pdf.drawString(70,350,'The student named above has been relieved from the school records.')
        pdf.line(370,205,520,205); pdf.setFont('Helvetica',10); pdf.drawCentredString(445,188,'Principal signature and stamp')
        pdf.showPage(); pdf.save(); buf.seek(0)
        return FileResponse(buf,as_attachment=True,filename=f'leaving-certificate-{student.admission_no}.pdf',content_type='application/pdf')
    @action(detail=True,methods=['get'])
    def profile(self,request,pk=None):
        s=self.get_object(); today=timezone.localdate(); fees=FeeRecord.objects.filter(student=s,month__gte=today.replace(day=1).replace(year=today.year-1)).order_by('-month')
        results=QuizResult.objects.filter(student=s).select_related('quiz').order_by('-quiz__quiz_date')
        attendance=Attendance.objects.filter(student=s,date__gte=today.replace(year=today.year-1)).values('status').annotate(total=Count('id'))
        monthly=results.annotate(year=ExtractYear('quiz__quiz_date'),month=ExtractMonth('quiz__quiz_date')).values('year','month').annotate(average=Avg(ExpressionWrapper(F('marks')*100.0/F('quiz__max_marks'),output_field=FloatField())),total=Count('id')).order_by('year','month')
        return Response({'student':self.get_serializer(s).data,'fees':FeeRecordSerializer(fees,many=True).data,'quiz_results':QuizResultSerializer(results,many=True).data,'monthly_performance':list(monthly),'attendance_summary':list(attendance)})

class FeeViewSet(ScopedViewSet):
    serializer_class=FeeRecordSerializer
    http_method_names=['get','post','patch','head','options']
    def get_queryset(self):
        qs=FeeRecord.objects.select_related('student','student__classroom','marked_paid_by')
        if not self.is_principal(): qs=qs.filter(student__classroom__incharge=self.request.user)
        class_id=self.request.query_params.get('classroom')
        if class_id: qs=qs.filter(student__classroom_id=class_id)
        if self.request.query_params.get('status')=='pending': qs=qs.exclude(status='paid')
        return qs
    def create(self,request,*args,**kwargs):
        if not self.is_principal(): raise PermissionDenied('Only the principal can create or adjust fee records.')
        return super().create(request,*args,**kwargs)
    def partial_update(self,request,*args,**kwargs):
        obj=self.get_object()
        if not self.is_principal(): raise PermissionDenied('Only the principal can update or mark fees paid.')
        if request.data.get('status')=='paid':
            obj.status='paid'; obj.paid_on=timezone.localdate(); obj.marked_paid_by=request.user
            if not obj.receipt_no: obj.receipt_no=f'AF-{timezone.now():%y%m}-'+uuid.uuid4().hex[:8].upper()
            obj.save(); return Response(self.get_serializer(obj).data)
        return super().partial_update(request,*args,**kwargs)
    @action(detail=True,methods=['get'])
    def slip(self,request,pk=None):
        fee=self.get_object()
        if fee.status!='paid': return Response({'detail':'A fee slip is available after payment is marked paid.'},status=400)
        return fee_slip_response(fee)

def fee_slip_response(fee):
    buf=BytesIO(); p=canvas.Canvas(buf,pagesize=A4)
    p.setTitle(f'Fee Slip {fee.receipt_no}')
    p.setFont('Helvetica-Bold',16); p.drawCentredString(297,790,'Al-Fazal Higher Secondary School')
    p.setFont('Helvetica',10); p.drawCentredString(297,773,'G.M Abad, Faisalabad')
    p.line(50,758,545,758)
    values=[('Receipt No.',fee.receipt_no),('Student',fee.student.full_name),('Father Name',fee.student.father_name),('Admission No.',fee.student.admission_no),('Class',fee.student.classroom.name),('Fee Month',fee.month.strftime('%B %Y')),('Amount',f'PKR {fee.amount:,.2f}'),('Payment Date',str(fee.paid_on or ''))]
    y=720
    for label,value in values:
        p.setFont('Helvetica-Bold',11);p.drawString(70,y,label+':')
        p.setFont('Helvetica',11);p.drawString(190,y,str(value));y-=34
    p.line(50,420,545,420);p.setFont('Helvetica-Oblique',9);p.drawString(70,400,'Fee received. Please retain this slip for your records.')
    p.showPage();p.save();buf.seek(0)
    return FileResponse(buf,as_attachment=True,filename=f'fee-slip-{fee.receipt_no}.pdf',content_type='application/pdf')

class QuizViewSet(ScopedViewSet):
    serializer_class=QuizSerializer
    def get_queryset(self):
        qs=Quiz.objects.select_related('classroom','created_by').prefetch_related('results__student')
        return qs if self.is_principal() else qs.filter(classroom__incharge=self.request.user)
    def perform_create(self,serializer):
        c=serializer.validated_data['classroom']
        if not self.is_principal() and c.incharge_id!=self.request.user.id: raise PermissionDenied('Create quizzes only for your assigned class.')
        serializer.save(created_by=self.request.user)
    @action(detail=True,methods=['post','get'])
    def results(self,request,pk=None):
        quiz=self.get_object()
        if request.method=='GET': return Response(QuizResultSerializer(quiz.results.select_related('student'),many=True).data)
        if not self.is_principal() and quiz.classroom.incharge_id!=request.user.id: raise PermissionDenied()
        rows=request.data.get('results',[])
        if not isinstance(rows,list): raise ValidationError({'results':'Send a list of student_id and marks.'})
        saved=[]
        for row in rows:
            student=get_object_or_404(Student,pk=row.get('student_id'),classroom=quiz.classroom,is_active=True)
            marks=Decimal(str(row.get('marks',0)))
            if marks<0 or marks>quiz.max_marks: raise ValidationError(f'Marks for {student.full_name} must be between 0 and {quiz.max_marks}.')
            result,_=QuizResult.objects.update_or_create(quiz=quiz,student=student,defaults={'marks':marks,'remarks':row.get('remarks','')})
            saved.append(result)
        return Response(QuizResultSerializer(saved,many=True).data,status=201)

class AttendanceViewSet(ScopedViewSet):
    serializer_class=AttendanceSerializer
    @action(detail=False,methods=['post'])
    def bulk(self,request):
        from django.db import transaction
        rows=request.data.get('records',[]); day=request.data.get('date') or timezone.localdate()
        if not isinstance(rows,list): raise ValidationError({'records':'Send a list of student_id and status.'})
        saved=[]
        with transaction.atomic():
            for row in rows:
                if row.get('status','present') not in Attendance.Status.values: raise ValidationError({'status':'Use present, absent or leave.'})
                student=get_object_or_404(Student,pk=row.get('student_id'),is_active=True)
                if not request.user.is_principal and student.classroom.incharge_id!=request.user.id: raise PermissionDenied()
                obj,_=Attendance.objects.update_or_create(student=student,date=day,defaults={'status':row.get('status','present'),'marked_by':request.user})
                saved.append(obj)
        return Response(AttendanceSerializer(saved,many=True).data)
    def get_queryset(self):
        qs=Attendance.objects.select_related('student','student__classroom','marked_by')
        if not self.is_principal(): qs=qs.filter(student__classroom__incharge=self.request.user)
        class_id=self.request.query_params.get('classroom'); day=self.request.query_params.get('date')
        if class_id: qs=qs.filter(student__classroom_id=class_id)
        if day: qs=qs.filter(date=day)
        return qs
    def perform_create(self,serializer):
        s=serializer.validated_data['student']
        if not self.is_principal() and s.classroom.incharge_id!=self.request.user.id: raise PermissionDenied()
        serializer.save(marked_by=self.request.user)

class CampusPostViewSet(ScopedViewSet):
    serializer_class=CampusPostSerializer
    def get_queryset(self):
        qs=CampusPost.objects.select_related('author','classroom')
        return qs if self.is_principal() else qs.filter(Q(classroom__incharge=self.request.user)|Q(classroom__isnull=True))
    def perform_create(self,serializer):
        classroom=serializer.validated_data.get('classroom')
        if not self.is_principal() and classroom and classroom.incharge_id!=self.request.user.id: raise PermissionDenied('You can only post to your assigned class.')
        serializer.save(author=self.request.user)
    def perform_update(self,serializer):
        if serializer.instance.is_automatic or (not self.is_principal() and serializer.instance.author_id!=self.request.user.id): raise PermissionDenied()
        serializer.save()
    def destroy(self,request,*args,**kwargs):
        obj=self.get_object()
        if obj.is_automatic or (not self.is_principal() and obj.author_id!=request.user.id): raise PermissionDenied()
        return super().destroy(request,*args,**kwargs)

class ChatRoomViewSet(ScopedViewSet):
    serializer_class=ChatRoomSerializer
    def get_queryset(self): return ChatRoom.objects.filter(members=self.request.user).prefetch_related('members','messages').distinct()
    def perform_create(self,serializer):
        member_ids=self.request.data.get('member_ids',[])
        users=User.objects.filter(id__in=member_ids,is_active=True).exclude(pk=self.request.user.pk)
        if users.exclude(role__in=[User.Role.TEACHER,User.Role.PRINCIPAL]).exclude(is_superuser=True).exists(): raise PermissionDenied('Only teachers and principals can join staff chats.')
        classroom=serializer.validated_data.get('classroom')
        if serializer.validated_data.get('kind')=='class':
            if not classroom: raise ValidationError({'classroom':'Select a class for a class group.'})
            if not self.is_principal() and classroom.incharge_id!=self.request.user.id: raise PermissionDenied()
        kind=serializer.validated_data.get('kind')
        if kind=='direct' and users.count()!=1: raise ValidationError({'member_ids':'A direct chat needs exactly one other teacher or principal.'})
        room=serializer.save(created_by=self.request.user)
        room.members.add(self.request.user)
        if kind=='class':
            if room.classroom.incharge_id: room.members.add(room.classroom.incharge)
            room.members.add(*User.objects.filter(Q(is_superuser=True)|Q(role=User.Role.PRINCIPAL),is_active=True))
        elif kind=='teachers':
            room.members.add(*User.objects.filter(Q(role=User.Role.TEACHER)|Q(role=User.Role.PRINCIPAL)|Q(is_superuser=True),is_active=True))
        else: room.members.add(*users)
    @action(detail=True,methods=['post'])
    def mark_seen(self,request,pk=None):
        room=self.get_object(); qs=room.messages.exclude(sender=request.user)
        for message in qs: message.seen_by.add(request.user)
        return Response({'marked':qs.count()})

class MessageViewSet(ScopedViewSet):
    serializer_class=MessageSerializer
    def get_queryset(self):
        qs=Message.objects.filter(room__members=self.request.user).select_related('sender','room').prefetch_related('seen_by')
        room_id=self.request.query_params.get('room')
        return qs.filter(room_id=room_id) if room_id else qs
    def perform_create(self,serializer):
        room=get_object_or_404(ChatRoom,pk=self.request.data.get('room'),members=self.request.user)
        message=serializer.save(sender=self.request.user,room=room)
        message.seen_by.add(self.request.user)
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        async_to_sync(get_channel_layer().group_send)(f'school_chat_{room.pk}',{'type':'chat.message','message':MessageSerializer(message,context={'request':self.request}).data})
    def destroy(self,request,*args,**kwargs):
        obj=self.get_object()
        if obj.sender_id!=request.user.id and not request.user.is_principal: raise PermissionDenied()
        return super().destroy(request,*args,**kwargs)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response({'id':request.user.id,'username':request.user.username,'name':request.user.get_full_name(),'role':'principal' if request.user.is_principal else request.user.role,'phone':request.user.phone,'email':request.user.email})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    u=request.user; today=timezone.localdate(); month=today.replace(day=1)
    classes=ClassRoom.objects.all() if u.is_principal else ClassRoom.objects.filter(incharge=u)
    students=Student.objects.filter(classroom__incharge=u,is_active=True) if not u.is_principal else Student.objects.filter(is_active=True)
    fees=FeeRecord.objects.filter(student__in=students,month=month)
    quizzes=Quiz.objects.filter(classroom__in=classes,quiz_date__year=today.year,quiz_date__month=today.month)
    return Response({'role':'principal' if u.is_principal else 'teacher','students':students.count(),'teachers':User.objects.filter(role='teacher',is_active=True).count() if u.is_principal else None,'classes':ClassRoomSerializer(classes.annotate(student_count=Count('students',filter=Q(students__is_active=True))),many=True).data,'fee_collected':str(fees.filter(status='paid').aggregate(v=Sum('amount'))['v'] or 0),'fee_pending':str(fees.exclude(status='paid').aggregate(v=Sum('amount'))['v'] or 0),'pending_fee_students':fees.exclude(status='paid').count(),'quizzes_this_month':quizzes.count(),'recent_posts':CampusPostSerializer(CampusPost.objects.filter(Q(classroom__in=classes)|Q(classroom__isnull=True))[:8],many=True,context={'request':request}).data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pdf_report(request,kind):
    user=request.user
    if kind not in ('fees','quiz','class'): return Response({'detail':'Unknown report.'},status=404)
    today=timezone.localdate()
    requested_date=request.query_params.get('date')
    report_date=today
    if requested_date:
        from django.utils.dateparse import parse_date
        report_date=parse_date(requested_date)
        if not report_date: return Response({'detail':'Use date format YYYY-MM-DD.'},status=400)
    requested_class=request.query_params.get('classroom')
    classrooms=ClassRoom.objects.all() if user.is_principal else ClassRoom.objects.filter(incharge=user)
    if requested_class:
        classrooms=classrooms.filter(pk=requested_class)
        if not classrooms.exists(): raise PermissionDenied('You can only download reports for your assigned class.')
    buf=BytesIO(); p=canvas.Canvas(buf,pagesize=A4); p.setTitle(f'{kind.title()} report')
    p.setFont('Helvetica-Bold',16);p.drawCentredString(297,800,'Al-Fazal Higher Secondary School')
    p.setFont('Helvetica',10);p.drawCentredString(297,782,'G.M Abad, Faisalabad');p.setFont('Helvetica-Bold',13);p.drawString(48,746,f'{kind.title()} Report - {report_date:%d %B %Y}')
    y=714
    def next_page(title):
        nonlocal y
        p.showPage(); y=800; p.setFont('Helvetica-Bold',12); p.drawString(48,y,f'Al-Fazal Higher Secondary School - {title} (continued)'); y-=28
    if kind=='fees':
        qs=FeeRecord.objects.select_related('student','student__classroom')
        if not user.is_principal: qs=qs.filter(student__classroom__incharge=user)
        qs=qs.filter(month=report_date.replace(day=1),student__classroom__in=classrooms).order_by('student__classroom__name','student__roll_no')
        paid=qs.filter(status='paid').aggregate(total=Sum('amount'),count=Count('id'))
        pending=qs.exclude(status='paid').aggregate(total=Sum('amount'),count=Count('id'))
        p.setFont('Helvetica-Bold',10);p.drawString(48,y,f'Paid: {paid["count"]} records / PKR {paid["total"] or 0}    Pending or late: {pending["count"]} records / PKR {pending["total"] or 0}');y-=25
        for f in qs:
            p.setFont('Helvetica',9);p.drawString(48,y,f'{f.student.classroom.name} | {f.student.full_name[:24]} | {f.effective_status.title()} | PKR {f.amount}');y-=13
            if y<45: next_page('Fee Report')
    elif kind=='quiz':
        quiz_id=request.query_params.get('quiz_id')
        if quiz_id:
            selected_quiz=Quiz.objects.filter(pk=quiz_id,classroom__in=classrooms).select_related('classroom').first()
            if not selected_quiz: raise PermissionDenied('You can only download reports for quizzes in your assigned class.')
            report_date=selected_quiz.quiz_date
            quizzes=Quiz.objects.filter(pk=selected_quiz.pk)
        else:
            quizzes=Quiz.objects.filter(classroom__in=classrooms,quiz_date__year=report_date.year,quiz_date__month=report_date.month).select_related('classroom').prefetch_related('results__student').order_by('classroom__name','quiz_date','title')
        if not quizzes.exists(): p.setFont('Helvetica',10);p.drawString(48,y,'No quizzes were recorded for this month.')
        for quiz in quizzes:
            p.setFont('Helvetica-Bold',11);p.drawString(48,y,f'{quiz.classroom.name} - {quiz.title[:35]} ({quiz.subject or "General"})');y-=16
            p.setFont('Helvetica',9);p.drawString(58,y,f'Date: {quiz.quiz_date:%d %b %Y} | Maximum marks: {quiz.max_marks}');y-=15
            p.setFont('Helvetica-Bold',9);p.drawString(58,y,'Roll');p.drawString(100,y,'Student');p.drawRightString(470,y,'Marks');p.drawRightString(535,y,'Percent');y-=13
            results={r.student_id:r for r in quiz.results.all()}
            for student in quiz.classroom.students.filter(is_active=True).order_by('roll_no'):
                result=results.get(student.pk); marks=f'{result.marks:g}' if result else 'Not entered'; percent=f'{result.percentage:.1f}%' if result else '-'
                p.setFont('Helvetica',9);p.drawString(58,y,str(student.roll_no)[:10]);p.drawString(100,y,student.full_name[:42]);p.drawRightString(470,y,marks);p.drawRightString(535,y,percent);y-=13
                if y<50: next_page('Quiz Report')
            y-=15
            if y<50: next_page('Quiz Report')
    else:
        p.setFont('Helvetica-Bold',9);p.drawString(48,y,'Class');p.drawString(100,y,'Roll');p.drawString(145,y,'Student');p.drawString(470,y,'Attendance');y-=16
        for c in classrooms:
            attendance={row.student_id:row.status for row in Attendance.objects.filter(student__classroom=c,date=report_date).only('student_id','status')}
            for student in c.students.filter(is_active=True).order_by('roll_no'):
                p.setFont('Helvetica',9);p.drawString(48,y,c.name[:12]);p.drawString(100,y,str(student.roll_no)[:12]);p.drawString(145,y,student.full_name[:45]);p.drawString(470,y,attendance.get(student.pk,'Not marked').title());y-=14
                if y<45: next_page('Attendance Report')
        if not classrooms.exists(): p.setFont('Helvetica',10);p.drawString(48,y,'No assigned class was found for this account.')
    p.showPage();p.save();buf.seek(0)
    return FileResponse(buf,as_attachment=True,filename=f'{kind}-report-{report_date:%Y-%m-%d}.pdf',content_type='application/pdf')


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=UserNotificationSerializer
    permission_classes=[IsAuthenticated]
    def get_queryset(self): return UserNotification.objects.filter(user=self.request.user)
    @action(detail=True,methods=['post'])
    def mark_read(self,request,pk=None):
        item=self.get_object();item.is_read=True;item.save(update_fields=['is_read']);return Response(self.get_serializer(item).data)
