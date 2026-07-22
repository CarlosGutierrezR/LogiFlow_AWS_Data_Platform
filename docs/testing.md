# Estrategia de pruebas

Pendiente de implementación (desde Fase 4 en adelante). Enfoque previsto:

- **Unitarias:** transformaciones PySpark con datos controlados (pytest, ejecución local).
- **De calidad:** reglas Glue Data Quality por dataset + reconciliación de conteos entre capas.
- **De integración:** ejecución end-to-end del pipeline en AWS con dataset sintético pequeño.
- **De infraestructura:** `terraform fmt -check`, `terraform validate`, revisión de `terraform plan`.

Regla: ningún resultado de prueba se documenta sin haberse ejecutado realmente.
