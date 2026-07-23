"""Job 2: raw → processed (+ quarantine).

Por entidad y fecha:
1. Deduplicación por clave primaria (conserva una fila por PK).
2. Validaciones del contrato: obligatorios, enumeraciones, rangos,
   timestamps parseables, coherencia temporal e integridad referencial
   contra las filas VÁLIDAS de las entidades referenciadas (por eso el
   orden de procesamiento va de dimensiones a hechos).
3. Filas válidas → processed en Parquet tipado.
4. Filas inválidas → quarantine con la lista de motivos (_error_reasons).
5. Reconciliación: raw == procesadas + cuarentena + duplicados eliminados.

Ejecución local (pruebas):
    python -m src.etl.raw_to_processed --date 2026-07-22 \
        --raw-path data/local/raw --processed-path data/local/processed \
        --quarantine-path data/local/quarantine
"""

from __future__ import annotations

import argparse
import logging
import sys

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from .schemas import LINEAGE_COLUMNS, PROCESSING_ORDER, TS_FORMAT, EntitySpec

logger = logging.getLogger("etl.raw_to_processed")

_ERR = "_error_reasons"


def _typed_column(field_name: str, field_type: str) -> F.Column:
    """Convierte la columna string de raw al tipo destino del contrato."""
    col = F.col(field_name)
    empty_as_null = F.when(col == "", None).otherwise(col)
    if field_type == "string":
        return empty_as_null
    if field_type in ("int", "double"):
        return empty_as_null.cast(field_type)
    if field_type == "boolean":
        return F.when(F.lower(col).isin("true", "1"), F.lit(True)).when(
            F.lower(col).isin("false", "0"), F.lit(False)
        )
    if field_type == "timestamp":
        return F.to_timestamp(empty_as_null, TS_FORMAT)
    if field_type == "date":
        return F.to_date(empty_as_null, "yyyy-MM-dd")
    raise ValueError(f"Tipo no soportado: {field_type}")


def deduplicate(df: DataFrame, spec: EntitySpec) -> tuple[DataFrame, int]:
    before = df.count()
    deduped = df.dropDuplicates([spec.pk])
    return deduped, before - deduped.count()


def add_error_flags(df: DataFrame, spec: EntitySpec) -> DataFrame:
    """Añade la columna _error_reasons (array de motivos, vacío si válida).

    Las comprobaciones se hacen sobre columnas tipadas temporales (_t_<campo>)
    para detectar valores no parseables sin perder el original string.
    """
    typed = df
    for name, ftype in spec.fields.items():
        typed = typed.withColumn(f"_t_{name}", _typed_column(name, ftype))

    reasons: list[F.Column] = []

    for name in spec.required:
        raw_col, typed_col = F.col(name), F.col(f"_t_{name}")
        missing = raw_col.isNull() | (raw_col == "")
        unparseable = ~missing & typed_col.isNull()
        reasons.append(F.when(missing, F.lit(f"E01:{name}:obligatorio_vacio")))
        reasons.append(F.when(unparseable, F.lit(f"E07:{name}:no_parseable")))

    for name, allowed in spec.enums.items():
        bad = F.col(name).isNotNull() & (F.col(name) != "") & ~F.col(name).isin(*allowed)
        reasons.append(F.when(bad, F.lit(f"E06:{name}:fuera_de_enum")))

    for name, (low, high) in spec.positive_ranges.items():
        t = F.col(f"_t_{name}")
        out_low = t.isNotNull() & (t <= F.lit(low))
        reasons.append(F.when(out_low, F.lit(f"E04:{name}:fuera_de_rango")))
        if high is not None:
            out_high = t.isNotNull() & (t > F.lit(high))
            reasons.append(F.when(out_high, F.lit(f"E04:{name}:fuera_de_rango")))

    for before_f, after_f in spec.temporal_order:
        b, a = F.col(f"_t_{before_f}"), F.col(f"_t_{after_f}")
        bad = b.isNotNull() & a.isNotNull() & (a <= b)
        reasons.append(F.when(bad, F.lit(f"E05:{after_f}:incoherencia_temporal")))

    return typed.withColumn(_ERR, F.array_compact(F.array(*reasons)))


