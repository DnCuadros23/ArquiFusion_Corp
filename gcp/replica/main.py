"""Función de réplica AWS -> Firestore (contracts/interfaces.md §2).

POST /replica  {"coleccion": "maquinas"|"incidentes", "id": "...", "operacion": "UPSERT"|"DELETE", "datos": {...}}
Idempotente: escribe siempre el mismo documento coleccion/id (set completo o delete).

Credenciales de Firestore:
  - Cloud Run functions: las de la cuenta de servicio por defecto (no hay que configurar nada)
  - Render / local: variable FIREBASE_CREDENTIALS con el JSON de la cuenta de servicio (en una línea)
"""
import hmac
import json
import os

from flask import Flask, jsonify, request

COLECCIONES = ('maquinas', 'incidentes')
OPERACIONES = ('UPSERT', 'DELETE')
PRIVADOS = ('task_token',)

_db = None


def db():
    global _db
    if _db is None:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not firebase_admin._apps:
            crudo = os.environ.get('FIREBASE_CREDENTIALS')
            if crudo:
                firebase_admin.initialize_app(credentials.Certificate(json.loads(crudo)))
            else:
                firebase_admin.initialize_app()
        _db = firestore.client()
    return _db


def error(codigo, mensaje):
    return jsonify({'error': mensaje}), codigo


def token_valido(req):
    esperado = os.environ.get('ARQUIFUSION_TOKEN', '')
    recibido = req.headers.get('X-Arquifusion-Token', '')
    return bool(esperado) and hmac.compare_digest(esperado, recibido)


def replicar(cuerpo):
    coleccion = cuerpo.get('coleccion')
    doc_id = cuerpo.get('id')
    operacion = cuerpo.get('operacion')
    if coleccion not in COLECCIONES:
        return error(400, 'coleccion debe ser maquinas o incidentes')
    if not isinstance(doc_id, str) or not doc_id or '/' in doc_id:
        return error(400, 'id inválido')
    if operacion not in OPERACIONES:
        return error(400, 'operacion debe ser UPSERT o DELETE')

    ref = db().collection(coleccion).document(doc_id)
    if operacion == 'DELETE':
        ref.delete()
    else:
        datos = cuerpo.get('datos')
        if not isinstance(datos, dict):
            return error(400, 'datos debe ser un objeto')
        datos = {k: v for k, v in datos.items() if k not in PRIVADOS}
        ref.set(datos)   # set completo: repetir la llamada deja el mismo documento
    print(json.dumps({'tipo': 'INFO', 'ruta': '/replica', 'coleccion': coleccion, 'id': doc_id, 'operacion': operacion}))
    return jsonify({'ok': True}), 200


def main(req):
    """Punto de entrada único (Cloud Run functions: --entry-point=main)."""
    ruta = req.path.rstrip('/') or '/'
    if req.method == 'GET' and ruta == '/':
        return jsonify({'ok': True, 'servicio': 'arquifusion-replica'}), 200
    if not token_valido(req):
        return error(401, 'Token inválido')
    if req.method != 'POST' or not ruta.endswith('/replica'):
        return error(404, 'Ruta no encontrada')
    cuerpo = req.get_json(silent=True)
    if not isinstance(cuerpo, dict):
        return error(400, 'El cuerpo debe ser un objeto JSON')
    try:
        return replicar(cuerpo)
    except Exception as e:
        print(json.dumps({'tipo': 'ERROR', 'mensaje': 'Fallo al escribir en Firestore', 'detalle': str(e)[:300]}))
        return error(500, 'No se pudo escribir en Firestore')


# Para Render o pruebas locales: gunicorn main:app
app = Flask(__name__)


@app.route('/', defaults={'ruta': ''}, methods=['GET', 'POST'])
@app.route('/<path:ruta>', methods=['GET', 'POST'])
def _todas(ruta):
    return main(request)
