# Fase 9: orquestación del pipeline batch con Step Functions.
# El state machine ejecuta los 3 jobs en secuencia usando la integración
# síncrona (.sync): cada job espera a que el anterior termine en SUCCEEDED
# antes de arrancar. Esto elimina las carreras y los ConcurrentRuns que
# aparecían al lanzar los jobs a mano (ver docs/runbook.md).

# ---------- Rol de ejecución del state machine ----------

resource "aws_iam_role" "sfn_pipeline" {
  name = "${local.name_prefix}-sfn-pipeline"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "states.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })
}

# Permisos: arrancar/monitorizar SOLO los 3 jobs del proyecto.
# La integración .sync de Glue funciona por polling (GetJobRun), por lo que
# basta con StartJobRun + GetJobRun + BatchStopJobRun sobre esos jobs.
resource "aws_iam_role_policy" "sfn_run_glue_jobs" {
  name = "run-glue-etl-jobs"
  role = aws_iam_role.sfn_pipeline.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RunAndMonitorGlueJobs"
        Effect = "Allow"
        Action = [
          "glue:StartJobRun",
          "glue:GetJobRun",
          "glue:GetJobRuns",
          "glue:BatchStopJobRun",
        ]
        Resource = [
          aws_glue_job.landing_to_raw.arn,
          aws_glue_job.raw_to_processed.arn,
          aws_glue_job.processed_to_curated.arn,
        ]
      }
    ]
  })
}

# ---------- Definición del state machine ----------

locals {
  # Retry común: 2 reintentos con backoff ante errores transitorios de Glue
  # (incluido ConcurrentRunsExceededException).
  glue_retry = [
    {
      ErrorEquals = [
        "Glue.ConcurrentRunsExceededException",
        "Glue.InternalServiceException",
        "States.TaskFailed",
      ]
      IntervalSeconds = 30
      MaxAttempts     = 2
      BackoffRate     = 2.0
    }
  ]

  pipeline_definition = jsonencode({
    Comment = "LogiFlow batch: landing -> raw -> processed -> curated"
    StartAt = "LandingToRaw"
    States = {
      LandingToRaw = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = aws_glue_job.landing_to_raw.name
          Arguments = {
            "--date.$" = "$.ingest_date"
          }
        }
        # Guarda el resultado del job en una rama aparte para conservar
        # $.ingest_date de cara a los estados siguientes.
        ResultPath = "$.landing_to_raw_result"
        Retry      = local.glue_retry
        Catch      = [{ ErrorEquals = ["States.ALL"], Next = "PipelineFailed" }]
        Next       = "RawToProcessed"
      }
      RawToProcessed = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = aws_glue_job.raw_to_processed.name
          Arguments = {
            "--date.$" = "$.ingest_date"
          }
        }
        ResultPath = "$.raw_to_processed_result"
        Retry      = local.glue_retry
        Catch      = [{ ErrorEquals = ["States.ALL"], Next = "PipelineFailed" }]
        Next       = "ProcessedToCurated"
      }
      ProcessedToCurated = {
        Type     = "Task"
        Resource = "arn:aws:states:::glue:startJobRun.sync"
        Parameters = {
          JobName = aws_glue_job.processed_to_curated.name
          Arguments = {
            "--date.$" = "$.ingest_date"
          }
        }
        ResultPath = "$.processed_to_curated_result"
        Retry      = local.glue_retry
        Catch      = [{ ErrorEquals = ["States.ALL"], Next = "PipelineFailed" }]
        Next       = "PipelineSucceeded"
      }
      PipelineSucceeded = { Type = "Succeed" }
      PipelineFailed = {
        Type  = "Fail"
        Error = "PipelineFailed"
        Cause = "Uno de los jobs de Glue falló; revisar CloudWatch Logs."
      }
    }
  })
}

resource "aws_sfn_state_machine" "pipeline" {
  name     = "${local.name_prefix}-batch-pipeline"
  role_arn = aws_iam_role.sfn_pipeline.arn

  definition = local.pipeline_definition

  tags = {
    purpose = "orchestration"
  }
}

output "sfn_pipeline_arn" {
  description = "ARN del state machine del pipeline batch."
  value       = aws_sfn_state_machine.pipeline.arn
}

output "sfn_pipeline_name" {
  value = aws_sfn_state_machine.pipeline.name
}
