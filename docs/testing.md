# Estrategia de pruebas

## Estado actual

- Fase 4: `tests/test_data_generator.py` — 13 pruebas del generador (contratos, claves, FK, enums, rangos, coherencia temporal, reproducibilidad por semilla, inyección de errores con manifiesto, CLI end-to-end). Última ejecución: 2026-07-22, 13/13 passed (Python 3.10.12, pytest 9.1.1).
- Ejecución: `python -m pytest tests/ -v` desde la raíz del repositorio (requiere `pip install pytest`).

## Enfoque general

- **Unitarias:** transformaciones PySpark con datos controlados (pytest, ejecución local).
- **De calidad:** reglas Glue Data Quality por dataset + reconciliación de conteos entre capas.
- **De integración:** ejecución end-to-end del pipeline en AWS con dataset sintético pequeño.
- **De infraestructura:** `terraform fmt -check`, `terraform validate`, revisión de `terraform plan`.

Regla: ningún resultado de prueba se documenta sin haberse ejecutado realmente.
