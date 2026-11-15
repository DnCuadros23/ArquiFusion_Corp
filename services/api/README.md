# services/api — carril ① · API para la web

Login con token Bearer (8 h), λ autorizador y las rutas de `contracts/interfaces.md` §3. El `tenant_id` y el `rol` siempre salen del token, nunca del cliente.

## Desplegar
```bash
cd services/api
serverless deploy --stage dev
```

La `API_URL` es la del endpoint `POST .../dev/api/login`, sin el `/login` final: `https://<id>.execute-api.us-east-1.amazonaws.com/dev/api`.

## Usuarios de demo
Créalos con este script (pide la contraseña por teclado):

```bash
python3 crear_usuario.py --stage dev --usuario tecnico1 --rol tecnico --nombre "Técnico Demo"
python3 crear_usuario.py --stage dev --usuario supervisor1 --rol supervisor --nombre "Supervisor Demo"
python3 crear_usuario.py --stage dev --usuario gerente1 --rol gerente --nombre "Gerente Demo"
```

Si Enrique ya subió `seed/usuarios.json`, también se cargan con `services/ingesta/cargar_seed.py`.

## Probar
```bash
TOKEN=$(curl -s -X POST "$API_URL/login" -H "Content-Type: application/json" -d '{"usuario":"supervisor1","password":"<tu-clave>"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s "$API_URL/maquinas" -H "Authorization: Bearer $TOKEN"
curl -s "$API_URL/incidentes?estado=TODOS" -H "Authorization: Bearer $TOKEN"
```

## Rutas
| Ruta | Quién | Nota |
|---|---|---|
| `POST /login` | todos | devuelve `token, rol, tenant_id, nombre` |
| `GET /maquinas`, `GET /maquinas/{id}` | todos | el detalle trae las últimas 50 lecturas y los incidentes |
| `GET /incidentes?estado=ABIERTOS\|CERRADOS\|TODOS` | todos | un técnico con `tecnico_id` ve solo los suyos; nunca se devuelve `task_token` |
| `POST /incidentes/{id}/cerrar` | técnico, supervisor | reanuda SFN-1 (`SendTaskSuccess`). Responde 409 si no está esperando cierre |
| `GET /tecnicos`, `GET /reportes/ultimo` | todos | `reportes` responde 404 hasta que corra SFN-2 |

## Pruebas (sin AWS)
```bash
python -m unittest discover -s tests -v
```
