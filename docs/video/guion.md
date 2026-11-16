# Guion del video — ArquiFusion Fleet

**Límite: 5:00. Objetivo: 4:40.** Si el archivo final pasa de 5:00, no se revisa.
Grabar por bloques y unir en la edición. Los datos son simulados y así se dice.

## Resumen por bloque

| # | Tiempo | Bloque | Pantalla | Criterios de la rúbrica |
|---|---|---|---|---|
| 1 | 0:00–0:25 | El problema | Mapa de la flota | Pitch |
| 2 | 0:25–1:20 | Arquitectura | `docs/arquitectura.png` | Arquitectura, 2 nubes, serverless, persistencia, secretos |
| 3 | 1:20–2:50 | Demo: un incidente de principio a fin | Terminal, Step Functions, web, correo | Problemas, Step Functions, IA |
| 4 | 2:50–3:25 | Demo: causa común | Terminal y web | Problemas |
| 5 | 3:25–3:55 | Demo: planificación diaria | Web (gerente) y Step Functions | Problemas, Step Functions, IA |
| 6 | 3:55–4:20 | Alta disponibilidad y escala | Firestore y diagrama | Persistencia, 2 nubes, serverless |
| 7 | 4:20–4:40 | Cierre | Lista de problemas resueltos | Pitch, problemas |

---

## Bloque 1 — El problema (0:00–0:25)

**Pantalla:** mapa de la flota con las 30 máquinas.

**Decir:**
> ¡Muy buenas a todos, guapísimos!
>
> En una mina, una máquina detenida frena a todas las que dependen de ella. ArquiFusion fabrica esa maquinaria y sus clientes tienen los datos, pero se enteran de la falla cuando ya ocurrió. ArquiFusion Fleet convierte la telemetría en decisiones: avisa antes de la falla, envía al técnico correcto y aprende del historial. Los datos de esta demo son simulados.

## Bloque 2 — Arquitectura (0:25–1:20)

**Pantalla:** el diagrama, señalando cada carril al nombrarlo.

**Decir:**
> Todo es serverless y basado en eventos: no hay nada encendido las 24 horas.
> La telemetría entra por API Gateway a una cola SQS, que absorbe los picos; si un mensaje falla tres veces va a una cola de errores y no se pierde. Una Lambda guarda cada lectura en DynamoDB y en un data lake en S3, y compara cada máquina con su propio comportamiento habitual.
> Cuando una anomalía persiste, arranca una Step Function. Tenemos tres: el flujo de incidente, la planificación diaria y el aprendizaje histórico con Glue y Athena.
> Usamos dos nubes. En AWS vive el núcleo. En Google Cloud está la inteligencia artificial, con Gemini en Cloud Run, la réplica de los datos en Firestore y la web en Firebase Hosting.
> Las URLs y el token que conectan ambas nubes están en AWS Secrets Manager, nunca en el código.

**Debe quedar dicho:** serverless · SQS con DLQ · 3 Step Functions · AWS + Google Cloud · Secrets Manager.

## Bloque 3 — Un incidente de principio a fin (1:20–2:50)

**Preparación:** incidentes anteriores cerrados y detector calentado.

| Paso | Pantalla | Decir |
|---|---|---|
| 3.1 | Terminal: `python simulator/simulador.py --escenario degradacion --rondas 8 --rapido` | "Lanzamos un escenario: la excavadora 007 empieza a subir temperatura, vibración y consumo a la vez." |
| 3.2 | Web: aparece el incidente CRÍTICA de `EXC-007` | "Ninguna variable sola era alarmante. El detector mira las tres juntas y exige que el cambio persista: una variable es observación, dos es media, tres es crítica." |
| 3.3 | Consola de Step Functions: la ejecución en curso | "Esto arranca la Step Function: enriquece con el historial, pide el análisis a la IA, busca causa común, asigna técnico, reserva repuestos y notifica. Cada paso tiene reintentos." |
| 3.4 | Web: detalle del incidente, análisis de IA | "Gemini explica qué cambió y qué revisar. No diagnostica: dice que merece revisión. Y la IA no decide; la severidad y la asignación son reglas nuestras." |
| 3.5 | Web: técnico asignado y su razón | "Eligió a un técnico de motor, disponible y el más cercano, y explica por qué. El historial muestra que esta máquina ya tuvo un recalentamiento hace dos semanas." |
| 3.6 | Correo recibido | "Cada rol recibe un mensaje distinto: el técnico el detalle, el supervisor quién atiende, y el gerente solo lo crítico." |
| 3.7 | Web como técnico: cerrar incidente → Step Functions en verde | "El flujo queda en pausa hasta que el técnico cierra el caso. Al cerrarlo se registra la intervención, los componentes y el tiempo detenida." |

