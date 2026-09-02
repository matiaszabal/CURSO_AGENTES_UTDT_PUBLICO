# Memory Sessions y Memory Bank en Google Cloud Agent Platform

> Fuente: conversación con Gemini, guardada el 2026-09-02. https://share.gemini.google/2HyEYxfojqYX

En la plataforma de agentes de Google Cloud (Vertex AI Agent Engine / Agent Platform), el manejo de contexto se divide estructuralmente en dos primitivas complementarias: **Sessions** (memoria de corto plazo o intra-sesión) y **Memory Bank** (memoria de largo plazo o inter-sesión).

## 1. Distinción arquitectónica

| Dimensión | Memory Sessions (Sessions) | Memory Bank |
|---|---|---|
| Scope / vida útil | Intra-sesión (ephemeral/bounded). Asociado a un `session_id` único. | Cross-session (persistent). Asociado a una identidad (`user_id` o custom scopes). |
| Naturaleza del dato | Secuencial y literal (transcripción cruda de turns, events, tool_calls). | Semántica y consolidada (hechos extraídos, entidades y preferencias). |
| Mecanismo de ingesta | Append sincrónico (`AppendEvent`) en tiempo de ejecución. | Extracción asíncrona mediante un LLM de fondo (`GenerateMemories`) o escritura explícita (`CreateMemory`). |
| Recuperación | Retrieval determinista por ventanas de contexto/historial de turnos. | Retrieval semántico por Embedding/Similarity Search (`text-embedding-005`, `text-multilingual-embedding-002`) o scope directo. |

## 2. Deep dive: Memory Sessions (intra-session state)

Funciona como la capa de persistencia inmediata para el working memory del agente.

- **Event Logging Structure**: cada interacción se registra mediante `AppendEvent`. Contiene mensajes del usuario, model outputs, llamadas a herramientas (`tool_use`), respuestas de API y variables de estado del flujo.
- **Window & Token Management**: controla el buffer de mensajes que entra directamente al context window del LLM en cada turn. Si la conversación excede los límites, Sessions permite estrategias de truncado o sliding window, sirviendo como la fuente de verdad histórica sin perder el orden cronológico estricto.

### Conceptos clave

- **Scope identificado (`session_id`)**: representa un hilo de conversación o ejecuciones vinculadas bajo un identificador único. Toda la información dentro de una sesión es aislada y efímera a esa iteración.
- **Append-only logging**: cada interacción se persiste secuencialmente mediante `AppendEvent`. Este registro no solo almacena texto plano, sino una estructura rica que incluye:
  - Mensajes del usuario (`UserMessage`)
  - Respuestas del modelo (`ModelOutput`)
  - Invocaciones y retornos de herramientas (`ToolCall` / `ToolResponse`)
  - Cambios en variables de estado de la sesión (`SessionState`)
- **Context Window Buffer**: funciona como la fuente de verdad que alimenta directamente la ventana de contexto del LLM en cada turno.

### Gestión de estado y truncado

Dado que los modelos tienen un límite de tokens por contexto, Sessions provee primitivas para gestionar el historial:

- **Sliding Window**: mantiene únicamente los últimos N turnos o K tokens más recientes para construir el prompt entrante.
- **State Variables**: permite persistir pares clave-valor (meta-información de la sesión) independientemente del truncado del historial de chat, garantizando que variables de contexto críticas (ej. `user_authenticated: true`, `active_order_id: 8841`) no se pierdan al descartar turnos antiguos.

### Ciclo de vida de una sesión

```
[Cliente] ──> CreateSession() ──> session_id: "sess_9981"
   │
   ├──> AppendEvent(User: "Hola") ─────────────► [ Session Log ]
   ├──> GetSessionHistory() ───────────────────► [ Inyección a Prompt LLM ]
   ├──> AppendEvent(Model: "Tool Request") ────► [ Session Log ]
   ├──> AppendEvent(ToolResponse: {...}) ─────► [ Session Log ]
   │
   └──> EndSession() / Expiration (TTL) ──────► Liberación / Ingesta a Memory Bank
```

Una vez que la sesión finaliza o expira por TTL (Time-To-Live), el log crudo de la sesión puede ser consumido asíncronamente por el Memory Bank para la extracción de recuerdos permanentes, pero la sesión en sí deja de mutar.

## 3. Deep dive: Memory Bank (long-term semantic storage)

A diferencia de Sessions (que guarda logs lineales de una conversación activa), Memory Bank sintetiza la información, resuelve contradicciones y persiste hechos, entidades e instrucciones explícitas vinculados a una entidad (`user_id` o scope).

### Pipeline interno

