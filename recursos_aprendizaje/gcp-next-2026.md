---
name: Google Cloud Next 2026 — Servicios y Anuncios
description: Conceptos, servicios y cambios de nombre clave de Google Cloud Next 2026. Referencia para demos, arquitecturas y presentaciones sobre GCP moderno.
date-added: 2026-05-22
source-project: Chile-presentacion-demo (demo NowAgent Analytics / Agentic Data Cloud)
---

# Google Cloud Next 2026 — Conocimiento de Dominio

## Cambios de nombre críticos

| Nombre anterior | Nombre actual (desde Next 2026) | URL consola | API Python |
|----------------|--------------------------------|-------------|------------|
| Dataplex Universal Catalog | **Knowledge Catalog** | `console.cloud.google.com/dataplex/govern/catalog` | `google.cloud.dataplex_v1.CatalogServiceClient` |
| Vertex AI (plataforma de agentes) | **Gemini Enterprise Agent Platform** | — | — |

> El cambio de nombre de Dataplex → Knowledge Catalog ocurrió el 10 de abril de 2026.
> Vertex AI → Gemini Enterprise Agent Platform: anunciado en Google Cloud Next 2026.
> Las URLs de consola y las APIs no cambiaron — solo el nombre comercial.

---

## Concepto paraguas: Agentic Data Cloud

La arquitectura central anunciada en Google Cloud Next 2026. Premisa: el cuello de botella de los agentes autónomos no es el modelo ni el compute — es el **contexto**. Agentic Data Cloud resuelve ese problema con tres pilares:

### Pilar 1 — Knowledge Catalog
- Grafo semántico corporativo enriquecido automáticamente por Gemini
- No es un catálogo de metadata técnica: contiene el **significado de negocio** de cada dato (qué KPI es, cuál es su target, cómo se calcula para esta empresa)
- Se auto-enriquece leyendo documentos internos, dashboards, logs de queries — sin tagging manual
- Incluye **Data Insights**: queries sugeridas basadas en historial de uso real, relaciones entre tablas inferidas automáticamente
- Integración directa con BigQuery: sincroniza descripciones de tablas y columnas
- Implementación práctica: `CatalogServiceClient().search_entries()` con `SearchEntriesRequest`

### Pilar 2 — Cross-Cloud Lakehouse
- Datos en AWS S3 o Azure Blob consultados desde BigQuery **sin moverlos**
- Construido sobre Apache Iceberg (estándar abierto, sin vendor lock-in)
- Federación bidireccional
- Para equipos de AI: elimina la espera de 6 meses de pipelines de migración antes de poder construir el agente

### Pilar 3 — Data Agent Kit
- Skills, herramientas y conectores para que agentes sean ciudadanos nativos del ecosistema de datos
- Permite orquestación de agentes especializados que se componen para resolver problemas de negocio
- Concepto clave: el data scientist de 2026 orquesta agentes, no ajusta modelos en notebooks

---

## Gemini Enterprise Agent Platform — Gobernanza de flota de agentes

Para llevar agentes a producción corporativa, GCP ofrece 5 capas de gobernanza:

### ① Agent Registry
- Catálogo central de todos los agentes de la organización
- Por cada agente: versión, modelo base, tools habilitadas, owner, SLA, estado de aprobación
- Ningún agente corre en producción sin estar registrado
- También registra qué agente puede llamar a qué otro (gobernanza de A2A)
- Equivalente al repositorio de código pero para agentes

### ② Agent Identity
- Cada agente tiene su propia Service Account (identidad criptográfica única)
- Principio de mínimo privilegio: el agente solo accede a lo que está explícitamente autorizado
- IAM bloquea y registra automáticamente cualquier intento de acceso no autorizado
- Nunca hereda credenciales del usuario que lo invoca

### ③ Agent Gateway
- Proxy centralizado de todas las llamadas del agente a APIs externas
- DLP en tiempo real: detecta y redacta datos sensibles antes de que salgan del perímetro
- Rate limiting por agente
- Bloqueo de endpoints no autorizados

### ④ Agent Sandbox
- Todo código generado por el agente (Python, scripts) corre en un contenedor efímero aislado
- Aislado de la red interna y de sistemas productivos
- El contenedor se destruye automáticamente al terminar
- Protege contra bugs, loops infinitos o comportamientos inesperados del código generado

