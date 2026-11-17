from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from school import views

router = DefaultRouter()
for prefix, view, basename in [
 ('classes', views.ClassRoomViewSet, 'class'), ('teachers', views.TeacherViewSet, 'teacher'),
 ('students', views.StudentViewSet, 'student'), ('fees', views.FeeViewSet, 'fee'),
 ('quizzes', views.QuizViewSet, 'quiz'), ('posts', views.CampusPostViewSet, 'post'),
 ('attendance', views.AttendanceViewSet, 'attendance'), ('chat-rooms', views.ChatRoomViewSet, 'chat-room'),
 ('messages', views.MessageViewSet, 'message'), ('notifications', views.NotificationViewSet, 'notification'),
]: router.register(prefix, view, basename=basename)
urlpatterns = [
 path('admin/', admin.site.urls),
 path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
 path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
 path('api/auth/me/', views.me, name='me'), path('api/dashboard/', views.dashboard, name='dashboard'),
 path('api/reports/<str:kind>.pdf', views.pdf_report, name='pdf_report'),
 path('api/', include(router.urls)),
]
if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
