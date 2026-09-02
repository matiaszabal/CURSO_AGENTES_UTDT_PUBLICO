# Embeddings y Búsqueda Vectorial: el mecanismo detrás de RAG

> **Por qué este documento.** El catálogo de amenazas de MAESTRO (Capa 2 →
> RAG & Retrieval Attacks) nombra **Context Stuffing**, **Semantic Search
> Manipulation** y **Vector Database Poisoning** sin desarrollar el mecanismo
> de embeddings y k-nearest-neighbors que las tres explotan. Este documento
> junta ese refresco en un solo lugar.
>
> **Qué asume ya sabido.** Que un modelo de embedding es un modelo entrenado
> (no se desarrolla acá cómo se entrena) y que ya se vio, en capítulos
> anteriores, la arquitectura general de un pipeline RAG (Planificador →
> Ejecutor → Herramientas → Memoria del Cap. 1). Acá el foco es
> específicamente cómo la memoria vectorial *decide* qué documentos trae al
> contexto, porque ese mecanismo de decisión es exactamente lo que las tres
> amenazas de Capa 2 explotan.

## Qué es un embedding

Un **embedding** es un vector numérico —de cientos o miles de dimensiones—
que un modelo de embedding produce a partir de un texto (una palabra, una
oración, un documento entero), construido de forma tal que textos
**semánticamente parecidos caen "cerca" unos de otros** en ese espacio de
alta dimensión. "Cerca" acá no es una métrica geográfica ni de coincidencia
de palabras: es geometría sobre significado. Dos oraciones que dicen lo
mismo con palabras completamente distintas ("el gato duerme en el sillón" /
"el felino descansa sobre el sofá") producen vectores cercanos; dos
oraciones con palabras parecidas pero significado opuesto pueden quedar
lejos.

La métrica estándar para medir esa cercanía es la **similitud coseno**: el
coseno del ángulo entre dos vectores, que va de -1 (opuestos) a 1
(idénticos en dirección), independiente de la magnitud de los vectores —lo
que importa es hacia dónde "apuntan", no qué tan largos son.

## Cómo decide un vector store qué traer al contexto

Un vector store **no busca por palabras clave** como lo haría un motor de
búsqueda tradicional. El flujo es:

1. La **query** del usuario se convierte en un embedding, con el mismo
   modelo de embedding que se usó para indexar los documentos.
2. El vector store calcula la similitud coseno entre ese embedding de query
   y **todos** los embeddings de documentos indexados (en la práctica, con
   estructuras de índice que evitan comparar contra todos literalmente, pero
   el resultado es equivalente).
3. Devuelve los **k vectores de documento más cercanos** —el algoritmo se
   llama **k-nearest-neighbors (k-NN)**— y esos son los documentos que se
   concatenan al prompt como "contexto" antes de llamar al modelo.

El punto crítico para entender las tres amenazas de MAESTRO Capa 2: el
mecanismo de recuperación **solo verifica cercanía en el espacio de
embeddings**. No verifica veracidad del contenido, no verifica quién escribió
el documento, no verifica si el documento sigue siendo relevante — verifica
exclusivamente una cosa: "¿este vector está cerca del vector de la query?".
Cualquier ataque que logre manipular esa única variable —la posición del
documento en el espacio de embeddings, o el volumen de contenido que compite
por el top-k— tiene éxito, sin necesidad de tocar nada más en el pipeline.

## Las tres amenazas de Capa 2, explicadas desde este mecanismo

| Amenaza | Qué manipula | Cómo actúa sobre el mecanismo de k-NN |
|---|---|---|
| **Semantic Search Manipulation** | El *contenido* de un documento nuevo | Redacta un documento deliberadamente cerca, en el espacio de embeddings, de las queries que le interesan al atacante —el equivalente de SEO adversarial aplicado a embeddings en vez de a rankings de buscador. El documento entra al índice de forma legítima (nadie lo intercepta), pero fue *diseñado* para ganar la carrera de recuperación. |
| **Context Stuffing** | El *volumen* de contenido que compite por el top-k | No necesita que ningún documento individual sea especialmente relevante — inunda el índice con contenido de alta similitud superficial (embeddings cercanos a queries comunes) pero bajo valor informativo real, de forma que el contexto legítimo quede diluido o directamente excluido del top-k por el límite de tokens de la ventana de contexto. Es un ataque de *disponibilidad* de la información correcta, no de integridad del contenido. |
| **Vector Database Poisoning** | La *representación* de un documento ya existente | No toca el contenido textual del documento en absoluto —accede directamente al store (o al pipeline de embedding) y reescribe la coordenada almacenada, de forma que un documento legítimo, con el mismo texto de siempre, empiece a aparecer como "cercano" a queries que antes no lo hubieran recuperado. Auditar el contenido de los documentos uno por uno no detecta este ataque: el contenido está limpio, lo que está corrompido es la entrada del índice que dice dónde vive semánticamente ese documento. |

La distinción operativa más importante de la tabla: Semantic Search
Manipulation y Context Stuffing entran por el **pipeline de ingesta**
(alguien publica o inyecta contenido nuevo); Vector Database Poisoning entra
por el **acceso al store o al modelo de embedding** — requiere un privilegio
más alto de montar, pero es más difícil de detectar porque no deja rastro en
el contenido.

## Por qué esto es, mecánicamente, RAG Data Poisoning y no solo "recuperación ruidosa"

Traer al contexto un documento con contenido malicioso —vía Semantic Search
Manipulation o directamente porque el atacante logró que se indexe— es el
paso previo típico de **RAG Data Poisoning** (ya cubierto en el Lab 2.2 —
ver `labs/guias_alumnos/lab22_rag_poisoning.md`): el mecanismo de k-NN no distingue "esto es un hecho a citar" de
"esto es una instrucción a ejecutar" — trae el vector más cercano y lo
concatena al prompt como contexto confiable, sin ninguna separación
sintáctica entre dato e instrucción. El modelo, corriente abajo, hereda el
mismo problema de fondo que Prompt Injection en Capa 1: no hay, a nivel de
arquitectura Transformer, un canal de instrucción separado del canal de
datos.

## Para seguir pensando

1. Si un vector store agregara un umbral mínimo de similitud (rechazar
   cualquier resultado por debajo de cierto score, en vez de siempre traer
   los k más cercanos aunque sean mediocres), ¿a cuál de las tres amenazas
   de la tabla afectaría más? ¿A cuál no afectaría en absoluto?
2. Vector Database Poisoning requiere acceso directo al store o al modelo de
   embedding —un privilegio más alto que publicar un documento. ¿Qué control
   de los que ya viste en Capa 4 (IAM, mínimo privilegio) aplicarías
   específicamente sobre quién puede escribir en un vector store de
   producción?
