"""Decisiones de SFN-1 como funciones puras (se prueban sin AWS)."""
import math
from datetime import datetime

VELOCIDAD_KMH = 25          # desplazamiento promedio de un técnico dentro de la operación
PENALIDAD_POR_INCIDENTE = 15  # minutos extra por cada incidente que el técnico ya atiende

RIESGO_POR_SEVERIDAD = {"CRITICA": "ALTO", "MEDIA": "MEDIO", "OBSERVACION": "BAJO"}
ESPECIALIDAD_POR_VARIABLE = {
    "temp_motor_c": "MOTOR",
    "combustible_l_h": "MOTOR",
    "vibracion_mm_s": "MOTOR",
    "presion_hid_bar": "HIDRAULICO",
}
NOMBRE_VARIABLE = {
    "temp_motor_c": "temperatura del motor",
    "vibracion_mm_s": "vibración",
    "presion_hid_bar": "presión hidráulica",
    "combustible_l_h": "consumo de combustible",
}
CAUSAS_A_REVISAR = {
    "temp_motor_c": "Sistema de enfriamiento",
    "vibracion_mm_s": "Montajes y rodamientos",
    "presion_hid_bar": "Circuito y sellos hidráulicos",
    "combustible_l_h": "Inyección y filtro de aire",
}


def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def distancia_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def eta_min(tecnico, lat, lon):
    viaje = distancia_km(lat, lon, tecnico["lat"], tecnico["lon"]) / VELOCIDAD_KMH * 60
    return viaje + PENALIDAD_POR_INCIDENTE * tecnico.get("incidentes_activos", 0)


def elegir_tecnico(tecnicos, especialidad, lat, lon):
    """Devuelve (tecnico_con_eta | None, razon). La especialidad es obligatoria; GENERAL es el respaldo."""
    disponibles = [t for t in tecnicos if t.get("disponible", True)]
    no_disponibles = [t["tecnico_id"] for t in tecnicos if not t.get("disponible", True)]
    exactos = [t for t in disponibles if t.get("especialidad") == especialidad]
    if exactos:
        candidatos, criterio = exactos, f"Especialidad {especialidad} coincide"
    else:
        candidatos = [t for t in disponibles if t.get("especialidad") == "GENERAL"]
        criterio = f"No hay {especialidad} disponible; se asigna técnico GENERAL"
    if not candidatos:
        return None, f"No hay técnicos disponibles de {especialidad} ni GENERAL. Requiere decisión del supervisor."

    orden = sorted(candidatos, key=lambda t: eta_min(t, lat, lon))
    elegido = orden[0]
    eta = round(eta_min(elegido, lat, lon))
    km = round(distancia_km(lat, lon, elegido["lat"], elegido["lon"]), 1)
    razon = (f"{criterio}; disponible; a {km} km; {elegido.get('incidentes_activos', 0)} incidente(s) activo(s); "
             f"llegada estimada {eta} min.")
    alternativas = [f"{t['tecnico_id']} ({round(eta_min(t, lat, lon))} min)" for t in orden[1:3]]
    if alternativas:
        razon += f" Alternativas: {', '.join(alternativas)}."
    if no_disponibles:
        razon += f" No disponibles: {', '.join(no_disponibles)}."
    return dict(elegido, eta_min=eta), razon


def candidatos_repuesto(repuestos, especialidad, modelo):
    """Repuestos compatibles con el modelo y la especialidad, primero los de mayor stock."""
    compatibles = [r for r in repuestos
                   if modelo in r.get("modelos_compatibles", [])
                   and (especialidad == "GENERAL" or r.get("especialidad") == especialidad)]
    return sorted(compatibles, key=lambda r: -r.get("stock", 0))


def analisis_plantilla(incidente):
    """analisis_ia de respaldo cuando la IA no responde. Mismo formato, fuente PLANTILLA."""
    variables = incidente.get("variables_anomalas", [])
    principal = variables[0]["variable"] if variables else None
    detalle = "; ".join(
        f"{NOMBRE_VARIABLE.get(v['variable'], v['variable'])} {v['valor']} (habitual {v['media_habitual']}, z {v['z']})"
        for v in variables)
    nombres = ", ".join(NOMBRE_VARIABLE.get(v["variable"], v["variable"]) for v in variables) or "variables"
    maquina, zona, sev = incidente["maquina_id"], incidente["zona"], incidente["severidad"]
    return {
        "nivel_riesgo": RIESGO_POR_SEVERIDAD.get(sev, "MEDIO"),
        "resumen": (f"{maquina} muestra {nombres} fuera de su comportamiento habitual. "
                    "Merece revisión; los datos no permiten afirmar una causa."),
        "posibles_causas_a_revisar": [CAUSAS_A_REVISAR[v["variable"]] for v in variables
                                      if v["variable"] in CAUSAS_A_REVISAR] or ["Inspección general"],
        "especialidad_sugerida": ESPECIALIDAD_POR_VARIABLE.get(principal, "GENERAL"),
        "mensajes_por_rol": {
            "tecnico": f"{maquina} ({zona}): {detalle}. Revisar en sitio.",
            "supervisor": f"{maquina} con anomalía {sev}. Ver asignación y avance en la plataforma.",
            "gerente": f"Una máquina de {zona} está en revisión ({sev}).",
        },
        "es_diagnostico": False,
        "fuente": "PLANTILLA",
    }
