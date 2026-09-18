# Labs de MCP con `adk web` — Módulo 4

Cinco agentes de [Google ADK](https://google.github.io/adk-docs/) que muestran
las dos puntas del **Model Context Protocol (MCP)**: agentes que *consumen*
servidores MCP (clientes) y servidores MCP que *exponen* herramientas
(servidores). Se corren todos juntos desde un único `adk web`.

## Los cinco ejemplos

| Agente | Qué muestra | Necesita |
|---|---|---|
| `weather_agent` | Cliente MCP + **servidor MCP propio** escrito con FastMCP (`weather_mcp_server.py`): las dos puntas del protocolo en un solo ejemplo | Solo la key de AI Studio |
| `mcp_agent` | Cliente MCP puro contra el servidor oficial de filesystem (`@modelcontextprotocol/server-filesystem`): cero código propio de manejo de archivos | Key de AI Studio + Node.js |
| `web_reader_agent` | Patrón invertido: ADK **exponiendo** una tool propia (`load_web_page`) como servidor MCP (`adk_mcp_server/adk_server.py`), consumida por otro agente ADK | Solo la key de AI Studio |
| `maps_agent` | Cliente MCP por **stdio** contra un servidor comunitario de Google Maps (`@modelcontextprotocol/server-google-maps`, marcado como *deprecado* en npm) | Key de AI Studio + Node.js + key de Maps |
| `maps_agent_grounding_lite` | Cliente MCP por **HTTP** contra Maps Grounding Lite, el servidor oficial y mantenido por Google. Mismo caso de uso que `maps_agent`, para contrastar stdio/comunitario vs. HTTP/oficial | Key de AI Studio + key de Maps |

Recomendamos empezar por `weather_agent` (no requiere nada más que la key del
modelo), seguir con `mcp_agent` y `web_reader_agent`, y dejar los dos de Maps
para el final.

## Instalación

Requisitos: Python 3.10 o superior (probado con 3.14) y [Node.js](https://nodejs.org/) (para
`npx`, que usan `mcp_agent` y `maps_agent`).

```bash
cd MODULO_4/labs_MCP

python3 -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # y completá tus keys (ver abajo)
```

### API key de Google AI Studio (obligatoria)

1. Entrá a <https://aistudio.google.com/apikey> y creá una key gratuita.
2. Pegala en `.env` como `GOOGLE_API_KEY=...`.

Dejá `GOOGLE_GENAI_USE_VERTEXAI=FALSE`: le indica a ADK que use AI Studio en
lugar de Vertex AI.

### API key de Google Maps (solo para los dos agentes de Maps)

Si no la configurás, esos dos agentes van a mostrar un error de configuración
en `adk web`, y los otros tres funcionan igual.

1. En [Google Cloud Console](https://console.cloud.google.com/) creá (o elegí) un proyecto. Maps Platform es de pago por uso y requiere una cuenta de facturación asociada; revisá los [precios vigentes](https://mapsplatform.google.com/pricing/) antes de habilitar las APIs. Estos ejemplos hacen muy pocas llamadas.
2. Creá una API key en *APIs y servicios → Credenciales* y pegala en `.env` como `GOOGLE_MAPS_API_KEY=...`.
3. Habilitá las APIs en *APIs y servicios → Biblioteca*:
   - `maps_agent`: Geocoding API, Places API, Directions API, Distance Matrix API y Elevation API (las que llama ese servidor). Google clasificó varias de ellas como "Legacy" y en proyectos nuevos puede no permitirte habilitarlas: si te pasa, usá `maps_agent_grounding_lite`, que es el reemplazo oficial.
   - `maps_agent_grounding_lite`: Maps Grounding Lite (`mapstools.googleapis.com`).
4. Recomendado: restringí la key a esas APIs.

## Cómo correr

Desde `labs_MCP/`, con el venv activado:

```bash
adk web
```

Abrí <http://127.0.0.1:8000> y elegí el agente en el desplegable. Para ver el
grafo del agente y las llamadas a tools, usá las pestañas *Trace* y *Events*.

> Si ya exportaste `GOOGLE_API_KEY` u otras variables en tu terminal, esas
> tienen prioridad sobre el `.env`. Ante un comportamiento raro, abrí una
> terminal nueva.

## Prompts de ejemplo

| Agente | Prompts |
|---|---|
| `weather_agent` | *"¿Qué clima hace en Buenos Aires?"* · *"Dame el pronóstico de Córdoba a 3 días"* · *"¿Qué ciudades soportás?"* |
| `mcp_agent` | *"List files in the current directory"* · *"Can you read the file named sample.txt?"* |
| `web_reader_agent` | *"Traeme el contenido de https://example.com"* |
| `maps_agent` | *"¿Cuánto se tarda en auto de la Torre UTDT (Av. Pres. Figueroa Alcorta 7350, Buenos Aires) al Obelisco?"* — usá la dirección completa: con el nombre corto a veces no geocodifica bien |
| `maps_agent_grounding_lite` | *"¿Qué clima hace en Buenos Aires?"* (tiene tool de clima, a diferencia de `maps_agent`) · *"Buscá cafeterías cerca de la Torre UTDT"* |

## Qué mirar en cada ejemplo

- **`weather_agent`**: abrí `weather_mcp_server.py`. Las tres funciones con `@mcp.tool` son todo el servidor; FastMCP genera el schema de cada tool a partir de los type hints y el docstring. El agente (`weather_agent/agent.py`) lo lanza como subproceso y le habla por stdio.
- **`mcp_agent`**: el agente no tiene código de archivos; la carpeta a la que el servidor puede acceder es `mcp_agent/archivos_demo/`. Probá pedirle que cree un archivo nuevo ahí. Probá también el `tool_filter` comentado en `agent.py`.
- **`web_reader_agent`**: compará `adk_mcp_server/adk_server.py` (servidor) con `web_reader_agent/agent.py` (cliente) para ver cómo una `FunctionTool` de ADK se convierte en una tool MCP.
- **`maps_agent` vs. `maps_agent_grounding_lite`**: mismo caso de uso con dos transportes. Compará latencia, tools disponibles y qué cambia en `StdioConnectionParams` vs. `StreamableHTTPConnectionParams`.

## Problemas frecuentes

- **`npx: command not found`** — instalá Node.js y reabrí la terminal.
- **`Falta GOOGLE_MAPS_API_KEY`** — completá la key en `.env` o ignorá los dos agentes de Maps.
- **El agente de Maps responde con un error de permisos (`REQUEST_DENIED`)** — falta habilitar alguna de las APIs de la lista en tu proyecto.
- **`401`/`403`/`API key not valid` del modelo** — revisá `GOOGLE_API_KEY` y que `GOOGLE_GENAI_USE_VERTEXAI=FALSE`.
- **Timeout al iniciar un agente con `npx`** — la primera vez npx descarga el paquete; volvé a intentar.
- **Una ruta relativa deja de funcionar** — `StdioServerParameters` resuelve rutas relativas contra el directorio desde el que corriste `adk web`, no contra el `agent.py`. Por eso los agentes calculan rutas absolutas con `Path(__file__)`.
