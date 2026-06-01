from pathlib import Path
import os
import dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
dotenv.load_dotenv()

# Safely catch the filename from .env and expand it to a full absolute path
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if cred_path and not os.path.isabs(cred_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str((BASE_DIR / cred_path).resolve())

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Security
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-key-for-football-app")
DEBUG = True
ALLOWED_HOSTS = ["*"]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    # Project apps
    "chatbot",
    "dashboard",
    # "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"

# Database (Metadata only)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Static Files
STATIC_URL = "static/"

# BigQuery & Groq Config (For Li's Chatbot Logic)
LOOKER_STUDIO_URL = os.environ.get("LOOKER_STUDIO_URL", "https://lookerstudio.google.com/embed/reporting/00c26aba-1328-4c33-aa11-c3cff2b64c53/page/If9xF")