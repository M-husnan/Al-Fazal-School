import os
from pathlib import Path
from datetime import timedelta
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / '.env')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-change-me-before-deployment')
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = [x.strip() for x in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if x.strip()]
INSTALLED_APPS = [
    'daphne', 'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'corsheaders', 'channels', 'cloudinary', 'school.apps.SchoolConfig',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
DATABASES = {'default': dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=600, ssl_require=os.getenv('DATABASE_SSL_REQUIRED', 'false').lower() == 'true')}
AUTH_USER_MODEL = 'school.User'
AUTH_PASSWORD_VALIDATORS = [
 {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
 {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator'},
 {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
 {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Karachi'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
if os.getenv('AWS_STORAGE_BUCKET_NAME'):
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': os.environ['AWS_STORAGE_BUCKET_NAME'],
            'endpoint_url': os.getenv('AWS_S3_ENDPOINT_URL') or None,
            'region_name': os.getenv('AWS_S3_REGION_NAME') or None,
            'access_key': os.getenv('AWS_ACCESS_KEY_ID') or None,
            'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY') or None,
        },
    }
    MEDIA_URL = os.getenv('AWS_MEDIA_URL', MEDIA_URL)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = [x.strip() for x in os.getenv('CORS_ALLOWED_ORIGINS','http://localhost:5173').split(',') if x.strip()]
REST_FRAMEWORK = {
 'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework_simplejwt.authentication.JWTAuthentication'],
 'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
 'DEFAULT_PAGINATION_CLASS':'school.pagination.CappedPageNumberPagination', 'PAGE_SIZE':50,
}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME':timedelta(minutes=30),'REFRESH_TOKEN_LIFETIME':timedelta(days=7),'ROTATE_REFRESH_TOKENS':True}
REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
 CHANNEL_LAYERS = {'default': {'BACKEND':'channels_redis.core.RedisChannelLayer','CONFIG':{'hosts':[REDIS_URL]}}}
else:
 CHANNEL_LAYERS = {'default': {'BACKEND':'channels.layers.InMemoryChannelLayer'}}
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

