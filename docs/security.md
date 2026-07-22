# Seguridad

## Reglas no negociables

1. Ningún secreto (claves, tokens, contraseñas, ARN sensibles) en código, Terraform, tfvars, logs o documentación. `.gitignore` bloquea `.env` y `*.tfvars`; se versionan solo `*.example`.
2. La cuenta root solo se usa para: crear la cuenta, activar MFA, crear la identidad de trabajo y configurar facturación. Nunca para trabajo diario.
3. MFA obligatorio en root y en la identidad de trabajo.
4. Preferencia por credenciales temporales (IAM Identity Center / `aws sso login`) frente a claves de acceso permanentes.
5. Mínimo privilegio: cada rol (Glue, Step Functions, etc.) tendrá una política acotada a sus recursos; nada de `*:*`.
6. S3: Block Public Access activado a nivel de cuenta y de bucket; cifrado en reposo en todos los buckets.
7. Secrets Manager para cualquier secreto de aplicación (cuando exista); nunca variables incrustadas.
8. Revisión anti-secretos antes de cada commit (se automatizará en CI en la fase 11).

## Estado actual

Fase 0: no existen todavía cuenta, credenciales ni recursos. Este documento se ampliará por fase con los roles y políticas concretos que se creen.
