---
title: "El gradiente, cómo entrena una red neuronal, y las 3 técnicas modernas de fine-tuning (SFT, LoRA, RLHF)"
created: 2026-08-07
updated: 2026-08-07
type: nivelacion-complementario
modulos: [4, 7]
tags: [gradiente, backpropagation, descenso-de-gradiente, fine-tuning, lora, rlhf, sft, peft]
---

# El gradiente, cómo entrena una red neuronal, y las 3 técnicas modernas de fine-tuning

> **Relación con el resto del repo**: este documento desarrolla en profundidad un tema que `nivelacion/04-machine-learning-deep-learning.md` da por prerrequisito y delega a fuentes externas (3Blue1Brown, Khan Academy) sin desarrollarlo -acá sí se desarrolla con texto propio. Las definiciones de fine-tuning y sus técnicas están alineadas deliberadamente con la terminología usada en la introducción del seminario ("20 LLM Fine-Tuning Techniques") -este documento no la contradice, la desarrolla.

---

## Parte 1 — El gradiente, con intuición

Imaginate que estás en una montaña, de noche, con niebla espesa. No podés ver el valle, pero querés llegar a él -al punto más bajo posible- porque ahí es donde está lo que buscás. Lo único que podés hacer es sentir, con los pies, hacia qué lado el suelo baja más pronunciadamente *ahí donde estás parado, en este momento*. Das un paso en esa dirección. Volvés a sentir el suelo. Das otro paso. Repetís esto muchas veces, y aunque nunca viste el mapa completo de la montaña, terminás llegando a un valle -no necesariamente el más bajo de todos los que existen, pero sí uno razonablemente bajo.

Eso es, en esencia, cómo se entrena una red neuronal. La "montaña" es una función que mide **qué tan mal está prediciendo la red en este momento** -se llama función de pérdida, o *loss*. Cuanto más alto el valor de la pérdida, peor está la red. Cuanto más bajo, mejor. Entrenar una red neuronal es, literalmente, buscar el conjunto de parámetros (los "pesos" de la red -las perillas que se pueden ajustar) que hace que esa pérdida sea lo más baja posible.

El **gradiente** es exactamente lo que sentías con los pies en la analogía: una señal local que te dice, parado exactamente donde estás ahora, hacia qué dirección aumenta más rápido la pérdida. No te dice dónde está el valle. No te dice si hay un valle más profundo del otro lado de la montaña. Solo te dice: "desde acá, si movés esta perilla un poquito hacia arriba, la pérdida sube; si la movés hacia abajo, la pérdida baja -y esta otra perilla influye todavía más". Como querés que la pérdida *baje*, te movés en la dirección **opuesta** al gradiente. Por eso el algoritmo se llama *descenso* de gradiente: bajás siguiendo la dirección contraria a la que el gradiente señala.

Un par de intuiciones adicionales que van a ser importantes más adelante:

- **El paso que das importa.** Si el paso es demasiado grande, podés pasarte de largo el valle y terminar más arriba de donde empezaste. Si es demasiado chico, tardás una eternidad en llegar. Ese tamaño de paso tiene un nombre técnico: la **tasa de aprendizaje** (*learning rate*).
- **Una red neuronal moderna no tiene una sola perilla -tiene miles de millones.** Cada peso de cada capa es una perilla distinta, y el gradiente te da, simultáneamente, la dirección de ajuste para cada una de esas miles de millones de perillas. Calcular eso de forma eficiente es, en sí mismo, un problema no trivial -y es exactamente lo que resuelve el algoritmo de *backpropagation* que vemos en la Parte 2.
- **El gradiente es una propiedad local, no global.** Solo sabe describir la pendiente justo donde estás parado. Por eso el entrenamiento puede quedar atascado en un valle que no es el más profundo posible (un "mínimo local") -en la práctica, con redes grandes y suficientes datos, esto resulta ser mucho menos catastrófico de lo que la intuición ingenua sugeriría, pero es una limitación real del método.

---

## Parte 2 — El gradiente, más formal

