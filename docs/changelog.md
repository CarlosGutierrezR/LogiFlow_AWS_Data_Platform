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

## 2026-07-22 — Fase 0: fundación del repositorio

- Estructura inicial del proyecto y documentación base (charter, arquitectura, roadmap, seguridad, costes).
- ADR-001 a ADR-004 registradas en decisions.md.
- `.gitignore` y `.gitattributes` con protección de secretos y estado de Terraform.
- Guía de creación segura de cuenta AWS (docs/aws-account-setup.md).
- Sin recursos AWS creados. Sin código de aplicación todavía.
