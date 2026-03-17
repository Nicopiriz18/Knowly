"""Centralized Pinecone client — instantiated once and reused."""

from pinecone import Pinecone

from config import settings

_index = None


def get_index():
    global _index
    if _index is None:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _index = pc.Index(settings.pinecone_index_name)
    return _index
