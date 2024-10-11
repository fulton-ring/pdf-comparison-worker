import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")

SUPABASE_URL: str = os.environ["SUPABASE_URL"]
SUPABASE_PRIVATE_KEY: str = os.environ["SUPABASE_PRIVATE_KEY"]
SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "uploads")
