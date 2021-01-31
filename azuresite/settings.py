"""
Django settings for azuresite project.

Generated by 'django-admin startproject' using Django 2.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

from pathlib import Path
import logging
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '-^rq(x*d--6_#635*j84d5(fz9@-3(9vdr_s$9+^@cw08dq(ja'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    #'polls.apps.PollsConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #koala-lms
    'taggit',  # Manage tags on objects
    'learning',  # The learning application itself
    'markdownx',  # To render Markdown documents
    'django_bootstrap_breadcrumbs',  # Display breadcrumbs using bootstrap
    'django_countries',  # Mainly to display country flags
    'accounts',
    # Theming
    'bootstrap',
    'fontawesome',
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

ROOT_URLCONF = 'azuresite.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'azuresite.wsgi.application'

AUTH_USER_MODEL = 'accounts.Person'

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.0/topics/i18n/
gettext = lambda x: x
LANGUAGE_CODE = 'es'
LANGUAGES = (
    #('fr', gettext('French')),
    ('en', gettext('English')),
    ('es', gettext('Spanish')),
)

TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

# Static files (CSS, JavaScript, Images)

#STATIC_URL = '/static/'
#STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

#STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static")
]

# noinspection PyUnresolvedReferences
STATIC_ROOT = os.path.join(BASE_DIR, "prodstatic")
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

"""
if os.getenv('GAE_APPLICATION'):
    DEFAULT_FILE_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    STATICFILES_STORAGE = 'storages.backends.gcloud.GoogleCloudStorage'
    #DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    GS_BUCKET_NAME = 'ietclms_storage_bucket'
    GS_DEFAULT_ACL = 'publicRead' 
    MEDIA_URL = 'https://storage.googleapis.com/ietclms_storage_bucket/'
else:
    PROJECT_PATH = os.path.join(os.path.abspath(os.path.split(__file__)[0]), '..')
    MEDIA_ROOT = os.path.join(PROJECT_PATH, 'site_media')
    MEDIA_URL = '/site_media/'   
"""

# Login URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

LOGGING_LEVEL = logging.INFO

TAGGIT_CASE_INSENSITIVE = True

# First try, in order to load local settings parameters
try:
    from lms.local_settings import *
except ImportError:
    pass

if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Second try, in order to override above things, if any
try:
    from lms.local_settings import *
except ImportError:
    pass



