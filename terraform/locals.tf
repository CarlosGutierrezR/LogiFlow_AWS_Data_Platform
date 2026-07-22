# Valores derivados y tags comunes (aplicados a todo recurso vía default_tags).

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    project     = var.project_name
    environment = var.environment
    owner       = var.owner
    purpose     = "data-engineering-portfolio"
    managed_by  = "terraform"
  }
}
