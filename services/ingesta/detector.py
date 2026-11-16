"""Detector de anomalías por máquina (lógica pura, sin AWS).

Cada variable mantiene una media y varianza móviles exponenciales (EWMA) como "comportamiento
habitual" de esa máquina. Una lectura se desvía si |z| > Z_UMBRAL; la variable cuenta como
anómala cuando se desvía en RACHA_MIN lecturas seguidas (persistencia, no un pico aislado).
La dispersión se fija al terminar el calentamiento y las lecturas desviadas no actualizan la
media, para que una degradación gradual no se "normalice" sola.

Severidad (contracts/incidente.schema.json):
  OBSERVACION = 1 variable anómala · MEDIA = 2 · CRITICA = 3+ o un valor fuera del límite físico.
Esto es una señal para revisar, nunca un diagnóstico.
"""
import math

from contrato import parse_ts

VARIABLES = ("temp_motor_c", "vibracion_mm_s", "presion_hid_bar", "combustible_l_h")
ALFA = 0.05               # EWMA tras el calentamiento (memoria ~20 lecturas)
Z_UMBRAL = 2.5
RACHA_MIN = 3
CALENTAMIENTO = 20          # lecturas necesarias antes de evaluar (promedio exacto en ese tramo)
PISO_RELATIVO = 0.02        # desviación mínima = 2 % de la media (evita falsos positivos por poco ruido)
LIMITES_FISICOS = {         # superar esto es CRITICA aunque no haya historial
    "temp_motor_c": 115.0,
    "vibracion_mm_s": 12.0,
    "presion_hid_bar": 400.0,
}


def _nuevo(x):
    return {"media": x, "varianza": 0.0, "n": 0, "racha": 0, "desde": None}


def _actualizar(s, x):
    # Calentamiento: media y varianza exactas (alfa = 1/(n+1)).
    # Después: solo la media sigue aprendiendo (EWMA); la dispersión queda fija, así una
    # deriva lenta no "ensancha" lo normal hasta esconderse.
    if s["n"] < CALENTAMIENTO:
        a = 1.0 / (s["n"] + 1)
        diff = x - s["media"]
        s["media"] += a * diff
        s["varianza"] = (1 - a) * (s["varianza"] + a * diff * diff)
    else:
        s["media"] += ALFA * (x - s["media"])
    s["n"] += 1


def _desviacion(s):
    return max(math.sqrt(max(s["varianza"], 0.0)), PISO_RELATIVO * abs(s["media"]), 1e-6)


def _minutos(desde, hasta):
    if not desde:
        return 0.0
    return round((parse_ts(hasta) - parse_ts(desde)).total_seconds() / 60, 1)


def evaluar(lectura, stats):
    """Evalúa una lectura contra las estadísticas previas de su máquina.

    Devuelve (resultado, stats_nuevas). resultado es None si no hay anomalía, o
    {"severidad": ..., "variables_anomalas": [...]}.
    """
    nuevas = {k: dict(v) for k, v in (stats or {}).items()}
    anomalas, fuera_limite = [], []

    for var in VARIABLES:
        if lectura.get(var) is None:
            continue
        x = float(lectura[var])
        s = nuevas.get(var) or _nuevo(x)
        z = (x - s["media"]) / _desviacion(s) if s["n"] else 0.0

        if var in LIMITES_FISICOS and x > LIMITES_FISICOS[var]:
            fuera_limite.append(var)
            s["racha"] += 1
            s["desde"] = s["desde"] or lectura["ts"]
        elif s["n"] < CALENTAMIENTO:
            _actualizar(s, x)
        elif abs(z) > Z_UMBRAL:
            s["racha"] += 1
            s["desde"] = s["desde"] or lectura["ts"]
        else:
            s["racha"], s["desde"] = 0, None
            _actualizar(s, x)

        if var in fuera_limite or s["racha"] >= RACHA_MIN:
            anomalas.append({
                "variable": var,
                "valor": round(x, 2),
                "media_habitual": round(s["media"], 2),
                "z": round(z, 2),
                "minutos_persistente": _minutos(s["desde"], lectura["ts"]),
            })
        nuevas[var] = s

    if not anomalas:
        return None, nuevas
    if fuera_limite or len(anomalas) >= 3:
        severidad = "CRITICA"
    elif len(anomalas) == 2:
        severidad = "MEDIA"
    else:
        severidad = "OBSERVACION"
    return {"severidad": severidad, "variables_anomalas": anomalas}, nuevas
