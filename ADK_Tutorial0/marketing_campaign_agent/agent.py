import os

try:
    from dotenv import load_dotenv
    load_dotenv()

    MODEL_NAME = os.environ.get("GOOGLE_GENAI_MODEL", "gemini-2.5-flash")
except ImportError:
    print("Warning: python-dotenv not installed. Ensure API key is set")
    MODEL_NAME = "gemini-2.5-flash"

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search

from .instructions import (
    MARKET_RESEARCH_INSTRUCTION,
    MESSAGING_STRATEGIST_INSTRUCTION,
    AD_COPY_WRITER_INSTRUCTION,
    VISUAL_SUGGESTER_INSTRUCTION,
    FORMATTER_INSTRUCTION,
    CAMPAIGN_ORCHESTRATOR_INSTRUCTION
)

# Sub-agente 1: el único con una tool (google_search). Guarda su resultado en
# el estado de la sesión bajo la clave "market_research_summary" (output_key).
market_research_agent = LlmAgent(
    name="MarketResearcher",
    model=MODEL_NAME,
    instruction=MARKET_RESEARCH_INSTRUCTION,
    tools=[google_search],
    output_key="market_research_summary"
)

# Sub-agentes 2 a 4: cada uno lee, dentro de su instruction (ver instructions.py),
# el output_key del anterior — así se pasan la posta sin que el usuario intervenga.
messaging_strategist_agent = LlmAgent(
    name="MessagingStrategist",
    model=MODEL_NAME,
    instruction=MESSAGING_STRATEGIST_INSTRUCTION,
    output_key="key_messaging"
)

ad_copy_writer_agent = LlmAgent(
    name="AdCopyWriter",
    model=MODEL_NAME,
    instruction=AD_COPY_WRITER_INSTRUCTION,
    output_key="ad_copy_variations"
)

visual_suggester_agent = LlmAgent(
    name="VisualSuggester",
    model=MODEL_NAME,
    instruction=VISUAL_SUGGESTER_INSTRUCTION,
    output_key="visual_concepts"
)

# Sub-agente 5: el cierre del pipeline — lee los 4 output_key anteriores a la vez
# y arma el brief final en Markdown.
formatter_agent = LlmAgent(
    name="CampaignBriefFormatter",
    model=MODEL_NAME,
    instruction=FORMATTER_INSTRUCTION,
    output_key="final_campaign_brief"
)

# SequentialAgent: ejecuta los 5 sub-agentes EN ORDEN, uno atrás del otro,
# compartiendo el mismo estado de sesión. Es la pieza de orquestación que
# convierte 5 agentes independientes en un pipeline con una sola entrada
# (la idea de producto) y una sola salida (el brief final).
campaign_orchestrator = SequentialAgent(
    name="MarketingCampaignAssistant",
    description=CAMPAIGN_ORCHESTRATOR_INSTRUCTION,
    sub_agents=[
        market_research_agent,
        messaging_strategist_agent,
        ad_copy_writer_agent,
        visual_suggester_agent,
        formatter_agent,
    ]
)

root_agent = campaign_orchestrator
