"""External authority adapter boundary.

Default behavior is MANUAL and performs no network calls. A future official
adapter can implement the same contract after endpoint, credentials and data
sharing approval are supplied.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol


class IntegrationNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class AdapterSettings:
    mode: str = "MANUAL"
    base_url: str = ""
    credential_ref: str = ""
    enabled: bool = False

    @classmethod
    def from_environment(cls, prefix: str) -> "AdapterSettings":
        mode = os.getenv(f"{prefix}_MODE", "MANUAL").strip().upper()
        enabled = os.getenv(f"{prefix}_ENABLED", "false").strip().lower() == "true"
        return cls(
            mode=mode,
            base_url=os.getenv(f"{prefix}_BASE_URL", "").strip(),
            credential_ref=os.getenv(f"{prefix}_CREDENTIAL_REF", "").strip(),
            enabled=enabled,
        )

    @property
    def ready(self) -> bool:
        return self.enabled and self.mode != "MANUAL" and bool(self.base_url and self.credential_ref)


class ExternalAuthorityAdapter(Protocol):
    key: str

    def status(self) -> dict[str, Any]: ...
    def send(self, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]: ...


class ManualAdapter:
    """Preview/export adapter used while no official API exists."""

    def __init__(self, key: str, settings: AdapterSettings):
        self.key = key
        self.settings = settings

    def status(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "mode": "MANUAL",
            "enabled": False,
            "ready": False,
            "networkCallsAllowed": False,
            "reason": "Chưa cấu hình API chính thức; tiếp tục quy trình thủ công.",
        }

    def send(self, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        raise IntegrationNotConfigured(
            f"Adapter {self.key} đang ở MANUAL mode; payload chỉ được preview/export."
        )


def get_adapter(key: str, env_prefix: str) -> ExternalAuthorityAdapter:
    settings = AdapterSettings.from_environment(env_prefix)
    # Network-capable adapters are intentionally not selected until an official
    # contract implementation is added and separately approved.
    return ManualAdapter(key, settings)


def maritime_authority_adapter() -> ExternalAuthorityAdapter:
    return get_adapter("maritime-authority", "MARITIME_AUTHORITY")


def registry_adapter() -> ExternalAuthorityAdapter:
    return get_adapter("vessel-registry", "VESSEL_REGISTRY")
