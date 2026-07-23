"""Job 3: processed → curated (modelo dimensional analítico).

Construye por fecha de ingesta:
- dim_warehouse: dimensión de almacenes (snapshot del día).
- dim_route: dimensión de rutas enriquecida con la ciudad del almacén origen.
- fact_shipments: hechos de envíos con métricas de negocio:
    * delivery_delay_hours  (retraso vs plan; negativo = adelanto)
    * actual_transit_hours  (tránsito real)
    * on_time               (entregado dentro del plan)
    * is_incident           (delayed | lost | returned)

Reconciliación: filas de fact_shipments == filas de processed.shipments.

Ejecución local (pruebas):
    python -m src.etl.processed_to_curated --date 2026-07-22 \
        --processed-path data/local/processed --curated-path data/local/curated
"""

from __future__ import annotations

import argparse
import logging
import sys

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

logger = logging.getLogger("etl.processed_to_curated")

_SECONDS_PER_HOUR = 3600.0


def _read(spark: SparkSession, root: str, entity: str, ingest_date: str) -> DataFrame:
    return spark.read.parquet(f"{root}/{entity}/ingest_date={ingest_date}/")


def build_dim_warehouse(warehouses: DataFrame) -> DataFrame:
    return warehouses.select(
        "warehouse_id",
        "name",
        "city",
        "province",
        "country_code",
        "capacity_packages",
        "opened_date",
        "is_active",
        "_ingest_date",
    )


def build_dim_route(routes: DataFrame, warehouses: DataFrame) -> DataFrame:
    origin = warehouses.select(
        F.col("warehouse_id").alias("origin_warehouse_id"),
        F.col("city").alias("origin_city"),
        F.col("province").alias("origin_province"),
    )
    return routes.join(origin, on="origin_warehouse_id", how="left").select(
        "route_id",
        "origin_warehouse_id",
        "origin_city",
        "origin_province",
        "destination_city",
        "destination_province",
        "distance_km",
        "expected_transit_hours",
        "carrier",
        "_ingest_date",
    )


def build_fact_shipments(shipments: DataFrame, orders: DataFrame, routes: DataFrame) -> DataFrame:
    order_attrs = orders.select(
        "order_id",
        "customer_id",
        F.col("origin_warehouse_id").alias("order_origin_warehouse_id"),
        F.col("destination_city").alias("order_destination_city"),
        "service_level",
        "num_packages",
        "total_weight_kg",
    )
    route_attrs = routes.select(
        "route_id",
        "carrier",
        "distance_km",
        "expected_transit_hours",
    )

    fact = shipments.join(order_attrs, on="order_id", how="left").join(
        route_attrs, on="route_id", how="left"
    )

    delay_seconds = F.col("actual_delivery_ts").cast("long") - F.col("planned_delivery_ts").cast(
        "long"
    )
    transit_seconds = F.col("actual_delivery_ts").cast("long") - F.col("actual_departure_ts").cast(
        "long"
    )

    return fact.select(
        "shipment_id",
        "order_id",
        "route_id",
        "customer_id",
        F.col("order_origin_warehouse_id").alias("origin_warehouse_id"),
        F.col("order_destination_city").alias("destination_city"),
        "carrier",
        "service_level",
        "status",
        "planned_departure_ts",
        "planned_delivery_ts",
        "actual_departure_ts",
        "actual_delivery_ts",
        "num_packages",
        "total_weight_kg",
        "distance_km",
        "expected_transit_hours",
        "cost_eur",
        (delay_seconds / _SECONDS_PER_HOUR).alias("delivery_delay_hours"),
        (transit_seconds / _SECONDS_PER_HOUR).alias("actual_transit_hours"),
        F.when(
            F.col("actual_delivery_ts").isNotNull(),
            F.col("actual_delivery_ts") <= F.col("planned_delivery_ts"),
        ).alias("on_time"),
        F.col("status").isin("delayed", "lost", "returned").alias("is_incident"),
        "_ingest_date",
    )


def run(argv: list[str] | None = None, spark: SparkSession | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(description="LogiFlow ETL: processed -> curated")
    parser.add_argument("--date", required=True)
    parser.add_argument("--processed-path", required=True)
    parser.add_argument("--curated-path", required=True)
    args, _ = parser.parse_known_args(argv)

    own_spark = spark is None
    if own_spark:
        spark = SparkSession.builder.appName("logiflow-processed-to-curated").getOrCreate()

    try:
        warehouses = _read(spark, args.processed_path, "warehouses", args.date)
        routes = _read(spark, args.processed_path, "routes", args.date)
        orders = _read(spark, args.processed_path, "orders", args.date)
        shipments = _read(spark, args.processed_path, "shipments", args.date)

        outputs = {
            "dim_warehouse": build_dim_warehouse(warehouses),
            "dim_route": build_dim_route(routes, warehouses),
            "fact_shipments": build_fact_shipments(shipments, orders, routes),
        }

        counts: dict[str, int] = {}
        for table, df in outputs.items():
            out = f"{args.curated_path}/{table}/ingest_date={args.date}/"
            df.write.mode("overwrite").parquet(out)
            counts[table] = spark.read.parquet(out).count()
            logger.info("tabla=%s filas=%d destino=%s", table, counts[table], out)

        shipments_count = shipments.count()
        if counts["fact_shipments"] != shipments_count:
            raise RuntimeError(
                "Reconciliación fallida: fact_shipments="
                f"{counts['fact_shipments']} != processed.shipments={shipments_count}"
            )
    finally:
        if own_spark:
            spark.stop()

    logger.info("processed->curated completado fecha=%s counts=%s", args.date, counts)
    return 0


if __name__ == "__main__":
    sys.exit(run())
