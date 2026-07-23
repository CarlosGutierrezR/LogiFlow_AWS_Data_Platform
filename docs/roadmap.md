# Roadmap por fases

Estados: `pendiente` | `en curso` | `completada (con evidencia)`.

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Fundación del repositorio: estructura, docs, git local | en curso |
| 1 | Cuenta AWS segura: creación, MFA, identidad de trabajo, presupuesto y alarmas, AWS CLI | completada con evidencia, salvo MFA/rotación de contraseña de root (pendiente, responsabilidad de Carlos) |
| 2 | Bootstrap Terraform: backend de estado, proveedor, tags, verificación de región (ADR-002) | completada (evidencia 2026-07-22: TF 1.15.8, provider aws 6.55.0, validate y plan limpios; región eu-west-1 decidida) |
| 3 | Capa de almacenamiento: buckets S3 (landing/raw/processed/curated/quarantine), cifrado, public access block, políticas | completada (evidencia 2026-07-22: apply de 25 recursos, outputs con los 5 buckets en eu-west-1) |
| 4 | Contratos de datos + generador de datos sintéticos de logística con errores controlados | completada (evidencia 2026-07-22: contratos v1.0 aprobados; 13/13 tests pytest; ejecución real con 558 filas y manifiesto de 13 errores) |
| 5 | Ingestión batch a landing + catalogación (Glue Catalog, crawlers) | completada (evidencia 2026-07-22: 12 archivos subidos con idempotencia demostrada; crawler catalogó 5 tablas con particiones ingest_date) |
| 6 | ETL PySpark landing→raw→processed + pruebas unitarias locales | completada (evidencia 2026-07-22: 6/6 tests Spark local + 4 runs SUCCEEDED en Glue 5.0 con 2 días procesados; quarantine y reconciliación operativas) |
| 7 | Calidad de datos (Glue Data Quality) + cuarentena + reconciliación | completada (evidencia 2026-07-22: cuarentena y reconciliación en F6; catálogo processed con 5 tablas; ruleset DQ evaluado con Score 1.0, 7/7 PASS) |
| 8 | Modelo dimensional en curated + Athena | completada (evidencia 2026-07-22: job curated ×2 días SUCCEEDED, 3 tablas dimensionales catalogadas, 3 KPIs ejecutados en Athena con resultados) |
| 9 | Orquestación: Step Functions + EventBridge + reintentos | Step Functions completada (evidencia 2026-07-23: state machine l2r→r2p→curated con .sync + retries; ejecución end-to-end SUCCEEDED en ~5 min con un disparo). EventBridge Scheduler pendiente si se desea disparo automático |
| 10 | Observabilidad: CloudWatch, SNS, logging estructurado, runbook | completada (evidencia 2026-07-23: tema SNS + 4 alarmas CloudWatch desplegadas; alarma de pipeline sobre ExecutionsFailed. Suscripción email pendiente de confirmar por Carlos) |
| 11 | Publicación en GitHub + CI/CD (GitHub Actions: lint, fmt, validate, tests) | completada (evidencia 2026-07-23: repo público github.com/CarlosGutierrezR/LogiFlow_AWS_Data_Platform; CI run #2 en verde, jobs Python y Terraform SUCCESS) |
| 12 | Cierre del núcleo: documentación final, evidencias, destrucción controlada y coste real | completada (2026-07-23: coste real = 0 cargado, cubierto por créditos del plan gratuito; procedimiento de terraform destroy documentado en runbook; README con capturas) |
| 13+ | Extensiones (streaming, Lake Formation, Redshift, QuickSight, Iceberg) — cada una con ADR propio | pendiente |

Regla: ninguna fase se marca completada sin evidencia real de ejecución.
