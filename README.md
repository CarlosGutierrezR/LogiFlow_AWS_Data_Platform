# LogiFlow AWS Data Platform

![CI](https://github.com/CarlosGutierrezR/LogiFlow_AWS_Data_Platform/actions/workflows/ci.yml/badge.svg)

Plataforma end-to-end de ingeniería de datos en AWS que simula el ciclo completo de un proyecto empresarial: ingestión batch, almacenamiento por capas en S3, catalogación, ETL con PySpark, calidad de datos, orquestación, gobierno, analítica con Athena, infraestructura como código con Terraform y CI/CD con GitHub Actions.

**Dominio de negocio:** logística y envíos (pedidos, envíos, rutas, almacenes, estados de entrega).

**Estado:** núcleo batch desplegado y ejecutado en AWS (eu-west-1). Pipeline orquestado con Step Functions, calidad con Glue Data Quality y KPIs consultables en Athena. Ver [docs/roadmap.md](docs/roadmap.md) para el detalle por fases.

## Capacidades demostradas

- **Ingestión idempotente** de datos sintéticos de logística a S3 (reejecución sin duplicados).
- **Data lake por capas**: landing → raw → processed → curated, más zona de cuarentena.
- **ETL con PySpark** (Glue 5.0): esquemas explícitos del contrato, deduplicación, validaciones, tipado, linaje y reconciliación estricta de conteos.
- **Doble control de calidad**: validación propia en el ETL (errores a cuarentena con motivo) + Glue Data Quality gestionado (evaluado con Score 1.0).
- **Modelo dimensional** (hechos de envíos + dimensiones) y **KPIs de negocio en Athena** (rendimiento por transportista, incidencias por almacén, estado por servicio).
- **Orquestación** con Step Functions (`.sync`, reintentos, captura de fallos).
- **Observabilidad**: alarmas CloudWatch + notificaciones SNS por email.
- **IaC completa** con Terraform e **IAM de mínimo privilegio** por capa.
- **CI** con GitHub Actions: ruff (lint + format), pytest y `terraform validate`.

## Stack

Python · PySpark · SQL · AWS (S3, Glue, Glue Data Quality, Athena, Step Functions, CloudWatch, SNS, IAM) · Terraform · GitHub Actions · pytest · ruff

## Arquitectura objetivo (núcleo batch)

```
Fuentes (CSV/JSON sintéticos)
        │
        ▼
S3 landing ──► S3 raw ──► S3 processed ──► S3 curated
        │           (Glue ETL / PySpark + Glue Data Quality)
        ▼
Glue Data Catalog ──► Athena (consulta y modelado analítico)

Orquestación: Step Functions + EventBridge Scheduler
Observabilidad: CloudWatch + SNS
Seguridad: IAM mínimo privilegio, cifrado, S3 public access block
IaC: Terraform | CI/CD: GitHub Actions
```

Extensiones previstas (solo tras completar y probar el núcleo batch): Kinesis, Lambda, Lake Formation, Redshift Serverless, QuickSight, RDS/DMS, Apache Iceberg.

## Estructura del repositorio

```
.
├── .github/workflows/   # CI (ruff, pytest, terraform validate)
├── docs/                # Documentación técnica y de negocio (charter, ADRs, runbook…)
├── ops/                 # Entry points de Glue y consultas Athena (KPIs)
├── src/                 # Código Python
│   ├── data_generator/  #   generador de datos sintéticos con errores controlados
│   ├── ingestion/       #   subida idempotente a S3
│   └── etl/             #   jobs PySpark (landing→raw→processed→curated) + esquemas
├── terraform/           # Infraestructura como código (S3, Glue, Athena, Step Functions, SNS…)
├── tests/               # pytest (unitarios + integración PySpark)
└── README.md
```

## Cómo ejecutar

Pipeline completo orquestado (un disparo ejecuta las 3 etapas en orden):

```powershell
$SM = terraform -chdir=terraform output -raw sfn_pipeline_arn
aws stepfunctions start-execution --state-machine-arn $SM --input '{"ingest_date":"2026-07-23"}'
```

Detalle de despliegue, ejecución e incidencias conocidas en [docs/runbook.md](docs/runbook.md).

## Documentación

| Documento | Contenido |
|---|---|
| [docs/project-charter.md](docs/project-charter.md) | Objetivo, alcance y criterios de éxito |
| [docs/architecture.md](docs/architecture.md) | Arquitectura y componentes |
| [docs/decisions.md](docs/decisions.md) | Decisiones arquitectónicas (ADR) |
| [docs/roadmap.md](docs/roadmap.md) | Fases y estado |
| [docs/security.md](docs/security.md) | Seguridad y gestión de credenciales |
| [docs/cost-control.md](docs/cost-control.md) | Control de costes |
| [docs/runbook.md](docs/runbook.md) | Ejecución, despliegue e incidencias resueltas |
| [docs/testing.md](docs/testing.md) | Estrategia y estado de las pruebas |
| [docs/changelog.md](docs/changelog.md) | Registro cronológico con evidencias |
| [docs/aws-account-setup.md](docs/aws-account-setup.md) | Guía de creación segura de la cuenta AWS |

## Autor

Carlos Alberto Gutiérrez Rondón — Data Engineer
[LinkedIn](https://www.linkedin.com/in/carlosgutierrez-rondon) · [GitHub](https://github.com/CarlosGutierrezR)
