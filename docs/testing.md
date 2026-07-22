# Estrategia de pruebas

## Estado actual

- Fase 4: `tests/test_data_generator.py` — 13 pruebas del generador (contratos, claves, FK, enums, rangos, coherencia temporal, reproducibilidad por semilla, inyección de errores con manifiesto, CLI end-to-end). Última ejecución: 2026-07-22, 13/13 passed (Python 3.10.12, pytest 9.1.1).
- Fase 5: `tests/test_upload_landing.py` — 6 pruebas de ingestión con cliente S3 simulado (idempotencia incluida). 19/19 en Linux/py3.10 y Windows/py3.14.
- Fase 6: `tests/test_etl_pipeline.py` — 6 pruebas del ETL PySpark: linaje en raw, esquema tipado, unicidad de PK, reconciliación de conteos y detección del 100 % de los errores inyectados. Última ejecución: 2026-07-22, 6/6 passed (Spark 3.5.9 local + Java 11, equivalente a Glue 5.0). Requiere `pip install "pyspark==3.5.*"` y Java; si pyspark no está instalado, estas pruebas se omiten automáticamente (importorskip) — en Windows sin Spark el resto de la suite sigue en verde.
- Ejecución: `python -m pytest tests/ -v` desde la raíz del repositorio (requiere `pip install pytest`).

## Enfoque general

- **Unitarias:** transformaciones PySpark con datos controlados (pytest, ejecución local).
- **De calidad:** reglas Glue Data Quality por dataset + reconciliación de conteos entre capas.
- **De integración:** ejecución end-to-end del pipeline en AWS con dataset sintético pequeño.
- **De infraestructura:** `terraform fmt -check`, `terraform validate`, revisión de `terraform plan`.

Regla: ningún resultado de prueba se documenta sin haberse ejecutado realmente.
