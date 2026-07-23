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
| 2026-07-22 | 1 | ninguno (solo AWS Budgets, sin coste) | 0 | Presupuesto `logiflow-zero-spend-budget` creado; confirmación en consola |
| 2026-07-22 | 3 | 5 buckets S3 vacíos → con ~187 KB | ~0 (verificar en Billing en 24-48 h) | Almacenamiento insignificante; PUTs de 18 objetos |
| 2026-07-22 | 5 | Glue: 3 ejecuciones de crawler (1 en vacío) | céntimos estimados — PENDIENTE verificar importe real en Billing | Primer servicio facturable del proyecto; crawler sin schedule |
| 2026-07-23 | 6-11 | Glue jobs (múltiples runs), crawlers, evaluación DQ, Athena, Step Functions, SNS, CloudWatch | **0 cargado** (cubierto por créditos del plan gratuito) | Consola de Facturación: "No se cobrará nada a su cuenta del plan gratuito. Los créditos cubren los costos del plan gratuito." Monitor de anomalías: *None detected* |

## Observación de cierre (Fase 12, 2026-07-23)

La cuenta está en el **plan gratuito de AWS con créditos**. La página de Administración de facturación indica explícitamente que *no se cobrará nada mientras los créditos cubran los costes del plan gratuito*, y el detector de anomalías no reporta nada. El desglose por servicio muestra "Datos no disponibles" por el desfase habitual de 24-48 h en la consolidación de costes.

No se registra una cifra exacta por servicio porque AWS aún no la ha consolidado en el momento del cierre; debe verificarse en Cost Explorer (`https://console.aws.amazon.com/cost-management`) pasadas 24-48 h. **No se anotan importes inventados.**

Para evitar cualquier gasto cuando el proyecto no esté en uso, la infraestructura es **totalmente destruible** con `terraform destroy` (ver procedimiento en `docs/runbook.md`).