**Recortar en edición:** la espera del simulador (unos 25 segundos) y los pasos de la Step Function.

## Bloque 4 — Causa común (2:50–3:25)

**Pantalla:** terminal con `python simulator/simulador.py --escenario causa_comun --rondas 9 --rapido`, luego la lista de incidentes.

**Decir:**
> Ahora cinco máquinas de la misma zona cambian en pocos minutos, cada una de forma distinta. En vez de tratarlas como cinco problemas aislados, la plataforma las agrupa como posible causa común y consulta el clima de la zona. Es una hipótesis para investigar, no una conclusión. Y reparte los casos entre técnicos según especialidad y carga de trabajo.

## Bloque 5 — Planificación diaria (3:25–3:55)

**Pantalla:** web con el usuario gerente, vista Planificación; un vistazo a la Step Function con sus cuatro ramas en paralelo.

**Decir:**
> Cada mañana otra Step Function analiza en paralelo cuatro cosas: qué máquinas necesitan mantenimiento preventivo según sus horas y su uso, cuáles gastan más combustible que las de su mismo modelo con la misma carga, cuáles están ociosas o sobreusadas, y qué repuestos van a faltar en cada almacén. Gemini lo resume para el gerente en lenguaje claro, con tres prioridades.

## Bloque 6 — Alta disponibilidad y escala (3:55–4:20)

**Pantalla:** consola de Firestore con máquinas e incidentes replicados; luego el diagrama.

**Decir:**
> Los datos viven en DynamoDB con recuperación a un punto en el tiempo y en S3 versionado. Además, cada cambio se replica a Firestore en Google Cloud, así los datos sobreviven a la caída de una nube completa.
> Y como todo es serverless, pasar de treinta máquinas a miles no requiere rediseñar nada: la cola crece, las funciones escalan solas y se paga solo por lo que se usa.

## Bloque 7 — Cierre (4:20–4:40)

**Pantalla:** lista de los problemas del reto con su solución.

**Decir:**
> ArquiFusion Fleet cubre los problemas del reto: anticipa fallas, planifica mantenimiento, controla repuestos y combustible, ubica la flota, asigna técnicos, comunica por rol, guarda el historial, detecta causas comunes y aprende de los datos. No es un dashboard: es una plataforma que decide qué merece atención y a quién avisar. Gracias.

---

## Lista de control por criterio

| Criterio | Pts | Dónde se cubre | Evidencia en pantalla |
|---|---|---|---|
| Problemas resueltos | 3 | Bloques 3, 4, 5 y 7 | Incidente, causa común, planificación, lista final |
| Persistencia y alta disponibilidad | 2 | Bloques 2 y 6 | Diagrama y consola de Firestore |
| Step Functions | 2 | Bloques 2, 3 y 5 | Ejecuciones en la consola de AWS |
| 2 nubes | 3 | Bloques 2 y 6 | Diagrama, Gemini en el incidente, Firestore |
| Arquitectura | 3 | Bloque 2 | `docs/arquitectura.png` |
| Pitch | 2 | Bloques 1 y 7 | Empieza por el problema del cliente |
| Serverless | 2 | Bloques 2 y 6 | Se dice explícitamente dos veces |
| IA | 3 | Bloques 3 y 5 | Análisis del incidente y resumen del gerente |
| Secretos en AWS (nota) | — | Bloque 2 | Se nombra Secrets Manager |

## Antes de grabar

- [ ] Confirmar que el análisis del incidente dice fuente `GEMINI` y no `PLANTILLA`.
- [ ] Confirmar que Firestore tiene las colecciones `maquinas` e `incidentes` con datos.
- [ ] Cerrar todos los incidentes abiertos desde la web.
- [ ] Mandar 5 rondas de `normal` para devolver las máquinas a su estado habitual (25 si el despliegue o la semilla cambiaron).
- [ ] Tener una ejecución reciente de la planificación diaria.
- [ ] No mostrar el `.env`, la API key ni contraseñas en pantalla.

## Si algo no está listo

| Falta | Qué cambiar |
|---|---|
| Gemini no responde (fuente `PLANTILLA`) | No grabar el paso 3.4 hasta arreglarlo: sin IA real se pierden los puntos de IA |
| Firestore sin datos | En el bloque 6 mostrar solo el diagrama y decir "la réplica está diseñada para"; no afirmar que funciona |
| Modo degradado de la web | No mostrarlo; se menciona como siguiente fase |
| Planificación sin datos | Ejecutar la Step Function a mano antes de grabar |
