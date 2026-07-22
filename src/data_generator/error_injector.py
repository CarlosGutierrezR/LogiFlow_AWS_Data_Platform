"""Inyección controlada de errores E01-E07 (docs/data-contracts.md).

Cada error inyectado queda registrado en un manifiesto para poder verificar
después que las reglas de calidad lo detectan. La inyección muta copias de las
filas, nunca los datos limpios originales.
"""

from __future__ import annotations

import copy
import random
from dataclasses import asdict, dataclass

# Campos obligatorios candidatos a E01 por entidad (subconjunto seguro).
_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "warehouses": ("city", "country_code"),
    "routes": ("carrier", "destination_city"),
    "orders": ("customer_id", "destination_city", "service_level"),
    "shipments": ("order_id", "status"),
    "delivery_events": ("shipment_id", "event_type"),
}

_PK_FIELD: dict[str, str] = {
    "warehouses": "warehouse_id",
    "routes": "route_id",
    "orders": "order_id",
    "shipments": "shipment_id",
    "delivery_events": "event_id",
}

# Códigos aplicables por entidad, según el contrato.
_APPLICABLE: dict[str, tuple[str, ...]] = {
    "warehouses": ("E01",),
    "routes": ("E01",),
    "orders": ("E01", "E02", "E04", "E06"),
    "shipments": ("E01", "E02", "E03", "E04", "E05", "E06"),
    "delivery_events": ("E01", "E03", "E06", "E07"),
}


@dataclass(frozen=True)
class InjectedError:
    entity: str
    error_code: str
    pk_value: str
    field: str
    detail: str


def _inject_one(
    entity: str, rows: list[dict], idx: int, code: str, rng: random.Random
) -> InjectedError:
    row = rows[idx]
    pk_field = _PK_FIELD[entity]
    pk_value = str(row[pk_field])

    if code == "E01":
        field = rng.choice(_REQUIRED_FIELDS[entity])
        row[field] = ""
        return InjectedError(entity, code, pk_value, field, "campo obligatorio vacío")

    if code == "E02":
        duplicate = copy.deepcopy(row)
        rows.append(duplicate)
        return InjectedError(entity, code, pk_value, pk_field, "clave primaria duplicada")

    if code == "E03":
        fk_field = "order_id" if entity == "shipments" else "shipment_id"
        broken = "ORD-00000000-99999" if entity == "shipments" else "SHP-00000000-99999"
        row[fk_field] = broken
        return InjectedError(entity, code, pk_value, fk_field, "referencia inexistente")

    if code == "E04":
        field = "total_weight_kg" if entity == "orders" else "cost_eur"
        row[field] = -abs(float(row[field]) if row[field] != "" else 1.0)
        return InjectedError(entity, code, pk_value, field, "valor negativo fuera de rango")

    if code == "E05":
        row["actual_departure_ts"] = "2026-07-22T20:00:00Z"
        row["actual_delivery_ts"] = "2026-07-22T05:00:00Z"
        return InjectedError(
            entity, code, pk_value, "actual_delivery_ts", "entrega anterior a salida"
        )

    if code == "E06":
        field = {
            "orders": "service_level",
            "shipments": "status",
            "delivery_events": "event_type",
        }[entity]
        row[field] = "INVALID_VALUE"
        return InjectedError(entity, code, pk_value, field, "valor fuera de enumeración")

    if code == "E07":
        row["event_ts"] = "31-02-2026 99:99"
        return InjectedError(entity, code, pk_value, "event_ts", "timestamp malformado")

    raise ValueError(f"Código de error desconocido: {code}")


def inject_errors(
    datasets: dict[str, list[dict]], error_rate: float, seed: int
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Devuelve (datasets con errores, manifiesto de errores inyectados).

    El número de errores por entidad es round(n_filas * error_rate), mínimo 1
    si error_rate > 0 y la entidad admite errores.
    """
    rng = random.Random(seed + 1)  # flujo independiente del generador
    result: dict[str, list[dict]] = {k: copy.deepcopy(v) for k, v in datasets.items()}
    manifest: list[dict] = []

    if error_rate <= 0:
        return result, manifest

    for entity, rows in result.items():
        applicable = _APPLICABLE.get(entity, ())
        if not applicable or not rows:
            continue
        n_errors = max(1, round(len(rows) * error_rate))
        # Índices sin repetición para no acumular dos errores en la misma fila.
        indices = rng.sample(range(len(rows)), min(n_errors, len(rows)))
        for idx in indices:
            code = rng.choice(applicable)
            if code == "E05" and rows[idx].get("actual_delivery_ts", "") == "":
                code = "E01"  # E05 requiere timestamps presentes; degradar a E01
            injected = _inject_one(entity, rows, idx, code, rng)
            manifest.append(asdict(injected))

    return result, manifest
