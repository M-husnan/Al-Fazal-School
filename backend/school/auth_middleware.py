from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.contrib.auth.models import AnonymousUser
class JwtQueryAuthMiddleware:
    """Short-lived JWT for browser WebSockets; use wss:// in production."""
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        scope=dict(scope); scope['user']=AnonymousUser()
        query=parse_qs(scope.get('query_string',b'').decode())
        token=query.get('token',[''])[0]
        if token:
            scope['user']=await self.get_user(token)
        return await self.app(scope,receive,send)
    @database_sync_to_async
    def get_user(self,raw):
        try:
            auth=JWTAuthentication(); validated=auth.get_validated_token(raw); return auth.get_user(validated)
        except Exception: return AnonymousUser()
