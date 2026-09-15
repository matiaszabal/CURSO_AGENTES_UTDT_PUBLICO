"""
demo_dos_modelos.py — Comparación rápida: modelo barato vs. modelo caro
Módulo 2: Diseño de Sistemas Agénticos — UTDT

Script opcional. Corre la MISMA query con un modelo barato y con uno caro, e
imprime, uno debajo del otro, respuesta + latencia + costo estimado. Sirve
para ver de un vistazo el contraste de costo que motiva el Ejercicio 3
(Dynamic Model Routing).

Uso:
    python demo_dos_modelos.py simple      # clasificación simple
    python demo_dos_modelos.py compleja    # decisión de negocio

Corre con una API key gratuita de Google AI Studio (https://aistudio.google.com/apikey):
    export GOOGLE_API_KEY="tu-api-key"
export GOOGLE_GENAI_USE_VERTEXAI=FALSE

Modelos: gemini-2.5-flash-lite (barato) y gemini-2.5-pro (caro) — mismos $
por millón de tokens que MODELOS_CONFIG en ejercicio_3_routing_dinamico.py.
Precios de referencia según https://ai.google.dev/gemini-api/docs/pricing —
verificar antes de usarlos para una decisión real, pueden cambiar.
"""

import sys
import time

from google import genai

MODELOS_CONFIG = {
    "gemini-2.5-flash-lite": {"input_cost_per_mtok": 0.10, "output_cost_per_mtok": 0.40},
    "gemini-2.5-pro": {"input_cost_per_mtok": 1.25, "output_cost_per_mtok": 10.00},
}
SYSTEM = "Sos un asistente de IA experto. Respondé en español, de forma clara y precisa."

QUERIES = {
    "simple": (
        "Clasificá este reclamo de tarjeta en una de estas categorías: "
        "desconocimiento_consumo, cobro_duplicado, servicio_no_prestado, fraude, "
        "estado_de_reclamo, documentacion, otro. Mensaje del titular: \"Me cobraron "
        "dos veces el mismo consumo del supermercado\". Respondé solo con la categoría."
    ),
    "compleja": (
        "Un titular reclama $415.000 por una compra no reconocida en el exterior. El "
        "reclamo lleva 32 días en análisis, supera el umbral que puede autorizar el "
        "agente automático, y el titular anticipó que va a hacer una denuncia ante el "
        "organismo de defensa del consumidor. Redactá la respuesta al titular y decidí "
        "si corresponde escalar a un supervisor, justificando la decisión."
    ),
}


def correr(client: genai.Client, modelo: str, query: str) -> dict:
    inicio = time.time()
    r = client.models.generate_content(
        model=modelo,
        contents=f"{SYSTEM}\n\n{query}",
    )
    latencia_ms = (time.time() - inicio) * 1000
    cfg = MODELOS_CONFIG[modelo]
    ti = len(query.split()) * 1.3          # misma estimación que ejercicio_3
    to = len(r.text.split()) * 1.3
    costo = ((ti / 1_000_000) * cfg["input_cost_per_mtok"] +
             (to / 1_000_000) * cfg["output_cost_per_mtok"])
    return {"modelo": modelo, "respuesta": r.text,
            "latencia_ms": latencia_ms, "costo": costo, "tokens": int(ti + to)}


def comparar(query: str) -> None:
    # Sin argumentos, el cliente toma la API key de la variable de entorno
    # GOOGLE_API_KEY (Google AI Studio). No usa Vertex AI ni proyecto de GCP.
    client = genai.Client()
    print("=" * 72)
    print(f"QUERY: {query}")
    print("=" * 72)
    resultados = [correr(client, m, query) for m in ("gemini-2.5-flash-lite", "gemini-2.5-pro")]
    for x in resultados:
        print(f"\n--- {x['modelo']} " + "-" * (66 - len(x["modelo"])))
        print(x["respuesta"].strip())
        print(f"\n  latencia {x['latencia_ms']:.0f}ms | "
              f"tokens ~{x['tokens']} | costo ${x['costo']:.8f}")
    barato, caro = resultados
    print("\n" + "-" * 72)
    print(f"  El caro costó {caro['costo'] / barato['costo']:.1f}x más que el barato "
          f"para ESTA query.")
    print("-" * 72)


if __name__ == "__main__":
    comparar(QUERIES[sys.argv[1] if len(sys.argv) > 1 else "simple"])
