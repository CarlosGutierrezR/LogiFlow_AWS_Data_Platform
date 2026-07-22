# Guía: creación segura de la cuenta AWS (Fase 1)

Objetivo: cuenta AWS personal lista para desplegar con Terraform, sin usar root en el día a día y con control de costes activo ANTES de crear recursos.

> Nota: los pasos de consola pueden variar ligeramente con el tiempo. Referencia oficial: https://docs.aws.amazon.com/accounts/latest/reference/manage-acct-creating.html

## 1. Crear la cuenta

- [x] Registrarse en https://aws.amazon.com con un email dedicado y contraseña fuerte (gestor de contraseñas).
- [x] Requiere tarjeta de crédito/débito y verificación telefónica.
- [x] Plan de soporte: Basic (gratuito).

## 2. Asegurar el usuario root

- [ ] Activar MFA en root (app de autenticación o passkey).
- [x] No crear claves de acceso (access keys) para root.
- [x] Guardar las credenciales root en el gestor de contraseñas; no volver a usarlas salvo necesidad administrativa.

## 3. Control de costes (antes que cualquier recurso)

- [x] AWS Budgets: presupuesto `logiflow-zero-spend-budget` (plantilla de gasto cero, alerta a chgut31@gmail.com si el gasto supera 0,01 USD). Creado 2026-07-22 vía consola.
- [ ] Activar alertas de facturación (Billing preferences → alerts).
- [ ] Verificar condiciones de free tier vigentes en https://aws.amazon.com/free (no asumir las de esta guía).

## 4. Identidad de trabajo (no root)

> ACTUALIZACIÓN 2026-07-22 (ADR-006): se descartó Identity Center para conservar el plan gratuito (crear Organizations convierte la cuenta a pago por uso y caducan los créditos). Creado usuario IAM `carlos-admin` con AdministratorAccess, contraseña autogenerada y cambio obligatorio al primer inicio. URL de consola: https://503782778600.signin.aws.amazon.com/console — pendiente: primer login de Carlos, contraseña definitiva y MFA del usuario. La sección siguiente queda como referencia histórica.

Opción recomendada — IAM Identity Center (credenciales temporales):
- [ ] Habilitar IAM Identity Center en la región elegida.
- [ ] Crear usuario `carlos` con MFA.
- [ ] Asignar permission set (AdministratorAccess al inicio; se restringirá cuando el proyecto esté estable — registrar como deuda de seguridad).
- [ ] Configurar CLI: `aws configure sso` → perfil `logiflow-dev`.
- [ ] Login diario: `aws sso login --profile logiflow-dev`.

Alternativa si Identity Center resulta un bloqueo: usuario IAM con MFA y claves de acceso locales (nunca versionadas), documentando el motivo en decisions.md.

## 4b. Evidencia CLI (2026-07-22)

- AWS CLI 2.36.5 instalada en Windows 11 (instalador oficial MSI usuario).
- `aws configure set region eu-south-2` aplicado.
- `aws login` completado vía navegador con la sesión de carlos-admin (sin access keys).
- `aws sts get-caller-identity` → `arn:aws:iam::<ACCOUNT_ID>:user/carlos-admin` ✔
- PENDIENTE de seguridad: MFA del usuario root y rotación de su contraseña (expuesta el 2026-07-22).

## 5. Verificación de región (ADR-002)

Con la cuenta activa, comprobar desde la consola en eu-south-2 que están disponibles: Glue (incl. Data Quality), Athena, Step Functions, EventBridge Scheduler. Si Glue Data Quality no aparece en eu-south-2 → usar eu-west-1 y actualizar ADR-002.

## 6. Evidencia de finalización de Fase 1

- Salida de `aws sts get-caller-identity --profile logiflow-dev` (ocultando el Account ID al documentar públicamente).
- Captura o descripción del presupuesto creado.
- Resultado de la verificación de región.
