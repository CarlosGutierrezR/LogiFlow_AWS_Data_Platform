# Fase 8: catálogo de curated + Athena para consultar el modelo dimensional.

# ---------- Base de datos y crawler de curated ----------

resource "aws_glue_catalog_database" "curated" {
  name        = "${replace(local.name_prefix, "-", "_")}_curated"
  description = "Modelo dimensional analítico (dim_warehouse, dim_route, fact_shipments)"
}

resource "aws_iam_role" "glue_crawler_curated" {
  name = "${local.name_prefix}-glue-crawler-curated"

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

resource "aws_iam_role_policy_attachment" "glue_service_curated" {
  role       = aws_iam_role.glue_crawler_curated.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_crawler_curated_s3" {
  name = "s3-read-curated-only"
  role = aws_iam_role.glue_crawler_curated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListCuratedBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.data_layer["curated"].arn
      },
      {
        Sid      = "ReadCuratedObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.data_layer["curated"].arn}/*"
      }
    ]
  })
}

resource "aws_glue_crawler" "curated" {
  name          = "${local.name_prefix}-curated-crawler"
  role          = aws_iam_role.glue_crawler_curated.arn
  database_name = aws_glue_catalog_database.curated.name
  description   = "Crawler bajo demanda del modelo dimensional curated"

  dynamic "s3_target" {
    for_each = toset(["dim_warehouse", "dim_route", "fact_shipments"])
    content {
      path = "s3://${aws_s3_bucket.data_layer["curated"].bucket}/${s3_target.value}/"
    }
  }

  tags = {
    layer = "curated"
  }
}

# ---------- Athena: bucket de resultados + workgroup ----------

resource "aws_s3_bucket" "athena_results" {
  bucket = "${local.name_prefix}-athena-results-${data.aws_caller_identity.current.account_id}"

  tags = {
    layer = "athena"
  }
}

resource "aws_s3_bucket_public_access_block" "athena_results" {
  bucket                  = aws_s3_bucket.athena_results.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Expira resultados de consultas a los 7 días (control de costes).
resource "aws_s3_bucket_lifecycle_configuration" "athena_results" {
  bucket = aws_s3_bucket.athena_results.id
  rule {
    id     = "expire-query-results"
    status = "Enabled"
    filter {}
    expiration {
      days = 7
    }
  }
}

resource "aws_athena_workgroup" "main" {
  name = "${local.name_prefix}-wg"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/query-results/"
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }

    # Corta consultas que escaneen más de 1 GB: red de seguridad de coste
    # (nuestros datos son KB; esto protege ante un error).
    bytes_scanned_cutoff_per_query = 1073741824
  }

  tags = {
    purpose = "analytics"
  }
}

output "athena_workgroup" {
  value = aws_athena_workgroup.main.name
}

output "glue_curated_database" {
  value = aws_glue_catalog_database.curated.name
}

output "glue_curated_crawler" {
  value = aws_glue_crawler.curated.name
}
