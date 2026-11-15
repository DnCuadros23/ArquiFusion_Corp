# Tareas de Denilson — Núcleo AWS

**Rama:** `feat/aws-denilson` · **Tus carpetas:** `services/**` · **Cuenta:** tu Learner Lab es la **cuenta de demo**.

Vas a construir todo lo que vive dentro del recuadro "AWS Cloud" del diagrama (`docs/arquitectura.png`): carriles ①–⑥ y la columna de persistencia.

> Si trabajas con un asistente de IA, dale este archivo, `contracts/interfaces.md`, los dos esquemas de `contracts/` y `docs/arquitectura.png`. Pídele que avance **un paso a la vez** y que no toque carpetas fuera de `services/`.

## Reglas para no bloquearte
- **No esperes a Matías:** mientras no tengas las URLs de Google, la λ de IA devuelve la plantilla (`fuente: "PLANTILLA"`). Cuando lleguen, solo cambias el secreto.
- **No esperes a Enrique:** prueba con el ejemplo que trae cada esquema en `contracts/` (campo `examples`) y con 3 máquinas escritas a mano. Cuando llegue `seed/`, cargas todo.
- Todas las funciones usan Python 3.12, `role: arn:aws:iam::${aws:accountId}:role/LabRole` y región `us-east-1`. Los logs se escriben en JSON de una línea.

---

## Paso 1 — `services/ingesta` (carril ②, más las tablas)

**Qué construyes:**
- Las 8 tablas DynamoDB, en modo **on-demand** y con **PITR** activado. `t_maquinas` e `t_incidentes` además con **Streams** (`NEW_IMAGE`):
  - `t_maquinas` (PK `tenant_id`, SK `maquina_id`)
  - `t_telemetria` (PK `maquina_id`, SK `ts`, con TTL `expira` a 3 días)
  - `t_incidentes` (PK `tenant_id`, SK `incidente_id`, con un GSI por `maquina_id`)
  - `t_tecnicos`, `t_repuestos`, `t_mantenimientos`, `t_reportes`, `t_umbrales`
- Bucket S3 `${stage}-arquifusion-datalake-${accountId}` con **versionado** y cifrado.
- API Gateway `POST /telemetria` con **API key** y usage plan.
- Cola SQS `t-telemetria` con su **DLQ** (recepciones máximas = 3).
- `λ ingesta`, disparada por SQS en lotes de 10. Para cada lectura:
  1. Valida el contrato y descarta lo inválido con un log de `ERROR`.
  2. Guarda en `t_telemetria`, actualiza el estado en `t_maquinas` y escribe el lote en S3: `raw/telemetria/fecha=AAAA-MM-DD/<uuid>.json`.
  3. Ejecuta el **detector**: guarda en `t_maquinas` la media y la varianza móviles (EWMA, alfa 0.1) de cada variable y calcula `z = (valor − media) / desviación`. Una variable cuenta como desviada si `|z| > 2.5` durante 3 o más lecturas seguidas.
  4. Asigna la severidad:
     - `OBSERVACION`: 1 variable desviada;
     - `MEDIA`: 2 o más;
     - `CRITICA`: 3 o más, o un valor fuera del rango físico (por ejemplo, temperatura > 115 °C).
  5. Si hay anomalía y la máquina no tiene ya un incidente abierto, ejecuta **SFN-1** con el incidente inicial.
- Script `services/ingesta/cargar_seed.py`, que lee `seed/*.json` y llena las tablas.

**Listo cuando:** envías el ejemplo de telemetría con Postman, aparece en DynamoDB y en S3, y una lectura anómala repetida arranca SFN-1.

**Entregas:** la `INGESTA_URL` y la API key a **Enrique** (por privado).

## Paso 2 — `services/incidentes` (carril ③, SFN-1)

