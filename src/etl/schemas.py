"""Esquemas explícitos y reglas de validación por entidad.

Fuente de verdad: docs/data-contracts.md v1.0. El crawler infiere esquemas
de landing, pero processed usa SIEMPRE estos esquemas, no los inferidos.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TS_FORMAT = "yyyy-MM-dd'T'HH:mm:ss'Z'"

# Tipos destino admitidos: string | int | double | boolean | timestamp | date
FieldType = str


@dataclass(frozen=True)
class EntitySpec:
    """Especificación de una entidad del contrato."""

    name: str
    pk: str
    fields: dict[str, FieldType]  # nombre -> tipo destino (orden = orden CSV)
    required: tuple[str, ...]
    enums: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # campo -> (mínimo exclusivo permitido, máximo inclusivo o None)
    positive_ranges: dict[str, tuple[float, float | None]] = field(
        default_factory=dict
    )
    # pares (antes, después): después debe ser > antes si ambos presentes
    temporal_order: tuple[tuple[str, str], ...] = ()
    # campo fk -> (entidad referenciada, campo referenciado)
    foreign_keys: dict[str, tuple[str, str]] = field(default_factory=dict)


SERVICE_LEVELS = ("standard", "express", "same_day")
SHIPMENT_STATUSES = ("created", "in_transit", "delivered", "delayed", "lost", "returned")
EVENT_TYPES = (
    "pickup",
    "depart_warehouse",
    "in_transit",
    "arrival_hub",
    "out_for_delivery",
    "delivered",
    "delivery_failed",
    "returned",
)

WAREHOUSES = EntitySpec(
    name="warehouses",
    pk="warehouse_id",
    fields={
        "warehouse_id": "string",
        "name": "string",
        "city": "string",
        "province": "string",
        "country_code": "string",
        "capacity_packages": "int",
        "opened_date": "date",
        "is_active": "boolean",
    },
    required=(
        "warehouse_id",
        "name",
        "city",
        "province",
        "country_code",
        "capacity_packages",
        "opened_date",
        "is_active",
    ),
    positive_ranges={"capacity_packages": (0, None)},
)

ROUTES = EntitySpec(
    name="routes",
    pk="route_id",
    fields={
        "route_id": "string",
        "origin_warehouse_id": "string",
        "destination_city": "string",
        "destination_province": "string",
        "distance_km": "double",
        "expected_transit_hours": "int",
        "carrier": "string",
    },
    required=(
        "route_id",
        "origin_warehouse_id",
        "destination_city",
        "destination_province",
        "distance_km",
        "expected_transit_hours",
        "carrier",
    ),
    enums={"carrier": ("TransIberia", "RapidCargo", "EuroLink", "LogiFast")},
    positive_ranges={
        "distance_km": (0, 5000),
        "expected_transit_hours": (0, 168),
    },
    foreign_keys={"origin_warehouse_id": ("warehouses", "warehouse_id")},
)

ORDERS = EntitySpec(
    name="orders",
    pk="order_id",
    fields={
        "order_id": "string",
        "customer_id": "string",
        "order_ts": "timestamp",
        "origin_warehouse_id": "string",
        "destination_city": "string",
        "destination_postal_code": "string",
        "num_packages": "int",
        "total_weight_kg": "double",
        "declared_value_eur": "double",
        "service_level": "string",
    },
    required=(
        "order_id",
        "customer_id",
        "order_ts",
        "origin_warehouse_id",
        "destination_city",
        "destination_postal_code",
        "num_packages",
        "total_weight_kg",
        "service_level",
    ),
    enums={"service_level": SERVICE_LEVELS},
    positive_ranges={
        "num_packages": (0, 200),
        "total_weight_kg": (0, 5000),
    },
    foreign_keys={"origin_warehouse_id": ("warehouses", "warehouse_id")},
)

SHIPMENTS = EntitySpec(
    name="shipments",
    pk="shipment_id",
    fields={
        "shipment_id": "string",
        "order_id": "string",
        "route_id": "string",
        "planned_departure_ts": "timestamp",
        "planned_delivery_ts": "timestamp",
        "actual_departure_ts": "timestamp",
        "actual_delivery_ts": "timestamp",
        "status": "string",
        "cost_eur": "double",
    },
    required=(
        "shipment_id",
        "order_id",
        "route_id",
        "planned_departure_ts",
        "planned_delivery_ts",
        "status",
        "cost_eur",
    ),
    enums={"status": SHIPMENT_STATUSES},
    positive_ranges={"cost_eur": (0, None)},
    temporal_order=(
        ("planned_departure_ts", "planned_delivery_ts"),
        ("actual_departure_ts", "actual_delivery_ts"),
    ),
    foreign_keys={
        "order_id": ("orders", "order_id"),
        "route_id": ("routes", "route_id"),
    },
)

DELIVERY_EVENTS = EntitySpec(
    name="delivery_events",
    pk="event_id",
    fields={
        "event_id": "string",
        "shipment_id": "string",
        "event_ts": "timestamp",
        "event_type": "string",
        "location_city": "string",
        "notes": "string",
    },
    required=("event_id", "shipment_id", "event_ts", "event_type", "location_city"),
    enums={"event_type": EVENT_TYPES},
    foreign_keys={"shipment_id": ("shipments", "shipment_id")},
)

# Orden de procesamiento: dimensiones antes que hechos (las FK se validan
# contra las filas válidas ya procesadas de la entidad referenciada).
PROCESSING_ORDER: tuple[EntitySpec, ...] = (
    WAREHOUSES,
    ROUTES,
    ORDERS,
    SHIPMENTS,
    DELIVERY_EVENTS,
)

SPECS_BY_NAME: dict[str, EntitySpec] = {s.name: s for s in PROCESSING_ORDER}

# Columnas de linaje añadidas en raw (prefijo _ para no chocar con el contrato).
LINEAGE_COLUMNS = ("_ingest_date", "_source_file", "_load_ts", "_batch_id")
