# ArquiFusion Fleet — Contexto para el equipo

> Léelo una vez (10 min). Es lo único que necesitas para saber qué construimos, por qué y qué te toca.

---

## 1. El reto en una frase

ArquiFusion fabrica maquinaria pesada (minería, construcción...). Quiere una plataforma que use los datos de sus máquinas para **avisar antes de que fallen, mandar al técnico correcto, controlar repuestos y combustible, y aprender del historial**, todo en la nube y pagando solo por lo que se usa.

## 2. Qué entregamos (por Canvas)

| Entregable | Regla |
|---|---|
| Video (pitch + demo) | **Máximo 5:00.** Si se pasa, no lo revisan |
| Repo de GitHub | Código + README corto + diagrama |
| Diagrama de arquitectura | Imagen en `docs/arquitectura.png` |
| ❌ Informe | **Prohibido.** Si lo subimos, nos anulan |

Fecha: **domingo**. Nuestro cierre interno: **domingo 18:00**.

## 3. Cómo nos califican (20 pts) y cómo lo cubrimos

| Criterio | Pts | Nuestra respuesta |
|---|---|---|
| Problemas resueltos | 3 | Resolvemos ~10 de los 12 problemas del reto (tabla en la sección 6) |
| Persistencia y alta disponibilidad | 2 | DynamoDB (multi-AZ + backups) + S3 versionado + **réplica en Google Firestore** + colas con DLQ |
| Step Functions | 2 | **3 flujos**: incidente, planificación diaria, carga de histórico |
| 2+ nubes (obligatorio) | 3 | **AWS** (núcleo) + **Google Cloud** (IA con Gemini, réplica, hosting web) |
| Arquitectura | 3 | Diagrama limpio, cada pieza con una razón |
| Pitch 5 min | 2 | Demo en vivo de un incidente de principio a fin |
| 100 % serverless | 2 | Nada encendido 24/7: Lambda, colas, Step Functions, Cloud Run |
| Uso de IA | 3 | Gemini explica anomalías, redacta mensajes por rol y resume el día |
| Extra (nota del profe) | — | Claves y secretos en **AWS Secrets Manager**, nunca en el código |

## 4. Cómo funciona (versión simple)

```
1. Un SIMULADOR hace de "máquinas" y manda lecturas (temperatura, vibración, combustible, GPS...).
2. AWS las recibe (API Gateway → cola SQS) y una Lambda las guarda (DynamoDB + S3).
3. Un DETECTOR compara cada máquina con su propio historial y con las de su mismo modelo.
4. Si algo raro se repite → arranca la Step Function de INCIDENTE:
      ¿qué tan grave? → la IA (Gemini en Google) lo explica sin inventar diagnósticos
      → ¿hay otras máquinas con problemas en la misma zona? (posible causa común)
      → elige técnico (especialidad + disponible + más cerca)
      → revisa si hay repuesto
      → avisa por correo según el rol (técnico / supervisor / gerente)
      → espera a que el técnico cierre el caso → guarda todo en el historial
5. Cada día otra Step Function PLANIFICA: mantenimientos, combustible raro, máquinas ociosas, repuestos.
6. Todo lo importante se COPIA a Google Firestore. Si AWS falla, la web sigue mostrando datos.
7. La WEB (React en Firebase Hosting) muestra mapa, incidentes, planificación y vista por rol.
```

## 5. Tecnologías (y por qué)

| Pieza | Servicio | Por qué |
|---|---|---|
| Recibir datos | API Gateway + **SQS** (+ DLQ) | La cola aguanta picos de 10 a 10 000 máquinas y no se pierde nada |
| Lógica | **Lambda (Python 3.12)** | Solo se paga cuando corre |
| Estado actual | **DynamoDB** | Rápida, sin servidor, la usamos en el curso |
| Histórico | **S3 + Glue + Athena** | Barato para mucho volumen, consultas SQL |
| Orquestar | **Step Functions** | Flujos visibles, con reintentos y espera humana |
| Avisos | **SNS** con filtros por rol | Cada rol recibe solo lo que le toca |
| Tareas programadas | **EventBridge** | Simulador y planificación diaria |
| Secretos | **Secrets Manager** | Pedido explícito del profe |
| IA | **Gemini (Vertex AI) en Cloud Run** | Explica y redacta; AWS Academy no trae IA generativa |
| Réplica | **Firestore** | Segunda nube = alta disponibilidad real |
| Web | **React + Vite** en **Firebase Hosting** | Gratis y con modo degradado |
| Desplegar AWS | **Serverless Framework** (`serverless.yml`, `LabRole`) | Lo vimos en clase |

