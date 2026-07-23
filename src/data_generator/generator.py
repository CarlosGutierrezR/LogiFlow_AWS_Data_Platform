"""Generación de datos limpios conforme a docs/data-contracts.md v1.0.

Toda la aleatoriedad usa la instancia de random.Random recibida (reproducible
por semilla). Las funciones devuelven listas de dicts; los errores se inyectan
después en error_injector.py, nunca aquí.
"""

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, time, timedelta, timezone

from .config import (
    CARRIERS,
    CITIES,
    SERVICE_LEVELS,
    GeneratorConfig,
)

_TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Ciclo de vida normal de un envío entregado (subconjunto ordenado de EVENT_TYPES).
_HAPPY_PATH: tuple[str, ...] = (
    "pickup",
    "depart_warehouse",
    "in_transit",
    "arrival_hub",
    "out_for_delivery",
    "delivered",
)


def _fmt(ts: datetime) -> str:
    return ts.strftime(_TS_FORMAT)


def generate_warehouses(cfg: GeneratorConfig, rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    for i in range(1, cfg.num_warehouses + 1):
        city, province = CITIES[(i - 1) % len(CITIES)]
        opened = date(2015 + (i % 8), 1 + (i % 12), 1 + (i % 27))
        rows.append(
            {
                "warehouse_id": f"WH-{i:03d}",
                "name": f"Centro Logistico {city}",
                "city": city,
                "province": province,
                "country_code": "ES",
                "capacity_packages": rng.randint(5_000, 50_000),
                "opened_date": opened.isoformat(),
                "is_active": True,
            }
        )
    return rows


def generate_routes(cfg: GeneratorConfig, rng: random.Random, warehouses: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for i in range(1, cfg.num_routes + 1):
        origin = rng.choice(warehouses)
        dest_city, dest_province = rng.choice(CITIES)
        rows.append(
            {
                "route_id": f"RT-{i:04d}",
                "origin_warehouse_id": origin["warehouse_id"],
                "destination_city": dest_city,
                "destination_province": dest_province,
                "distance_km": round(rng.uniform(20, 1200), 1),
                "expected_transit_hours": rng.randint(4, 96),
                "carrier": rng.choice(CARRIERS),
            }
        )
    return rows


def generate_orders(cfg: GeneratorConfig, rng: random.Random, warehouses: list[dict]) -> list[dict]:
    day_compact = cfg.ingest_date.strftime("%Y%m%d")
    base = datetime.combine(cfg.ingest_date, time(6, 0), tzinfo=timezone.utc)
    rows: list[dict] = []
    for i in range(1, cfg.num_orders + 1):
        order_ts = base + timedelta(minutes=rng.randint(0, 14 * 60), seconds=rng.randint(0, 59))
        dest_city, _ = rng.choice(CITIES)
        declared: str = str(round(rng.uniform(10, 3000), 2)) if rng.random() > 0.15 else ""
        rows.append(
            {
                "order_id": f"ORD-{day_compact}-{i:05d}",
                "customer_id": f"CUST-{rng.randint(1, 99999):05d}",
                "order_ts": _fmt(order_ts),
                "origin_warehouse_id": rng.choice(warehouses)["warehouse_id"],
                "destination_city": dest_city,
                "destination_postal_code": f"{rng.randint(1, 52):02d}{rng.randint(0, 999):03d}",
                "num_packages": rng.randint(1, 20),
                "total_weight_kg": round(rng.uniform(0.5, 800), 2),
                "declared_value_eur": declared,
                "service_level": rng.choice(SERVICE_LEVELS),
            }
        )
    return rows


def generate_shipments(
    cfg: GeneratorConfig,
    rng: random.Random,
    orders: list[dict],
    routes: list[dict],
) -> list[dict]:
    day_compact = cfg.ingest_date.strftime("%Y%m%d")
    rows: list[dict] = []
    for i, order in enumerate(orders, start=1):
        route = rng.choice(routes)
        order_ts = datetime.strptime(order["order_ts"], _TS_FORMAT).replace(tzinfo=timezone.utc)
        planned_departure = order_ts + timedelta(hours=rng.randint(1, 12))
        planned_delivery = planned_departure + timedelta(hours=int(route["expected_transit_hours"]))
        status = rng.choices(
            ["delivered", "in_transit", "delayed", "created", "returned", "lost"],
            weights=[55, 20, 12, 8, 4, 1],
        )[0]

        actual_departure = ""
        actual_delivery = ""
        if status not in ("created",):
            actual_departure_dt = planned_departure + timedelta(minutes=rng.randint(-30, 180))
            actual_departure = _fmt(actual_departure_dt)
            if status in ("delivered", "returned"):
                actual_delivery = _fmt(
                    actual_departure_dt
                    + timedelta(hours=int(route["expected_transit_hours"]))
                    + timedelta(minutes=rng.randint(-60, 600))
                )

        rows.append(
            {
                "shipment_id": f"SHP-{day_compact}-{i:05d}",
                "order_id": order["order_id"],
                "route_id": route["route_id"],
                "planned_departure_ts": _fmt(planned_departure),
                "planned_delivery_ts": _fmt(planned_delivery),
                "actual_departure_ts": actual_departure,
                "actual_delivery_ts": actual_delivery,
                "status": status,
                "cost_eur": round(5 + float(route["distance_km"]) * rng.uniform(0.02, 0.09), 2),
            }
        )
    return rows


def generate_delivery_events(
    cfg: GeneratorConfig, rng: random.Random, shipments: list[dict]
) -> list[dict]:
    rows: list[dict] = []
    for shipment in shipments:
        if not shipment["actual_departure_ts"]:
            continue  # envíos aún no salidos no tienen eventos
        start = datetime.strptime(shipment["actual_departure_ts"], _TS_FORMAT).replace(
            tzinfo=timezone.utc
        )

        if shipment["status"] == "delivered":
            sequence = _HAPPY_PATH
        elif shipment["status"] == "returned":
            sequence = _HAPPY_PATH[:4] + ("delivery_failed", "returned")
        elif shipment["status"] == "delayed":
            sequence = _HAPPY_PATH[: rng.randint(3, 5)]
        elif shipment["status"] == "lost":
            sequence = _HAPPY_PATH[: rng.randint(2, 3)]
        else:  # in_transit
            sequence = _HAPPY_PATH[: rng.randint(2, 4)]

        ts = start
        for event_type in sequence:
            ts = ts + timedelta(minutes=rng.randint(30, 600))
            rows.append(
                {
                    "event_id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                    "shipment_id": shipment["shipment_id"],
                    "event_ts": _fmt(ts),
                    "event_type": event_type,
                    "location_city": rng.choice(CITIES)[0],
                    "notes": "",
                }
            )
    return rows


def generate_all(cfg: GeneratorConfig) -> dict[str, list[dict]]:
    """Genera el dataset completo y coherente de un día (sin errores)."""
    rng = random.Random(cfg.seed)
    warehouses = generate_warehouses(cfg, rng)
    routes = generate_routes(cfg, rng, warehouses)
    orders = generate_orders(cfg, rng, warehouses)
    shipments = generate_shipments(cfg, rng, orders, routes)
    events = generate_delivery_events(cfg, rng, shipments)
    return {
        "warehouses": warehouses,
        "routes": routes,
        "orders": orders,
        "shipments": shipments,
        "delivery_events": events,
    }
