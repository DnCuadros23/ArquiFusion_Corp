"""λ replicador (carril ⑤): DynamoDB Streams → POST {replica_url}/replica en Google Cloud (Firestore).

- Sin secreto `arquifusion/gcp` todavía: registra un aviso y no falla (no bloquea el stream).
- Dentro de un lote, solo se envía el último cambio de cada documento.
- Si Google no responde, informa el registro fallido y Lambda reintenta; tras 5 intentos va a la DLQ.
"""
import json
import os
import urllib.request
from decimal import Decimal

from comun import log

COLECCIONES = {"t_maquinas": ("maquinas", "maquina_id"), "t_incidentes": ("incidentes", "incidente_id")}
CAMPOS_PRIVADOS = {"task_token", "stats"}   # nunca salen de AWS
_secreto = None


# ---------------- lógica pura ----------------
def deserializar(valor):
    """Formato de DynamoDB Streams ({"S": "x"}, {"N": "1"}, {"M": {...}}...) → Python."""
    (tipo, v), = valor.items()
    if tipo == "S":
        return v
    if tipo == "N":
        d = Decimal(v)
        return int(d) if d == d.to_integral_value() else float(d)
    if tipo == "BOOL":
        return v
    if tipo == "NULL":
        return None
    if tipo == "M":
        return {k: deserializar(x) for k, x in v.items()}
    if tipo == "L":
        return [deserializar(x) for x in v]
    if tipo in ("SS", "NS"):
        return [deserializar({tipo[0]: x}) for x in v]
    return None


def coleccion_de(arn):
    """arn:...:table/dev-t_maquinas/stream/... → ("maquinas", "maquina_id")."""
    tabla = arn.split("table/")[1].split("/")[0]      # "dev-t_maquinas"
    return COLECCIONES.get(tabla.split("-", 1)[-1], (None, None))


def a_operaciones(records):
    """Convierte los registros del stream en operaciones /replica (la última por documento gana)."""
    ops = {}
    for r in records:
        coleccion, clave = coleccion_de(r["eventSourceARN"])
        if not coleccion:
            continue
        ddb = r["dynamodb"]
        if r["eventName"] == "REMOVE":
            doc_id = deserializar(ddb["Keys"][clave])
            op = {"coleccion": coleccion, "id": doc_id, "operacion": "DELETE", "datos": {}}
        else:
            datos = {k: deserializar(v) for k, v in ddb["NewImage"].items() if k not in CAMPOS_PRIVADOS}
            doc_id = datos[clave]
            op = {"coleccion": coleccion, "id": doc_id, "operacion": "UPSERT", "datos": datos}
        anterior = ops.get((coleccion, doc_id))
        secuencias = (anterior["_secuencias"] if anterior else []) + [ddb["SequenceNumber"]]
        ops[(coleccion, doc_id)] = {**op, "_secuencias": secuencias}
    return list(ops.values())


# ---------------- envío ----------------
def leer_secreto():
    global _secreto
    if _secreto is None:
        import boto3  # noqa: PLC0415 (import tardío: las pruebas no necesitan boto3)
        from botocore.exceptions import ClientError  # noqa: PLC0415
        try:
            valor = boto3.client("secretsmanager").get_secret_value(SecretId=os.environ["SECRET_GCP"])
            _secreto = json.loads(valor["SecretString"])
        except ClientError as e:
            log("WARN", {"accion": "replica_sin_configurar", "detalle": str(e)})
            return None
    return _secreto


def enviar(secreto, op):
    cuerpo = {k: v for k, v in op.items() if not k.startswith("_")}
    req = urllib.request.Request(
        secreto["replica_url"].rstrip("/") + "/replica",
        data=json.dumps(cuerpo, default=str).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Arquifusion-Token": secreto["token"]},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")


def handler(event, context):
    secreto = leer_secreto()
    if not secreto:
        return {"batchItemFailures": []}  # Google aún no está configurado: no bloquear el stream
    fallidas = []
    for op in a_operaciones(event.get("Records", [])):
        try:
            enviar(secreto, op)
        except Exception as e:
            log("ERROR", {"accion": "replicar", "coleccion": op["coleccion"], "id": op["id"], "error": str(e)})
            fallidas.extend(op["_secuencias"])
    # Lambda reintenta desde la secuencia fallida más antigua.
    return {"batchItemFailures": [{"itemIdentifier": min(fallidas, key=int)}] if fallidas else []}
