"""λ api: rutas de contracts/interfaces.md §3. El tenant y el rol SIEMPRE salen del token (autorizador)."""
import json
import os

import boto3
from boto3.dynamodb.conditions import Key

from comun import de_dynamo, log, respuesta

ddb = boto3.resource("dynamodb")
t_maquinas = ddb.Table(os.environ["T_MAQUINAS"])
t_telemetria = ddb.Table(os.environ["T_TELEMETRIA"])
t_incidentes = ddb.Table(os.environ["T_INCIDENTES"])
t_tecnicos = ddb.Table(os.environ["T_TECNICOS"])
t_reportes = ddb.Table(os.environ["T_REPORTES"])
sfn = boto3.client("stepfunctions")

ABIERTOS = {"DETECTADO", "ANALIZADO", "ASIGNADO", "EN_ATENCION"}
CAMPOS_MAQUINA = ("maquina_id", "modelo", "tipo", "zona", "lat", "lon", "estado", "horas_motor",
                  "riesgo", "ultima_ts", "ultima_lectura", "incidente_abierto", "costo_hora_usd")


# ---------------- lógica pura ----------------
def resumen_maquina(m):
    return {k: m.get(k) for k in CAMPOS_MAQUINA}


def sin_secretos(inc):
    return {k: v for k, v in inc.items() if k != "task_token"}


def filtrar_incidentes(incidentes, estado, sesion):
    estado = (estado or "ABIERTOS").upper()
    if estado == "ABIERTOS":
        incidentes = [i for i in incidentes if i.get("estado") in ABIERTOS]
    elif estado != "TODOS":
        incidentes = [i for i in incidentes if i.get("estado") == estado]
    if sesion.get("rol") == "tecnico" and sesion.get("tecnico_id"):
        incidentes = [i for i in incidentes if (i.get("tecnico_asignado") or {}).get("tecnico_id") == sesion["tecnico_id"]]
    return sorted((sin_secretos(i) for i in incidentes), key=lambda i: i.get("creado_ts", ""), reverse=True)


def validar_cierre(datos):
    errores = []
    if not isinstance(datos.get("intervencion"), str) or not datos["intervencion"].strip():
        errores.append("'intervencion' es obligatoria")
    if not isinstance(datos.get("componentes_reemplazados", []), list):
        errores.append("'componentes_reemplazados' debe ser una lista")
    if not isinstance(datos.get("falla_confirmada", False), bool):
        errores.append("'falla_confirmada' debe ser true o false")
    m = datos.get("minutos_detenida")
    if m is not None and (isinstance(m, bool) or not isinstance(m, (int, float)) or m < 0):
        errores.append("'minutos_detenida' debe ser un número >= 0")
    return errores


# ---------------- acceso a datos ----------------
def todos(tabla, **kw):
    items, r = [], tabla.query(**kw)
    items += r["Items"]
    while "LastEvaluatedKey" in r:
        r = tabla.query(ExclusiveStartKey=r["LastEvaluatedKey"], **kw)
        items += r["Items"]
    return de_dynamo(items)


def obtener_incidente(tenant, incidente_id):
    return de_dynamo(t_incidentes.get_item(Key={"tenant_id": tenant, "incidente_id": incidente_id}).get("Item"))


# ---------------- rutas ----------------
def listar_maquinas(sesion, ev):
    maquinas = todos(t_maquinas, KeyConditionExpression=Key("tenant_id").eq(sesion["tenant_id"]))
    return 200, [resumen_maquina(m) for m in sorted(maquinas, key=lambda m: m["maquina_id"])]


def detalle_maquina(sesion, ev):
    mid = ev["pathParameters"]["id"]
    m = de_dynamo(t_maquinas.get_item(Key={"tenant_id": sesion["tenant_id"], "maquina_id": mid}).get("Item"))
    if not m:
        return 404, {"error": "máquina no encontrada"}
    lecturas = de_dynamo(t_telemetria.query(KeyConditionExpression=Key("maquina_id").eq(mid),
                                            ScanIndexForward=False, Limit=50)["Items"])
    incidentes = de_dynamo(t_incidentes.query(IndexName="por_maquina", KeyConditionExpression=Key("maquina_id").eq(mid),
                                              ScanIndexForward=False, Limit=20)["Items"])
    return 200, {**resumen_maquina(m),
                 "lecturas": [{k: v for k, v in l.items() if k != "expira"} for l in reversed(lecturas)],
                 "incidentes": [sin_secretos(i) for i in incidentes if i.get("tenant_id") == sesion["tenant_id"]]}