Formalicemos la montaña. Sea `θ` el vector que contiene **todos** los pesos entrenables de la red -si la red tiene mil millones de parámetros, `θ` es un vector de mil millones de números. Sea `L(θ)` la función de pérdida: un número que mide qué tan mal predice la red con esos pesos concretos, medido sobre un lote de ejemplos de entrenamiento (pares entrada-salida correcta).

El **gradiente** de `L` respecto de `θ`, que se escribe `∇θ L(θ)`, es el vector de **derivadas parciales** de `L` respecto de cada peso individual:

```
∇θ L(θ) = ( ∂L/∂θ_1 , ∂L/∂θ_2 , ... , ∂L/∂θ_n )
```

Cada componente `∂L/∂θ_i` responde exactamente la pregunta de la analogía: "si muevo únicamente el peso `θ_i` una cantidad infinitesimal, manteniendo todos los demás fijos, ¿cuánto y en qué dirección cambia la pérdida?". El vector completo apunta, en el espacio de todos los pesos simultáneamente, hacia la dirección de **mayor aumento** de la pérdida.

La regla de actualización de **descenso de gradiente** es directa: en cada paso `t`, actualizás los pesos moviéndote en la dirección opuesta al gradiente, escalado por la tasa de aprendizaje `η`:

```
θ(t+1) = θ(t) − η · ∇θ L(θ(t))
```

Repetido miles o millones de veces, sobre lotes de datos distintos en cada paso (eso es lo que significa la S de **SGD**, *Stochastic Gradient Descent* -"estocástico" porque cada paso usa una muestra aleatoria de datos, no el dataset completo, lo cual es tanto una necesidad práctica con datasets enormes como, empíricamente, ayuda a evitar algunos mínimos locales malos), los pesos convergen hacia una región donde la pérdida es baja. En la práctica casi nadie usa SGD puro -se usan variantes como **Adam**, que ajustan la tasa de aprendizaje de forma adaptativa por cada peso individual y suavizan la trayectoria acumulando información de los gradientes de pasos anteriores- pero el principio de fondo es exactamente el mismo: seguir el gradiente, en la dirección contraria, con pasos de tamaño razonable.

### Backpropagation: cómo se calcula el gradiente en la práctica

Calcular `∂L/∂θ_i` para cada uno de los miles de millones de pesos, uno por uno y de forma independiente, sería computacionalmente inviable. **Backpropagation** (retropropagación) es el algoritmo que lo hace tratable, aprovechando la **regla de la cadena** del cálculo diferencial y la estructura en capas de la red.

La idea central: la red se computa en dos pasadas.

1. **Pasada hacia adelante (*forward pass*)**: la entrada `x` atraviesa la red capa por capa -cada capa aplica su transformación (una multiplicación de matriz por los pesos de esa capa, más una no linealidad)- hasta producir una predicción `ŷ`, que se compara contra el valor correcto `y` mediante la función de pérdida, dando `L(ŷ, y)`.

2. **Pasada hacia atrás (*backward pass*)**: partiendo del error en la salida (`∂L/∂ŷ`), backpropagation propaga ese error **hacia atrás**, capa por capa, usando la regla de la cadena para calcular cuánto contribuyó cada peso de cada capa al error final. La regla de la cadena dice, esquemáticamente, que la derivada de una composición de funciones es el producto de las derivadas de cada función -así que el gradiente de una capa profunda se calcula multiplicando, en cadena, los gradientes locales de cada capa entre esa y la salida.

Lo elegante del algoritmo es que **reutiliza cómputo**: los términos intermedios que se calculan al propagar el error desde la capa `N` hacia la capa `N-1` son exactamente los que hacen falta para seguir propagando desde la capa `N-1` hacia la capa `N-2`, y así sucesivamente. Esto significa que backpropagation calcula el gradiente completo, respecto de **todos** los pesos de la red, en esencialmente el mismo costo computacional que una sola pasada hacia adelante extra -en vez del costo, muchísimo mayor, de calcular cada derivada parcial por separado desde cero.

Una vez que backpropagation entregó `∇θ L`, ese vector se usa directamente en la regla de actualización de descenso de gradiente de más arriba. **Entrenar una red neuronal es, de punta a punta, este ciclo repetido: forward pass → calcular la pérdida → backward pass (backpropagation) → actualizar los pesos con descenso de gradiente → repetir con el próximo lote de datos.**

