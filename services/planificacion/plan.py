"""Análisis de SFN-2 como funciones puras (se prueban sin AWS).

Cada análisis recibe máquinas y sus lecturas de las últimas 24 h (de datos), y devuelve hallazgos
ordenados por prioridad. Solo se compara una máquina contra otras de su MISMO modelo.
"""
from statistics import mean, median

INTERVALO_PREVENTIVO_H = 500      # horas entre mantenimientos (por defecto para todos los modelos)
UMBRAL_COMBUSTIBLE = 0.20         # +20 % sobre la mediana del modelo
UTILIZACION_BAJA = 0.30           # < 30 % del tiempo operando
HORAS_EXCESIVAS = 20              # > 20 h operando en el día
COSTO_ALTO = 1.30                 # costo por tonelada > 1.3 × mediana del modelo
CONSUMO_IRREGULAR = 3             # 3+ usos de un repuesto en 7 días


def _por_modelo(filas):
    grupos = {}
    for f in filas:
        grupos.setdefault(f["modelo"], []).append(f)
    return grupos


def preventivo(maquinas, lecturas):
    """Horas desde el último mantenimiento, ajustadas por la carga relativa a su modelo."""
    carga_media = {m["maquina_id"]: mean([l["carga_t"] for l in lecturas.get(m["maquina_id"], [])
                                           if l.get("carga_t") is not None] or [0]) for m in maquinas}
    filas = []
    for modelo, grupo in _por_modelo(maquinas).items():
        cargas = [carga_media[m["maquina_id"]] for m in grupo if carga_media[m["maquina_id"]] > 0]
        ref = median(cargas) if cargas else 0
        for m in grupo:
            if "horas_ultimo_mant" not in m:
                continue
            factor = min(max(carga_media[m["maquina_id"]] / ref, 0.8), 1.3) if ref else 1.0
            efectivas = (m["horas_motor"] - m["horas_ultimo_mant"]) * factor
            avance = efectivas / INTERVALO_PREVENTIVO_H
            estado = "VENCIDO" if avance >= 1 else "PRONTO" if avance >= 0.85 else "OK"
            filas.append({"maquina_id": m["maquina_id"], "modelo": modelo, "zona": m.get("zona"),
                          "horas_desde_mant": round(m["horas_motor"] - m["horas_ultimo_mant"], 1),
                          "factor_carga": round(factor, 2), "avance_pct": round(avance * 100),
                          "horas_restantes": round(max(INTERVALO_PREVENTIVO_H - efectivas, 0)),
                          "estado": estado})
    return sorted(filas, key=lambda f: -f["avance_pct"])


def combustible(maquinas, lecturas):
    """L por tonelada (o L/h si no hay carga) contra la mediana de su modelo, con tendencia."""
    filas = []
    for modelo, grupo in _por_modelo(maquinas).items():
        metrica = {}
        for m in grupo:
            ops = [l for l in lecturas.get(m["maquina_id"], [])
                   if l.get("estado") == "OPERANDO" and l.get("combustible_l_h") is not None]
            if len(ops) < 4:
                continue
            con_carga = [l for l in ops if (l.get("carga_t") or 0) > 0]
            if con_carga:
                valores = [l["combustible_l_h"] / l["carga_t"] for l in con_carga]
                unidad = "L/h por t"
            else:
                valores = [l["combustible_l_h"] for l in ops]
                unidad = "L/h"
            mitad = len(valores) // 2
            inicio = mean(valores[:mitad])
            tendencia = mean(valores[mitad:]) / inicio - 1 if inicio else 0
            metrica[m["maquina_id"]] = (mean(valores), tendencia, unidad, m)
        if len(metrica) < 2:
            continue  # no hay contra quién comparar
        ref = median(v[0] for v in metrica.values())
        for mid, (valor, tendencia, unidad, m) in metrica.items():
            desvio = valor / ref - 1 if ref else 0
            if desvio > UMBRAL_COMBUSTIBLE:
                filas.append({"maquina_id": mid, "modelo": modelo, "zona": m.get("zona"), "unidad": unidad,
                              "valor": round(valor, 3), "mediana_modelo": round(ref, 3),
                              "desvio_pct": round(desvio * 100), "tendencia_pct": round(tendencia * 100),
                              "nota": "Comparado con máquinas del mismo modelo y su carga; no demuestra una falla."})
    return sorted(filas, key=lambda f: -f["desvio_pct"])


