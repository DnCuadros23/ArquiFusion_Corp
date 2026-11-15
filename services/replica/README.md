# services/replica — carril ⑤ · Réplica multi-nube

Lee los Streams de `t_maquinas` y `t_incidentes` y envía cada cambio a `POST {replica_url}/replica` (Firestore, en Google Cloud). Nunca envía `task_token` ni las estadísticas internas del detector.

- **Sin el secreto `arquifusion/gcp`:** no hace nada y no falla. Se puede desplegar desde ya.
- **Si Google no responde:** Lambda reintenta 5 veces y luego deja el lote en la cola `<stage>-replica-dlq`.

## Desplegar
```bash
cd services/replica && serverless deploy --stage dev
```

## Cuando Matías pase los datos
```bash
aws secretsmanager create-secret --name arquifusion/gcp --secret-string '{"ia_url":"https://...","replica_url":"https://...","token":"..."}'
python3 replicar_todo.py --stage dev
```

`replicar_todo.py` es la copia inicial de lo que ya existía, porque el stream solo envía cambios nuevos.

Las Lambdas guardan el secreto en memoria. Si lo creas o cambias después de desplegar, vuelve a desplegar `replica` e `incidentes` para que lo lean de nuevo.

## Pruebas (sin AWS)
```bash
python -m unittest discover -s tests -v
```
