"""Escritura de archivos landing según la nomenclatura del contrato:

{output_dir}/{entidad}/ingest_date=YYYY-MM-DD/{entidad}_YYYYMMDD.csv|jsonl
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

_JSONL_ENTITIES = {"delivery_events"}


def landing_path(output_dir: Path, entity: str, ingest_date: date) -> Path:
    extension = "jsonl" if entity in _JSONL_ENTITIES else "csv"
    day_compact = ingest_date.strftime("%Y%m%d")
    return (
        output_dir
        / entity
        / f"ingest_date={ingest_date.isoformat()}"
        / f"{entity}_{day_compact}.{extension}"
    )


def write_entity(output_dir: Path, entity: str, rows: list[dict], ingest_date: date) -> Path:
    if not rows:
        raise ValueError(f"Entidad sin filas: {entity}")
    path = landing_path(output_dir, entity, ingest_date)
    path.parent.mkdir(parents=True, exist_ok=True)

    if entity in _JSONL_ENTITIES:
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    else:
        fieldnames = list(rows[0].keys())
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    logger.info("escrito entity=%s filas=%d ruta=%s", entity, len(rows), path)
    return path


def write_manifest(
    output_dir: Path, manifest: list[dict], ingest_date: date, config_summary: dict
) -> Path:
    day_compact = ingest_date.strftime("%Y%m%d")
    path = output_dir / "_manifests" / f"errors_manifest_{day_compact}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ingest_date": ingest_date.isoformat(),
        "config": config_summary,
        "injected_error_count": len(manifest),
        "errors": manifest,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("manifiesto de errores escrito: %s (%d errores)", path, len(manifest))
    return path