def utilizacion(maquinas, lecturas, horas_ventana=24):
    """Ociosas, sobreusadas y con costo por tonelada alto respecto a su modelo."""
    base = []
    for m in maquinas:
        ls = lecturas.get(m["maquina_id"], [])
        if not ls:
            continue
        pct = sum(l.get("estado") == "OPERANDO" for l in ls) / len(ls)
        horas = pct * horas_ventana
        toneladas = sum(l.get("carga_t") or 0 for l in ls if l.get("estado") == "OPERANDO")
        costo = horas * m.get("costo_hora_usd", 0)
        base.append({"maquina_id": m["maquina_id"], "modelo": m["modelo"], "zona": m.get("zona"),
                     "utilizacion_pct": round(pct * 100), "horas_operando": round(horas, 1),
                     "costo_usd": round(costo), "costo_por_t": costo / toneladas if toneladas else None})
    filas = []
    for modelo, grupo in _por_modelo(base).items():
        costos = [g["costo_por_t"] for g in grupo if g["costo_por_t"]]
        ref = median(costos) if costos else None
        for g in grupo:
            hallazgos = []
            if g["utilizacion_pct"] < UTILIZACION_BAJA * 100:
                hallazgos.append("BAJA_UTILIZACION")
            if g["horas_operando"] > HORAS_EXCESIVAS:
                hallazgos.append("JORNADA_EXCESIVA")
            if ref and g["costo_por_t"] and g["costo_por_t"] > COSTO_ALTO * ref:
                hallazgos.append("BAJA_PRODUCTIVIDAD_ALTO_COSTO")
            if hallazgos:
                filas.append({**{k: v for k, v in g.items() if k != "costo_por_t"},
                              "costo_por_t": round(g["costo_por_t"], 2) if g["costo_por_t"] else None,
                              "hallazgos": hallazgos})
    return sorted(filas, key=lambda f: (-len(f["hallazgos"]), f["utilizacion_pct"]))


def repuestos(stock, usos_7d, preventivos_proximos):
    """Demanda a 7 días = usos recientes + kits de preventivo (filtros) de máquinas PRONTO/VENCIDO.

    stock: filas de t_repuestos · usos_7d: {repuesto_id: n} · preventivos_proximos: [modelo, ...]
    """
    por_repuesto = {}
    for r in stock:
        p = por_repuesto.setdefault(r["repuesto_id"], {"repuesto_id": r["repuesto_id"], "nombre": r.get("nombre"),
                                                       "stock_total": 0, "stock_minimo": 0, "almacenes": {},
                                                       "modelos": set(r.get("modelos_compatibles", []))})
        p["stock_total"] += r.get("stock", 0)
        p["stock_minimo"] += r.get("stock_minimo", 0)
        p["almacenes"][r["almacen"]] = r.get("stock", 0)
    filas = []
    for rid, p in por_repuesto.items():
        es_kit = "filtro" in (p["nombre"] or rid).lower()
        demanda = usos_7d.get(rid, 0) + (sum(m in p["modelos"] for m in preventivos_proximos) if es_kit else 0)
        quedaria = p["stock_total"] - demanda
        alertas = []
        if quedaria < p["stock_minimo"]:
            alertas.append("FALTANTE_PROYECTADO")
        if usos_7d.get(rid, 0) >= CONSUMO_IRREGULAR:
            alertas.append("CONSUMO_IRREGULAR")
        if alertas:
            mejor = max(p["almacenes"], key=p["almacenes"].get)
            filas.append({"repuesto_id": rid, "nombre": p["nombre"], "stock_total": p["stock_total"],
                          "stock_minimo": p["stock_minimo"], "demanda_7d": demanda, "quedaria": quedaria,
                          "almacenes": p["almacenes"], "alertas": alertas,
                          "sugerencia": f"Reponer {max(p['stock_minimo'] - quedaria, 0) + 1} u.; hoy hay más en {mejor}"})
    return sorted(filas, key=lambda f: f["quedaria"] - f["stock_minimo"])


def resumen_plantilla(reporte):
    """Resumen de respaldo cuando la IA no responde (mismo formato que /resumen)."""
    prev = [f for f in reporte["preventivo"] if f["estado"] != "OK"]
    prioridades = []
    if prev:
        prioridades.append(f"Programar mantenimiento de {', '.join(f['maquina_id'] for f in prev[:3])}")
    if reporte["combustible"]:
        c = reporte["combustible"][0]
        prioridades.append(f"Revisar consumo de {c['maquina_id']} (+{c['desvio_pct']} % vs su modelo)")
    if reporte["repuestos"]:
        prioridades.append(f"Reponer {reporte['repuestos'][0]['repuesto_id']}")
    if reporte["utilizacion"]:
        prioridades.append(f"Reasignar trabajo de {reporte['utilizacion'][0]['maquina_id']}")
    texto = (f"Planificación del {reporte['fecha']}: {len(prev)} máquina(s) con mantenimiento próximo o vencido, "
             f"{len(reporte['combustible'])} con consumo de combustible fuera de lo esperado, "
             f"{len(reporte['utilizacion'])} con utilización o costo a revisar y "
             f"{len(reporte['repuestos'])} repuesto(s) en riesgo de faltar.")
    return {"resumen_gerente": texto, "prioridades": prioridades[:3] or ["Sin acciones urgentes"]}
