-- KPIs de logística LogiFlow — capa curated (Athena)
-- Base de datos: logiflow_dev_curated. Workgroup: logiflow-dev-wg.
-- Ejecutar cada consulta por separado con: aws athena start-query-execution.

-- KPI 1: rendimiento de entrega por transportista
--   volumen, % de entregas a tiempo, retraso medio (h) y coste medio.
SELECT
    carrier,
    COUNT(*)                                               AS total_shipments,
    SUM(CASE WHEN on_time THEN 1 ELSE 0 END)               AS on_time_deliveries,
    ROUND(AVG(CASE WHEN on_time THEN 1.0 ELSE 0.0 END) * 100, 1) AS on_time_pct,
    ROUND(AVG(delivery_delay_hours), 2)                    AS avg_delay_hours,
    ROUND(AVG(cost_eur), 2)                                AS avg_cost_eur
FROM fact_shipments
GROUP BY carrier
ORDER BY on_time_pct DESC;

-- KPI 2: tasa de incidencias por almacén de origen
SELECT
    f.origin_warehouse_id,
    w.city                                                 AS warehouse_city,
    COUNT(*)                                               AS total_shipments,
    SUM(CASE WHEN f.is_incident THEN 1 ELSE 0 END)         AS incidents,
    ROUND(AVG(CASE WHEN f.is_incident THEN 1.0 ELSE 0.0 END) * 100, 1) AS incident_pct
FROM fact_shipments f
LEFT JOIN dim_warehouse w
    ON f.origin_warehouse_id = w.warehouse_id
GROUP BY f.origin_warehouse_id, w.city
ORDER BY incident_pct DESC;

-- KPI 3: distribución de envíos por estado y nivel de servicio
SELECT
    service_level,
    status,
    COUNT(*) AS shipments
FROM fact_shipments
GROUP BY service_level, status
ORDER BY service_level, shipments DESC;

-- KPI 4: rutas más lentas (retraso medio) con al menos 2 envíos entregados
SELECT
    r.route_id,
    r.origin_city,
    r.destination_city,
    r.carrier,
    COUNT(*)                                AS delivered_shipments,
    ROUND(AVG(f.actual_transit_hours), 1)   AS avg_transit_hours,
    ROUND(AVG(r.expected_transit_hours), 1) AS expected_transit_hours,
    ROUND(AVG(f.delivery_delay_hours), 2)   AS avg_delay_hours
FROM fact_shipments f
JOIN dim_route r
    ON f.route_id = r.route_id
WHERE f.actual_delivery_ts IS NOT NULL
GROUP BY r.route_id, r.origin_city, r.destination_city, r.carrier
HAVING COUNT(*) >= 2
ORDER BY avg_delay_hours DESC
LIMIT 10;
