import os
from pathlib import Path
from decouple import config
from dotenv import load_dotenv


load_dotenv()

MICROSERVICE_API = os.getenv("MICROSERVICE_API", "http://54.237.196.120/api")

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='your-secret-key-here')

DEBUG = config('DEBUG', default=False, cast=bool)


# settings.py
DEFAULT_CHARSET = 'utf-8'
FILE_CHARSET = 'utf-8'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*', '192.168.x.x', '54.237.196.120', 'kifrealty.com', 'www.kifrealty.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
    'tinymce',
    'ckeditor',  # For rich text editing
    'ckeditor_uploader',  # For image uploads in editor
    'exclusive_properties',
    'django.contrib.sitemaps',
]

TINYMCE_DEFAULT_CONFIG = {
    "height": 500,
    "width": "100%",
    "menubar": "file edit view insert format tools table help",
    "plugins": "advlist autolink lists link image charmap print preview anchor "
               "searchreplace visualblocks code fullscreen "
               "insertdatetime media table paste code help wordcount",
    "toolbar": "undo redo | formatselect | "
               "bold italic backcolor | alignleft aligncenter "
               "alignright alignjustify | bullist numlist outdent indent | "
               "removeformat | help",
    "custom_undo_redo_levels": 10,
}


MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # compress responses
    'main.middleware.RemoveWWW',
    'main.middleware.UTF8EnforcementMiddleware',  # New UTF-8 middleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'kif_realty.urls'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Optional: Configure image processing settings
IMAGE_QUALITY = 85
MAX_IMAGE_SIZE = (1200, 800)

# Pagination settings
PAGINATE_BY = 6

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'main.context_processors.turnstile',
            ],
        },
    },
]

WSGI_APPLICATION = 'kif_realty.wsgi.application'

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
        'height': 300,
        'width': '100%',
        'removePlugins': 'stylesheetparser',
        'allowedContent': True,
        'extraPlugins': ','.join([
            'uploadimage',
            'div',
            'autolink',
            'autoembed',
            'embedsemantic',
            'autogrow',
            'widget',
            'lineutils',
            'clipboard',
            'dialog',
            'dialogui',
            'elementspath'
        ]),
    }
}

CKEDITOR_UPLOAD_PATH = "exclusive_properties/editor_uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_JQUERY_URL = 'https://ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min.js'

# Email configuration (for inquiry notifications)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'KIF Realty <noreply@kifrealty.com>'

# Celery configuration (for background tasks)
from celery.schedules import crontab

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=CELERY_BROKER_URL)
CELERY_TIMEZONE = 'Asia/Dubai'

CELERY_BEAT_SCHEDULE = {
    # Refresh the X-OPP property catalog + developers list every midnight.
    # Data is stored durably in the DB (ApiSnapshot), so the site always has
    # listings to serve — visitors never wait on an API rebuild.
    # (Primary refresh mechanism is the `refresh_xopp` cron job; this Celery
    # schedule only applies if a Celery worker+beat is running.)
    'refresh-xopp-cache': {
        'task': 'main.tasks.refresh_xopp_cache',
        'schedule': crontab(hour=0, minute=0),
    },
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'sitemap_cache_table',
    }
}

# --- Spam protection -------------------------------------------------------
# Cloudflare Turnstile. The site key is public (rendered into every form); the
# secret key must only ever live in .env on the server.
# Defaults are Cloudflare's documented TEST keys, which always pass - so the
# forms keep working before the real keys are in place. Replace both in .env.
TURNSTILE_SITE_KEY = config('TURNSTILE_SITE_KEY', default='1x00000000000000000000AA')
TURNSTILE_SECRET_KEY = config('TURNSTILE_SECRET_KEY',
                              default='1x0000000000000000000000000000000AA')

# Web3Forms access key. Previously hardcoded into every public page; it is now
# attached server-side so it is no longer exposed in the HTML.
WEB3FORMS_ACCESS_KEY = config('WEB3FORMS_ACCESS_KEY',
                              default='a2fcfc35-c47d-4e6b-8710-e0fa4bad892d')

# DATABASES = {
#      'default': {
#          'ENGINE': 'django.db.backends.postgresql',
#          'NAME': os.getenv('DB_NAME'),
#          'USER': os.getenv('DB_USER'),
#          'PASSWORD': os.getenv('DB_PASSWORD'),
#          'HOST': os.getenv('DB_HOST', 'localhost'),
#          'PORT': os.getenv('DB_PORT', '5432'),
#      }
# }

DATABASES = {
   'default': {
       'ENGINE': 'django.db.backends.sqlite3',
      'NAME': BASE_DIR / 'db.sqlite3',
   }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# External API Configuration
PROPERTIES_API_URL = f"{MICROSERVICE_API}/properties/filter/"
CITIES_API_URL = f"{MICROSERVICE_API}/cities/"
DEVELOPERS_API_URL = f"{MICROSERVICE_API}/developers/"
API_TIMEOUT = 8

# X-OPP Partner Property API (read-only partner catalog, X-API-Key auth)
XOPP_API_BASE = config('XOPP_API_BASE', default='https://www.x-opperp.com/api/v1/partner')
XOPP_API_KEY = config('XOPP_API_KEY', default='')