**Qué construyes:**
- Step Function **Standard** con el plugin `serverless-step-functions`. Los pasos son exactamente los del diagrama, y cada uno es una λ:
  1. **Enriquecer:** historial de la máquina (`t_incidentes`, `t_mantenimientos`) y su ubicación.
  2. **Analizar con IA:** lee `arquifusion/gcp` de Secrets Manager y llama a `POST {ia_url}/analizar`.
     - En la definición pon `Retry` (2 intentos, backoff de 2 s) y `Catch` a una λ "plantilla" que arma `analisis_ia` con `fuente: "PLANTILLA"`.
  3. **Choice severidad:** `OBSERVACION` registra y termina; `MEDIA` o `CRITICA` continúa.
  4. **¿Causa común?:** si hay 3 o más incidentes en la misma zona en los últimos 60 min, pone el mismo `grupo_causa_comun` y consulta el clima de la zona en Open-Meteo (`api.open-meteo.com`, sin key). Es una hipótesis para investigar, no una conclusión.
  5. **Asignar técnico:**
     - filtra por especialidad (`especialidad_sugerida`) y por técnicos disponibles;
     - ordena por `ETA = distancia_haversine_km / 25 km/h * 60 + 15 × incidentes_activos`;
     - guarda la `razon` de la elección.
  6. **Reservar repuestos:** descuenta el stock en `t_repuestos` y marca `disponible: false` si no alcanza.
  7. **Notificar por rol:** publica en SNS `alertas-flota` con los atributos `rol` y `severidad`.
     - Crea 3 suscripciones de email con filtro: técnico (todo), supervisor (`MEDIA` y `CRITICA`) y gerente (solo `CRITICA`). Usa los correos de los tres.
  8. **Esperar técnico:** usa `.waitForTaskToken`, guarda el `task_token` en el incidente y pone el estado `ASIGNADO`.
  9. **Cerrar y registrar:** recibe los datos de cierre, calcula el tiempo detenido, libera al técnico y deja el estado `CERRADO`.
- Cada paso agrega un evento a `linea_tiempo`.

**Listo cuando:** una anomalía produce un incidente `ASIGNADO`, llegan los correos según el rol y la ejecución queda esperando en el paso 8.

## Paso 3 — `services/api` (carril ①)

**Qué construyes:**
- API Gateway REST con **λ autorizador** (token Bearer). Los tokens van en una tabla `t_tokens` y duran 8 h.
- `λ api` con las rutas de `contracts/interfaces.md` §3.
- `POST /incidentes/{id}/cerrar` llama a `SendTaskSuccess` con el `task_token` guardado.
- CORS para el dominio de Firebase Hosting.

**Listo cuando:** con Postman haces login, listas máquinas e incidentes, cierras uno y la Step Function termina en verde.

**Entregas:** la `API_URL` y los usuarios de demo a **Matías**.

## Paso 4 — `services/replica` (carril ⑤)

**Qué construyes:**
- `λ replicador`, disparada por los Streams de `t_maquinas` y `t_incidentes`. Llama a `POST {replica_url}/replica`, quitando antes `task_token`.

**Listo cuando:** un incidente nuevo aparece en Firestore (pídele a Matías que lo confirme).

## Paso 5 — `services/planificacion` (carril ④, SFN-2)

**Qué construyes:**
- Regla EventBridge `cron(0 11 * * ? *)` (06:00 en Lima). La Step Function también debe poder ejecutarse a mano para la demo.
- `Parallel` con 4 λ:
  - **preventivo:** horas desde el último mantenimiento y carga media, con prioridad;
  - **combustible:** L/h por tonelada contra la mediana **del mismo modelo**; se marca si supera la mediana en más de 20 %;
  - **utilización:** máquinas ociosas (< 30 % del tiempo operando) y sobreusadas (> 20 h/día), con su costo;
  - **repuestos:** demanda proyectada a 7 días contra stock; se marca si quedará bajo el mínimo.
- λ resumen: llama a `POST {ia_url}/resumen`.
- λ guardar: escribe en `t_reportes` y avisa al gerente por SNS.

**Listo cuando:** la ejecución manual termina en verde y `GET /reportes/ultimo` devuelve el resumen.

## Paso 6 — `services/historico` (carril ⑥, SFN-3) · **solo si sobra tiempo**

**Qué construyes:**
- Una λ que descarga AI4I 2020 desde UCI y el clima de Open-Meteo hacia `s3://.../raw/historico/`.
- Un crawler de Glue y una consulta de Athena: promedio de cada variable en las lecturas previas a una falla frente a lecturas normales.
- Una λ que escribe esos resultados en `t_umbrales`.

**Si no da el tiempo:** queda en el diagrama como "fase siguiente" y se menciona en el video.

## Paso 7 — Despliegue final (stage `prod`)
- Despliega todos los servicios con `--stage prod` en tu cuenta.
- Carga la semilla.
- Despliega el simulador de Enrique (`simulator/serverless.yml`).
- Confirma las 3 suscripciones de email.
- Deja el simulador **apagado** hasta la grabación.

---

## Puntos de encuentro con el equipo
| Cuándo | Qué se comprueba |
|---|---|
| Al terminar el paso 1 | Enrique envía lecturas reales a tu `INGESTA_URL` |
| Cuando Matías te pase las URLs | Pruebas `/analizar` desde SFN-1 (cambias solo el secreto) |
| Al terminar el paso 3 | Matías conecta la web a tu `API_URL` |
| Antes de grabar | Recorrido completo: degradación → incidente → correo → cierre desde la web → Firestore |
