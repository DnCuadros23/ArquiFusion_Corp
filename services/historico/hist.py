"""Lógica pura de SFN-3 · Aprendizaje histórico (sin AWS)."""
import csv
import io

# Encabezados originales de AI4I 2020 → nombres aptos para Athena
COLUMNAS_AI4I = {
    "UDI": "udi", "Product ID": "producto", "Type": "calidad",
    "Air temperature [K]": "temp_aire_k", "Process temperature [K]": "temp_proceso_k",
    "Rotational speed [rpm]": "rpm", "Torque [Nm]": "torque_nm", "Tool wear [min]": "desgaste_min",
    "Machine failure": "falla", "TWF": "falla_desgaste", "HDF": "falla_disipacion", "PWF": "falla_potencia",
    "OSF": "falla_sobrecarga", "RNF": "falla_aleatoria",
}

# Variables que compara la consulta de Athena (serverless.yml) entre registros con falla y normales
VARIABLES = {
    "dif_temperatura_k": "la diferencia de temperatura proceso-aire",
    "rpm": "la velocidad de giro",
    "torque_nm": "el torque",
    "desgaste_min": "el desgaste acumulado",
    "potencia_w": "la potencia",
}


def limpiar_ai4i(texto_csv):
    """Quita el BOM y renombra columnas. Devuelve (csv_limpio, filas, fallas)."""
    lector = csv.DictReader(io.StringIO(texto_csv.lstrip("﻿")))
    faltan = set(COLUMNAS_AI4I) - set(lector.fieldnames or [])
    if faltan:
        raise ValueError(f"el CSV de AI4I cambió de formato; faltan columnas {sorted(faltan)}")
    salida = io.StringIO()
    escritor = csv.DictWriter(salida, fieldnames=list(COLUMNAS_AI4I.values()), lineterminator="\n")
    escritor.writeheader()
    filas = fallas = 0
    for fila in lector:
        escritor.writerow({nuevo: fila[viejo] for viejo, nuevo in COLUMNAS_AI4I.items()})
        filas += 1
        fallas += fila["Machine failure"] == "1"
    return salida.getvalue(), filas, fallas


def filas_athena(resultado):
    """Respuesta de GetQueryResults → lista de dicts (la primera fila es el encabezado)."""
    filas = resultado["ResultSet"]["Rows"]
    encabezado = [c.get("VarCharValue") for c in filas[0]["Data"]]
    return [dict(zip(encabezado, (c.get("VarCharValue") for c in f["Data"]))) for f in filas[1:]]


def umbrales(filas):
    """Compara medias con falla vs. normal. Son patrones de referencia, no reglas de diagnóstico."""
    por_clase = {str(f["falla"]): f for f in filas}
    normal, falla = por_clase.get("0"), por_clase.get("1")
    if not normal or not falla:
        raise ValueError("la consulta no devolvió registros normales y con falla")
    items = []
    for var, nombre in VARIABLES.items():
        n, f = float(normal[var]), float(falla[var])
        cambio = (f / n - 1) * 100 if n else 0.0
        items.append({
            "modelo": "REFERENCIA_AI4I", "variable": var, "nombre": nombre.split(" ", 1)[1],
            "media_normal": round(n, 2), "media_con_falla": round(f, 2), "cambio_pct": round(cambio, 1),
            "registros_normales": int(normal["registros"]), "registros_con_falla": int(falla["registros"]),
            "interpretacion": f"En registros con falla, {nombre} es {abs(round(cambio))} % "
                              f"{'mayor' if cambio >= 0 else 'menor'} que en operación normal.",
            "fuente": "AI4I 2020 Predictive Maintenance Dataset (UCI)",
        })
    return sorted(items, key=lambda i: -abs(i["cambio_pct"]))
