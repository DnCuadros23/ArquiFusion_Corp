"""Pruebas sin AWS ni internet:  python -m unittest discover -s tests -v"""
import csv
import io
import sys
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import hist  # noqa: E402

CSV_AI4I = ("﻿UDI,Product ID,Type,Air temperature [K],Process temperature [K],Rotational speed [rpm],"
            "Torque [Nm],Tool wear [min],Machine failure,TWF,HDF,PWF,OSF,RNF\n"
            "1,M14860,M,298.1,308.6,1551,42.8,0,0,0,0,0,0,0\n"
            "2,L47181,L,298.2,308.7,1408,46.3,3,0,0,0,0,0,0\n"
            "3,L47182,L,298.1,308.5,1282,60.7,216,1,0,0,0,1,0\n")


def athena(filas):
    def fila(valores):
        return {"Data": [{"VarCharValue": str(v)} for v in valores]}
    enc = ["falla", "registros", "dif_temperatura_k", "rpm", "torque_nm", "desgaste_min", "potencia_w"]
    return {"ResultSet": {"Rows": [fila(enc)] + [fila(f) for f in filas]}}


class TestHistorico(unittest.TestCase):
    def test_limpiar_ai4i(self):
        limpio, filas, fallas = hist.limpiar_ai4i(CSV_AI4I)
        self.assertEqual((filas, fallas), (3, 1))
        lector = list(csv.DictReader(io.StringIO(limpio)))
        self.assertEqual(lector[2]["torque_nm"], "60.7")
        self.assertNotIn("﻿", limpio)
        self.assertTrue(all(" " not in c and "[" not in c for c in lector[0]))   # nombres aptos para Athena

    def test_formato_cambiado(self):
        with self.assertRaises(ValueError):
            hist.limpiar_ai4i("a,b\n1,2\n")

    def test_umbrales(self):
        r = athena([[0, 9661, 10.0, 1540, 39.6, 106, 6400], [1, 339, 9.5, 1496, 50.2, 144, 7500]])
        items = hist.umbrales(hist.filas_athena(r))
        por_var = {i["variable"]: i for i in items}
        self.assertEqual(por_var["torque_nm"]["cambio_pct"], 26.8)
        self.assertIn("mayor", por_var["desgaste_min"]["interpretacion"])
        self.assertIn("menor", por_var["rpm"]["interpretacion"])
        self.assertEqual(items[0]["variable"], "desgaste_min")       # el cambio más grande primero
        self.assertTrue(all(i["modelo"] == "REFERENCIA_AI4I" for i in items))

    def test_umbrales_sin_clases(self):
        with self.assertRaises(ValueError):
            hist.umbrales(hist.filas_athena(athena([[0, 10, 1, 1, 1, 1, 1]])))

    def test_definicion(self):
        import yaml  # noqa: PLC0415
        d = yaml.safe_load((AQUI.parent / "serverless.yml").read_text(encoding="utf-8"))
        definicion = d["stepFunctions"]["stateMachines"]["historico"]["definition"]
        estados = definicion["States"]
        destinos = {definicion["StartAt"]} | {e.get("Next") for e in estados.values()} | {e.get("Default") for e in estados.values()}
        destinos |= {c["Next"] for e in estados.values() for c in e.get("Catch", []) + e.get("Choices", [])}
        destinos.discard(None)
        self.assertEqual(destinos - set(estados), set())


if __name__ == "__main__":
    unittest.main()
