# lab01_v_b_workflow.py — Versión B: workflow con LLM (agencia baja)
#
# CONSIGNA
# Mismo problema que la Versión A — clasificar un reclamo de tarjeta de
# crédito — pero ahora usando un modelo de lenguaje para *entender* el
# texto, sin dejar que el modelo decida qué acción tomar.
#
# CÓMO SE RESUELVE
# Un `Agent` de ADK2 SIN `tools` clasifica el reclamo y devuelve un JSON
# con una forma fija, forzada por `output_schema` (un modelo Pydantic):
# categoría, prioridad, razón, tarjeta_id, si pide bloqueo y cuántos
# consumos desconoce. El agente no puede *hacer* nada — no tiene
# herramientas para llamar — solo puede *responder*. El mapeo de
# categoría → acción (`abrir_caso_fraude`, `bloquear_tarjeta`, etc.) es
# un diccionario de Python: el ruteo sigue siendo 100% determinista, el
# LLM solo rellena datos. Por eso esto es "agencia baja" y no un agente:
# mismo framework que la Versión C, pero sin tools no hay agencia real.
#
# CÓMO LEER LA SALIDA
# El campo `razon` es donde se nota que el modelo entendió el mensaje
# completo — incluso cuando trae dos pedidos distintos, cosa que el
# Versión A no lograba. El campo `accion` (y `accion_secundaria`, si el
# cliente pidió el bloqueo pero la categoría principal es otra) NO lo
# escribió el modelo: sale del diccionario `acciones` de abajo. El texto
# de `razon` cambia en cada corrida (es un LLM); la estructura del JSON
# no, porque `output_schema` la fuerza.
import os
import asyncio
import json
import re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from pydantic import BaseModel
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types


class ClasificacionReclamo(BaseModel):
    categoria: str
    prioridad: str
    razon: str
    tarjeta_id: Optional[str] = None
    pide_bloqueo: bool
    cantidad_consumos_desconocidos: Optional[int] = None


clasificador_agente = Agent(
    name="clasificador_reclamos",
    model="gemini-2.5-flash",
    instruction="""Clasificás reclamos de clientes de tarjeta de crédito de un banco argentino.

Categoría: "desconocimiento_consumo" (el cliente no reconoce uno o más
consumos), "bloqueo_tarjeta" (pide bloquear o dar de baja la tarjeta),
"limites" (consulta sobre límites o aumentos) o "consulta_general"
(cualquier otra cosa).

Prioridad: "alta" si hay desconocimiento de consumos o pedido de bloqueo,
"media" si es sobre límites, "baja" en el resto.

Completá tarjeta_id con los últimos 4 dígitos si se mencionan (o dejalo
vacío), pide_bloqueo con true si el cliente pide el bloqueo en cualquier
parte del mensaje, y cantidad_consumos_desconocidos con el número si se
menciona.""",
    output_schema=ClasificacionReclamo,
)

# Mapeo determinista categoría → acción. Esto es lo que hace que el
# sistema siga siendo auditable: la pregunta "¿por qué este reclamo fue a
# fraude?" se responde con esta línea de código, no con una inferencia
# estadística.
ACCIONES_POR_CATEGORIA = {
    'desconocimiento_consumo': 'abrir_caso_fraude',
    'bloqueo_tarjeta': 'bloquear_tarjeta',
    'limites': 'derivar_a_riesgo',
    'consulta_general': 'responder_faq',
}


def _extraer_json(texto_respuesta: str) -> dict:
    """
    Pela fences de markdown (```json ... ```) si vinieran, antes de
    parsear. `output_schema` reduce mucho la frecuencia de este problema
    frente a pedir el JSON solo por prompt, pero no la elimina del todo:
    el parser defensivo es el control, no una sugerencia en el prompt.
    """
    texto_limpio = texto_respuesta.strip()
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto_limpio, re.DOTALL)
    if match:
        texto_limpio = match.group(1)
    return json.loads(texto_limpio)


async def clasificar_con_llm(texto: str) -> dict:
    """
    Clasifica un reclamo con el Agent de ADK2 y aplica el ruteo
    determinista. El agente rellena datos; esta función decide la
    acción.
    """
    if not isinstance(texto, str) or not texto.strip():
        return {'error': 'texto de entrada inválido o vacío', 'metodo': 'workflow_llm_adk2'}

    runner = InMemoryRunner(agent=clasificador_agente)

    try:
        # InMemoryRunner(agent=...) usa por defecto app_name="InMemoryRunner",
        # no el nombre del agente — hay que crear la sesión y correrla con
        # runner.app_name en los dos lados, o falla con "Session not found".
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="sistema-clasificacion",
        )

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=texto)],
        )

        texto_respuesta = ""
        async for event in runner.run_async(
            user_id="sistema-clasificacion",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        texto_respuesta += part.text

        if not texto_respuesta:
            return {'error': 'el agente no generó una respuesta', 'metodo': 'workflow_llm_adk2'}

        resultado = _extraer_json(texto_respuesta)
        resultado['metodo'] = 'workflow_llm_adk2'
        resultado['accion'] = ACCIONES_POR_CATEGORIA.get(resultado['categoria'], 'derivar_a_analista')

        if resultado.get('pide_bloqueo') and resultado['accion'] != 'bloquear_tarjeta':
            resultado['accion_secundaria'] = 'bloquear_tarjeta'

        return resultado
    except (json.JSONDecodeError, KeyError, TypeError):
        return {'error': 'respuesta no parseable', 'raw': texto_respuesta, 'metodo': 'workflow_llm_adk2'}
    except Exception as e:
        return {'error': f'fallo la llamada al agente: {e}', 'metodo': 'workflow_llm_adk2'}


# Mismos casos de prueba que la Versión A, para comparar directamente.
casos = [
    "Desconozco tres consumos en mi tarjeta terminada en 4417 de los últimos 10 días, quiero que me la bloqueen y que me devuelvan la plata",
    "Perdí la billetera, necesito bloquear la tarjeta ya mismo",
    "¿Cuánto tarda la reposición de una tarjeta nueva?",
    "Hola, me llegó el resumen con un consumo en dólares que no reconozco y además quiero saber si tengo cobertura de seguro de compra",
]


async def main():
    for caso in casos:
        resultado = await clasificar_con_llm(caso)
        print(f"\nTexto: {caso[:60]}...")
        print(f"Resultado: {json.dumps(resultado, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
