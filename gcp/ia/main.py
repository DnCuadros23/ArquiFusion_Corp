"""Función de IA de ArquiFusion (Gemini).

Rutas (contracts/interfaces.md §2):
  POST /analizar  -> analisis_ia de un incidente
  POST /resumen   -> resumen diario para el gerente
  GET  /          -> salud (útil para "despertar" el servicio antes de la demo)

Corre igual en:
  - Cloud Run functions:  --entry-point=main
  - Render / local:       gunicorn main:app
Credenciales de Gemini, en este orden:
  - GEMINI_API_KEY (Google AI Studio, gratis)
  - si no existe, Vertex AI con GOOGLE_CLOUD_PROJECT
"""
import hmac
import json
import os
from typing import List, Literal

from flask import Flask, jsonify, request
from pydantic import BaseModel, ValidationError

MODELO = os.environ.get('GEMINI_MODEL', 'gemini-3-flash-preview')


# ---------- Esquemas de salida (iguales a contracts/incidente.schema.json) ----------

class MensajesPorRol(BaseModel):
    tecnico: str
    supervisor: str
    gerente: str


class AnalisisIA(BaseModel):
    nivel_riesgo: Literal['BAJO', 'MEDIO', 'ALTO']
    resumen: str
    posibles_causas_a_revisar: List[str]
    especialidad_sugerida: Literal['MOTOR', 'HIDRAULICO', 'ELECTRICO', 'TREN_RODAJE', 'GENERAL']
    mensajes_por_rol: MensajesPorRol


class ResumenDiario(BaseModel):
    resumen_gerente: str
    prioridades: List[str]


# ---------- Gemini ----------

_cliente = None


def cliente():
    global _cliente
    if _cliente is None:
        from google import genai
        clave = os.environ.get('GEMINI_API_KEY')
        if clave:
            _cliente = genai.Client(api_key=clave)
        else:
            _cliente = genai.Client(vertexai=True,
                                    project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
                                    location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'global'))
    return _cliente


def preguntar_a_gemini(prompt, esquema):
    from google.genai import types
    respuesta = cliente().models.generate_content(
        model=MODELO,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type='application/json',
            response_schema=esquema,
        ),
    )
    return esquema.model_validate_json(respuesta.text)


# ---------- Prompts ----------

INSTRUCCIONES_ANALISIS = """Eres un asistente de mantenimiento de maquinaria pesada (minería y construcción).
Recibes un incidente detectado automáticamente a partir de la telemetría de una máquina.

Reglas obligatorias:
- Usa SOLO los datos del incidente: variables anómalas (valor, media habitual, z en desviaciones estándar, minutos persistente), máquina, modelo, zona, historial y grupo de causa común. No inventes datos.
- NUNCA afirmes un diagnóstico. Una anomalía no es una falla confirmada. Di que la situación "merece revisión" y lista causas A REVISAR, no causas confirmadas.
- nivel_riesgo: BAJO si es una sola variable con desviación moderada; MEDIO si varias variables se desvían juntas de forma persistente; ALTO si hay 3 o más variables muy desviadas o valores fuera de rango físico.
- especialidad_sugerida: la especialidad técnica más adecuada para revisar (MOTOR, HIDRAULICO, ELECTRICO, TREN_RODAJE o GENERAL).
- posibles_causas_a_revisar: de 2 a 4 elementos cortos.
- Redacta 3 mensajes distintos en español:
  * tecnico: detalle técnico (variables, valores, z, minutos) y qué revisar primero. Máximo 3 líneas.
  * supervisor: urgencia y quién atiende si hay técnico asignado. Máximo 2 líneas.
  * gerente: impacto en una sola línea, sin tecnicismos ni valores numéricos de sensores.
- Si grupo_causa_comun no es nulo, menciona que hay otras máquinas afectadas en la misma zona y, si se da, el clima, SOLO como hipótesis a investigar.
- resumen: 1 o 2 oraciones en español.
"""

