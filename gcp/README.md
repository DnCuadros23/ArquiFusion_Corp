# Google Cloud: IA (Gemini) y réplica (Firestore)

Contrato: `contracts/interfaces.md` §2. Ambas funciones validan el header `X-Arquifusion-Token` (variable `ARQUIFUSION_TOKEN`).

| Carpeta | Rutas | Variables |
|---|---|---|
| `ia/` | `POST /analizar`, `POST /resumen`, `GET /` (salud) | `ARQUIFUSION_TOKEN`; `GEMINI_API_KEY` (AI Studio) **o** `GOOGLE_CLOUD_PROJECT` (Vertex AI) |
| `replica/` | `POST /replica`, `GET /` (salud) | `ARQUIFUSION_TOKEN`; `FIREBASE_CREDENTIALS` solo fuera de Google Cloud |

**Cloud Run functions** (entrada `main`):

```bash
cd gcp/ia
gcloud functions deploy arquifusion-ia --gen2 --runtime=python312 --region=us-central1 --trigger-http \
  --allow-unauthenticated --entry-point=main --memory=512Mi --timeout=30s --max-instances=3 \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=<proyecto>,GOOGLE_CLOUD_LOCATION=global,GEMINI_MODEL=gemini-3-flash-preview --set-secrets=ARQUIFUSION_TOKEN=arquifusion-token:latest
```

**Alternativa gratuita (Render):** Root Directory `gcp/ia` o `gcp/replica`, build `pip install -r requirements.txt`, start `gunicorn main:app --timeout 60`.

**Prueba:**

```bash
curl -X POST <IA_URL>/analizar -H "Content-Type: application/json" -H "X-Arquifusion-Token: <token>" -d @gcp/ia/prueba_incidente.json
curl -X POST <REPLICA_URL>/replica -H "Content-Type: application/json" -H "X-Arquifusion-Token: <token>" -d @gcp/replica/prueba_replica.json
```

`firestore.rules`: lectura pública solo de `maquinas` e `incidentes` (datos simulados); escritura cerrada a clientes.
