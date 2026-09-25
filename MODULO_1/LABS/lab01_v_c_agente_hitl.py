# lab01_v_c_agente_hitl.py — Versión C: agente ADK2 con HITL granular
#
# CONSIGNA
# Mismo problema que las Versiones A y B, pero ahora resuelto por un agente
# de verdad: un `Agent` de ADK2 con tools, que decide por sí mismo qué
# herramienta llamar, con qué argumentos y en qué orden. Una de las tres
# acciones — bloquear la tarjeta — es irreversible en la práctica (no se
# reactiva, se repone con otro plástico), así que tiene que quedar sujeta
# a aprobación humana antes de ejecutarse.
#
# CÓMO SE RESUELVE
# Tres tools de Python (`consultar_movimientos`, `abrir_caso_fraude`,
# `bloquear_tarjeta`) se le dan al agente con `FunctionTool`. La única
# línea que importa de todo el archivo es esta:
#
#   FunctionTool(bloquear_tarjeta, require_confirmation=True)
#
# Con ese flag, ADK2 intercepta la llamada: cuando el modelo decide
# invocar `bloquear_tarjeta`, la ejecución queda suspendida y el evento
# trae `actions.requested_tool_confirmations` en vez de ejecutar la
# función. El agente ya eligió los argumentos (`tarjeta_id`) — lo que
# falta es que un humano apruebe. Acá se imprime por consola (bloque
# `[HITL]`); en producción sería una cola de aprobación con auditoría.
# Sacar ese flag no rompe nada — cambia el comportamiento en silencio, de
# "pide aprobación" a "ejecuta directo".
#
# CÓMO LEER LA SALIDA
# Cada caso imprime la conversación completa. Si en algún punto aparece
# el bloque `[HITL]`, el agente decidió bloquear la tarjeta y quedó
# esperando aprobación — no hay "respuesta final" del agente en ese
# turno, y eso es correcto, no un error: nadie implementó el paso de
# aprobación en este ejemplo. El comportamiento no es determinista: el mismo
# input puede resolver el caso con distinta cantidad de pasos, o el
# agente puede pedir más datos en texto en vez de llamar a una tool.
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import InMemoryRunner

# --- Herramientas del agente ---


def consultar_movimientos(cuenta: str, desde: str, hasta: str) -> dict:
    """
    Consulta los movimientos de una cuenta en un rango de fechas.

    Args:
        cuenta: Identificador de la cuenta del cliente
        desde: Fecha de inicio del período, en formato YYYY-MM-DD
        hasta: Fecha de fin del período, en formato YYYY-MM-DD

    Returns:
        Diccionario con la lista de movimientos del período
    """
    movimientos_simulados = {
        "AR-0099-4417": [
            {"id": "MOV-8801", "fecha": "2026-07-19", "comercio": "SUPERMERCADO NORTE", "monto": 48200.00, "moneda": "ARS"},
            {"id": "MOV-8814", "fecha": "2026-07-21", "comercio": "DIGITALGOODS LTD",   "monto": 129.99,   "moneda": "USD"},
            {"id": "MOV-8815", "fecha": "2026-07-21", "comercio": "DIGITALGOODS LTD",   "monto": 129.99,   "moneda": "USD"},
            {"id": "MOV-8822", "fecha": "2026-07-24", "comercio": "GAMESTORE ONLINE",   "monto": 89.50,    "moneda": "USD"},
            {"id": "MOV-8830", "fecha": "2026-07-26", "comercio": "FARMACIA CENTRAL",   "monto": 15300.00, "moneda": "ARS"},
        ]
    }

    if cuenta in movimientos_simulados:
        return {
            "cuenta": cuenta,
            "desde": desde,
            "hasta": hasta,
            "movimientos": movimientos_simulados[cuenta],
        }
    return {"cuenta": cuenta, "movimientos": [], "estado": "cuenta_no_encontrada"}


def abrir_caso_fraude(
    tarjeta_id: str,
    movimientos_desconocidos: str,
    monto_total_desconocido: float,
) -> dict:
    """
    Abre un caso de desconocimiento de consumos para que lo investigue el
    área de prevención de fraude. Es una acción REVERSIBLE: un caso mal
    abierto se cierra sin consecuencias para el cliente.

    Args:
        tarjeta_id: Últimos 4 dígitos de la tarjeta
        movimientos_desconocidos: IDs de los movimientos desconocidos, separados por coma
        monto_total_desconocido: Monto total en disputa

    Returns:
        Confirmación con número de caso y plazos
    """
    import random
    caso_id = f"FRD-{random.randint(10000, 99999)}"
    return {
        "caso_id": caso_id,
        "tarjeta_id": tarjeta_id,
        "movimientos": movimientos_desconocidos,
        "monto_total": monto_total_desconocido,
        "estado": "abierto",
        "plazo_respuesta_dias_habiles": 15,
        "mensaje": (
            f"Caso {caso_id} abierto. El área de fraude investiga y responde en un "
            f"plazo máximo de 15 días hábiles. Los importes en disputa quedan "
            f"marcados como 'en revisión' en el resumen."
        ),
    }


