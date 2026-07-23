"""Configuración del generador. Sin valores sensibles: todo es sintético."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class GeneratorConfig:
    """Parámetros de una ejecución del generador.

    Los valores por defecto siguen docs/data-contracts.md (volumen < 1 MB/día).
    """

    ingest_date: date
    output_dir: Path
    num_orders: int = 80
    num_warehouses: int = 8
    num_routes: int = 25
    error_rate: float = 0.02
    seed: int = 42

    def __post_init__(self) -> None:
        if self.num_orders <= 0:
            raise ValueError("num_orders debe ser > 0")
        if not 0.0 <= self.error_rate <= 0.5:
            raise ValueError("error_rate debe estar entre 0 y 0.5")
        if self.num_warehouses <= 0 or self.num_routes <= 0:
            raise ValueError("num_warehouses y num_routes deben ser > 0")


CARRIERS: tuple[str, ...] = ("TransIberia", "RapidCargo", "EuroLink", "LogiFast")

SERVICE_LEVELS: tuple[str, ...] = ("standard", "express", "same_day")

SHIPMENT_STATUSES: tuple[str, ...] = (
    "created",
    "in_transit",
    "delivered",
    "delayed",
    "lost",
    "returned",
)

EVENT_TYPES: tuple[str, ...] = (
    "pickup",
    "depart_warehouse",
    "in_transit",
    "arrival_hub",
    "out_for_delivery",
    "delivered",
    "delivery_failed",
    "returned",
)

CITIES: tuple[tuple[str, str], ...] = (
    ("Madrid", "Madrid"),
    ("Barcelona", "Barcelona"),
    ("Valencia", "Valencia"),
    ("Sevilla", "Sevilla"),
    ("Zaragoza", "Zaragoza"),
    ("Malaga", "Malaga"),
    ("Bilbao", "Bizkaia"),
    ("Granada", "Granada"),
    ("Murcia", "Murcia"),
    ("Vigo", "Pontevedra"),
    ("Gijon", "Asturias"),
    ("Valladolid", "Valladolid"),
)
