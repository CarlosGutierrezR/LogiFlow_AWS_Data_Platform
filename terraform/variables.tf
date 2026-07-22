# Variables globales del proyecto.

variable "aws_region" {
  description = "Región AWS del proyecto (ADR-002: eu-west-1)."
  type        = string
  default     = "eu-west-1"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "La región debe tener formato AWS válido, p. ej. eu-west-1."
  }
}

variable "project_name" {
  description = "Nombre corto del proyecto; se usa como prefijo de recursos."
  type        = string
  default     = "logiflow"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,20}$", var.project_name))
    error_message = "Solo minúsculas, números y guiones (3-21 caracteres, empieza por letra)."
  }
}

variable "environment" {
  description = "Ambiente de despliegue."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Ambiente permitido: dev o prod."
  }
}

variable "owner" {
  description = "Propietario de los recursos (para tags y trazabilidad)."
  type        = string
  default     = "carlos-gutierrez"
}
