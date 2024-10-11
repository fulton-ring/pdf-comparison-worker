from supabase import create_client, Client

from worker import config

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_PRIVATE_KEY)
