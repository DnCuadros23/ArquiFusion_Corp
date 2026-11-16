"""Lambdas de SFN-1 · Flujo de incidente. Cada paso recibe el incidente, lo completa, lo guarda
en t_incidentes (los Streams lo replican a Firestore) y lo devuelve a la Step Function."""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

import logica
from comun import a_dynamo, ahora_iso, de_dynamo, log

ddb = boto3.resource("dynamodb")
t_incidentes = ddb.Table(os.environ["T_INCIDENTES"])
t_maquinas = ddb.Table(os.environ["T_MAQUINAS"])
t_tecnicos = ddb.Table(os.environ["T_TECNICOS"])
t_repuestos = ddb.Table(os.environ["T_REPUESTOS"])
t_mantenimientos = ddb.Table(os.environ["T_MANTENIMIENTOS"])
sns = boto3.client("sns")
secrets = boto3.client("secretsmanager")

# Campos que solo viven en la Step Function (no se guardan) y campos que se manejan aparte.
TRANSITORIOS = {"contexto", "error_ia", "cierre_recibido", "error_espera"}
NO_PISAR = {"tenant_id", "incidente_id", "task_token"}


class IAError(Exception):
    """La IA respondió mal o no respondió: la Step Function reintenta."""


class IASinConfigurar(Exception):
    """Aún no existe el secreto de GCP: se pasa directo a la plantilla."""


# ---------------- utilidades ----------------
def evento(inc, nombre, detalle):
    inc.setdefault("linea_tiempo", []).append({"ts": ahora_iso(), "evento": nombre, "detalle": detalle})


def guardar(inc):
    """Actualiza campo por campo. No pisa grupo_causa_comun con null: otra ejecución puede haberlo puesto."""
    campos = {k: v for k, v in inc.items()
              if k not in TRANSITORIOS | NO_PISAR and not (k == "grupo_causa_comun" and v is None)}
    nombres = {f"#{i}": k for i, k in enumerate(campos)}
    valores = {f":{i}": v for i, v in enumerate(campos.values())}
    t_incidentes.update_item(
        Key={"tenant_id": inc["tenant_id"], "incidente_id": inc["incidente_id"]},
        UpdateExpression="SET " + ", ".join(f"#{i} = :{i}" for i in range(len(campos))),
        ExpressionAttributeNames=nombres,
        ExpressionAttributeValues=a_dynamo(valores),
    )
    return inc


def liberar_maquina(inc):
    try:
        t_maquinas.update_item(
            Key={"tenant_id": inc["tenant_id"], "maquina_id": inc["maquina_id"]},
            UpdateExpression="REMOVE incidente_abierto SET riesgo = :r",
            ConditionExpression="incidente_abierto = :id",
            ExpressionAttributeValues={":r": "NORMAL", ":id": inc["incidente_id"]},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise


_secreto = None


def llamar_gcp(ruta, cuerpo):
    global _secreto
    if _secreto is None:
        try:
            _secreto = json.loads(secrets.get_secret_value(SecretId=os.environ["SECRET_GCP"])["SecretString"])
        except ClientError as e:
            raise IASinConfigurar(str(e))
    req = urllib.request.Request(
        _secreto["ia_url"].rstrip("/") + ruta,
        data=json.dumps(cuerpo, default=str).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Arquifusion-Token": _secreto["token"]},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:  # HTTP 4xx/5xx, timeout o JSON inválido
        raise IAError(f"{type(e).__name__}: {e}")


def clima_actual(lat, lon):
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lon,
                                "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"})
    try:
        with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{q}", timeout=4) as r:
            return json.loads(r.read()).get("current")
    except Exception as e:
        log("WARN", {"accion": "clima", "error": str(e)})
        return None


# ---------------- pasos ----------------
def enriquecer(inc, context):
    previos = de_dynamo(t_incidentes.query(
        IndexName="por_maquina", KeyConditionExpression=Key("maquina_id").eq(inc["maquina_id"]),
        ScanIndexForward=False, Limit=6)["Items"])
    previos = [{"incidente_id": p["incidente_id"], "creado_ts": p["creado_ts"], "severidad": p.get("severidad"),
                "estado": p.get("estado"), "intervencion": (p.get("cierre") or {}).get("intervencion")}
               for p in previos if p["incidente_id"] != inc["incidente_id"]][:5]
    mants = de_dynamo(t_mantenimientos.query(
        KeyConditionExpression=Key("maquina_id").eq(inc["maquina_id"]), ScanIndexForward=False, Limit=3)["Items"])
    maquina = de_dynamo(t_maquinas.get_item(
        Key={"tenant_id": inc["tenant_id"], "maquina_id": inc["maquina_id"]}).get("Item") or {})
    horas_desde = None
    if "horas_ultimo_mant" in maquina and "horas_motor" in maquina:
        horas_desde = round(maquina["horas_motor"] - maquina["horas_ultimo_mant"], 1)

    inc["contexto"] = {"incidentes_previos": previos, "mantenimientos": mants,
                       "horas_desde_ultimo_mant": horas_desde}
    evento(inc, "ENRIQUECIDO", f"{len(previos)} incidente(s) previo(s) y {len(mants)} mantenimiento(s) revisados")
    return guardar(inc)


