"""Subida idempotente de una fecha de ingesta desde landing local a S3.

Uso (desde la raíz del repositorio, con sesión `aws login` activa):

    python -m src.ingestion.upload_landing --date 2026-07-22 \
        --bucket logiflow-dev-landing-<ACCOUNT_ID>

Idempotencia: si el objeto ya existe en S3 con el mismo tamaño, se omite.
Reejecutar la misma fecha no duplica datos (requisito de docs/architecture.md).
El cliente S3 se inyecta para poder probar sin AWS (tests con cliente falso).
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

logger = logging.getLogger("ingestion.upload_landing")

ENTITIES: tuple[str, ...] = (
    "warehouses",
    "routes",
    "orders",
    "shipments",
    "delivery_events",
)


@dataclass
class UploadResult:
    uploaded: list[str]
    skipped: list[str]

    @property
    def total(self) -> int:
        return len(self.uploaded) + len(self.skipped)


def collect_local_files(local_dir: Path, ingest_date: date) -> list[Path]:
    """Localiza los archivos de una fecha: 5 entidades + manifiesto de errores."""
    partition = f"ingest_date={ingest_date.isoformat()}"
    day_compact = ingest_date.strftime("%Y%m%d")
    files: list[Path] = []

    for entity in ENTITIES:
        entity_dir = local_dir / entity / partition
        if not entity_dir.is_dir():
            raise FileNotFoundError(
                f"No existe {entity_dir}. ¿Ejecutaste el generador para esa fecha?"
            )
        found = sorted(p for p in entity_dir.iterdir() if p.is_file())
        if not found:
            raise FileNotFoundError(f"Partición vacía: {entity_dir}")
        files.extend(found)

    manifest = local_dir / "_manifests" / f"errors_manifest_{day_compact}.json"
    if manifest.is_file():
        files.append(manifest)
    else:
        logger.warning("manifiesto no encontrado (se continúa sin él): %s", manifest)
    return files


def s3_key_for(local_dir: Path, file_path: Path) -> str:
    """Clave S3 = ruta relativa a local_dir, con separador '/'."""
    return file_path.relative_to(local_dir).as_posix()


def _object_exists_same_size(s3_client, bucket: str, key: str, size: int) -> bool:
    try:
        head = s3_client.head_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 - boto3 lanza ClientError; el falso, KeyError
        error_code = ""
        response = getattr(exc, "response", None)
        if isinstance(response, dict):
            error_code = response.get("Error", {}).get("Code", "")
        if error_code in ("404", "NoSuchKey", "NotFound") or isinstance(exc, KeyError):
            return False
        raise
    return int(head.get("ContentLength", -1)) == size


def upload_partition(s3_client, bucket: str, local_dir: Path, ingest_date: date) -> UploadResult:
    files = collect_local_files(local_dir, ingest_date)
    result = UploadResult(uploaded=[], skipped=[])

    for file_path in files:
        key = s3_key_for(local_dir, file_path)
        size = file_path.stat().st_size
        if _object_exists_same_size(s3_client, bucket, key, size):
            logger.info("omitido (ya existe, mismo tamaño) key=%s", key)
            result.skipped.append(key)
            continue
        s3_client.upload_file(str(file_path), bucket, key)
        logger.info("subido key=%s bytes=%d", key, size)
        result.uploaded.append(key)

    logger.info(
        "resumen fecha=%s subidos=%d omitidos=%d total=%d",
        ingest_date,
        len(result.uploaded),
        len(result.skipped),
        result.total,
    )
    return result


def run(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="Subida de landing local a S3")
    parser.add_argument("--date", required=True, help="Fecha YYYY-MM-DD a subir")
    parser.add_argument("--bucket", required=True, help="Bucket S3 de landing")
    parser.add_argument("--local-dir", default="data/local/landing")
    args = parser.parse_args(argv)

    try:
        ingest_date = date.fromisoformat(args.date)
    except ValueError:
        logger.error("fecha inválida: %s", args.date)
        return 2

    try:
        import boto3  # import tardío: los tests no necesitan boto3
    except ImportError:
        logger.error("boto3 no instalado. Ejecuta: pip install boto3")
        return 2

    try:
        result = upload_partition(
            boto3.client("s3"), args.bucket, Path(args.local_dir), ingest_date
        )
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return 2

    return 0 if result.total > 0 else 1


if __name__ == "__main__":
    sys.exit(run())
