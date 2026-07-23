# Changelog

## 2026-07-22 — Fase 1 (parcial): cuenta y control de costes

- Cuenta AWS personal creada (verificación en consola).
- Presupuesto `logiflow-zero-spend-budget` creado (plantilla gasto cero, alerta >0,01 USD por email). Confirmado por la consola.
- Preferencias de alertas activadas: nivel gratuito + alertas de facturación de CloudWatch. Confirmado por la consola.
- Incidente de seguridad: contraseña root expuesta en captura durante la sesión de trabajo → pendiente rotación de contraseña y MFA (bloqueado ~24 h por política según el usuario).
- Pendiente: MFA root, cambio de contraseña, IAM Identity Center, AWS CLI + Agent Toolkit (ADR-005).

## 2026-07-22 — Fase 1 cerrada (con una excepción)

- Cuenta activada tras resolver la verificación de la tarjeta (retención temporal ~1 USD según pantalla oficial de AWS).
- Usuario IAM `carlos-admin` creado con AdministratorAccess + MFA virtual; contraseña definitiva establecida por el usuario (ADR-006: se descartó Identity Center para conservar el plan gratuito y sus créditos).
- AWS CLI 2.36.5 en Windows 11; `aws login` con credenciales temporales; `aws sts get-caller-identity` verifica `user/carlos-admin`. Región CLI por defecto: eu-south-2.
- Excepción abierta: MFA y rotación de contraseña del usuario root.

## 2026-07-22 — Fase 2: bootstrap de Terraform

- ADR-002 resuelta: verificado en consola que Glue Data Quality NO está en eu-south-2; región del proyecto: **eu-west-1** (decisión de Carlos). CLI reconfigurada.
- Creado `terraform/`: versions.tf (TF >=1.9 <2.0, provider aws ~> 6.0), providers.tf (default_tags), variables.tf (con validaciones), locals.tf, terraform.tfvars.example.
- Evidencia de ejecución en Windows: Terraform v1.15.8, provider aws v6.55.0 (signed), `terraform validate` OK, `terraform plan` sin cambios. `.terraform.lock.hcl` generado (se versiona).
- Sin recursos creados; coste cero.

## 2026-07-22 — Fase 3: capa de almacenamiento S3 desplegada

- `terraform apply`: 25 recursos creados sin errores (evidencia: "Apply complete! Resources: 25 added, 0 changed, 0 destroyed").
- 5 buckets en eu-west-1: logiflow-dev-{landing,raw,processed,curated,quarantine}-<account_id>.
- Configuración: Block Public Access total, SSE-S3, versionado en raw/curated, expiración landing 30d / quarantine 90d, limpieza de multiparts (7d), tags automáticos.
- Estado de Terraform: backend local (terraform.tfstate, no versionado). Migración a backend S3 pendiente de fase posterior.
- Coste: buckets vacíos, 0 USD. Rollback: `terraform destroy` (vaciar buckets antes si contienen datos).

## 2026-07-22 — Fase 4: contratos de datos y generador sintético

- docs/data-contracts.md v1.0 aprobado por Carlos: 5 entidades (warehouses, routes, orders, shipments CSV; delivery_events JSONL), reglas de calidad y taxonomía de errores E01-E07.
- src/data_generator/: config, generator, error_injector, writers, main (CLI). Solo stdlib; reproducible por semilla; logging estructurado; manifiesto JSON de errores inyectados.
- tests/test_data_generator.py: 13 pruebas (unicidad PK, FK, enums, rangos, coherencia temporal, reproducibilidad, inyección, CLI end-to-end). Evidencia: 13/13 passed (Python 3.10, pytest 9.1.1).
- Ejecución real: 558 filas, 5 entidades, particionado ingest_date=YYYY-MM-DD, 13 errores inyectados y registrados. Salida en data/local/ (no versionada).
- Sin recursos AWS nuevos; coste cero.

## 2026-07-22 — Fase 5: ingestión a S3 y catalogación

