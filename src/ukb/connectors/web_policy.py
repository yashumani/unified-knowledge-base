from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


class WebConnectorError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedUrl:
    url: str
    parsed: SplitResult
    host: str
    port: int


class WebUrlPolicy:
    """Validate URL shape, hostname allowlists, ports, and literal addresses."""

    def __init__(
        self,
        *,
        allowed_hosts: list[str],
        allowed_ports: list[int],
        allow_private_networks: bool,
    ):
        self.allowed_hosts = [self._normalize_host(value) for value in allowed_hosts]
        self.allowed_ports = set(allowed_ports)
        self.allow_private_networks = allow_private_networks

    def validate(self, url: str) -> ValidatedUrl:
        if not self.allowed_hosts:
            raise WebConnectorError("No source hosts are configured.")
        parsed = urlsplit(url.strip())
        if parsed.scheme.casefold() not in {"http", "https"}:
            raise WebConnectorError("Only HTTP and HTTPS are accepted.")
        if parsed.username or parsed.password:
            raise WebConnectorError("User information is not accepted in source URLs.")
        if not parsed.hostname:
            raise WebConnectorError("A source hostname is required.")

        host = self._normalize_host(parsed.hostname)
        if not self._host_allowed(host):
            raise WebConnectorError(f"Source host is not configured: {host}")
        try:
            port = parsed.port or (443 if parsed.scheme.casefold() == "https" else 80)
        except ValueError as exc:
            raise WebConnectorError("The source port is invalid.") from exc
        if port not in self.allowed_ports:
            raise WebConnectorError(f"Source port is not configured: {port}")

        self._validate_literal_address(host)
        normalized_url = urlunsplit(
            (parsed.scheme.casefold(), parsed.netloc, parsed.path or "/", parsed.query, "")
        )
        return ValidatedUrl(
            url=normalized_url,
            parsed=urlsplit(normalized_url),
            host=host,
            port=port,
        )

    def _host_allowed(self, host: str) -> bool:
        for pattern in self.allowed_hosts:
            if pattern == host:
                return True
            if pattern.startswith("*.") and host.endswith(pattern[1:]):
                return True
        return False

    def _normalize_host(self, value: str) -> str:
        host = value.strip().casefold().rstrip(".")
        if host == "*":
            raise WebConnectorError("A global host pattern is not supported.")
        return host.encode("idna").decode("ascii")

    def _validate_literal_address(self, host: str) -> None:
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return
        if not self.allow_private_networks and not address.is_global:
            raise WebConnectorError("Private or special-use source addresses are disabled.")
