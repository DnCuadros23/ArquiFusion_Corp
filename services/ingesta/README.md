# services/ingesta — carril ② + capa de datos

Crea las 10 tablas DynamoDB, el data lake S3, la cola SQS con DLQ, la API `POST /telemetria` con API key, la λ `recibir` (valida y encola) y la λ `ingesta` (guarda, detecta y abre incidentes).

## Desplegar
```bash
cd services/ingesta
serverless deploy --stage dev
```

Para obtener la API key:

```bash
aws apigateway get-api-keys --include-values --query "items[?name=='dev-arquifusion-ingesta'].value" --output text
```

Para cargar la semilla (cuando exista `seed/`):

```bash
python cargar_seed.py --stage dev
```

## Probar
```bash
curl -X POST "$INGESTA_URL/telemetria" -H "x-api-key: $API_KEY" -H "Content-Type: application/json" -d '{"tenant_id":"MINA_SUR","maquina_id":"EXC-007","modelo":"EXC-320","ts":"2026-11-15T15:00:00Z","zona":"TAJO_NORTE","lat":-16.7175,"lon":-71.865,"estado":"OPERANDO","horas_motor":4521.5,"temp_motor_c":120}'
```

Debe responder `202 {"encoladas": 1}`. Como la temperatura supera el límite físico, en `dev-t_incidentes` aparece un incidente `CRITICA`.

Pruebas de la lógica (sin AWS):

```bash
python -m unittest discover -s tests -v
```

## Notas
- El detector necesita 20 lecturas normales por máquina antes de evaluar (ver `contracts/interfaces.md` §4).
- Mientras SFN-1 no esté desplegada, el incidente queda en `DETECTADO` y se registra un `ERROR` en el log (es lo esperado).
- La máquina queda con `incidente_abierto` hasta que SFN-1 la cierre. Así no se abren incidentes duplicados.
- Otros servicios usan las tablas por nombre (`<stage>-t_<tabla>`) y los Streams mediante `${cf:arquifusion-ingesta-<stage>.TIncidentesStreamArn}`.