def listar_incidentes(sesion, ev):
    estado = (ev.get("queryStringParameters") or {}).get("estado")
    incidentes = todos(t_incidentes, KeyConditionExpression=Key("tenant_id").eq(sesion["tenant_id"]))
    return 200, filtrar_incidentes(incidentes, estado, sesion)


def detalle_incidente(sesion, ev):
    inc = obtener_incidente(sesion["tenant_id"], ev["pathParameters"]["id"])
    return (200, sin_secretos(inc)) if inc else (404, {"error": "incidente no encontrado"})


def cerrar_incidente(sesion, ev):
    if sesion.get("rol") not in ("tecnico", "supervisor"):
        return 403, {"error": "solo un técnico o supervisor puede cerrar incidentes"}
    try:
        datos = json.loads(ev.get("body") or "")
    except ValueError:
        return 400, {"error": "el cuerpo no es JSON válido"}
    errores = validar_cierre(datos if isinstance(datos, dict) else {})
    if errores:
        return 400, {"errores": errores}

    inc = obtener_incidente(sesion["tenant_id"], ev["pathParameters"]["id"])
    if not inc:
        return 404, {"error": "incidente no encontrado"}
    if not inc.get("task_token"):
        return 409, {"error": f"el incidente no está esperando cierre (estado {inc.get('estado')})"}

    salida = {k: datos[k] for k in ("intervencion", "componentes_reemplazados", "falla_confirmada", "minutos_detenida")
              if k in datos}
    salida["cerrado_por"] = sesion.get("usuario")
    try:
        sfn.send_task_success(taskToken=inc["task_token"], output=json.dumps(salida))
    except (sfn.exceptions.TaskTimedOut, sfn.exceptions.InvalidToken, sfn.exceptions.TaskDoesNotExist):
        return 409, {"error": "el flujo de este incidente ya no está esperando cierre"}
    log("INFO", {"accion": "cerrar_incidente", "incidente_id": inc["incidente_id"], "usuario": sesion.get("usuario")})
    return 200, {"ok": True}


def listar_tecnicos(sesion, ev):
    tecnicos = todos(t_tecnicos, KeyConditionExpression=Key("tenant_id").eq(sesion["tenant_id"]))
    campos = ("tecnico_id", "nombre", "especialidad", "zona", "lat", "lon", "disponible", "incidentes_activos")
    return 200, [{k: t.get(k) for k in campos} for t in sorted(tecnicos, key=lambda t: t["tecnico_id"])]


def ultimo_reporte(sesion, ev):
    r = de_dynamo(t_reportes.query(KeyConditionExpression=Key("tenant_id").eq(sesion["tenant_id"]),
                                   ScanIndexForward=False, Limit=1)["Items"])
    return (200, r[0]) if r else (404, {"error": "todavía no hay reportes"})


RUTAS = {
    ("GET", "/api/maquinas"): listar_maquinas,
    ("GET", "/api/maquinas/{id}"): detalle_maquina,
    ("GET", "/api/incidentes"): listar_incidentes,
    ("GET", "/api/incidentes/{id}"): detalle_incidente,
    ("POST", "/api/incidentes/{id}/cerrar"): cerrar_incidente,
    ("GET", "/api/tecnicos"): listar_tecnicos,
    ("GET", "/api/reportes/ultimo"): ultimo_reporte,
}


def handler(event, context):
    ruta = RUTAS.get((event.get("httpMethod"), event.get("resource")))
    if not ruta:
        return respuesta(404, {"error": "ruta no encontrada"})
    sesion = (event.get("requestContext") or {}).get("authorizer") or {}
    if not sesion.get("tenant_id"):
        return respuesta(401, {"error": "sin sesión"})
    try:
        status, cuerpo = ruta(sesion, event)
    except Exception as e:
        log("ERROR", {"ruta": event.get("resource"), "error": str(e)})
        return respuesta(500, {"error": "error interno"})
    return respuesta(status, cuerpo)
