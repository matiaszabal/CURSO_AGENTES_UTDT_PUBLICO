# lab01_ej2_investigacion.py — Aparte opcional: agente de investigación
#
# CONSIGNA
# Dado un tema, investigarlo en varios pasos: planificar qué preguntas
# responder, buscar información para cada una, evaluar si alcanza o hay
# que seguir buscando, y sintetizar un resumen final. El ciclo clásico
# Reason → Act → Observe → Reason.
#
# CÓMO SE RESUELVE
# A diferencia de la Versión C (donde el propio agente decide qué tool llamar
# y en qué orden), acá el control de flujo es explícito: un `while` en
# Python decide cuándo seguir investigando y cuándo pasar a sintetizar
# (función `investigar_tema`, más abajo). El modelo no orquesta nada —
# solo se lo llama en dos puntos puntuales, como un `Agent` de ADK2 de un
# solo turno y sin tools: una vez para planificar (devuelve 3 preguntas)
# y una vez para sintetizar (devuelve el resumen final). La búsqueda
# (`buscar_informacion`) es una función de Python sobre un diccionario
# fijo — nadie "decide" llamarla, el código la invoca directo en cada
# iteración del `while`.
#
# Es el contraste que vale la pena comparar con la Versión C: mismo
# framework (ADK2) en los dos casos, pero acá la arquitectura decide
# cuándo se llama al modelo y cuándo se corta el loop; en la Versión C esa
# decisión la toma el modelo mismo, turno a turno.
#
# CÓMO LEER LA SALIDA
# Cada corrida imprime los 4 pasos en orden ([PLANIFICAR], [INVESTIGAR]
# ×N, [EVALUAR] ×N, [SINTETIZAR]) y termina con el resumen final. El plan
# de preguntas y el texto del resumen no son deterministas — puede
# cambiar el número de iteraciones si el modelo devuelve menos de 3
# preguntas en el plan — pero el *flujo de control* (cuándo se corta el
# loop) sí lo es: depende de `iteraciones` y `max_iteraciones`, dos
# variables de Python, no de una decisión del modelo.
import os
import asyncio
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

# --- Estado del agente ---

class EstadoAgente(TypedDict):
    """Estado completo del agente de investigación."""
    tema: str
    plan_investigacion: list[str]
    busquedas_realizadas: list[dict]
    iteraciones: int
    max_iteraciones: int
    resumen_final: str
    continuar_investigando: bool

# --- Herramienta mock (simula búsquedas reales) ---

BASE_CONOCIMIENTO = {
    "agentes ia": """Los agentes IA son sistemas autónomos que combinan modelos de lenguaje
    con herramientas, memoria y orquestación. Pueden tomar decisiones, ejecutar acciones
    y aprender de los resultados. Ejemplos: AutoGPT, AgentGPT, sistemas multi-agente.""",

    "google adk2": """Google Agent Development Kit 2 (ADK2) es el framework oficial de Google
    para construir agentes IA en Google Cloud Platform. Incluye soporte nativo para MCP, A2A,
    integración con servicios de Google Cloud y despliegue en Cloud Run. Lanzado en 2025.""",

    "mcp protocol": """Model Context Protocol (MCP) es un estándar abierto lanzado por Anthropic
    en noviembre 2024 para conectar modelos de lenguaje con herramientas externas. Usa JSON-RPC
    sobre stdio o HTTP/SSE. Adoptado por LangGraph, CrewAI, OpenAI SDK y ADK2.""",

    "langgraph": """LangGraph es un framework de LangChain Inc. para construir agentes con flujo
    de estado explícito. Modela el agente como un grafo dirigido donde los nodos son funciones
    y las aristas son transiciones. Facilita la recuperación de fallos mediante serialización
    del estado.""",

    "agency spectrum": """El Agency Spectrum es el concepto de que la autonomía de los sistemas IA
    es un continuo, no binario. Va desde scripts deterministas hasta agentes completamente autónomos.
    La calibración correcta depende de la variabilidad de la tarea y la tolerancia al riesgo.""",
}

def buscar_informacion(query: str) -> str:
    """
    Simula una búsqueda de información. En producción, esto llamaría
    a una API de búsqueda real (Google Search, Tavily, etc.)

    Args:
        query: Pregunta o término de búsqueda

    Returns:
        Texto con información encontrada
    """
    query_lower = query.lower()
    resultados = []

    for clave, contenido in BASE_CONOCIMIENTO.items():
        if any(palabra in query_lower for palabra in clave.split()):
            resultados.append(f"[Resultado para '{clave}']: {contenido}")

    if resultados:
        return "\n\n".join(resultados)
    return f"No se encontró información específica sobre '{query}'. Intenta con términos más generales."

# --- Agentes ADK2 de un solo turno (sin tools) ---

planificador_agente = Agent(
    name="planificador_investigacion",
    model="gemini-2.5-flash",
    instruction="Sos un asistente de investigación. Tu tarea es planificar una investigación.",
)

