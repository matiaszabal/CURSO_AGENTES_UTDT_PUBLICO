"""
Ejercicio 2 — Sistema Multiagente con Procesamiento Paralelo (ADK2)
Módulo 2: Diseño de Sistemas Agénticos — UTDT

Tres agentes de análisis (sentimiento, urgencia, tema) corridos en paralelo
con ParallelAgent y comparados contra la misma corrida en secuencial para
medir el speedup real. El módulo también define un cuarto agente
(`agregador`) y un pipeline completo (`pipeline_completo`) que lo encadena
después de los tres análisis — no lo ejecuta el benchmark de abajo (que solo
mide el paralelismo), pero queda armado para que lo pruebes vos si querés
ver la síntesis completa (ver README, sección "Adaptar el dominio").

Setup y cómo correrlo: ver README.md de esta carpeta.
Corre con una API key gratuita de Google AI Studio (https://aistudio.google.com/apikey):
    export GOOGLE_API_KEY="tu-api-key"
    export GOOGLE_GENAI_USE_VERTEXAI=FALSE

Cuota: este es el ejercicio que más rápido agota el tier gratuito — dispara
3 requests en la misma fracción de segundo, y lo repite 3 veces (una por
mensaje de MENSAJES_TEST). Si ves un 429, recortá MENSAJES_TEST a un solo
mensaje. Ver "Errores frecuentes" en el README.
"""

import asyncio
import time
from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types


# -------------------------------------------------------
# 1. Agentes especializados de análisis
# -------------------------------------------------------

analizador_sentimiento = LlmAgent(
    name="analizador_sentimiento",
    model="gemini-2.5-flash",  # Modelo liviano para tarea estructurada
    instruction="""
    Analizás el sentimiento emocional del mensaje del cliente.
    Respondé ÚNICAMENTE con un JSON válido con este formato exacto:
    {
        "sentimiento": "positivo" | "neutro" | "negativo" | "muy_negativo",
        "intensidad": 1-10,
        "indicadores": ["lista", "de", "palabras", "clave"]
    }
    """,
    output_key="analisis_sentimiento",
)

analizador_urgencia = LlmAgent(
    name="analizador_urgencia",
    model="gemini-2.5-flash",
    instruction="""
    Evaluás la urgencia del mensaje del cliente.
    Respondé ÚNICAMENTE con un JSON válido con este formato exacto:
    {
        "nivel_urgencia": "baja" | "media" | "alta" | "critica",
        "requiere_humano": true | false,
        "tiempo_respuesta_sugerido": "inmediato" | "1 hora" | "mismo día" | "48 horas"
    }
    """,
    output_key="analisis_urgencia",
)

clasificador_tema = LlmAgent(
    name="clasificador_tema",
    model="gemini-2.5-flash",
    instruction="""
    Clasificás el tema principal del mensaje del titular en el contexto de una mesa de
    reclamos de tarjeta de crédito.
    Respondé ÚNICAMENTE con un JSON válido con este formato exacto:
    {
        "categoria": "desconocimiento_consumo" | "cobro_duplicado" | "servicio_no_prestado"
                     | "fraude" | "estado_de_reclamo" | "documentacion" | "otro",
        "sub_categoria": "descripción breve",
        "accion_sugerida": "descripción de qué debería hacer el agente"
    }
    """,
    output_key="clasificacion_tema",
)


# -------------------------------------------------------
# 2. Agente de agregación de resultados
# -------------------------------------------------------

agregador = LlmAgent(
    name="agregador_analisis",
    model="gemini-2.5-flash",
    instruction="""
    Recibís los análisis de sentimiento, urgencia y clasificación de un mensaje de cliente.
    Tu tarea es sintetizarlos en una recomendación de acción clara para el agente de soporte.

    El contexto de la sesión contiene:
    - analisis_sentimiento: resultado del análisis emocional
    - analisis_urgencia: resultado del análisis de urgencia
    - clasificacion_tema: resultado de la clasificación

    Generá un resumen ejecutivo en JSON con este formato:
    {
        "prioridad_atencion": "alta" | "media" | "baja",
        "ruta_sugerida": "agente_automatico" | "agente_humano" | "escalacion_gerencial",
        "resumen_situacion": "descripción concisa en español",
        "acciones_inmediatas": ["lista de acciones recomendadas"]
    }
    """,
    output_key="recomendacion_final",
)


# -------------------------------------------------------
# 3. Pipeline completo: Parallel → Aggregate → Soporte
# -------------------------------------------------------

