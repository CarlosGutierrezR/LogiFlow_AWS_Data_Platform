# Capa de almacenamiento del data lake (Fase 3).
# 5 buckets por capas. El sufijo con el account id garantiza unicidad global
# sin exponer información sensible adicional (el account id no es un secreto).

locals {
  # Configuración por capa:
  # - versioning: capas que conservan histórico (raw = dato original, curated = analítico)
  # - expiration_days: capas efímeras (landing se reprocesa a raw; quarantine se revisa y purga)
  data_layers = {
    landing = {
      versioning      = false
      expiration_days = 30
    }
    raw = {
      versioning      = true
      expiration_days = null
    }
    processed = {
      versioning      = false
      expiration_days = null
    }
    curated = {
      versioning      = true
      expiration_days = null
    }
    quarantine = {
      versioning      = false
      expiration_days = 90
    }
  }
}

resource "aws_s3_bucket" "data_layer" {
  for_each = local.data_layers

  bucket = "${local.name_prefix}-${each.key}-${data.aws_caller_identity.current.account_id}"

  tags = {
    layer = each.key
  }
}

# Bloqueo total de acceso público en cada bucket (además del nivel de cuenta).
resource "aws_s3_bucket_public_access_block" "data_layer" {
  for_each = local.data_layers

  bucket = aws_s3_bucket.data_layer[each.key].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Cifrado en reposo con SSE-S3 (AES256). KMS gestionado por el cliente se
# valorará en una fase posterior si se justifica (ver docs/security.md).
resource "aws_s3_bucket_server_side_encryption_configuration" "data_layer" {
  for_each = local.data_layers

  bucket = aws_s3_bucket.data_layer[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Versionado solo donde aporta valor (histórico de raw y curated).
resource "aws_s3_bucket_versioning" "data_layer" {
  for_each = local.data_layers

  bucket = aws_s3_bucket.data_layer[each.key].id

  versioning_configuration {
    status = each.value.versioning ? "Enabled" : "Suspended"
  }
}

# Ciclo de vida: limpieza de multiparts incompletos en todos los buckets
# y expiración de objetos en las capas efímeras (control de costes).
resource "aws_s3_bucket_lifecycle_configuration" "data_layer" {
  for_each = local.data_layers

  bucket = aws_s3_bucket.data_layer[each.key].id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  dynamic "rule" {
    for_each = each.value.expiration_days == null ? [] : [each.value.expiration_days]

    content {
      id     = "expire-after-${rule.value}-days"
      status = "Enabled"

      filter {}

      expiration {
        days = rule.value
      }
    }
  }
}
