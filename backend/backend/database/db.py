"""Supabase client for backend operations (service role — bypasses RLS)."""

from supabase import create_client, Client
from backend.config.settings import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_service_key)