# Interfaces entre partes

Este archivo es el **acuerdo entre los tres**. Si cada uno respeta lo que está aquí, podemos trabajar en paralelo sin esperarnos. Si alguien necesita cambiar algo, lo avisa en el grupo **antes** de tocarlo.

Los formatos de lectura e incidente están en `telemetria.schema.json` e `incidente.schema.json` (cada uno trae un ejemplo).

---

## 1. Quién es dueño de qué carpeta

Nadie edita la carpeta de otro. Así nunca hay conflictos de merge.

| Persona | Rama | Carpetas que le pertenecen |
|---|---|---|
| **Denilson** (AWS) | `feat/aws-denilson` | `services/**`, `docs/arquitectura.png` |
| **Matías** (Google Cloud + web) | `feat/gcp-matias` | `gcp/**`, `frontend/**` |
| **Enrique** (datos, simulador, video) | `feat/datos-enrique` | `seed/**`, `simulator/**`, `docs/video/**`, `README.md` |
| Los tres | — | `contracts/**` (solo con acuerdo) |

---

## 2. AWS → Google Cloud (lo construye Matías, lo llama Denilson)

Todas las llamadas llevan el header `X-Arquifusion-Token: <token compartido>`. Si el token no coincide, la función responde `401`.

### `POST {IA_URL}/analizar`
- **Recibe:** un incidente con el formato de `incidente.schema.json`, sin `analisis_ia`.
- **Devuelve `200`:** el objeto `analisis_ia`, exactamente como en el esquema: `nivel_riesgo`, `resumen`, `posibles_causas_a_revisar`, `especialidad_sugerida`, `mensajes_por_rol` (`tecnico`, `supervisor`, `gerente`), `es_diagnostico: false` y `fuente: "GEMINI"`.
- **Si Gemini falla:** devuelve `503`. AWS reintenta y, si sigue fallando, usa una plantilla.
- **Tiempo máximo:** 20 segundos.

### `POST {IA_URL}/resumen`
- **Recibe:** `{ "tenant_id": "...", "fecha": "AAAA-MM-DD", "preventivo": [...], "combustible": [...], "utilizacion": [...], "repuestos": [...] }`.
- **Devuelve `200`:** `{ "resumen_gerente": "texto de 5 a 8 líneas", "prioridades": ["...", "...", "..."] }`.

### `POST {REPLICA_URL}/replica`
- **Recibe:** `{ "coleccion": "maquinas" | "incidentes", "id": "...", "operacion": "UPSERT" | "DELETE", "datos": { ... } }`.
- **Hace:** escribe en Firestore `coleccion/id` con `datos` (si es UPSERT) o borra el documento (si es DELETE). Repetir la misma llamada no duplica nada.
- **Devuelve `200`:** `{ "ok": true }`.
- **Importante:** AWS nunca manda `task_token` a Firestore.

### Cómo se comparten las URLs y el token
1. Matías despliega las funciones y genera un token largo y aleatorio.
2. Lo guarda en GCP Secret Manager como `arquifusion-token`.
3. Le pasa a Denilson **por mensaje privado** (nunca por el repo) `IA_URL`, `REPLICA_URL` y el token.
4. Denilson los guarda en AWS Secrets Manager como `arquifusion/gcp` con esta forma: `{"ia_url": "...", "replica_url": "...", "token": "..."}`.

---

## 3. Web → AWS (lo construye Denilson, lo usa Matías)

- **URL base:** `{API_URL}` = `https://<id>.execute-api.us-east-1.amazonaws.com/prod/api`.
- **Autenticación:** todas las rutas, salvo `/login`, llevan `Authorization: Bearer <token>`. El autorizador saca `tenant_id` y `rol` del token.
- **CORS:** abierto para el dominio de Firebase Hosting.

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `POST /login` | `{ "usuario", "password" }` | `{ "token", "rol", "tenant_id", "nombre" }` (el token dura 8 h) |
| `GET /maquinas` | — | `[ { maquina_id, modelo, zona, lat, lon, estado, horas_motor, ultima_lectura, riesgo } ]` |
| `GET /maquinas/{id}` | — | máquina + últimas 50 lecturas + incidentes de esa máquina |
| `GET /incidentes?estado=ABIERTOS` | — | lista de incidentes (formato del esquema, sin `task_token`) |
| `GET /incidentes/{id}` | — | un incidente completo |
| `POST /incidentes/{id}/cerrar` | `{ "intervencion", "componentes_reemplazados": [], "falla_confirmada": true/false, "minutos_detenida" }` | `{ "ok": true }` (reanuda la Step Function) |
| `GET /tecnicos` | — | `[ { tecnico_id, nombre, especialidad, zona, disponible, incidentes_activos } ]` |
| `GET /reportes/ultimo` | — | último reporte diario de SFN-2, con `resumen_gerente` |

**Roles en la web:**
- `tecnico`: ve sus incidentes asignados y puede cerrarlos.
- `supervisor`: ve todos los incidentes y los técnicos.
- `gerente`: ve el resumen, los indicadores y los incidentes críticos.

---

## 4. Simulador → AWS (lo construye Enrique, lo recibe Denilson)

- **`POST {INGESTA_URL}/telemetria`**, con header `x-api-key: <api key>`.
- **Cuerpo:** una lectura (`telemetria.schema.json`) o una lista de lecturas.
- **Respuesta:** `202` → `{ "encoladas": n }`.
- Denilson le pasa a Enrique `INGESTA_URL` y la API key por mensaje privado.
- **Calentamiento del detector:** cada máquina necesita **20 lecturas normales** antes de que se evalúen anomalías (con eso aprende su comportamiento habitual). Antes de lanzar cualquier escenario de falla, el simulador debe mandar al menos 25 rondas del escenario `normal`. Superar un límite físico (temperatura > 115 °C, vibración > 12 mm/s, presión > 400 bar) se detecta siempre, aun sin calentamiento.
- Con la degradación del escenario `degradacion` (+2 °C por lectura, junto con vibración y combustible), el incidente se abre en la 5.ª lectura anómala.

---

## 5. Datos semilla (los hace Enrique, los carga Denilson)

Archivos JSON en `seed/`, todos con `tenant_id: "MINA_SUR"`:

| Archivo | Campos |
|---|---|
| `maquinas.json` | `maquina_id, modelo, tipo, zona, lat, lon, horas_motor, horas_ultimo_mant, costo_hora_usd` |
| `tecnicos.json` | `tecnico_id, nombre, especialidad (MOTOR, HIDRAULICO, ELECTRICO, TREN_RODAJE, GENERAL), zona, lat, lon, disponible, email` |
| `repuestos.json` | `repuesto_id, nombre, almacen, stock, stock_minimo, modelos_compatibles[], especialidad` |
| `mantenimientos.json` | `maquina_id, fecha, tipo, horas_motor, componentes[], tecnico_id` |
| `usuarios.json` | `usuario, password_sha256, rol, nombre` (contraseñas de demo, nunca reales) |
| `zonas.json` | `zona, lat, lon` (centro de cada zona, para el clima y el mapa) |

---

## 6. Firestore (lo escribe AWS mediante `/replica`, lo lee la web)

- **Colecciones:** `maquinas/{maquina_id}` e `incidentes/{incidente_id}`, con los mismos campos que en DynamoDB, salvo `task_token`.
- **Reglas:** la web solo puede leer; solo la cuenta de servicio de la función `/replica` puede escribir.
- **Modo degradado:** si `{API_URL}` no responde en 5 segundos, la web lee de Firestore y muestra el aviso "Modo degradado (solo lectura)".