INSTRUCCIONES_RESUMEN = """Eres un asistente que resume la planificación diaria de una flota de maquinaria pesada para el gerente.
Usa SOLO los datos recibidos (preventivo, combustible, utilización, repuestos). No inventes cifras.
- resumen_gerente: texto en español de 5 a 8 líneas, claro y sin tecnicismos.
- prioridades: exactamente 3 acciones concretas para hoy, ordenadas de mayor a menor urgencia.
Si una lista viene vacía, dilo en lugar de suponer.
"""

CAMPOS_PRIVADOS = ('task_token', 'analisis_ia', 'cierre')


def prompt_analisis(incidente):
    datos = {k: v for k, v in incidente.items() if k not in CAMPOS_PRIVADOS}
    return f"{INSTRUCCIONES_ANALISIS}\nIncidente (JSON):\n{json.dumps(datos, ensure_ascii=False)}"


def prompt_resumen(reporte):
    return f"{INSTRUCCIONES_RESUMEN}\nReporte diario (JSON):\n{json.dumps(reporte, ensure_ascii=False)}"


# ---------- HTTP ----------

def error(codigo, mensaje):
    return jsonify({'error': mensaje}), codigo


def token_valido(req):
    esperado = os.environ.get('ARQUIFUSION_TOKEN', '')
    recibido = req.headers.get('X-Arquifusion-Token', '')
    return bool(esperado) and hmac.compare_digest(esperado, recibido)


def analizar(incidente):
    for campo in ('maquina_id', 'variables_anomalas'):
        if campo not in incidente:
            return error(400, f'Falta el campo {campo}')
    try:
        analisis = preguntar_a_gemini(prompt_analisis(incidente), AnalisisIA)
    except ValidationError as e:
        print(json.dumps({'tipo': 'ERROR', 'mensaje': 'Respuesta de Gemini inválida', 'detalle': str(e)[:300]}))
        return error(503, 'La IA devolvió una respuesta inválida')
    except Exception as e:
        print(json.dumps({'tipo': 'ERROR', 'mensaje': 'Gemini no respondió', 'detalle': str(e)[:300]}))
        return error(503, 'La IA no está disponible')

    salida = analisis.model_dump()
    salida['posibles_causas_a_revisar'] = salida['posibles_causas_a_revisar'][:4]
    salida['es_diagnostico'] = False   # nunca es un diagnóstico, diga lo que diga el modelo
    salida['fuente'] = 'GEMINI'
    print(json.dumps({'tipo': 'INFO', 'ruta': '/analizar', 'maquina_id': incidente.get('maquina_id'),
                      'nivel_riesgo': salida['nivel_riesgo']}))
    return jsonify(salida), 200


def resumir(reporte):
    try:
        resumen = preguntar_a_gemini(prompt_resumen(reporte), ResumenDiario)
    except Exception as e:
        print(json.dumps({'tipo': 'ERROR', 'mensaje': 'Fallo en /resumen', 'detalle': str(e)[:300]}))
        return error(503, 'La IA no está disponible')
    salida = resumen.model_dump()
    salida['prioridades'] = salida['prioridades'][:3]
    return jsonify(salida), 200


def main(req):
    """Punto de entrada único (Cloud Run functions: --entry-point=main)."""
    ruta = req.path.rstrip('/') or '/'
    if req.method == 'GET' and ruta == '/':
        return jsonify({'ok': True, 'servicio': 'arquifusion-ia', 'modelo': MODELO}), 200
    if not token_valido(req):
        return error(401, 'Token inválido')
    if req.method != 'POST':
        return error(405, 'Método no permitido')
    cuerpo = req.get_json(silent=True)
    if not isinstance(cuerpo, dict):
        return error(400, 'El cuerpo debe ser un objeto JSON')
    if ruta.endswith('/analizar'):
        return analizar(cuerpo)
    if ruta.endswith('/resumen'):
        return resumir(cuerpo)
    return error(404, 'Ruta no encontrada')


# Para Render o pruebas locales: gunicorn main:app
app = Flask(__name__)


@app.route('/', defaults={'ruta': ''}, methods=['GET', 'POST'])
@app.route('/<path:ruta>', methods=['GET', 'POST'])
def _todas(ruta):
    return main(request)
