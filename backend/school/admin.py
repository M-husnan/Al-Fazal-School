from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from .models import User, ClassRoom, Student, FeeRecord, Quiz, QuizResult, Attendance, CampusPost, ChatRoom, Message, UserNotification

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets=BaseUserAdmin.fieldsets+(('School role',{'fields':('role','phone')}),)
    add_fieldsets=BaseUserAdmin.add_fieldsets+(('School role',{'fields':('role','phone')}),)
    list_display=('username','first_name','last_name','email','role','is_active','is_staff')
    list_filter=('role','is_active','is_staff')
    search_fields=('username','first_name','last_name','email','phone')

class StudentInline(admin.TabularInline):
    model=Student; extra=0; fields=('roll_no','admission_no','full_name','father_name','enrollment_status','is_active'); show_change_link=True
@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display=('name','grade','section','incharge','monthly_fee','is_active')
    search_fields=('name','grade','section','incharge__username')
    list_filter=('is_active','grade')
    inlines=[StudentInline]
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display=('admission_no','full_name','father_name','classroom','roll_no','enrollment_status','leaving_date','is_active')
    list_filter=('classroom','gender','enrollment_status','is_active')
    search_fields=('admission_no','full_name','father_name','roll_no','phone','guardian_phone')
    readonly_fields=('id','created_at','certificate_no')
    list_per_page=50

@admin.action(description='Mark selected fee records as paid')
def mark_fees_paid(modeladmin,request,queryset):
    if not request.user.is_superuser and request.user.role!='principal':
        modeladmin.message_user(request,'Only principal can mark fees paid.',level=messages.ERROR); return
    today=timezone.localdate()
    for fee in queryset.exclude(status='paid'):
        fee.status='paid';fee.paid_on=today;fee.marked_paid_by=request.user
        fee.receipt_no=fee.receipt_no or f'AF-{timezone.now():%y%m}-{fee.pk:08d}'
        fee.save()
    modeladmin.message_user(request,'Selected fee records marked as paid. Use each record’s slip link to print receipts.')
@admin.register(FeeRecord)
class FeeRecordAdmin(admin.ModelAdmin):
    list_display=('student','classroom','month','amount','status','due_date','paid_on','receipt_no')
    list_filter=('status','month','student__classroom')
    search_fields=('student__full_name','student__admission_no','receipt_no')
    readonly_fields=('receipt_no','paid_on','marked_paid_by','created_at')
    actions=[mark_fees_paid]
    @admin.display(description='Class')
    def classroom(self,obj): return obj.student.classroom

class QuizResultInline(admin.TabularInline):
    model=QuizResult; extra=0; autocomplete_fields=('student',)
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display=('title','subject','classroom','quiz_date','max_marks','created_by')
    list_filter=('classroom','quiz_date','subject')
    search_fields=('title','subject','classroom__name')
    inlines=[QuizResultInline]
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display=('student','classroom','date','status','marked_by')
    list_filter=('date','status','student__classroom')
    search_fields=('student__full_name','student__admission_no')
    @admin.display(description='Class')
    def classroom(self,obj): return obj.student.classroom
@admin.register(CampusPost)
class CampusPostAdmin(admin.ModelAdmin):
    list_display=('title','post_type','classroom','author','is_automatic','created_at')
    list_filter=('post_type','is_automatic','created_at')
    search_fields=('title','body','classroom__name')
@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display=('name','kind','classroom','created_by','created_at')
    list_filter=('kind','classroom')
    filter_horizontal=('members',)
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display=('room','sender','kind','sent_at')
    list_filter=('kind','sent_at')
    search_fields=('text','sender__username')
@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display=('user','title','is_read','created_at')
    list_filter=('is_read','created_at')
    search_fields=('user__username','title','body')
