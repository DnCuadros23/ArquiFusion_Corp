"""Copia inicial a Firestore de todo lo que ya existe (el stream solo envía cambios nuevos).

Úsalo una vez, después de crear el secreto arquifusion/gcp:
    python3 replicar_todo.py --stage dev
"""
import argparse
import os

import boto3

from comun import de_dynamo
import replicador


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", default="dev")
    a = p.parse_args()
    os.environ.setdefault("SECRET_GCP", "arquifusion/gcp")
    secreto = replicador.leer_secreto()
    if not secreto:
        raise SystemExit("Falta el secreto arquifusion/gcp (ver README).")

    ddb = boto3.resource("dynamodb", region_name="us-east-1")
    for tabla, (coleccion, clave) in replicador.COLECCIONES.items():
        t, kw, total = ddb.Table(f"{a.stage}-{tabla}"), {}, 0
        while True:
            r = t.scan(**kw)
            for item in de_dynamo(r["Items"]):
                datos = {k: v for k, v in item.items() if k not in replicador.CAMPOS_PRIVADOS}
                replicador.enviar(secreto, {"coleccion": coleccion, "id": datos[clave],
                                            "operacion": "UPSERT", "datos": datos})
                total += 1
            if "LastEvaluatedKey" not in r:
                break
            kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]
        print(f"  OK  {total} documentos → Firestore/{coleccion}")


if __name__ == "__main__":
    main()
