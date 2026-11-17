import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from school.auth_middleware import JwtQueryAuthMiddleware
from school.routing import websocket_urlpatterns
http_application=get_asgi_application()
application=ProtocolTypeRouter({'http':http_application,'websocket':JwtQueryAuthMiddleware(URLRouter(websocket_urlpatterns))})
