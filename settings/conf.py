from decouple import config

SECRET_KEY: str = config("BLOG_SECRET_KEY", cast=str)
ENV_ID: str = config("BLOG_ENV_ID", cast=str)

# Print every SQL query to the console (local only)
SQL_LOG: bool = config("BLOG_SQL_LOG", default=False, cast=bool)