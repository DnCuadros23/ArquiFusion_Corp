# Tareas de Enrique — Datos, simulador, video y entrega

**Rama:** `feat/datos-enrique` · **Tus carpetas:** `seed/**`, `simulator/**`, `docs/video/**`, `README.md`

Tu trabajo hace que la demo **cuente una historia creíble** y que la entrega cumpla todas las reglas. Sin tus datos y tus escenarios, no hay nada que mostrar.

> Si trabajas con un asistente de IA, dale este archivo, `contracts/interfaces.md`, `contracts/telemetria.schema.json` y `docs/arquitectura.png`. Pídele que avance **un paso a la vez** y que no toque carpetas fuera de las tuyas.

## Reglas
- Respeta los formatos de `contracts/interfaces.md` §4 y §5: Denilson carga tus archivos tal cual.
- Todos los datos son **simulados** y así se dice en el video. No uses nombres de empresas reales.

---

## Paso 1 — `seed/` · Datos semilla (entrégalo primero, Denilson lo necesita)

| Archivo | Contenido |
|---|---|
| `zonas.json` | 4 zonas cercanas entre sí (a 2–8 km): `TAJO_NORTE`, `TAJO_SUR`, `CHANCADORA`, `TALLER_CENTRAL`, con su centro `lat`/`lon` (alrededor de −16.72, −71.85 (pampa desértica de Arequipa)) |
| `maquinas.json` | **30 máquinas** en 3 modelos: 12 excavadoras `EXC-320` (`EXC-001…012`), 12 camiones `CAM-793` (`CAM-001…012`) y 6 cargadores `CAR-994` (`CAR-001…006`). Repartidas en las zonas, con horas de motor distintas (1 500 a 12 000) y `costo_hora_usd` según el modelo |
| `tecnicos.json` | **8 técnicos**: 2 MOTOR, 2 HIDRAULICO, 1 ELECTRICO, 1 TREN_RODAJE y 2 GENERAL, en zonas distintas, uno ya ocupado. Como `email` usa los correos del equipo |
| `repuestos.json` | ~15 repuestos en 2 almacenes (`TALLER_CENTRAL`, `TAJO_SUR`): filtros de aire y aceite, sellos hidráulicos, correas, inyectores… Que alguno tenga **stock bajo** a propósito |
| `mantenimientos.json` | 2–3 mantenimientos pasados por máquina. Que `EXC-007` tenga uno de **hace 2 semanas** por recalentamiento (sirve para mostrar el historial) |
| `usuarios.json` | `tecnico1`, `supervisor1` y `gerente1`, con `password_sha256` de contraseñas de demo |

**Listo cuando:** los 6 archivos están en tu rama, validan contra los campos de `interfaces.md` y se lo avisas a Denilson.

## Paso 2 — `simulator/` · Simulador con escenarios

**Qué construyes:**
- `simulator/simulador.py`, que funciona de dos formas:
  - **como script:** `python simulador.py --url $INGESTA_URL --key $API_KEY --escenario degradacion --minutos 10`;
  - **como Lambda:** `handler(event, context)`, que lee el escenario de `event["escenario"]` (por defecto `normal`).
- Cada ejecución manda **una lectura por máquina** (las 30), por defecto cada 1 min de tiempo simulado. Con `--rapido`, manda lecturas cada 5 s para la demo.

**Valores normales por modelo** (con ruido aleatorio pequeño):

| Variable | EXC-320 | CAM-793 | CAR-994 |
|---|---|---|---|
| Temperatura (°C) | 85–92 | 88–95 | 86–93 |
| Vibración (mm/s) | 3.5–4.5 | 3–4 | 3.5–4.5 |
| Presión hidráulica (bar) | 300–330 | 180–210 | 260–290 |
| Combustible (L/h) | 35–40 | 90–110 | 50–60 |

- `carga_t`, `velocidad_kmh` y `rpm` deben ser coherentes con el estado de la máquina.

**Escenarios** (son la historia del video):

| Escenario | Qué pasa |
|---|---|
| `normal` | Todo dentro de lo habitual |
| `degradacion` | `EXC-007` sube poco a poco su temperatura (+2 °C por lectura), su vibración y su combustible a la vez → incidente MEDIA o CRÍTICA |
| `combustible` | `CAM-004` gasta un 35 % más que los otros camiones con la misma carga → aparece en el reporte de combustible |
| `causa_comun` | 5 máquinas de `TAJO_NORTE` muestran cambios distintos en los mismos 10 minutos → se agrupan como posible causa común |
| `productividad` | `CAR-003` queda en `RALENTI` casi todo el día y `CAM-010` trabaja más de 20 h |

- `simulator/serverless.yml`: la Lambda (Python 3.12, LabRole) con una regla de EventBridge `rate(1 minute)` **desactivada por defecto**, y las variables `INGESTA_URL` y `API_KEY` sacadas de parámetros del despliegue. Denilson lo despliega en la cuenta de demo.

**Listo cuando:** con la URL de Denilson, `--escenario degradacion` provoca un incidente visible en DynamoDB.

## Paso 3 — `docs/video/guion.md` · Guion del video (5:00 máximo, apunta a 4:40)

| Tiempo | Bloque | Qué se muestra |
|---|---|---|
| 0:00–0:30 | El problema | Flota detenida = operación detenida; los 12 dolores en una frase |
| 0:30–1:30 | Arquitectura | `docs/arquitectura.png`: recorrido por los carriles ①–⑥ y por qué hay dos nubes |
| 1:30–3:50 | **Demo en vivo** | 1) mapa de la flota; 2) se lanza `degradacion`; 3) la Step Function se ve avanzar en la consola; 4) la IA explica; 5) se asigna técnico con su razón; 6) llegan los correos por rol; 7) el técnico cierra desde la web; 8) `causa_comun` agrupa 5 máquinas; 9) se corta la API y la web sigue en modo degradado |
| 3:50–4:25 | Escala y costo | Todo serverless, pago por uso, SQS absorbe picos, Cloud Run escala a cero |
| 4:25–4:40 | Cierre | Qué problemas resolvemos y qué sigue |

- Ensaya con cronómetro. **Si pasa de 5:00, no se revisa.**

## Paso 4 — `README.md` final y entrega
- **README corto (no es un informe):** qué es, el diagrama, el link al video, cómo desplegar (AWS: `serverless deploy`, GCP: `gcloud`, web: `firebase deploy`) y la tabla de carpetas.
- **Lista de la entrega en Canvas:** link al video, link al repo y `docs/arquitectura.png`.
- **Revisa que no queden secretos en el repo:**
  ```bash
  git log -p | grep -iE "token|secret|key|password"
  ```
  No debe aparecer nada real.

## Paso 5 — Pruebas antes de grabar
- Recorre los 5 escenarios con la web publicada y anota lo que falle como *issue* en GitHub, asignado a su dueño.

---

## Puntos de encuentro con el equipo
| Cuándo | Qué se comprueba |
|---|---|
| Al terminar el paso 1 | Denilson carga tu semilla |
| Cuando Denilson te pase `INGESTA_URL` y la API key | Pruebas tus escenarios contra AWS real |
| Cuando Matías te pase la web | Ensayas el video completo |