```
[ Sessions (Raw Dialogue Logs) ]
        │
        ▼ (Async Pipeline: GenerateMemories)
┌─────────────────────────────────────────────────┐
│ Extraction Engine                                │
│ - Filters managed topics (Personal Info,         │
│   Preferences, Explicit Instructions)             │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│ Consolidation Layer                              │
│ - Conflict resolution (updates old facts)        │
│ - Deduplication & Entity Resolution              │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│ Vector Index & Metadata Storage                  │
│ (Isolated by scope, e.g., user_id)               │
└─────────────────────────────────────────────────┘
        │
        ▼ (Preload or Tool-based Retrieval)
[ Context Injection to Agent Turn ]
```

### 3.1 Ingesta y extracción (async `GenerateMemories`)

Consume transcripciones crudas de Sessions o JSONs externos mediante operaciones asíncronas. Un LLM ligero (por defecto `gemini-2.5-flash`) procesa el diálogo analizando Memory Topics:

- **Managed Topics**: reglas predefinidas de la plataforma (`USER_PERSONAL_INFO`, `USER_PREFERENCES`, `EXPLICIT_INSTRUCTIONS`).
- **Custom Topics**: tópicos definidos por el desarrollador mediante `CustomizationConfig` para capturar lógica del dominio de negocio.
- **Few-Shot Examples**: posibilidad de pasar pares (`conversation_source`, `generated_memories`) para guiar la precisión de la extracción.

### 3.2 Consolidador y resolución de conflictos

Evita el bloat de almacenamiento y la redundancia en el context window mediante dos reglas:

- **Deduplicación**: si un hecho extraído ya existe en la base semántica del usuario, no genera una nueva entrada.
- **Mutación/Update**: si un hecho entra en conflicto directo con uno previo (ej. de "el usuario vive en Buenos Aires" a "el usuario se mudó a Madrid"), el motor actualiza la memoria atómica invalidando el valor obsoleto. Ejemplo: si una sesión previa indica "el usuario prefiere respuestas en Python" y una nueva sesión especifica "ahora uso Go para microservicios", el motor fusiona los hechos actualizando la preferencia sin duplicar nodos.

### 3.3 Mutación manual (`CreateMemory` / memory-as-a-tool)

Bypass directo del pipeline asíncrono. Permite que un agente con capacidad de Function Calling inserte o modifique registros atómicos en el Memory Bank en tiempo real de ejecución, sin esperar la extracción asíncrona de fin de sesión.

### 3.4 Mecanismos de recuperación (retrieval)

- **Scope-based Exact Lookup**: filtro estructurado determinista (ej. `query_memories(scope={"user_id": "usr_9941"})`). Retorna el grafo o lista completa de hechos del usuario.
- **Vector Similarity Search**: conversión del prompt o mensaje entrante a embeddings (mediante `text-embedding-005` o `text-multilingual-embedding-002`) ejecutando una búsqueda k-NN semántica contra el historial consolidado. Inyecta únicamente las memorias relevantes al turno actual, optimizando el costo de tokens.

### 3.5 Configuraciones avanzadas y gobierno

- **Time-to-Live (TTL)**: expiración automática configurable a nivel de memoria o sesión (ej. retención de recuerdos temporales por 30 días).
- **Model Customization**: decoupling del `generation_model` (encargado del razonamiento/sintaxis de extracción) y el `embedding_model` (encargado del vector space).
- **Isolation Scope**: aislamiento lógico estricto de datos multi-tenant respaldado por la infraestructura de GCP (VPC-SC, IAM y encriptación KMS).

## 4. Integración vía ADK (Agent Development Kit)

En el marco de desarrollo de agentes en Vertex AI (ADK), la integración se realiza de forma nativa mediante herramientas de orquestación en el prompt del sistema:

- **Preload Strategy (`PreloadMemoryTool`)**: en cada turn, el Agent Engine realiza un similarity search automático en el Memory Bank usando el prompt entrante, e inyecta los top-k recuerdos relevantes directamente en la System Instruction antes de pasar el control al modelo.
- **On-Demand Strategy (`MemoryTool`)**: el agente decide dinámicamente, mediante Function Calling, cuándo consultar el Memory Bank o escribir un registro en él mediante `retrieve_memories()` o `create_memory()`.

---

**Nota de contraste con la implementación propia**: en `agentic-retail-demo`/`nowagent-analytics` (ver memorias del proyecto DEMO-GOOGLE-COMPLETA) se usa exactamente el patrón Preload — `PreloadMemoryTool()` en la lista de tools del agente + `generate_memories(config={"wait_for_completion": True})` disparado al cierre de una sesión — validado en producción con el caso Carlos Mendez/NovaMart (memoria del Día 1 recuperada automáticamente en la sesión del Día 2, scope `user_id`).
