from supabase import create_client, Client

from worker import config


def get_supabase_client():
    return create_client(config.SUPABASE_URL, config.SUPABASE_PRIVATE_KEY)
