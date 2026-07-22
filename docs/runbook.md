# Runbook operativo

## Despliegue y destrucción (Fase 3 — S3)

Requisitos: sesión CLI activa (`aws login` como carlos-admin), Terraform >= 1.9.

```powershell
cd D:\LogiFlow_AWS_Data_Platform\terraform
terraform plan     # revisar SIEMPRE antes de aplicar
terraform apply    # confirmar con 'yes'
```

Verificación: `aws s3 ls | Select-String logiflow` debe listar 5 buckets.

### Destrucción controlada

ADVERTENCIA: elimina los 5 buckets del data lake. Si contienen datos, `destroy` fallará salvo vaciado previo (los buckets con versionado —raw, curated— requieren borrar también versiones).

```powershell
cd D:\LogiFlow_AWS_Data_Platform\terraform
terraform destroy  # confirmar con 'yes'
```

### Estado de Terraform

Backend local: `terraform/terraform.tfstate` (NO versionado, no borrar). Migración a backend S3 prevista en fase posterior.

## Ejecución del ETL (Fase 6 — hasta que exista orquestación)

Orden obligatorio por fecha: `landing-to-raw` → esperar SUCCEEDED → `raw-to-processed`.

```powershell
'{"JobName":"logiflow-dev-landing-to-raw","Arguments":{"--date":"YYYY-MM-DD"}}' | Out-File -Encoding ascii run.json
aws glue start-job-run --cli-input-json file://run.json
aws glue get-job-runs --job-name logiflow-dev-landing-to-raw --query "JobRuns[0].{estado:JobRunState,error:ErrorMessage}"
```

### Incidencias conocidas y su tratamiento

| Síntoma | Causa | Acción |
|---|---|---|
| `FAILED` con `SystemExit: 0` | sys.exit() en el script (Glue lo trata como fallo) | No usar sys.exit en entry points (corregido 2026-07-22) |
| `PATH_NOT_FOUND` en raw-to-processed | Se lanzó antes de terminar landing-to-raw | Respetar el orden; se automatizará con Step Functions |
| `ConcurrentRunsExceededException` | Run recién terminado aún cuenta para el límite | Esperar ~30 s y reintentar |
| Job "SUCCEEDED" tras leer datos parciales | Carrera lectura/escritura entre jobs | Relanzar raw-to-processed (idempotente) |

Pendiente de fases futuras: reprocesamiento desde cuarentena, rotación de credenciales.
