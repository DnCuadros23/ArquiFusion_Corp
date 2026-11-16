"""Utilidades compartidas por las Lambdas del servicio."""
import json
from datetime import datetime, timezone
from decimal import Decimal


def log(tipo, datos):
    print(json.dumps({"tipo": tipo, "log_datos": datos}, default=str, ensure_ascii=False))


def ahora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def a_dynamo(obj):
    """float → Decimal (DynamoDB no acepta float)."""
    return json.loads(json.dumps(obj), parse_float=Decimal)


def de_dynamo(obj):
    """Decimal → int/float para poder operar y serializar."""
    if isinstance(obj, list):
        return [de_dynamo(x) for x in obj]
    if isinstance(obj, dict):
        return {k: de_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    return obj


def respuesta(status, cuerpo):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(cuerpo, ensure_ascii=False),
    }
