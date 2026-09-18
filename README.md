# Arquitectura de Agentes IA — UTDT

- [Módulo 1](MODULO_1/)
- [Tutorial 0 — Introducción a Google ADK](ADK_Tutorial0/)
- [Módulo 4 — Labs de MCP con `adk web`](MODULO_4/labs_MCP/)
- [Recursos de aprendizaje](recursos_aprendizaje/)
- [Pre-curso](https://matiaszabal.github.io/utdt-slides/pre-curso/)

## Cómo correr los labs

Cada carpeta tiene su propio README con el paso a paso. Resumen para el
**Módulo 4 (labs de MCP)**:

```bash
git clone https://github.com/matiaszabal/CURSO_AGENTES_UTDT_PUBLICO.git
cd CURSO_AGENTES_UTDT_PUBLICO/MODULO_4/labs_MCP
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # pegá tu API key de Google AI Studio (gratis)
adk web                   # http://127.0.0.1:8000
```

Necesitás Python 3.10+, Node.js y una key de <https://aistudio.google.com/apikey>.
Detalle, ejemplos de prompts y solución de problemas en
[`MODULO_4/labs_MCP/README.md`](MODULO_4/labs_MCP/README.md).
