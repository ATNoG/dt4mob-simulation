import httpx

from .certificate_service import CertificateService

from src.settings import settings


def _new_instance() -> CertificateService:
    http_client = httpx.AsyncClient(verify=False)
    return CertificateService(
        settings=settings.certificate, client=http_client
    )


certificate_service: CertificateService = _new_instance()