def bloquear_tarjeta(tarjeta_id: str) -> dict:
    """
    Bloquea de forma preventiva una tarjeta de crédito.

    ACCIÓN IRREVERSIBLE EN LA PRÁCTICA: una vez bloqueada, la tarjeta no se
    reactiva — se repone con un plástico nuevo y otro número. El cliente queda
    sin ese medio de pago hasta que llegue la reposición, y los débitos
    automáticos asociados fallan.

    Args:
        tarjeta_id: Últimos 4 dígitos de la tarjeta a bloquear

    Returns:
        Confirmación del bloqueo y datos de la reposición
    """
    return {
        "tarjeta_id": tarjeta_id,
        "estado": "bloqueada",
        "reversible": False,
        "reposicion_dias_habiles": 7,
        "mensaje": (
            f"Tarjeta terminada en {tarjeta_id} bloqueada. La reposición llega en "
            f"7 días hábiles. Los débitos automáticos asociados van a rechazarse "
            f"hasta que se active el plástico nuevo."
        ),
    }


# --- Configuración del agente ---

agente_fraude = Agent(
    name="agente_fraude_tarjetas",
    model="gemini-2.5-flash",
    instruction="""Sos un agente de atención de reclamos de tarjetas de crédito
de un banco argentino.

Cuando un cliente te contacta:
1. Entendé el reclamo completo antes de actuar. Un mismo mensaje puede
   contener varios pedidos distintos: atendelos todos.
2. Si el cliente desconoce consumos, consultá primero los movimientos del
   período que menciona. NO abras un caso de fraude sin haber mirado los
   movimientos.
3. Identificá qué movimientos concretos podrían ser los desconocidos y
   confirmalos con el cliente antes de incluirlos en el caso.
4. Si el cliente pide el bloqueo de la tarjeta, llamá a la herramienta
   correspondiente apenas tengas el tarjeta_id (usá los últimos 4 dígitos
   que mencione el cliente, o los que ya conste en la conversación). NO le
   pidas confirmación al cliente vos mismo en el texto antes de llamarla:
   el sistema intercepta esa llamada automáticamente y exige aprobación
   humana antes de ejecutarla — ese control ya existe, tu trabajo es
   invocar la herramienta, no simular el permiso en la respuesta.
   Explicale al cliente, en tu respuesta, que el bloqueo implica
   reposición del plástico y que los débitos automáticos se van a rechazar.
5. Nunca prometas la devolución del dinero. Lo que podés informar es que
   los importes quedan en revisión y el plazo del caso.
6. Siempre informá al cliente qué acciones tomaste y qué puede esperar.

Sé empático, claro y profesional. Hablá en español rioplatense.""",
    tools=[
        FunctionTool(consultar_movimientos),
        FunctionTool(abrir_caso_fraude),
        FunctionTool(bloquear_tarjeta, require_confirmation=True),   # ← el ejercicio
    ],
)


async def procesar_reclamo(texto_reclamo: str) -> str:
    """Procesa un reclamo usando el agente ADK2."""
    if not isinstance(texto_reclamo, str) or not texto_reclamo.strip():
        return "Error: el reclamo no puede estar vacío."

    runner = InMemoryRunner(agent=agente_fraude)

    try:
        # InMemoryRunner(agent=...) usa por defecto app_name="InMemoryRunner",
        # no el nombre del agente. Si create_session usara
        # agente_fraude.name acá, run_async buscaría la sesión bajo un
        # app_name distinto y tiraría "Session not found" — por eso las
        # dos llamadas usan runner.app_name.
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="cliente-001",
        )

        from google.genai import types as genai_types

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=texto_reclamo)],
        )

        respuesta_final = ""
        quedo_esperando_aprobacion = False
        async for event in runner.run_async(
            user_id="cliente-001",
            session_id=session.id,
            new_message=content,
        ):
            pedidos = getattr(event.actions, "requested_tool_confirmations", None)
            if pedidos:
                quedo_esperando_aprobacion = True
                for fc_id, confirmacion in pedidos.items():
                    print(f"\n  [HITL] El agente pide ejecutar una acción que requiere aprobación.")
                    print(f"  [HITL] call_id: {fc_id}")
                    print(f"  [HITL] motivo:  {confirmacion.hint or '(sin hint)'}")
                    print(f"  [HITL] → El agente NO ejecutó nada. Espera decisión humana.\n")

            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        respuesta_final += part.text

        if respuesta_final:
            return respuesta_final
        if quedo_esperando_aprobacion:
            # Esto NO es un error: es el punto del ejercicio. El turno queda
            # suspendido acá — el agente no tiene más texto para dar hasta
            # que un humano apruebe o rechace la tool. En este lab no se
            # implementa el paso de aprobación (queda fuera del alcance del
            # ejercicio); en producción, esto es donde entra la consola del
            # operador de fraude.
            return "(sin respuesta final — el agente quedó esperando la aprobación humana del bloqueo, ver [HITL] arriba)"
        return "El agente no generó una respuesta."
    except Exception as e:
        return f"Error al procesar el reclamo con el agente: {e}"


async def main():
    casos = [
        "Desconozco tres consumos en mi tarjeta terminada en 4417 de los últimos 10 días, quiero que me la bloqueen y que me devuelvan la plata",
        "Perdí la billetera, necesito bloquear la tarjeta ya mismo",
        "¿Cuánto tarda la reposición de una tarjeta nueva?",
    ]

    for caso in casos:
        print(f"\n{'='*60}")
        print(f"RECLAMO: {caso}")
        print(f"{'='*60}")
        respuesta = await procesar_reclamo(caso)
        print(f"AGENTE: {respuesta}")


if __name__ == "__main__":
    asyncio.run(main())
