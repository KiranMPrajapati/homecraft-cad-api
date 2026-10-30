import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
if os.getenv('DJANGO_LOAD_DOTENV', 'true').lower() == 'true':
    load_dotenv(BASE_DIR / '.env', override=False)

def flag(name, default='false'):
    return os.getenv(name, default).lower() == 'true'

def csv(name, default=''):
    return [x.strip() for x in os.getenv(name, default).split(',') if x.strip()]

DEBUG = flag('DJANGO_DEBUG')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    raise ImproperlyConfigured('Set DJANGO_SECRET_KEY before starting Django.')
ALLOWED_HOSTS = csv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver')
ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'
INSTALLED_APPS = ['corsheaders', 'rest_framework', 'cad_generator']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'corsheaders.middleware.CorsMiddleware', 'cad_generator.middleware.BodyLimitMiddleware', 'django.middleware.common.CommonMiddleware']
DATABASES = {}
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOWED_ORIGINS = csv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
CORS_ALLOW_CREDENTIALS = False
SECURE_SSL_REDIRECT = flag('DJANGO_SECURE_SSL_REDIRECT')
SECURE_HSTS_SECONDS = int(os.getenv('DJANGO_SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = flag('DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS')
SECURE_HSTS_PRELOAD = flag('DJANGO_SECURE_HSTS_PRELOAD')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
if flag('DJANGO_TRUST_PROXY_SSL'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DATA_UPLOAD_MAX_MEMORY_SIZE = 262144
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [], 'UNAUTHENTICATED_USER': None,
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': os.getenv('API_THROTTLE_RATE', '10/min')},
    'NUM_PROXIES': int(os.getenv('DJANGO_NUM_PROXIES', '0')),
}
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
OPENAI_TIMEOUT_SECONDS = max(1, min(60, float(os.getenv('OPENAI_TIMEOUT_SECONDS', '25'))))
GEOMETRY_REPAIR_RETRIES = max(0, min(2, int(os.getenv('GEOMETRY_REPAIR_RETRIES', '1'))))
LOGGING = {'version': 1, 'disable_existing_loggers': False, 'loggers': {'openai': {'level': 'WARNING'}, 'httpx': {'level': 'WARNING'}}}
