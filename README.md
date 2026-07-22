# LogiFlow AWS Data Platform

Plataforma end-to-end de ingeniería de datos en AWS que simula el ciclo completo de un proyecto empresarial: ingestión batch, almacenamiento por capas en S3, catalogación, ETL con PySpark, calidad de datos, orquestación, gobierno, analítica con Athena, infraestructura como código con Terraform y CI/CD con GitHub Actions.

**Dominio de negocio:** logística y envíos (pedidos, envíos, rutas, almacenes, estados de entrega).

**Estado actual:** Fase 0 — fundación del repositorio. Sin recursos desplegados en AWS.

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
├── docs/          # Documentación técnica y de negocio
├── (fases futuras: terraform/, src/, tests/, data/, .github/)
└── README.md
```

## Documentación

| Documento | Contenido |
|---|---|
| [docs/project-charter.md](docs/project-charter.md) | Objetivo, alcance y criterios de éxito |
| [docs/architecture.md](docs/architecture.md) | Arquitectura y componentes |
| [docs/decisions.md](docs/decisions.md) | Decisiones arquitectónicas (ADR) |
| [docs/roadmap.md](docs/roadmap.md) | Fases y estado |
| [docs/security.md](docs/security.md) | Seguridad y gestión de credenciales |
| [docs/cost-control.md](docs/cost-control.md) | Control de costes |
| [docs/aws-account-setup.md](docs/aws-account-setup.md) | Guía de creación segura de la cuenta AWS |

## Autor

Carlos Alberto Gutiérrez Rondón — Data Engineer
[LinkedIn](https://www.linkedin.com/in/carlosgutierrez-rondon) · [GitHub](https://github.com/CarlosGutierrezR)
