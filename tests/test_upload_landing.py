"""Pruebas de la ingestión a S3 con un cliente falso (sin AWS ni boto3)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.ingestion.upload_landing import (
    ENTITIES,
    collect_local_files,
    s3_key_for,
    upload_partition,
)

INGEST = date(2026, 7, 22)


class FakeS3Client:
    """Simula head_object/upload_file sobre un dict en memoria."""

    def __init__(self) -> None:
        self.objects: dict[str, int] = {}
        self.upload_calls: list[str] = []

    def head_object(self, Bucket: str, Key: str) -> dict:  # noqa: N803
        if Key not in self.objects:
            raise KeyError(Key)
        return {"ContentLength": self.objects[Key]}

    def upload_file(self, Filename: str, Bucket: str, Key: str) -> None:  # noqa: N803
        self.objects[Key] = Path(Filename).stat().st_size
        self.upload_calls.append(Key)


def _make_landing(tmp_path: Path, ingest: date = INGEST) -> Path:
    """Crea una estructura landing local mínima y válida."""
    partition = f"ingest_date={ingest.isoformat()}"
    day = ingest.strftime("%Y%m%d")
    for entity in ENTITIES:
        ext = "jsonl" if entity == "delivery_events" else "csv"
        file = tmp_path / entity / partition / f"{entity}_{day}.{ext}"
        file.parent.mkdir(parents=True)
        file.write_text(f"contenido-{entity}\n", encoding="utf-8")
    manifest = tmp_path / "_manifests" / f"errors_manifest_{day}.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    return tmp_path


def test_collect_finds_six_files(tmp_path: Path) -> None:
    local = _make_landing(tmp_path)
    files = collect_local_files(local, INGEST)
    assert len(files) == len(ENTITIES) + 1  # 5 entidades + manifiesto


def test_collect_fails_if_partition_missing(tmp_path: Path) -> None:
    local = _make_landing(tmp_path)
    with pytest.raises(FileNotFoundError):
        collect_local_files(local, date(2026, 7, 24))


def test_s3_keys_preserve_layout(tmp_path: Path) -> None:
    local = _make_landing(tmp_path)
    files = collect_local_files(local, INGEST)
    keys = {s3_key_for(local, f) for f in files}
    assert "orders/ingest_date=2026-07-22/orders_20260722.csv" in keys
    assert "_manifests/errors_manifest_20260722.json" in keys
    assert all("\\" not in k for k in keys)  # separador POSIX incluso en Windows


def test_upload_all_new_files(tmp_path: Path) -> None:
    local = _make_landing(tmp_path)
    client = FakeS3Client()
    result = upload_partition(client, "bucket-x", local, INGEST)
    assert len(result.uploaded) == 6
    assert result.skipped == []


def test_reupload_is_idempotent(tmp_path: Path) -> None:
    local = _make_landing(tmp_path)
    client = FakeS3Client()
    upload_partition(client, "bucket-x", local, INGEST)
    result = upload_partition(client, "bucket-x", local, INGEST)
    assert result.uploaded == []
    assert len(result.skipped) == 6
    assert len(client.upload_calls) == 6  # no hubo segundas subidas


def test_changed_file_is_reuploaded(tmp_path: Path) -> None:
    local = _make_landing(tmp_path)
    client = FakeS3Client()
    upload_partition(client, "bucket-x", local, INGEST)

    target = local / "orders" / f"ingest_date={INGEST.isoformat()}" / "orders_20260722.csv"
    target.write_text("contenido-mas-largo-que-el-anterior\n", encoding="utf-8")

    result = upload_partition(client, "bucket-x", local, INGEST)
    assert result.uploaded == ["orders/ingest_date=2026-07-22/orders_20260722.csv"]
    assert len(result.skipped) == 5
