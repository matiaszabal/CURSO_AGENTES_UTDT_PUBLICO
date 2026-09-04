# Tutorial 0 — Introducción a Google ADK

Tres ejemplos curados y probados en vivo para dar los primeros pasos con **Google ADK** (Agent Development Kit), el framework de Google para construir agentes basados en LLM: agentes con tools, agentes que se encadenan entre sí, y agentes que fuerzan su salida a un formato estructurado.

Adaptado desde [github.com/AhsanAyaz/ai-agents-google-adk](https://github.com/AhsanAyaz/ai-agents-google-adk) (tiene más ejemplos de los que se incluyen acá — este tutorial se queda con los 3 más simples e intuitivos para arrancar).

## Los tres ejemplos, en orden

| # | Carpeta | Qué aprendés | Nivel |
|---|---|---|---|
| 1 | [`tools_agent/`](tools_agent/) | Qué es una tool y cómo el agente decide usarla solo | Introductorio |
| 2 | [`structured_output/`](structured_output/) | Forzar salida con schema (Pydantic) + encadenar 2 agentes vía estado | Intermedio |
| 3 | [`marketing_campaign_agent/`](marketing_campaign_agent/) | Orquestar un pipeline de 5 agentes con `SequentialAgent` | Cierre / integrador |

Cada carpeta tiene su propio `README.md` con el objetivo puntual del ejemplo, una explicación de cómo está implementado (con fragmentos de código comentados) y consultas de prueba sugeridas. Empezá por el 1 y segui el orden — cada uno suma un concepto sobre el anterior.

## Setup (una sola vez)

```bash
cd ADK/Tutorial0
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Esto instala, entre otras cosas, `google-cloud-aiplatform[adk,agent_engines]`, que trae el **CLI `adk`** que vas a usar para correr los ejemplos.

## Autenticación (elegí UNA de las dos)

Google ADK necesita acceso a un modelo Gemini. Cada ejemplo tiene su propio `.env.example` — copialo a `.env` en esa misma carpeta (`cp .env.example .env`) y completá **una** de estas dos opciones.

⚠️ **El `.env.example` ya viene con la Opción A activa** (lista para completar) **y la Opción B comentada**. Si querés usar la B, comentá las líneas de la A y descomentá las de la B — dejar las dos activas al mismo tiempo hace que gane la B y te tire un error confuso mencionando `tu-project-id`.

### Opción A — Google AI Studio (recomendada para arrancar)

La más simple: no necesitás una cuenta de Google Cloud ni `gcloud` instalado.

1. Conseguí una API key gratis en [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. En el `.env` (ya están activas, solo completá la key):
   ```
   GOOGLE_API_KEY=tu-api-key
   GOOGLE_GENAI_USE_VERTEXAI=FALSE
   ```

### Opción B — Vertex AI con tu cuenta de Google Cloud

Si ya tenés un proyecto de GCP con la API de Vertex AI habilitada:

1. `gcloud auth application-default login`
2. `gcloud config set project tu-project-id`
3. En el `.env`, comentá las 2 líneas de la Opción A y descomentá/completá:
   ```
   GOOGLE_GENAI_USE_VERTEXAI=TRUE
   GOOGLE_CLOUD_PROJECT=tu-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   ```

En ambos casos, el modelo usado es `gemini-2.5-flash` (rápido y con buena relación costo/calidad para estos ejemplos).

## Cómo correr un ejemplo

Desde `ADK/Tutorial0/` (así `adk` detecta los tres a la vez):

```bash
# una sola consulta por consola:
adk run tools_agent "¿qué hora es?"

# o la interfaz web, con selector de ejemplo, historial y grafo de agentes:
adk web
```

`adk web` levanta un servidor local (por defecto en `http://127.0.0.1:8000`) con una UI donde podés:
- Elegir qué ejemplo correr, arriba a la izquierda.
- Chatear con el agente y ver, evento por evento, qué tool o sub-agente se ejecutó.
- Ver el **grafo de la estructura del agente** (ícono junto al selector) — muy útil en `marketing_campaign_agent`, donde se ven los 5 sub-agentes encadenados, resaltados en verde mientras corren.

## Qué está probado

Los tres ejemplos se corrieron de punta a punta contra la API real (vía Vertex AI) sin errores, el **2026-09-03/04** — incluidos los 5 pasos completos de `marketing_campaign_agent` (confirmado por log: 5 llamadas al modelo y cierre limpio del runner) y el tool que pega contra una API externa en `tools_agent` (`get_randomuser_from_ramdomuserme`).

La vía A (Google AI Studio) se dejó bien configurada en el código y los `.env.example` (y se verificó que, tal como quedan los archivos, no cae en la trampa de la sección de arriba), pero no se probó con una API key real en este entorno — antes de una clase en vivo, conviene correr al menos uno con esa opción para confirmar.

**Nota de idioma:** las *instructions* de los agentes (los prompts que definen su comportamiento, en `agent.py`/`instructions.py`) quedaron en inglés — son el código ya probado del repo original, y traducirlas implicaba re-testear todo. En la práctica, el modelo suele responder en el idioma de tu pregunta, pero en las pruebas `marketing_campaign_agent` devolvió el brief mayormente en inglés incluso con una consulta en español. Si para el curso preferís que respondan siempre en español, hay que traducir esas instructions y volver a probar — es una decisión de contenido, no algo que se resuelve solo con documentación.
