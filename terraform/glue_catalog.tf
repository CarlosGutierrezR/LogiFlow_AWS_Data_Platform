# Fase 5: catalogación de la capa landing con Glue Data Catalog.
# Un único crawler bajo demanda (sin schedule) para controlar costes:
# cada ejecución se factura por tiempo de DPU (ver docs/cost-control.md).

resource "aws_glue_catalog_database" "landing" {
  name        = "${replace(local.name_prefix, "-", "_")}_landing"
  description = "Esquemas inferidos de la capa landing de LogiFlow (fuente: crawler)"
}

# Rol del crawler: confianza solo para el servicio Glue.
resource "aws_iam_role" "glue_crawler_landing" {
  name = "${local.name_prefix}-glue-crawler-landing"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "glue.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# Permisos estándar del servicio Glue (catálogo + logs de CloudWatch).
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_crawler_landing.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Acceso S3 de mínimo privilegio: solo lectura y solo el bucket landing.
resource "aws_iam_role_policy" "glue_crawler_s3_read" {
  name = "s3-read-landing-only"
  role = aws_iam_role.glue_crawler_landing.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListLandingBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.data_layer["landing"].arn
      },
      {
        Sid      = "ReadLandingObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.data_layer["landing"].arn}/*"
      }
    ]
  })
}

resource "aws_glue_crawler" "landing" {
  name          = "${local.name_prefix}-landing-crawler"
  role          = aws_iam_role.glue_crawler_landing.arn
  database_name = aws_glue_catalog_database.landing.name
  description   = "Crawler bajo demanda de las 5 entidades de landing"

  # Un target por entidad; _manifests queda fuera al no estar en estos prefijos.
  dynamic "s3_target" {
    for_each = toset([
      "warehouses",
      "routes",
      "orders",
      "shipments",
      "delivery_events",
    ])
    content {
      path = "s3://${aws_s3_bucket.data_layer["landing"].bucket}/${s3_target.value}/"
    }
  }

  # Sin schedule: ejecución manual (aws glue start-crawler) para evitar
  # cargos recurrentes durante el desarrollo.

  tags = {
    layer = "landing"
  }
}

output "glue_landing_database" {
  description = "Base de datos del catálogo para landing."
  value       = aws_glue_catalog_database.landing.name
}

output "glue_landing_crawler" {
  description = "Nombre del crawler de landing (ejecutar bajo demanda)."
  value       = aws_glue_crawler.landing.name
}
