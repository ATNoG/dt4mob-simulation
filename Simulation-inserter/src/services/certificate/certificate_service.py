import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from src.settings.certificate import CertificateSettings
from src.services.auth import auth_service


class CertificateError(Exception):
    """Exception for certificate issuance errors"""
    pass


class CertificateService:
    def __init__(self, settings: CertificateSettings, client: httpx.AsyncClient):
        self._settings = settings
        self._client = client
        self._last_issued: datetime | None = None
        self._cert_path: str | None = None
        self._key_path: str | None = None
        self._reissue: bool = True

    def needs_reissue(self) -> bool:
        if not self._reissue:
            return False
        if self._last_issued is None:
            return True
        buffer = timedelta(seconds=self._settings.ttl * 3600 * 0.8)
        return datetime.now(timezone.utc) > (self._last_issued + buffer)

    async def issue(self) -> tuple[str, str]:
        payload = {
            "subject": self._settings.subject,
            "ttl": self._settings.ttl,
        }
        token = await auth_service.get_token()
        logging.debug(f"Requesting certificate issuance for subject {self._settings.subject} with TTL {self._settings.ttl}h and token {token}")
        try:
            res = await self._client.post(
                self._settings.ca_url,
                json=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            )
            if not res.is_success:
                raise CertificateError(
                    f"Certificate issuance failed [{res.status_code}]: {res.text}"
                )
        except httpx.HTTPError as e:
            raise CertificateError(f"Certificate issuance request failed: {e}")

        body = res.json()
        cert_pem = body["cert"].encode("utf-8")
        key_pem = body["priv"].encode("utf-8")

        cert_dir = Path(self._settings.cert_dir)
        cert_dir.mkdir(parents=True, exist_ok=True)

        cert_path = str(cert_dir / "cert.pem")
        key_path = str(cert_dir / "key.pem")

        os.chmod(key_path, 0o600) if os.path.exists(key_path) else None

        with open(cert_path, "wb") as f:
            f.write(cert_pem)
        with open(key_path, "wb") as f:
            f.write(key_pem)

        os.chmod(key_path, 0o600)

        self._last_issued = datetime.now(timezone.utc)
        self._cert_path = cert_path
        self._key_path = key_path

        logging.info(f"Certificate issued for {self._settings.subject}, valid for {self._settings.ttl}h")
        return cert_path, key_path

    async def get_cert_paths(self) -> tuple[str, str]:
        if self._settings.cert_path and self._settings.key_path:
            self._reissue = False
            return self._settings.cert_path, self._settings.key_path
        else:
            return await self.issue()

    @property
    def cert_path(self) -> str | None:
        return self._cert_path

    @property
    def key_path(self) -> str | None:
        return self._key_path
