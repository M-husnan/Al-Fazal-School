from rest_framework import serializers
from .models import User, ClassRoom, Student, FeeRecord, Quiz, QuizResult, Attendance, CampusPost, ChatRoom, Message, UserNotification

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User; fields=['id','username','first_name','last_name','email','phone','role','is_active']; read_only_fields=['role']
class TeacherCreateSerializer(serializers.ModelSerializer):
    password=serializers.CharField(write_only=True, min_length=10)
    class Meta:
        model=User; fields=['id','username','first_name','last_name','email','phone','password','role','is_active']; read_only_fields=['role']
    def create(self, validated_data):
        password=validated_data.pop('password'); user=User(**validated_data, role=User.Role.TEACHER); user.set_password(password); user.save(); return user
class ClassRoomSerializer(serializers.ModelSerializer):
    incharge_name=serializers.CharField(source='incharge.get_full_name', read_only=True)
    student_count=serializers.IntegerField(read_only=True)
    class Meta: model=ClassRoom; fields='__all__'
class StudentSerializer(serializers.ModelSerializer):
    picture = serializers.ImageField(required=False, allow_null=True)
    classroom_name = serializers.CharField(
        source='classroom.name',
        read_only=True
    )

    class Meta:
        model = Student
        fields = '__all__'
class FeeRecordSerializer(serializers.ModelSerializer):
    student_name=serializers.CharField(source='student.full_name', read_only=True)
    admission_no=serializers.CharField(source='student.admission_no', read_only=True)
    classroom_name=serializers.CharField(source='student.classroom.name', read_only=True)
    effective_status=serializers.CharField(read_only=True)
    class Meta: model=FeeRecord; fields='__all__'; read_only_fields=['receipt_no','paid_on','marked_paid_by','created_at']
class QuizResultSerializer(serializers.ModelSerializer):
    student_name=serializers.CharField(source='student.full_name', read_only=True)
    roll_no=serializers.CharField(source='student.roll_no', read_only=True)
    percentage=serializers.FloatField(read_only=True)
    quiz_title=serializers.CharField(source='quiz.title',read_only=True)
    quiz_date=serializers.DateField(source='quiz.quiz_date',read_only=True)
    max_marks=serializers.IntegerField(source='quiz.max_marks',read_only=True)
    class Meta: model=QuizResult; fields='__all__'
class QuizSerializer(serializers.ModelSerializer):
    classroom_name=serializers.CharField(source='classroom.name', read_only=True)
    created_by_name=serializers.CharField(source='created_by.get_full_name', read_only=True)
    results=QuizResultSerializer(many=True, read_only=True)
    class Meta: model=Quiz; fields='__all__'; read_only_fields=['created_by','created_at']
class AttendanceSerializer(serializers.ModelSerializer):
    student_name=serializers.CharField(source='student.full_name', read_only=True)
    class Meta: model=Attendance; fields='__all__'; read_only_fields=['marked_by']
class CampusPostSerializer(serializers.ModelSerializer):
    author_name=serializers.CharField(source='author.get_full_name', read_only=True)
    classroom_name=serializers.CharField(source='classroom.name', read_only=True)
    class Meta: model=CampusPost; fields='__all__'; read_only_fields=['author','is_automatic','created_at']
class MessageSerializer(serializers.ModelSerializer):
    sender_name=serializers.CharField(source='sender.get_full_name', read_only=True)
    seen_count=serializers.IntegerField(source='seen_by.count', read_only=True)
    class Meta: model=Message; fields='__all__'; read_only_fields=['sender','seen_by','sent_at']
class ChatRoomSerializer(serializers.ModelSerializer):
    member_names=serializers.SerializerMethodField()
    latest_message=serializers.SerializerMethodField()
    class Meta: model=ChatRoom; fields='__all__'; read_only_fields=['created_by','created_at']
    def get_member_names(self,obj): return [u.get_full_name() or u.username for u in obj.members.all()]
    def get_latest_message(self,obj):
        m=obj.messages.select_related('sender').order_by('-sent_at').first()
        return MessageSerializer(m,context=self.context).data if m else None
class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta: model=UserNotification; fields='__all__'; read_only_fields=['user','created_at']
