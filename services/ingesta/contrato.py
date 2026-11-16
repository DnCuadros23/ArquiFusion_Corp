"""Validación de una lectura según contracts/telemetria.schema.json (sin dependencias externas)."""
import re
from datetime import datetime

REQUERIDOS = ("tenant_id", "maquina_id", "modelo", "ts", "zona", "lat", "lon", "estado", "horas_motor")
NUMERICOS = ("lat", "lon", "horas_motor", "temp_motor_c", "vibracion_mm_s", "presion_hid_bar",
             "combustible_l_h", "carga_t", "velocidad_kmh", "rpm")
NO_NEGATIVOS = ("horas_motor", "vibracion_mm_s", "presion_hid_bar", "combustible_l_h",
                "carga_t", "velocidad_kmh", "rpm")
TEXTOS = ("tenant_id", "maquina_id", "modelo", "ts", "zona", "estado")
ESTADOS = {"OPERANDO", "RALENTI", "DETENIDA", "MANTENIMIENTO"}
PERMITIDOS = set(REQUERIDOS) | set(NUMERICOS)
PATRON_ID = re.compile(r"^[A-Z]{3}-[0-9]{3}$")


def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def validar(lectura):
    """Devuelve la lista de errores (vacía si la lectura es válida)."""
    if not isinstance(lectura, dict):
        return ["la lectura debe ser un objeto JSON"]
    errores = [f"falta '{c}'" for c in REQUERIDOS if c not in lectura]
    errores += [f"campo no permitido '{c}'" for c in lectura if c not in PERMITIDOS]
    for c in TEXTOS:
        if c in lectura and not isinstance(lectura[c], str):
            errores.append(f"'{c}' debe ser texto")
    for c in NUMERICOS:
        v = lectura.get(c)
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            errores.append(f"'{c}' debe ser numérico")
        elif c in NO_NEGATIVOS and v < 0:
            errores.append(f"'{c}' no puede ser negativo")
    if errores:
        return errores
    if not PATRON_ID.match(lectura["maquina_id"]):
        errores.append("'maquina_id' debe tener el formato ABC-123")
    if lectura["estado"] not in ESTADOS:
        errores.append(f"'estado' debe ser uno de {sorted(ESTADOS)}")
    if not -90 <= lectura["lat"] <= 90 or not -180 <= lectura["lon"] <= 180:
        errores.append("coordenadas fuera de rango")
    try:
        parse_ts(lectura["ts"])
    except ValueError:
        errores.append("'ts' debe ser ISO 8601 (ej. 2026-11-14T15:00:00Z)")
    return errores
