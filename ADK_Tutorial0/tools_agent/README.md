# 1. tools_agent — Tool calling básico

## Objetivo

Entender qué es una **tool** en ADK y cómo un agente decide, por sí solo, cuándo usarla. Es el punto de partida del tutorial: un solo agente, sin orquestación ni schemas, para enfocarse en un único concepto.

Este agente puede:
- Consultar la fecha y hora actual (`get_current_date_and_time`).
- Traer un usuario aleatorio de una API pública (`get_randomuser_from_ramdomuserme`).

## Cómo funciona (código en `agent.py`)

En ADK, cualquier función Python se convierte en una tool con solo pasarla en la lista `tools=[...]` del agente — no hace falta decorador ni registro:

```python
root_agent = Agent(
    name="tools_agent",
    tools=[get_current_date_and_time, get_randomuser_from_ramdomuserme],
    model="gemini-2.5-flash",
    instruction="...",
)
```

Lo importante: el **docstring** de cada función es lo que el modelo lee para decidir *cuándo* conviene llamarla. No es un comentario decorativo — es, en la práctica, parte del prompt que ve el LLM. Si el docstring es vago, el modelo va a dudar entre usar la tool o inventar una respuesta.

El agente, en cada turno, decide autónomamente si necesita alguna tool, cuál, y con qué argumentos — vos solo describís qué tools tiene disponibles.

## Cómo correr

Desde `ADK/Tutorial0/` (para que `adk` detecte los tres ejemplos):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cd tools_agent
cp .env.example .env   # completá la Opción A o B — ver ../README.md
cd ..

adk run tools_agent "¿qué hora es?"
# o con interfaz web (podés ver el trace de qué tool se llamó y con qué args):
adk web
```

## Preguntas para probar

- "¿Qué fecha es hoy?"
- "Dame un usuario random"
- "Decime la hora y de paso un usuario de prueba" (dispara las dos tools en el mismo turno)
