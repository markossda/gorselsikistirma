"""Supabase Storage bağlantı modülü."""

import os
from supabase import create_client, Client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def upload_to_bucket(
    client: Client,
    bucket: str,
    path: str,
    file_bytes: bytes,
    content_type: str,
) -> dict:
    """Dosyayı Supabase Storage bucket'a yükler."""
    res = client.storage.from_(bucket).upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return {"path": path, "status": "ok"}


def list_bucket_files(client: Client, bucket: str, folder: str = "") -> list:
    """Bucket'taki dosyaları listeler."""
    return client.storage.from_(bucket).list(folder)
