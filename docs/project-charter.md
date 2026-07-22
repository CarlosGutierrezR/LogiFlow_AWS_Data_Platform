# Project Charter — LogiFlow AWS Data Platform

## Objetivo

Construir una plataforma de datos en AWS, reproducible y documentada, que demuestre competencias de Data Engineer en un escenario empresarial realista de logística. El proyecto es la pieza AWS del portafolio de Carlos Gutiérrez (complementa Veritas Fex en GCP).

## Problema de negocio simulado

LogiFlow es una empresa ficticia de logística que recibe diariamente ficheros de pedidos y envíos desde sistemas operacionales. Necesita centralizarlos, garantizar su calidad y ofrecer indicadores fiables (tiempos de entrega, incidencias, rendimiento por ruta y almacén) a los equipos de operaciones.

## Alcance del núcleo (fases 0–N del roadmap)

- Generación de datos sintéticos de logística (CSV/JSON).
- Ingestión batch a S3 con capas landing/raw/processed/curated.
- Glue Data Catalog, crawlers y ETL con PySpark.
- Validación de calidad (Glue Data Quality) y zona de cuarentena.
- Orquestación con Step Functions + EventBridge Scheduler.
- Consulta analítica con Athena y modelo dimensional.
- Observabilidad: CloudWatch, SNS, logging estructurado.
- Terraform, GitHub Actions, pruebas y documentación completa.

## Fuera de alcance del núcleo

Streaming (Kinesis), Lake Formation, Redshift, QuickSight, RDS/DMS e Iceberg: solo como extensiones posteriores, cada una con justificación y control de costes.

## Criterios de éxito

1. Infraestructura 100 % reproducible con `terraform apply` / destruible con `terraform destroy`.
2. Pipeline batch ejecutado end-to-end con evidencia real (logs, capturas, salidas de Athena).
3. Sin secretos en el repositorio; mínimo privilegio en IAM.
4. Coste mensual controlado con presupuesto y alarmas (objetivo: casi cero con datos sintéticos y serverless).
5. Documentación suficiente para que un tercero reproduzca el proyecto.

## Restricciones

- Cuenta AWS personal nueva (free tier), datos exclusivamente sintéticos.
- Presupuesto mínimo; recursos efímeros y serverless.
- Trabajo por fases con evidencia antes de avanzar.
