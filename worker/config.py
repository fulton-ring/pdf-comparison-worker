import os

import dotenv

dotenv.load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")

SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_PRIVATE_KEY: str = os.getenv("SUPABASE_PRIVATE_KEY")
SUPABASE_UPLOADS_BUCKET: str = os.getenv("SUPABASE_UPLOADS_BUCKET", "uploads")
SUPABASE_JOBS_BUCKET: str = os.getenv("SUPABASE_JOBS_BUCKET", "jobs")
