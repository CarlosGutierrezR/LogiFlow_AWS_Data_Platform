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

## Ejecución orquestada (Fase 9 — recomendada)

Un solo disparo ejecuta las 3 etapas en orden con esperas y reintentos:

```powershell
$SM = terraform output -raw sfn_pipeline_arn
$exec = aws stepfunctions start-execution --state-machine-arn $SM --input '{\"ingest_date\":\"YYYY-MM-DD\"}' --query executionArn --output text
aws stepfunctions describe-execution --execution-arn $exec --query status --output text
```

Diagnóstico de fallos: `aws stepfunctions get-execution-history --execution-arn $exec --reverse-order --max-items 6`.

Incidencia conocida: con la integración `.sync`, la salida del job reemplaza el input del estado; para conservar `$.ingest_date` en toda la cadena cada tarea usa `ResultPath` (corregido 2026-07-23).

## Destrucción segura de toda la infraestructura (Fase 12)

⚠️ **Elimina todos los recursos AWS del proyecto.** Úsalo para no gastar cuando el proyecto no esté en uso; recréalo cuando lo necesites con `terraform apply`.

Los buckets tienen `force_destroy = false` (protección intencionada): `terraform destroy` **fallará** si contienen objetos. Hay que vaciarlos antes. Los buckets con versionado (`raw`, `curated`) requieren borrar también las versiones y los *delete markers*.

### Paso 1 — Vaciar todos los buckets (PowerShell, sesión `aws login` activa)

```powershell
$acc = (aws sts get-caller-identity --query Account --output text)
$buckets = @(
  "logiflow-dev-landing-$acc", "logiflow-dev-raw-$acc",
  "logiflow-dev-processed-$acc", "logiflow-dev-curated-$acc",
  "logiflow-dev-quarantine-$acc", "logiflow-dev-artifacts-$acc",
  "logiflow-dev-athena-results-$acc"
)
foreach ($b in $buckets) {
  Write-Host "Vaciando $b ..."
  aws s3 rm "s3://$b" --recursive
  # Purga de versiones y delete markers (buckets con versionado)
  $vers = aws s3api list-object-versions --bucket $b `
    --query "Versions[].{Key:Key,VersionId:VersionId}" --output json | ConvertFrom-Json
  foreach ($o in $vers) { aws s3api delete-object --bucket $b --key $o.Key --version-id $o.VersionId | Out-Null }
  $marks = aws s3api list-object-versions --bucket $b `
    --query "DeleteMarkers[].{Key:Key,VersionId:VersionId}" --output json | ConvertFrom-Json
  foreach ($o in $marks) { aws s3api delete-object --bucket $b --key $o.Key --version-id $o.VersionId | Out-Null }
}
```

### Paso 2 — Destruir la infraestructura

```powershell
cd D:\LogiFlow_AWS_Data_Platform\terraform
terraform destroy    # revisar el plan; confirmar con 'yes'
```

Debe terminar con `Destroy complete! Resources: N destroyed.`

### Paso 3 — Verificar que no queda nada facturable

```powershell
aws s3 ls | Select-String logiflow          # sin resultados
aws glue get-jobs --query "Jobs[?starts_with(Name, 'logiflow')].Name"   # []
aws stepfunctions list-state-machines --query "stateMachines[?starts_with(name,'logiflow')].name"  # []
```

Lo que **no** elimina `terraform destroy` (y no genera coste): el presupuesto `logiflow-zero-spend-budget`, el usuario IAM `carlos-admin` y el estado local de Terraform (`terraform.tfstate`). El estado se conserva a propósito para poder recrear la plataforma.

Pendiente de fases futuras: reprocesamiento desde cuarentena, rotación de credenciales.
