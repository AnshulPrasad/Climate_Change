from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-me-in-production'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'climate_dashboard.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'dashboard' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'climate_dashboard.wsgi.application'

STATIC_URL = '/static/'
STATICFILES_DIRS = []

MEDIA_URL = '/output/'
MEDIA_ROOT = BASE_DIR / 'output'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Google Earth Engine service account (set via environment or override here)
GEE_SERVICE_ACCOUNT = os.environ.get('GEE_SERVICE_ACCOUNT', '')
GEE_KEY_FILE = os.environ.get('GEE_KEY_FILE', '')