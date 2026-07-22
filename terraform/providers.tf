# Proveedor AWS. Credenciales: NUNCA en código; las toma del entorno
# (aws login / perfil por defecto de la CLI).

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}
