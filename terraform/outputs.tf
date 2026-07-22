# Outputs no sensibles para uso en fases posteriores (Glue, Athena, docs).

output "data_bucket_names" {
  description = "Nombre de cada bucket por capa."
  value       = { for k, b in aws_s3_bucket.data_layer : k => b.bucket }
}

output "data_bucket_arns" {
  description = "ARN de cada bucket por capa (para políticas IAM de fases siguientes)."
  value       = { for k, b in aws_s3_bucket.data_layer : k => b.arn }
}

output "aws_region_in_use" {
  description = "Región efectiva del despliegue."
  value       = var.aws_region
}
