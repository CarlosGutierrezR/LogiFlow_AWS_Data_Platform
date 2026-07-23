# Fase 10: observabilidad — alarmas CloudWatch + notificaciones SNS.
# Detecta fallos del pipeline (Step Functions) y de cada job de Glue, y avisa
# por email. Métricas usadas: todas publicadas por AWS sin coste adicional de
# instrumentación (Step Functions y Glue emiten métricas a CloudWatch).

variable "alert_email" {
  description = "Email que recibe las alertas operativas (debe confirmarse en el correo de suscripción SNS)."
  type        = string
  default     = "chgut31@gmail.com"
}

# ---------- Tema SNS ----------

resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"

  tags = {
    purpose = "observability"
  }
}

resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
  # La suscripción por email requiere confirmación manual desde el enlace
  # que AWS envía al correo; hasta entonces queda "PendingConfirmation".
}

# ---------- Alarma: ejecuciones fallidas del pipeline ----------

resource "aws_cloudwatch_metric_alarm" "pipeline_failed" {
  alarm_name        = "${local.name_prefix}-pipeline-failed"
  alarm_description = "El state machine del pipeline batch registró una ejecución fallida."

  namespace   = "AWS/States"
  metric_name = "ExecutionsFailed"
  dimensions = {
    StateMachineArn = aws_sfn_state_machine.pipeline.arn
  }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]

  tags = {
    purpose = "observability"
  }
}

# ---------- Alarmas: fallos de cada job de Glue ----------
# Glue publica glue.driver.aggregate.numFailedTasks, pero para "job fallido"
# la señal fiable es la métrica de tipo de tarea; usamos la métrica de fallos
# de ejecución por job a través de la dimensión JobRunState no está disponible
# como métrica directa, así que alarmamos sobre numFailedTasks > 0 por job.

resource "aws_cloudwatch_metric_alarm" "glue_job_failed" {
  for_each = toset([
    aws_glue_job.landing_to_raw.name,
    aws_glue_job.raw_to_processed.name,
    aws_glue_job.processed_to_curated.name,
  ])

  alarm_name        = "${each.value}-failed-tasks"
  alarm_description = "El job de Glue ${each.value} registró tareas fallidas."

  namespace   = "Glue"
  metric_name = "glue.driver.aggregate.numFailedTasks"
  dimensions = {
    JobName  = each.value
    JobRunId = "ALL"
    Type     = "count"
  }

  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]

  tags = {
    purpose = "observability"
  }
}

output "sns_alerts_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
