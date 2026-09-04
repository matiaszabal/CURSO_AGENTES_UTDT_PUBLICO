# 3. marketing_campaign_agent — Pipeline multi-agente (cierre del tutorial)

## Objetivo

Este es el ejemplo más completo de los tres: muestra cómo **orquestar varios agentes especializados en secuencia** para resolver una tarea que ningún agente único haría bien solo. Junta todo lo visto antes (tools en `tools_agent`, estado compartido en `structured_output`) en un pipeline real de 5 pasos.

A partir de una idea de producto, el sistema genera un brief de campaña de marketing completo:

```
idea de producto
      │
      ▼
┌─────────────────┐   busca en Google, resume el mercado
│ MarketResearcher │   (única tool del pipeline: google_search)
└─────────────────┘
      │ state['market_research_summary']
      ▼
┌─────────────────────┐  define el mensaje central
│ MessagingStrategist  │
└─────────────────────┘
      │ state['key_messaging']
      ▼
┌───────────────┐  escribe variantes de copy (tweet, post, headline)
│ AdCopyWriter   │
└───────────────┘
      │ state['ad_copy_variations']
      ▼
┌─────────────────┐  sugiere conceptos visuales para cada copy
│ VisualSuggester  │
└─────────────────┘
      │ state['visual_concepts']
      ▼
┌───────────────────────┐  junta TODO en un brief final en Markdown
│ CampaignBriefFormatter │
└───────────────────────┘
```

## Cómo funciona (código en `agent.py` / `instructions.py`)

Cada paso es un `LlmAgent` independiente con su propio `instruction` (en `instructions.py`) y su propio `output_key`, que es la clave donde ADK guarda su resultado en el **estado de la sesión**:

```python
market_research_agent = LlmAgent(
    name="MarketResearcher",
    instruction=MARKET_RESEARCH_INSTRUCTION,
    tools=[google_search],
    output_key="market_research_summary",
)
```

El truco para encadenarlos está en el `instruction` de cada agente siguiente — referencia directamente el `state` del anterior (ver `instructions.py`, por ejemplo `MESSAGING_STRATEGIST_INSTRUCTION` dice *"Market research summary is available in state['market_research_summary']"*). No hace falta pasarle nada a mano: ADK inyecta el estado acumulado en cada paso.

El `SequentialAgent` es lo que ata todo:

```python
root_agent = SequentialAgent(
    name="MarketingCampaignAssistant",
    sub_agents=[market_research_agent, messaging_strategist_agent,
                ad_copy_writer_agent, visual_suggester_agent, formatter_agent],
)
```

Ejecuta la lista en orden estricto, uno atrás del otro, sobre el mismo estado de sesión — a diferencia de un `ParallelAgent` (no usado acá) que los correría todos a la vez.

## Cómo correr

Desde `ADK/Tutorial0/` (con el venv ya activado):

```bash
cd marketing_campaign_agent
cp .env.example .env   # completá la Opción A o B — ver ../README.md
cd ..

adk run marketing_campaign_agent "Campaña de lanzamiento para <tu producto/target>"
# o con interfaz web:
adk web
```

⏱️ Este ejemplo tarda notablemente más que los otros dos — son 5 llamadas al LLM en cadena (una de ellas con búsqueda en Google), esperá entre 30 y 60 segundos.

En `adk web`, hacé click en el ícono de grafo (junto al selector de app, arriba) para ver la estructura de los 5 sub-agentes — y mientras corre una consulta, ese mismo grafo va resaltando en verde cuál sub-agente está ejecutándose en cada momento.

## Ejemplo probado

"Campaña de lanzamiento para una app de finanzas personales dirigida a jóvenes profesionales en Argentina" — corrido de punta a punta sin errores, produjo un brief completo con research de mercado, mensaje central, 2 tweets + 2 social posts + 3 headlines, y conceptos visuales detallados para cada pieza.
