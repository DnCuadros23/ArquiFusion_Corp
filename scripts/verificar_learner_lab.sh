#!/usr/bin/env bash
# Fase 0 — comprueba que el Learner Lab tiene lo que necesitamos.
# Uso: bash scripts/verificar_learner_lab.sh
# Requiere AWS CLI con las credenciales del Learner Lab (~/.aws/credentials).

REGION="${AWS_REGION:-us-east-1}"
ok=0; fallas=0

check () {
  local nombre="$1"; shift
  if salida=$("$@" --region "$REGION" 2>&1); then
    echo "  OK    $nombre"; ok=$((ok+1))
  else
    echo "  FALLA $nombre -> $(echo "$salida" | tail -n1)"; fallas=$((fallas+1))
  fi
}

echo "Cuenta y región:"
aws sts get-caller-identity --query '[Account,Arn]' --output text || { echo "Sin credenciales. Copia las del Learner Lab a ~/.aws/credentials"; exit 1; }
echo "  región: $REGION"
echo
echo "Servicios:"
check "IAM LabRole existe"            aws iam get-role --role-name LabRole --query Role.Arn --output text
check "Lambda"                        aws lambda list-functions --max-items 1
check "API Gateway"                   aws apigateway get-rest-apis --limit 1
check "SQS"                           aws sqs list-queues --max-results 1
check "SNS"                           aws sns list-topics
check "DynamoDB"                      aws dynamodb list-tables --max-items 1
check "DynamoDB Streams"              aws dynamodbstreams list-streams --limit 1
check "S3"                            aws s3api list-buckets --query 'Buckets[0].Name'
check "Step Functions"                aws stepfunctions list-state-machines --max-results 1
check "EventBridge Scheduler"         aws scheduler list-schedules --max-results 1
check "EventBridge (reglas)"          aws events list-rules --limit 1
check "Secrets Manager"               aws secretsmanager list-secrets --max-results 1
check "Glue"                          aws glue get-databases --max-results 1
check "Athena"                        aws athena list-work-groups --max-results 1
check "CloudWatch Logs"               aws logs describe-log-groups --limit 1
check "CloudFormation"                aws cloudformation list-stacks --max-items 1

echo
echo "Resultado: $ok OK, $fallas con falla."
[ "$fallas" -eq 0 ] && echo "Learner Lab listo para Fase 1." || echo "Avisa al equipo qué servicio falló antes de diseñar sobre él."
