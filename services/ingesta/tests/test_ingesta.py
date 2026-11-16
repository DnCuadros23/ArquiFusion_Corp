"""Pruebas de la lógica pura (sin AWS):  python -m unittest discover -s tests -v"""
import json
import random
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

from contrato import validar  # noqa: E402
from detector import CALENTAMIENTO, evaluar  # noqa: E402

EJEMPLO = json.loads((AQUI.parents[2] / "contracts" / "telemetria.schema.json").read_text(encoding="utf-8"))["examples"][0]
T0 = datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)


def lectura(i, **cambios):
    base = dict(EJEMPLO, ts=(T0 + timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    base.update(cambios)
    return base


def normal(i, rnd):
    return lectura(i, temp_motor_c=rnd.uniform(85, 92), vibracion_mm_s=rnd.uniform(3.5, 4.5),
                   presion_hid_bar=rnd.uniform(300, 330), combustible_l_h=rnd.uniform(35, 40))


class TestContrato(unittest.TestCase):
    def test_ejemplo_valido(self):
        self.assertEqual(validar(EJEMPLO), [])

    def test_errores(self):
        self.assertIn("falta 'ts'", validar({k: v for k, v in EJEMPLO.items() if k != "ts"}))
        self.assertTrue(validar(dict(EJEMPLO, maquina_id="exc7")))
        self.assertTrue(validar(dict(EJEMPLO, estado="VOLANDO")))
        self.assertTrue(validar(dict(EJEMPLO, temp_motor_c="90")))
        self.assertTrue(validar(dict(EJEMPLO, extra=1)))
        self.assertTrue(validar(dict(EJEMPLO, ts="ayer")))
        self.assertTrue(validar([EJEMPLO]))


class TestDetector(unittest.TestCase):
    def calentar(self, rnd, n=30):
        stats = None
        for i in range(n):
            resultado, stats = evaluar(normal(i, rnd), stats)
            self.assertIsNone(resultado, f"falso positivo en lectura normal {i}")
        return stats

    def test_operacion_normal_sin_alertas(self):
        rnd = random.Random(1)
        stats = self.calentar(rnd, 200)
        self.assertGreater(stats["temp_motor_c"]["n"], CALENTAMIENTO)

    def test_pico_aislado_no_alerta(self):
        rnd = random.Random(2)
        stats = self.calentar(rnd)
        resultado, stats = evaluar(lectura(31, temp_motor_c=105), stats)
        self.assertIsNone(resultado)
        resultado, _ = evaluar(normal(32, rnd), stats)
        self.assertIsNone(resultado)

    def test_degradacion_gradual_multivariable(self):
        rnd = random.Random(3)
        stats = self.calentar(rnd)
        severidades = []
        for k in range(1, 12):
            r, stats = evaluar(lectura(30 + k, temp_motor_c=88.5 + 2 * k, vibracion_mm_s=4 + 0.4 * k,
                                       presion_hid_bar=315, combustible_l_h=37.5 + 1.2 * k), stats)
            severidades.append(r["severidad"] if r else None)
        self.assertIn("CRITICA", severidades)
        self.assertIsNone(severidades[0], "no debe alertar con una sola lectura")
        r_final_vars = {v["variable"] for v in r["variables_anomalas"]}
        self.assertTrue({"temp_motor_c", "vibracion_mm_s", "combustible_l_h"} <= r_final_vars)
        self.assertGreater(r["variables_anomalas"][0]["minutos_persistente"], 0)

    def test_dos_variables_es_media(self):
        rnd = random.Random(4)
        stats = self.calentar(rnd)
        r = None
        for k in range(1, 5):
            r, stats = evaluar(lectura(30 + k, temp_motor_c=100, vibracion_mm_s=7,
                                       presion_hid_bar=315, combustible_l_h=37.5), stats)
        self.assertEqual(r["severidad"], "MEDIA")

    def test_limite_fisico_es_critica_inmediata(self):
        r, _ = evaluar(lectura(0, temp_motor_c=120), None)
        self.assertEqual(r["severidad"], "CRITICA")


if __name__ == "__main__":
    unittest.main()
