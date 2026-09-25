# Labs Módulo 1 — Arquitectura de Agentes IA · UTDT 2026

Cuatro ejemplos del Módulo 1 para correr en tu máquina con una API key de
Google AI Studio.

## El caso

Un banco recibe reclamos de clientes de tarjeta de crédito en texto libre,
por ejemplo:

> "Desconozco tres consumos en mi tarjeta terminada en 4417 de los últimos
> 10 días, quiero que me la bloqueen y que me devuelvan la plata"

El mismo caso se resuelve tres veces, con tres arquitecturas distintas, para
recorrer el *agency spectrum*: de código rígido a agente autónomo con
control humano.

| Script | Arquitectura | Agencia |
|---|---|---|
| `lab01_v_a_determinista.py` | Reglas hardcodeadas, sin LLM | Cero |
| `lab01_v_b_workflow.py` | `Agent` de ADK2 sin tools, ruteo determinista en código | Baja |
| `lab01_v_c_agente_hitl.py` | `Agent` de ADK2 con tools y aprobación humana granular | Media |
| `lab01_ej2_investigacion.py` | Agente de investigación con orquestación explícita en ADK2 (opcional) | Baja/media |

Cada script tiene, en su propio encabezado, la consigna que resuelve, cómo
la resuelve y cómo leer su salida.

## Setup

### 1. Obtener una API key

Generá una API key gratuita en [Google AI Studio](https://aistudio.google.com/apikey).

### 2. Entorno y dependencias (una sola vez)

```bash
./setup.sh
```

Crea el `.venv`, instala `requirements.txt` y, si no existe `.env`, lo crea a
partir de `.env.example`.

### 3. Completar `.env`

Editá `.env` y pegá tu key:

```
GOOGLE_API_KEY=tu-api-key
```

No compartas ni subas a ningún repo el archivo `.env`.

## Ejecutar

```bash
./run.sh 1        # Versión A — determinista, no necesita API key
./run.sh 2        # Versión B — workflow con ADK2
./run.sh 3        # Versión C — agente ADK2 con aprobación humana
./run.sh aside    # Ejercicio opcional — agente de investigación
./run.sh all      # Versiones A, B y C en secuencia
```

`run.sh` activa el `.venv` y carga `.env`, así que no hace falta activar el
entorno ni exportar variables a mano.

## Sobre la salida

El comportamiento de las Versiones B, C y del ejercicio opcional **no es
determinista**: el texto y, en la Versión C, la cantidad de pasos del agente
pueden cambiar entre corridas. La Versión A sí es 100% reproducible.

La API key gratuita tiene un límite de *requests* por minuto y por día. Si
ves un error de cuota (429), esperá un minuto y volvé a correr.

## Estructura

```
labs_mod1_alumnos/
├── setup.sh                      # crear .venv, instalar deps, armar .env
├── run.sh                        # correr un ejemplo con venv + .env cargados
├── requirements.txt
├── .env.example                  # plantilla — copiar a .env y completar
├── lab01_v_a_determinista.py
├── lab01_v_b_workflow.py
├── lab01_v_c_agente_hitl.py
└── lab01_ej2_investigacion.py
```
