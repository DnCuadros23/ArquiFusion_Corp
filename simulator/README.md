# simulator/ — Simulador de la flota (datos simulados)

Cada ronda manda una lectura por máquina (las 30 de `seed/maquinas.json`) a `POST {INGESTA_URL}/telemetria`.
Solo usa la librería estándar de Python 3.12.

## Configurar

Crea un `.env` en la raíz del repo (está en `.gitignore`, nunca se sube):

```
INGESTA_URL=https://<id>.execute-api.us-east-1.amazonaws.com/dev
API_KEY=<api key>
```

También sirven `--url` y `--key`, o las variables de entorno.

## Orden para la demo

**1. Calentar el detector** (una sola vez por despliegue). Cada máquina necesita 20 lecturas normales antes de que se evalúen anomalías; mandamos 25:

```bash
python simulador.py --escenario normal --rondas 25 --rapido
```

**2. Lanzar un escenario:**

```bash
python simulador.py --escenario degradacion --rondas 8 --rapido
```

| Escenario | Qué pasa | Qué se ve en la plataforma |
|---|---|---|
| `normal` | Todo dentro de lo habitual | Ningún incidente |
| `degradacion` | `EXC-007` sube temperatura (+2 °C por lectura), vibración y combustible a la vez | Incidente **CRÍTICA** (3 variables) en la 5.ª ronda |
| `combustible` | `CAM-004` gasta 35 % más con la misma carga | Observación en la 3.ª ronda y aparece en el reporte de combustible |
| `causa_comun` | `EXC-004`, `EXC-005`, `EXC-006`, `CAM-001` y `CAR-001` (todas en `TAJO_NORTE`) cambian de forma distinta, una ronda tras otra | 5 incidentes **MEDIA** entre las rondas 3 y 7, agrupados como posible causa común |
| `productividad` | `CAR-003` pasa el 90 % del tiempo en `RALENTI` y `CAM-010` trabaja 22 h; el resto, 14 h | Sale en el reporte de utilización. `CAR-003` genera además una observación por su consumo |

`productividad` necesita un día completo de datos. Con `--simular-horas` los `ts` se reparten en las últimas N horas:

```bash
python simulador.py --escenario productividad --simular-horas 24 --rondas 96 --intervalo 3
```

Otras opciones: `--minutos N` (duración real), `--intervalo S` (segundos entre rondas, 60 por defecto), `--rapido` (5 s) y `--dry-run` (no envía, muestra una lectura por ronda).

## Cosas a tener en cuenta

- **No bajes de 3 s entre rondas:** dos lecturas de la misma máquina procesadas a la vez pueden pisar sus estadísticas.
- Una máquina con un incidente abierto no abre otro hasta que se cierre. Para repetir un escenario hay que cerrar el incidente desde la web.
- Después de un escenario de falla, la máquina afectada vuelve a sus valores normales con `--escenario normal`.
- Una máquina `DETENIDA` no manda sensores (se omiten; no se manda 0), como pide el contrato.
- Los valores habituales de cada máquina son fijos (dependen de su `maquina_id`), así que el calentamiento sirve para cualquier ejecución posterior.

## Como Lambda

`handler(event, context)` lee `event["escenario"]` (por defecto `normal`) y, opcionalmente, `rondas`, `intervalo_s` y `simular_horas`. El despliegue y la regla de EventBridge (desactivada por defecto) están explicados en `serverless.yml`.

```bash
aws lambda invoke --function-name arquifusion-simulador-prod-simulador --cli-binary-format raw-in-base64-out --payload '{"escenario":"degradacion","rondas":8,"intervalo_s":5}' salida.json
```
