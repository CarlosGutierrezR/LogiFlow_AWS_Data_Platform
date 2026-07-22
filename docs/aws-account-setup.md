# Guía: creación segura de la cuenta AWS (Fase 1)

Objetivo: cuenta AWS personal lista para desplegar con Terraform, sin usar root en el día a día y con control de costes activo ANTES de crear recursos.

> Nota: los pasos de consola pueden variar ligeramente con el tiempo. Referencia oficial: https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-creating.html

## 1. Crear la cuenta

- [ ] Registrarse en https://aws.amazon.com con un email dedicado y contraseña fuerte (gestor de contraseñas).
- [ ] Requiere tarjeta de crédito/débito y verificación telefónica.
- [ ] Plan de soporte: Basic (gratuito).

## 2. Asegurar el usuario root

- [ ] Activar MFA en root (app de autenticación o passkey).
- [ ] No crear claves de acceso (access keys) para root.
- [ ] Guardar las credenciales root en el gestor de contraseñas; no volver a usarlas salvo necesidad administrativa.

## 3. Control de costes (antes que cualquier recurso)

- [ ] AWS Budgets: presupuesto mensual con alertas por email a chgut31@gmail.com (umbral bajo, p. ej. 5–10 USD, con avisos al 50/80/100 %).
- [ ] Activar alertas de facturación (Billing preferences → alerts).
- [ ] Verificar condiciones de free tier vigentes en https://aws.amazon.com/free (no asumir las de esta guía).

## 4. Identidad de trabajo (no root)

Opción recomendada — IAM Identity Center (credenciales temporales):
- [ ] Habilitar IAM Identity Center en la región elegida.
- [ ] Crear usuario `carlos` con MFA.
- [ ] Asignar permission set (AdministratorAccess al inicio; se restringirá cuando el proyecto esté estable — registrar como deuda de seguridad).
- [ ] Configurar CLI: `aws configure sso` → perfil `logiflow-dev`.
- [ ] Login diario: `aws sso login --profile logiflow-dev`.

Alternativa si Identity Center resulta un bloqueo: usuario IAM con MFA y claves de acceso locales (nunca versionadas), documentando el motivo en decisions.md.

## 5. Verificación de región (ADR-002)

Con la cuenta activa, comprobar desde la consola en eu-south-2 que están disponibles: Glue (incl. Data Quality), Athena, Step Functions, EventBridge Scheduler. Si Glue Data Quality no aparece en eu-south-2 → usar eu-west-1 y actualizar ADR-002.

## 6. Evidencia de finalización de Fase 1

- Salida de `aws sts get-caller-identity --profile logiflow-dev` (ocultando el Account ID al documentar públicamente).
- Captura o descripción del presupuesto creado.
- Resultado de la verificación de región.
