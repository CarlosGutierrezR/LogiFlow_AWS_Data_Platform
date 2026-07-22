# Fase 6b: jobs de Glue para el ETL (landing->raw y raw->processed).
# Runtime Glue 5.0 (Spark 3.5), el mismo con el que se probaron los jobs en local.
# Control de coste: 2 workers G.1X (mínimo), timeout 10 min, sin reintentos,
# ejecución solo bajo demanda (start-job-run).

# ---------- Bucket de artefactos (scripts y paquete src.zip) ----------

resource "aws_s3_bucket" "artifacts" {
  bucket = "${local.name_prefix}-artifacts-${data.aws_caller_identity.current.account_id}"

  tags = {
    layer = "artifacts"
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# ---------- Empaquetado y subida del código ----------

# El zip debe contener el paquete con raíz "src/" para que "from src.etl import ..."
# funcione vía --extra-py-files. archive_file con source_dir perdería ese prefijo,
# así que el zip se construye entrada a entrada con las rutas relativas correctas:
data "archive_file" "src_zip_rooted" {
  type        = "zip"
  output_path = "${path.module}/.build/src.zip"

  dynamic "source" {
    for_each = fileset("${path.module}/..", "src/**/*.py")
    content {
      filename = source.value
      content  = file("${path.module}/../${source.value}")
    }
  }
}

resource "aws_s3_object" "src_zip" {
  bucket      = aws_s3_bucket.artifacts.id
  key         = "etl/src.zip"
  source      = data.archive_file.src_zip_rooted.output_path
  source_hash = data.archive_file.src_zip_rooted.output_base64sha256
}

resource "aws_s3_object" "entry_landing_to_raw" {
  bucket      = aws_s3_bucket.artifacts.id
  key         = "etl/landing_to_raw_entry.py"
  source      = "${path.module}/../ops/glue_entries/landing_to_raw_entry.py"
  source_hash = filebase64sha256("${path.module}/../ops/glue_entries/landing_to_raw_entry.py")
}

resource "aws_s3_object" "entry_raw_to_processed" {
  bucket      = aws_s3_bucket.artifacts.id
  key         = "etl/raw_to_processed_entry.py"
  source      = "${path.module}/../ops/glue_entries/raw_to_processed_entry.py"
  source_hash = filebase64sha256("${path.module}/../ops/glue_entries/raw_to_processed_entry.py")
}

# ---------- Rol IAM de los jobs (mínimo privilegio por capa) ----------

resource "aws_iam_role" "glue_etl" {
  name = "${local.name_prefix}-glue-etl"

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

resource "aws_iam_role_policy_attachment" "glue_etl_service" {
  role       = aws_iam_role.glue_etl.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "glue_etl_s3" {
  name = "s3-data-layers"
  role = aws_iam_role.glue_etl.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListDataBuckets"
        Effect = "Allow"
        Action = ["s3:ListBucket"]
        Resource = [
          aws_s3_bucket.data_layer["landing"].arn,
          aws_s3_bucket.data_layer["raw"].arn,
          aws_s3_bucket.data_layer["processed"].arn,
          aws_s3_bucket.data_layer["quarantine"].arn,
          aws_s3_bucket.artifacts.arn,
        ]
      },
      {
        Sid    = "ReadLandingAndArtifacts"
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = [
          "${aws_s3_bucket.data_layer["landing"].arn}/*",
          "${aws_s3_bucket.artifacts.arn}/*",
        ]
      },
      {
        Sid    = "ReadWriteRawProcessedQuarantine"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = [
          "${aws_s3_bucket.data_layer["raw"].arn}/*",
          "${aws_s3_bucket.data_layer["processed"].arn}/*",
          "${aws_s3_bucket.data_layer["quarantine"].arn}/*",
        ]
      }
    ]
  })
}

# ---------- Definición de los jobs ----------

locals {
  glue_job_common_args = {
    "--extra-py-files"                   = "s3://${aws_s3_bucket.artifacts.bucket}/${aws_s3_object.src_zip.key}"
    "--job-language"                     = "python"
    "--enable-continuous-cloudwatch-log" = "true"
    # --date se pasa en cada ejecución con start-job-run
  }
}

resource "aws_glue_job" "landing_to_raw" {
  name              = "${local.name_prefix}-landing-to-raw"
  role_arn          = aws_iam_role.glue_etl.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 10
  max_retries       = 0

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.artifacts.bucket}/${aws_s3_object.entry_landing_to_raw.key}"
    python_version  = "3"
  }

  default_arguments = merge(local.glue_job_common_args, {
    "--landing-path" = "s3://${aws_s3_bucket.data_layer["landing"].bucket}"
    "--raw-path"     = "s3://${aws_s3_bucket.data_layer["raw"].bucket}"
  })

  tags = {
    layer = "raw"
  }
}

resource "aws_glue_job" "raw_to_processed" {
  name              = "${local.name_prefix}-raw-to-processed"
  role_arn          = aws_iam_role.glue_etl.arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 10
  max_retries       = 0

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.artifacts.bucket}/${aws_s3_object.entry_raw_to_processed.key}"
    python_version  = "3"
  }

  default_arguments = merge(local.glue_job_common_args, {
    "--raw-path"        = "s3://${aws_s3_bucket.data_layer["raw"].bucket}"
    "--processed-path"  = "s3://${aws_s3_bucket.data_layer["processed"].bucket}"
    "--quarantine-path" = "s3://${aws_s3_bucket.data_layer["quarantine"].bucket}"
  })

  tags = {
    layer = "processed"
  }
}

output "glue_etl_jobs" {
  description = "Jobs de ETL desplegados (ejecutar con start-job-run)."
  value = {
    landing_to_raw   = aws_glue_job.landing_to_raw.name
    raw_to_processed = aws_glue_job.raw_to_processed.name
  }
}
