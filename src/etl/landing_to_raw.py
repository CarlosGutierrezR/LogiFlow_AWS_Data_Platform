"""Job 1: landing → raw.

Conserva el dato original (todas las columnas como string, sin transformar)
y añade columnas de linaje. Idempotente: reescribe la partición completa de
la fecha procesada.

Ejecución local (pruebas):
    python -m src.etl.landing_to_raw --date 2026-07-22 \
        --landing-path data/local/landing --raw-path data/local/raw

En Glue: mismo script; los argumentos del job usan los mismos nombres.
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructField, StructType

from .schemas import PROCESSING_ORDER, EntitySpec

logger = logging.getLogger("etl.landing_to_raw")

_JSONL_ENTITIES = {"delivery_events"}


def _string_schema(spec: EntitySpec) -> StructType:
    """Esquema todo-string: raw no interpreta tipos, solo conserva."""
    return StructType(
        [StructField(name, StringType(), True) for name in spec.fields]
    )


def read_landing_entity(
    spark: SparkSession, landing_path: str, spec: EntitySpec, ingest_date: str
) -> DataFrame:
    path = f"{landing_path}/{spec.name}/ingest_date={ingest_date}/"
    schema = _string_schema(spec)
    if spec.name in _JSONL_ENTITIES:
        return spark.read.schema(schema).json(path)
    return spark.read.schema(schema).option("header", True).csv(path)


def add_lineage(
    df: DataFrame, ingest_date: str, batch_id: str, load_ts: str
) -> DataFrame:
    return (
        df.withColumn("_ingest_date", F.lit(ingest_date))
        .withColumn("_source_file", F.input_file_name())
        .withColumn("_load_ts", F.lit(load_ts))
        .withColumn("_batch_id", F.lit(batch_id))
    )


def run_entity(
    spark: SparkSession,
    landing_path: str,
    raw_path: str,
    spec: EntitySpec,
    ingest_date: str,
    batch_id: str,
    load_ts: str,
) -> int:
    df = read_landing_entity(spark, landing_path, spec, ingest_date)
    enriched = add_lineage(df, ingest_date, batch_id, load_ts)
    out_path = f"{raw_path}/{spec.name}/ingest_date={ingest_date}/"
    enriched.write.mode("overwrite").parquet(out_path)
    count = spark.read.parquet(out_path).count()
    logger.info(
        "entidad=%s filas_raw=%d destino=%s", spec.name, count, out_path
    )
    return count


def run(argv: list[str] | None = None, spark: SparkSession | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    parser = argparse.ArgumentParser(description="LogiFlow ETL: landing -> raw")
    parser.add_argument("--date", required=True, help="Fecha de ingesta YYYY-MM-DD")
    parser.add_argument("--landing-path", required=True)
    parser.add_argument("--raw-path", required=True)
    parser.add_argument("--batch-id", default=None)
    args, _ = parser.parse_known_args(argv)  # Glue añade args propios: ignorarlos

    batch_id = args.batch_id or f"batch-{uuid.uuid4().hex[:12]}"
    load_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    own_spark = spark is None
    if own_spark:
        spark = (
            SparkSession.builder.appName("logiflow-landing-to-raw")
            .getOrCreate()
        )

    try:
        totals = {
            spec.name: run_entity(
                spark,
                args.landing_path,
                args.raw_path,
                spec,
                args.date,
                batch_id,
                load_ts,
            )
            for spec in PROCESSING_ORDER
        }
    finally:
        if own_spark:
            spark.stop()

    logger.info("landing->raw completado batch=%s totales=%s", batch_id, totals)
    return 0


if __name__ == "__main__":
    sys.exit(run())
