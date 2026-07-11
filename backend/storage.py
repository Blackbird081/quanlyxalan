"""Attachment storage and scanner boundaries."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ObjectStorage(Protocol):
    backend_name: str
    def put_quarantined(self, object_key: str, content: bytes) -> str: ...


class LocalQuarantineStorage:
    backend_name = "LOCAL_QUARANTINE"

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put_quarantined(self, object_key: str, content: bytes) -> str:
        target = (self.root / object_key).resolve()
        if self.root not in target.parents:
            raise ValueError("Object key nằm ngoài quarantine root.")
        target.write_bytes(content)
        return object_key


class AttachmentScanner(Protocol):
    def scan(self, object_key: str) -> str: ...


class ScannerNotConfigured:
    """Fail-closed scanner used until Defender/ClamAV is configured."""

    def scan(self, object_key: str) -> str:
        return "QUARANTINED"
