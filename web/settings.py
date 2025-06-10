import os

# Print out safe environment variables at load time
print(f"WEBSITE_HOSTNAME: {os.getenv('WEBSITE_HOSTNAME')}")
print(f"BOT_URL: {os.getenv('BOT_URL')}")
print(f"DB_HOST: {os.getenv('DB_HOST')}")

# Env values tell us where we are running
WEBSITE_HOSTNAME = os.getenv("WEBSITE_HOSTNAME")

# Azure (also local functions)
if WEBSITE_HOSTNAME:
    DEBUG = True
    ALLOWED_HOSTS = [WEBSITE_HOSTNAME, "localhost"]
    CSRF_TRUSTED_ORIGINS = ["https://" + WEBSITE_HOSTNAME]
# Local or Codespace
else:
    DEBUG = True
    ALLOWED_HOSTS = []
    # Codespace
    if os.getenv("CODESPACES"):
        CSRF_TRUSTED_ORIGINS = [f'https://{os.getenv("CODESPACE_NAME")}-8000.{os.getenv("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")}']

BOT_URL = os.getenv("BOT_URL")
BOT_MASTER_KEY = os.getenv("MASTER_KEY")
BOT_NAME = "bot"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": "5432",
    }
}

# Other important
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
BOOTSTRAP5 = {"theme_url": "https://bootswatch.com/5/solar/bootstrap.min.css"}

# Mem0
MEM0CONF = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4.1-nano",
            "temperature": 0.2,
            "max_tokens": 2000,
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small"
        }
    },
}

# Locations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WSGI_APPLICATION = "web.wsgi.application"
ROOT_URLCONF = "web.urls"
STATIC_URL = "web/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Misc
LANGUAGE_CODE = "en-us"
TIME_ZONE = "EET"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Installations
INSTALLED_APPS = [
    "chat.apps.ChatConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_bootstrap5",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]