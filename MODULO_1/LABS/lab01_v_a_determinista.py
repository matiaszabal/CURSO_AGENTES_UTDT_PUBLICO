# lab01_v_a_determinista.py — Versión A: código determinista (cero agencia)
#
# CONSIGNA
# Un banco recibe reclamos de clientes de tarjeta de crédito en texto
# libre, por ejemplo:
#   "Desconozco tres consumos en mi tarjeta terminada en 4417 de los
#    últimos 10 días, quiero que me la bloqueen y que me devuelvan la
#    plata"
# Hay que clasificar el reclamo (categoría, prioridad) y decidir qué
# acción tomar — sin usar ningún modelo de lenguaje.
#
# CÓMO SE RESUELVE
# Con reglas hardcodeadas: una lista de palabras clave por categoría,
# evaluadas en un orden de prioridad fijo. La primera regla que matchea
# gana y las demás ni se miran — por eso un mensaje con dos pedidos
# distintos (p. ej. "desconozco un consumo" + "quiero cancelar mi
# tarjeta") termina clasificado en una sola categoría: la que aparece
# primero en el código, no necesariamente la más urgente para el cliente.
# Es la propiedad central que esta versión existe para mostrar: el
# sistema no tira ningún error — devuelve una respuesta con la misma
# forma que si hubiera entendido todo, y nadie se entera de lo que se
# perdió.
#
# CÓMO LEER LA SALIDA
# Cada resultado es un dict con `categoria`, `prioridad`, `accion`,
# `tarjeta_id` (extraído con regex) y `metodo='determinista'`. No hay
# texto libre, no hay nada que "interpretar": lo que ves es exactamente
# lo que ejecutó el código, así que la salida es 100% reproducible —
# correr este script mil veces da el mismo resultado las mil veces.
import re
from dataclasses import dataclass


@dataclass
class ReclamoTarjeta:
    texto: str
    tarjeta_id: str | None = None


def extraer_tarjeta_id(texto: str) -> str | None:
    """Extrae los últimos 4 dígitos de la tarjeta con regex."""
    match = re.search(r'(?:tarjeta|terminada en|final)\D{0,15}(\d{4})\b', texto.lower())
    return match.group(1) if match else None


def clasificar_reclamo_determinista(texto: str) -> dict:
    """
    Clasificador basado en palabras clave, evaluadas en orden de
    prioridad. Retorna categoria, prioridad y accion — sin llamar a
    ningún modelo.
    """
    if not isinstance(texto, str) or not texto.strip():
        return {'error': 'texto de entrada inválido o vacío', 'metodo': 'determinista'}

    texto_lower = texto.lower()

    # Reglas hardcodeadas, evaluadas EN ORDEN. La primera que matchea gana
    # y el resto del mensaje se descarta en silencio — es el punto del
    # ejercicio, no un bug.
    if any(w in texto_lower for w in ['desconozco', 'no reconozco', 'desconocido', 'no fui yo', 'fraude']):
        categoria = 'desconocimiento_consumo'
        prioridad = 'alta'
        accion = 'abrir_caso_fraude'
    elif any(w in texto_lower for w in ['bloque', 'anular', 'dar de baja']):
        categoria = 'bloqueo_tarjeta'
        prioridad = 'alta'
        accion = 'bloquear_tarjeta'
    elif any(w in texto_lower for w in ['límite', 'limite', 'tope', 'aumento']):
        categoria = 'limites'
        prioridad = 'media'
        accion = 'derivar_a_riesgo'
    else:
        categoria = 'consulta_general'
        prioridad = 'baja'
        accion = 'responder_faq'

    return {
        'categoria': categoria,
        'prioridad': prioridad,
        'accion': accion,
        'tarjeta_id': extraer_tarjeta_id(texto),
        'metodo': 'determinista',
    }


# Casos de prueba. El primero y el último traen dos pedidos distintos en
# el mismo mensaje — ahí es donde se ve la pérdida de información.
casos = [
    "Desconozco tres consumos en mi tarjeta terminada en 4417 de los últimos 10 días, quiero que me la bloqueen y que me devuelvan la plata",
    "Perdí la billetera, necesito bloquear la tarjeta ya mismo",
    "¿Cuánto tarda la reposición de una tarjeta nueva?",
    "Hola, me llegó el resumen con un consumo en dólares que no reconozco y además quiero saber si tengo cobertura de seguro de compra",
]

if __name__ == "__main__":
    for caso in casos:
        resultado = clasificar_reclamo_determinista(caso)
        print(f"\nTexto: {caso[:60]}...")
        print(f"Resultado: {resultado}")