def analizar(inc, context):
    cuerpo = {k: v for k, v in inc.items() if k not in ("analisis_ia", "task_token")}
    res = llamar_gcp("/analizar", cuerpo)
    faltan = [k for k in ("nivel_riesgo", "resumen", "mensajes_por_rol", "especialidad_sugerida") if k not in res]
    if faltan:
        raise IAError(f"respuesta incompleta, faltan {faltan}")
    res.update(es_diagnostico=False, fuente="GEMINI")
    inc["analisis_ia"] = res
    inc["estado"] = "ANALIZADO"
    evento(inc, "ANALIZADO", f"Riesgo {res['nivel_riesgo']} según Gemini")
    return guardar(inc)


def plantilla(inc, context):
    error = (inc.get("error_ia") or {}).get("Error", "desconocido")
    inc["analisis_ia"] = logica.analisis_plantilla(inc)
    inc["estado"] = "ANALIZADO"
    evento(inc, "ANALIZADO", f"IA no disponible ({error}); se usó la plantilla de respaldo")
    log("WARN", {"accion": "plantilla_ia", "incidente_id": inc["incidente_id"], "error": error})
    return guardar(inc)


def observacion(inc, context):
    inc["estado"] = "CERRADO"
    evento(inc, "OBSERVACION", "Una sola variable fuera de lo habitual: se registra y se sigue monitoreando")
    guardar(inc)
    liberar_maquina(inc)
    return inc