---

## Parte 3 — Qué es el fine-tuning

Un modelo de lenguaje grande se entrena primero en una etapa de **preentrenamiento** (*pretraining*): se ajustan sus pesos, con exactamente el ciclo descripto arriba, sobre una cantidad enorme de texto genérico, con un objetivo simple (predecir la próxima palabra). El resultado es un modelo con conocimiento general del lenguaje y del mundo, pero sin ningún comportamiento específico entrenado -no sabe, por ejemplo, comportarse como un asistente que responde preguntas de forma útil y segura.

**Fine-tuning** (ajuste fino) es continuar ese mismo proceso de entrenamiento -el mismo ciclo forward pass, backpropagation, descenso de gradiente- pero **a partir de los pesos ya preentrenados**, sobre un dataset más chico y más específico, para especializar el comportamiento del modelo hacia un objetivo concreto. Es importante remarcar qué *no* es fine-tuning: no es lo mismo que darle instrucciones al modelo dentro del prompt (*in-context learning*, *prompting*) -eso no modifica ni un solo peso de la red, es información temporal que se procesa en cada llamada y se descarta después. Fine-tuning sí modifica los pesos, de forma persistente, mediante el mecanismo de gradiente que ya conocés.

---

## Parte 4 — Las 3 técnicas modernas más importantes

### 1. SFT (Supervised Fine-Tuning) — enseñar por imitación de ejemplos

La técnica más directa: se arma un dataset de pares (instrucción, respuesta ideal) -escritos por humanos, o generados y curados- y se continúa entrenando el modelo preentrenado con el mismo objetivo de predicción de próxima palabra, pero ahora sobre estos ejemplos de instrucción-respuesta en vez de texto genérico de internet. El modelo aprende, por imitación estadística, a producir respuestas con el estilo y la estructura de esos ejemplos -de ahí que también se la llame *instruction tuning*.

Mecánicamente, SFT **no introduce ningún concepto nuevo** respecto de lo que ya viste: es exactamente el mismo ciclo de gradiente descendente y backpropagation de la Parte 2, aplicado sobre un dataset distinto (curado, más chico, con un formato específico de instrucción-respuesta) en vez del corpus genérico del preentrenamiento.

La limitación de SFT es la que motiva la técnica siguiente de este documento: solo puede enseñar lo que puede demostrarse con un ejemplo concreto de "la respuesta ideal". Pero muchas veces lo que se quiere optimizar es más parecido a una preferencia relativa ("esta respuesta es mejor que esa otra, aunque ninguna de las dos sea perfecta") que a una única respuesta correcta -para eso hace falta RLHF (técnica 3, más abajo).

### 2. LoRA (Low-Rank Adaptation) — fine-tuning eficiente en parámetros

El problema que resuelve: hacer fine-tuning completo de un modelo con miles de millones de parámetros significa actualizar *todos* esos pesos, lo que exige guardar en memoria no solo los pesos sino también sus gradientes y el estado del optimizador para cada uno -típicamente 3 a 4 veces el tamaño del modelo en memoria adicional. Para modelos grandes, esto es prohibitivamente caro en la mayoría de los contextos.

La idea de LoRA: en vez de actualizar la matriz de pesos original `W` (de dimensiones `d×d`) directamente, se la **congela** -no se le calcula gradiente, no se actualiza- y se aprende, por separado, una matriz de corrección `ΔW` que se suma: `W' = W + ΔW`. La innovación central es **restringir `ΔW` a tener rango bajo**: en vez de ser una matriz completa de `d×d` parámetros libres, se la factoriza como el producto de dos matrices mucho más chicas, `ΔW = B·A`, donde `B` es de `d×r` y `A` es de `r×d`, con `r` (el "rango") mucho menor que `d` -en la práctica, `r` suele estar entre 4 y 64, mientras `d` puede ser de varios miles.

