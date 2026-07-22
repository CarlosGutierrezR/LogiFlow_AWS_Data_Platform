"""Pruebas del ETL PySpark: unitarias de validación + end-to-end.

La prueba clave es TestEndToEnd: genera un día con el generador (Fase 4),
ejecuta landing→raw→processed y verifica que TODOS los errores del
manifiesto de inyección acaban detectados (en cuarentena o deduplicados).

Requiere pyspark 3.5.x (mismo runtime que Glue 5.0) y Java 11+.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

pyspark = pytest.importorskip("pyspark", reason="pyspark no instalado")

from pyspark.sql import SparkSession  # noqa: E402

from src.data_generator.config import GeneratorConfig  # noqa: E402
from src.data_generator.error_injector import inject_errors  # noqa: E402
from src.data_generator.generator import generate_all  # noqa: E402
from src.data_generator.writers import write_entity, write_manifest  # noqa: E402
from src.etl import landing_to_raw, raw_to_processed  # noqa: E402
from src.etl.schemas import PROCESSING_ORDER, SPECS_BY_NAME  # noqa: E402

INGEST = "2026-07-22"


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder.master("local[2]")
        .appName("logiflow-tests")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture(scope="session")
def pipeline_run(spark, tmp_path_factory):
    """Genera datos con errores, ejecuta ambos jobs y devuelve rutas + manifiesto."""
    base = tmp_path_factory.mktemp("lake")
    landing = base / "landing"
    cfg = GeneratorConfig(
        ingest_date=date.fromisoformat(INGEST),
        output_dir=landing,
        num_orders=60,
        error_rate=0.05,
        seed=777,
    )
    clean = generate_all(cfg)
    dirty, manifest = inject_errors(clean, cfg.error_rate, cfg.seed)
    for entity, rows in dirty.items():
        write_entity(landing, entity, rows, cfg.ingest_date)
    write_manifest(landing, manifest, cfg.ingest_date, {})

    paths = {
        "landing": str(landing),
        "raw": str(base / "raw"),
        "processed": str(base / "processed"),
        "quarantine": str(base / "quarantine"),
    }

    assert (
        landing_to_raw.run(
            [
                "--date", INGEST,
                "--landing-path", paths["landing"],
                "--raw-path", paths["raw"],
                "--batch-id", "batch-test",
            ],
            spark=spark,
        )
        == 0
    )
    assert (
        raw_to_processed.run(
            [
                "--date", INGEST,
                "--raw-path", paths["raw"],
                "--processed-path", paths["processed"],
                "--quarantine-path", paths["quarantine"],
            ],
            spark=spark,
        )
        == 0
    )
    return paths, manifest, dirty


def _read(spark, root: str, entity: str):
    path = Path(root) / entity / f"ingest_date={INGEST}"
    if not path.exists():
        return None
    return spark.read.parquet(str(path))


class TestRaw:
    def test_raw_preserves_counts_and_adds_lineage(self, spark, pipeline_run):
        paths, _, dirty = pipeline_run
        for spec in PROCESSING_ORDER:
            raw_df = _read(spark, paths["raw"], spec.name)
            assert raw_df is not None
            assert raw_df.count() == len(dirty[spec.name])
            for col in ("_ingest_date", "_source_file", "_load_ts", "_batch_id"):
                assert col in raw_df.columns
            assert raw_df.filter(raw_df._batch_id == "batch-test").count() > 0


class TestProcessed:
    def test_typed_schema(self, spark, pipeline_run):
        paths, _, _ = pipeline_run
        orders = _read(spark, paths["processed"], "orders")
        types = dict(orders.dtypes)
        assert types["num_packages"] == "int"
        assert types["total_weight_kg"] == "double"
        assert types["order_ts"] == "timestamp"

    def test_no_invalid_values_in_processed(self, spark, pipeline_run):
        paths, _, _ = pipeline_run
        orders = _read(spark, paths["processed"], "orders")
        assert orders.filter("total_weight_kg <= 0").count() == 0
        assert (
            orders.filter(
                "service_level not in ('standard','express','same_day')"
            ).count()
            == 0
        )
        shipments = _read(spark, paths["processed"], "shipments")
        assert (
            shipments.filter(
                "actual_delivery_ts is not null and actual_departure_ts is not null "
                "and actual_delivery_ts <= actual_departure_ts"
            ).count()
            == 0
        )

    def test_pk_unique_in_processed(self, spark, pipeline_run):
        paths, _, _ = pipeline_run
        for spec in PROCESSING_ORDER:
            df = _read(spark, paths["processed"], spec.name)
            assert df.count() == df.select(spec.pk).distinct().count()


class TestReconciliationAndDetection:
    def test_counts_reconcile(self, spark, pipeline_run):
        paths, _, dirty = pipeline_run
        for spec in PROCESSING_ORDER:
            raw_n = _read(spark, paths["raw"], spec.name).count()
            processed_n = _read(spark, paths["processed"], spec.name).count()
            q_df = _read(spark, paths["quarantine"], spec.name)
            quarantined_n = q_df.count() if q_df is not None else 0
            dedup_n = raw_n - _read(spark, paths["raw"], spec.name).select(
                spec.pk
            ).distinct().count()
            assert raw_n == processed_n + quarantined_n + dedup_n, spec.name

    def test_all_injected_errors_detected(self, spark, pipeline_run):
        """Cada error del manifiesto debe estar neutralizado:
        E02 → deduplicado; el resto → su PK en cuarentena de su entidad."""
        paths, manifest, _ = pipeline_run
        assert manifest, "el manifiesto no puede estar vacío en esta prueba"

        quarantined: dict[str, set[str]] = {}
        for spec in PROCESSING_ORDER:
            df = _read(spark, paths["quarantine"], spec.name)
            quarantined[spec.name] = (
                {r[0] for r in df.select(spec.pk).collect()} if df is not None else set()
            )

        missed = []
        for err in manifest:
            entity, code, pk = err["entity"], err["error_code"], err["pk_value"]
            if code == "E02":
                df = _read(spark, paths["processed"], entity)
                pk_field = SPECS_BY_NAME[entity].pk
                n = df.filter(f"{pk_field} = '{pk}'").count()
                if n > 1:
                    missed.append(err)
            elif pk not in quarantined[entity]:
                missed.append(err)

        assert not missed, f"errores inyectados NO detectados: {missed}"