def causa_comun(inc, context):
    desde = (datetime.now(timezone.utc) - timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recientes = de_dynamo(t_incidentes.query(
        KeyConditionExpression=Key("tenant_id").eq(inc["tenant_id"]),
        FilterExpression=Attr("zona").eq(inc["zona"]) & Attr("creado_ts").gte(desde))["Items"])
    otros = [i for i in recientes if i["maquina_id"] != inc["maquina_id"]]
    maquinas = {i["maquina_id"] for i in otros} | {inc["maquina_id"]}

    if len(maquinas) >= 3:
        grupo = next((i["grupo_causa_comun"] for i in otros if i.get("grupo_causa_comun")), None) \
            or f"CC-{inc['zona']}-{datetime.now(timezone.utc):%Y%m%d%H%M}"
        inc["grupo_causa_comun"] = grupo
        for o in otros:
            if not o.get("grupo_causa_comun"):
                t_incidentes.update_item(Key={"tenant_id": o["tenant_id"], "incidente_id": o["incidente_id"]},
                                         UpdateExpression="SET grupo_causa_comun = :g",
                                         ExpressionAttributeValues={":g": grupo})
        clima = clima_actual(inc["lat"], inc["lon"])
        inc.setdefault("contexto", {})["clima"] = clima
        clima_txt = (f" Clima actual: {clima.get('temperature_2m')} °C, lluvia {clima.get('precipitation')} mm, "
                     f"viento {clima.get('wind_speed_10m')} km/h." if clima else "")
        evento(inc, "POSIBLE_CAUSA_COMUN",
               f"{len(maquinas)} máquinas de {inc['zona']} con anomalías en 60 min ({grupo}).{clima_txt} "
               "Hipótesis a investigar, no confirmada.")
        return guardar(inc)
    return inc


def asignar(inc, context):
    tecnicos = de_dynamo(t_tecnicos.query(KeyConditionExpression=Key("tenant_id").eq(inc["tenant_id"]))["Items"])
    especialidad = (inc.get("analisis_ia") or {}).get("especialidad_sugerida") or "GENERAL"
    elegido, razon = logica.elegir_tecnico(tecnicos, especialidad, inc["lat"], inc["lon"])
    if elegido:
        t_tecnicos.update_item(Key={"tenant_id": inc["tenant_id"], "tecnico_id": elegido["tecnico_id"]},
                               UpdateExpression="ADD incidentes_activos :uno", ExpressionAttributeValues={":uno": 1})
        inc["tecnico_asignado"] = {"tecnico_id": elegido["tecnico_id"], "nombre": elegido.get("nombre"),
                                   "especialidad": elegido.get("especialidad"), "eta_min": elegido["eta_min"],
                                   "razon": razon}
        inc["estado"] = "ASIGNADO"
        evento(inc, "ASIGNADO", f"{elegido.get('nombre')} ({elegido['tecnico_id']}), llegada en {elegido['eta_min']} min")
    else:
        inc["tecnico_asignado"] = None
        evento(inc, "SIN_TECNICO", razon)
    return guardar(inc)


def repuestos(inc, context):
    especialidad = (inc.get("analisis_ia") or {}).get("especialidad_sugerida") or "GENERAL"
    todos = de_dynamo(t_repuestos.query(KeyConditionExpression=Key("tenant_id").eq(inc["tenant_id"]))["Items"])
    candidatos = logica.candidatos_repuesto(todos, especialidad, inc["modelo"])
    reservado = None
    for r in candidatos:
        try:
            nuevo = t_repuestos.update_item(
                Key={"tenant_id": inc["tenant_id"], "repuesto_almacen": r["repuesto_almacen"]},
                UpdateExpression="SET stock = stock - :uno", ConditionExpression="stock >= :uno",
                ExpressionAttributeValues={":uno": 1}, ReturnValues="UPDATED_NEW")
            reservado = dict(r, stock=int(nuevo["Attributes"]["stock"]))
            break
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                raise

    if reservado:
        inc["repuestos"] = [{"repuesto_id": reservado["repuesto_id"], "almacen": reservado["almacen"],
                             "cantidad": 1, "disponible": True}]
        evento(inc, "REPUESTO_RESERVADO", f"{reservado.get('nombre', reservado['repuesto_id'])} en {reservado['almacen']}")
        if reservado["stock"] < reservado.get("stock_minimo", 0):
            evento(inc, "STOCK_BAJO", f"{reservado['repuesto_id']} en {reservado['almacen']} quedó con "
                                      f"{reservado['stock']} (mínimo {reservado['stock_minimo']})")
    elif candidatos:
        r = candidatos[0]
        inc["repuestos"] = [{"repuesto_id": r["repuesto_id"], "almacen": r["almacen"], "cantidad": 1, "disponible": False}]
        evento(inc, "SIN_STOCK", f"{r['repuesto_id']} sin stock en ningún almacén: pedir reposición")
    else:
        inc["repuestos"] = []
        evento(inc, "SIN_REPUESTO", "No se identificó un repuesto compatible; lo define el técnico en sitio")
    return guardar(inc)


def notificar(inc, context):
    ia = inc.get("analisis_ia") or {}
    mensajes = ia.get("mensajes_por_rol") or {}
    tec = inc.get("tecnico_asignado") or {}
    asunto = f"[{inc['severidad']}] {inc['maquina_id']} - {inc['zona']}"  # SNS exige asunto ASCII
    pie = (f"\n\nIncidente {inc['incidente_id']}"
           f"\nTécnico: {tec.get('nombre', 'sin asignar')} (llegada {tec.get('eta_min', '-')} min)"
           f"\nEsto es una alerta para revisar, no un diagnóstico confirmado.")
    for rol in ("tecnico", "supervisor", "gerente"):
        sns.publish(
            TopicArn=os.environ["TOPIC_ALERTAS"], Subject=asunto[:100],
            Message=(mensajes.get(rol) or ia.get("resumen", "")) + pie,
            MessageAttributes={"rol": {"DataType": "String", "StringValue": rol},
                               "severidad": {"DataType": "String", "StringValue": inc["severidad"]}},
        )
    evento(inc, "NOTIFICADO", "Aviso enviado por rol según severidad")
    return guardar(inc)


def guardar_token(event, context):
    """Paso 8 (waitForTaskToken): deja el token para que la web pueda reanudar el flujo al cerrar."""
    inc = event["incidente"]
    evento(inc, "ESPERANDO_TECNICO", "En espera del cierre del técnico desde la plataforma")
    guardar(inc)
    t_incidentes.update_item(Key={"tenant_id": inc["tenant_id"], "incidente_id": inc["incidente_id"]},
                             UpdateExpression="SET task_token = :t", ExpressionAttributeValues={":t": event["token"]})
    return {"ok": True}


def cerrar(inc, context):
    datos = inc.get("cierre_recibido") or {}
    por_tiempo = "error_espera" in inc
    ahora = ahora_iso()
    minutos = datos.get("minutos_detenida")
    if minutos is None:
        minutos = round((logica.parse_ts(ahora) - logica.parse_ts(inc["creado_ts"])).total_seconds() / 60)
    inc["cierre"] = {
        "cerrado_ts": ahora,
        "minutos_detenida": minutos,
        "intervencion": datos.get("intervencion") or ("Cerrado por tiempo de espera" if por_tiempo else ""),
        "componentes_reemplazados": datos.get("componentes_reemplazados", []),
        "falla_confirmada": bool(datos.get("falla_confirmada", False)),
    }
    inc["estado"] = "CERRADO"
    evento(inc, "CERRADO", f"Intervención registrada; {minutos} min de detención")
    guardar(inc)
    t_incidentes.update_item(Key={"tenant_id": inc["tenant_id"], "incidente_id": inc["incidente_id"]},
                             UpdateExpression="REMOVE task_token")

    tec = inc.get("tecnico_asignado")
    if tec:
        t_tecnicos.update_item(Key={"tenant_id": inc["tenant_id"], "tecnico_id": tec["tecnico_id"]},
                               UpdateExpression="ADD incidentes_activos :menos", ExpressionAttributeValues={":menos": -1})
    t_mantenimientos.put_item(Item=a_dynamo({
        "maquina_id": inc["maquina_id"], "fecha": ahora, "tipo": "CORRECTIVO", "incidente_id": inc["incidente_id"],
        "componentes": inc["cierre"]["componentes_reemplazados"], "tecnico_id": (tec or {}).get("tecnico_id"),
        "falla_confirmada": inc["cierre"]["falla_confirmada"],
    }))
    liberar_maquina(inc)
    return inc
