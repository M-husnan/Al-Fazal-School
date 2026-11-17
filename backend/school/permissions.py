from rest_framework.permissions import BasePermission, SAFE_METHODS
class PrincipalOnly(BasePermission):
    def has_permission(self, request, view): return bool(request.user and request.user.is_authenticated and request.user.is_principal)
class PrincipalOrTeacher(BasePermission):
    def has_permission(self, request, view): return bool(request.user and request.user.is_authenticated and (request.user.is_principal or request.user.role == 'teacher'))
class SchoolObjectPermission(BasePermission):
    def has_permission(self, request, view): return bool(request.user and request.user.is_authenticated)
    def has_object_permission(self, request, view, obj):
        user=request.user
        if user.is_principal: return True
        if hasattr(obj,'members'):
            return obj.members.filter(pk=user.pk).exists()
        if hasattr(obj,'room') and hasattr(obj.room,'members'):
            return obj.room.members.filter(pk=user.pk).exists()
        if hasattr(obj,'author_id') and obj.author_id == user.pk and getattr(obj,'classroom_id',None) is None:
            return True
        classroom=getattr(obj,'classroom',None)
        if classroom is None and hasattr(obj,'student'): classroom=obj.student.classroom
        if classroom is None and hasattr(obj,'quiz'): classroom=obj.quiz.classroom
        if classroom is None and hasattr(obj,'room') and obj.room.kind == 'class': classroom=obj.room.classroom
        return bool(classroom and classroom.incharge_id == user.id)