- src/ingestion/upload_landing.py: subida idempotente (omite objetos existentes con mismo tamaño) con cliente S3 inyectable; 6 pruebas nuevas (19 en total, todas pasando en Linux/py3.10 y Windows/py3.14).
- Dependencias de ejecución: boto3 + botocore[crt] (el proveedor de credenciales de `aws login` requiere awscrt; detectado y resuelto durante la fase).
- terraform/glue_catalog.tf aplicado (5 recursos): base de datos logiflow_dev_landing, rol de crawler con lectura restringida al bucket landing, crawler bajo demanda sin schedule.
- Evidencia: 12 archivos (2 días × 5 entidades + 2 manifiestos) en s3://logiflow-dev-landing-.../; reejecución con "subidos=0 omitidos=6"; crawler catalogó 5 tablas y particiones ["2026-07-22","2026-07-23"].
- Coste: primeras ejecuciones facturables (3 pasadas de crawler, una en vacío). Importe esperado: céntimos; verificar en Billing y registrar en cost-control.md.

## 2026-07-22 — Fase 6a: ETL PySpark (desarrollo y pruebas locales)

- src/etl/schemas.py: esquemas explícitos y reglas por entidad (fuente de verdad: data-contracts v1.0); processed nunca usa los esquemas inferidos por el crawler.
- src/etl/landing_to_raw.py: conserva el dato original (todo string) + linaje (_ingest_date, _source_file, _load_ts, _batch_id); Parquet particionado; idempotente por sobrescritura de partición.
- src/etl/raw_to_processed.py: dedup por PK, validación de obligatorios/enums/rangos/timestamps/coherencia temporal/FKs (contra filas válidas, dimensiones→hechos), tipado al contrato; inválidas a quarantine con motivos "Exx:campo:detalle"; reconciliación estricta de conteos (falla el job si no cuadra).
- Jobs portables: argparse (sin dependencia de awsglue); mismo script en Spark local y Glue.
- Evidencia: 6/6 pruebas pasadas en Spark 3.5.9 + Java 11 (runtime equivalente a Glue 5.0), incluida la detección del 100 % de errores inyectados y reconciliación en 5 entidades.
- Pendiente (6b): despliegue como Glue jobs (Terraform), ejecución real en AWS y coste asociado.

## 2026-07-22 — Fase 6b: ETL desplegado y ejecutado en AWS

- terraform/glue_jobs.tf (11 recursos): bucket de artefactos, src.zip + entry points, rol IAM por capas, 2 jobs Glue 5.0 (G.1X ×2, timeout 10 min, sin reintentos, bajo demanda).
- Evidencia final: 4 runs SUCCEEDED (l2r 135s/108s, r2p 126s/78s) para 2026-07-22 y 2026-07-23; particiones en processed y quarantine de ambos días.
- Incidencias reales resueltas (documentadas en runbook):
  1. `SystemExit: 0` → Glue marca FAILED si el script llama a sys.exit() aunque el código sea 0; corregido en los entry points.
  2. Carrera de dependencia: r2p lanzado antes de que l2r terminara → PATH_NOT_FOUND; motiva la orquestación (Fase 9).
  3. `ConcurrentRunsExceededException`: un run recién terminado sigue contando para el límite de concurrencia unos segundos.
- Coste: ~9 runs de Glue en total durante la fase (incl. fallidos) — verificar importe real en Billing y anotar en cost-control.md.

## 2026-07-22 — Fase 7: catálogo de processed + Glue Data Quality

- terraform/glue_quality.tf: base de datos logiflow_dev_processed, crawler bajo demanda con rol de lectura restringida, y 2 rulesets DQ (orders, shipments) gateados con variable enable_dq_rulesets (despliegue en 2 pasos porque los rulesets referencian tablas del crawler).
- Evidencia: crawler catalogó las 5 tablas de processed; evaluación DQ sobre orders con **Score 1.0 y 7/7 reglas PASS** (run dqrun-81aa9e50...).
- La validación custom del ETL (F6) y la verificación gestionada (Glue DQ) quedan como doble control de calidad, cada una con su rol: la primera limpia y pone en cuarentena, la segunda certifica.
- Coste: 1 run de crawler + 1 evaluación DQ (DPU-tiempo, céntimos). Pendiente consolidar importes reales en Billing.