### ⑤ Cloud Audit Logs
- Trazabilidad automática de cada acción del agente: qué consultó, cuándo, bajo qué identidad, con qué resultado
- No es opcional: es el requisito de compliance para producción corporativa
- Permite auditar decisiones autónomas y detectar anomalías

---

## Protocolo A2A (Agent-to-Agent)

- Estándar Google Cloud para delegación de trabajo entre agentes especializados
- Permite: especialización, paralelismo, separación de responsabilidades
- Las llamadas A2A también requieren gobernanza → registradas en Agent Registry
- Ejemplo: Agente Analítico → (A2A) → Agente de Comunicaciones (redacta y envía email)

---

## Nuevas capacidades para equipos AI/DS

| Capacidad | Descripción |
|-----------|-------------|
| **Memory Bank / Memory Profiles** | Memoria persistente para agentes entre sesiones; fin del "cada sesión empieza de cero" |
| **Deep Research Agent** | Razonamiento multi-paso con citaciones sobre BigQuery + documentos internos |
| **TabularFM** | Modelo foundational zero-shot para regresión y clasificación tabular; menos feature engineering |
| **AI.PARSE_DOCUMENT** | Documentos no estructurados y datos estructurados en la misma query SQL de BigQuery |
| **Conversational Analytics** | Chat con BigQuery, Looker y AlloyDB sin escribir SQL |
| **Vertex AI Grounding** | Ancla cada afirmación del agente a datos reales verificables; elimina alucinaciones |

---

## Notas de implementación práctica (ADK)

- **SDK Python**: `google-adk>=1.34.0` (package `google-adk` via uv/pip)
- **Knowledge Catalog API**: `google.cloud.dataplex_v1.CatalogServiceClient().search_entries()` con `SearchEntriesRequest(name="projects/<PROJECT>/locations/global", query=..., page_size=6)`
- **Acceder a descripción de una tabla/columna**: `result.dataplex_entry.entry_source.description` (no `entry.description`)
- **DataScans** (Data Profile / Data Documentation): requieren dataset en single-region (no `US` multi-region), service agent `service-<NUM>@gcp-sa-dataplex.iam.gserviceaccount.com` con `roles/bigquery.dataViewer` + `roles/bigquery.jobUser`; en algunos entornos sandbox pueden estar restringidos a nivel de organización
- **Modelo para demos**: `gemini-flash-latest` o `gemini-2.0-flash-001`
- **Patrón ReAct** en ADK: el trace muestra Thought → Action (tool call) → Observation en cada iteración; no sigue flujo hardcodeado

---

## Patrón arquitectónico de referencia (NowAgent Analytics)

```
Email/Trigger
    │
    ▼
Cloud Run + Eventarc
    │
    ▼
Vertex AI Agents — ADK (google.adk.agents.Agent)
    │  Identity: <agente>@<project>.iam.gserviceaccount.com
    │  Agent Sandbox: código generado corre en contenedor efímero
    │
    ├──→ [get_catalog_context]
    │       Knowledge Catalog (Dataplex CatalogServiceClient)
    │       → Contexto semántico de tablas y columnas
    │
    ├──→ [execute_bigquery_query]
    │       BigQuery: datos estructurados
    │       → SQL autónomo sobre dataset del negocio
    │
    └──→ [search_strategy_docs]
            BigQuery: tabla de documentos internos
            → Contexto cualitativo y estratégico
    │
    ▼
Respuesta con citaciones [CATALOG:] [DOC:] [DATOS:]
    │
    ▼ (A2A)
Agente de Comunicaciones → Respuesta al usuario final

Observabilidad: Cloud Audit Logs (automático por Service Account)
```

---

## Transición conceptual central

> **System of Intelligence** (reactivo, responde preguntas)
> → **System of Action** (autónomo, investiga + decide + ejecuta + audita)

El mensaje de negocio de Google Cloud Next 2026: la IA empresarial madura cuando puede actuar sobre datos corporativos con identidad propia, herramientas nativas, y trazabilidad completa — no solo cuando responde bien una pregunta en un chat.
