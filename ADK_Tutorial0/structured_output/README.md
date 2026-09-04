# 2. structured_output — Salida estructurada y agentes encadenados

## Objetivo

Sumar dos conceptos nuevos sobre lo visto en `tools_agent`:

1. **Forzar la salida del LLM a un schema** (Pydantic), en vez de confiar en que el modelo devuelva texto en el formato que pediste.
2. **Encadenar dos agentes** donde el segundo recibe, ya tipado, el resultado del primero.

El caso de uso: el usuario cuenta un problema personal (finanzas, estrés, alimentación, etc.), un primer agente lo clasifica y recomienda qué tipo de profesional consultar, y un segundo agente arma una respuesta de orientación inicial con ese diagnóstico.

## Cómo funciona (código en `agent.py`)

**Paso 1 — el schema es el contrato:**

```python
class ProblemAnalysis(BaseModel):
    consultant_type: ConsultantTypeEnum
    identified_issues_summary: str
```

`output_schema=ProblemAnalysis` en el primer agente (`ProblemAnalyzerAgent`) obliga a que su respuesta sea un JSON válido contra ese modelo — nada de texto libre, nada de parsear manualmente la respuesta del LLM con regex. `consultant_type` además está restringido a un `Enum` (10 valores posibles): el modelo no puede inventar una categoría que no exista.

**Paso 2 — el estado conecta los agentes:**

`output_key="problem_analysis_result"` guarda ese JSON en el estado compartido de la sesión. El segundo agente lo referencia directo en su instrucción con `{problem_analysis_result}`, y además declara `input_schema=ProblemAnalysis` — así ADK valida que lo que recibe tiene la forma esperada antes de generar su propia salida (`output_schema=ConsultationResp`, un modelo más grande con explicación, preguntas y próximos pasos).

**Paso 3 — `SequentialAgent` los une:**

```python
root_agent = SequentialAgent(
    name="StructuredConsultationAgent",
    sub_agents=[problem_analyzer_agent, advice_generator_agent],
)
```

Ejecuta los sub-agentes en orden, uno atrás del otro, compartiendo el mismo estado de sesión — es el mecanismo que permite el paso 2.

## Cómo correr

Desde `ADK/Tutorial0/` (con el venv ya activado, ver el README raíz):

```bash
cd structured_output
cp .env.example .env   # completá la Opción A o B — ver ../README.md
cd ..

adk run structured_output "no sé cómo organizar mis finanzas"
# o con interfaz web (podés ver el JSON de cada paso y el grafo de los 2 agentes):
adk web
```

## Preguntas para probar

- "no sé cómo organizar mis finanzas" → debería recomendar `financial_advisor`
- "últimamente como muy mal y no tengo energía para hacer ejercicio" → probablemente `nutritionist` o `personal_trainer`
- Algo muy vago tipo "no sé qué hacer con mi vida" → buen caso para ver cómo cae en `general_helper`