> **Plan B si no conseguimos créditos de Google:** la IA se llama desde una Lambda con una key gratuita de Google AI Studio, y Firestore + Firebase Hosting siguen en plan gratuito. **El código de IA se escribe para que funcione en ambos lados**, así que nadie pierde trabajo.

## 6. Problemas del reto que resolvemos

| Problema | Cómo |
|---|---|
| Anticipar fallas / comportamiento raro | Detector multivariable + historial propio + comparación con su modelo |
| Ubicación y estado | Mapa con colores por estado |
| Asignar técnicos | Puntaje: especialidad, disponibilidad, distancia, carga |
| Comunicación por rol | SNS con filtros + mensajes de la IA adaptados al rol |
| Historial | Cada incidente guarda línea de tiempo, técnico, repuestos y tiempo detenido |
| Combustible | Consumo por tonelada vs máquinas del mismo modelo |
| Causa común | 3+ incidentes en la misma zona y hora → grupo + clima de la zona |
| Mantenimiento preventivo | Horas desde el último mantenimiento, ajustado por carga |
| Repuestos | Stock vs demanda proyectada, alerta de faltantes |
| Productividad | Máquinas ociosas, sobreusadas, caras y poco productivas |
| Aprender del histórico | Dataset público AI4I 2020 → qué cambia antes de una falla |

**Regla de oro:** una anomalía **no es** una falla confirmada. La plataforma dice "merece revisión", nunca "el motor está roto".

## 7. Los datos

No nos dan datos. Usamos:
1. **Simulador propio** con escenarios preparados para la demo (una máquina que se degrada, una que gasta más combustible, cinco de la misma zona fallando juntas).
2. **AI4I 2020** (dataset público de mantenimiento predictivo) para calibrar umbrales.
3. **Open-Meteo** (API gratis de clima) para revisar si el clima explica una causa común.

Formato de una lectura (**no se cambia sin avisar a los tres**):

```json
{"tenant_id":"MINA_SUR","maquina_id":"EXC-007","modelo":"EXC-320","ts":"2026-11-14T15:00:00Z",
 "lat":-15.84,"lon":-70.02,"zona":"TAJO_NORTE","estado":"OPERANDO","horas_motor":4521.5,
 "temp_motor_c":92.1,"vibracion_mm_s":4.2,"presion_hid_bar":310,"combustible_l_h":38.5,
 "carga_t":28.0,"velocidad_kmh":6.1,"rpm":1850}
```

## 8. Quién hace qué

| Persona | Área | Entrega principal |
|---|---|---|
| **P1 — Datos** | Simulador, ingesta, tablas, datos semilla, histórico (Athena), API de consultas | Las lecturas llegan y se pueden consultar |
| **P2 — Orquestación** | Detector, Step Functions (incidente y planificación), SNS, Secrets Manager | Un incidente recorre todo el flujo |
| **P3 — IA + Web (Denilson)** | Google Cloud (Gemini, Firestore, Hosting), réplica, frontend | La IA explica, la web lo muestra, la réplica funciona |

Diagrama y video: **los tres**, el domingo por la tarde.

## 9. Reglas del repo

- `main` siempre funciona. Nadie hace push directo a `main`.
- Cada uno trabaja en su rama: `feat/datos-...`, `feat/flujos-...`, `feat/web-...`.
- Pull Request pequeño + un compañero lo revisa rápido + merge.
- **Nunca** subir claves, `.env` ni JSON de credenciales (ya están en `.gitignore`).
- Todas las Lambdas usan `role: arn:aws:iam::<cuenta>:role/LabRole`.
- Al terminar de probar: **apagar el simulador** (EventBridge) para no gastar créditos.
- Las sesiones de Learner Lab duran 4 h: todo debe poder redeployarse con `serverless deploy`.

## 10. Glosario mínimo

- **Anomalía:** valor que se aleja de lo normal de esa máquina. No es una falla confirmada.
- **Incidente:** algo que requiere atención y queda registrado.
- **Step Function:** un diagrama de pasos que AWS ejecuta solo (con reintentos y esperas).
- **Task token:** la Step Function se "pausa" hasta que el técnico pulsa "cerrar" en la web.
- **DLQ:** cola donde caen los mensajes que fallaron varias veces, para no perderlos.
- **Réplica:** copia de los datos en otra nube por si la primera falla.
