"""POST /telemetria (protegido con API key): valida y encola en SQS. Responde 202 rápido."""
import json
import os

import boto3

from comun import log, respuesta
from contrato import validar

sqs = boto3.client("sqs")
MAX_LECTURAS = 500


def handler(event, context):
    try:
        datos = json.loads(event.get("body") or "")
    except (TypeError, ValueError):
        return respuesta(400, {"error": "el cuerpo no es JSON válido"})

    lecturas = datos if isinstance(datos, list) else [datos]
    if len(lecturas) > MAX_LECTURAS:
        return respuesta(413, {"error": f"máximo {MAX_LECTURAS} lecturas por envío"})

    validas, rechazadas = [], []
    for i, lectura in enumerate(lecturas):
        errores = validar(lectura)
        if errores:
            rechazadas.append({"indice": i, "errores": errores})
        else:
            validas.append(lectura)

    for i in range(0, len(validas), 10):
        lote = validas[i:i + 10]
        r = sqs.send_message_batch(
            QueueUrl=os.environ["QUEUE_URL"],
            Entries=[{"Id": str(j), "MessageBody": json.dumps(x)} for j, x in enumerate(lote)],
        )
        if r.get("Failed"):
            log("ERROR", {"accion": "encolar", "fallidos": r["Failed"]})
            return respuesta(500, {"error": "no se pudo encolar", "encoladas": i})

    if rechazadas:
        log("WARN", {"accion": "rechazar", "rechazadas": rechazadas[:20]})
    return respuesta(202 if validas else 400, {"encoladas": len(validas), "rechazadas": rechazadas})
