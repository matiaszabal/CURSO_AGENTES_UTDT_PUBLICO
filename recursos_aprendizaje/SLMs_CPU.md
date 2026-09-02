# Modelos open-source para correr localmente sin GPU (CPU-only)

Investigación puntual (2026-07-27) para adaptar los labs del curso a un backend
LLM local, sin depender de cuota/costo de API (Gemini, Anthropic). Contexto:
`google-adk` soporta cualquier modelo servido con interfaz OpenAI-compatible vía
su wrapper `LiteLlm`, así que el mismo mecanismo que se usaría para Anthropic
(`LiteLlm(model="anthropic/...")`) sirve para un modelo local servido por Ollama:

```python
from google.adk.models.lite_llm import LiteLlm
model = LiteLlm(model="ollama_chat/qwen3.5:4b")
```

Cero código adaptador nuevo — solo cambiar el string del modelo en los labs
basados en ADK (p. ej. Lab 8.A/8.B de Red Teaming).

## Recomendación

**Qwen3.5:4b** vía Ollama — mejor balance de tool-calling nativo confiable +
liviano para CPU, para máquinas sin GPU.

```bash
ollama pull qwen3.5:4b
```

## Comparativa de opciones evaluadas

| Modelo | Tamaño | Tool-calling | Notas |
|---|---|---|---|
| **Qwen3.5:4b** | 4B | Nativo, buenos resultados en BFCL-V4 | Pick recomendado — mejor balance velocidad/confiabilidad en CPU |
| Qwen3.5:9b | 9B | Nativo, más preciso | Hay un [issue abierto en Ollama](https://github.com/ollama/ollama/issues/14745): a veces imprime el tool call como texto en vez de ejecutarlo |
| Gemma 4 (E4B) | ~4B efectivo | ~86% en τ2-bench (mejora fuerte vs. Gemma 3) | En CPU x86 genérica, benchmarks encontrados dan solo ~2-5 tok/s — más lento que Qwen3.5:4b |
| Gemma 3 | — | Solo ~6.6% en τ2-bench | **Evitar** para tareas agénticas — no diseñado para tool-calling confiable |
| Phi-4-mini-instruct | 3.8B | Diseñado con foco en CPU y formato function-calling | Buen plan B si Qwen3.5 da problemas en la práctica |
| SmolLM3 | 3B | — | Mencionado en varias fuentes como opción CPU-friendly, no evaluado a fondo |
| Llama 3.2 | 3B | Débil — JSON parse rate de solo 47.8–56.5% en benchmarks encontrados | No recomendado para tool-calling estructurado a este tamaño |

## Expectativa de performance en CPU (sin GPU)

- Modelos ~3-4B: en el orden de varios tokens/seg en CPU x86 genérica (mucho
  más rápido en Apple Silicon, no aplica acá).
- Para labs con tool-calling encadenado (3-4 pasos, p. ej. Lab 8.2.6 chaining,
  8.2.9 orchestration en las slides de teoría de ch08) contar con que cada
  corrida completa tome uno o varios minutos — viable para trabajo asincrónico,
  ajustado para demo en vivo de clase.
- Verificado en esta máquina: AMD Ryzen 7 3700U (8 threads), 13GB RAM — sin GPU.

## Sources

- [Best CPU-only local LLMs in 2026: what runs well without a GPU](https://www.popularai.org/p/best-cpu-only-local-llm-2026)
- [Best Local LLM Models 2026: Benchmarks, Hardware, and Use Cases — RockB](https://baeseokjae.github.io/posts/best-local-llm-models-2026/)
- [The Best Open Source and Open-Weight LLM Models to Run Locally in 2026 — Hugging Face](https://huggingface.co/blog/daya-shankar/open-source-llm-models-to-run-locally)
- [Best Open-Source LLM Models in 2026: Coding, Local, Agentic AI, Benchmarks, and License — Hugging Face](https://huggingface.co/blog/daya-shankar/open-source-llms)
- [The Best Open-Source Small Language Models (SLMs) in 2026 — BentoML](https://www.bentoml.com/blog/the-best-open-source-small-language-models)
- [CPU-Only LLM 2026: Phi-4 Mini Runs 12 tok/s, No GPU](https://www.promptquorum.com/local-llms/best-cpu-only-llm)
- [Best Open-Source LLMs for Coding You Can Run Locally (2026)](https://www.proxpc.com/blogs/best-open-source-llms-for-coding-you-can-run-locally-2026)
- [7 Best Small Language Models Under 10B Parameters in 2026](https://www.labellerr.com/blog/best-small-language-models-under-10b-parameters/)
- [The Best Small Language Models in 2026: A Practical Comparison — TinyWeights.dev](https://tinyweights.dev/posts/best-small-language-models-2026/)
- [Local AI in 2026: The Best Models to Run on Your Own Hardware (Qwen, Mistral, Llama Updated) — AI Magicx](https://www.aimagicx.com/blog/local-ai-models-2026-qwen-mistral-llama-hardware-guide)
- [Open Source LLM Comparison Table (2026) — ComputingForGeeks](https://computingforgeeks.com/open-source-llm-comparison/)
- [Small LLM Performance Benchmark - Research Report — AscentCore](https://ascentcore.com/2026/04/01/small-llm-performance-benchmark/)
- [Llama 3 8B vs Qwen 3 7B: 2026 Local LLM Verdict](https://www.kunalganglani.com/blog/llama-3-8b-vs-qwen-3-7b)
- [Best Ollama Model for Tool Calling Agent 2026: Comparison & Benchmarks](https://webscraft.org/blog/yaku-model-ollama-obrati-dlya-agenta-z-tool-calling-porivnyannya-i-benchmarki?lang=en)
- [How to Implement Tool Calling with Gemma 4 and Python — MachineLearningMastery.com](https://machinelearningmastery.com/how-to-implement-tool-calling-with-gemma-4-and-python/)
- [Gemma 4 Tool Calling Explained: Build AI Agents with Function Calling — Analytics Vidhya](https://www.analyticsvidhya.com/blog/2026/04/gemma-4-tool-calling/)
- [Run Gemma 4 Locally with Ollama - Vision, Tool Calling, All Sizes (2026) — OpenClaw Sanctuary](https://openclawsanctuary.com/gemma4)
- [Best Ollama Models for AI Agents 2026: 9 Tested & Ranked — Local AI Master](https://localaimaster.com/blog/best-ollama-models-for-agents)
- [Qwen 3.5 + Ollama: How to Run AI Agents Locally — Matteo Giardino](https://matteogiardino.com/en/blog/qwen-35-ollama-openclaw-setup-guide)
- [qwen3.5:9b sometimes prints out tool call instead of executing it · Issue #14745 · ollama/ollama](https://github.com/ollama/ollama/issues/14745)
- [Best Local LLMs for Function Calling: Qwen 3.6, Gemma 4 — InsiderLLM](https://insiderllm.com/guides/function-calling-local-llms/)
- [Ollama Adds Qwen 3.5 with Native Tool Calling and Multimodal Support](https://summarizemeeting.com/en/news/ollama-qwen-3-5-local-tool-calling-multimodal)
- [Gemma 4 CPU Only: No GPU Needed, How Slow Is It — Gemma4All](https://gemma4all.com/blog/gemma-4-cpu-only)
- [Gemma 4 E4B on M1: 42 tokens/sec — Benchmark & Setup (2026) — LLMCheck](https://llmcheck.net/models/gemma-4-e4b-on-m1/)
