"""Lambdas de SFN-2 · Planificación diaria."""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

import plan
from comun import a_dynamo, ahora_iso, de_dynamo, log

ddb = boto3.resource("dynamodb")
t_maquinas = ddb.Table(os.environ["T_MAQUINAS"])
t_telemetria = ddb.Table(os.environ["T_TELEMETRIA"])
t_incidentes = ddb.Table(os.environ["T_INCIDENTES"])
t_repuestos = ddb.Table(os.environ["T_REPUESTOS"])
t_reportes = ddb.Table(os.environ["T_REPORTES"])
sns = boto3.client("sns")
secrets = boto3.client("secretsmanager")
TENANT = os.environ.get("TENANT", "MINA_SUR")
MAX_ITEMS = 10   # por lista, para el resumen y el correo


class IAError(Exception):
    pass


class IASinConfigurar(Exception):
    pass


# ---------------- datos ----------------
def consultar(tabla, **kw):
    items, r = [], tabla.query(**kw)
    items += r["Items"]
    while "LastEvaluatedKey" in r:
        r = tabla.query(ExclusiveStartKey=r["LastEvaluatedKey"], **kw)
        items += r["Items"]
    return de_dynamo(items)


def maquinas_y_lecturas():
    """Máquinas del tenant y sus lecturas de las 24 h previas a su última lectura."""
    maquinas = consultar(t_maquinas, KeyConditionExpression=Key("tenant_id").eq(TENANT))
    lecturas = {}
    for m in maquinas:
        if not m.get("ultima_ts"):
            continue
        fin = datetime.fromisoformat(m["ultima_ts"].replace("Z", "+00:00"))
        desde = (fin - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        lecturas[m["maquina_id"]] = consultar(
            t_telemetria, KeyConditionExpression=Key("maquina_id").eq(m["maquina_id"]) & Key("ts").gte(desde))
    return maquinas, lecturas


# ---------------- ramas del Parallel ----------------
def preventivo(event, context):
    return {"preventivo": plan.preventivo(*maquinas_y_lecturas())}


def combustible(event, context):
    return {"combustible": plan.combustible(*maquinas_y_lecturas())}


def utilizacion(event, context):
    return {"utilizacion": plan.utilizacion(*maquinas_y_lecturas())}


def repuestos(event, context):
    maquinas, lecturas = maquinas_y_lecturas()
    proximos = [f["modelo"] for f in plan.preventivo(maquinas, lecturas) if f["estado"] != "OK"]
    desde = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    usos = {}
    for inc in consultar(t_incidentes, KeyConditionExpression=Key("tenant_id").eq(TENANT)):
        if inc.get("creado_ts", "") >= desde:
            for r in inc.get("repuestos") or []:
                if r.get("disponible"):
                    usos[r["repuesto_id"]] = usos.get(r["repuesto_id"], 0) + r.get("cantidad", 1)
    stock = consultar(t_repuestos, KeyConditionExpression=Key("tenant_id").eq(TENANT))
    return {"repuestos": plan.repuestos(stock, usos, proximos)}


# ---------------- resumen + guardar ----------------
def armar_reporte(event):
    reporte = {"tenant_id": TENANT, "fecha": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    for parte in event["analisis"]:
        reporte.update(parte)
    return reporte


_secreto = None


def resumen(event, context):
    global _secreto
    reporte = armar_reporte(event)
    if _secreto is None:
        try:
            _secreto = json.loads(secrets.get_secret_value(SecretId=os.environ["SECRET_GCP"])["SecretString"])
        except ClientError as e:
            raise IASinConfigurar(str(e))
    cuerpo = {k: (v[:MAX_ITEMS] if isinstance(v, list) else v) for k, v in reporte.items()}
    req = urllib.request.Request(_secreto["ia_url"].rstrip("/") + "/resumen",
                                 data=json.dumps(cuerpo, default=str).encode("utf-8"),
                                 headers={"Content-Type": "application/json", "X-Arquifusion-Token": _secreto["token"]},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            res = json.loads(r.read())
    except Exception as e:
        raise IAError(f"{type(e).__name__}: {e}")
    if "resumen_gerente" not in res:
        raise IAError("respuesta sin resumen_gerente")
    return {**reporte, "resumen_gerente": res["resumen_gerente"], "prioridades": res.get("prioridades", []),
            "fuente": "GEMINI"}


def resumen_plantilla(event, context):
    reporte = armar_reporte(event)
    log("WARN", {"accion": "resumen_plantilla", "error": (event.get("error_ia") or {}).get("Error")})
    return {**reporte, **plan.resumen_plantilla(reporte), "fuente": "PLANTILLA"}


def guardar(reporte, context):
    item = {**reporte, "fecha_tipo": f"{reporte['fecha']}#diario", "generado_ts": ahora_iso()}
    t_reportes.put_item(Item=a_dynamo(item))
    texto = (reporte["resumen_gerente"] + "\n\nPrioridades:\n" +
             "\n".join(f"- {p}" for p in reporte.get("prioridades", [])) +
             "\n\nDetalle completo en la plataforma (Planificación).")
    sns.publish(TopicArn=os.environ["TOPIC_ALERTAS"], Subject=f"Planificacion diaria {reporte['fecha']}",
                Message=texto,
                MessageAttributes={"rol": {"DataType": "String", "StringValue": "gerente"},
                                   "severidad": {"DataType": "String", "StringValue": "REPORTE"}})
    log("INFO", {"accion": "reporte_guardado", "fecha": reporte["fecha"], "fuente": reporte.get("fuente")})
    return {"fecha": reporte["fecha"], "fuente": reporte.get("fuente"),
            "conteos": {k: len(reporte.get(k, [])) for k in ("preventivo", "combustible", "utilizacion", "repuestos")}}
