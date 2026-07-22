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

Pendiente de fases futuras: respuesta a fallos del pipeline, reprocesamiento desde cuarentena, rotación de credenciales.
