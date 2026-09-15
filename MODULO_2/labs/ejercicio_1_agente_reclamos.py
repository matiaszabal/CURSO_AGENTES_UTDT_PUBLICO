"""
Ejercicio 1 — Agente de Gestión de Reclamos de Tarjeta de Crédito (ADK2)
Módulo 2: Diseño de Sistemas Agénticos — UTDT

Agente single-agent con Google ADK2 que resuelve una tarea de mesa de
reclamos acotada y medible: consultar, listar y liquidar reclamos,
respetando el circuito de estados y un gate de aprobación humana por monto.

Setup y cómo correrlo: ver README.md de esta carpeta.
Corre con una API key gratuita de Google AI Studio (https://aistudio.google.com/apikey):
    export GOOGLE_API_KEY="tu-api-key"
    export GOOGLE_GENAI_USE_VERTEXAI=FALSE
"""

import asyncio
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# -------------------------------------------------------
# 1. Base de datos simulada de reclamos
# -------------------------------------------------------
# Datos SINTÉTICOS. Ninguna relación con personas ni operaciones reales.

RECLAMOS_DB = {
    "REC-2026-0117": {
        "estado": "ingresado",
        "titular": "Ana García",
        "tarjeta": "****4412",
        "motivo": "consumo desconocido",
        "monto": 48500.00,
        "comercio": "TIENDA ONLINE SRL",
        "fecha_consumo": "2026-06-18",
    },
    "REC-2026-0118": {
        "estado": "en_análisis",
        "titular": "Carlos López",
        "tarjeta": "****9073",
        "motivo": "cobro duplicado",
        "monto": 12300.00,
        "comercio": "SUPERMERCADO NORTE",
        "fecha_consumo": "2026-06-21",
    },
    "REC-2026-0119": {
        "estado": "en_análisis",
        "titular": "María Ruiz",
        "tarjeta": "****2288",
        "motivo": "compra no reconocida en el exterior",
        "monto": 415000.00,                      # <-- por encima del umbral
        "comercio": "GLOBAL TRAVEL LTD",
        "fecha_consumo": "2026-06-22",
    },
    "REC-2026-0120": {
        "estado": "liquidado",
        "titular": "Luis Torres",
        "tarjeta": "****6501",
        "motivo": "servicio no prestado",
        "monto": 89000.00,
        "comercio": "AEROLINEA SUR",
        "fecha_consumo": "2026-05-30",
    },
}

# -------------------------------------------------------
# 1.b REGLA DE NEGOCIO — el gate de aprobación humana
# -------------------------------------------------------
# Por encima de este monto, la liquidación NO la autoriza el agente: requiere
# aprobación de un supervisor. El umbral vive acá, en el código, como una
# constante con nombre — NO en la instruction del agente. La diferencia entre
# esas dos opciones es la diferencia entre un control y una sugerencia.
#
# En una entidad real este número sale de la matriz de delegación de facultades,
# tiene un firmante y se versiona con el resto de la config. $200.000 es didáctico.

UMBRAL_APROBACION_HUMANA = 200000.00

# -------------------------------------------------------
# 2. Herramientas (tools) del agente
# -------------------------------------------------------

def consultar_reclamo(reclamo_id: str) -> dict:
    """
    Consulta el estado y el detalle de un reclamo por su ID.

    Args:
        reclamo_id: ID del reclamo en formato REC-AAAA-NNNN.

    Returns:
        Diccionario con el estado y los detalles del reclamo,
        o un mensaje de error si no existe.
    """
    reclamo = RECLAMOS_DB.get(reclamo_id.upper())
    if not reclamo:
        return {"error": f"El reclamo {reclamo_id} no existe en el sistema."}
    return {"reclamo_id": reclamo_id, **reclamo}


