# services/planificacion — carril ④ · SFN-2

```
EventBridge (06:00 Lima) → Parallel[ Preventivo | Combustible | Utilización | Repuestos ]
   → ResumenConIA (Retry x2; Catch → ResumenPlantilla) → GuardarYAvisar (t_reportes + correo al gerente)
```

| Análisis | Regla |
|---|---|
| Preventivo | Horas desde el último mantenimiento × factor de carga (entre 0.8 y 1.3, frente a su modelo). Intervalo de 500 h: **PRONTO** ≥ 85 %, **VENCIDO** ≥ 100 % |
| Combustible | L/h por tonelada contra la mediana **del mismo modelo**; se marca si supera en más de 20 %. Incluye la tendencia |
| Utilización | Ociosa (< 30 % del tiempo operando), jornada excesiva (> 20 h) y costo por tonelada > 1.3 × mediana del modelo |
| Repuestos | Demanda a 7 días = usos en incidentes + kits de filtro de las máquinas PRONTO/VENCIDO. Avisa de faltante proyectado y de consumo irregular (3 o más usos en 7 días) |

Todo se calcula sobre las 24 h previas a la última lectura de cada máquina, así funciona aunque el simulador acelere el tiempo.

## Desplegar (después de `ingesta` e `incidentes`)
```bash
cd services/planificacion && npm install && serverless deploy --stage dev
```

Vuelve a desplegar también `incidentes`: su filtro del gerente ahora acepta `REPORTE`.

## Ejecutar a mano (demo)
```bash
aws stepfunctions start-execution --state-machine-arn arn:aws:states:us-east-1:<cuenta>:stateMachine:arquifusion-planificacion-dev
```

Luego `GET /api/reportes/ultimo` devuelve el reporte con el resumen para el gerente.

## Pruebas (sin AWS)
```bash
python -m unittest discover -s tests -v
```
