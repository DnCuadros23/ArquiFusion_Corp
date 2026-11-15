"""Simulador de la flota de ArquiFusion Fleet (datos simulados).

Cada ronda manda una lectura por máquina (las 30 de seed/maquinas.json) a POST {INGESTA_URL}/telemetria.

Como script:
    python simulador.py --escenario normal --rondas 25 --rapido          # calentamiento del detector
    python simulador.py --escenario degradacion --minutos 10 --rapido
    python simulador.py --escenario productividad --simular-horas 24 --rondas 96 --intervalo 3
    python simulador.py --escenario causa_comun --rondas 3 --dry-run     # no envía, solo muestra

Como Lambda:
    handler({"escenario": "normal"}, context)                             # 1 ronda (regla de EventBridge)
    handler({"escenario": "degradacion", "rondas": 10, "intervalo_s": 5}, context)

La URL y la API key salen de --url/--key, de las variables INGESTA_URL y API_KEY o del .env de la raíz.
Solo usa la librería estándar de Python.
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TENANT = "MINA_SUR"
ESCENARIOS = ("normal", "degradacion", "combustible", "causa_comun", "productividad")

# Rangos normales por modelo (docs/tareas/ENRIQUE.md) y valores de trabajo típicos.
MODELOS = {
    "EXC-320": {"temp_motor_c": (85, 92), "vibracion_mm_s": (3.5, 4.5), "presion_hid_bar": (300, 330),
                "combustible_l_h": (35, 40), "carga_t": 28.0, "velocidad_kmh": 6.0, "rpm": 1850},
    "CAM-793": {"temp_motor_c": (88, 95), "vibracion_mm_s": (3.0, 4.0), "presion_hid_bar": (180, 210),
                "combustible_l_h": (90, 110), "carga_t": 220.0, "velocidad_kmh": 28.0, "rpm": 1700},
    "CAR-994": {"temp_motor_c": (86, 93), "vibracion_mm_s": (3.5, 4.5), "presion_hid_bar": (260, 290),
                "combustible_l_h": (50, 60), "carga_t": 35.0, "velocidad_kmh": 12.0, "rpm": 1800},
}
SENSORES = ("temp_motor_c", "vibracion_mm_s", "presion_hid_bar", "combustible_l_h")
# Ruido de cada lectura, como fracción del valor habitual. Es pequeño a propósito: el detector
# considera normal hasta ±5 % de la media de cada máquina.
RUIDO = {"temp_motor_c": 0.003, "vibracion_mm_s": 0.012, "presion_hid_bar": 0.008, "combustible_l_h": 0.012}

# --- protagonistas de cada escenario
MAQ_DEGRADACION = "EXC-007"
MAQ_COMBUSTIBLE = "CAM-004"
MAQ_OCIOSA = "CAR-003"
MAQ_SOBREUSADA = "CAM-010"
# Cinco máquinas de TAJO_NORTE con cambios distintos; cada una empieza una ronda después de la anterior.
CAUSA_COMUN = [
    ("EXC-004", {"temp_motor_c": 1.08, "vibracion_mm_s": 1.30}),
    ("EXC-005", {"vibracion_mm_s": 1.35, "combustible_l_h": 1.15}),
    ("EXC-006", {"temp_motor_c": 1.09, "combustible_l_h": 1.18}),
    ("CAM-001", {"presion_hid_bar": 0.85, "temp_motor_c": 1.08}),
    ("CAR-001", {"vibracion_mm_s": 1.30, "presion_hid_bar": 0.86}),
]
TURNO_UTC = (11, 25)   # 06:00–20:00 en Lima (UTC−5): horas en que la flota trabaja (escenario productividad)


def cargar_maquinas():
    for ruta in (AQUI / "maquinas.json", AQUI.parent / "seed" / "maquinas.json"):
        if ruta.exists():
            return json.loads(ruta.read_text(encoding="utf-8"))
    raise FileNotFoundError("No encuentro maquinas.json (ni junto al simulador ni en ../seed)")


def habitual(maquina):
    """Valores habituales de una máquina: fijos para cada maquina_id, dentro del rango de su modelo."""
    rng = random.Random(maquina["maquina_id"])
    base = {}
    for var in SENSORES:
        lo, hi = MODELOS[maquina["modelo"]][var]
        margen = (hi - lo) * 0.2
        base[var] = rng.uniform(lo + margen, hi - margen)
    if maquina["maquina_id"] == MAQ_DEGRADACION:
        base["temp_motor_c"] = 90.0
    return base


def _factor_degradacion(paso):
    """Vibración y combustible de EXC-007: suben poco en los pasos 1–2 y claramente desde el 3,
    para que crucen el umbral en la misma lectura que la temperatura (+2 °C por lectura)."""
    return 1 + 0.01 * paso if paso <= 2 else 1.08 + 0.02 * (paso - 3)


def _en_turno(ts, horas_extra=0):
    h = ts.hour + ts.minute / 60
    ini, fin = TURNO_UTC[0] - horas_extra / 2, TURNO_UTC[1] + horas_extra / 2
    return ini <= h < fin or ini <= h + 24 < fin


def lectura(maquina, escenario, paso, ts, horas_desde_inicio=0.0):
    """Arma una lectura válida según contracts/telemetria.schema.json. `paso` empieza en 1."""
    mid, modelo = maquina["maquina_id"], maquina["modelo"]
    m = MODELOS[modelo]
    v = {var: x * (1 + random.uniform(-RUIDO[var], RUIDO[var])) for var, x in habitual(maquina).items()}
    estado, carga, vel, rpm = "OPERANDO", m["carga_t"], m["velocidad_kmh"], m["rpm"]

    if escenario == "degradacion" and mid == MAQ_DEGRADACION:
        f = _factor_degradacion(paso)
        v["temp_motor_c"] = min(v["temp_motor_c"] + 2.0 * paso, 118.0)
        v["vibracion_mm_s"] *= f
        v["combustible_l_h"] *= f
    elif escenario == "combustible" and mid == MAQ_COMBUSTIBLE:
        v["combustible_l_h"] *= 1.35                      # misma carga, 35 % más consumo
    elif escenario == "causa_comun":
        for i, (afectada, cambios) in enumerate(CAUSA_COMUN):
            if mid == afectada and paso > i:
                for var, factor in cambios.items():
                    v[var] *= factor
    elif escenario == "productividad":
        if mid == MAQ_OCIOSA:
            estado = "OPERANDO" if paso % 10 == 0 else "RALENTI"
        elif mid == MAQ_SOBREUSADA:
            estado = "OPERANDO" if _en_turno(ts, horas_extra=8) else "DETENIDA"     # 22 h al día
        else:
            estado = "OPERANDO" if _en_turno(ts) else "DETENIDA"                    # 14 h al día

    if estado == "RALENTI":         # motor encendido sin trabajar: gasta combustible y no produce
        v["combustible_l_h"] *= 0.25
        carga, vel, rpm = 0.0, 0.0, 700
    elif estado == "DETENIDA":      # motor apagado: los sensores no reportan (se omiten, no se manda 0)
        v, carga, vel, rpm = {}, 0.0, 0.0, 0

    activo = estado != "DETENIDA"
    r = {
        "tenant_id": TENANT, "maquina_id": mid, "modelo": modelo,
        "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "zona": maquina["zona"],
        "lat": round(maquina["lat"] + (random.uniform(-2e-4, 2e-4) if vel else 0), 5),
        "lon": round(maquina["lon"] + (random.uniform(-2e-4, 2e-4) if vel else 0), 5),
        "estado": estado,
        "horas_motor": round(maquina["horas_motor"] + (horas_desde_inicio if activo else 0), 2),
        "carga_t": round(carga * random.uniform(0.95, 1.05), 1) if carga else 0.0,
        "velocidad_kmh": round(vel * random.uniform(0.9, 1.1), 1) if vel else 0.0,
        "rpm": round(rpm * random.uniform(0.98, 1.02)) if rpm else 0,
    }
    for var, x in v.items():
        r[var] = round(x, 2)
    return r


def ronda(maquinas, escenario, paso, ts, horas_desde_inicio=0.0):
    return [lectura(m, escenario, paso, ts, horas_desde_inicio) for m in maquinas]


def enviar(url, key, lecturas):
    req = urllib.request.Request(
        url.rstrip("/") + "/telemetria", data=json.dumps(lecturas).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "x-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:300]}


def ejecutar(url, key, escenario="normal", rondas=1, intervalo_s=60.0, simular_horas=None,
             paso_inicial=1, dry_run=False, salida=print):
    """Manda `rondas` rondas. Con `simular_horas`, los `ts` se reparten en las últimas N horas."""
    if escenario not in ESCENARIOS:
        raise ValueError(f"escenario debe ser uno de {ESCENARIOS}")
    maquinas = cargar_maquinas()
    inicio = datetime.now(timezone.utc)
    total = 0
    for i in range(rondas):
        paso = paso_inicial + i
        if simular_horas:
            ts = inicio - timedelta(hours=simular_horas) + timedelta(hours=simular_horas * (i + 1) / rondas)
            horas = simular_horas * (i + 1) / rondas
        else:
            ts = datetime.now(timezone.utc)
            horas = (ts - inicio).total_seconds() / 3600
        lecturas = ronda(maquinas, escenario, paso, ts, horas)
        if dry_run:
            salida(f"[{escenario}] ronda {i + 1}/{rondas} (sin enviar): {json.dumps(lecturas[6], ensure_ascii=False)}")
        else:
            estado, cuerpo = enviar(url, key, lecturas)
            total += cuerpo.get("encoladas", 0) if isinstance(cuerpo, dict) else 0
            salida(json.dumps({"tipo": "INFO" if estado == 202 else "ERROR", "escenario": escenario,
                               "ronda": i + 1, "de": rondas, "http": estado, "respuesta": cuerpo},
                              ensure_ascii=False))
        if i < rondas - 1 and intervalo_s > 0:
            time.sleep(intervalo_s)
    return {"escenario": escenario, "rondas": rondas, "encoladas": total}


def handler(event, context):
    """Entrada como Lambda. La regla de EventBridge manda {"escenario": "normal"} cada minuto."""
    event = event or {}
    return ejecutar(
        os.environ["INGESTA_URL"], os.environ["API_KEY"],
        escenario=event.get("escenario", "normal"),
        rondas=int(event.get("rondas", 1)),
        intervalo_s=float(event.get("intervalo_s", 5)),
        simular_horas=event.get("simular_horas"),
        paso_inicial=int(event.get("paso_inicial", 1)),
    )


def _leer_env():
    ruta = AQUI.parent / ".env"
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                k, val = linea.split("=", 1)
                os.environ.setdefault(k.strip(), val.strip())


def main():
    _leer_env()
    p = argparse.ArgumentParser(description="Simulador de telemetría de ArquiFusion Fleet")
    p.add_argument("--url", default=os.environ.get("INGESTA_URL"), help="URL base de ingesta (sin /telemetria)")
    p.add_argument("--key", default=os.environ.get("API_KEY"), help="API key de ingesta")
    p.add_argument("--escenario", default="normal", choices=ESCENARIOS)
    p.add_argument("--minutos", type=float, default=10, help="duración real de la ejecución")
    p.add_argument("--rondas", type=int, help="número de rondas (tiene prioridad sobre --minutos)")
    p.add_argument("--intervalo", type=float, help="segundos entre rondas (por defecto 60)")
    p.add_argument("--rapido", action="store_true", help="una ronda cada 5 s (para la demo)")
    p.add_argument("--simular-horas", type=float, help="reparte los ts en las últimas N horas")
    p.add_argument("--dry-run", action="store_true", help="no envía; muestra una lectura por ronda")
    a = p.parse_args()

    intervalo = a.intervalo if a.intervalo is not None else (5.0 if a.rapido else 60.0)
    rondas = a.rondas or max(1, round(a.minutos * 60 / max(intervalo, 1)))
    if not a.dry_run and not (a.url and a.key):
        sys.exit("Falta --url/--key (o INGESTA_URL y API_KEY en el entorno o en el .env de la raíz)")
    url = (a.url or "").removesuffix("/telemetria")
    print(ejecutar(url, a.key, a.escenario, rondas, 0 if a.dry_run else intervalo, a.simular_horas,
                   dry_run=a.dry_run))


if __name__ == "__main__":
    main()
