# Registro de decisiones arquitectónicas (ADR)

Formato: contexto → decisión → estado → consecuencias.
Estados: `propuesta` | `aprobada` | `supuesto pendiente de verificación` | `reemplazada`.

---

## ADR-001 — Dominio de negocio: logística y envíos

- **Fecha:** 2026-07-22
- **Estado:** aprobada
- **Contexto:** el proyecto necesita un dominio realista que defina datos sintéticos, contratos de datos y KPIs.
- **Decisión:** simular una empresa de logística (pedidos, envíos, rutas, almacenes, estados de entrega). Coherente con el nombre LogiFlow y diferenciador frente a los proyectos previos del autor (ventas, finanzas).
- **Consecuencias:** los contratos de datos y el modelo dimensional (fase de diseño) se definirán sobre entidades logísticas.

## ADR-002 — Región AWS: preferencia eu-south-2, verificación pendiente

- **Fecha:** 2026-07-22
- **Estado:** supuesto pendiente de verificación
- **Contexto:** el usuario prefiere eu-south-2 (España) por cercanía. Verificado en documentación oficial: AWS Glue está disponible en eu-south-2 desde abril de 2023 (AWS What's New, 2023-04-05). NO confirmado: disponibilidad de Glue Data Quality en eu-south-2. Confirmado además que las sesiones interactivas de Glue no están disponibles en eu-south-2 (docs de AWS Glue, consultado 2026-07-22).
- **Decisión:** la región será variable de Terraform (`var.aws_region`). Antes del primer despliegue de Glue se verificará Glue Data Quality en eu-south-2 desde la cuenta (consola/CLI). Si no está disponible, fallback aprobado: eu-west-1 (Irlanda).
- **Consecuencias:** ningún nombre de recurso debe codificar la región de forma rígida.

## ADR-003 — Control de versiones: Git local primero

- **Fecha:** 2026-07-22
- **Estado:** aprobada
- **Contexto:** el usuario prefiere consolidar el núcleo antes de publicar en GitHub.
- **Decisión:** repositorio Git local desde la Fase 0; publicación en github.com/CarlosGutierrezR cuando el núcleo batch esté desplegado y probado. CI/CD (GitHub Actions) se activará al publicar.
- **Consecuencias:** la revisión anti-secretos se aplica desde el primer commit local, no solo al publicar.

## ADR-004 — Cuenta AWS nueva con configuración segura previa

- **Fecha:** 2026-07-22
- **Estado:** aprobada
- **Contexto:** no existe cuenta AWS. Es prerrequisito de cualquier despliegue.
- **Decisión:** crear cuenta personal siguiendo docs/aws-account-setup.md: MFA en root, root solo para lo imprescindible, identidad de trabajo con IAM Identity Center (o usuario IAM con MFA como alternativa), AWS Budgets con alertas antes de crear cualquier recurso.
- **Consecuencias:** la Fase 1 (bootstrap de Terraform) queda bloqueada hasta completar esta configuración con evidencia.

## ADR-005 — Autenticación CLI con `aws login` y Agent Toolkit for AWS

- **Fecha:** 2026-07-22
- **Estado:** aprobada
- **Contexto:** AWS publicó `aws login` (nov. 2025, CLI ≥ 2.32.0): credenciales temporales vinculadas a la sesión de consola del navegador, sin access keys permanentes. El Agent Toolkit for AWS (jun. 2026, `aws configure agent-toolkit`, servicio solo en us-east-1) configura MCP server y skills para agentes de código.
- **Decisión:** usar `aws login` como método de autenticación de la CLI (sustituye el flujo `aws configure sso` previsto), siempre iniciando sesión con el usuario de trabajo de Identity Center, nunca con root. Instalar el Agent Toolkit como herramienta de desarrollo. El archivo de reglas del toolkit (paso 7 del setup) se revisará antes de incorporarlo a CLAUDE.md por posible conflicto con las reglas propias del proyecto.
- **Consecuencias:** sin claves de acceso de larga duración en la máquina local; la región del toolkit (us-east-1) es independiente de la región del proyecto (ADR-002).
- **Referencias:** https://aws.amazon.com/blogs/security/simplified-developer-access-to-aws-with-aws-login · https://aws.amazon.com/about-aws/whats-new/2026/06/aws-cli-agent-toolkit/

## ADR-006 — Usuario IAM clásico en lugar de IAM Identity Center

- **Fecha:** 2026-07-22
- **Estado:** aprobada (decisión de Carlos)
- **Contexto:** al intentar habilitar IAM Identity Center, la consola advirtió que crear AWS Organizations convierte automáticamente la cuenta de plan gratuito a pago por uso y **los créditos del nivel gratuito caducan inmediatamente**. La cuenta está en el plan gratuito de AWS (modelo de cuenta con créditos y límite de gasto), valioso para un proyecto de portafolio.
- **Decisión:** crear el usuario IAM `carlos-admin` (consola + `AdministratorAccess` + `IAMUserChangePassword`, contraseña autogenerada con restablecimiento obligatorio) y posponer Identity Center. `aws login` funciona igualmente con usuarios IAM (SignInLocalDevelopmentAccess), así que ADR-005 no cambia.
- **Consecuencias:** se conservan plan gratuito y créditos. Restricción de mínimo privilegio pendiente: `AdministratorAccess` es temporal de arranque; se sustituirá por políticas acotadas cuando la infraestructura esté estable (deuda de seguridad registrada). Migración a Identity Center posible más adelante con ADR propio.
- **Evidencia:** aviso de la consola en pantalla de habilitación de Identity Center (2026-07-22); confirmación "La persona se ha creado correctamente".
