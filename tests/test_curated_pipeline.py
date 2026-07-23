"""Pruebas del modelo dimensional curated (Fase 8). Requiere pyspark."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

pyspark = pytest.importorskip("pyspark", reason="pyspark no instalado")

from pyspark.sql import SparkSession  # noqa: E402

from src.data_generator.config import GeneratorConfig  # noqa: E402
from src.data_generator.error_injector import inject_errors  # noqa: E402
from src.data_generator.generator import generate_all  # noqa: E402
from src.data_generator.writers import write_entity  # noqa: E402
from src.etl import landing_to_raw, processed_to_curated, raw_to_processed  # noqa: E402

INGEST = "2026-07-22"


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("logiflow-curated-tests")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="session")
def curated_run(spark, tmp_path_factory):
    base = tmp_path_factory.mktemp("lake8")
    landing = base / "landing"
    cfg = GeneratorConfig(
        ingest_date=date.fromisoformat(INGEST),
        output_dir=landing,
        num_orders=50,
        error_rate=0.03,
        seed=2024,
    )
    dirty, _ = inject_errors(generate_all(cfg), cfg.error_rate, cfg.seed)
    for entity, rows in dirty.items():
        write_entity(landing, entity, rows, cfg.ingest_date)

    paths = {k: str(base / k) for k in ("landing", "raw", "processed", "curated")}
    quarantine = str(base / "quarantine")

    landing_to_raw.run(
        ["--date", INGEST, "--landing-path", paths["landing"], "--raw-path", paths["raw"]],
        spark=spark,
    )
    raw_to_processed.run(
        [
            "--date",
            INGEST,
            "--raw-path",
            paths["raw"],
            "--processed-path",
            paths["processed"],
            "--quarantine-path",
            quarantine,
        ],
        spark=spark,
    )
    assert (
        processed_to_curated.run(
            [
                "--date",
                INGEST,
                "--processed-path",
                paths["processed"],
                "--curated-path",
                paths["curated"],
            ],
            spark=spark,
        )
        == 0
    )
    return paths


def _read(spark, root: str, table: str):
    return spark.read.parquet(str(Path(root) / table / f"ingest_date={INGEST}"))


def test_fact_reconciles_with_processed(spark, curated_run):
    fact = _read(spark, curated_run["curated"], "fact_shipments")
    shipments = _read(spark, curated_run["processed"], "shipments")
    assert fact.count() == shipments.count()


def test_dims_unique_keys(spark, curated_run):
    dim_w = _read(spark, curated_run["curated"], "dim_warehouse")
    dim_r = _read(spark, curated_run["curated"], "dim_route")
    assert dim_w.count() == dim_w.select("warehouse_id").distinct().count()
    assert dim_r.count() == dim_r.select("route_id").distinct().count()
    # enriquecimiento: toda ruta con almacén válido tiene ciudad de origen
    assert dim_r.filter("origin_city is null").count() == 0


def test_fact_metrics_coherent(spark, curated_run):
    fact = _read(spark, curated_run["curated"], "fact_shipments")
    # on_time solo puede evaluarse con entrega real
    assert fact.filter("on_time is not null and actual_delivery_ts is null").count() == 0
    # el retraso existe exactamente cuando hay entrega real
    assert (
        fact.filter("delivery_delay_hours is not null and actual_delivery_ts is null").count() == 0
    )
    # coherencia on_time vs delay
    assert fact.filter("on_time = true and delivery_delay_hours > 0").count() == 0
    assert fact.filter("on_time = false and delivery_delay_hours <= 0").count() == 0
    # incidentes = estados de incidencia
    assert (
        fact.filter("is_incident = true and status not in ('delayed','lost','returned')").count()
        == 0
    )


def test_fact_no_null_keys(spark, curated_run):
    fact = _read(spark, curated_run["curated"], "fact_shipments")
    assert fact.filter("shipment_id is null or order_id is null").count() == 0
