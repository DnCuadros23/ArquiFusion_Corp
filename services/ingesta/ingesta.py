"""λ ingesta + detector (trigger SQS).

Por cada lectura: guarda en t_telemetria, actualiza el estado de la máquina, evalúa anomalías
y, si hay una y la máquina no tiene ya un incidente abierto, crea el incidente y arranca SFN-1.
El lote completo se escribe en S3 (raw/) para el histórico.
"""
import json
import os
import time
import uuid

import boto3
from botocore.exceptions import ClientError

from comun import a_dynamo, ahora_iso, de_dynamo, log
from contrato import validar
from detector import evaluar

dynamodb = boto3.resource("dynamodb")
t_maquinas = dynamodb.Table(os.environ["T_MAQUINAS"])
t_telemetria = dynamodb.Table(os.environ["T_TELEMETRIA"])
t_incidentes = dynamodb.Table(os.environ["T_INCIDENTES"])
s3 = boto3.client("s3")
sfn = boto3.client("stepfunctions")

TTL_TELEMETRIA = 3 * 24 * 3600


def handler(event, context):
    fallidos, lecturas = [], []
    for rec in event.get("Records", []):
        try:
            lectura = json.loads(rec["body"])
        except ValueError:
            log("ERROR", {"accion": "parsear", "messageId": rec.get("messageId")})
            continue
        errores = validar(lectura)
        if errores:  # inválida: se descarta (reintentar no la arreglaría)
            log("ERROR", {"accion": "validar", "errores": errores, "lectura": lectura})
            continue
        lecturas.append((rec["messageId"], lectura))

    lecturas.sort(key=lambda par: par[1]["ts"])
    procesadas = []
    for message_id, lectura in lecturas:
        try:
            procesar(lectura)
            procesadas.append(lectura)
        except Exception as e:  # el mensaje vuelve a la cola y, tras 3 intentos, a la DLQ
            log("ERROR", {"accion": "procesar", "maquina_id": lectura["maquina_id"], "error": str(e)})
            fallidos.append({"itemIdentifier": message_id})

    if procesadas:
        guardar_en_s3(procesadas)
    log("INFO", {"accion": "lote", "procesadas": len(procesadas), "fallidas": len(fallidos)})
    return {"batchItemFailures": fallidos}


def procesar(lectura):
    t_telemetria.put_item(Item=a_dynamo({**lectura, "expira": int(time.time()) + TTL_TELEMETRIA}))

    clave = {"tenant_id": lectura["tenant_id"], "maquina_id": lectura["maquina_id"]}
    maquina = de_dynamo(t_maquinas.get_item(Key=clave, ConsistentRead=True).get("Item") or {})
    resultado, stats = evaluar(lectura, maquina.get("stats"))

    t_maquinas.update_item(
        Key=clave,
        UpdateExpression=(
            "SET modelo = :modelo, zona = :zona, lat = :lat, lon = :lon, estado = :estado, "
            "horas_motor = :horas, ultima_lectura = :lectura, ultima_ts = :ts, stats = :stats, riesgo = :riesgo"
        ),
        ExpressionAttributeValues=a_dynamo({
            ":modelo": lectura["modelo"], ":zona": lectura["zona"], ":lat": lectura["lat"],
            ":lon": lectura["lon"], ":estado": lectura["estado"], ":horas": lectura["horas_motor"],
            ":lectura": lectura, ":ts": lectura["ts"], ":stats": stats,
            ":riesgo": resultado["severidad"] if resultado else "NORMAL",
        }),
    )

    if resultado and not maquina.get("incidente_abierto"):
        abrir_incidente(lectura, resultado, clave)


def abrir_incidente(lectura, resultado, clave):
    incidente_id = str(uuid.uuid4())
    # Marca la máquina de forma atómica: si otra ejecución ya abrió un incidente, no duplicamos.
    try:
        t_maquinas.update_item(
            Key=clave,
            UpdateExpression="SET incidente_abierto = :id",
            ConditionExpression="attribute_not_exists(incidente_abierto) OR attribute_type(incidente_abierto, :tnulo)",
            ExpressionAttributeValues={":id": incidente_id, ":tnulo": "NULL"},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return
        raise

    ahora = ahora_iso()
    vars_txt = ", ".join(v["variable"] for v in resultado["variables_anomalas"])
    incidente = {
        "tenant_id": lectura["tenant_id"],
        "incidente_id": incidente_id,
        "maquina_id": lectura["maquina_id"],
        "modelo": lectura["modelo"],
        "zona": lectura["zona"],
        "lat": lectura["lat"],
        "lon": lectura["lon"],
        "creado_ts": ahora,
        "estado": "DETECTADO",
        "severidad": resultado["severidad"],
        "variables_anomalas": resultado["variables_anomalas"],
        "analisis_ia": None,
        "grupo_causa_comun": None,
        "tecnico_asignado": None,
        "repuestos": [],
        "linea_tiempo": [{"ts": ahora, "evento": "DETECTADO",
                          "detalle": f"{len(resultado['variables_anomalas'])} variable(s) fuera de lo habitual: {vars_txt}"}],
        "cierre": None,
        "task_token": None,
    }
    t_incidentes.put_item(Item=a_dynamo(incidente))
    log("INFO", {"accion": "incidente_creado", "incidente_id": incidente_id,
                 "maquina_id": lectura["maquina_id"], "severidad": resultado["severidad"]})

    try:
        sfn.start_execution(stateMachineArn=os.environ["SFN_INCIDENTES_ARN"],
                            name=incidente_id, input=json.dumps(incidente))
    except ClientError as e:
        # Si SFN-1 aún no está desplegada, el incidente queda DETECTADO y se ve igual en la web.
        log("ERROR", {"accion": "iniciar_sfn", "incidente_id": incidente_id, "error": str(e)})


def guardar_en_s3(lecturas):
    fecha = lecturas[0]["ts"][:10]
    clave = f"raw/telemetria/fecha={fecha}/{uuid.uuid4()}.json"
    cuerpo = "\n".join(json.dumps(x, ensure_ascii=False) for x in lecturas)  # JSON por línea (Athena)
    try:
        s3.put_object(Bucket=os.environ["BUCKET_DATALAKE"], Key=clave, Body=cuerpo.encode("utf-8"),
                      ContentType="application/x-ndjson")
    except ClientError as e:
        log("ERROR", {"accion": "guardar_s3", "error": str(e)})
