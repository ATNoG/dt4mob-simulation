import httpx
from .ditto_class import DittoClient

from src.settings import settings
from src.services.auth import auth_service

def _new_instance() -> DittoClient:
    http_client = httpx.Client(verify=False)
    return DittoClient(
        client=http_client, auth_service=auth_service, ditto_settings=settings.ditto
    )


ditto_client: DittoClient = _new_instance()