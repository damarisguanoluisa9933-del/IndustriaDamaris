import os
from pathlib import Path
import dj_database_url  # Importamos dj-database-url

# Ruta base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Clave secreta
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-v+p&0%!u_24j1qboi8#0dwp+s67+#774y8t8*5f+@(xt^4jhmd'
)

# Estado de depuración (False si está en servidor de producción, True por defecto en local)
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# Permitir todos los hosts en desarrollo/despliegue (o leídos de variables de entorno)
ALLOWED_HOSTS = ['*']
if 'RENDER_EXTERNAL_HOSTNAME' in os.environ:
    ALLOWED_HOSTS.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])

# Aplicaciones instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'Produccion',  # Aplicación principal del proyecto
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Sirve estáticos en producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'IndustriaDamaris.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'IndustriaDamaris.wsgi.application'

# BASE DE DATOS CONFIGURADA CON POSTGRESQL
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/bd_Industria'
        ),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Validación de contraseñas
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

# Idioma y zona horaria para Ecuador
LANGUAGE_CODE = 'es-ec'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

# Archivos estáticos (CSS, JS, Imágenes del tema)
STATIC_URL = '/static/'

STATIC_DIR_PATH = os.path.join(BASE_DIR, 'IndustriaDamaris/static')
if os.path.exists(STATIC_DIR_PATH):
    STATICFILES_DIRS = [STATIC_DIR_PATH]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuración de almacenamiento estático compatible para WhiteNoise en Django 4.2+ / 5.x
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Archivos multimedia subidos por los usuarios
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'IndustriaDamaris/media/')

# Configuración SMTP de Correo Institucional
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'damaris.guanoluisa9933@utc.edu.ec'
EMAIL_HOST_PASSWORD = 'zwdltkkmjwrgntvr'
DEFAULT_FROM_EMAIL = 'Industria Damaris <damaris.guanoluisa9933@utc.edu.ec>'