# Control de costes

## Principios

- Solo servicios serverless de pago por uso en el núcleo: S3, Glue, Athena, Step Functions, EventBridge, CloudWatch, SNS.
- Volúmenes pequeños y datos sintéticos (MBs, no GBs).
- Ningún recurso de coste fijo permanente (sin NAT Gateway, RDS, Redshift, Kinesis ni QuickSight en el núcleo).
- Todo recurso llevará tags: `project=logiflow`, `environment`, `owner`, `purpose`.
- Cada fase documentará qué servicios pueden generar cargos ANTES de desplegar.
- `terraform destroy` verificado por fase; el proyecto completo debe poder eliminarse.

## Prerrequisito antes de crear cualquier recurso (Fase 1)

1. Presupuesto mensual en AWS Budgets con alertas por email (p. ej. al 50 %, 80 % y 100 % de un umbral bajo tipo 5–10 USD; el umbral lo decide Carlos).
2. Alerta de facturación en CloudWatch.
3. Revisión de precios de Glue, Athena y S3 en la calculadora oficial (https://calculator.aws) — no se usarán estimaciones inventadas en esta documentación.

## Registro de costes reales

| Fecha | Fase | Servicios activos | Coste observado | Fuente |
|---|---|---|---|---|
| — | — | ninguno | 0 (sin cuenta aún) | — |
