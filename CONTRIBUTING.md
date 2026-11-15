# Cómo trabajamos

## Ramas
- `main` siempre despliega. Nada de push directo.
- Ramas por área: `feat/datos-<algo>` (P1), `feat/flujos-<algo>` (P2), `feat/web-<algo>` (P3).
- PR pequeño → un compañero revisa (5 min) → merge. Integrar varias veces al día.

## Cuentas de AWS (importante)
Cada uno tiene **su propio Learner Lab** (cuenta distinta). Por eso:
- Cada uno prueba su servicio en **su** cuenta con `--stage dev`.
- La **cuenta de demo** es la de **una sola persona** (definirla en Fase 0). Ahí se despliega todo con `--stage prod` para la demo y el video.
- Nunca escribir un Account ID en el código: usar `${aws:accountId}` en `serverless.yml` y `context.invoked_function_arn` en Python.

## Convenciones
- Python 3.12, `role: arn:aws:iam::${aws:accountId}:role/LabRole`, región `us-east-1`.
- Nombres de recursos: `${sls:stage}-<nombre>` (ej. `dev-t_maquinas`).
- Tablas multi-tenant: PK `tenant_id` cuando aplique.
- Logs en JSON de una línea: `print(json.dumps({"tipo": "INFO", "log_datos": ...}))`.
- Los mensajes respetan `contracts/`. Si hay que cambiar un contrato, se avisa a los tres **antes**.

## Secretos
- AWS: Secrets Manager (`arquifusion/gcp`). GCP: Secret Manager.
- Nada de claves en código, `.env` o capturas del video.

## Antes de cerrar el día
- Apagar el simulador (EventBridge) para no gastar créditos.
- Hacer push de tu rama aunque esté a medias.