sintetizador_agente = Agent(
    name="sintetizador_investigacion",
    model="gemini-2.5-flash",
    instruction="Sos un experto en síntesis de información técnica. Escribís en español claro y preciso.",
)


async def _llamar_agente(agente: Agent, prompt: str, user_id: str) -> str:
    """Invoca un Agent ADK2 de un solo turno y devuelve el texto final."""
    runner = InMemoryRunner(agent=agente)
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
    )

    content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])

    respuesta = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    respuesta += part.text

    return respuesta

# --- Pasos del flujo (uno por cada nodo del flujo) ---

async def paso_planificar(estado: EstadoAgente) -> EstadoAgente:
    """Planifica qué aspectos del tema investigar."""
    print(f"\n[PLANIFICAR] Tema: {estado['tema']}")

    prompt = f"""Para investigar el tema "{estado['tema']}",
    listá exactamente 3 preguntas clave que deberías responder.
    Respondé con una lista numerada, solo las preguntas, sin explicaciones adicionales."""

    respuesta = await _llamar_agente(planificador_agente, prompt, user_id="investigacion-plan")

    lineas = [l.strip() for l in respuesta.split('\n') if l.strip()]
    preguntas = [l.lstrip('123456789. )') for l in lineas if l[0].isdigit()][:3]

    print(f"[PLANIFICAR] Plan: {preguntas}")

    return {
        **estado,
        "plan_investigacion": preguntas,
        "continuar_investigando": True,
    }

def paso_investigar(estado: EstadoAgente) -> EstadoAgente:
    """Ejecuta las búsquedas según el plan. No llama a ningún agente."""
    print(f"\n[INVESTIGAR] Iteración {estado['iteraciones'] + 1}")

    nuevas_busquedas = []

    idx = estado['iteraciones']
    if idx < len(estado['plan_investigacion']):
        pregunta = estado['plan_investigacion'][idx]
        resultado = buscar_informacion(pregunta)
        nuevas_busquedas.append({
            "pregunta": pregunta,
            "resultado": resultado,
        })
        print(f"[INVESTIGAR] Pregunta: {pregunta[:60]}...")

    return {
        **estado,
        "busquedas_realizadas": estado['busquedas_realizadas'] + nuevas_busquedas,
        "iteraciones": estado['iteraciones'] + 1,
    }

def paso_evaluar(estado: EstadoAgente) -> EstadoAgente:
    """Evalúa si hay suficiente información o si se debe continuar investigando."""
    print(f"\n[EVALUAR] {len(estado['busquedas_realizadas'])} búsquedas realizadas")

    continuar = (
        estado['iteraciones'] < len(estado['plan_investigacion']) and
        estado['iteraciones'] < estado['max_iteraciones']
    )

    print(f"[EVALUAR] ¿Continuar? {continuar}")

    return {
        **estado,
        "continuar_investigando": continuar,
    }

async def paso_sintetizar(estado: EstadoAgente) -> EstadoAgente:
    """Genera el resumen final de la investigación."""
    print(f"\n[SINTETIZAR] Generando resumen...")

    contexto = "\n\n".join([
        f"Pregunta: {b['pregunta']}\nRespuesta: {b['resultado']}"
        for b in estado['busquedas_realizadas']
    ])

    prompt = f"""Basándote en la siguiente información recopilada sobre "{estado['tema']}",
    escribí un resumen técnico estructurado de 3-4 párrafos.

INFORMACIÓN RECOPILADA:
{contexto}

El resumen debe ser coherente, técnico y útil para estudiantes universitarios."""

    respuesta = await _llamar_agente(sintetizador_agente, prompt, user_id="investigacion-sintesis")

    return {
        **estado,
        "resumen_final": respuesta,
    }

# --- Orquestación explícita: el `while` decide el flujo ---

async def investigar_tema(tema: str, max_iteraciones: int = 3) -> str:
    """
    Ejecuta el agente de investigación sobre un tema dado. El flujo
    planificar → investigar → evaluar → [investigar de nuevo | sintetizar]
    está escrito como un `while` en código Python: el criterio de corte
    (`estado["continuar_investigando"]`) lo decide `paso_evaluar`, no el
    modelo.
    """
    estado = EstadoAgente(
        tema=tema,
        plan_investigacion=[],
        busquedas_realizadas=[],
        iteraciones=0,
        max_iteraciones=max_iteraciones,
        resumen_final="",
        continuar_investigando=True,
    )

    estado = await paso_planificar(estado)

    while estado["continuar_investigando"]:
        estado = paso_investigar(estado)
        estado = paso_evaluar(estado)

    estado = await paso_sintetizar(estado)
    return estado["resumen_final"]


async def main():
    temas = [
        "Agentes IA y el framework ADK2 de Google",
        "El protocolo MCP y su impacto en el ecosistema de agentes",
    ]

    for tema in temas:
        print(f"\n{'='*70}")
        print(f"TEMA: {tema}")
        print(f"{'='*70}")
        resumen = await investigar_tema(tema)
        print(f"\nRESUMEN FINAL:\n{resumen}")


if __name__ == "__main__":
    asyncio.run(main())
