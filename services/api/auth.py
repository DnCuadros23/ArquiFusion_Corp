"""Login con token Bearer + autorizador de API Gateway (tipo TOKEN)."""
import hashlib
import hmac
import json
import os
import secrets
import time

import boto3

from comun import de_dynamo, log, respuesta

ddb = boto3.resource("dynamodb")
t_usuarios = ddb.Table(os.environ["T_USUARIOS"])
t_tokens = ddb.Table(os.environ["T_TOKENS"])
DURACION_TOKEN = 8 * 3600
ROLES = {"tecnico", "supervisor", "gerente"}


def sha256(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def login(event, context):
    try:
        datos = json.loads(event.get("body") or "")
        usuario, password = str(datos["usuario"]), str(datos["password"])
    except (ValueError, KeyError, TypeError):
        return respuesta(400, {"error": "envía usuario y password"})

    u = de_dynamo(t_usuarios.get_item(Key={"usuario": usuario}).get("Item") or {})
    if not u or not hmac.compare_digest(u.get("password_sha256", ""), sha256(password)) or u.get("rol") not in ROLES:
        log("WARN", {"accion": "login_fallido", "usuario": usuario})
        return respuesta(401, {"error": "usuario o contraseña incorrectos"})

    token = secrets.token_urlsafe(32)
    sesion = {"token": token, "usuario": usuario, "rol": u["rol"], "tenant_id": u.get("tenant_id", "MINA_SUR"),
              "nombre": u.get("nombre", usuario), "tecnico_id": u.get("tecnico_id"),
              "expira": int(time.time()) + DURACION_TOKEN}
    t_tokens.put_item(Item={k: v for k, v in sesion.items() if v is not None})
    log("INFO", {"accion": "login", "usuario": usuario, "rol": u["rol"]})
    return respuesta(200, {k: sesion[k] for k in ("token", "rol", "tenant_id", "nombre")})


def politica(efecto, method_arn, contexto=None):
    # Permite todas las rutas de la API para que el resultado sirva aunque se cachee.
    arn_api = "/".join(method_arn.split("/")[:2]) + "/*/*"
    salida = {"principalId": (contexto or {}).get("usuario", "anonimo"),
              "policyDocument": {"Version": "2012-10-17",
                                 "Statement": [{"Action": "execute-api:Invoke", "Effect": efecto, "Resource": arn_api}]}}
    if contexto:
        salida["context"] = contexto
    return salida


def autorizador(event, context):
    encabezado = event.get("authorizationToken") or ""
    if not encabezado.startswith("Bearer "):
        raise Exception("Unauthorized")  # API Gateway responde 401
    sesion = de_dynamo(t_tokens.get_item(Key={"token": encabezado[7:].strip()}).get("Item") or {})
    if not sesion or sesion.get("expira", 0) < time.time():
        raise Exception("Unauthorized")
    contexto = {k: str(sesion[k]) for k in ("usuario", "rol", "tenant_id", "nombre", "tecnico_id") if sesion.get(k)}
    return politica("Allow", event["methodArn"], contexto)
