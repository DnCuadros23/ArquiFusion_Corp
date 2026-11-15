import json
import os


def hola(event, context):
    cuenta = context.invoked_function_arn.split(":")[4]
    cuerpo = {"mensaje": "ArquiFusion Fleet vivo", "stage": os.environ.get("STAGE"), "cuenta": cuenta}
    print(json.dumps({"tipo": "INFO", "log_datos": cuerpo}))
    return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": json.dumps(cuerpo)}
