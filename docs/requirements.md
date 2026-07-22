# Requisitos

Se detallarán en la Fase 4 (contratos de datos) y siguientes. Requisitos iniciales derivados del charter:

**Funcionales:** ingestión batch diaria de pedidos y envíos; capas landing→curated; catálogo consultable; KPIs de entrega (tiempos, incidencias, rendimiento por ruta/almacén) en Athena.

**No funcionales:** reproducibilidad total (Terraform), idempotencia, coste casi nulo, sin secretos versionados, evidencia de ejecución por fase.
