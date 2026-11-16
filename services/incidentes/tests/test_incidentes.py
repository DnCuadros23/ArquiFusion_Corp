"""Pruebas sin AWS:  python -m unittest discover -s tests -v"""
import json
import sys
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

import logica  # noqa: E402

INCIDENTE = json.loads((AQUI.parents[2] / "contracts" / "incidente.schema.json").read_text(encoding="utf-8"))["examples"][0]
LAT, LON = INCIDENTE["lat"], INCIDENTE["lon"]

TECNICOS = [
    {"tecnico_id": "TEC-01", "nombre": "Ana", "especialidad": "MOTOR", "lat": LAT, "lon": LON, "disponible": False},
    {"tecnico_id": "TEC-02", "nombre": "Luis", "especialidad": "MOTOR", "lat": LAT + 0.05, "lon": LON, "disponible": True},
    {"tecnico_id": "TEC-03", "nombre": "Rosa", "especialidad": "MOTOR", "lat": LAT + 0.01, "lon": LON, "disponible": True,
     "incidentes_activos": 0},
    {"tecnico_id": "TEC-04", "nombre": "Juan", "especialidad": "HIDRAULICO", "lat": LAT, "lon": LON, "disponible": True},
    {"tecnico_id": "TEC-05", "nombre": "Eva", "especialidad": "GENERAL", "lat": LAT, "lon": LON, "disponible": True},
]


class TestAsignacion(unittest.TestCase):
    def test_respeta_especialidad_y_disponibilidad(self):
        t, razon = logica.elegir_tecnico(TECNICOS, "MOTOR", LAT, LON)
        self.assertEqual(t["tecnico_id"], "TEC-03")          # el más cercano de MOTOR que está disponible
        self.assertIn("TEC-01", razon)                         # se explica por qué no el ocupado
        self.assertIn("Especialidad MOTOR", razon)

    def test_carga_de_trabajo_pesa(self):
        tecnicos = [dict(TECNICOS[2], incidentes_activos=3), TECNICOS[1]]
        t, _ = logica.elegir_tecnico(tecnicos, "MOTOR", LAT, LON)
        self.assertEqual(t["tecnico_id"], "TEC-02")          # más lejos pero libre

    def test_respaldo_general(self):
        t, razon = logica.elegir_tecnico(TECNICOS, "ELECTRICO", LAT, LON)
        self.assertEqual(t["tecnico_id"], "TEC-05")
        self.assertIn("GENERAL", razon)

    def test_sin_tecnicos(self):
        t, razon = logica.elegir_tecnico([TECNICOS[0]], "MOTOR", LAT, LON)
        self.assertIsNone(t)
        self.assertIn("supervisor", razon)


class TestRepuestos(unittest.TestCase):
    def test_compatibles_por_modelo_y_especialidad(self):
        reps = [
            {"repuesto_id": "FILTRO", "almacen": "A", "stock": 2, "especialidad": "MOTOR", "modelos_compatibles": ["EXC-320"]},
            {"repuesto_id": "FILTRO", "almacen": "B", "stock": 9, "especialidad": "MOTOR", "modelos_compatibles": ["EXC-320"]},
            {"repuesto_id": "SELLO", "almacen": "A", "stock": 5, "especialidad": "HIDRAULICO", "modelos_compatibles": ["EXC-320"]},
            {"repuesto_id": "CORREA", "almacen": "A", "stock": 5, "especialidad": "MOTOR", "modelos_compatibles": ["CAM-793"]},
        ]
        c = logica.candidatos_repuesto(reps, "MOTOR", "EXC-320")
        self.assertEqual([(r["repuesto_id"], r["almacen"]) for r in c], [("FILTRO", "B"), ("FILTRO", "A")])


class TestPlantilla(unittest.TestCase):
    def test_formato_y_sin_diagnostico(self):
        inc = {k: v for k, v in INCIDENTE.items() if k != "analisis_ia"}
        a = logica.analisis_plantilla(inc)
        self.assertEqual(set(a), set(INCIDENTE["analisis_ia"]))
        self.assertFalse(a["es_diagnostico"])
        self.assertEqual(a["fuente"], "PLANTILLA")
        self.assertEqual(a["especialidad_sugerida"], "MOTOR")
        self.assertEqual(set(a["mensajes_por_rol"]), {"tecnico", "supervisor", "gerente"})
        self.assertIn("no permiten afirmar", a["resumen"])


class TestDefinicion(unittest.TestCase):
    def test_todos_los_next_existen(self):
        import yaml  # noqa: PLC0415  (solo para esta prueba)
        texto = (AQUI.parent / "serverless.yml").read_text(encoding="utf-8")
        definicion = yaml.safe_load(texto)["stepFunctions"]["stateMachines"]["incidentes"]["definition"]
        estados = definicion["States"]
        destinos = {definicion["StartAt"]}
        for e in estados.values():
            destinos |= {e.get("Next"), e.get("Default")}
            destinos |= {c["Next"] for c in e.get("Choices", []) + e.get("Catch", [])}
        destinos.discard(None)
        self.assertEqual(destinos - set(estados), set())
        self.assertTrue(any(e.get("End") for e in estados.values()))


if __name__ == "__main__":
    unittest.main()
