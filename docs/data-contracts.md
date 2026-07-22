# Contratos de datos — LogiFlow (dominio logística)

Versión 1.0 — 2026-07-22. Cualquier cambio de esquema exige nueva versión aquí y entrada en decisions.md.

Convenciones: nombres de campos en `snake_case` inglés; timestamps ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`); decimales con punto; moneda EUR.

## Visión general

| Entidad | Tipo | Formato fuente | Frecuencia | Clave primaria |
|---|---|---|---|---|
| warehouses | maestro (dimensión) | CSV | completo diario | warehouse_id |
| routes | maestro (dimensión) | CSV | completo diario | route_id |
| orders | transaccional | CSV | incremental diario | order_id |
| shipments | transaccional | CSV | incremental diario | shipment_id |
| delivery_events | eventos | JSON Lines | incremental diario | event_id |

Relaciones: `shipments.order_id → orders`, `shipments.route_id → routes`, `routes.origin_warehouse_id → warehouses`, `delivery_events.shipment_id → shipments`.

## warehouses (CSV)

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| warehouse_id | string | no | patrón `WH-[0-9]{3}`, único |
| name | string | no | — |
| city | string | no | — |
| province | string | no | — |
| country_code | string | no | ISO-3166 alpha-2 (`ES`, `PT`, `FR`) |
| capacity_packages | int | no | > 0 |
| opened_date | date | no | <= fecha actual |
| is_active | bool | no | — |

## routes (CSV)

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| route_id | string | no | patrón `RT-[0-9]{4}`, único |
| origin_warehouse_id | string | no | FK a warehouses |
| destination_city | string | no | — |
| destination_province | string | no | — |
| distance_km | decimal | no | > 0 y < 5000 |
| expected_transit_hours | int | no | > 0 y <= 168 |
| carrier | string | no | catálogo: `TransIberia`, `RapidCargo`, `EuroLink`, `LogiFast` |

## orders (CSV)

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| order_id | string | no | patrón `ORD-[0-9]{8}-[0-9]{5}`, único |
| customer_id | string | no | patrón `CUST-[0-9]{5}` |
| order_ts | timestamp | no | <= ahora |
| origin_warehouse_id | string | no | FK a warehouses |
| destination_city | string | no | — |
| destination_postal_code | string | no | 5 dígitos |
| num_packages | int | no | entre 1 y 200 |
| total_weight_kg | decimal | no | > 0 y <= 5000 |
| declared_value_eur | decimal | sí | >= 0 si presente |
| service_level | string | no | `standard` \| `express` \| `same_day` |

## shipments (CSV)

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| shipment_id | string | no | patrón `SHP-[0-9]{8}-[0-9]{5}`, único |
| order_id | string | no | FK a orders |
| route_id | string | no | FK a routes |
| planned_departure_ts | timestamp | no | — |
| planned_delivery_ts | timestamp | no | > planned_departure_ts |
| actual_departure_ts | timestamp | sí | — |
| actual_delivery_ts | timestamp | sí | > actual_departure_ts si ambos presentes |
| status | string | no | `created` \| `in_transit` \| `delivered` \| `delayed` \| `lost` \| `returned` |
| cost_eur | decimal | no | > 0 |

## delivery_events (JSON Lines)

| Campo | Tipo | Nulo | Regla |
|---|---|---|---|
| event_id | string | no | UUID v4, único |
| shipment_id | string | no | FK a shipments |
| event_ts | timestamp | no | — |
| event_type | string | no | `pickup` \| `depart_warehouse` \| `in_transit` \| `arrival_hub` \| `out_for_delivery` \| `delivered` \| `delivery_failed` \| `returned` |
| location_city | string | no | — |
| notes | string | sí | — |

## Reglas de calidad transversales

1. Unicidad de clave primaria en cada archivo.
2. Integridad referencial según las relaciones declaradas.
3. Coherencia temporal: entregas posteriores a salidas; eventos dentro del ciclo de vida del envío.
4. Enumeraciones cerradas (valores fuera de catálogo → cuarentena).
5. Reconciliación de conteos entre capas tras cada carga.
6. Registro inválido → zona quarantine con motivo y origen; nunca se descarta silenciosamente.

## Errores sintéticos controlados (para probar la calidad)

El generador inyecta errores con tasa configurable (por defecto 2 %) y los registra en un manifiesto para poder verificar la detección:

| Código | Error | Entidades |
|---|---|---|
| E01 | nulo en campo obligatorio | todas |
| E02 | clave primaria duplicada | orders, shipments |
| E03 | FK rota (referencia inexistente) | shipments, delivery_events |
| E04 | valor fuera de rango (peso/coste negativo) | orders, shipments |
| E05 | incoherencia temporal (entrega < salida) | shipments |
| E06 | valor fuera de enumeración | orders, shipments, delivery_events |
| E07 | timestamp malformado | delivery_events |

## Nomenclatura de archivos en landing

```
landing/{entidad}/ingest_date=YYYY-MM-DD/{entidad}_YYYYMMDD.csv|jsonl
```

Volumen inicial por día sintético: ~50-100 orders, ~1 shipment por order, ~4-6 events por shipment, 8 warehouses, 25 routes. Total < 1 MB/día (control de costes).
