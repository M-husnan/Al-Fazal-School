import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

class User(AbstractUser):
    class Role(models.TextChoices):
        PRINCIPAL = 'principal', 'Principal'
        TEACHER = 'teacher', 'Teacher'
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.TEACHER)
    phone = models.CharField(max_length=30, blank=True)
    @property
    def is_principal(self): return self.is_superuser or self.role == self.Role.PRINCIPAL
    def save(self, *args, **kwargs):
        if self.is_superuser: self.role = self.Role.PRINCIPAL
        super().save(*args, **kwargs)

class ClassRoom(models.Model):
    name = models.CharField(max_length=60, help_text='Example: Class 10-A')
    grade = models.CharField(max_length=20, blank=True)
    section = models.CharField(max_length=20, blank=True)
    incharge = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='incharge_classes', limit_choices_to={'role':'teacher'})
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    class Meta:
        ordering = ['name']
        constraints=[models.UniqueConstraint(fields=['incharge'],condition=Q(incharge__isnull=False),name='one_class_per_teacher_incharge')]
    def __str__(self): return self.name

class Student(models.Model):
    class Gender(models.TextChoices): MALE='male','Male'; FEMALE='female','Female'; OTHER='other','Other'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admission_no = models.CharField(max_length=40, unique=True)
    full_name = models.CharField(max_length=160)
    father_name = models.CharField(max_length=160)
    picture = models.ImageField(upload_to='students/%Y/%m/', blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=8, choices=Gender.choices, blank=True)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.PROTECT, related_name='students')
    roll_no = models.CharField(max_length=30)
    admission_date = models.DateField(default=timezone.localdate)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    guardian_phone = models.CharField(max_length=30, blank=True)
    previous_school = models.CharField(max_length=180, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['classroom__name','roll_no']
        constraints = [models.UniqueConstraint(fields=['classroom','roll_no'], name='unique_roll_per_class')]
    def __str__(self): return f'{self.full_name} ({self.admission_no})'

class FeeRecord(models.Model):
    class Status(models.TextChoices): PENDING='pending','Pending'; PAID='paid','Paid'; LATE='late','Late'
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fees')
    month = models.DateField(help_text='Use first day of the fee month')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    paid_on = models.DateField(null=True, blank=True)
    receipt_no = models.CharField(max_length=40, unique=True, blank=True)
    marked_paid_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='fees_marked_paid')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-month','student__classroom__name','student__roll_no']
        constraints = [models.UniqueConstraint(fields=['student','month'], name='unique_student_fee_month')]
    @property
    def effective_status(self):
        if self.status == self.Status.PAID: return self.Status.PAID
        return self.Status.LATE if timezone.localdate() > self.due_date else self.Status.PENDING
    def __str__(self): return f'{self.student} - {self.month:%B %Y}'

class Quiz(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=160)
    subject = models.CharField(max_length=100, blank=True)
    quiz_date = models.DateField(default=timezone.localdate)
    max_marks = models.PositiveSmallIntegerField(default=100, validators=[MinValueValidator(1), MaxValueValidator(10000)])
    paper = models.FileField(upload_to='quiz-papers/%Y/%m/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='quizzes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-quiz_date','title']
    def __str__(self): return f'{self.classroom}: {self.title}'

class QuizResult(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_results')
    marks = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    remarks = models.CharField(max_length=255, blank=True)
    class Meta: constraints = [models.UniqueConstraint(fields=['quiz','student'], name='unique_quiz_student_result')]
    @property
    def percentage(self): return round(float(self.marks / self.quiz.max_marks * 100), 2) if self.quiz.max_marks else 0

class Attendance(models.Model):
    class Status(models.TextChoices): PRESENT='present','Present'; ABSENT='absent','Absent'; LEAVE='leave','Leave'
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PRESENT)
    marked_by = models.ForeignKey(User, on_delete=models.PROTECT)
    class Meta: constraints = [models.UniqueConstraint(fields=['student','date'], name='unique_attendance_student_date')]

class CampusPost(models.Model):
    class Type(models.TextChoices): NEWS='news','Campus News'; ANNOUNCEMENT='announcement','Announcement'; EVENT='event','Event'; FEE='fee_report','Fee Report'; QUIZ='quiz_report','Quiz Report'
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='campus_posts')
    classroom = models.ForeignKey(ClassRoom, null=True, blank=True, on_delete=models.CASCADE, related_name='posts')
    post_type = models.CharField(max_length=20, choices=Type.choices, default=Type.NEWS)
    title = models.CharField(max_length=180)
    body = models.TextField()
    image = models.ImageField(upload_to='campus-posts/%Y/%m/', blank=True, null=True)
    attachment = models.FileField(upload_to='campus-files/%Y/%m/', blank=True, null=True)
    is_automatic = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']

class ChatRoom(models.Model):
    class Kind(models.TextChoices): DIRECT='direct','Direct'; TEACHERS='teachers','All Teachers'; CLASS='class','Class Group'
    name = models.CharField(max_length=140, blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.DIRECT)
    classroom = models.ForeignKey(ClassRoom, null=True, blank=True, on_delete=models.CASCADE, related_name='chat_rooms')
    members = models.ManyToManyField(User, related_name='chat_rooms')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='rooms_created')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return self.name or f'Chat {self.pk}'

class Message(models.Model):
    class Kind(models.TextChoices): TEXT='text','Text'; IMAGE='image','Image'; PDF='pdf','PDF'; VOICE='voice','Voice note'; FILE='file','File'
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sent_messages')
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.TEXT)
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='chat/%Y/%m/', blank=True, null=True)
    seen_by = models.ManyToManyField(User, blank=True, related_name='seen_messages')
    sent_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['sent_at']

class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='school_notifications')
    title = models.CharField(max_length=160)
    body = models.TextField()
    link = models.CharField(max_length=250, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
