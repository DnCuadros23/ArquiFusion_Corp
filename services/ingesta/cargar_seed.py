"""Carga los datos semilla de seed/*.json en las tablas del stage indicado.

Uso (desde services/ingesta, con credenciales del Learner Lab):
    python cargar_seed.py --stage dev
    python cargar_seed.py --stage prod --seed ../../seed

Es idempotente: volver a ejecutarlo sobrescribe los mismos registros.
Las máquinas se crean con el estado inicial; la telemetría y las estadísticas llegan después.
"""
import argparse
import json
from pathlib import Path

import boto3

from comun import a_dynamo

TENANT = "MINA_SUR"

# archivo -> (tabla, función que arma el ítem)
CARGAS = {
    "maquinas.json": ("t_maquinas", lambda x: {"tenant_id": TENANT, "estado": "OPERANDO",
                                                "riesgo": "NORMAL", **x}),
    "tecnicos.json": ("t_tecnicos", lambda x: {"tenant_id": TENANT, "incidentes_activos": 0, **x}),
    "repuestos.json": ("t_repuestos", lambda x: {"tenant_id": TENANT,
                                                  "repuesto_almacen": f"{x['repuesto_id']}#{x['almacen']}", **x}),
    "mantenimientos.json": ("t_mantenimientos", lambda x: dict(x)),
    "usuarios.json": ("t_usuarios", lambda x: {"tenant_id": TENANT, **x}),
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", default="dev")
    p.add_argument("--seed", default=str(Path(__file__).resolve().parents[2] / "seed"))
    args = p.parse_args()

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    carpeta = Path(args.seed)
    for archivo, (tabla, armar) in CARGAS.items():
        ruta = carpeta / archivo
        if not ruta.exists():
            print(f"  -   {archivo}: no existe todavía, se omite")
            continue
        registros = json.loads(ruta.read_text(encoding="utf-8"))
        t = dynamodb.Table(f"{args.stage}-{tabla}")
        with t.batch_writer() as lote:
            for r in registros:
                lote.put_item(Item=a_dynamo(armar(r)))
        print(f"  OK  {archivo}: {len(registros)} registros → {args.stage}-{tabla}")


if __name__ == "__main__":
    main()
