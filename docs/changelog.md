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

## 2026-07-22 — Fase 0: fundación del repositorio

- Estructura inicial del proyecto y documentación base (charter, arquitectura, roadmap, seguridad, costes).
- ADR-001 a ADR-004 registradas en decisions.md.
- `.gitignore` y `.gitattributes` con protección de secretos y estado de Terraform.
- Guía de creación segura de cuenta AWS (docs/aws-account-setup.md).
- Sin recursos AWS creados. Sin código de aplicación todavía.
