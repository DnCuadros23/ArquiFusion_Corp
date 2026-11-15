"""Crea o actualiza un usuario de demo en <stage>-t_usuarios (la contraseña se guarda como SHA-256).

    python crear_usuario.py --stage dev --usuario tecnico1 --rol tecnico --nombre "Técnico Demo"
La contraseña se pide por teclado (no queda en el historial de la terminal).
"""
import argparse
import getpass
import hashlib

import boto3


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", default="dev")
    p.add_argument("--usuario", required=True)
    p.add_argument("--rol", required=True, choices=["tecnico", "supervisor", "gerente"])
    p.add_argument("--nombre", required=True)
    p.add_argument("--tecnico-id", help="si es técnico: su tecnico_id, para ver solo sus incidentes")
    a = p.parse_args()

    password = getpass.getpass("Contraseña de demo: ")
    item = {"usuario": a.usuario, "rol": a.rol, "nombre": a.nombre, "tenant_id": "MINA_SUR",
            "password_sha256": hashlib.sha256(password.encode("utf-8")).hexdigest()}
    if a.tecnico_id:
        item["tecnico_id"] = a.tecnico_id
    boto3.resource("dynamodb", region_name="us-east-1").Table(f"{a.stage}-t_usuarios").put_item(Item=item)
    print(f"OK  {a.usuario} ({a.rol}) en {a.stage}-t_usuarios")


if __name__ == "__main__":
    main()
