# Web ArquiFusion Fleet (React + Vite + Leaflet)

```bash
cd frontend
cp .env.example .env        # VITE_USE_MOCK=true para trabajar sin AWS
npm install
npm run dev                 # http://localhost:5173  (demo: tecnico / supervisor / gerente, clave demo123)
```

Con la API real: `VITE_USE_MOCK=false` y `VITE_API_URL=https://<id>.execute-api.us-east-1.amazonaws.com/prod/api`.

**Modo degradado:** si la API no responde en 5 s, las listas de máquinas e incidentes se leen de Firestore (variables `VITE_FIREBASE_*`) y se desactivan las acciones.

**Despliegue en Firebase Hosting:**

```bash
npm install -g firebase-tools
firebase login
firebase use --add            # elegir el proyecto
npm run build
firebase deploy --only hosting
```
