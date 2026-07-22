# Fase 7: catalogación de processed + reglas de Glue Data Quality.
# Las reglas DQ actúan como verificación gestionada SOBRE la capa ya limpiada
# por el ETL: deben pasar al 100 % (si fallan, el ETL tiene un bug).
#
# Despliegue en dos pasos (los rulesets referencian tablas que crea el crawler):
#   1) terraform apply                       -> base de datos + crawler
#   2) ejecutar el crawler y, al terminar:
#      terraform apply -var enable_dq_rulesets=true

variable "enable_dq_rulesets" {
  description = "Crear los rulesets DQ (requiere que el crawler de processed haya catalogado las tablas)."
  type        = bool
  default     = false
}

resource "aws_glue_catalog_database" "processed" {
  name        = "${replace(local.name_prefix, "-", "_")}_processed"
  description = "Tablas de la capa processed (tipadas según data-contracts v1.0)"
}

resource "aws_iam_role" "glue_crawler_processed" {
  name = "${local.name_prefix}-glue-crawler-processed"

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

resource "aws_iam_role_policy_attachment" "glue_service_processed" {
  role       = aws_iam_role.glue_crawler_processed.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_crawler_processed_s3" {
  name = "s3-read-processed-only"
  role = aws_iam_role.glue_crawler_processed.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListProcessedBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.data_layer["processed"].arn
      },
      {
        Sid      = "ReadProcessedObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.data_layer["processed"].arn}/*"
      }
    ]
  })
}

resource "aws_glue_crawler" "processed" {
  name          = "${local.name_prefix}-processed-crawler"
  role          = aws_iam_role.glue_crawler_processed.arn
  database_name = aws_glue_catalog_database.processed.name
  description   = "Crawler bajo demanda de la capa processed (Parquet tipado)"

  dynamic "s3_target" {
    for_each = toset([
      "warehouses",
      "routes",
      "orders",
      "shipments",
      "delivery_events",
    ])
    content {
      path = "s3://${aws_s3_bucket.data_layer["processed"].bucket}/${s3_target.value}/"
    }
  }

  tags = {
    layer = "processed"
  }
}

# ---------- Rulesets de Glue Data Quality (paso 2) ----------

resource "aws_glue_data_quality_ruleset" "orders" {
  count = var.enable_dq_rulesets ? 1 : 0

  name        = "${local.name_prefix}-orders-dq"
  description = "Verificación gestionada sobre processed.orders (debe pasar al 100%)"

  ruleset = <<-EOT
    Rules = [
      IsComplete "order_id",
      IsUnique "order_id",
      IsComplete "customer_id",
      IsComplete "order_ts",
      ColumnValues "service_level" in ["standard", "express", "same_day"],
      ColumnValues "total_weight_kg" > 0,
      ColumnValues "num_packages" > 0
    ]
  EOT

  target_table {
    database_name = aws_glue_catalog_database.processed.name
    table_name    = "orders"
  }
}

resource "aws_glue_data_quality_ruleset" "shipments" {
  count = var.enable_dq_rulesets ? 1 : 0

  name        = "${local.name_prefix}-shipments-dq"
  description = "Verificación gestionada sobre processed.shipments (debe pasar al 100%)"

  ruleset = <<-EOT
    Rules = [
      IsComplete "shipment_id",
      IsUnique "shipment_id",
      IsComplete "order_id",
      IsComplete "route_id",
      ColumnValues "status" in ["created", "in_transit", "delivered", "delayed", "lost", "returned"],
      ColumnValues "cost_eur" > 0
    ]
  EOT

  target_table {
    database_name = aws_glue_catalog_database.processed.name
    table_name    = "shipments"
  }
}

output "glue_processed_database" {
  value = aws_glue_catalog_database.processed.name
}

output "glue_processed_crawler" {
  value = aws_glue_crawler.processed.name
}
