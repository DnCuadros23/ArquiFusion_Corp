"""Pruebas sin AWS:  python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import replicador  # noqa: E402

ARN_M = "arn:aws:dynamodb:us-east-1:1:table/dev-t_maquinas/stream/2026"
ARN_I = "arn:aws:dynamodb:us-east-1:1:table/dev-t_incidentes/stream/2026"


def reg(arn, evento, seq, imagen=None, claves=None):
    d = {"SequenceNumber": seq}
    if imagen:
        d["NewImage"] = imagen
    if claves:
        d["Keys"] = claves
    return {"eventSourceARN": arn, "eventName": evento, "dynamodb": d}


MAQ = lambda temp: {"tenant_id": {"S": "MINA_SUR"}, "maquina_id": {"S": "EXC-007"}, "riesgo": {"S": "NORMAL"},
                    "lat": {"N": "-15.84"}, "horas_motor": {"N": "4521"}, "stats": {"M": {}},
                    "ultima_lectura": {"M": {"temp_motor_c": {"N": temp}}}}
INC = {"tenant_id": {"S": "MINA_SUR"}, "incidente_id": {"S": "abc"}, "task_token": {"S": "secreto"},
       "analisis_ia": {"NULL": True}, "repuestos": {"L": []}, "cierre": {"M": {"falla_confirmada": {"BOOL": True}}}}


class TestReplica(unittest.TestCase):
    def test_deserializar(self):
        self.assertEqual(replicador.deserializar({"N": "4521"}), 4521)
        self.assertEqual(replicador.deserializar({"N": "-15.84"}), -15.84)
        self.assertIsNone(replicador.deserializar({"NULL": True}))
        self.assertEqual(replicador.deserializar({"L": [{"S": "a"}, {"BOOL": False}]}), ["a", False])

    def test_tabla_a_coleccion(self):
        self.assertEqual(replicador.coleccion_de(ARN_M), ("maquinas", "maquina_id"))
        self.assertEqual(replicador.coleccion_de(ARN_I), ("incidentes", "incidente_id"))
        self.assertEqual(replicador.coleccion_de("arn:aws:dynamodb:x:1:table/dev-t_tokens/stream/1"), (None, None))

    def test_ultimo_cambio_gana_y_sin_privados(self):
        ops = replicador.a_operaciones([
            reg(ARN_M, "MODIFY", "100", MAQ("90")), reg(ARN_M, "MODIFY", "101", MAQ("95")),
            reg(ARN_I, "INSERT", "102", INC),
            reg(ARN_I, "REMOVE", "103", claves={"tenant_id": {"S": "MINA_SUR"}, "incidente_id": {"S": "viejo"}}),
        ])
        self.assertEqual(len(ops), 3)
        maq = next(o for o in ops if o["coleccion"] == "maquinas")
        self.assertEqual(maq["datos"]["ultima_lectura"]["temp_motor_c"], 95)
        self.assertEqual(maq["_secuencias"], ["100", "101"])
        self.assertNotIn("stats", maq["datos"])
        inc = next(o for o in ops if o["id"] == "abc")
        self.assertNotIn("task_token", inc["datos"])
        self.assertTrue(inc["datos"]["cierre"]["falla_confirmada"])
        self.assertEqual(next(o for o in ops if o["id"] == "viejo")["operacion"], "DELETE")

    def test_sin_secreto_no_bloquea(self):
        with mock.patch.object(replicador, "leer_secreto", return_value=None):
            self.assertEqual(replicador.handler({"Records": [reg(ARN_I, "INSERT", "1", INC)]}, None),
                             {"batchItemFailures": []})

    def test_falla_reporta_secuencia_mas_antigua(self):
        records = [reg(ARN_I, "INSERT", "99", INC), reg(ARN_M, "MODIFY", "100", MAQ("90"))]
        with mock.patch.object(replicador, "leer_secreto", return_value={"replica_url": "x", "token": "t"}), \
                mock.patch.object(replicador, "enviar", side_effect=RuntimeError("caído")):
            self.assertEqual(replicador.handler({"Records": records}, None),
                             {"batchItemFailures": [{"itemIdentifier": "99"}]})


if __name__ == "__main__":
    unittest.main()
