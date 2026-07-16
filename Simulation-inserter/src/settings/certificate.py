from pydantic import BaseModel


class CertificateSettings(BaseModel):
    ca_url: str = "https://dt4mob.av.it.pt/certificates/issue"
    subject: str = "sumo-inserter"
    ttl: int = 1
    cert_dir: str = "/tmp/mqtt-certs"

    cert_file: str | None = None
    key_file: str | None = None

    @property
    def cert_path(self) -> str | None:
        if self.cert_file is not None:
            return f"{self.cert_dir}/{self.cert_file}"
        return None
    
    @property
    def key_path(self) -> str | None:
        if self.key_file is not None:
            return f"{self.cert_dir}/{self.key_file}"
        return None