## 2026-07-22 — Fase 8: modelo dimensional (curated) + Athena

- src/etl/processed_to_curated.py: dim_warehouse, dim_route (enriquecida con ciudad de origen), fact_shipments con métricas de negocio (delivery_delay_hours, actual_transit_hours, on_time, is_incident); reconciliación fact == processed.shipments.
- Verificación local de la lógica curated (troceada por límite de 45s del sandbox): reconcile True, dim_route sin nulos, coherencia on_time/delay/incident, sin claves nulas. Suite completa test_curated_pipeline.py queda para CI/máquina más rápida.
- terraform: job processed-to-curated (Glue 5.0), crawler+db curated, Athena workgroup (corte 1 GB/consulta, resultados cifrados con expiración 7d). Rol ETL ampliado a curated. ops/athena_queries/kpis.sql con 4 KPIs.
- Fix: variable enable_dq_rulesets movida a terraform.tfvars (antes cada apply sin -var borraba los rulesets DQ). tfvars no versionado; example actualizado.
- Evidencia: 2 días curated SUCCEEDED; 3 tablas catalogadas; 3 KPIs ejecutados en Athena (rendimiento por transportista, incidencias por almacén, estado×servicio) con resultados coherentes.
- OBSERVACIÓN: on_time_pct ≈ 0% en todos los transportistas. No es bug del ETL (delay medio positivo bien calculado) sino sesgo del generador (entregas casi siempre tarde). Mejora futura: ajustar offsets temporales en generate_shipments para on-time realista.
- Coste: job ×2 + 1 crawler + 3 consultas Athena (KB escaneados). Pendiente consolidar en Billing.

## 2026-07-23 — Fase 9: orquestación con Step Functions

- terraform/step_functions.tf: state machine logiflow-dev-batch-pipeline (STANDARD) que encadena landing→raw→processed→curated con integración síncrona (.sync), reintentos (2 intentos, backoff x2, cubre ConcurrentRunsExceededException) y Catch a estado PipelineFailed. Rol de ejecución con permisos solo sobre los 3 jobs.
- Incidencia resuelta (documentada en runbook): con .sync la salida del job reemplaza el input, perdiendo $.ingest_date en el segundo estado. Solución: ResultPath por tarea para preservar el input a lo largo de la cadena.
- Evidencia: ejecución end-to-end con input {"ingest_date":"2026-07-23"} → SUCCEEDED en ~5 min (3 jobs en serie, sin carreras ni intervención manual). Resuelve las condiciones de carrera de la Fase 6.
- Coste: 3 runs de Glue por ejecución del pipeline (DPU-tiempo). El state machine STANDARD factura por transición de estado (céntimos).

## 2026-07-23 — Fase 10: observabilidad (CloudWatch + SNS)

- terraform/observability.tf: tema SNS logiflow-dev-alerts con suscripción email (var.alert_email); alarma pipeline_failed sobre AWS/States ExecutionsFailed (señal principal); 4 alarmas totales (pipeline + numFailedTasks por cada job Glue).
- Evidencia: 6 recursos creados; alarmas en INSUFFICIENT_DATA (normal sin métricas recientes). Suscripción email CONFIRMADA (2026-07-23): list-subscriptions muestra ARN en lugar de PendingConfirmation → notificaciones activas.
- Limitación documentada: numFailedTasks detecta fallos de tareas Spark, no todos los fallos de job (p.ej. SystemExit). La alarma del pipeline (ExecutionsFailed) es la de referencia y cubre cualquier fallo de la cadena orquestada.
- Coste: SNS y CloudWatch alarmas a este volumen son céntimos o dentro de free tier.

## 2026-07-22 — Fase 0: fundación del repositorio

- Estructura inicial del proyecto y documentación base (charter, arquitectura, roadmap, seguridad, costes).
- ADR-001 a ADR-004 registradas en decisions.md.
- `.gitignore` y `.gitattributes` con protección de secretos y estado de Terraform.
- Guía de creación segura de cuenta AWS (docs/aws-account-setup.md).
- Sin recursos AWS creados. Sin código de aplicación todavía.
