"""Pruebas sin AWS:  python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))
import plan  # noqa: E402


def maq(mid, modelo="EXC-320", horas=5000, ult=4600, costo=120):
    return {"maquina_id": mid, "modelo": modelo, "zona": "TAJO_NORTE", "horas_motor": horas,
            "horas_ultimo_mant": ult, "costo_hora_usd": costo}


def lecturas(n=24, estado="OPERANDO", comb=37.0, carga=28.0, sube=0.0):
    return [{"estado": estado, "combustible_l_h": comb + sube * i, "carga_t": carga} for i in range(n)]


class TestPlan(unittest.TestCase):
    def test_preventivo_prioriza_y_ajusta_por_carga(self):
        ms = [maq("EXC-001", ult=4600), maq("EXC-002", ult=4400), maq("EXC-003", ult=4800)]
        ls = {"EXC-001": lecturas(), "EXC-002": lecturas(), "EXC-003": lecturas(carga=40)}
        f = {x["maquina_id"]: x for x in plan.preventivo(ms, ls)}
        self.assertEqual(f["EXC-002"]["estado"], "VENCIDO")         # 600 h > 500
        self.assertEqual(f["EXC-001"]["estado"], "OK")              # 400 h × 1.0 = 80 %
        self.assertGreater(f["EXC-003"]["factor_carga"], 1)         # más carga que su modelo → se adelanta
        self.assertEqual(plan.preventivo(ms, ls)[0]["maquina_id"], "EXC-002")

    def test_combustible_solo_contra_su_modelo(self):
        ms = [maq(f"CAM-00{i}", modelo="CAM-793") for i in range(1, 5)] + [maq("EXC-001")]
        ls = {f"CAM-00{i}": lecturas(comb=100, carga=200) for i in range(1, 4)}
        ls["CAM-004"] = lecturas(comb=135, carga=200, sube=0.5)      # +35 % y subiendo
        ls["EXC-001"] = lecturas(comb=37, carga=28)                  # otro modelo, solo: no se compara
        f = plan.combustible(ms, ls)
        self.assertEqual([x["maquina_id"] for x in f], ["CAM-004"])
        self.assertGreaterEqual(f[0]["desvio_pct"], 35)
        self.assertGreater(f[0]["tendencia_pct"], 0)
        self.assertIn("no demuestra una falla", f[0]["nota"])

    def test_utilizacion(self):
        ms = [maq("CAR-003", "CAR-994"), maq("CAM-010", "CAM-793"), maq("CAM-011", "CAM-793")]
        ls = {"CAR-003": lecturas(estado="RALENTI") + lecturas(n=2),
              "CAM-010": lecturas(n=24),
              "CAM-011": lecturas(n=12) + lecturas(n=12, estado="DETENIDA")}
        f = {x["maquina_id"]: x["hallazgos"] for x in plan.utilizacion(ms, ls)}
        self.assertIn("BAJA_UTILIZACION", f["CAR-003"])
        self.assertIn("JORNADA_EXCESIVA", f["CAM-010"])
        self.assertNotIn("CAM-011", f)

    def test_repuestos_faltante_e_irregular(self):
        stock = [
            {"repuesto_id": "FILTRO-AIRE-320", "nombre": "Filtro de aire", "almacen": "TALLER_CENTRAL", "stock": 3,
             "stock_minimo": 2, "modelos_compatibles": ["EXC-320"]},
            {"repuesto_id": "SELLO-HID", "nombre": "Sello hidráulico", "almacen": "TAJO_SUR", "stock": 10,
             "stock_minimo": 2, "modelos_compatibles": ["EXC-320"]},
            {"repuesto_id": "CORREA", "nombre": "Correa", "almacen": "TAJO_SUR", "stock": 9, "stock_minimo": 1,
             "modelos_compatibles": ["CAM-793"]},
        ]
        f = {x["repuesto_id"]: x for x in plan.repuestos(stock, {"SELLO-HID": 4}, ["EXC-320", "EXC-320"])}
        self.assertIn("FALTANTE_PROYECTADO", f["FILTRO-AIRE-320"]["alertas"])   # 3 − 2 kits = 1 < 2
        self.assertIn("CONSUMO_IRREGULAR", f["SELLO-HID"]["alertas"])
        self.assertNotIn("CORREA", f)

    def test_resumen_plantilla(self):
        rep = {"fecha": "2026-11-15", "preventivo": [{"maquina_id": "EXC-002", "estado": "VENCIDO"}],
               "combustible": [{"maquina_id": "CAM-004", "desvio_pct": 35}], "utilizacion": [], "repuestos": []}
        r = plan.resumen_plantilla(rep)
        self.assertIn("EXC-002", r["prioridades"][0])
        self.assertLessEqual(len(r["prioridades"]), 3)


class TestDefinicion(unittest.TestCase):
    def test_estados_y_ramas(self):
        import yaml  # noqa: PLC0415
        d = yaml.safe_load((AQUI.parent / "serverless.yml").read_text(encoding="utf-8"))
        definicion = d["stepFunctions"]["stateMachines"]["planificacion"]["definition"]
        estados = definicion["States"]
        destinos = {definicion["StartAt"]} | {e.get("Next") for e in estados.values()}
        destinos |= {c["Next"] for e in estados.values() for c in e.get("Catch", [])}
        destinos.discard(None)
        self.assertEqual(destinos - set(estados), set())
        self.assertEqual(len(estados["Analizar"]["Branches"]), 4)
        handlers = {f["handler"].split(".")[1] for f in d["functions"].values()}
        import ast  # noqa: PLC0415
        definidos = {n.name for n in ast.parse((AQUI.parent / "pasos_plan.py").read_text(encoding="utf-8")).body
                     if isinstance(n, ast.FunctionDef)}
        self.assertEqual(handlers - definidos, set())


if __name__ == "__main__":
    unittest.main()
