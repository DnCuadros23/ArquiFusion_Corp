# ArquiFusion Fleet

Plataforma serverless multi-nube (**AWS + Google Cloud**) que convierte la telemetría de flotas de maquinaria pesada en decisiones: anticipa fallas, asigna técnicos, controla repuestos y combustible, y aprende del historial.

- 🎥 Video (≤ 5 min): https://youtu.be/gPjCpdl_1H4
- 🗺️ Arquitectura: [`docs/arquitectura.png`](docs/arquitectura.png)
- 📖 Contexto completo del equipo: [`docs/CONTEXTO_EQUIPO.md`](docs/CONTEXTO_EQUIPO.md)
- ✅ Tareas: [Denilson](docs/tareas/DENILSON.md) · [Matías](docs/tareas/MATIAS.md) · [Enrique](docs/tareas/ENRIQUE.md) · Acuerdos: [`contracts/interfaces.md`](contracts/interfaces.md)

## Estructura

```
contracts/     Formato de los mensajes (telemetría, incidente) con ejemplos. Fuente de verdad.
simulator/     Simulador de máquinas con escenarios de demo            (Enrique)
seed/          Datos iniciales: máquinas, técnicos, repuestos           (Enrique)
services/      Microservicios AWS, cada uno con su serverless.yml
  _hola/       Prueba de despliegue (Fase 0)
  ingesta/     API Gateway → SQS → Lambda → DynamoDB + S3, detector    (Denilson)
  incidentes/  Step Function 1: flujo de incidente                     (Denilson)
  planificacion/ Step Function 2: planificación diaria                 (Denilson)
  historico/   Step Function 3: datos históricos → Athena              (Denilson)
  replica/     DynamoDB Streams → Google Firestore                     (Denilson)
  api/         Consultas para la web                                   (Denilson)
gcp/           Cloud Run functions: ia (Gemini) y replica (Firestore)  (Matías)
frontend/      React + Vite en Firebase Hosting                        (Matías)
scripts/       verificar_learner_lab.sh
docs/          Contexto del equipo y diagrama
```

Las carpetas de `services/` se crean cuando su responsable empieza (Fase 1).

## Desplegar un servicio de AWS

```bash
cd services/<servicio>
serverless deploy --stage dev
```

Requisitos: credenciales del Learner Lab en `~/.aws/credentials`, `serverless login`, Python 3.12.

## Checkpoint 0 (cada integrante)

```bash
bash scripts/verificar_learner_lab.sh          # todos los servicios en OK
cd services/_hola && serverless deploy --stage dev   # GET .../dev/hola → 200
```

## Reglas rápidas

- Nada de push directo a `main`: rama `feat/<area>-<algo>` → PR → revisión de un compañero → merge.
- Cero secretos en el repo: van en AWS Secrets Manager (`arquifusion/gcp`) y GCP Secret Manager.
- Sin Account IDs en el código: `${aws:accountId}` en YAML, `context.invoked_function_arn` en Python.
- Apagar el simulador al terminar de probar.
