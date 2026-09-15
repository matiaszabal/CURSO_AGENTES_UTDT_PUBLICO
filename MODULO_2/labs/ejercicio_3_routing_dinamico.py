"""
Ejercicio 3 — Dynamic Model Routing (ADK2)
Módulo 2: Diseño de Sistemas Agénticos — UTDT

Un clasificador (siempre con el modelo más barato) decide la complejidad de
cada query, y un router instancia un LlmAgent con el modelo correspondiente
en runtime. Al final se compara el costo real contra la alternativa de usar
siempre el modelo más caro.

Patrón de routing: `LlmAgent.model` es estático una vez instanciado el agente,
así que el router no "cambia" el modelo de un agente existente — construye un
LlmAgent nuevo con el modelo correspondiente en cada request.

Dominio: mesa de reclamos de tarjeta de crédito — las mismas 5 queries que
usa el Ejercicio 1.

Setup y cómo correrlo: ver README.md de esta carpeta.
Corre con una API key gratuita de Google AI Studio (https://aistudio.google.com/apikey):
    export GOOGLE_API_KEY="tu-api-key"
    export GOOGLE_GENAI_USE_VERTEXAI=FALSE

Cuota — atención con gemini-2.5-pro: 2 de las 5 queries de evaluación rutean a
ese modelo, que suele tener la cuota gratuita más ajustada de los tres. Si te
da 429 solo ahí, cambiá MODELO_MAP["compleja"] por "gemini-2.5-flash": el
patrón de routing queda idéntico, solo cambian los números de costo. Ver
"Errores frecuentes" en el README.
"""

import asyncio
import json
import time

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# -------------------------------------------------------
# 1. Modelos disponibles con sus costos (por millón de tokens)
# -------------------------------------------------------

MODELOS_CONFIG = {
    "gemini-2.5-flash-lite": {
        "input_cost_per_mtok": 0.10,
        "output_cost_per_mtok": 0.40,
        "descripcion": "Rápido y económico — tareas simples y estructuradas",
    },
    "gemini-2.5-flash": {
        "input_cost_per_mtok": 0.30,
        "output_cost_per_mtok": 2.50,
        "descripcion": "Balance costo/rendimiento — análisis moderado",
    },
    "gemini-2.5-pro": {
        "input_cost_per_mtok": 1.25,
        "output_cost_per_mtok": 10.00,
        "descripcion": "Máxima capacidad — razonamiento complejo, multi-paso",
    },
}
# Precios de referencia (USD por millón de tokens) según
# https://ai.google.dev/gemini-api/docs/pricing — verificar antes de usar
# estos números para una decisión real, pueden cambiar.

MODELO_MAP = {
    "simple": "gemini-2.5-flash-lite",
    "media": "gemini-2.5-flash",
    "compleja": "gemini-2.5-pro",
}


# -------------------------------------------------------
# 2. Helper genérico: correr un LlmAgent y devolver el texto final
#    (mismo idiomatismo de Runner + InMemorySessionService que el
#    Ejercicio 1 — se reutiliza tal cual, con el agente como parámetro)
# -------------------------------------------------------

