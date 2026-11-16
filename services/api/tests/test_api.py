"""Pruebas sin AWS (boto3 simulado):  python -m unittest discover -s tests -v"""
import json
import os
import sys
import time
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# boto3 falso: las tablas son mocks y no se llama a AWS.
TABLAS = {}
falso = types.ModuleType("boto3")
falso.resource = lambda *_a, **_k: mock.Mock(Table=lambda n: TABLAS.setdefault(n, mock.Mock(name=n)))
falso.client = lambda *_a, **_k: mock.Mock()
condiciones = types.ModuleType("boto3.dynamodb.conditions")
condiciones.Key = mock.MagicMock()
sys.modules.update({"boto3": falso, "boto3.dynamodb": types.ModuleType("boto3.dynamodb"),
                    "boto3.dynamodb.conditions": condiciones})
for v in ("T_USUARIOS", "T_TOKENS", "T_MAQUINAS", "T_TELEMETRIA", "T_INCIDENTES", "T_TECNICOS", "T_REPORTES"):
    os.environ[v] = v

import auth  # noqa: E402
import rutas  # noqa: E402

INCIDENTES = [
    {"incidente_id": "a", "estado": "ASIGNADO", "creado_ts": "2026-11-15T10:00:00Z", "task_token": "x",
     "tecnico_asignado": {"tecnico_id": "TEC-01"}},
    {"incidente_id": "b", "estado": "CERRADO", "creado_ts": "2026-11-15T11:00:00Z"},
    {"incidente_id": "c", "estado": "DETECTADO", "creado_ts": "2026-11-15T12:00:00Z", "tecnico_asignado": None},
]


class TestAuth(unittest.TestCase):
    def setUp(self):
        TABLAS["T_USUARIOS"].get_item.return_value = {"Item": {
            "usuario": "tecnico1", "password_sha256": auth.sha256("demo123"), "rol": "tecnico", "nombre": "Rosa"}}

    def test_login_ok_y_fallido(self):
        ok = auth.login({"body": json.dumps({"usuario": "tecnico1", "password": "demo123"})}, None)
        self.assertEqual(ok["statusCode"], 200)
        self.assertEqual(json.loads(ok["body"])["rol"], "tecnico")
        self.assertIn("Access-Control-Allow-Origin", ok["headers"])
        malo = auth.login({"body": json.dumps({"usuario": "tecnico1", "password": "otra"})}, None)
        self.assertEqual(malo["statusCode"], 401)
        self.assertEqual(auth.login({"body": "no-json"}, None)["statusCode"], 400)

    def test_autorizador(self):
        arn = "arn:aws:execute-api:us-east-1:111:abc123/dev/GET/api/maquinas"
        TABLAS["T_TOKENS"].get_item.return_value = {"Item": {
            "token": "t", "usuario": "u", "rol": "gerente", "tenant_id": "MINA_SUR", "expira": int(time.time()) + 60}}
        p = auth.autorizador({"authorizationToken": "Bearer t", "methodArn": arn}, None)
        self.assertEqual(p["policyDocument"]["Statement"][0]["Effect"], "Allow")
        self.assertEqual(p["policyDocument"]["Statement"][0]["Resource"], "arn:aws:execute-api:us-east-1:111:abc123/dev/*/*")
        self.assertEqual(p["context"]["rol"], "gerente")
        with self.assertRaises(Exception):
            auth.autorizador({"authorizationToken": "sin-bearer", "methodArn": arn}, None)
        TABLAS["T_TOKENS"].get_item.return_value = {"Item": {"token": "t", "expira": int(time.time()) - 1}}
        with self.assertRaises(Exception):
            auth.autorizador({"authorizationToken": "Bearer t", "methodArn": arn}, None)


class TestRutas(unittest.TestCase):
    def test_filtros_y_sin_token(self):
        abiertos = rutas.filtrar_incidentes(INCIDENTES, None, {"rol": "supervisor"})
        self.assertEqual([i["incidente_id"] for i in abiertos], ["c", "a"])
        self.assertTrue(all("task_token" not in i for i in abiertos))
        self.assertEqual(len(rutas.filtrar_incidentes(INCIDENTES, "todos", {})), 3)
        propios = rutas.filtrar_incidentes(INCIDENTES, "ABIERTOS", {"rol": "tecnico", "tecnico_id": "TEC-01"})
        self.assertEqual([i["incidente_id"] for i in propios], ["a"])

    def test_validar_cierre(self):
        self.assertEqual(rutas.validar_cierre({"intervencion": "Cambio", "falla_confirmada": True, "minutos_detenida": 30}), [])
        self.assertTrue(rutas.validar_cierre({}))
        self.assertTrue(rutas.validar_cierre({"intervencion": "x", "minutos_detenida": -1}))

    def test_permisos_y_rutas(self):
        ev = {"httpMethod": "POST", "resource": "/api/incidentes/{id}/cerrar", "pathParameters": {"id": "a"},
              "body": "{}", "requestContext": {"authorizer": {"tenant_id": "MINA_SUR", "rol": "gerente"}}}
        self.assertEqual(rutas.handler(ev, None)["statusCode"], 403)
        self.assertEqual(rutas.handler(dict(ev, resource="/nada"), None)["statusCode"], 404)
        self.assertEqual(rutas.handler(dict(ev, requestContext={}), None)["statusCode"], 401)

    def test_cerrar_reanuda_flujo(self):
        TABLAS["T_INCIDENTES"].get_item.return_value = {"Item": dict(INCIDENTES[0], tenant_id="MINA_SUR")}
        ev = {"httpMethod": "POST", "resource": "/api/incidentes/{id}/cerrar", "pathParameters": {"id": "a"},
              "body": json.dumps({"intervencion": "Cambio de termostato", "falla_confirmada": True}),
              "requestContext": {"authorizer": {"tenant_id": "MINA_SUR", "rol": "tecnico", "usuario": "tecnico1"}}}
        r = rutas.handler(ev, None)
        self.assertEqual(r["statusCode"], 200, r["body"])
        enviado = rutas.sfn.send_task_success.call_args.kwargs
        self.assertEqual(enviado["taskToken"], "x")
        self.assertEqual(json.loads(enviado["output"])["cerrado_por"], "tecnico1")


if __name__ == "__main__":
    unittest.main()
