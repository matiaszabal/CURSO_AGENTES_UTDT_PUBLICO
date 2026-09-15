# Labs — Módulo 2: Diseño de Sistemas Agénticos

**Curso**: Arquitectura de Agentes IA — UTDT
**Entorno recomendado**: Google Colab o entorno local con Python 3.10+ — **no requiere cuenta de GCP**, solo una API key gratuita de [Google AI Studio](https://aistudio.google.com/apikey)

Tres ejercicios con Google ADK2, todos ambientados en una mesa de reclamos de tarjeta de crédito (datos sintéticos, sin relación con personas ni operaciones reales):

| # | Archivo | Qué muestra |
|---|---|---|
| 1 | [`ejercicio_1_agente_reclamos.py`](ejercicio_1_agente_reclamos.py) | Un agente con tools (`FunctionTool`) y un gate de aprobación humana por monto |
| 2 | [`ejercicio_2_pipeline_paralelo.py`](ejercicio_2_pipeline_paralelo.py) | Multiagente con `ParallelAgent` + `SequentialAgent`, y benchmark paralelo vs. secuencial |
| 3 | [`ejercicio_3_routing_dinamico.py`](ejercicio_3_routing_dinamico.py) | Un router que elige dinámicamente el modelo (barato/medio/caro) según la complejidad de la query |

Bonus opcional: [`demo_dos_modelos.py`](demo_dos_modelos.py) corre la misma query con un modelo barato y uno caro, y muestra el contraste de costo/latencia lado a lado — es el ejemplo más rápido para entender el problema que resuelve el Ejercicio 3.

Los tres ejercicios son independientes entre sí y se pueden correr en cualquier orden (el Ejercicio 3 reutiliza el dominio de datos del Ejercicio 1, pero no importa su código).

---

## Setup (una sola vez)

```bash
cd MODULO_2/labs
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

En Google Colab:

```python
!pip install -q "google-adk>=2.8.0" nest_asyncio
```

### Autenticación

Estos labs corren contra **Google AI Studio**, no contra Vertex AI: no hace falta cuenta de GCP, `gcloud`, ni proyecto configurado.

1. Conseguí una API key gratuita en [aistudio.google.com/apikey](https://aistudio.google.com/apikey).
2. Configurala **antes** de correr cualquier script:

```bash
export GOOGLE_API_KEY="tu-api-key-de-ai-studio"
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
```

En un notebook (Colab/Jupyter):

```python
import os
os.environ["GOOGLE_API_KEY"] = "tu-api-key-de-ai-studio"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
```

> ⚠️ **No pegues tu API key en un notebook que subas a un repositorio.** Es la fuga de credenciales más común en entregas de cursos. Si usás Colab, guardala en *Secrets* (ícono de llave en el panel izquierdo) en vez de escribirla en una celda.

### Cuota del tier gratuito — leé esto antes de correr nada

La API key gratuita tiene un límite de requests por minuto y por día, distinto para cada modelo. Consumo aproximado de cada ejercicio:

| Ejercicio | Llamadas al modelo | Modelos | Comentario |
|---|---|---|---|
| 1 | ~6–18 | `gemini-2.5-flash` | 6 casos de prueba × 1 a 3 turnos con tool calls cada uno |
| 2 | **~18** | `gemini-2.5-flash` | 3 mensajes × (3 análisis en paralelo + los mismos 3 en secuencial) |
| 3 | ~10 | `gemini-2.5-flash-lite` + `gemini-2.5-flash` + **`gemini-2.5-pro`** | 5 queries × (1 clasificación + 1 ejecución); 2 de las 5 caen en `gemini-2.5-pro`, que suele tener la cuota gratuita más ajustada |
| bonus | ~2 | `gemini-2.5-flash-lite` + `gemini-2.5-pro` | `demo_dos_modelos.py`, una corrida por modelo |

**El Ejercicio 2 es el que más rápido agota la cuota**: dispara los tres analizadores en paralelo (tres requests en la misma fracción de segundo) y lo repite tres veces.

No hace falta correr los tres ejercicios el mismo día — son independientes.

---

## Cómo correr cada ejercicio

```bash
python ejercicio_1_agente_reclamos.py
python ejercicio_2_pipeline_paralelo.py
python ejercicio_3_routing_dinamico.py

# Bonus: comparación rápida modelo barato vs. caro
python demo_dos_modelos.py simple      # clasificación simple
python demo_dos_modelos.py compleja    # decisión de negocio
```

Cada script imprime en consola su propia evaluación (casos de prueba, benchmark de tiempos o análisis de costo, según el ejercicio) — no hace falta ningún argumento salvo en `demo_dos_modelos.py`.

---

## Errores frecuentes

Los problemas que más tiempo hacen perder en estos labs, con el síntoma literal y el arreglo.

### 1. `429 RESOURCE_EXHAUSTED` — se agotó la cuota

**Dónde:** cualquier ejercicio. Con mucha más frecuencia en el Ejercicio 2.

```text
google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED
```

**No es un bug: es el límite del tier gratuito de AI Studio**, que tiene cuota por minuto y por día, distinta para cada modelo. Qué hacer, en orden:

1. **Esperar.** Si el límite es el de por minuto, se libera solo en menos de sesenta segundos. Si es el diario, hay que esperar al día siguiente.
2. **Recortar las listas.** Son constantes al principio de cada script y bajarlas no cambia nada de lo que el ejercicio enseña:
   - Ejercicio 1 → recortar `CASOS_DE_PRUEBA`.
   - Ejercicio 2 → dejar **un solo** mensaje en `MENSAJES_TEST` (pasa de ~18 llamadas a ~6).
   - Ejercicio 3 → dejar **dos** casos en `QUERIES_EVALUACION`, uno simple y uno complejo (pasa de ~10 llamadas a ~4). Alcanza para ver el contraste de costo, que es el punto.
3. **Espaciar las llamadas.** En el Ejercicio 2, un `await asyncio.sleep(20)` entre mensajes dentro del loop de `main()`; en el Ejercicio 3, un `time.sleep(10)` entre casos. Tarda más y no falla.
4. **Ojo con `gemini-2.5-pro`.** Suele ser el modelo con la cuota gratuita más ajustada, y el Ejercicio 3 lo invoca para las queries que el router clasifica como "complejas". Si solo falla ahí, cambiá `MODELO_MAP["compleja"]` por `"gemini-2.5-flash"` en `ejercicio_3_routing_dinamico.py`: el patrón de routing queda idéntico, solo cambian los números de costo.
5. **No corras los tres ejercicios el mismo día** si estás con la cuota justa.

> Esto también es contenido, no solo un obstáculo: en producción la cuota es un componente de arquitectura que entra en el presupuesto y necesita una política de reintento con backoff. Un agente que se cae con un 429 no es un agente confiable.

### 2. El modelo devuelve el JSON envuelto en un bloque markdown

**Dónde:** Ejercicio 3 (`clasificar_complejidad`). Los agentes de análisis del Ejercicio 2 (`analizador_sentimiento`, `analizador_urgencia`, `clasificador_tema`) también piden JSON, pero ese JSON nunca se parsea en Python — pasa como texto al agente agregador, así que ahí este error no puede ocurrir.

Aunque el prompt diga "respondé ÚNICAMENTE con un JSON válido", el modelo devuelve con frecuencia esto:

````text
```json
{"complejidad": "simple", "justificacion": "Pregunta factual directa."}
```
````

Y entonces `json.loads(contenido)` explota con `json.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`.

`ejercicio_3_routing_dinamico.py` ya maneja este caso (limpia el bloque markdown antes de parsear, y usa un `try/except` con un valor por defecto si igual falla). **La salida de un LLM es una entrada no confiable**: se valida como se valida cualquier input externo. Si adaptás el código a tu propio dominio y agregás un `json.loads` en algún otro lugar (por ejemplo, para leer de verdad la salida de los analizadores del Ejercicio 2), conservá ese patrón.

### 3. `API key not valid` / el cliente no encuentra la credencial

**Dónde:** cualquier ejercicio, en la primera llamada al modelo.

```text
ValueError: No API key was provided. Please pass a valid API key.
```
```text
google.genai.errors.ClientError: 400 INVALID_ARGUMENT ... API_KEY_INVALID
```

Verificá en este orden:

1. Que `GOOGLE_API_KEY` esté seteada **antes** de correr el script.
2. Que sea una key de **AI Studio** ([aistudio.google.com/apikey](https://aistudio.google.com/apikey)), no un service account de GCP.
3. Que no haya quedado un `GOOGLE_GENAI_USE_VERTEXAI=TRUE` (o `=1`) dando vueltas en el entorno: con esa variable activa el cliente ignora la API key y busca credenciales de Vertex, que no tenés.
4. En Colab, si guardaste la key en *Secrets*, acordate de habilitar el acceso del notebook y de copiarla a `os.environ` — no se inyecta sola.

### 4. `RuntimeError: asyncio.run() cannot be called from a running event loop`

**Dónde:** los tres ejercicios, si los corrés en Colab o Jupyter.

Los tres terminan con `asyncio.run(...)` dentro de un `if __name__ == "__main__":`, correcto para un script `.py` pero no dentro de un notebook (que ya tiene un event loop corriendo). Dos salidas, ambas válidas:

```python
# a) parchear asyncio una vez, al principio del notebook — funciona para
#    los tres ejercicios sin tocar nada más:
import nest_asyncio; nest_asyncio.apply()
asyncio.run(main())  # o asyncio.run(ejecutar_suite_evaluacion()) en el Ejercicio 1

# b) correrlo como script de verdad:
#    python ejercicio_1_agente_reclamos.py
```

El punto de entrada de cada uno cambia de nombre: `ejecutar_suite_evaluacion()` en el Ejercicio 1, `main()` en los Ejercicios 2 y 3.

### 5. `ModuleNotFoundError` después de un `!pip install` en Colab

**Dónde:** cualquier ejercicio, típicamente con `google-adk`.

Colab a veces necesita reiniciar el runtime para ver un paquete recién instalado. Si el `!pip install` terminó bien pero el `import` falla: **Entorno de ejecución → Reiniciar sesión**, y volver a correr desde la primera celda. No hace falta reinstalar, los paquetes siguen ahí.

---

## Adaptar el dominio a tu propio caso

`RECLAMOS_DB` (Ejercicio 1) es una tabla en memoria con 4 casos. Si trabajás en un área con reglas de negocio propias, reemplazala por una tabla de tu proceso y dejá el resto igual: las tools, el gate de aprobación humana y el patrón de evaluación funcional son genéricos.

En el Ejercicio 2, el benchmark de `main()` solo corre los 3 analizadores en paralelo (`pipeline_analisis`) para medir el speedup — no ejecuta el agente agregador. El módulo también define `agregador` y `pipeline_completo` (`ParallelAgent` seguido del agregador vía `SequentialAgent`) por si querés ver la síntesis final de los 3 análisis; para probarlo, corré ese pipeline con un `InMemoryRunner` igual que hace `benchmark_paralelo_vs_secuencial` con `pipeline_analisis`, y revisá el estado de la sesión al final.
