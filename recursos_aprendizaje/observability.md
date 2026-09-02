# Agent Observability — trazabilidad en producción

> OPTIMIZE · visibilidad operacional
> Fuente: guión v2 de la presentación Chile-AGP (Agent Platform), sección "Agent Observability" — DEMO-GOOGLE-COMPLETA, 2026-09-02.

Observability en agentes es más compleja que en microservicios tradicionales porque el camino de ejecución es no determinístico —el mismo input puede producir trazas distintas según qué decida invocar el modelo en cada turno. Necesitás ver cada paso, no sólo input y output agregados.

**[señalar los cuatro niveles]** Traces: cada paso del flujo ReAct, con la tool invocada, input, output, latencia y tokens. Logs: eventos estructurados por la convención semántica GenAI de OpenTelemetry —`gen_ai.user.message`, `gen_ai.choice`, `gen_ai.system.message`— capturados en Cloud Logging junto con eventos de Model Armor y errores de tools. Métricas: latencia p50/p95/p99, success rate, consumo de tokens de entrada y salida. Y Sessions: sesiones activas, turnos promedio, usuarios únicos.

**[nota técnica sobre el mecanismo]** El mecanismo concreto: activar `otel_to_cloud` instrumenta el runtime con un exportador OTLP hacia el endpoint unificado de telemetría de Google Cloud, autenticado con las credenciales de la service account del agente. Eso requiere un permiso IAM específico —`roles/cloudtrace.agent`, que incluye `telemetry.traces.write`— sin el cual el runtime sigue funcionando con normalidad pero cada intento de exportar un batch de spans falla en silencio con 403, y la consola de Trace queda vacía aunque el agente responda correctamente. Es un modo de falla típico de plataforma: nada se rompe funcionalmente, pero la visibilidad desaparece sin ningún síntoma para el usuario final.

**[señalar Unified Trace Viewer]** Unified Trace Viewer —anunciado en Google Cloud Next '26— consume esos mismos traces para dar visibilidad en tiempo real del camino de razonamiento, paso a paso, dentro de la consola: cuándo el agente entró en un loop repetitivo, en qué tool falló, cuánto tardó cada step — sin correlacionar logs dispersos a mano.

**[señalar el feedback loop]** El feedback loop en producción tiene cinco pasos. Monitor con alertas cuando latencia o error rate sube sobre baseline. Diagnose para identificar si el fallo está en una tool, en el contexto o en el prompt. Fix + Eval para corregir y validar contra el pipeline de evaluación que las métricas no bajaron. Deploy nuevo al Agent Registry con nuevo resource ID. Y Rollback si falla — el Registry mantiene la versión anterior disponible, rollback en segundos. Es el ciclo completo de operación de un sistema agéntico en producción.

---

## OpenTelemetry (OTel)

> Fuente: notas propias sobre el proyecto de guardrails (litellm_guardrails_practice / adk_tool_guard_practice), 2026-09-02.

Es un estándar abierto (proyecto de la CNCF) para instrumentar software y capturar tres tipos de señales de forma vendor-neutral:

- **Traces**: la cadena de eventos de una request, como un árbol de spans. Cada span tiene nombre, timestamps, atributos clave-valor, y puede tener hijos (spans anidados) — así se ve el flujo completo de una operación distribuida.
- **Metrics**: contadores, gauges, histogramas (latencia, throughput, error rate).
- **Logs**: eventos puntuales, correlacionables con el trace/span activo en ese momento.

El protocolo de transporte es **OTLP** (OpenTelemetry Protocol) — cualquier backend que lo hable (Jaeger, Tempo, Langfuse, Cloud Trace, Datadog, etc.) puede recibir los datos sin acoplar tu código a un vendor específico. Esa es la propuesta de valor: instrumentás una vez, exportás a donde quieras.

### Aplicado a observability de agentes

En un agente LLM, cada span representa un paso: una llamada al modelo, una tool call, un retrieval, un guardrail check. Para estandarizar esto entre frameworks, OTel define **semantic conventions para GenAI** (atributos `gen_ai.*`: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, etc.) — así un span de "llamada a Gemini" se ve estructuralmente igual venga de LangChain, de ADK, o de un SDK custom.

Ya hay esto corriendo en el proyecto de guardrails, aunque no se lo haya nombrado así explícitamente: **Langfuse v4 es OTel-based por dentro**. El callback `langfuse_otel` que se usa en `litellm_guardrails_practice/config.yaml` y `config_gemini.yaml` es justamente eso — LiteLLM emite spans OTel, Langfuse los recibe vía OTLP. Al instrumentar el Tool Guard y el guard de Llama Guard con `start_as_current_observation(as_type="guardrail")` / `as_type="generation"`, se estaban creando spans OTel con atributos semánticos específicos de GenAI. Y al armar `flywheel_export.py` leyendo `events_core` en ClickHouse, se estaba leyendo el JSON OTLP crudo que Langfuse persiste — la evidencia de que todo esto es OTel debajo del capó, no una API propietaria de Langfuse.

### Cómo se usa específicamente en GCP

El backend nativo de GCP para traces es Cloud Trace, que habla OTLP directamente (o vía el OpenTelemetry Collector con el exporter `googlecloudexporter`).

Puntos concretos para agentes en GCP:

- **Vertex AI Agent Engine / Agent Builder**: cuando se despliega un agente ahí, las invocaciones generan trazas automáticamente exportables a Cloud Trace sin instrumentación manual — es el mismo patrón que en [gcp-next-2026.md](gcp-next-2026.md) (línea 113) sobre el patrón ReAct de ADK: el trace muestra Thought → Action (tool call) → Observation en cada iteración, que es literalmente una cadena de spans OTel.
- **ADK local** (como el de `adk_tool_guard_practice/`): no tiene el auto-export a Cloud Trace activado por default corriendo local — para eso hace falta configurar el exporter de OTel apuntando a Cloud Trace API (`cloudtrace.googleapis.com`), algo que no se hizo en esa sesión (se usó Langfuse como backend en su lugar, una alternativa self-hosted al mismo propósito).
- **Cloud Monitoring** consume las métricas OTel (latencia por modelo, tokens consumidos, tasa de error de guardrails) para dashboards/alerting — el mismo tipo de dato que hoy se saca manualmente de ClickHouse con el Flywheel, pero con Cloud Monitoring estaría como dashboard nativo si se exportara a GCP en vez de (o además de) Langfuse.

### Cómo verificarlo si se quiere probar

El camino más corto sería agregar el exporter OTLP de Cloud Trace al mismo LiteLLM proxy que ya está corriendo (`callbacks: ["langfuse_otel"]` podría convivir con un segundo callback apuntando a GCP, o LiteLLM tiene soporte nativo para `google_cloud_trace` como callback) y comparar los spans en Cloud Trace Explorer contra lo que ya se ve en Langfuse — mismo dato, dos backends.

**Pendiente relacionado, sin resolver:** armar la variante `-gcp-trace` como comparación (mismo patrón `-gemini` ya usado), o retomar el swap de Capa 2 a Gemini que había quedado pausado a mitad de camino (Input/Output Guard ya verificado con Gemini como modelo bajo prueba; faltaba el Tool Guard de ADK).
