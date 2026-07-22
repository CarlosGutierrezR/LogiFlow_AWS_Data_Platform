# Versiones fijadas de Terraform y proveedores.
# Nota: verificar la última versión estable del proveedor AWS en
# https://registry.terraform.io/providers/hashicorp/aws antes del primer init;
# la restricción "~> 6.0" acepta 6.x pero no un futuro 7.x con breaking changes.

terraform {
  required_version = ">= 1.9.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  # Backend local en esta fase. Se migrará a backend S3 + bloqueo
  # cuando exista el bucket de estado (fase de almacenamiento).
  backend "local" {}
}
