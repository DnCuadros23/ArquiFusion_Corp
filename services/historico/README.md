# services/historico — carril ⑥ · SFN-3

```
EventBridge (domingos) → DescargarDatasets → IniciarCrawler → (Wait 20 s ↔ EstadoCrawler) hasta READY
   → ConsultarAthena (.sync) → ActualizarUmbrales (t_umbrales)
```

- **Fuentes públicas:**
  - [AI4I 2020](https://archive.ics.uci.edu/dataset/601) (UCI): 10 000 registros con etiqueta de falla. Se guarda en `s3://<datalake>/raw/historico/ai4i/`.
  - Open-Meteo: clima diario de los últimos 30 días por zona, en `raw/historico/clima/`.
- **Glue crawler `arquifusion-ai4i-<stage>`:** cataloga el CSV como la tabla `arquifusion_<stage>.ai4i`.
- **Athena:** compara los registros con falla contra los normales.
- **Resultado en `t_umbrales`** (modelo `REFERENCIA_AI4I`). Con los datos reales sale, por ejemplo: *"En registros con falla, el desgaste acumulado es 35 % mayor y el torque 27 % mayor que en operación normal"*. Son **patrones de referencia, no reglas de diagnóstico**.

## Desplegar y ejecutar
```bash
cd services/historico && npm install && serverless deploy --stage dev
aws stepfunctions start-execution --state-machine-arn arn:aws:states:us-east-1:<cuenta>:stateMachine:arquifusion-historico-dev
```

Tarda de 2 a 3 minutos, sobre todo por el crawler. Para ver el resultado:

```bash
aws dynamodb scan --table-name dev-t_umbrales --query "Items[].interpretacion.S" --output table
```

## Pruebas (sin AWS ni internet)
```bash
python -m unittest discover -s tests -v
```