async def ejecutar_agente(agente: LlmAgent, mensaje_usuario: str, app_name: str, session_id: str) -> str:
    """Ejecuta un LlmAgent con un mensaje de usuario y devuelve la respuesta final."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agente,
        app_name=app_name,
        session_service=session_service,
    )

    await session_service.create_session(
        app_name=app_name,
        user_id="usuario-test",
        session_id=session_id,
    )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=mensaje_usuario)],
    )

    # No cortamos el generador con `break` apenas llega la respuesta final:
    # un `async for` interrumpido a mitad de camino dispara GeneratorExit en
    # medio del span de OpenTelemetry que instrumenta el Runner, y esa
    # cancelación cruza de contexto async y corrompe llamadas subsiguientes
    # (ValueError: "was created in a different Context"). Dejamos que el
    # generador drene solo — son pocos eventos por turno, no es costoso.
    respuesta_final = ""
    async for event in runner.run_async(
        user_id="usuario-test",
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            respuesta_final = event.content.parts[0].text

    return respuesta_final


# -------------------------------------------------------
# 3. Clasificador de complejidad (siempre con el modelo más barato)
# -------------------------------------------------------

clasificador_agent = LlmAgent(
    name="clasificador_complejidad",
    model="gemini-2.5-flash-lite",
    instruction="""
    Clasificás la complejidad de la query que te manda el usuario, para decidir
    a qué modelo de IA rutearla.

    Respondé ÚNICAMENTE con un JSON válido:
    {
        "complejidad": "simple" | "media" | "compleja",
        "justificacion": "razón breve en una oración"
    }

    Criterios:
    - simple: pregunta factual directa, clasificación binaria, extracción de dato único
    - media: análisis con 2-3 pasos, síntesis de información, respuesta estructurada
    - compleja: razonamiento multi-paso, análisis crítico, decisión con múltiples variables
    """,
)


async def clasificar_complejidad(query: str, session_id: str) -> dict:
    """Clasifica la query y devuelve {'complejidad': ..., 'justificacion': ...}."""
    contenido = await ejecutar_agente(
        clasificador_agent, query, app_name="router_clasificador", session_id=session_id
    )
    contenido = contenido.strip()

    try:
        # El modelo suele devolver el JSON envuelto en un bloque markdown
        # aunque el prompt diga "ÚNICAMENTE JSON" — se limpia antes de parsear.
        if "```json" in contenido:
            contenido = contenido.split("```json")[1].split("```")[0].strip()
        elif "```" in contenido:
            contenido = contenido.split("```")[1].split("```")[0].strip()

        clasificacion = json.loads(contenido)
        complejidad = clasificacion.get("complejidad", "media")
        justificacion = clasificacion.get("justificacion", "Clasificación por defecto")
    except (json.JSONDecodeError, KeyError, IndexError):
        # La salida de un LLM es una entrada no confiable: si no se puede
        # parsear, degradamos a "media" — nunca a "simple" (mandaría queries
        # complejas a un modelo que no las resuelve) ni a "compleja"
        # (convertiría cualquier inestabilidad del clasificador en una factura).
        complejidad = "media"
        justificacion = "Error en clasificación, usando nivel medio por defecto"

    return {"complejidad": complejidad, "justificacion": justificacion}


# -------------------------------------------------------
# 4. Ejecución con el modelo ruteado — acá pasa el patrón central del
#    ejercicio: se instancia un LlmAgent NUEVO con el modelo elegido en
#    runtime, porque `model` queda fijo una vez construido el agente.
# -------------------------------------------------------

def crear_agente_ejecutor(modelo: str) -> LlmAgent:
    """Router per-query: instancia el agente con el modelo correcto en runtime."""
    return LlmAgent(
        name="agente_enrutado",
        model=modelo,
        instruction="Sos un asistente de IA experto. Respondé en español, de forma clara y precisa.",
    )


async def ejecutar_con_modelo_ruteado(query: str, modelo: str, session_id: str) -> dict:
    """Ejecuta la query con el modelo seleccionado por el router y mide costo/latencia."""
    config = MODELOS_CONFIG[modelo]
    agente = crear_agente_ejecutor(modelo)

    inicio = time.time()
    respuesta = await ejecutar_agente(
        agente, query, app_name="router_ejecutor", session_id=session_id
    )
    latencia_ms = (time.time() - inicio) * 1000

    # Estimación aproximada de tokens (por palabras, no tokens reales de la
    # API) — alcanza para comparar el costo entre modelos apples-to-apples.
    tokens_input_estimados = len(query.split()) * 1.3
    tokens_output_estimados = len(respuesta.split()) * 1.3

    costo = (
        (tokens_input_estimados / 1_000_000) * config["input_cost_per_mtok"]
        + (tokens_output_estimados / 1_000_000) * config["output_cost_per_mtok"]
    )

    return {
        "respuesta": respuesta,
        "tokens_usados": int(tokens_input_estimados + tokens_output_estimados),
        # Desagregados — los necesita analizar_ahorro_costo_v2 para facturar
        # la línea de base con el mismo tráfico real, no con una heurística.
        "tokens_input": int(tokens_input_estimados),
        "tokens_output": int(tokens_output_estimados),
        "costo_estimado_usd": costo,
        "latencia_ms": latencia_ms,
    }


# -------------------------------------------------------
# 5. Evaluación comparativa: 5 queries del dominio de reclamos de tarjeta
# -------------------------------------------------------
# ¿Sin cuota o con un 429? Dejá dos casos (uno simple y uno complejo) — baja
# de ~10 a ~4 llamadas y alcanza para ver el contraste de costo, que es el punto.

QUERIES_EVALUACION = [
    {
        "query": 'Clasificá este reclamo de tarjeta en una categoría: "No reconozco un consumo de $48.500 en TIENDA ONLINE SRL del 18/06".',
        "complejidad_esperada": "simple",
        "descripcion": "Clasificación de reclamo en categoría cerrada",
    },
    {
        "query": "Un reclamo por $415.000 por compra no reconocida en el exterior lleva 32 días en análisis y el titular envió una carta documento. Evaluá el riesgo operacional y reputacional del caso y recomendá un curso de acción, considerando el plazo de respuesta comprometido y la exposición ante el organismo de defensa del consumidor.",
        "complejidad_esperada": "compleja",
        "descripcion": "Evaluación de riesgo con múltiples variables",
    },
    {
        "query": "Resumí en 3 puntos qué documentación respaldatoria conviene pedirle a un titular que desconoce un consumo realizado con tarjeta presente.",
        "complejidad_esperada": "media",
        "descripcion": "Síntesis de criterio operativo",
    },
    {
        "query": '¿Qué significa "contracargo" en el circuito de una marca de tarjeta?',
        "complejidad_esperada": "simple",
        "descripcion": "Definición de término del dominio",
    },
    {
        "query": "Diseñá los criterios de un gate de aprobación humana para la liquidación de reclamos: umbral de monto, excepciones por tipo de reclamo, evidencia mínima que debe adjuntarse y quién firma en cada tramo. Considerá el trade-off entre tiempo de resolución y riesgo de pago indebido.",
        "complejidad_esperada": "compleja",
        "descripcion": "Diseño de control con trade-off explícito",
    },
]


def analizar_ahorro_costo(resultados: list[dict]) -> None:
    """
    Analiza y reporta el ahorro de costo del routing vs. usar siempre el modelo
    más caro. OJO: esta línea de base tiene un defecto a propósito — ver
    analizar_ahorro_costo_v2 más abajo. Vale la pena ver por qué el primer
    número da mal antes de ver el corregido.
    """
    print(f"\n{'='*60}")
    print("ANÁLISIS DE AHORRO v1 (línea de base con heurística) — Dynamic Model Routing")
    print(f"{'='*60}")

    costo_con_routing = sum(r["costo_estimado_usd"] for r in resultados)
    tokens_totales = sum(r["tokens_usados"] for r in resultados)

    # Costo si siempre usáramos el modelo más caro — heurística: asume que el
    # 60% de los tokens son de output y los factura todos a ese precio,
    # ignorando el 40% de input. Es el defecto que corrige la v2.
    costo_sin_routing = sum(
        (r["tokens_usados"] * 0.6 / 1_000_000) * MODELOS_CONFIG["gemini-2.5-pro"]["output_cost_per_mtok"]
        for r in resultados
    )

    ahorro_pct = (1 - costo_con_routing / costo_sin_routing) * 100 if costo_sin_routing > 0 else 0

    print(f"\nCosto total CON routing:  ${costo_con_routing:.6f}")
    print(f"Costo total SIN routing:  ${costo_sin_routing:.6f}")
    print(f"Ahorro estimado:          {ahorro_pct:.1f}%")
    print(f"Tokens procesados:        {tokens_totales:,}")

    print(f"\n{'Modelo':<25} {'Queries':>8} {'Costo Total':>14}")
    print("-" * 50)

    por_modelo: dict[str, dict] = {}
    for r in resultados:
        m = r["modelo_seleccionado"]
        if m not in por_modelo:
            por_modelo[m] = {"count": 0, "costo": 0.0}
        por_modelo[m]["count"] += 1
        por_modelo[m]["costo"] += r["costo_estimado_usd"]

    for modelo, stats in por_modelo.items():
        print(f"{modelo:<25} {stats['count']:>8} ${stats['costo']:>13.6f}")

    if ahorro_pct < 0:
        print(f"\n⚠️  El ahorro dio NEGATIVO. El patrón de routing funciona — la línea de base está")
        print(f"    mal calculada. Ver ANÁLISIS DE AHORRO v2 abajo para el número real.")


def analizar_ahorro_costo_v2(resultados: list[dict], modelo_baseline: str = "gemini-2.5-pro") -> None:
    """
    Igual que analizar_ahorro_costo, pero con una línea de base comparable:
    el MISMO tráfico (mismos tokens de input y de output) facturado íntegramente
    al modelo de referencia. No usa ninguna heurística de "% de output" — por
    eso es la comparación correcta.
    """
    cfg_base = MODELOS_CONFIG[modelo_baseline]

    costo_con_routing = sum(r["costo_estimado_usd"] for r in resultados)
    costo_sin_routing = sum(
        (r["tokens_input"] / 1_000_000) * cfg_base["input_cost_per_mtok"]
        + (r["tokens_output"] / 1_000_000) * cfg_base["output_cost_per_mtok"]
        for r in resultados
    )

    ahorro_pct = (1 - costo_con_routing / costo_sin_routing) * 100 if costo_sin_routing > 0 else 0

    print(f"\n{'='*60}")
    print(f"ANÁLISIS DE AHORRO v2 — línea de base: todo a {modelo_baseline}")
    print(f"{'='*60}")
    print(f"Costo total CON routing:  ${costo_con_routing:.6f}")
    print(f"Costo total SIN routing:  ${costo_sin_routing:.6f}")
    print(f"Ahorro real:              {ahorro_pct:.1f}%")

    tokens_totales = sum(r["tokens_input"] + r["tokens_output"] for r in resultados)
    for r in resultados:
        share = (r["tokens_input"] + r["tokens_output"]) / tokens_totales * 100
        print(f"  {r['modelo_seleccionado']:<20} share de tokens: {share:5.1f}%")

    print(f"\nConclusión: el ahorro del routing es una propiedad de la mezcla de tráfico,")
    print(f"no del patrón en sí — corré esto sobre tu propio corpus antes de prometer un %.")


async def main():
    resultados = []

    print("EVALUACIÓN — Dynamic Model Router con ADK2 (Google AI Studio)")
    print("=" * 60)

    for i, caso in enumerate(QUERIES_EVALUACION):
        print(f"\n[Caso] {caso['descripcion']}")
        print(f"Query: {caso['query'][:80]}...")

        session_id = f"router-eval-{i}"

        clasificacion = await clasificar_complejidad(caso["query"], session_id=f"{session_id}-clf")
        complejidad = clasificacion["complejidad"]
        modelo_seleccionado = MODELO_MAP.get(complejidad, "gemini-2.5-flash")

        ejecucion = await ejecutar_con_modelo_ruteado(
            caso["query"], modelo_seleccionado, session_id=f"{session_id}-exec"
        )

        match_esperado = complejidad == caso["complejidad_esperada"]
        resultado = {
            "complejidad": complejidad,
            "modelo_seleccionado": modelo_seleccionado,
            "justificacion_routing": clasificacion["justificacion"],
            **ejecucion,
        }
        resultados.append(resultado)

        print(f"Complejidad detectada: {complejidad} "
              f"({'✓' if match_esperado else '✗'} esperaba {caso['complejidad_esperada']})")
        print(f"Modelo usado:          {modelo_seleccionado}")
        print(f"Justificación:         {clasificacion['justificacion']}")
        print(f"Latencia:              {resultado['latencia_ms']:.0f}ms")
        print(f"Costo estimado:        ${resultado['costo_estimado_usd']:.6f}")

    # Reporte de ahorro — primero el roto (v1), después el real (v2): vale la
    # pena ver por qué el primer número da mal antes de ver el corregido.
    analizar_ahorro_costo(resultados)
    analizar_ahorro_costo_v2(resultados)

    # Accuracy del router
    matches = sum(
        1 for r, c in zip(resultados, QUERIES_EVALUACION)
        if r["complejidad"] == c["complejidad_esperada"]
    )
    print(f"\nAccuracy del router: {matches}/{len(QUERIES_EVALUACION)} "
          f"({matches/len(QUERIES_EVALUACION)*100:.0f}%)")


if __name__ == "__main__":
    asyncio.run(main())
