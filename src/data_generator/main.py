"""CLI del generador de datos sintéticos de LogiFlow.

Uso (desde la raíz del repositorio):

    python -m src.data_generator.main --date 2026-07-22 --output-dir data/local/landing

No toca AWS: escribe solo en el sistema de archivos local. La subida a S3
se hace en la fase de ingestión.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from .config import GeneratorConfig
from .error_injector import inject_errors
from .generator import generate_all
from .writers import write_entity, write_manifest


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generador sintético LogiFlow")
    parser.add_argument(
        "--date",
        required=True,
        help="Fecha de ingesta YYYY-MM-DD (día de negocio a generar)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/local/landing",
        help="Directorio raíz de salida (por defecto data/local/landing)",
    )
    parser.add_argument("--num-orders", type=int, default=80)
    parser.add_argument("--error-rate", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("data_generator")

    args = _parse_args(argv)
    try:
        ingest_date = date.fromisoformat(args.date)
    except ValueError:
        logger.error("fecha inválida: %s (formato esperado YYYY-MM-DD)", args.date)
        return 2

    try:
        cfg = GeneratorConfig(
            ingest_date=ingest_date,
            output_dir=Path(args.output_dir),
            num_orders=args.num_orders,
            error_rate=args.error_rate,
            seed=args.seed,
        )
    except ValueError as exc:
        logger.error("configuración inválida: %s", exc)
        return 2

    logger.info(
        "inicio generación date=%s orders=%d error_rate=%.3f seed=%d",
        cfg.ingest_date,
        cfg.num_orders,
        cfg.error_rate,
        cfg.seed,
    )

    clean = generate_all(cfg)
    dirty, manifest = inject_errors(clean, cfg.error_rate, cfg.seed)

    for entity, rows in dirty.items():
        write_entity(cfg.output_dir, entity, rows, cfg.ingest_date)

    write_manifest(
        cfg.output_dir,
        manifest,
        cfg.ingest_date,
        config_summary={
            "num_orders": cfg.num_orders,
            "error_rate": cfg.error_rate,
            "seed": cfg.seed,
        },
    )

    total_rows = sum(len(rows) for rows in dirty.values())
    logger.info(
        "generación completada: %d filas en %d entidades, %d errores inyectados",
        total_rows,
        len(dirty),
        len(manifest),
    )
    return 0


if __name__ == "__main__":
    sys.exit(run())
