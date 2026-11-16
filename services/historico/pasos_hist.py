"""Lambdas de SFN-3: descargar fuentes públicas y guardar los patrones aprendidos."""
import io
import json
import os
import urllib.parse
import urllib.request
import zipfile
from datetime import date, timedelta

import boto3
from boto3.dynamodb.conditions import Key

import hist
from comun import a_dynamo, ahora_iso, de_dynamo, log

URL_AI4I = "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip"
s3 = boto3.client("s3")
athena = boto3.client("athena")
ddb = boto3.resource("dynamodb")
BUCKET = os.environ["BUCKET_DATALAKE"]


def _get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read()


def descargar(event, context):
    # 1) AI4I 2020: dataset público de mantenimiento predictivo (10 000 registros con etiqueta de falla)
    with zipfile.ZipFile(io.BytesIO(_get(URL_AI4I))) as z:
        nombre = next(n for n in z.namelist() if n.endswith(".csv"))
        limpio, filas, fallas = hist.limpiar_ai4i(z.read(nombre).decode("utf-8-sig"))
    s3.put_object(Bucket=BUCKET, Key="raw/historico/ai4i/ai4i2020.csv", Body=limpio.encode("utf-8"),
                  ContentType="text/csv")

    # 2) Clima diario de los últimos 30 días en cada zona (para investigar causas comunes)
    maquinas = de_dynamo(ddb.Table(os.environ["T_MAQUINAS"]).query(
        KeyConditionExpression=Key("tenant_id").eq(os.environ.get("TENANT", "MINA_SUR")))["Items"])
    zonas = {}
    for m in maquinas:
        zonas.setdefault(m["zona"], []).append((m["lat"], m["lon"]))
    hoy = date.today()
    dias = 0
    for zona, puntos in zonas.items():
        lat = sum(p[0] for p in puntos) / len(puntos)
        lon = sum(p[1] for p in puntos) / len(puntos)
        q = urllib.parse.urlencode({"latitude": round(lat, 4), "longitude": round(lon, 4),
                                    "start_date": (hoy - timedelta(days=31)).isoformat(),
                                    "end_date": (hoy - timedelta(days=1)).isoformat(),
                                    "daily": "temperature_2m_max,precipitation_sum,wind_speed_10m_max",
                                    "timezone": "America/Lima"})
        try:
            d = json.loads(_get(f"https://archive-api.open-meteo.com/v1/archive?{q}", timeout=15))["daily"]
        except Exception as e:  # el clima es complementario: no detiene el flujo
            log("WARN", {"accion": "clima_historico", "zona": zona, "error": str(e)})
            continue
        lineas = [json.dumps({"zona": zona, "fecha": t, "temp_max_c": tm, "lluvia_mm": ll, "viento_max_kmh": v})
                  for t, tm, ll, v in zip(d["time"], d["temperature_2m_max"], d["precipitation_sum"],
                                          d["wind_speed_10m_max"])]
        s3.put_object(Bucket=BUCKET, Key=f"raw/historico/clima/zona={zona}/clima.json",
                      Body="\n".join(lineas).encode("utf-8"))
        dias += len(lineas)

    resultado = {"ai4i_registros": filas, "ai4i_fallas": fallas, "clima_zonas": len(zonas), "clima_dias": dias}
    log("INFO", {"accion": "descarga_historico", **resultado})
    return resultado


def actualizar_umbrales(event, context):
    qid = event["athena"]["QueryExecution"]["QueryExecutionId"]
    items = hist.umbrales(hist.filas_athena(athena.get_query_results(QueryExecutionId=qid)))
    tabla = ddb.Table(os.environ["T_UMBRALES"])
    ahora = ahora_iso()
    with tabla.batch_writer() as lote:
        for i in items:
            lote.put_item(Item=a_dynamo({**i, "actualizado_ts": ahora}))
    log("INFO", {"accion": "umbrales_actualizados", "variables": [i["variable"] for i in items]})
    return {"patrones": [i["interpretacion"] for i in items]}
