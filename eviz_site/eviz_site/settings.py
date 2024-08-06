"""
Django settings for eviz_site project.

Generated by 'django-admin startproject' using Django 5.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path
from os import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = environ["django_secret_key"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_FAILURE_VIEW = "eviz.views.error_pages.csrf_failure"

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "eviz"
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eviz_site.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ "./templates" ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'eviz_site.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "OPTIONS": {
            "service": "MexerDB",
            # All other information provided through environment variables
            # PGSERVICEFILE and PGPASSFILE
            "application_name": "Mexer Site"
        }
    },
    "sandbox": {
        "ENGINE": "django.db.backends.postgresql",
        "OPTIONS": {
            "service": "SandboxDB",
            "application_name": "Mexer Site"
        }
    },
    'users': {
        'ENGINE': 'django.db.backends.postgresql',
        "OPTIONS":{
            "service": "users",
            "application_name": "Mexer Site"
        }
    }

}

DATABASE_ROUTERS = ["eviz.routers.DatabaseRouter"]


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
    BASE_DIR / "static/css",
    BASE_DIR / "static/js",
]
STATIC_BASE = BASE_DIR / "static"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CSRF_TRUSTED_ORIGINS = ['https://eviz.cs.calvin.edu', "https://*.mexer.site"]


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = "sandbox.smtp.mailtrap.io" # email host for the test smtp server
EMAIL_HOST = "live.smtp.mailtrap.io"
EMAIL_PORT = 587
EMAIL_HOST_USER = "api"
EMAIL_HOST_PASSWORD = environ["email_password"]
EMAIL_USE_TLS = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[{asctime}] {levelname} (File:{filename} Function:{funcName} Line:{lineno}) {message}",
            "style": "{" # '{' to format above string
        }
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": "general.log",
            "formatter": "default"
        }
    },
    "loggers": {
        "eviz_default": {
            "level": "DEBUG",
            "handlers": ["file"]
        } 
    }
}

SANKEY_COLORS_PATH = BASE_DIR / "internal_resources" / "sankey_color_categories.json"

SANDBOX_PREFIX = "sDB:"

IEA_TABLES = ["CL-PFU IEA", "CL-PFU IEA+MW"]