def add_fk_errors(df: DataFrame, spec: EntitySpec, valid_refs: dict[str, DataFrame]) -> DataFrame:
    """Marca E03 si la FK no existe entre las filas válidas de la referencia."""
    result = df
    for fk_field, (ref_entity, ref_field) in spec.foreign_keys.items():
        marker = f"_fk_ok_{fk_field}"
        ref = (
            valid_refs[ref_entity]
            .select(F.col(ref_field).alias(fk_field))
            .distinct()
            .withColumn(marker, F.lit(True))
        )
        result = result.join(ref, on=fk_field, how="left")
        broken = F.col(fk_field).isNotNull() & F.col(marker).isNull()
        result = result.withColumn(
            _ERR,
            F.when(
                broken,
                F.array_union(F.col(_ERR), F.array(F.lit(f"E03:{fk_field}:fk_rota"))),
            ).otherwise(F.col(_ERR)),
        ).drop(marker)
    return result


def split_valid_invalid(df: DataFrame) -> tuple[DataFrame, DataFrame]:
    return (
        df.filter(F.size(_ERR) == 0),
        df.filter(F.size(_ERR) > 0),
    )


def select_processed(df: DataFrame, spec: EntitySpec) -> DataFrame:
    """Proyección final tipada + linaje (descarta strings originales)."""
    cols = [F.col(f"_t_{name}").alias(name) for name in spec.fields]
    cols += [F.col(c) for c in LINEAGE_COLUMNS]
    return df.select(*cols)


def select_quarantine(df: DataFrame, spec: EntitySpec) -> DataFrame:
    """Conserva los valores ORIGINALES string + motivos, para reproceso."""
    cols = [F.col(name) for name in spec.fields]
    cols += [F.col(c) for c in LINEAGE_COLUMNS]
    cols.append(F.array_join(F.col(_ERR), ";").alias("error_reasons"))
    return df.select(*cols)


def run_entity(
    spark: SparkSession,
    paths: dict[str, str],
    spec: EntitySpec,
    ingest_date: str,
    valid_refs: dict[str, DataFrame],
) -> dict[str, int]:
    raw_df = spark.read.parquet(f"{paths['raw']}/{spec.name}/ingest_date={ingest_date}/")
    raw_count = raw_df.count()

    deduped, dup_removed = deduplicate(raw_df, spec)
    flagged = add_error_flags(deduped, spec)
    flagged = add_fk_errors(flagged, spec, valid_refs)
    valid, invalid = split_valid_invalid(flagged)

    processed_out = f"{paths['processed']}/{spec.name}/ingest_date={ingest_date}/"
    quarantine_out = f"{paths['quarantine']}/{spec.name}/ingest_date={ingest_date}/"
    select_processed(valid, spec).write.mode("overwrite").parquet(processed_out)

    invalid_count = invalid.count()
    if invalid_count > 0:
        select_quarantine(invalid, spec).write.mode("overwrite").parquet(quarantine_out)

    valid_count = spark.read.parquet(processed_out).count()

    # Reconciliación estricta de conteos.
    if raw_count != valid_count + invalid_count + dup_removed:
        raise RuntimeError(
            f"Reconciliación fallida en {spec.name}: raw={raw_count} "
            f"!= validas={valid_count} + invalidas={invalid_count} "
            f"+ duplicadas={dup_removed}"
        )

    # Las FK de entidades posteriores se validan contra las filas válidas.
    valid_refs[spec.name] = valid.select(spec.pk).cache()

    metrics = {
        "raw": raw_count,
        "valid": valid_count,
        "quarantined": invalid_count,
        "duplicates_removed": dup_removed,
    }
    logger.info("entidad=%s metrics=%s", spec.name, metrics)
    return metrics


def run(argv: list[str] | None = None, spark: SparkSession | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="LogiFlow ETL: raw -> processed")
    parser.add_argument("--date", required=True)
    parser.add_argument("--raw-path", required=True)
    parser.add_argument("--processed-path", required=True)
    parser.add_argument("--quarantine-path", required=True)
    args, _ = parser.parse_known_args(argv)

    paths = {
        "raw": args.raw_path,
        "processed": args.processed_path,
        "quarantine": args.quarantine_path,
    }

    own_spark = spark is None
    if own_spark:
        spark = SparkSession.builder.appName("logiflow-raw-to-processed").getOrCreate()

    try:
        valid_refs: dict[str, DataFrame] = {}
        all_metrics = {
            spec.name: run_entity(spark, paths, spec, args.date, valid_refs)
            for spec in PROCESSING_ORDER
        }
    finally:
        if own_spark:
            spark.stop()

    logger.info("raw->processed completado fecha=%s metrics=%s", args.date, all_metrics)
    return 0


if __name__ == "__main__":
    sys.exit(run())
