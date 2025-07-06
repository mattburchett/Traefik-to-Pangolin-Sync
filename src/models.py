from enum import Enum
from dataclasses import dataclass
from typing import Optional


class HTTPForwardMethod(Enum):
    HTTP = "HTTP"
    HTTPS = "HTTPS"


@dataclass
class TCPForward:
    site_name: str
    source_port: int
    target_host: str
    target_port: int
    name: Optional[str] = None

    def __str__(self) -> str:
        name_part = f"[{self.name}] " if self.name else ""
        return f"{name_part}{self.source_port}→ {self.target_host}:{self.target_port} TCP ({self.site_name})"


@dataclass
class UDPForward:
    site_name: str
    source_port: int
    target_host: str
    target_port: int
    name: Optional[str] = None

    def __str__(self) -> str:
        name_part = f"[{self.name}] " if self.name else ""
        return f"{name_part}{self.source_port}→ {self.target_host}:{self.target_port} UDP ({self.site_name})"


@dataclass
class TraefikSite:
    site_name: str
    api_url: str
    api_http_routers_path: str
    target_host: str
    target_port: int
    target_method: HTTPForwardMethod
    host_whitelist: list[str]

    def __str__(self) -> str:
        return f"TraefikSite({self.site_name}: {self.api_url})"


@dataclass
class HTTPForward:
    subdomain: str
    domain: str
    site_name: str
    target_host: str
    target_port: int
    target_method: HTTPForwardMethod

    @property
    def fqdn(self) -> str:
        if self.subdomain:
            return f"{self.subdomain}.{self.domain}"
        return self.domain

    def __str__(self) -> str:
        return f"{self.fqdn}→ {self.target_method.value.lower()}://{self.target_host}:{self.target_port} ({self.site_name})"
