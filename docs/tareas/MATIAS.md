# Tareas de Matías — Google Cloud y la web

**Rama:** `feat/gcp-matias` · **Tus carpetas:** `gcp/**`, `frontend/**` · **Cuenta:** tu proyecto de Google Cloud.

Vas a construir todo lo que vive en el recuadro "Google Cloud" del diagrama (`docs/arquitectura.png`): la IA con Gemini, la réplica en Firestore y la web en Firebase Hosting.

> Si trabajas con un asistente de IA, dale este archivo, `contracts/interfaces.md`, los dos esquemas de `contracts/` y `docs/arquitectura.png`. Pídele que avance **un paso a la vez** y que no toque carpetas fuera de `gcp/` y `frontend/`.

## Reglas para no bloquearte
- **No esperes a Denilson:** la web arranca con datos de prueba (`VITE_USE_MOCK=true`), tomados de los ejemplos de `contracts/`. Cuando él te pase la `API_URL`, cambias la variable y listo.
- **Tus funciones solo dependen del contrato:** pruébalas con `curl` usando el incidente de ejemplo.
- **Nunca subas al repo** claves, tokens ni el JSON de la cuenta de servicio.

---

## Paso 0 — Preparar el proyecto (sección 10 de `docs/CONTEXTO_EQUIPO.md`)
- Crea el proyecto, activa las APIs y crea Firestore en `us-central1`.
- Configura una alerta de presupuesto de USD 10.
- Invita a Denilson y a Enrique como Editor.
- Genera el token compartido con `openssl rand -hex 32` y guárdalo en Secret Manager como `arquifusion-token`.

## Paso 1 — `gcp/ia` · Cloud Run function de IA (más importante)

**Qué construyes** (Python 3.12, una sola función HTTP):
- Comprueba `X-Arquifusion-Token` contra Secret Manager y responde `401` si no coincide.
- **`POST /analizar`:** llama a Gemini (`gemini-2.5-flash` en Vertex AI) con el SDK `google-genai` (`vertexai=True`).
  - Usa `temperature 0.2` y **salida JSON con `response_schema`** igual a `analisis_ia` de `contracts/incidente.schema.json`.
  - El prompt debe dejar claro que:
    - es un asistente de mantenimiento de maquinaria pesada;
    - usa **solo** los datos recibidos: variables anómalas, su z, cuántos minutos llevan, el historial y la zona;
    - **nunca afirma un diagnóstico**: dice "merece revisión" y lista causas *a revisar*;
    - redacta 3 mensajes distintos: técnico (detalle técnico), supervisor (quién atiende y la urgencia) y gerente (impacto en una línea, sin tecnicismos);
    - si `grupo_causa_comun` no es nulo, menciona que hay otras máquinas afectadas en la zona y el clima, como **hipótesis**.
  - Valida la respuesta y fuerza `es_diagnostico: false` y `fuente: "GEMINI"`.
  - Si Gemini falla, responde `503`.
- **`POST /resumen`:** recibe el reporte diario y devuelve `{ resumen_gerente, prioridades[3] }`.
- Despliegue:
  ```bash
  gcloud functions deploy arquifusion-ia --gen2 --runtime=python312 --region=us-central1 --trigger-http --allow-unauthenticated --entry-point=main --memory=512Mi --timeout=30s --max-instances=3
  ```
  Se publica sin autenticación de Google porque la protección es el token; `--max-instances=3` limita el costo.

**Listo cuando:** un `curl` con el incidente de ejemplo devuelve un `analisis_ia` válido en menos de 10 s, y sin token devuelve 401.

**Entregas:** la `IA_URL` y el token a **Denilson** (por privado).

## Paso 2 — `gcp/replica` · Cloud Run function de réplica

**Qué construyes:**
- **`POST /replica`**, según `contracts/interfaces.md` §2: hace UPSERT o DELETE en `maquinas/{id}` o `incidentes/{id}` de Firestore. Si viene `task_token`, lo descarta. Valida el token igual que la función de IA.
- `gcp/firestore.rules`: lectura pública solo de `maquinas` e `incidentes` (son datos simulados) y escritura bloqueada para los clientes.

**Listo cuando:** un `curl` crea un documento en Firestore y repetirlo no lo duplica.

**Entregas:** la `REPLICA_URL` a **Denilson**.

## Paso 3 — `frontend/` · Web React + Vite + Leaflet

**Pantallas:**
1. **Login:** `POST /login`. Guarda el token y el rol en memoria o `sessionStorage`.
2. **Flota (mapa):** máquinas en Leaflet, con color por estado (operando, detenida, mantenimiento, en riesgo) y un panel lateral con la máquina seleccionada.
3. **Incidentes:**
   - lista con filtros por severidad y estado, y una insignia de "posible causa común";
   - detalle con: variables anómalas (valor contra media habitual), explicación de la IA con el aviso *"no es un diagnóstico confirmado"*, técnico asignado y su `razon`, repuestos y **línea de tiempo**.
4. **Cerrar incidente** (solo para el rol técnico): formulario con intervención, componentes, ¿falla confirmada? y minutos detenida. Llama a `POST /incidentes/{id}/cerrar`.
5. **Planificación** (gerente y supervisor): `GET /reportes/ultimo` con el resumen de la IA y tablas de preventivo, combustible, utilización y repuestos.
6. **Vista por rol:** el menú y el nivel de detalle cambian según `rol`.

**Modo degradado:**
- Si la API no responde en 5 s, lee `maquinas` e `incidentes` desde Firestore con el SDK web de Firebase.
- Muestra un aviso amarillo: *"Modo degradado: datos desde la réplica (solo lectura)"* y desactiva los botones de acción.

**Variables de entorno:** `VITE_API_URL`, `VITE_USE_MOCK` y `VITE_FIREBASE_*`. La configuración web de Firebase no es secreta, pero va en `.env` igual.

**Despliegue:** `firebase init hosting` (carpeta `dist`) y `npm run build && firebase deploy --only hosting`.

**Listo cuando:** la web publicada hace login contra AWS, muestra el mapa y los incidentes reales, cierra un incidente y, con la API cortada, sigue mostrando datos en modo degradado.

**Entregas:** la URL pública a **Enrique**, para el video.

---

## Puntos de encuentro con el equipo
| Cuándo | Qué se comprueba |
|---|---|
| Al terminar el paso 1 | Denilson pone tus URLs en su secreto y SFN-1 usa Gemini real |
| Cuando Denilson te pase la `API_URL` | Cambias de mock a datos reales |
| Antes de grabar | Pruebas el modo degradado junto con Denilson |
