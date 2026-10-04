from settings.base import *

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "blog",
        "USER": "postgress",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "5432",
    }
}