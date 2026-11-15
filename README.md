# ArquiFusion Fleet

Plataforma serverless multi-nube (**AWS + Google Cloud**) que convierte la telemetría de flotas de maquinaria pesada en decisiones: anticipa fallas, asigna técnicos, controla repuestos y combustible, y aprende del historial.

- 🎥 Video (≤ 5 min): _pendiente_
- 🗺️ Arquitectura: [`docs/arquitectura.png`](docs/arquitectura.png)
- 📖 Contexto del equipo: [`docs/CONTEXTO_EQUIPO.md`](docs/CONTEXTO_EQUIPO.md)

## Estructura

```
contracts/      Formato de los mensajes (telemetría, incidente). Fuente de verdad.
simulator/      Simulador de máquinas con escenarios de demo
seed/           Datos iniciales: máquinas, técnicos, repuestos, mantenimientos
services/       Microservicios AWS (uno por carpeta, cada uno con su serverless.yml)
  _hola/        Prueba de despliegue (Fase 0)
  ingesta/      API Gateway → SQS → Lambda → DynamoDB + S3, detector
  incidentes/   Step Function 1: flujo de incidente
  planificacion/Step Function 2: planificación diaria
  historico/    Step Function 3: carga de datos históricos → Athena
  replica/      DynamoDB Streams → Google Firestore
  api/          Consultas para la web
gcp/            Cloud Run functions: ia (Gemini) y replica (Firestore)
frontend/       React + Vite (Firebase Hosting)
scripts/        Utilidades (verificación del Learner Lab, despliegue)
docs/           Diagrama y guías
```

## Desplegar un servicio de AWS

```bash
cd services/<servicio>
serverless deploy --stage dev
```

Requisitos: credenciales del Learner Lab en `~/.aws/credentials`, `serverless login`, Python 3.12.