pipeline_analisis = ParallelAgent(
    name="pipeline_analisis_paralelo",
    sub_agents=[
        analizador_sentimiento,
        analizador_urgencia,
        clasificador_tema,
    ],
)

pipeline_completo = SequentialAgent(
    name="pipeline_soporte_completo",
    sub_agents=[
        pipeline_analisis,  # Los 3 análisis corren en paralelo
        agregador,          # Agrega los 3 resultados
        # Aquí se podría encadenar el agente_reclamos_tarjeta del Ejercicio 1
    ],
)


# -------------------------------------------------------
# 4. Benchmark: paralelo vs. secuencial
# -------------------------------------------------------

async def _drenar(runner, user_id: str, session_id: str, content) -> None:
    """Corre el runner hasta el final sin cortar el generador con `break`
    (ver nota de por qué en ejercicio_1_agente_reclamos.py)."""
    async for _ in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        pass


async def benchmark_paralelo_vs_secuencial(mensaje: str):
    """
    Compara el tiempo de ejecución entre procesamiento paralelo y secuencial.

    Para aislar el efecto del paralelismo, ambas ramas ejecutan exactamente
    los mismos 3 análisis (sentimiento, urgencia, tema) y ninguna incluye el
    agregador: la rama paralela usa `pipeline_analisis` (el ParallelAgent de
    los 3 analizadores, sin agregador), no `pipeline_completo`.
    """
    print(f"\n{'='*60}")
    print(f"BENCHMARK — Mensaje: '{mensaje[:60]}...'")
    print(f"{'='*60}")

    content = types.Content(role="user", parts=[types.Part.from_text(text=mensaje)])

    # Ejecución paralela (3 analizadores en paralelo, sin agregador)
    runner = InMemoryRunner(agent=pipeline_analisis, app_name="benchmark")
    await runner.session_service.create_session(
        app_name="benchmark", user_id="benchmark-user", session_id="sesion-paralela"
    )

    inicio = time.time()
    await _drenar(runner, "benchmark-user", "sesion-paralela", content)
    tiempo_paralelo = time.time() - inicio

    # Ejecución secuencial (los mismos 3 analizadores, uno por uno)
    inicio = time.time()
    for agente in [analizador_sentimiento, analizador_urgencia, clasificador_tema]:
        runner_seq = InMemoryRunner(agent=agente, app_name="benchmark-seq")
        await runner_seq.session_service.create_session(
            app_name="benchmark-seq",
            user_id="benchmark-user",
            session_id=f"sesion-seq-{agente.name}",
        )
        await _drenar(runner_seq, "benchmark-user", f"sesion-seq-{agente.name}", content)
    tiempo_secuencial = time.time() - inicio

    speedup = tiempo_secuencial / tiempo_paralelo if tiempo_paralelo > 0 else 0

    print(f"\nTiempo paralelo:    {tiempo_paralelo:.2f}s")
    print(f"Tiempo secuencial:  {tiempo_secuencial:.2f}s")
    print(f"Speedup:            {speedup:.1f}×")
    print(f"Ahorro de tiempo:   {(1 - tiempo_paralelo/tiempo_secuencial)*100:.0f}%")

    return {
        "tiempo_paralelo": tiempo_paralelo,
        "tiempo_secuencial": tiempo_secuencial,
        "speedup": speedup,
    }


# -------------------------------------------------------
# 5. Ejecución del benchmark con diferentes mensajes
# -------------------------------------------------------
# ¿Sin cuota o con un 429? Dejá un solo mensaje en esta lista — baja de ~18 a
# ~6 llamadas al modelo sin cambiar nada de lo que el ejercicio enseña.

MENSAJES_TEST = [
    "¡Necesito que frenen el reclamo REC-2026-0119! Ya pasaron 32 días y nadie me llamó. Voy a hacer la denuncia.",
    "Hola, ¿pueden decirme en qué estado está mi reclamo REC-2026-0118? Gracias.",
    "Me cobraron dos veces el mismo consumo del supermercado y quiero que me devuelvan la diferencia del reclamo REC-2026-0118.",
]


async def main():
    resultados = []
    for mensaje in MENSAJES_TEST:
        resultado = await benchmark_paralelo_vs_secuencial(mensaje)
        resultados.append(resultado)

    speedups = [r["speedup"] for r in resultados]
    print(f"\n{'='*60}")
    print(f"SPEEDUP PROMEDIO: {sum(speedups)/len(speedups):.1f}×")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