Solo `A` y `B` reciben gradiente y se entrenan -`W` permanece congelada todo el tiempo. Como `r ≪ d`, la cantidad de parámetros entrenables se reduce drásticamente: del orden de un 90% menos parámetros entrenables que un fine-tuning completo, con calidad comparable en la mayoría de las tareas evaluadas. Un detalle práctico importante: en el momento de servir el modelo (*inference*), `W + BA` se puede pre-calcular y fusionar en una única matriz, así que **no hay ningún costo extra de latencia** respecto de un modelo con fine-tuning completo -la eficiencia de LoRA está toda del lado del entrenamiento, no de la inferencia.

Una variante ampliamente usada es **QLoRA**: la misma idea de LoRA, pero la matriz base `W` (congelada) se almacena cuantizada a 4 bits en vez de en precisión completa, reduciendo todavía más el uso de memoria, mientras los adaptadores `A` y `B` se siguen entrenando en mayor precisión. Esto permite hacer fine-tuning de modelos grandes en hardware considerablemente más modesto.

### 3. RLHF (Reinforcement Learning from Human Feedback) — alinear por preferencias, no por imitación

El problema que resuelve: SFT enseña al modelo a imitar ejemplos, pero muchas de las cualidades que se quieren en un asistente -qué tan útil, seguro o bien ponderada es una respuesta frente a otra- son más fáciles de **comparar** que de escribir como un único ejemplo "perfecto". RLHF ataca ese problema en tres etapas:

1. **Recolección de datos de preferencia**: se le muestran a evaluadores humanos dos (o más) respuestas candidatas para el mismo prompt, generadas por el propio modelo, y se les pide elegir cuál prefieren.

2. **Entrenamiento de un modelo de recompensa** (*reward model*): con esos datos de comparación, se entrena -otra vez, con el mismo mecanismo de gradiente y backpropagation- un modelo separado cuya única tarea es predecir un puntaje de "qué tan buena" es una respuesta, de forma consistente con las preferencias humanas observadas.

3. **Optimización por refuerzo**: se usa un algoritmo de aprendizaje por refuerzo -clásicamente **PPO** (*Proximal Policy Optimization*)- para seguir ajustando los pesos del modelo (el que ya pasó por SFT), esta vez con el objetivo de maximizar el puntaje que le asigna el modelo de recompensa a sus propias respuestas. Un detalle importante de diseño: se agrega una penalización basada en divergencia KL respecto del modelo original de SFT, para evitar que el modelo se aleje tanto en busca de maximizar el puntaje que termine explotando algún defecto del modelo de recompensa en vez de mejorar de verdad -esto se conoce como *reward hacking*, y es exactamente el mismo fenómeno que se estudia como superficie de ataque en el capítulo 7 de este curso.

Vale la pena remarcar una variante moderna que simplifica bastante esta receta: **DPO** (*Direct Preference Optimization*) elimina por completo el modelo de recompensa separado y el ciclo explícito de RL -reformula los mismos datos de preferencia como una función de pérdida que se puede optimizar directamente con descenso de gradiente y backpropagation estándar, el mismo mecanismo de siempre, sin la complejidad adicional de entrenar un reward model y correr PPO. También existen **RLAIF** (la misma idea de RLHF, pero con retroalimentación generada por otro modelo de IA en vez de evaluadores humanos) y variantes recientes más eficientes en memoria como **GRPO** y **RLVR**.

---

## El hilo que conecta todo

Vale la pena cerrar con el punto que probablemente sea el más importante de todo el documento: **preentrenamiento, SFT, LoRA y RLHF/DPO no son mecanismos distintos** -las cuatro técnicas usan exactamente el mismo motor de fondo, el ciclo de la Parte 2 (forward pass → pérdida → backpropagation → descenso de gradiente). Lo que cambia entre una técnica y otra es (a) sobre qué datos se calcula la pérdida, (b) qué función de pérdida se usa, y (c) sobre cuántos y cuáles parámetros se permite que el gradiente actúe. Entender el gradiente y backpropagation con solidez es, en ese sentido, entender el núcleo común de todo lo demás que vas a ver sobre cómo se entrenan y se ajustan los modelos que este curso trata como superficie de ataque.