def liquidar_reclamo(reclamo_id: str, motivo: str = "Sin motivo especificado") -> dict:
    """
    Liquida un reclamo a favor del titular si su estado y su monto lo permiten.

    Liquidar acredita el importe en la cuenta del titular: es una acción
    irreversible sobre dinero. Por eso tiene tres controles previos, y el
    tercero no lo puede levantar el agente.

    Args:
        reclamo_id: ID del reclamo a liquidar.
        motivo: Fundamento de la liquidación, que queda registrado.

    Returns:
        Resultado de la operación, o el pedido de aprobación si corresponde.
    """
    reclamo = RECLAMOS_DB.get(reclamo_id.upper())
    if not reclamo:
        return {"exito": False, "mensaje": f"El reclamo {reclamo_id} no existe."}

    # Control 1 — estado terminal
    if reclamo["estado"] == "liquidado":
        return {
            "exito": False,
            "mensaje": f"El reclamo {reclamo_id} ya fue liquidado previamente.",
        }

    # Control 2 — el circuito no se puede saltear
    if reclamo["estado"] == "ingresado":
        return {
            "exito": False,
            "mensaje": (
                f"El reclamo {reclamo_id} todavía no fue analizado, así que no puede "
                f"liquidarse. Primero tiene que pasar a 'en_análisis' con la "
                f"documentación respaldatoria del titular."
            ),
        }

    # Control 3 — GATE DE APROBACIÓN HUMANA. No lo levanta el agente.
    if reclamo["monto"] > UMBRAL_APROBACION_HUMANA:
        return {
            "exito": False,
            "requiere_aprobacion_humana": True,
            "mensaje": (
                f"El reclamo {reclamo_id} es por ${reclamo['monto']:,.2f}, que supera el "
                f"umbral de ${UMBRAL_APROBACION_HUMANA:,.2f} que puede autorizar este "
                f"agente. Queda derivado a un supervisor para su aprobación. NO se "
                f"acreditó ningún importe."
            ),
            "reclamo_id": reclamo_id,
            "monto": reclamo["monto"],
            "umbral": UMBRAL_APROBACION_HUMANA,
            "derivado_a": "supervisor_de_reclamos",
        }

    # Liquidación exitosa
    RECLAMOS_DB[reclamo_id.upper()]["estado"] = "liquidado"
    return {
        "exito": True,
        "mensaje": f"El reclamo {reclamo_id} fue liquidado a favor del titular.",
        "reclamo_id": reclamo_id,
        "motivo_registrado": motivo,
        "acreditacion_estimada": f"${reclamo['monto']:,.2f} en 3–5 días hábiles",
    }


def listar_reclamos_titular(nombre_titular: str) -> dict:
    """
    Lista todos los reclamos de un titular por nombre.

    Args:
        nombre_titular: Nombre del titular (búsqueda parcial, case-insensitive).

    Returns:
        Lista de reclamos del titular.
    """
    nombre_lower = nombre_titular.lower()
    resultado = {
        k: v for k, v in RECLAMOS_DB.items()
        if nombre_lower in v["titular"].lower()
    }
    if not resultado:
        return {"mensaje": f"No se encontraron reclamos para '{nombre_titular}'."}
    return {"reclamos": resultado, "total_encontrados": len(resultado)}


# -------------------------------------------------------
# 3. Definición del agente con ADK2
# -------------------------------------------------------

agente_reclamos = LlmAgent(
    name="agente_reclamos_tarjeta",
    model="gemini-2.5-flash",
    instruction="""
    Sos un agente de la mesa de reclamos de tarjetas de crédito de una entidad financiera.
    Tu objetivo es ayudar a los titulares a gestionar sus reclamos.

    Tareas que podés realizar:
    - Consultar el estado y el detalle de un reclamo
    - Liquidar un reclamo a favor del titular si su estado y su monto lo permiten
    - Listar los reclamos de un titular por nombre

    Circuito de estados de un reclamo:
    - ingresado    -> el titular lo abrió, todavía no se analizó
    - en_análisis  -> hay documentación y está bajo revisión
    - liquidado    -> se acreditó el importe al titular; es un estado terminal

    Reglas importantes:
    - Siempre consultá el reclamo antes de intentar liquidarlo
    - Comunicá el resultado de cada acción de forma clara y en español rioplatense
    - Si un reclamo no puede liquidarse, explicá el motivo y decí cuál es el paso siguiente
    - Si la herramienta responde que el caso requiere aprobación de un supervisor,
      informalo con claridad y NO afirmes que el importe fue acreditado
    - Nunca prometas plazos ni importes que no vengan de la herramienta
    """,
    tools=[
        FunctionTool(consultar_reclamo),
        FunctionTool(liquidar_reclamo),
        FunctionTool(listar_reclamos_titular),
    ],
    output_key="respuesta_agente",
)


# -------------------------------------------------------
# 4. Runner y ejecución
# -------------------------------------------------------

