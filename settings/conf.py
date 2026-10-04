from decouple import config

SECRET_KEY = config("BLOG_SECRET_KEY")
ENV_ID = config("BLOG_ENV_ID")