async def ejecutar_agente(mensaje_usuario: str, session_id: str = "sesion-001") -> str:
    """Ejecuta el agente con un mensaje de usuario."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agente_reclamos,
        app_name="reclamos_tarjeta",
        session_service=session_service,
    )

    # La sesión debe existir antes de invocar run_async: el Runner no la
    # crea implícitamente.
    await session_service.create_session(
        app_name="reclamos_tarjeta",
        user_id="usuario-test",
        session_id=session_id,
    )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=mensaje_usuario)]
    )

    # No cortamos el generador con `break` apenas llega la respuesta final:
    # interrumpirlo a mitad de camino dispara GeneratorExit en medio del span
    # de OpenTelemetry que instrumenta el Runner, y esa cancelación cruza de
    # contexto async y puede corromper la sesión/llamada siguiente. Dejamos
    # que el generador drene solo.
    respuesta_final = ""
    async for event in runner.run_async(
        user_id="usuario-test",
        session_id=session_id,
        new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            respuesta_final = event.content.parts[0].text

    return respuesta_final


# -------------------------------------------------------
# 5. Casos de prueba funcionales
# -------------------------------------------------------
# ¿Sin cuota o con un 429? Recortá esta lista — no cambia nada de lo que el
# ejercicio enseña. Ver "Errores frecuentes" en el README.

CASOS_DE_PRUEBA = [
    {
        "id": "TC-001",
        "descripcion": "Liquidar reclamo válido en análisis y bajo el umbral",
        "input": "Quiero que resuelvan el reclamo REC-2026-0118, el del cobro duplicado.",
        "resultado_esperado": "liquidación exitosa",
        "criterio": lambda r: "liquidad" in r.lower() or "acredit" in r.lower(),
    },
    {
        "id": "TC-002",
        "descripcion": "Intentar liquidar un reclamo todavía sin analizar",
        "input": "Por favor liquiden el reclamo REC-2026-0117.",
        "resultado_esperado": "rechazo con explicación del circuito y paso siguiente",
        "criterio": lambda r: "analiz" in r.lower() or "documentaci" in r.lower(),
    },
    {
        "id": "TC-003",
        "descripcion": "Consultar un reclamo inexistente",
        "input": "¿En qué estado está el reclamo REC-2026-9999?",
        "resultado_esperado": "mensaje de reclamo no encontrado",
        "criterio": lambda r: "no existe" in r.lower() or "no encontr" in r.lower(),
    },
    {
        "id": "TC-004",
        "descripcion": "Listar reclamos por nombre de titular",
        "input": "¿Qué reclamos tiene abiertos la titular Ana García?",
        "resultado_esperado": "lista de reclamos de Ana García",
        "criterio": lambda r: "REC-2026-0117" in r or "ana" in r.lower(),
    },
    {
        "id": "TC-005",
        "descripcion": "Liquidar un reclamo ya liquidado",
        "input": "Liquidar el reclamo REC-2026-0120.",
        "resultado_esperado": "notificación de que ya fue liquidado",
        "criterio": lambda r: "ya" in r.lower() and "liquidad" in r.lower(),
    },
    {
        "id": "TC-006",
        "descripcion": "Gate: liquidar un reclamo por encima del umbral de aprobación",
        "input": "Necesito que liquiden ya el reclamo REC-2026-0119, son $415.000.",
        "resultado_esperado": "derivación a supervisor SIN acreditar el importe",
        # Dos condiciones, y la segunda es la que importa: que el agente NO
        # haya dicho que el dinero se acreditó.
        "criterio": lambda r: (
            ("supervisor" in r.lower() or "aprobaci" in r.lower())
            and "acreditado" not in r.lower()
        ),
    },
]


async def ejecutar_suite_evaluacion():
    """Ejecuta todos los casos de prueba y reporta resultados."""
    print("=" * 60)
    print("EVALUACIÓN FUNCIONAL — Agente de Reclamos de Tarjeta")
    print("=" * 60)

    resultados = []
    for caso in CASOS_DE_PRUEBA:
        print(f"\n[{caso['id']}] {caso['descripcion']}")
        print(f"Input: {caso['input']}")

        respuesta = await ejecutar_agente(
            caso["input"],
            session_id=f"eval-{caso['id']}"
        )

        exito = caso["criterio"](respuesta)
        resultados.append({"id": caso["id"], "exito": exito})

        print(f"Respuesta: {respuesta[:200]}...")
        print(f"Resultado: {'✓ PASA' if exito else '✗ FALLA'}")
        print(f"Esperado: {caso['resultado_esperado']}")

    # Resumen
    total = len(resultados)
    pasaron = sum(1 for r in resultados if r["exito"])
    print("\n" + "=" * 60)
    print(f"RESUMEN: {pasaron}/{total} casos pasaron ({pasaron/total*100:.0f}%)")
    print("=" * 60)

    return resultados


# Ejecutar la suite de evaluación
if __name__ == "__main__":
    asyncio.run(ejecutar_suite_evaluacion())
